import pytest

from src.core.slice_engine import SliceEngine
from src.core.path_offset import PathOffset
from src.core.stl.bottom_face_mesh import BottomFaceMeshBuilder
from src.core.types import (
    Contour,
    EdgeType,
    Path,
    PathRole,
    PathType,
    Point,
    SliceParams,
    calculate_u_shape_offset_at_z,
    is_bottom_face_effective,
)


def _x_bounds_at_z(mesh, z: float) -> tuple[float, float]:
    xs = [
        float(vertex[0])
        for vertex in mesh.vertices
        if abs(float(vertex[2]) - z) < 1e-6
    ]
    assert xs
    return min(xs), max(xs)


def _contour_with_hole() -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(0.0, 0.0),
                Point(100.0, 0.0),
                Point(100.0, 100.0),
                Point(0.0, 100.0),
            ],
            path_type=PathType.OUTER,
            is_closed=True,
        ),
        holes=[
            Path(
                points=[
                    Point(30.0, 30.0),
                    Point(70.0, 30.0),
                    Point(70.0, 70.0),
                    Point(30.0, 70.0),
                ],
                path_type=PathType.HOLE,
                is_closed=True,
            )
        ],
    )


def _u_shape_params() -> SliceParams:
    params = SliceParams()
    params.shell.edge_type = EdgeType.U_SHAPED
    params.shell.height = 10.0
    params.shell.layer_height = 1.0
    params.shell.u_arc_height = 5.0
    params.shell.line_width = 1.0
    params.shell.wall_count = 1
    return params


def test_u_shape_offset_uses_quarter_circle_then_straight():
    params = _u_shape_params()

    assert calculate_u_shape_offset_at_z(0.0, params.shell) == pytest.approx(0.0)
    assert calculate_u_shape_offset_at_z(5.0, params.shell) == pytest.approx(5.0)
    assert calculate_u_shape_offset_at_z(8.0, params.shell) == pytest.approx(5.0)
    assert calculate_u_shape_offset_at_z(2.5, params.shell) == pytest.approx(
        (2 * 5.0 * 2.5 - 2.5 * 2.5) ** 0.5
    )


def test_u_shape_expands_outer_and_shrinks_holes():
    contour = _contour_with_hole()
    params = _u_shape_params()
    engine = SliceEngine()

    bottom = engine._apply_edge_profile(contour, 0.0, params.shell)
    arc_top = engine._apply_edge_profile(contour, 5.0, params.shell)
    straight_part = engine._apply_edge_profile(contour, 10.0, params.shell)

    assert bottom is not None
    assert arc_top is not None
    assert straight_part is not None
    assert bottom.outer.bounds == pytest.approx((0.0, 0.0, 100.0, 100.0))
    assert bottom.holes[0].bounds == pytest.approx((30.0, 30.0, 70.0, 70.0))
    assert arc_top.outer.bounds == pytest.approx((-5.0, -5.0, 105.0, 105.0))
    assert arc_top.holes[0].bounds == pytest.approx((35.0, 35.0, 65.0, 65.0))
    assert straight_part.outer.bounds == pytest.approx(arc_top.outer.bounds)
    assert straight_part.holes[0].bounds == pytest.approx(arc_top.holes[0].bounds)


def test_u_shape_auto_emits_bottom_face_fill_when_bottom_face_toggle_is_off():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 2.0

    result = SliceEngine().slice([contour], params)

    assert is_bottom_face_effective(params) is True
    bottom_face_layers = [
        layer
        for layer in result.layers
        if any(path.role == PathRole.FILL_BOTTOM_FACE for path in layer.paths)
    ]
    assert [layer.z_height for layer in bottom_face_layers] == pytest.approx([0.0, 1.0])


def test_u_shape_bottom_face_mesh_follows_arc_offsets_by_layer():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 2.0

    mesh = BottomFaceMeshBuilder(PathOffset()).build([contour], params)

    assert mesh is not None
    assert mesh.vertices[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert mesh.vertices[:, 2].max() == pytest.approx(2.0, abs=1e-6)

    wall_thickness = params.shell.line_width * params.shell.wall_count
    layer_offset = calculate_u_shape_offset_at_z(1.0, params.shell)

    assert _x_bounds_at_z(mesh, 0.0) == pytest.approx(
        (wall_thickness, 100.0 - wall_thickness),
        abs=1e-6,
    )
    assert _x_bounds_at_z(mesh, 1.0) == pytest.approx(
        (wall_thickness - layer_offset, 100.0 - wall_thickness + layer_offset),
        abs=1e-6,
    )
