"""Tests for baseplate/panel DXF export contours."""

import os
import sys
import tempfile

import ezdxf

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.dxf_writer import DXFWriter, export_baseplate_dxf, export_panel_dxf
from src.core.types import (
    BevelDirection,
    Contour,
    EdgeType,
    Path,
    Point,
    SliceParams,
)


def create_test_contour():
    """Create a simple rectangle contour with one hole."""
    outer = Path(
        points=[
            Point(0, 0),
            Point(100, 0),
            Point(100, 100),
            Point(0, 100),
        ],
        is_closed=True,
    )
    hole = Path(
        points=[
            Point(35, 35),
            Point(65, 35),
            Point(65, 65),
            Point(35, 65),
        ],
        is_closed=True,
    )
    return Contour(outer=outer, holes=[hole], name="Test contour")


def assert_bounds(path, expected_bounds, tolerance=1e-3):
    """Assert path bounds with tolerance."""
    actual = path.bounds
    for actual_value, expected_value in zip(actual, expected_bounds):
        assert abs(actual_value - expected_value) <= tolerance, (
            f"Expected bounds {expected_bounds}, got {actual}"
        )


def read_lwpolyline_bounds(file_path):
    """Read all LWPolyline bounds from a DXF file."""
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
    bounds = []

    for entity in msp:
        if entity.dxftype() != "LWPOLYLINE":
            continue
        points = [(point[0], point[1]) for point in entity.get_points()]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        bounds.append((min(xs), min(ys), max(xs), max(ys)))

    return sorted(bounds)


def test_baseplate_contour_uses_inner_wall_and_default_extra_shrink():
    """Baseplate DXF should use z=0 inner-wall seat contour, then apply 1mm tolerance."""
    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.STRAIGHT
    params.shell.wall_thickness = 1.2

    writer = DXFWriter()
    baseplate_contours = writer._get_baseplate_contours([contour], params)

    assert len(baseplate_contours) == 1
    assert_bounds(baseplate_contours[0].outer, (1.2, 1.2, 98.8, 98.8))
    assert len(baseplate_contours[0].holes) == 1
    assert_bounds(baseplate_contours[0].holes[0], (33.8, 33.8, 66.2, 66.2))

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        output_path = f.name

    try:
        success = export_baseplate_dxf([contour], output_path, params)
        assert success is True
        bounds = read_lwpolyline_bounds(output_path)
        assert bounds == [(2.2, 2.2, 97.8, 97.8), (32.8, 32.8, 67.2, 67.2)]
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_panel_contour_uses_top_inner_wall_and_default_extra_shrink():
    """Panel DXF should use top inner-wall seat contour, then apply 1mm tolerance."""
    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.STRAIGHT
    params.shell.height = 30.0
    params.shell.wall_thickness = 1.2

    writer = DXFWriter()
    panel_contours = writer._get_panel_contours([contour], params)

    assert len(panel_contours) == 1
    assert_bounds(panel_contours[0].outer, (1.2, 1.2, 98.8, 98.8))
    assert len(panel_contours[0].holes) == 1
    assert_bounds(panel_contours[0].holes[0], (33.8, 33.8, 66.2, 66.2))

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        output_path = f.name

    try:
        success = export_panel_dxf([contour], output_path, params)
        assert success is True
        bounds = read_lwpolyline_bounds(output_path)
        assert bounds == [(2.2, 2.2, 97.8, 97.8), (32.8, 32.8, 67.2, 67.2)]
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_panel_beveled_export_scales_holes_in_same_direction():
    """Top-small beveled panel export should use top contour, then include wall thickness seat."""
    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_SMALL
    params.shell.bevel_width = 5.0
    params.shell.height = 30.0
    params.shell.wall_thickness = 1.2
    writer = DXFWriter()
    panel_contours = writer._get_panel_contours([contour], params)

    assert len(panel_contours) == 1
    assert_bounds(panel_contours[0].outer, (6.2, 6.2, 93.8, 93.8))
    assert len(panel_contours[0].holes) == 1
    assert_bounds(panel_contours[0].holes[0], (38.8, 38.8, 61.2, 61.2))


def test_export_uses_independent_clearance_and_kerf_settings():
    """DXF export should apply outer clearance, hole clearance, and kerf independently."""
    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.STRAIGHT
    params.shell.wall_thickness = 1.2
    params.shell.dxf_outer_clearance = 0.5
    params.shell.dxf_hole_clearance = 1.5
    params.shell.dxf_laser_kerf = 0.2

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        output_path = f.name

    try:
        success = export_baseplate_dxf([contour], output_path, params)
        assert success is True
        bounds = read_lwpolyline_bounds(output_path)
        assert bounds == [(1.8, 1.8, 98.2, 98.2), (32.2, 32.2, 67.8, 67.8)]
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


if __name__ == "__main__":
    test_baseplate_contour_uses_inner_wall_and_default_extra_shrink()
    test_panel_contour_uses_top_inner_wall_and_default_extra_shrink()
    test_panel_beveled_export_scales_holes_in_same_direction()
    test_export_uses_independent_clearance_and_kerf_settings()
    print("All DXF writer tests passed.")
