#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [ "numpy", "paraview", "foamlib"]
# ///
#!/usr/bin/env pvpython
"""
Compute field-based metrics from OpenFOAM case using ParaView.

Usage:
    pvpython compute_metric.py <case_dir> <metric_name>

Available metrics:
    combustion_efficiency    - Fuel conversion efficiency (0-1)
    ch4_domain_average      - Volume-averaged CH4 in domain (0-1)
    pattern_factor          - Temperature pattern factor (>0)
    temperature_rise        - Temperature rise efficiency (0-1)

Note: pressure_loss has been moved to get_metric.sh for faster extraction from logs

Outputs only the scalar metric value, or error message with traceback.
"""

import sys
import traceback
from pathlib import Path

from paraview.simple import *
import vtk

try:
    from foamlib import FoamFile
    FOAMLIB_AVAILABLE = True
except ImportError:
    FOAMLIB_AVAILABLE = False


def read_boundary_condition(case_dir, field_name, patch_name, fallback_value):
    """
    Read boundary condition value from OpenFOAM field file using foamlib.

    Args:
        case_dir: Path to case directory
        field_name: Field name (e.g., 'CH4', 'T')
        patch_name: Patch name (e.g., 'inletFuel', 'inletAir')
        fallback_value: Value to use if reading fails

    Returns:
        Boundary value (scalar or first component for vectors)
    """
    if not FOAMLIB_AVAILABLE:
        return fallback_value

    try:
        field_file = Path(case_dir) / "0.orig" / field_name
        if not field_file.exists():
            field_file = Path(case_dir) / "0" / field_name

        if not field_file.exists():
            return fallback_value

        # Read using foamlib
        foam_file = FoamFile(field_file)

        # Access boundaryField
        boundary_field = foam_file["boundaryField"]

        if patch_name not in boundary_field:
            return fallback_value

        patch_data = boundary_field[patch_name]

        # Get value - could be 'value' or inletValue depending on BC type
        if "value" in patch_data:
            value = patch_data["value"]
        elif "inletValue" in patch_data:
            value = patch_data["inletValue"]
        else:
            return fallback_value

        # Handle uniform values
        if hasattr(value, '__iter__') and not isinstance(value, str):
            # For vectors, return first component or magnitude
            if len(value) > 0:
                return float(value[0]) if len(value) == 1 else float(value)
        else:
            return float(value)

    except Exception as e:
        return fallback_value


def get_inlet_conditions(case_dir):
    """
    Read inlet boundary conditions from OpenFOAM files.

    Returns:
        dict with 'CH4_inlet' and 'T_inlet' values
    """
    # Read CH4 mass fraction at fuel inlet
    ch4_inlet = read_boundary_condition(case_dir, "CH4", "inletFuel", 0.1561)

    # Read temperature at inlets (use air inlet as reference, both should be same)
    t_inlet = read_boundary_condition(case_dir, "T", "inletAir", 300.0)

    return {
        "CH4_inlet": ch4_inlet,
        "T_inlet": t_inlet
    }


def get_combustion_efficiency(case_reader, case_dir):
    """
    Compute: η_c = 1 - (CH4_outlet / CH4_inlet)

    Uses outlet patch directly to measure fuel conversion.
    This correctly measures fuel conversion for a flow-through combustor.
    """
    # Read inlet CH4 mass fraction from boundary conditions
    inlet_conditions = get_inlet_conditions(case_dir)
    ch4_inlet = inlet_conditions["CH4_inlet"]

    # Extract outlet patch directly from multi-block dataset
    # ParaView loads patches as separate blocks
    case_reader.UpdatePipeline()

    # Get available blocks (convert to list)
    blocks_property = case_reader.GetPropertyValue("MeshRegions")
    blocks = list(blocks_property)  # Convert to regular Python list

    outlet_block_name = None
    outlet_block_index = None
    for i, block in enumerate(blocks):
        if 'outlet' in block.lower():
            outlet_block_name = block
            outlet_block_index = i
            break

    if outlet_block_name is None:
        raise ValueError(f"Outlet patch not found. Available blocks: {blocks}")

    # Fetch the entire multi-block dataset from the case reader
    # OpenFOAM reader returns: [internalMesh, boundary[patches...]]
    full_data = servermanager.Fetch(case_reader)

    # Find outlet patch in the hierarchical structure
    # Structure: Block 0 = internalMesh, Block 1 = boundary (contains patches)
    outlet_block = None
    for i in range(full_data.GetNumberOfBlocks()):
        block = full_data.GetBlock(i)
        block_name = full_data.GetMetaData(i).Get(vtk.vtkCompositeDataSet.NAME()) if full_data.GetMetaData(i) else "unnamed"

        if outlet_block_name.lower() in block_name.lower():
            outlet_block = block
            break

        # Check sub-blocks (patches are in "boundary" block)
        if hasattr(block, 'GetNumberOfBlocks'):
            for j in range(block.GetNumberOfBlocks()):
                sub_block = block.GetBlock(j)
                sub_name = block.GetMetaData(j).Get(vtk.vtkCompositeDataSet.NAME()) if block.GetMetaData(j) else "unnamed"
                if 'outlet' in sub_name.lower():
                    outlet_block = sub_block
                    break
            if outlet_block:
                break

    if outlet_block is None:
        raise ValueError(f"Could not find outlet block in fetched data structure")

    # Get CH4 array from outlet patch (try cell data first, then point data)
    cell_data = outlet_block.GetCellData()
    point_data = outlet_block.GetPointData()

    ch4_array = cell_data.GetArray('CH4')
    if ch4_array is None:
        ch4_array = point_data.GetArray('CH4')

    if ch4_array is None:
        cell_arrays = [cell_data.GetArrayName(i) for i in range(cell_data.GetNumberOfArrays())]
        point_arrays = [point_data.GetArrayName(i) for i in range(point_data.GetNumberOfArrays())]
        raise ValueError(f"CH4 array not found at outlet. Cell arrays: {cell_arrays}, Point arrays: {point_arrays}")

    # Use VTK's IntegrateAttributes to compute area-weighted average
    # This properly integrates fields over the surface accounting for cell areas
    integrate = vtk.vtkIntegrateAttributes()
    integrate.SetInputData(outlet_block)
    integrate.Update()
    integrated_data = integrate.GetOutput()

    # Get integrated CH4 and area from integrated data
    integrated_cell_data = integrated_data.GetCellData()
    integrated_point_data = integrated_data.GetPointData()

    ch4_integrated_array = integrated_cell_data.GetArray('CH4')
    if ch4_integrated_array is None:
        ch4_integrated_array = integrated_point_data.GetArray('CH4')

    if ch4_integrated_array is None:
        raise ValueError("vtkIntegrateAttributes failed to integrate CH4")

    area_array = integrated_cell_data.GetArray('Area')
    if area_array is None:
        area_array = integrated_point_data.GetArray('Area')

    if area_array is None:
        raise ValueError("vtkIntegrateAttributes failed to compute Area")

    # Extract scalar values
    ch4_integrated = ch4_integrated_array.GetValue(0)
    area = area_array.GetValue(0)

    if area <= 0:
        raise ValueError(f"Invalid outlet area: {area}")

    # Compute area-averaged CH4 at outlet
    ch4_outlet = ch4_integrated / area

    # Efficiency based on outlet
    efficiency = 1.0 - (ch4_outlet / ch4_inlet)

    return efficiency


# REMOVED: get_pressure_loss function
# Pressure metrics have been moved to get_metric.sh for faster log-based extraction
# This avoids the need to load the entire case in ParaView just for pressure values


def get_ch4_domain_average(case_reader, case_dir):
    """
    Compute volume-averaged CH4 mass fraction over the entire domain.

    This metric indicates fuel loading/accumulation in the combustor:
    - High values: Fuel accumulating (poor combustion or transient filling)
    - Low values: Less fuel in domain (good combustion or low fuel input)

    Note: This is different from combustion_efficiency which compares outlet to inlet.
    For optimization, you typically want this value to be LOW at steady state
    (indicating fuel is being consumed, not accumulating).

    Args:
        case_reader: ParaView case reader
        case_dir: Path to case directory (for reading BCs)

    Returns:
        Volume-averaged CH4 mass fraction (0-1)
    """
    # Integrate CH4 over entire internal mesh volume
    integ = IntegrateVariables(Input=case_reader)
    integ.UpdatePipeline()

    data = servermanager.Fetch(integ)
    cell_data = data.GetCellData()

    # Get CH4 integrated value
    ch4_array = cell_data.GetArray('CH4')
    if ch4_array is None:
        raise ValueError("CH4 array not found in integrated data")
    ch4_integrated = ch4_array.GetValue(0)

    # Get volume
    vol_array = cell_data.GetArray('Volume')
    if vol_array is None:
        raise ValueError("Volume array not found in integrated data")
    volume = vol_array.GetValue(0)

    # Compute volume-averaged CH4
    if volume <= 0:
        raise ValueError(f"Invalid volume: {volume}")

    ch4_avg = ch4_integrated / volume

    return ch4_avg


def get_pattern_factor(case_reader, case_dir):
    """
    Compute: PF = (T_max - T_avg) / (T_avg - T_inlet)

    Returns a large penalty value if combustion hasn't occurred.

    Args:
        case_reader: ParaView case reader
        case_dir: Path to case directory (for reading BCs)
    """
    # Get T_max from field range
    case_reader.UpdatePipeline()
    data_info = case_reader.GetDataInformation()
    cell_data_info = data_info.GetCellDataInformation()
    T_array_info = cell_data_info.GetArrayInformation('T')

    if T_array_info is None:
        raise ValueError("Temperature array 'T' not found in cell data information")

    T_range = T_array_info.GetComponentRange(0)
    T_max = T_range[1]

    # Integrate T over volume
    integ = IntegrateVariables(Input=case_reader)
    integ.UpdatePipeline()

    data = servermanager.Fetch(integ)
    cell_data = data.GetCellData()

    # Get T integrated value
    T_array = cell_data.GetArray('T')
    if T_array is None:
        raise ValueError("Temperature array 'T' not found in integrated data")
    T_integrated = T_array.GetValue(0)

    # Get volume
    vol_array = cell_data.GetArray('Volume')
    if vol_array is None:
        raise ValueError("Volume array not found in integrated data")
    volume = vol_array.GetValue(0)

    # Compute average
    if volume <= 0:
        raise ValueError(f"Invalid volume: {volume}")

    T_avg = T_integrated / volume

    # Read inlet temperature from boundary conditions
    inlet_conditions = get_inlet_conditions(case_dir)
    T_inlet = inlet_conditions["T_inlet"]

    # Pattern factor
    denominator = T_avg - T_inlet
    if denominator <= 0:
        # No combustion occurred - return large penalty value
        # This indicates poor mixing/no ignition
        return 999.0

    PF = (T_max - T_avg) / denominator

    return PF


def get_temperature_rise_efficiency(case_reader, case_dir):
    """
    Compute: η_T = (T_avg - T_inlet) / (T_max - T_inlet)

    Returns 0.0 if combustion hasn't occurred (no temperature rise).

    Args:
        case_reader: ParaView case reader
        case_dir: Path to case directory (for reading BCs)
    """
    # Get T_max from field range
    case_reader.UpdatePipeline()
    data_info = case_reader.GetDataInformation()
    cell_data_info = data_info.GetCellDataInformation()
    T_array_info = cell_data_info.GetArrayInformation('T')

    if T_array_info is None:
        raise ValueError("Temperature array 'T' not found in cell data information")

    T_range = T_array_info.GetComponentRange(0)
    T_max = T_range[1]

    # Integrate T over volume
    integ = IntegrateVariables(Input=case_reader)
    integ.UpdatePipeline()

    data = servermanager.Fetch(integ)
    cell_data = data.GetCellData()

    # Get T integrated value
    T_array = cell_data.GetArray('T')
    if T_array is None:
        raise ValueError("Temperature array 'T' not found in integrated data")
    T_integrated = T_array.GetValue(0)

    # Get volume
    vol_array = cell_data.GetArray('Volume')
    if vol_array is None:
        raise ValueError("Volume array not found in integrated data")
    volume = vol_array.GetValue(0)

    # Compute average
    if volume <= 0:
        raise ValueError(f"Invalid volume: {volume}")

    T_avg = T_integrated / volume

    # Read inlet temperature from boundary conditions
    inlet_conditions = get_inlet_conditions(case_dir)
    T_inlet = inlet_conditions["T_inlet"]

    # Temperature rise efficiency
    denominator = T_max - T_inlet
    if denominator <= 0:
        # No combustion occurred - return 0 (worst efficiency)
        return 0.0

    eta_T = (T_avg - T_inlet) / denominator

    return eta_T


def main():
    """Main entry point."""
    try:
        # Compute requested metric
        metrics = {
            'combustion_efficiency': get_combustion_efficiency,
            'ch4_domain_average': get_ch4_domain_average,
            'pattern_factor': get_pattern_factor,
            'temperature_rise': get_temperature_rise_efficiency,
        }

        if len(sys.argv) < 3 or len(sys.argv) > 4:
            print(f"Usage: pvpython compute_metric.py <case_dir> <metric_name> [--time TIME]", file=sys.stderr)
            print(f"Available metrics: {list(metrics.keys())}", file=sys.stderr)
            print(f"Optional: --time TIME (default: latest)", file=sys.stderr)
            sys.exit(1)

        case_dir = Path(sys.argv[1])
        metric_name = sys.argv[2]

        # Parse optional time argument
        requested_time = None
        if len(sys.argv) == 4:
            time_arg = sys.argv[3]
            if time_arg.startswith('--time='):
                requested_time = float(time_arg.split('=')[1])
            else:
                sys.exit(1)

        if not case_dir.exists():
            raise FileNotFoundError(f"Case directory does not exist: {case_dir}")

        if metric_name not in metrics:
            raise ValueError(f"Unknown metric: {metric_name}. Available: {list(metrics.keys())}")

        # Check if it's a decomposed case (has processor* dirs)
        processor_dirs = list(case_dir.glob("processor*"))
        if processor_dirs:
            # Decomposed case - use case directory directly
            case_reader = OpenFOAMReader(FileName=str(case_dir))
            case_reader.CaseType = 'Decomposed Case'
        else:
            # Serial/reconstructed case - create .foam file if needed
            foam_file = case_dir / "case.foam"
            if not foam_file.exists():
                foam_file.touch()
            case_reader = OpenFOAMReader(FileName=str(foam_file))

        # Load internal mesh and boundary patches
        # Make sure to load outlet patch for efficiency calculation
        case_reader.MeshRegions = ['internalMesh', 'patch/inletAir', 'patch/inletFuel', 'patch/outlet']

        # Force refresh of pipeline information to get all time steps
        case_reader.UpdatePipelineInformation()

        # Enable ALL available cell arrays
        case_reader.CellArrays = case_reader.CellArrays.Available

        # Get time steps
        time_values = case_reader.TimestepValues
        if not time_values:
            raise ValueError("No time steps found in case")

        # Determine which time to use
        if requested_time is not None:
            # Find closest available time to requested time
            available_times = list(time_values)
            closest_time = min(available_times, key=lambda t: abs(t - requested_time))

            if abs(closest_time - requested_time) > 1e-6:
                print(f"Warning: Requested time {requested_time} not available. Using closest time {closest_time}", file=sys.stderr)

            use_time = closest_time
        else:
            # Default: use latest time
            use_time = time_values[-1]

        # Update to selected time step
        case_reader.UpdatePipeline(time=use_time)

        # Compute metric (pass case_dir for reading boundary conditions)
        value = metrics[metric_name](case_reader, case_dir)

        # Output result
        print(f"{value}")

    except Exception as e:
        print(f"Error computing metric: {e}", file=sys.stderr)
        print("\nTraceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
