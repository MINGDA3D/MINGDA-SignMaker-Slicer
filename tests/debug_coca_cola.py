"""
Debug script to analyze the Coca-Cola DXF outline issue
"""

import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.dxf_parser import DXFParser
from src.core.path_offset import PathOffset
from src.core.types import Path as CorePath, Point, EdgeDirection

def analyze_contours():
    """Analyze the Coca-Cola DXF contours"""
    print("=" * 60)
    print("Analyzing Coca-Cola DXF")
    print("=" * 60)

    dxf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "可口可乐.dxf")

    if not os.path.exists(dxf_path):
        print(f"DXF file not found: {dxf_path}")
        return

    parser = DXFParser()
    contours = parser.parse(dxf_path)

    print(f"\nTotal contours: {len(contours)}")

    path_offset = PathOffset()

    for i, contour in enumerate(contours):
        print(f"\n--- Contour {i} ---")
        print(f"  Outer points: {len(contour.outer.points)}")
        print(f"  Holes: {len(contour.holes)}")

        # Get bounds
        bounds = contour.outer.bounds
        print(f"  Bounds: X[{bounds[0]:.2f}, {bounds[2]:.2f}] Y[{bounds[1]:.2f}, {bounds[3]:.2f}]")

        # Test offset operations (like outline does)
        wall_thickness = 1.2
        outline_width = 3.0
        outline_offset = 0.0

        # For outer outline (external direction)
        offset_bottom = outline_offset + outline_width  # 3.0
        offset_top = outline_offset  # 0.0

        print(f"\n  Testing offset operations:")
        print(f"    offset_bottom = {offset_bottom}")
        print(f"    offset_top = {offset_top}")

        # Offset for bottom edge
        if abs(offset_bottom) > 0.001:
            bottom_results = path_offset.offset(contour.outer, offset_bottom)
            if bottom_results:
                print(f"    Bottom offset: {len(bottom_results)} result(s)")
                for j, r in enumerate(bottom_results):
                    print(f"      Result {j}: {len(r.points)} points")
            else:
                print(f"    Bottom offset: FAILED (no results)")

        # Offset for top edge
        if abs(offset_top) > 0.001:
            top_results = path_offset.offset(contour.outer, offset_top)
            if top_results:
                print(f"    Top offset: {len(top_results)} result(s)")
            else:
                print(f"    Top offset: FAILED")
        else:
            print(f"    Top offset: No offset needed (0.0)")

        # Check for inner direction
        print(f"\n  Testing inner direction:")
        inner_offset_bottom = -(wall_thickness + outline_offset + outline_width)  # -4.2
        inner_offset_top = -(wall_thickness + outline_offset)  # -1.2

        print(f"    inner_offset_bottom = {inner_offset_bottom}")
        print(f"    inner_offset_top = {inner_offset_top}")

        inner_bottom_results = path_offset.offset(contour.outer, inner_offset_bottom)
        if inner_bottom_results:
            print(f"    Inner bottom offset: {len(inner_bottom_results)} result(s)")
            for j, r in enumerate(inner_bottom_results):
                print(f"      Result {j}: {len(r.points)} points")
        else:
            print(f"    Inner bottom offset: FAILED (contour may collapse)")


def test_ruled_surface_issue():
    """Test what happens with ruled surface on complex contours"""
    print("\n" + "=" * 60)
    print("Testing ruled surface generation")
    print("=" * 60)

    dxf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "可口可乐.dxf")

    if not os.path.exists(dxf_path):
        print(f"DXF file not found: {dxf_path}")
        return

    parser = DXFParser()
    contours = parser.parse(dxf_path)
    path_offset = PathOffset()

    from src.core.stl_writer import STLWriter
    writer = STLWriter(wall_thickness=1.2)

    # Test each contour separately
    for i, contour in enumerate(contours):
        print(f"\n--- Testing Contour {i} ---")

        # Parameters
        outline_width = 3.0
        outline_offset = 0.0
        offset_bottom = outline_offset + outline_width
        offset_top = outline_offset

        # Get bottom coords
        if abs(offset_bottom) < 0.001:
            bottom_outer_coords = [(p.x, p.y) for p in contour.outer.points]
        else:
            bottom_results = path_offset.offset(contour.outer, offset_bottom)
            if not bottom_results:
                print(f"  SKIP: Bottom offset failed")
                continue
            bottom_outer_coords = [(p.x, p.y) for p in bottom_results[0].points]

        # Get top coords (wall edge)
        if abs(offset_top) < 0.001:
            wall_edge_coords = [(p.x, p.y) for p in contour.outer.points]
        else:
            top_results = path_offset.offset(contour.outer, offset_top)
            if not top_results:
                print(f"  SKIP: Top offset failed")
                continue
            wall_edge_coords = [(p.x, p.y) for p in top_results[0].points]

        print(f"  Bottom coords: {len(bottom_outer_coords)} points")
        print(f"  Wall edge coords: {len(wall_edge_coords)} points")

        # Check if point counts differ significantly
        diff = abs(len(bottom_outer_coords) - len(wall_edge_coords))
        print(f"  Point count difference: {diff}")

        if diff > 10:
            print(f"  WARNING: Large point count difference may cause issues!")

        # Check arc lengths
        import math
        def calc_arc_length(coords):
            total = 0
            for j in range(len(coords)):
                k = (j + 1) % len(coords)
                dx = coords[k][0] - coords[j][0]
                dy = coords[k][1] - coords[j][1]
                total += math.sqrt(dx*dx + dy*dy)
            return total

        arc1 = calc_arc_length(bottom_outer_coords)
        arc2 = calc_arc_length(wall_edge_coords)
        print(f"  Bottom arc length: {arc1:.2f}")
        print(f"  Wall arc length: {arc2:.2f}")
        print(f"  Arc length ratio: {arc1/arc2:.4f}" if arc2 > 0 else "  Arc length ratio: N/A")


def compare_wrap_vs_outline():
    """Compare edge wrap (working) vs outline (broken) to find the difference"""
    print("\n" + "=" * 60)
    print("Comparing Edge Wrap vs Outline")
    print("=" * 60)

    dxf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "可口可乐.dxf")

    if not os.path.exists(dxf_path):
        print(f"DXF file not found: {dxf_path}")
        return

    parser = DXFParser()
    contours = parser.parse(dxf_path)
    path_offset = PathOffset()

    from shapely.geometry import Polygon as ShapelyPolygon
    from shapely.validation import make_valid

    for i, contour in enumerate(contours):
        print(f"\n--- Contour {i} ---")

        outer_points = contour.outer.points
        wrap_width = 3.0

        # Edge wrap approach (working)
        print("\n  [Edge Wrap Approach]")
        inner_ring_coords = [(p.x, p.y) for p in outer_points]
        if inner_ring_coords[0] != inner_ring_coords[-1]:
            inner_ring_coords.append(inner_ring_coords[0])

        outer_edge_results = path_offset.offset(contour.outer, wrap_width)
        if outer_edge_results:
            outer_ring_coords = [(p.x, p.y) for p in outer_edge_results[0].points]
            if outer_ring_coords[0] != outer_ring_coords[-1]:
                outer_ring_coords.append(outer_ring_coords[0])

            try:
                wrap_polygon = ShapelyPolygon(outer_ring_coords, [inner_ring_coords])
                if not wrap_polygon.is_valid:
                    wrap_polygon = make_valid(wrap_polygon)

                print(f"    Polygon valid: {wrap_polygon.is_valid}")
                print(f"    Polygon area: {wrap_polygon.area:.2f}")
                print(f"    Polygon type: {wrap_polygon.geom_type}")

                if wrap_polygon.geom_type == 'MultiPolygon':
                    print(f"    MultiPolygon parts: {len(wrap_polygon.geoms)}")

            except Exception as e:
                print(f"    Error: {e}")
        else:
            print(f"    Offset failed!")

        # Outline approach (broken)
        print("\n  [Outline Approach]")
        outline_width = 3.0
        offset_bottom = outline_width  # 3.0 (outer)
        offset_top = 0.0  # wall edge

        # Bottom outer coords
        bottom_results = path_offset.offset(contour.outer, offset_bottom)
        if bottom_results:
            bottom_outer_coords = [(p.x, p.y) for p in bottom_results[0].points]
            if bottom_outer_coords[0] != bottom_outer_coords[-1]:
                bottom_outer_coords.append(bottom_outer_coords[0])
        else:
            print(f"    Bottom offset failed!")
            continue

        # Wall edge coords (no offset)
        wall_edge_coords = [(p.x, p.y) for p in outer_points]
        if wall_edge_coords[0] != wall_edge_coords[-1]:
            wall_edge_coords.append(wall_edge_coords[0])

        print(f"    Bottom coords: {len(bottom_outer_coords)}")
        print(f"    Wall coords: {len(wall_edge_coords)}")

        # Create bottom polygon (same as edge wrap)
        try:
            bottom_polygon = ShapelyPolygon(bottom_outer_coords, [wall_edge_coords])
            if not bottom_polygon.is_valid:
                bottom_polygon = make_valid(bottom_polygon)

            print(f"    Bottom polygon valid: {bottom_polygon.is_valid}")
            print(f"    Bottom polygon area: {bottom_polygon.area:.2f}")
            print(f"    Bottom polygon type: {bottom_polygon.geom_type}")

            if bottom_polygon.geom_type == 'MultiPolygon':
                print(f"    MultiPolygon parts: {len(bottom_polygon.geoms)}")
                for j, geom in enumerate(bottom_polygon.geoms):
                    print(f"      Part {j}: area={geom.area:.2f}")

        except Exception as e:
            print(f"    Error: {e}")


if __name__ == "__main__":
    analyze_contours()
    test_ruled_surface_issue()
    compare_wrap_vs_outline()
