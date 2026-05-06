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


def _outer_wall_bounds(layer) -> tuple[float, float, float, float]:
    wall_paths = [path for path in layer.paths if path.role == PathRole.WALL]
    assert wall_paths
    outer_wall = max(
        wall_paths,
        key=lambda path: (
            max(point.x for point in path.points)
            - min(point.x for point in path.points)
        ),
    )
    xs = [point.x for point in outer_wall.points]
    ys = [point.y for point in outer_wall.points]
    return min(xs), min(ys), max(xs), max(ys)


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


def test_u_shape_offset_uses_printable_arc_then_straight():
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6

    assert calculate_u_shape_offset_at_z(0.0, params.shell) == pytest.approx(0.0)
    assert calculate_u_shape_offset_at_z(5.0, params.shell) == pytest.approx(5.0)
    assert calculate_u_shape_offset_at_z(8.0, params.shell) == pytest.approx(5.0)
    mid_offset = calculate_u_shape_offset_at_z(2.5, params.shell)
    assert mid_offset > 5.0 * 0.5
    assert mid_offset < 5.0


def test_u_shape_offset_limits_first_layer_without_flattening_arc():
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6

    first_layer_offset = calculate_u_shape_offset_at_z(
        params.shell.layer_height,
        params.shell,
    )
    early_delta = calculate_u_shape_offset_at_z(0.6, params.shell) - (
        calculate_u_shape_offset_at_z(0.3, params.shell)
    )
    later_delta = calculate_u_shape_offset_at_z(3.6, params.shell) - (
        calculate_u_shape_offset_at_z(3.3, params.shell)
    )

    assert 0.0 < first_layer_offset <= params.shell.line_width
    assert early_delta > later_delta


def test_u_shape_contour_applies_printable_arc_to_outer_and_holes():
    contour = _contour_with_hole()
    params = _u_shape_params()
    engine = SliceEngine()

    offset = calculate_u_shape_offset_at_z(2.5, params.shell)
    arc_mid = engine._apply_edge_profile(contour, 2.5, params.shell)

    assert arc_mid is not None
    assert arc_mid.outer.bounds == pytest.approx(
        (-offset, -offset, 100.0 + offset, 100.0 + offset),
        abs=1e-3,
    )
    assert arc_mid.holes[0].bounds == pytest.approx(
        (30.0 + offset, 30.0 + offset, 70.0 - offset, 70.0 - offset),
        abs=1e-3,
    )


def test_u_shape_offset_stays_flat_for_bottom_thickness_then_arcs():
    params = _u_shape_params()
    flat_height = 2.0

    assert calculate_u_shape_offset_at_z(
        0.0,
        params.shell,
        flat_height,
    ) == pytest.approx(0.0)
    assert calculate_u_shape_offset_at_z(
        1.0,
        params.shell,
        flat_height,
    ) == pytest.approx(0.0)
    assert calculate_u_shape_offset_at_z(
        2.0,
        params.shell,
        flat_height,
    ) == pytest.approx(0.0)
    first_arc_offset = calculate_u_shape_offset_at_z(3.0, params.shell, flat_height)
    assert 0.0 < first_arc_offset <= params.shell.line_width
    mid_offset = calculate_u_shape_offset_at_z(4.5, params.shell, flat_height)
    assert mid_offset >= 5.0 * 0.5
    assert mid_offset < 5.0
    assert calculate_u_shape_offset_at_z(
        7.0,
        params.shell,
        flat_height,
    ) == pytest.approx(5.0)


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


def test_u_shape_bottom_layers_keep_same_profile_before_arc():
    contour = _contour_with_hole()
    params = _u_shape_params()
    engine = SliceEngine()
    flat_height = 2.0

    bottom = engine._apply_edge_profile(
        contour,
        0.0,
        params.shell,
        u_flat_height=flat_height,
    )
    flat_top = engine._apply_edge_profile(
        contour,
        flat_height,
        params.shell,
        u_flat_height=flat_height,
    )
    arc_mid = engine._apply_edge_profile(
        contour,
        flat_height + 2.5,
        params.shell,
        u_flat_height=flat_height,
    )

    assert bottom is not None
    assert flat_top is not None
    assert arc_mid is not None
    assert flat_top.outer.bounds == pytest.approx(bottom.outer.bounds)
    assert flat_top.holes[0].bounds == pytest.approx(bottom.holes[0].bounds)
    assert arc_mid.outer.bounds[0] < bottom.outer.bounds[0]
    assert arc_mid.holes[0].bounds[0] > bottom.holes[0].bounds[0]


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


def test_u_shape_sliced_wall_paths_stay_flat_through_bottom_face_layers():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 2.0

    result = SliceEngine().slice([contour], params)
    layers_by_z = {layer.z_height: layer for layer in result.layers}

    bottom_bounds = _outer_wall_bounds(layers_by_z[0.0])
    second_bottom_bounds = _outer_wall_bounds(layers_by_z[1.0])
    first_arc_bounds = _outer_wall_bounds(layers_by_z[3.0])
    arc_bounds = _outer_wall_bounds(layers_by_z[4.0])

    assert second_bottom_bounds == pytest.approx(bottom_bounds)
    assert first_arc_bounds[0] < bottom_bounds[0]
    assert first_arc_bounds[0] > arc_bounds[0]
    assert first_arc_bounds[2] > bottom_bounds[2]
    assert first_arc_bounds[2] < arc_bounds[2]
    assert arc_bounds[0] < bottom_bounds[0]
    assert arc_bounds[2] > bottom_bounds[2]


def test_u_shape_bottom_face_mesh_stays_flat_through_bottom_thickness():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 2.0

    mesh = BottomFaceMeshBuilder(PathOffset()).build([contour], params)

    assert mesh is not None
    assert mesh.vertices[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert mesh.vertices[:, 2].max() == pytest.approx(2.0, abs=1e-6)

    wall_thickness = params.shell.line_width * params.shell.wall_count

    assert _x_bounds_at_z(mesh, 0.0) == pytest.approx(
        (wall_thickness, 100.0 - wall_thickness),
        abs=1e-6,
    )
    assert _x_bounds_at_z(mesh, 1.0) == pytest.approx(
        (wall_thickness, 100.0 - wall_thickness),
        abs=1e-6,
    )
