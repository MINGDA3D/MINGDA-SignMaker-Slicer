"""Regression tests for nested standalone contour shell meshes."""

import pytest
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl import ShellMeshBuilder
from src.core.stl.profile_regions import (
    contour_to_geometry,
    extract_polygons,
    merge_contours_by_nesting,
    profile_nesting_depths,
)
from src.core.stl.step_mesh import StepMeshBuilder
from src.core.types import Contour, Path, Point, SliceParams, normalize_slice_params


def _rectangle(x_min: float, y_min: float, x_max: float, y_max: float) -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(x_min, y_min),
                Point(x_max, y_min),
                Point(x_max, y_max),
                Point(x_min, y_max),
            ],
            is_closed=True,
        )
    )


def _shell_region(contours: list[Contour], params: SliceParams) -> BaseGeometry:
    result = SliceEngine().slice(contours, params)
    builder = ShellMeshBuilder(PathOffset(), params.shell.wall_thickness)
    polygons = builder._build_layer_shell_region_polygons(
        contours,
        result.layers[0],
        params,
    )
    return unary_union(polygons)


def _profiles(
    contours: list[Contour],
) -> list[ShapelyPolygon]:
    profiles: list[ShapelyPolygon] = []
    for contour in contours:
        profiles.extend(extract_polygons(contour_to_geometry(contour)))
    return profiles


def test_nested_contour_wall_supports_top_step_with_bottom_face_enabled() -> None:
    """A nested SVG loop must retain the wall that supports its top ledge."""
    outer_contour = _rectangle(0, 0, 40, 40)
    nested_contour = _rectangle(12, 12, 20, 20)

    params = SliceParams()
    params.shell.height = 3.0
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.wall_thickness = 1.2
    params.shell.wall_count = 2
    params.bottom_face.enabled = True
    params.bottom_face.thickness = 0.3
    params.step.panel_step_enabled = True
    params.step.panel_step_height = 2.4
    params.step.panel_step_width = 1.8
    params = normalize_slice_params(params)

    shell_region = _shell_region([outer_contour, nested_contour], params)

    assert shell_region.covers(ShapelyPoint(12.6, 16.0))
    assert not shell_region.covers(ShapelyPoint(16.0, 16.0))

    step_builder = StepMeshBuilder(PathOffset())
    wall_inner_paths = step_builder.path_offset.offset(
        nested_contour.outer,
        -params.shell.wall_thickness,
    )
    wall_inner_coords = [
        (point.x, point.y) for point in wall_inner_paths[0].points
    ]
    step_region = step_builder._build_step_ring_geometry(
        wall_inner_coords,
        params.step.panel_step_width,
        is_hole=False,
    )

    assert step_region is not None
    assert step_region.distance(shell_region) == pytest.approx(0.0, abs=1e-6)


def test_overlapping_top_level_contours_still_merge_before_shelling() -> None:
    """Overlapping outer profiles must not regain walls inside their union."""
    left_contour = _rectangle(0, 0, 20, 20)
    right_contour = _rectangle(10, 0, 30, 20)

    params = SliceParams()
    params.shell.height = 0.3
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.wall_thickness = 1.2
    params.shell.wall_count = 2
    params = normalize_slice_params(params)

    shell_region = _shell_region([left_contour, right_contour], params)

    assert shell_region.covers(ShapelyPoint(0.6, 10.0))
    assert not shell_region.covers(ShapelyPoint(10.6, 10.0))


def test_collectively_contained_loop_remains_an_independent_wall() -> None:
    """Two overlapping parents must not jointly absorb a smaller inner loop."""
    contours = [
        _rectangle(0, 0, 30, 40),
        _rectangle(20, 0, 50, 40),
        _rectangle(15, 10, 35, 30),
    ]
    params = SliceParams()
    params.shell.height = 0.3
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.wall_thickness = 1.2
    params.shell.wall_count = 2
    params = normalize_slice_params(params)

    profiles = _profiles(contours)
    shell_region = _shell_region(contours, params)
    merged_contours = merge_contours_by_nesting(contours)

    assert profile_nesting_depths(profiles) == [0, 0, 1]
    assert len(merged_contours) == 2
    assert shell_region.covers(ShapelyPoint(15.6, 20.0))
    assert not shell_region.covers(ShapelyPoint(25.0, 20.0))


def test_boundary_touching_child_merges_with_parent_profile() -> None:
    """A child touching the outer boundary is overlap, not strict nesting."""
    contours = [
        _rectangle(0, 0, 40, 40),
        _rectangle(0, 10, 12, 30),
    ]
    profiles = _profiles(contours)

    assert profile_nesting_depths(profiles) == [0, 0]
    assert len(merge_contours_by_nesting(contours)) == 1


def test_strict_nesting_depth_supports_multiple_inner_levels() -> None:
    contours = [
        _rectangle(0, 0, 80, 80),
        _rectangle(10, 10, 70, 70),
        _rectangle(20, 20, 60, 60),
        _rectangle(30, 30, 50, 50),
    ]
    assert profile_nesting_depths(_profiles(contours)) == [0, 1, 2, 3]


def test_flat_step_merges_overlapping_profiles_before_building_ledges() -> None:
    contours = [
        _rectangle(0, 0, 20, 20),
        _rectangle(10, 0, 30, 20),
    ]
    merged_contours = merge_contours_by_nesting(contours)

    assert len(merged_contours) == 1
    assert merged_contours[0].outer.bounds == pytest.approx((0, 0, 30, 20))


def test_flat_step_builder_uses_shared_profile_merge() -> None:
    contours = [
        _rectangle(0, 0, 20, 20),
        _rectangle(10, 0, 30, 20),
    ]
    params = SliceParams()
    params.shell.height = 3.0
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.wall_thickness = 1.2
    params.shell.wall_count = 2
    params.step.panel_step_enabled = True
    params.step.panel_step_height = 2.4
    params.step.panel_step_width = 1.8
    params = normalize_slice_params(params)
    meshes = StepMeshBuilder(PathOffset())._build_flat_step_meshes(
        contours,
        params,
    )

    assert len(meshes) == 1


def test_explicit_empty_transformed_contours_do_not_fall_back() -> None:
    contours = [_rectangle(0, 0, 20, 20)]
    params = SliceParams()
    params.shell.height = 3.0
    params.step.panel_step_enabled = True
    params.step.panel_step_height = 2.4
    params = normalize_slice_params(params)

    meshes = StepMeshBuilder(PathOffset())._build_flat_step_meshes(
        contours,
        params,
        panel_contours=[],
    )

    assert meshes == []


def test_flat_step_drops_boundaries_filled_by_same_depth_profile_union() -> None:
    parent = _rectangle(0, 0, 40, 40)
    parent.holes = [_rectangle(10, 10, 30, 30).outer]
    filler = _rectangle(10, 10, 30, 30)
    merged_contours = merge_contours_by_nesting([parent, filler])

    assert len(merged_contours) == 1
    assert merged_contours[0].holes == []


def test_merged_contour_winding_matches_outer_and_hole_roles() -> None:
    parent = _rectangle(0, 0, 40, 40)
    parent.holes = [_rectangle(10, 10, 30, 30).outer]

    merged_contours = merge_contours_by_nesting([parent])

    assert len(merged_contours) == 1
    assert merged_contours[0].outer.area > 0
    assert len(merged_contours[0].holes) == 1
    assert merged_contours[0].holes[0].area < 0


def test_flat_step_keeps_all_islands_created_by_inner_wall_offset() -> None:
    contours = [
        _rectangle(0, 0, 10, 10),
        _rectangle(9.5, 9.5, 19.5, 19.5),
    ]
    step_builder = StepMeshBuilder(PathOffset())
    merged_contours = merge_contours_by_nesting(contours)

    assert len(merged_contours) == 1
    assert len(
        step_builder.path_offset.offset(merged_contours[0].outer, -1.2)
    ) == 2

    meshes = step_builder._build_flat_step_meshes_for_contour(
        merged_contours[0],
        step_width=1.8,
        step_thickness=0.4,
        z_position=2.0,
        wall_thickness=1.2,
    )

    assert len(meshes) == 2
