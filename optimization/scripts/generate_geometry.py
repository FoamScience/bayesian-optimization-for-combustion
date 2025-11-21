#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [ "numpy", "pymadcad>=0.19.1", "foamlib>=1.3.13", "numpy-stl>=3.2.0", "matplotlib>=3.5.0" ]
# ///

# Only import common modules at top level
# Heavy 3D geometry dependencies are imported inside generate_geometry() function
import math
import argparse
import base64
import io
import sys

def generate_2d_image(parametrization, default_config=None):
    """
    Generate a base64-encoded 2D illustration of the geometry wires.

    parametrization is a python dict overriding some default_config values:
        Example:
            bevelPosition: 0.1
            bevelAngle: 60
            outletWidth: 0.08
            rearBodyLength: 0.02
            rearBodyWidth: 0.042
            rearBodyPosition: 0.12
            rearBodyAngle: 0
            vane1Position: 0.086
            vane1FilletCoeff: 0.8
            vane1Leg1Length: 0.015
            vane1Leg1Angle: 90
            vane1Leg2Length: 0.015
            vane1Leg2Angle: 90
            vane2Position: 0.086
            vane2FilletCoeff: 0.8
            vane2Leg1Length: 0.015
            vane2Leg1Angle: 180
            vane2Leg2Length: 0.015
            vane2Leg2Angle: 180

    default_config is the FoamFile of default case dictionary: AVC/system/geometryDict
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Polygon
    import copy
    from foamlib import FoamFile

    # Load default config if not provided
    if default_config is None:
        default_config = FoamFile("AVC/system/geometryDict")

    # Merge parametrization into config
    cfg = copy.deepcopy(default_config)

    # Apply parametrization overrides (map from flat names to nested structure)
    param_map = {
        'bevelPosition': ('channel', 'bevel', 'position'),
        'bevelAngle': ('channel', 'bevel', 'angle'),
        'outletWidth': ('channel', 'outletWidth'),
        'rearBodyLength': ('rearBluntBody', 'length'),
        'rearBodyWidth': ('rearBluntBody', 'width'),
        'rearBodyPosition': ('rearBluntBody', 'positionX'),
        'rearBodyAngle': ('rearBluntBody', 'rotationAngle'),
        'vane1CenterX': ('vane1', 'centerX'),
        'vane1CenterY': ('vane1', 'centerY'),
        'vane1FilletCoeff': ('vane1', 'filetCoeff'),
        'vane1Leg1Length': ('vane1', 'L1'),
        'vane1Leg1Angle': ('vane1', 'angleLeg1'),
        'vane1Leg2Length': ('vane1', 'L2'),
        'vane1Leg2Angle': ('vane1', 'angleLeg2'),
        'vane2CenterX': ('vane2', 'centerX'),
        'vane2CenterY': ('vane2', 'centerY'),
        'vane2FilletCoeff': ('vane2', 'filetCoeff'),
        'vane2Leg1Length': ('vane2', 'L1'),
        'vane2Leg1Angle': ('vane2', 'angleLeg1'),
        'vane2Leg2Length': ('vane2', 'L2'),
        'vane2Leg2Angle': ('vane2', 'angleLeg2'),
    }

    for param_name, nested_keys in param_map.items():
        if param_name in parametrization:
            # Navigate to the nested location and set value
            target = cfg
            for key in nested_keys[:-1]:
                target = target[key]
            target[nested_keys[-1]] = parametrization[param_name]

    # Build geometry wire points (same logic as generate_geometry())
    bevel_pos = cfg["channel"]["bevel"]["position"]
    bevel_theta = cfg["channel"]["bevel"]["angle"]
    out_width = cfg["channel"]["outletWidth"] if bevel_theta >= 1 else cfg["channel"]["inletWidth"]
    bevel_width = (cfg["channel"]["inletWidth"] - out_width) / 2.0 if bevel_theta >= 1 else 0

    # Channel outline points
    channel1 = (0, 0)
    channel2 = (bevel_pos, 0)
    channel3 = (bevel_pos + bevel_width / math.tan(math.radians(bevel_theta)) if bevel_theta >= 1 else bevel_pos, bevel_width)
    channel4 = (cfg["channel"]["length"], channel3[1])
    channel5 = (channel4[0], channel4[1] + out_width)
    channel6 = (channel3[0], channel3[1] + out_width)
    channel7 = (channel2[0], cfg["channel"]["inletWidth"])
    channel8 = (channel1[0], cfg["channel"]["inletWidth"])
    channel9 = (channel8[0], channel8[1] - (cfg["channel"]["inletWidth"] - cfg["frontBluntBody"]["width"]) / 2.0)
    channel10 = (channel9[0] + cfg["frontBluntBody"]["length"], channel9[1])
    channel11 = (channel10[0], channel10[1] - cfg["frontBluntBody"]["width"])
    channel12 = (channel11[0] - cfg["frontBluntBody"]["length"], channel11[1])

    # Rear blunt body points
    rear_blunt_body_posY = (cfg["channel"]["inletWidth"] - cfg["rearBluntBody"]["width"]) / 2.0
    channel13 = (cfg["rearBluntBody"]["positionX"], rear_blunt_body_posY)
    channel14 = (channel13[0] + cfg["rearBluntBody"]["length"], channel13[1])
    channel15 = (channel14[0], channel14[1] + cfg["rearBluntBody"]["width"])
    channel16 = (channel13[0], channel13[1] + cfg["rearBluntBody"]["width"])

    # Apply rotation to rear body if needed
    rear_angle_rad = math.radians(cfg["rearBluntBody"]["rotationAngle"])
    if abs(rear_angle_rad) > 1e-9:
        # Rotate around center
        center_x = (channel13[0] + channel14[0] + channel15[0] + channel16[0]) / 4.0
        center_y = (channel13[1] + channel14[1] + channel15[1] + channel16[1]) / 4.0

        def rotate_point(pt, cx, cy, angle):
            dx = pt[0] - cx
            dy = pt[1] - cy
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)

        channel13 = rotate_point(channel13, center_x, center_y, rear_angle_rad)
        channel14 = rotate_point(channel14, center_x, center_y, rear_angle_rad)
        channel15 = rotate_point(channel15, center_x, center_y, rear_angle_rad)
        channel16 = rotate_point(channel16, center_x, center_y, rear_angle_rad)

    # Create vane shapes
    def create_vane_2d(vane_cfg):
        thickness = vane_cfg["thickness"]
        l1 = vane_cfg["L1"]
        l2 = vane_cfg["L2"]
        angle1_rad = math.radians(vane_cfg["angleLeg1"])
        angle2_rad = math.radians(vane_cfg["angleLeg2"])
        cx = vane_cfg["centerX"]
        cy = vane_cfg["centerY"]

        # Apply 2D rotation around Z axis (matches madcad rotatearound)
        # For vec3(x, y, 0) rotated by θ around Z: (x*cos(θ) - y*sin(θ), x*sin(θ) + y*cos(θ))
        cos1, sin1 = math.cos(angle1_rad), math.sin(angle1_rad)
        cos2, sin2 = math.cos(angle2_rad), math.sin(angle2_rad)

        # Leg 1: [O, r1*vec3(0,l1,0), r1*vec3(thickness,l1,0)]
        leg1_p1 = (0, 0)
        leg1_p2 = (0*cos1 - l1*sin1, 0*sin1 + l1*cos1)  # = (-l1*sin1, l1*cos1)
        leg1_p3 = (thickness*cos1 - l1*sin1, thickness*sin1 + l1*cos1)

        # Leg 2: [r2*vec3(l2,thickness,0), r2*vec3(l2,0,0)]
        leg2_p1 = (l2*cos2 - thickness*sin2, l2*sin2 + thickness*cos2)
        leg2_p2 = (l2*cos2 - 0*sin2, l2*sin2 + 0*cos2)  # = (l2*cos2, l2*sin2)

        # Create vane polygon (simplified - no filet intersection calculation for 2D)
        vane_points = [
            (cx + leg1_p1[0], cy + leg1_p1[1]),
            (cx + leg1_p2[0], cy + leg1_p2[1]),
            (cx + leg1_p3[0], cy + leg1_p3[1]),
            (cx + leg2_p1[0], cy + leg2_p1[1]),
            (cx + leg2_p2[0], cy + leg2_p2[1]),
        ]
        return vane_points

    vane1_points = create_vane_2d(cfg["vane1"])
    vane2_points = create_vane_2d(cfg["vane2"])

    # Create matplotlib figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    # Plot channel outline
    channel_outer = [channel1, channel2, channel3, channel4, channel5, channel6, channel7, channel8, channel1]
    xs, ys = zip(*channel_outer)
    ax.plot(xs, ys, 'k-', linewidth=2, label='Channel walls')

    # Plot front blunt body
    front_body = [channel9, channel10, channel11, channel12, channel9]
    xs, ys = zip(*front_body)
    ax.fill(xs, ys, color='gray', alpha=0.5, edgecolor='black', linewidth=1.5, label='Front body')

    # Plot rear blunt body
    rear_body = [channel13, channel14, channel15, channel16, channel13]
    xs, ys = zip(*rear_body)
    ax.fill(xs, ys, color='lightblue', alpha=0.5, edgecolor='blue', linewidth=1.5, label='Rear body')

    # Plot vanes
    vane1_closed = vane1_points + [vane1_points[0]]
    xs, ys = zip(*vane1_closed)
    ax.fill(xs, ys, color='orange', alpha=0.5, edgecolor='darkorange', linewidth=1.5, label='Vane 1')

    vane2_closed = vane2_points + [vane2_points[0]]
    xs, ys = zip(*vane2_closed)
    ax.fill(xs, ys, color='green', alpha=0.5, edgecolor='darkgreen', linewidth=1.5, label='Vane 2')

    # Mark inlet regions
    ax.plot([channel8[0], channel9[0]], [channel8[1], channel9[1]], 'b-', linewidth=3, label='Air inlet')
    ax.plot([channel12[0], channel1[0]], [channel12[1], channel1[1]], 'r-', linewidth=3, label='Fuel inlet')

    # Mark outlet
    ax.plot([channel4[0], channel5[0]], [channel4[1], channel5[1]], 'g-', linewidth=3, label='Outlet')

    # Formatting
    ax.set_aspect('equal')
    ax.set_xlabel('X (m)', fontsize=12)
    ax.set_ylabel('Y (m)', fontsize=12)
    ax.set_title('AVC Geometry - 2D Cross-section', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)

    # Set axis limits with some padding
    ax.set_xlim(-0.01, cfg["channel"]["length"] + 0.01)
    ax.set_ylim(-0.01, cfg["channel"]["inletWidth"] + 0.01)

    # Convert to base64
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    return img_base64

def generate_geometry():
    """Generate the 3D STL geometry files."""
    # Import 3D geometry dependencies
    from madcad import (
        brick, difference, transform,
        flatsurface, rotatearound, extrusion, union,
        wire, Wire, Segment, web, filet, translate,
        O, X, Y, Z, vec3
    )
    from madcad.boolean import boolean
    from madcad.io import write
    from stl import Mode

    extrude_dir = 2e-3*Z

    channel1 = O
    bevel_pos = config["channel"]["bevel"]["position"]
    channel2 = vec3(bevel_pos, 0, 0)
    bevel_theta = config["channel"]["bevel"]["angle"]
    out_width = config["channel"]["outletWidth"] if bevel_theta >= 1 else config["channel"]["inletWidth"]
    bevel_width = (config["channel"]["inletWidth"] - out_width)/2.0 if bevel_theta >= 1 else 0
    channel3 = vec3(bevel_pos+bevel_width/math.tan(math.radians(bevel_theta)) if bevel_theta >= 1 else bevel_pos, bevel_width, 0)
    channel4 = vec3(config["channel"]["length"], channel3[1], 0)
    channel5 = channel4 + vec3(0, out_width, 0)
    channel6 = channel3 + vec3(0, out_width, 0)
    channel7 = channel2 + vec3(0, config["channel"]["inletWidth"], 0)
    channel8 = channel1 + vec3(0, config["channel"]["inletWidth"], 0)
    channel9 = channel8 - vec3(0, (config["channel"]["inletWidth"]-config["frontBluntBody"]["width"])/2.0, 0)
    channel10 = channel9 + vec3(config["frontBluntBody"]["length"], 0, 0)
    channel11 = channel10 - vec3(0, config["frontBluntBody"]["width"], 0)
    channel12 = channel11 - vec3(config["frontBluntBody"]["length"], 0, 0)

    base_outline = web(Wire(points=[channel1, channel2, channel3, channel4,
                        channel5, channel6, channel7, channel8,
                        channel9, channel10, channel11, channel12]).close().segmented())

    walls_1 = web(Wire(points=[channel1, channel2, channel3, channel4]))
    walls_2 = web(Wire(points=[channel5, channel6, channel7, channel8]))
    walls_mesh = union(extrusion(walls_1, extrude_dir), extrusion(walls_2, extrude_dir))
    write(mesh=walls_mesh, name="walls", type="stl", mode=Mode.ASCII)

    inlet1 = web(Wire(points=[channel8, channel9]))
    inlet2 = web(Wire(points=[channel12, channel1]))
    inlet1_mesh = extrusion(inlet1, extrude_dir)
    inlet2_mesh = extrusion(inlet2, extrude_dir)
    write(mesh=inlet1_mesh, name="inletAir", type="stl", mode=Mode.ASCII)
    write(mesh=inlet2_mesh, name="inletFuel", type="stl", mode=Mode.ASCII)

    outlet = web(Wire(points=[channel4, channel5]))
    outlet_mesh = extrusion(outlet, extrude_dir)
    write(mesh=outlet_mesh, name="outlet", type="stl", mode=Mode.ASCII)

    front_body = web(Wire(points=[channel9, channel10, channel11, channel12]))
    front_body_mesh = extrusion(front_body, extrude_dir)
    write(mesh=front_body_mesh, name="frontBody", type="stl", mode=Mode.ASCII)

    rear_blunt_body_posY = (config["channel"]["inletWidth"]-config["rearBluntBody"]["width"])/2.0

    channel13 = vec3(config["rearBluntBody"]["positionX"], rear_blunt_body_posY, 0)
    channel14 = channel13 + vec3(config["rearBluntBody"]["length"], 0, 0)
    channel15 = channel14 + vec3(0, config["rearBluntBody"]["width"], 0)
    channel16 = channel13 + vec3(0, config["rearBluntBody"]["width"], 0)
    rear_rotation = rotatearound(config["rearBluntBody"]["rotationAngle"], (channel13+channel14+channel15+channel16)/4.0, Z)

    # rear_body_length < outlet width if its its x > channel3.x
    # rear_body_length < inlet width - 2*(config["rearBluntBody"]["positionX"]-bevel_pos)*tan(theta) if its config["rearBluntBody"]["positionX"] < x < channel3.x
    # rear_body_length < inlet width if its x <= config["rearBluntBody"]["positionX"]

    rear_body = web(Wire(points=[channel13, channel14, channel15, channel16]).close().segmented())
    rear_body_mesh = extrusion(rear_body, extrude_dir).transform(rear_rotation)
    write(mesh=rear_body_mesh, name="rearBody", type="stl", mode=Mode.ASCII)

    vane1C = vec3(config["vane1"]["centerX"], config["vane1"]["centerY"], 0)

    def create_vane(vane_config):
        thickness = vane_config["thickness"]
        l1 = vane_config["L1"]
        r1 = rotatearound(math.radians(vane_config["angleLeg1"]), O, Z)
        l2 = vane_config["L2"]
        r2 = rotatearound(math.radians(vane_config["angleLeg2"]), O, Z)
        leg1 = [O, r1 * vec3(0, l1, 0), r1 * vec3(thickness, l1, 0)]
        leg2 = [r2 * vec3(l2, thickness, 0), r2 * vec3(l2, 0, 0)]
        v1 = leg1[1] - leg1[0]       # direction of first leg's top edge
        p1 = leg1[2]
        v2 = leg2[1] - leg1[0]       # direction of second leg's top edge
        p2 = leg2[0]
        D = v1[0] * v2[1] - v1[1] * v2[0]
        if abs(D) < 1e-9:  # handle floating-point safely
            print("Couldn't create the vane shape; problem with angles?")
            return None
        t = (v2[1] * (p2[0] - p1[0]) - v2[0] * (p2[1] - p1[1])) / D
        intersection = p1 + t * v1
        section = wire(leg1 + [intersection] + leg2).close().segmented().flip()
        if vane_config["filetCoeff"] != 0.0:
            filet(section, [2, 3, 4], radius=thickness * vane_config["filetCoeff"], resolution=('div', 16))
        section.finish()
        origin = vec3(vane_config["centerX"], vane_config["centerY"],0)
        return extrusion(section, extrude_dir).transform(translate(origin))

    guide_vane1_mesh = create_vane(config["vane1"])
    guide_vane2_mesh = create_vane(config["vane2"])

    write(mesh=guide_vane1_mesh, name="vane1", type="stl", mode=Mode.ASCII)
    write(mesh=guide_vane2_mesh, name="vane2", type="stl", mode=Mode.ASCII)

    def concat_and_remove(input_paths, out_path):
        import os, tempfile, shutil
        input_paths = [p for p in input_paths if p]
        if not input_paths:
            raise ValueError("No input files provided")
        dir_out = os.path.dirname(os.path.abspath(out_path)) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_out, prefix=".tmp_concat_", suffix=".stl")
        os.close(fd)
        try:
            with open(tmp_path, "wb") as wfd:
                for p in input_paths:
                    with open(p, "rb") as rfd:
                        shutil.copyfileobj(rfd, wfd)
            shutil.move(tmp_path, out_path)
            for p in input_paths:
                try:
                    os.remove(p)
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f"Warning: couldn't remove {p}: {e}", file=sys.stderr)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    concat_and_remove(["walls", "outlet", "inletAir", "inletFuel", "frontBody", "rearBody", "vane1", "vane2"], "avc.stl")

config = None

if __name__ == "__main__":
    from foamlib import FoamFile

    parser = argparse.ArgumentParser(
        description="Generate geometry for combustion optimization case"
    )
    parser.add_argument(
        "--geometry",
        action="store_true",
        help="Generate 3D STL geometry files (default behavior)"
    )
    parser.add_argument(
        "--image",
        action="store_true",
        help="Generate base64-encoded 2D illustration of the geometry"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="system/geometryDict",
        help="Path to the input geometry dictionary file (default: geometryDict)"
    )

    args = parser.parse_args()

    # Load configuration from specified input file
    config = FoamFile(args.input)

    # Default to geometry generation if no arguments provided
    if not args.geometry and not args.image:
        args.geometry = True

    if args.image:
        img_base64 = generate_2d_image({})

    if args.geometry:
        generate_geometry()
