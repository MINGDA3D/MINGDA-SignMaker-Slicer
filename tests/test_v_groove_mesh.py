"""Regression tests for V-groove mesh attachment."""

from __future__ import annotations

import pytest
from shapely.geometry import LineString
from shapely.ops import unary_union

from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl.profile_regions import extract_polygons
from src.core.stl.step_mesh import StepMeshBuilder
from src.core.types import (
    Contour,
    Layer,
    LayerPath,
    Path,
    PathRole,
    Point,
    SliceParams,
    SliceResult,
)


def _v_groove_params() -> SliceParams:
    """Match the multi-wall settings from the reported preview defect."""
    params = SliceParams()
    params.shell.height = 10.0
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.wall_count = 5
    params.shell.wall_thickness = 3.0
    params.machine.nozzle_diameter = 0.6
    params.step.baseplate_step_enabled = True
    params.step.baseplate_step_height = 3.0
    params.step.baseplate_step_width = 2.4
    params.step.baseplate_step_is_v_groove = True
    return params


def _bounds(path: Path | LayerPath) -> tuple[float, float, float, float]:
    xs = [point.x for point in path.points]
    ys = [point.y for point in path.points]
    return min(xs), min(ys), max(xs), max(ys)


def _last_v_groove_layer(result: SliceResult) -> Layer:
    return [
        layer
        for layer in result.layers
        if any(path.role == PathRole.V_GROOVE for path in layer.paths)
    ][-1]


def test_concentric_multiwall_v_grooves_match_their_cavity_facing_walls() -> None:
    """Concentric wall passes must not all resolve to the first outer pass."""
    contour = Contour(
        outer=Path(
            points=[
                Point(0.0, 0.0),
                Point(100.0, 0.0),
                Point(100.0, 100.0),
                Point(0.0, 100.0),
            ],
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
                is_closed=True,
            )
        ],
    )
    params = _v_groove_params()
    layer = _last_v_groove_layer(SliceEngine().slice([contour], params))
    builder = StepMeshBuilder(PathOffset())
    walls = [path for path in layer.paths if path.role == PathRole.WALL]
    grooves = [path for path in layer.paths if path.role == PathRole.V_GROOVE]
    outer_groove = max(grooves, key=lambda path: _bounds(path)[2] - _bounds(path)[0])
    hole_groove = min(grooves, key=lambda path: _bounds(path)[2] - _bounds(path)[0])

    outer_wall = builder._match_step_to_wall_path(outer_groove, walls)
    hole_wall = builder._match_step_to_wall_path(hole_groove, walls)

    assert outer_wall is not None
    assert hole_wall is not None
    assert outer_wall is not hole_wall
    assert _bounds(outer_wall) == pytest.approx((2.7, 2.7, 97.3, 97.3), abs=1e-3)
    assert _bounds(hole_wall) == pytest.approx((27.3, 27.3, 72.7, 72.7), abs=1e-3)
    assert not builder._is_hole_step_path(outer_groove, outer_wall)
    assert builder._is_hole_step_path(hole_groove, hole_wall)

    geometry = builder._build_v_groove_layer_geometry(layer, params)
    polygons = sorted(
        extract_polygons(geometry),
        key=lambda polygon: polygon.bounds[2] - polygon.bounds[0],
        reverse=True,
    )
    assert len(polygons) == 2
    assert polygons[0].bounds == pytest.approx((3.0, 3.0, 97.0, 97.0), abs=1e-3)
    assert polygons[1].bounds == pytest.approx((24.6, 24.6, 75.4, 75.4), abs=1e-3)


def test_pointed_v_groove_starts_at_the_true_inner_wall_edge() -> None:
    """A symmetric pointed outline must attach at 3 mm, not the first 0.6 mm wall."""
    contour = Contour(
        outer=Path(
            points=[
                Point(-50.0, 0.0),
                Point(0.0, 12.0),
                Point(50.0, 0.0),
                Point(0.0, -12.0),
            ],
            is_closed=True,
        )
    )
    params = _v_groove_params()
    result = SliceEngine().slice([contour], params)
    layer = _last_v_groove_layer(result)
    builder = StepMeshBuilder(PathOffset())
    walls = [path for path in layer.paths if path.role == PathRole.WALL]
    groove = next(path for path in layer.paths if path.role == PathRole.V_GROOVE)

    matched_wall = builder._match_step_to_wall_path(groove, walls)

    assert matched_wall is not None
    assert matched_wall is walls[-1]

    wall_inner_coords = builder._calculate_inner_wall_from_path(
        matched_wall,
        matched_wall.line_width,
        reference_path=groove,
    )
    expected_inner = builder.path_offset.offset(
        contour.outer,
        -params.shell.wall_thickness,
    )[0]
    actual_bounds = (
        min(x for x, _y in wall_inner_coords[:-1]),
        min(y for _x, y in wall_inner_coords[:-1]),
        max(x for x, _y in wall_inner_coords[:-1]),
        max(y for _x, y in wall_inner_coords[:-1]),
    )
    groove_mesh = builder.build([contour], result, params)

    assert actual_bounds == pytest.approx(_bounds(expected_inner), abs=3e-3)
    assert groove_mesh is not None
    # A miter-limited toolpath cannot deposit the entire sharp wall-inset tip.
    # Reconstructing a ring from the wall used to invent that missing material.
    # Independently sweep every actual print path, then compare the mesh bounds.
    footprints = []
    for sliced_layer in result.layers:
        for path in sliced_layer.paths:
            if path.role != PathRole.V_GROOVE:
                continue
            coordinates = [(point.x, point.y) for point in path.points]
            coordinates.append(coordinates[0])
            footprints.append(LineString(coordinates).buffer(
                path.line_width / 2.0, join_style=2, mitre_limit=2.0,
            ))
    printed_region = unary_union(footprints)
    assert tuple(groove_mesh.bounds[0][:2]) + tuple(
        groove_mesh.bounds[1][:2]
    ) == pytest.approx(printed_region.bounds, abs=1e-6)
    assert printed_region.bounds[0] > _bounds(expected_inner)[0] + 0.1


def test_overlapping_outer_and_hole_v_grooves_are_unioned_once_per_layer() -> None:
    """Meeting grooves must form one footprint instead of duplicate solids."""
    contour = Contour(
        outer=Path(
            points=[
                Point(0.0, 0.0),
                Point(100.0, 0.0),
                Point(100.0, 100.0),
                Point(0.0, 100.0),
            ],
            is_closed=True,
        ),
        holes=[
            Path(
                points=[
                    Point(8.4, 8.4),
                    Point(91.6, 8.4),
                    Point(91.6, 91.6),
                    Point(8.4, 91.6),
                ],
                is_closed=True,
            )
        ],
    )
    params = _v_groove_params()
    layer = _last_v_groove_layer(SliceEngine().slice([contour], params))
    builder = StepMeshBuilder(PathOffset())

    geometry = builder._build_v_groove_layer_geometry(layer, params)
    polygons = extract_polygons(geometry)

    assert len(polygons) == 1
    assert polygons[0].bounds == pytest.approx((3.0, 3.0, 97.0, 97.0), abs=1e-3)
    assert polygons[0].area == pytest.approx(879.36, abs=1e-3)

    mesh = builder.mesh_utils.extrude_polygon(polygons[0], layer.layer_height)
    assert mesh is not None
    assert abs(mesh.volume) == pytest.approx(263.808, abs=1e-3)
