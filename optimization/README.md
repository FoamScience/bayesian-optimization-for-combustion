# Bayesian Optimization for Combustion Problems

> DISCLAIMER: the optimization experiment is still WIP; there are some bugs in the case configuration...

## Overview

This project demonstrates multi-objective Bayesian optimization (MOBO) applied to the design of an **Axial Vortex-trapped Combustor (AVC)** using OpenFOAM CFD simulations and the FoamBO framework.

The goal is to optimize the combustor geometry to minimize methane emissions and temperature non-uniformity while maintaining sufficient temperature rise for efficient combustion.

## For Reproducing

```bash
# Install dependencies and setup directories
./prepare.sh

# Start optimization (requires OpenFOAM and Python environment)
uvx foamBO --config MOO.yaml
```

**Requirements**:
- OpenFOAM v2506 or later (OpenCFD version)
- Python 3.10+ with ParaView libraries
- FoamBO package

## Problem Description

### Axial Vortex-trapped Combustor (AVC)

The AVC is a compact combustion chamber design that uses aerodynamically-generated vortices to stabilize the flame and improve mixing. The geometry consists of:

- **Main channel**: A convergent/divergent flow channel with adjustable bevel geometry
- **Blunt bodies**: Front (fixed) and rear (variable) bluff bodies to generate recirculation zones
- **Swirl vanes**: Two parametric vanes (vane1 and vane2) to induce swirl and create vortex trapping

### Physics Model

**Solver**: `reactingFoam` (OpenFOAM's compressible reacting flow solver)

**Key features**:
- **Chemistry**: GRI-Mech 3.0 mechanism (53 species, 325 reactions) for methane-air combustion
- **Combustion model**: Eddy Dissipation Concept (EDC) for turbulence-chemistry interaction
- **Turbulence**: k-epsilon RANS model
- **Radiation**: P1 model with absorption-emission
- **Hot start initialization**: Domain initialized at 300K with air, then ignited with chemistry enabled

**Flow conditions**:
- Inlet velocity: 37 m/s (air)
- Inlet temperature: 300 K
- Operating pressure: 101325 Pa (atmospheric)
- Fuel: Pre-mixed methane-air at bottom inlet (15.61% CH4, 19.66% O2, 64.73% N2)

**Simulation timeline**:
1. Cold flow test (0-6 ms): Chemistry OFF, flow field development
2. Hot run (6-50 ms): Chemistry ON, combustion simulation

## Design Parameters

The optimization explores a **19-dimensional design space** with both continuous and discrete parameters:

### Channel Geometry (3 parameters)
- `bevelPosition`: [0.1, 0.3] m - Axial location of channel contraction
- `bevelAngle`: [0, 120]° - Angle of channel wall convergence
- `outletWidth`: [0.07, 0.095] m - Exit width of combustor

### Rear Blunt Body (4 parameters)
- `rearBodyLength`: [0.01, 0.03] m - Streamwise dimension
- `rearBodyWidth`: [0.02, 0.045] m - Transverse dimension
- `rearBodyPosition`: [0.12, 0.3] m - Axial location
- `rearBodyAngle`: [-80, 80]° - Rotation angle

### Vane 1 (6 parameters)
- `vane1Position`: [0.086, 0.12] m - Axial location
- `vane1FilletCoeff`: {0.0, 0.5, 0.8} - Fillet radius coefficient (discrete)
- `vane1Leg1Length`: [0.01, 0.02] m - First leg length
- `vane1Leg1Angle`: [85, 120]° - First leg angle
- `vane1Leg2Length`: [0.01, 0.02] m - Second leg length
- `vane1Leg2Angle`: [30, 95]° - Second leg angle

### Vane 2 (6 parameters)
- `vane2Position`: [0.086, 0.12] m - Axial location
- `vane2FilletCoeff`: {0.0, 0.5, 0.8} - Fillet radius coefficient (discrete)
- `vane2Leg1Length`: [0.01, 0.02] m - First leg length
- `vane2Leg1Angle`: [175, 220]° - First leg angle
- `vane2Leg2Length`: [0.01, 0.02] m - Second leg length
- `vane2Leg2Angle`: [150, 185]° - Second leg angle

**Total**: 17 continuous + 2 discrete (ordered categorical) = 19 parameters

## Optimization Configuration

### Objectives

Multi-objective optimization with **3 competing objectives**:

```
minimize:   CH4DomainAvg        (Average CH4 mass fraction in domain)
minimize:   PatternFactor       (Temperature non-uniformity at outlet)
maximize:   TemperatureRise     (T_outlet - T_inlet)
```

**Trade-offs**:
- Lower CH4 = better combustion efficiency (less unburned fuel)
- Lower pattern factor = more uniform temperature distribution (better for turbine durability)
- Higher temperature rise = more energy extraction (conflicting with uniformity)

### Constraints

Outcome constraints ensure designs don't deviate too far from baseline performance:

```
CH4DomainAvg <= 1.1 × baseline
PatternFactor <= 1.1 × baseline
TemperatureRise >= 0.9 × baseline
```

### Metrics

**Primary metrics** (used in objectives/constraints):
- `CH4DomainAvg`: Volume-weighted average CH4 mass fraction (computed via ParaView/Python)
- `PatternFactor`: Outlet temperature non-uniformity metric (computed via ParaView/Python)
- `TemperatureRise`: Bulk temperature increase from inlet to outlet (computed via ParaView/Python)

**Progress metric** (for early stopping):
- `ContinuityErrors`: Cumulative mass conservation error (extracted from solver log)

### Baseline Design

Reference geometry parameters defined in `MOO.yaml:76-96`:
```yaml
bevelPosition: 0.1,    bevelAngle: 60°,    outletWidth: 0.08 m
rearBodyLength: 0.02,  rearBodyWidth: 0.042, rearBodyPosition: 0.12, rearBodyAngle: 0°
vane1: pos=0.086, fillet=0.8, L1=0.015@90°, L2=0.015@90°
vane2: pos=0.086, fillet=0.8, L1=0.015@180°, L2=0.015@180°
```

## FoamBO Configuration

### Trial Generation
- **Method**: `fast` - Quick generation of trial parameters using Sobol sequences

### Orchestration
- **Max trials**: 100 simulations
- **Parallelism**: 3 concurrent simulations
- **Timeout**: 48 hours per trial
- **TTL**: 3600 seconds (1 hour) for trial cleanup

### Global Stopping Strategy
Stops optimization when improvement plateaus:
- Minimum trials: 10
- Window size: 5 trials
- Improvement threshold: 10% required across window

### Early Stopping Strategy
Terminates poor-performing trials early to save compute:
- **Type**: Percentile-based
- **Metric**: `ContinuityErrors` (lower is better)
- **Threshold**: Stop trials in bottom 25th percentile
- **Min progression**: Monitor after 5 time steps
- **Ignore first**: 20 trials (to build sufficient data)

### Case Runner
- **Template**: `AVC/` directory
- **Mode**: `local` execution
- **Runner script**: `./Allrun` (see workflow below)
- **Trial destination**: `/tmp/data/trials/` (working directory for each trial)
- **Artifacts**: `./artifacts/` (stores results and visualizations)

### Parameter Injection

Optimization parameters are injected into `system/geometryDict` via variable substitution. For example:
```yaml
bevelPosition → channel.bevel.position
vane1Leg1Angle → vane1.angleLeg1
```

## Workflow

### 1. Preparation
```bash
./prepare.sh
```
Sets up required directories at `/tmp/data` and installs dependencies.

### 2. Optimization Loop

For each trial, FoamBO executes `AVC/Allrun`:

```bash
# 1. Generate parametric geometry
uv run --script /tmp/data/scripts/generate_geometry.py

# 2. Generate 2D Cartesian mesh
cartesian2DMesh

# 3. Quality check
checkMesh

# 4. Prepare initial conditions
restore0Dir

# 5. Convert chemistry mechanism
chemkinToFoam grimech30.dat thermo30.dat transportProperties

# 6. Initialize fields (fuel region + hot cavity)
setFields
decomposePar

# 7. Cold flow test (chemistry OFF, 0-6 ms)
foamDictionary constant/chemistryProperties -entry chemistry -set off
mpirun -np N reactingFoam -parallel

# 8. Hot run (chemistry ON, 6-50 ms)
foamDictionary constant/chemistryProperties -entry chemistry -set on
foamDictionary system/controlDict -entry endTime -set 0.050
mpirun -np N reactingFoam -parallel
```

### 3. Metric Extraction

After simulation, metrics are computed:

**Log-based metrics** (via `scripts/get_metric.sh`):
```bash
./scripts/get_metric.sh . continuity_error_cumulative
```
Extracts cumulative mass conservation error from OpenFOAM log.

**Field-based metrics** (via `scripts/compute_metric.py`):
```bash
pvpython scripts/compute_metric.py . ch4_domain_average
pvpython scripts/compute_metric.py . pattern_factor
pvpython scripts/compute_metric.py . temperature_rise
```
Uses ParaView Python to post-process field data.

### 4. Start Optimization

```bash
uvx foamBO --config MOO.yaml
```

FoamBO will:
1. Generate trial parameters using Bayesian optimization
2. Launch 3 parallel simulations
3. Monitor progress via `ContinuityErrors` metric
4. Stop poor trials early (percentile threshold)
5. Extract final metrics upon completion
6. Update Gaussian Process surrogate model
7. Propose next trial parameters
8. Repeat until global stopping criterion met

### 5. Results

Results stored in:
- `./artifacts/`: Pareto frontier data, convergence plots, sensitivity analysis
- `/tmp/data/trials/trial_XXX/`: Individual simulation directories
- `foamBO.db` (if using database backend): Full optimization history

## Key Features

### Multi-Objective Bayesian Optimization
- **Surrogate model**: Gaussian Process regression for expensive CFD simulations
- **Acquisition function**: Expected Hypervolume Improvement (EHVI) for multi-objective
- **Handles mixed variables**: Continuous (floats), discrete (ints), and categorical (fillet coefficients)

### Intelligent Early Stopping
- Monitors continuity errors during simulation
- Stops simulations predicted to perform poorly (bottom 25%)
- Saves ~75% compute time on bad designs

### Constraint Handling
- Outcome constraints prevent degenerate designs
- Ensures feasibility relative to baseline performance

### Automated Workflow
- Geometry generation from parameters
- Meshing, initialization, solving, post-processing
- Metric extraction and reporting
- Full reproducibility via configuration file
