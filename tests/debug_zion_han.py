"""
Debug Zion Han DXF outline issue - E letters filled
"""

import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.dxf_parser import DXFParser
from src.core.path_offset import PathOffset
from src.core.types import EdgeDirection


def analyze_zion_han():
    """Analyze Zion Han DXF structure"""
    print("=" * 60)
    print("Analyzing Zion Han DXF")
    print("=" * 60)

    dxf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "Zion Han.dxf")

    if not os.path.exists(dxf_path):
        print(f"DXF file not found: {dxf_path}")
        return

    parser = DXFParser()
    contours = parser.parse(dxf_path)

    print(f"\nTotal contours: {len(contours)}")

    for i, contour in enumerate(contours):
        print(f"\n--- Contour {i} ---")
        print(f"  Outer points: {len(contour.outer.points)}")
        print(f"  Holes: {len(contour.holes)}")

        # Get bounds
        bounds = contour.outer.bounds
        print(f"  Bounds: X[{bounds[0]:.2f}, {bounds[2]:.2f}] Y[{bounds[1]:.2f}, {bounds[3]:.2f}]")

        # List holes
        for j, hole in enumerate(contour.holes):
            hole_bounds = hole.bounds
            print(f"    Hole {j}: {len(hole.points)} points, bounds X[{hole_bounds[0]:.2f}, {hole_bounds[2]:.2f}] Y[{hole_bounds[1]:.2f}, {hole_bounds[3]:.2f}]")


def test_hole_outline():
    """Test hole outline generation"""
    print("\n" + "=" * 60)
    print("Testing Hole Outline Generation")
    print("=" * 60)

    dxf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "Zion Han.dxf")

    if not os.path.exists(dxf_path):
        print(f"DXF file not found: {dxf_path}")
        return

    parser = DXFParser()
    contours = parser.parse(dxf_path)

    path_offset = PathOffset()
    wall_thickness = 1.2
    outline_width = 3.0
    outline_offset = 0.0

    # Find contours with holes (likely the E letters)
    for i, contour in enumerate(contours):
        if contour.holes:
            print(f"\n--- Contour {i} with {len(contour.holes)} holes ---")

            for j, hole in enumerate(contour.holes):
                print(f"\n  Hole {j}:")
                print(f"    Points: {len(hole.points)}")

                # Test OUTER direction offsets for holes
                # 外部勾边：从内孔外壁向字壳内部延伸
                hole_offset_bottom = -(outline_offset + outline_width)  # -3.0
                hole_offset_top = -outline_offset  # 0.0

                print(f"    OUTER direction:")
                print(f"      offset_bottom = {hole_offset_bottom}")
                print(f"      offset_top = {hole_offset_top}")

                # Test offset
                if abs(hole_offset_bottom) > 0.001:
                    result = path_offset.offset(hole, hole_offset_bottom)
                    if result:
                        print(f"      Bottom offset result: {len(result)} contour(s)")
                        for k, r in enumerate(result):
                            print(f"        Result {k}: {len(r.points)} points")
                    else:
                        print(f"      Bottom offset FAILED")

                # Test INNER direction offsets for holes
                # 内孔内部勾边：从内孔内壁向孔内延伸
                hole_offset_bottom_inner = wall_thickness + outline_offset + outline_width  # 4.2
                hole_offset_top_inner = wall_thickness + outline_offset  # 1.2

                print(f"    INNER direction:")
                print(f"      offset_bottom = {hole_offset_bottom_inner}")
                print(f"      offset_top = {hole_offset_top_inner}")

                if abs(hole_offset_bottom_inner) > 0.001:
                    result = path_offset.offset(hole, hole_offset_bottom_inner)
                    if result:
                        print(f"      Bottom offset result: {len(result)} contour(s)")
                    else:
                        print(f"      Bottom offset FAILED (hole too small)")


if __name__ == "__main__":
    analyze_zion_han()
    test_hole_outline()
