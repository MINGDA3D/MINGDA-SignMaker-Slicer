import math

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
    U_SHAPE_FINE_LAYER_HEIGHT,
    U_SHAPE_OVERHANG_LINE_WIDTH_RATIO,
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


def _printable_outward_arc_offset(radius: float, arc_z: float, slope: float) -> float:
    if arc_z <= 0.0:
        return 0.0
    if arc_z >= radius:
        return radius
    if slope <= 1.0:
        return min(radius, arc_z)
    center_x = radius / (1.0 - slope)
    center_z = -slope * radius / (1.0 - slope)
    printable_radius = math.hypot(center_x, center_z)
    return center_x + math.sqrt(
        max(0.0, printable_radius * printable_radius - (arc_z - center_z) ** 2)
    )


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


def _contour_with_reversed_winding() -> Contour:
    contour = _contour_with_hole()
    return Contour(
        outer=Path(
            points=list(reversed(contour.outer.points)),
            path_type=PathType.OUTER,
            is_closed=True,
        ),
        holes=[
            Path(
                points=list(reversed(contour.holes[0].points)),
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


def test_u_shape_offset_uses_curved_arc_then_straight():
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.u_bottom_layers = 0
    max_overhang = params.shell.line_width * U_SHAPE_OVERHANG_LINE_WIDTH_RATIO
    slope = max_overhang / U_SHAPE_FINE_LAYER_HEIGHT

    assert calculate_u_shape_offset_at_z(0.0, params.shell) == pytest.approx(0.0)
    assert calculate_u_shape_offset_at_z(0.1, params.shell) == pytest.approx(
        _printable_outward_arc_offset(5.0, 0.1, slope)
    )
    assert calculate_u_shape_offset_at_z(0.2, params.shell) == pytest.approx(
        _printable_outward_arc_offset(5.0, 0.2, slope)
    )
    previous_offset = calculate_u_shape_offset_at_z(0.0, params.shell)
    step_count = int(0.6 / U_SHAPE_FINE_LAYER_HEIGHT)
    for index in range(1, step_count + 1):
        z = round(index * U_SHAPE_FINE_LAYER_HEIGHT, 6)
        offset = calculate_u_shape_offset_at_z(z, params.shell)
        assert offset - previous_offset <= max_overhang + 1e-9
        previous_offset = offset
    assert calculate_u_shape_offset_at_z(5.0, params.shell) == pytest.approx(5.0)
    assert calculate_u_shape_offset_at_z(10.0, params.shell) == pytest.approx(5.0)
    mid_offset = calculate_u_shape_offset_at_z(2.5, params.shell)
    assert mid_offset == pytest.approx(
        _printable_outward_arc_offset(5.0, 2.5, slope)
    )
    assert 0.0 < mid_offset < 5.0


def test_u_shape_offset_starts_from_build_plate():
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.u_bottom_layers = 0

    first_offset = calculate_u_shape_offset_at_z(0.0, params.shell)
    second_offset = calculate_u_shape_offset_at_z(U_SHAPE_FINE_LAYER_HEIGHT, params.shell)
    third_offset = calculate_u_shape_offset_at_z(U_SHAPE_FINE_LAYER_HEIGHT * 2, params.shell)

    assert first_offset == pytest.approx(0.0)
    assert second_offset > first_offset
    assert second_offset - first_offset <= params.shell.line_width * U_SHAPE_OVERHANG_LINE_WIDTH_RATIO + 1e-9
    assert third_offset - second_offset <= params.shell.line_width * U_SHAPE_OVERHANG_LINE_WIDTH_RATIO + 1e-9


def test_u_shape_offset_has_no_single_fine_layer_overhang_jump():
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.u_bottom_layers = 3

    max_delta = params.shell.line_width * U_SHAPE_OVERHANG_LINE_WIDTH_RATIO
    previous_offset = calculate_u_shape_offset_at_z(0.0, params.shell)

    step_count = int(params.shell.u_arc_height / U_SHAPE_FINE_LAYER_HEIGHT)
    for index in range(1, step_count + 1):
        z = round(index * U_SHAPE_FINE_LAYER_HEIGHT, 6)
        offset = calculate_u_shape_offset_at_z(z, params.shell)
        assert offset - previous_offset <= max_delta + 1e-9
        previous_offset = offset


def test_u_shape_offset_keeps_circular_form_while_limiting_initial_slope():
    params = _u_shape_params()
    params.shell.layer_height = 1.0
    params.shell.line_width = 1.0
    params.shell.u_bottom_layers = 0
    slope = (params.shell.line_width * U_SHAPE_OVERHANG_LINE_WIDTH_RATIO) / U_SHAPE_FINE_LAYER_HEIGHT

    assert calculate_u_shape_offset_at_z(2.5, params.shell) == pytest.approx(
        _printable_outward_arc_offset(5.0, 2.5, slope)
    )
    assert calculate_u_shape_offset_at_z(5.0, params.shell) == pytest.approx(5.0)
    assert calculate_u_shape_offset_at_z(10.0, params.shell) == pytest.approx(5.0)


def test_u_shape_contour_applies_printable_arc_to_outer_and_holes():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.shell.u_bottom_layers = 0
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


def test_u_shape_offset_profile_start_is_independent_from_solid_bottom_height():
    params = _u_shape_params()
    params.shell.height = 12.0
    params.shell.layer_height = 0.3
    params.shell.u_bottom_layers = 3
    profile_start = 2.0

    assert calculate_u_shape_offset_at_z(
        0.0,
        params.shell,
        profile_start,
    ) == pytest.approx(0.0)
    assert calculate_u_shape_offset_at_z(
        1.0,
        params.shell,
        profile_start,
    ) == pytest.approx(0.0)
    assert calculate_u_shape_offset_at_z(
        1.9,
        params.shell,
        profile_start,
    ) == pytest.approx(0.0)
    first_layer_offset = calculate_u_shape_offset_at_z(2.0, params.shell, profile_start)
    assert first_layer_offset == pytest.approx(0.0)
    first_arc_offset = calculate_u_shape_offset_at_z(2.2, params.shell, profile_start)
    slope = (params.shell.line_width * U_SHAPE_OVERHANG_LINE_WIDTH_RATIO) / U_SHAPE_FINE_LAYER_HEIGHT
    assert first_arc_offset == pytest.approx(
        _printable_outward_arc_offset(5.0, 0.2, slope)
    )
    mid_offset = calculate_u_shape_offset_at_z(4.4, params.shell, profile_start)
    assert mid_offset == pytest.approx(
        _printable_outward_arc_offset(5.0, 2.4, slope)
    )
    assert calculate_u_shape_offset_at_z(
        12.0,
        params.shell,
        profile_start,
    ) == pytest.approx(5.0)


def test_u_shape_expands_outer_and_shrinks_holes():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.shell.u_bottom_layers = 0
    engine = SliceEngine()

    bottom = engine._apply_edge_profile(contour, 0.0, params.shell)
    arc_top = engine._apply_edge_profile(contour, 5.2, params.shell)
    straight_part = engine._apply_edge_profile(contour, 10.0, params.shell)

    assert bottom is not None
    assert arc_top is not None
    assert straight_part is not None
    bottom_offset = calculate_u_shape_offset_at_z(0.0, params.shell)
    assert bottom.outer.bounds == pytest.approx(
        (-bottom_offset, -bottom_offset, 100.0 + bottom_offset, 100.0 + bottom_offset),
        abs=1e-3,
    )
    assert bottom.holes[0].bounds == pytest.approx(
        (30.0 + bottom_offset, 30.0 + bottom_offset, 70.0 - bottom_offset, 70.0 - bottom_offset),
        abs=1e-3,
    )
    assert arc_top.outer.bounds == pytest.approx((-5.0, -5.0, 105.0, 105.0))
    assert arc_top.holes[0].bounds == pytest.approx((35.0, 35.0, 65.0, 65.0))
    assert straight_part.outer.bounds == pytest.approx((-5.0, -5.0, 105.0, 105.0))
    assert straight_part.holes[0].bounds == pytest.approx((35.0, 35.0, 65.0, 65.0))


def test_u_shape_expands_outer_and_shrinks_holes_with_reversed_winding():
    contour = _contour_with_reversed_winding()
    params = _u_shape_params()
    params.shell.u_bottom_layers = 0
    engine = SliceEngine()

    arc_top = engine._apply_edge_profile(contour, 5.2, params.shell)

    assert arc_top is not None
    assert arc_top.outer.bounds == pytest.approx((-5.0, -5.0, 105.0, 105.0))
    assert arc_top.holes[0].bounds == pytest.approx((35.0, 35.0, 65.0, 65.0))


def test_u_shape_bottom_solid_layers_follow_profile_started_at_z_0():
    contour = _contour_with_hole()
    params = _u_shape_params()
    engine = SliceEngine()
    bottom_height = 0.9
    bottom_top_offset = calculate_u_shape_offset_at_z(bottom_height, params.shell)

    bottom = engine._apply_edge_profile(
        contour,
        0.0,
        params.shell,
    )
    before_profile = engine._apply_edge_profile(
        contour,
        0.1,
        params.shell,
    )
    profile_started = engine._apply_edge_profile(
        contour,
        0.2,
        params.shell,
    )
    bottom_top = engine._apply_edge_profile(
        contour,
        bottom_height,
        params.shell,
    )
    arc_mid = engine._apply_edge_profile(
        contour,
        2.6,
        params.shell,
    )

    assert bottom is not None
    assert before_profile is not None
    assert profile_started is not None
    assert bottom_top is not None
    assert arc_mid is not None
    bottom_offset = calculate_u_shape_offset_at_z(0.0, params.shell)
    before_profile_offset = calculate_u_shape_offset_at_z(0.1, params.shell)
    profile_started_offset = calculate_u_shape_offset_at_z(0.2, params.shell)
    assert bottom.outer.bounds[0] == pytest.approx(-bottom_offset, abs=1e-3)
    assert before_profile.outer.bounds[0] == pytest.approx(-before_profile_offset, abs=1e-3)
    assert profile_started.outer.bounds[0] == pytest.approx(-profile_started_offset, abs=1e-3)
    assert profile_started.holes[0].bounds[0] == pytest.approx(30.0 + profile_started_offset, abs=1e-3)
    assert bottom_top.outer.bounds[0] == pytest.approx(-bottom_top_offset, abs=1e-3)
    assert bottom_top.holes[0].bounds[0] == pytest.approx(30.0 + bottom_top_offset, abs=1e-3)
    assert arc_mid.outer.bounds[0] < bottom_top.outer.bounds[0]
    assert arc_mid.holes[0].bounds[0] > bottom_top.holes[0].bounds[0]


def test_u_shape_auto_emits_bottom_face_fill_when_bottom_face_toggle_is_off():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.u_bottom_layers = 3
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 2.0

    result = SliceEngine().slice([contour], params)

    assert is_bottom_face_effective(params) is True
    bottom_face_layers = [
        layer
        for layer in result.layers
        if any(path.role == PathRole.FILL_BOTTOM_FACE for path in layer.paths)
    ]
    expected_bottom_layers = math.ceil(
        params.shell.u_bottom_layers * params.shell.layer_height / U_SHAPE_FINE_LAYER_HEIGHT
    )
    assert len(bottom_face_layers) == expected_bottom_layers
    assert bottom_face_layers[0].z_height == pytest.approx(0.0)
    assert bottom_face_layers[-1].z_height == pytest.approx(
        (expected_bottom_layers - 1) * U_SHAPE_FINE_LAYER_HEIGHT
    )
    assert all(layer.layer_height == pytest.approx(U_SHAPE_FINE_LAYER_HEIGHT) for layer in bottom_face_layers)


def test_u_shape_arc_region_uses_fine_layers():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.u_bottom_layers = 3
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 2.0
    params.shell.u_arc_height = 5.0

    result = SliceEngine().slice([contour], params)

    arc_layers = [
        layer
        for layer in result.layers
        if 0.0 <= layer.z_height < 5.0 - 1e-6
    ]

    expected_arc_layers = math.ceil(params.shell.u_arc_height / U_SHAPE_FINE_LAYER_HEIGHT)
    assert len(arc_layers) == expected_arc_layers
    assert arc_layers[0].z_height == pytest.approx(0.0)
    assert arc_layers[-1].z_height == pytest.approx(
        (expected_arc_layers - 1) * U_SHAPE_FINE_LAYER_HEIGHT
    )
    assert all(layer.layer_height == pytest.approx(U_SHAPE_FINE_LAYER_HEIGHT) for layer in arc_layers)


def test_u_shape_sliced_wall_paths_expand_through_bottom_layers():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.u_bottom_layers = 3
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 2.0

    result = SliceEngine().slice([contour], params)
    layers_by_z = {layer.z_height: layer for layer in result.layers}

    bottom_bounds = _outer_wall_bounds(layers_by_z[0.0])
    second_arc_bounds = _outer_wall_bounds(layers_by_z[0.1])
    third_arc_bounds = _outer_wall_bounds(layers_by_z[0.2])
    bottom_top_bounds = _outer_wall_bounds(layers_by_z[0.8])
    arc_bounds = _outer_wall_bounds(layers_by_z[1.9])
    bottom_offset = calculate_u_shape_offset_at_z(0.0, params.shell)
    second_offset = calculate_u_shape_offset_at_z(0.1, params.shell)
    third_offset = calculate_u_shape_offset_at_z(0.2, params.shell)
    bottom_top_offset = calculate_u_shape_offset_at_z(0.8, params.shell)

    assert second_arc_bounds[0] == pytest.approx(bottom_bounds[0] - (second_offset - bottom_offset), abs=1e-3)
    assert second_arc_bounds[2] == pytest.approx(bottom_bounds[2] + (second_offset - bottom_offset), abs=1e-3)
    assert third_arc_bounds[0] == pytest.approx(bottom_bounds[0] - (third_offset - bottom_offset), abs=1e-3)
    assert third_arc_bounds[2] == pytest.approx(bottom_bounds[2] + (third_offset - bottom_offset), abs=1e-3)
    assert bottom_top_bounds[0] == pytest.approx(bottom_bounds[0] - (bottom_top_offset - bottom_offset), abs=1e-3)
    assert bottom_top_bounds[2] == pytest.approx(bottom_bounds[2] + (bottom_top_offset - bottom_offset), abs=1e-3)
    assert arc_bounds[0] < bottom_bounds[0]
    assert arc_bounds[2] > bottom_bounds[2]
    assert arc_bounds[0] < bottom_top_bounds[0]
    assert arc_bounds[2] > bottom_top_bounds[2]


def test_u_shape_bottom_face_mesh_uses_u_bottom_layers_and_fine_steps():
    contour = _contour_with_hole()
    params = _u_shape_params()
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.u_bottom_layers = 3
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 2.0

    mesh = BottomFaceMeshBuilder(PathOffset()).build([contour], params)

    assert mesh is not None
    assert mesh.vertices[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert mesh.vertices[:, 2].max() == pytest.approx(0.9, abs=1e-6)

    wall_thickness = params.shell.line_width * params.shell.wall_count

    bottom_offset = calculate_u_shape_offset_at_z(0.0, params.shell)
    second_offset = calculate_u_shape_offset_at_z(0.1, params.shell)
    third_offset = calculate_u_shape_offset_at_z(0.2, params.shell)

    assert _x_bounds_at_z(mesh, 0.0) == pytest.approx(
        (wall_thickness - bottom_offset, 100.0 - wall_thickness + bottom_offset),
        abs=1e-3,
    )
    assert _x_bounds_at_z(mesh, 0.1) == pytest.approx(
        (wall_thickness - second_offset, 100.0 - wall_thickness + second_offset),
        abs=1e-3,
    )
    assert _x_bounds_at_z(mesh, 0.2) == pytest.approx(
        (wall_thickness - third_offset, 100.0 - wall_thickness + third_offset),
        abs=1e-3,
    )
