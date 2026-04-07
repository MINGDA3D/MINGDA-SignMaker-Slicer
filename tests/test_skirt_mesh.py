import pytest

from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl.skirt_mesh import SkirtMeshBuilder
from src.core.types import BevelDirection, Contour, EdgeType, Path, Point, SliceParams


def _distance_to_rect_xy(x, y, rect):
    left, bottom, right, top = rect
    if left <= x <= right and bottom <= y <= top:
        return min(x - left, right - x, y - bottom, top - y)
    dx = max(left - x, 0.0, x - right)
    dy = max(bottom - y, 0.0, y - top)
    return (dx * dx + dy * dy) ** 0.5


def _min_mesh_gap(mesh, rect):
    return min(_distance_to_rect_xy(vertex[0], vertex[1], rect) for vertex in mesh.vertices)


def test_skirt_mesh_is_watertight_for_short_connectors():
    contour = Contour(
        outer=Path(
            points=[
                Point(0, 0),
                Point(50, 0),
                Point(50, 12),
                Point(18, 12),
                Point(18, 50),
                Point(0, 50),
            ]
        ),
        holes=[],
    )

    params = SliceParams()
    params.skirt.enabled = True
    params.skirt.height = 0.3

    mesh = SkirtMeshBuilder(PathOffset()).build([contour], params)

    assert mesh is not None
    assert len(mesh.faces) > 0
    assert mesh.is_watertight
    assert mesh.body_count == 1


def test_skirt_mesh_uses_bottom_reference_for_top_large_bevel():
    contour = Contour(
        outer=Path(
            points=[
                Point(0, 0),
                Point(40, 0),
                Point(40, 20),
                Point(0, 20),
            ]
        ),
        holes=[],
    )

    params = SliceParams()
    params.skirt.enabled = True
    params.skirt.height = 0.3
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_LARGE
    params.shell.bevel_width = 2.0
    params.shell.baseplate_thickness = 1.0
    params.shell.panel_thickness = 1.0
    params.shell.height = 10.0

    bottom_contour = SliceEngine()._apply_edge_profile(contour, 0, params.shell)
    assert bottom_contour is not None

    straight_mesh = SkirtMeshBuilder(PathOffset()).build([contour], params)
    beveled_mesh = SkirtMeshBuilder(PathOffset()).build(
        [bottom_contour], params, source_contours=[bottom_contour]
    )

    assert straight_mesh is not None
    assert beveled_mesh is not None
    assert tuple(map(tuple, beveled_mesh.bounds)) == tuple(map(tuple, straight_mesh.bounds))


def test_skirt_mesh_respects_breakaway_gap_from_wall():
    contour = Contour(
        outer=Path(
            points=[
                Point(0, 0),
                Point(40, 0),
                Point(40, 20),
                Point(0, 20),
            ]
        ),
        holes=[],
    )

    params_touching = SliceParams()
    params_touching.skirt.enabled = True
    params_touching.skirt.height = 0.3
    params_touching.skirt.offset = 0.0

    params_gapped = SliceParams()
    params_gapped.skirt.enabled = True
    params_gapped.skirt.height = 0.3
    params_gapped.skirt.offset = 0.1

    touching_mesh = SkirtMeshBuilder(PathOffset()).build([contour], params_touching)
    gapped_mesh = SkirtMeshBuilder(PathOffset()).build([contour], params_gapped)

    assert touching_mesh is not None
    assert gapped_mesh is not None
    assert touching_mesh.is_watertight
    assert gapped_mesh.is_watertight
    assert _min_mesh_gap(touching_mesh, (0.0, 0.0, 40.0, 20.0)) == pytest.approx(0.0, abs=1e-6)
    assert _min_mesh_gap(gapped_mesh, (0.0, 0.0, 40.0, 20.0)) == pytest.approx(0.1, abs=1e-4)


def test_skirt_mesh_uses_nozzle_diameter_for_export_geometry():
    contour = Contour(
        outer=Path(
            points=[
                Point(0, 0),
                Point(40, 0),
                Point(40, 20),
                Point(0, 20),
            ]
        ),
        holes=[],
    )

    params = SliceParams()
    params.skirt.enabled = True
    params.skirt.height = 0.3
    params.machine.nozzle_diameter = 0.6

    mesh = SkirtMeshBuilder(PathOffset()).build([contour], params)

    assert mesh is not None
    assert mesh.bounds[0][0] == pytest.approx(-5.3, abs=1e-4)
    assert mesh.bounds[1][0] == pytest.approx(45.3, abs=1e-4)
