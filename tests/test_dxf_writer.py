"""
Test DXF export functionality (baseplate and panel)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.types import (
    Point, Path, Contour, SliceParams, ShellParams,
    EdgeType, BevelDirection, EdgeProfile, EdgeProfileType
)
from src.core.dxf_writer import DXFWriter, export_baseplate_dxf, export_panel_dxf
import tempfile
import os


def create_test_contour():
    """Create test contour (simple rectangle)"""
    # Outer contour: 100x100mm rectangle
    outer_points = [
        Point(0, 0),
        Point(100, 0),
        Point(100, 100),
        Point(0, 100),
    ]
    outer = Path(points=outer_points, is_closed=True)

    # Hole: 30x30mm rectangle (centered)
    hole_points = [
        Point(35, 35),
        Point(65, 35),
        Point(65, 65),
        Point(35, 65),
    ]
    hole = Path(points=hole_points, is_closed=True)

    return Contour(outer=outer, holes=[hole], name="Test contour")


def test_export_baseplate_straight_edge():
    """Test straight edge baseplate export"""
    print("=" * 50)
    print("Test 1: Straight edge baseplate export")
    print("=" * 50)

    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.STRAIGHT
    params.shell.height = 30.0

    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as f:
        output_path = f.name

    try:
        success = export_baseplate_dxf([contour], output_path, params, -0.4)
        print(f"Export result: {'Success' if success else 'Failed'}")
        print(f"Output file: {output_path}")

        # Check file exists and size > 0
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"File size: {size} bytes")
            assert size > 0, "File size is 0"
        else:
            print("Error: File not created")

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

    print("Test 1 passed!\n")


def test_export_panel_straight_edge():
    """Test straight edge panel export"""
    print("=" * 50)
    print("Test 2: Straight edge panel export")
    print("=" * 50)

    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.STRAIGHT
    params.shell.height = 30.0

    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as f:
        output_path = f.name

    try:
        success = export_panel_dxf([contour], output_path, params, 0.0)
        print(f"Export result: {'Success' if success else 'Failed'}")
        print(f"Output file: {output_path}")

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"File size: {size} bytes")
            assert size > 0, "File size is 0"

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

    print("Test 2 passed!\n")


def test_export_baseplate_beveled_top_small():
    """Test beveled (top small) baseplate export"""
    print("=" * 50)
    print("Test 3: Beveled (top small) baseplate export")
    print("=" * 50)

    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_SMALL
    params.shell.bevel_width = 5.0
    params.shell.height = 30.0

    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as f:
        output_path = f.name

    try:
        success = export_baseplate_dxf([contour], output_path, params, -0.4)
        print(f"Export result: {'Success' if success else 'Failed'}")
        print(f"Bevel direction: TOP_SMALL -> baseplate uses original contour")

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"File size: {size} bytes")
            assert size > 0, "File size is 0"

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

    print("Test 3 passed!\n")


def test_export_panel_beveled_top_small():
    """Test beveled (top small) panel export"""
    print("=" * 50)
    print("Test 4: Beveled (top small) panel export")
    print("=" * 50)

    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_SMALL
    params.shell.bevel_width = 5.0
    params.shell.height = 30.0

    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as f:
        output_path = f.name

    try:
        success = export_panel_dxf([contour], output_path, params, 0.0)
        print(f"Export result: {'Success' if success else 'Failed'}")
        print(f"Bevel direction: TOP_SMALL -> panel uses inset {params.shell.bevel_width}mm contour")

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"File size: {size} bytes")
            assert size > 0, "File size is 0"

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

    print("Test 4 passed!\n")


def test_export_baseplate_beveled_top_large():
    """Test beveled (top large) baseplate export"""
    print("=" * 50)
    print("Test 5: Beveled (top large) baseplate export")
    print("=" * 50)

    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_LARGE
    params.shell.bevel_width = 5.0
    params.shell.height = 30.0

    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as f:
        output_path = f.name

    try:
        success = export_baseplate_dxf([contour], output_path, params, -0.4)
        print(f"Export result: {'Success' if success else 'Failed'}")
        print(f"Bevel direction: TOP_LARGE -> baseplate uses inset {params.shell.bevel_width}mm contour")

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"File size: {size} bytes")
            assert size > 0, "File size is 0"

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

    print("Test 5 passed!\n")


def test_export_panel_beveled_top_large():
    """Test beveled (top large) panel export"""
    print("=" * 50)
    print("Test 6: Beveled (top large) panel export")
    print("=" * 50)

    contour = create_test_contour()
    params = SliceParams()
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_LARGE
    params.shell.bevel_width = 5.0
    params.shell.height = 30.0

    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as f:
        output_path = f.name

    try:
        success = export_panel_dxf([contour], output_path, params, 0.0)
        print(f"Export result: {'Success' if success else 'Failed'}")
        print(f"Bevel direction: TOP_LARGE -> panel uses original contour")

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"File size: {size} bytes")
            assert size > 0, "File size is 0"

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

    print("Test 6 passed!\n")


def test_dxf_writer_class():
    """Test DXFWriter class methods"""
    print("=" * 50)
    print("Test 7: DXFWriter class methods")
    print("=" * 50)

    writer = DXFWriter()
    contour = create_test_contour()
    params = SliceParams()

    # Test get bottom offset
    params.shell.edge_type = EdgeType.STRAIGHT
    offset = writer._get_bottom_offset(params.shell)
    print(f"Straight edge bottom offset: {offset}")
    assert abs(offset) < 0.001, f"Straight edge bottom offset should be 0, got {offset}"

    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_SMALL
    params.shell.bevel_width = 5.0
    offset = writer._get_bottom_offset(params.shell)
    print(f"Beveled (TOP_SMALL) bottom offset: {offset}")
    assert abs(offset) < 0.001, f"TOP_SMALL bottom offset should be 0, got {offset}"

    params.shell.bevel_direction = BevelDirection.TOP_LARGE
    offset = writer._get_bottom_offset(params.shell)
    print(f"Beveled (TOP_LARGE) bottom offset: {offset}")
    assert abs(offset - (-5.0)) < 0.001, f"TOP_LARGE bottom offset should be -5, got {offset}"

    # Test get top offset
    params.shell.edge_type = EdgeType.STRAIGHT
    offset = writer._get_top_offset(params.shell)
    print(f"Straight edge top offset: {offset}")
    assert abs(offset) < 0.001

    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_SMALL
    offset = writer._get_top_offset(params.shell)
    print(f"Beveled (TOP_SMALL) top offset: {offset}")
    assert abs(offset - (-5.0)) < 0.001

    params.shell.bevel_direction = BevelDirection.TOP_LARGE
    offset = writer._get_top_offset(params.shell)
    print(f"Beveled (TOP_LARGE) top offset: {offset}")
    assert abs(offset) < 0.001

    print("Test 7 passed!\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DXF Export Functionality Tests")
    print("=" * 60 + "\n")

    test_export_baseplate_straight_edge()
    test_export_panel_straight_edge()
    test_export_baseplate_beveled_top_small()
    test_export_panel_beveled_top_small()
    test_export_baseplate_beveled_top_large()
    test_export_panel_beveled_top_large()
    test_dxf_writer_class()

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)
