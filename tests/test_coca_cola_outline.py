"""
Test outline generation with Coca-Cola DXF
"""

import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.dxf_parser import DXFParser
from src.core.slice_engine import SliceEngine
from src.core.stl_writer import STLWriter
from src.core.types import (
    SliceParams, ShellParams, EdgeWrapParams, EdgeDirection,
    SliceResult, Layer, LayerPath, PathRole, ExtruderType
)


def test_coca_cola_outline():
    """Test outline generation with Coca-Cola DXF"""
    print("=" * 60)
    print("Testing Coca-Cola Outline Generation")
    print("=" * 60)

    dxf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "可口可乐.dxf")

    if not os.path.exists(dxf_path):
        print(f"DXF file not found: {dxf_path}")
        return False

    # Parse DXF
    parser = DXFParser()
    contours = parser.parse(dxf_path)
    print(f"Loaded {len(contours)} contours from DXF")

    # Create slice result
    total_height = 30.0
    layer_height = 0.3
    num_layers = int(total_height / layer_height)

    layers = []
    for i in range(num_layers):
        layer = Layer(
            z_height=i * layer_height,
            layer_height=layer_height,
            extruder=ExtruderType.EXTRUDER_1
        )

        for contour in contours:
            layer_path = LayerPath(
                points=contour.outer.points,
                role=PathRole.WALL,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=1.2,
                is_closed=True
            )
            layer.paths.append(layer_path)

        layers.append(layer)

    result = SliceResult(
        layers=layers,
        total_layers=num_layers,
        total_height=total_height
    )

    # Create parameters with outline enabled
    params = SliceParams()
    params.shell = ShellParams(
        height=total_height,
        layer_height=layer_height,
        wall_thickness=1.2
    )
    params.edge_wrap = EdgeWrapParams(
        outline_enabled=True,
        outline_width=3.0,
        outline_height=3.0,
        outline_offset=0.0,
        outline_direction=EdgeDirection.OUTER
    )

    # Create STL writer
    writer = STLWriter(wall_thickness=1.2)

    # Test outline mesh generation
    print("\nGenerating outline mesh...")
    try:
        outline_mesh = writer._build_outline_mesh(contours, result, params)

        if outline_mesh is not None:
            print(f"SUCCESS: Outline mesh generated!")
            print(f"  - Vertices: {len(outline_mesh.vertices)}")
            print(f"  - Faces: {len(outline_mesh.faces)}")

            # Check for geometry issues
            bounds = outline_mesh.bounds
            print(f"  - Bounds: X[{bounds[0][0]:.2f}, {bounds[1][0]:.2f}]")
            print(f"           Y[{bounds[0][1]:.2f}, {bounds[1][1]:.2f}]")
            print(f"           Z[{bounds[0][2]:.2f}, {bounds[1][2]:.2f}]")

            # Check face area distribution
            face_areas = outline_mesh.area_faces
            if len(face_areas) > 0:
                max_area = max(face_areas)
                avg_area = sum(face_areas) / len(face_areas)
                print(f"  - Max face area: {max_area:.4f}")
                print(f"  - Avg face area: {avg_area:.4f}")
                print(f"  - Ratio: {max_area/avg_area:.2f}")

                # Check for abnormally large faces
                if max_area > 1000:
                    print(f"  WARNING: Very large faces detected! May have geometry errors.")
                    return False
                elif max_area > 200 * avg_area:
                    print(f"  WARNING: Face area ratio too high! May have geometry errors.")
                    return False
                else:
                    print(f"  OK: Face area distribution looks normal")

            return True
        else:
            print("FAILED: Outline mesh is None")
            return False

    except Exception as e:
        print(f"FAILED: Exception during outline generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coca_cola_full_export():
    """Test full STL export with Coca-Cola DXF"""
    print("\n" + "=" * 60)
    print("Testing Full STL Export")
    print("=" * 60)

    dxf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "可口可乐.dxf")

    if not os.path.exists(dxf_path):
        print(f"DXF file not found: {dxf_path}")
        return False

    # Parse DXF
    parser = DXFParser()
    contours = parser.parse(dxf_path)

    # Create slice result
    total_height = 30.0
    layer_height = 0.3
    num_layers = int(total_height / layer_height)

    layers = []
    for i in range(num_layers):
        layer = Layer(
            z_height=i * layer_height,
            layer_height=layer_height,
            extruder=ExtruderType.EXTRUDER_1
        )

        for contour in contours:
            layer_path = LayerPath(
                points=contour.outer.points,
                role=PathRole.WALL,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=1.2,
                is_closed=True
            )
            layer.paths.append(layer_path)

        layers.append(layer)

    result = SliceResult(
        layers=layers,
        total_layers=num_layers,
        total_height=total_height
    )

    # Create parameters
    params = SliceParams()
    params.shell = ShellParams(
        height=total_height,
        layer_height=layer_height,
        wall_thickness=1.2
    )
    params.edge_wrap = EdgeWrapParams(
        outline_enabled=True,
        outline_width=3.0,
        outline_height=3.0,
        outline_offset=0.0,
        outline_direction=EdgeDirection.OUTER
    )

    # Export STL
    output_path = os.path.join(os.path.dirname(__file__), "coca_cola_outline_test.stl")
    writer = STLWriter(wall_thickness=1.2)

    try:
        writer.write(result, output_path, binary=True, contours=contours, params=params)

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"SUCCESS: STL file exported!")
            print(f"  - Path: {output_path}")
            print(f"  - Size: {file_size / 1024:.2f} KB")

            # Keep file for inspection
            print(f"  - File kept for inspection")
            return True
        else:
            print("FAILED: STL file not created")
            return False

    except Exception as e:
        print(f"FAILED: Exception during export: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = []

    results.append(("Outline mesh generation", test_coca_cola_outline()))
    results.append(("Full STL export", test_coca_cola_full_export()))

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    print("=" * 60)
