import pytest
import numpy as np

from src.core.path_offset import PathOffset
from src.core.stl.edge_wrap_mesh import EdgeWrapMeshBuilder
from src.core.types import (
    Contour,
    EdgeDirection,
    Path,
    PathType,
    Point,
    SliceParams,
    SliceResult,
)
from src.utils.geometry import normalize_path


def _build_contour_with_hole() -> Contour:
    outer = normalize_path(Path(
        points=[
            Point(0.0, 0.0),
            Point(100.0, 0.0),
            Point(100.0, 100.0),
            Point(0.0, 100.0),
        ],
        path_type=PathType.OUTER,
        is_closed=True,
    ))
    hole = normalize_path(Path(
        points=[
            Point(30.0, 30.0),
            Point(70.0, 30.0),
            Point(70.0, 70.0),
            Point(30.0, 70.0),
        ],
        path_type=PathType.INNER,
        is_closed=True,
    ))
    return Contour(outer=outer, holes=[hole])


def _build_params() -> SliceParams:
    params = SliceParams()
    params.shell.height = 30.0
    params.shell.wall_thickness = 1.2
    return params


def test_inner_hole_wrap_starts_at_inner_wall_and_keeps_full_width():
    contour = _build_contour_with_hole()
    params = _build_params()
    builder = EdgeWrapMeshBuilder(PathOffset(), wall_thickness=params.shell.wall_thickness)

    outer_ring, inner_ring = builder._build_hole_wrap_rings(
        contour.holes[0], 2.0, EdgeDirection.INNER
    )

    assert min(x for x, _ in inner_ring[:-1]) == pytest.approx(28.8, abs=1e-6)
    assert max(x for x, _ in inner_ring[:-1]) == pytest.approx(71.2, abs=1e-6)
    assert min(x for x, _ in outer_ring[:-1]) == pytest.approx(26.8, abs=1e-6)
    assert max(x for x, _ in outer_ring[:-1]) == pytest.approx(73.2, abs=1e-6)
    assert (
        min(x for x, _ in inner_ring[:-1])
        - min(x for x, _ in outer_ring[:-1])
    ) == pytest.approx(2.0, abs=1e-6)


def test_inner_hole_outline_starts_at_inner_wall_and_keeps_full_width():
    contour = _build_contour_with_hole()
    params = _build_params()
    builder = EdgeWrapMeshBuilder(PathOffset(), wall_thickness=params.shell.wall_thickness)
    offset_bottom, offset_top = builder._get_hole_outline_offsets(
        2.0, 0.0, EdgeDirection.INNER
    )
    assert offset_bottom == pytest.approx(1.2, abs=1e-6)
    assert offset_top == pytest.approx(3.2, abs=1e-6)
    assert offset_top - offset_bottom == pytest.approx(2.0, abs=1e-6)
    mesh = builder._build_sloped_ring(
        contour.holes[0], 27.0, 30.0, offset_bottom, offset_top, is_outer=False
    )

    assert mesh is not None
    assert mesh.bounds[0][0] == pytest.approx(26.8, abs=1e-6)
    assert mesh.bounds[0][1] == pytest.approx(26.8, abs=1e-6)
    assert mesh.bounds[1][0] == pytest.approx(73.2, abs=1e-6)
    assert mesh.bounds[1][1] == pytest.approx(73.2, abs=1e-6)


def test_outer_hole_outline_starts_at_outer_wall_without_gap():
    contour = _build_contour_with_hole()
    params = _build_params()
    builder = EdgeWrapMeshBuilder(PathOffset(), wall_thickness=params.shell.wall_thickness)
    offset_bottom, offset_top = builder._get_hole_outline_offsets(
        2.0, 0.0, EdgeDirection.OUTER
    )

    assert offset_bottom == pytest.approx(0.0, abs=1e-6)
    assert offset_top == pytest.approx(-2.0, abs=1e-6)
    assert offset_bottom - offset_top == pytest.approx(2.0, abs=1e-6)

    mesh = builder._build_sloped_ring(
        contour.holes[0], 27.0, 30.0, offset_bottom, offset_top, is_outer=False
    )

    assert mesh is not None
    assert mesh.bounds[0][0] == pytest.approx(30.0, abs=1e-6)
    assert mesh.bounds[0][1] == pytest.approx(30.0, abs=1e-6)
    assert mesh.bounds[1][0] == pytest.approx(70.0, abs=1e-6)
    assert mesh.bounds[1][1] == pytest.approx(70.0, abs=1e-6)


def test_outer_hole_wrap_starts_at_outer_wall_without_gap():
    contour = _build_contour_with_hole()
    params = _build_params()
    builder = EdgeWrapMeshBuilder(PathOffset(), wall_thickness=params.shell.wall_thickness)

    outer_ring, inner_ring = builder._build_hole_wrap_rings(
        contour.holes[0], 2.0, EdgeDirection.OUTER
    )

    assert min(x for x, _ in outer_ring[:-1]) == pytest.approx(30.0, abs=1e-6)
    assert max(x for x, _ in outer_ring[:-1]) == pytest.approx(70.0, abs=1e-6)
    assert min(x for x, _ in inner_ring[:-1]) == pytest.approx(32.0, abs=1e-6)
    assert max(x for x, _ in inner_ring[:-1]) == pytest.approx(68.0, abs=1e-6)
    assert (
        min(x for x, _ in inner_ring[:-1])
        - min(x for x, _ in outer_ring[:-1])
    ) == pytest.approx(2.0, abs=1e-6)


def test_wrap_and_outline_are_generated_from_bottom_z_range():
    contour = _build_contour_with_hole()
    params = _build_params()
    params.edge_wrap.wrap_enabled = True
    params.edge_wrap.wrap_width = 2.0
    params.edge_wrap.wrap_height = 3.0
    params.edge_wrap.wrap_direction = EdgeDirection.OUTER
    params.edge_wrap.outline_enabled = True
    params.edge_wrap.outline_width = 1.0
    params.edge_wrap.outline_height = 2.0
    params.edge_wrap.outline_direction = EdgeDirection.OUTER

    builder = EdgeWrapMeshBuilder(PathOffset(), wall_thickness=params.shell.wall_thickness)

    wrap_mesh = builder.build_wrap([contour], SliceResult(), params)
    outline_mesh = builder.build_outline([contour], SliceResult(), params)

    assert wrap_mesh is not None
    assert outline_mesh is not None
    assert wrap_mesh.bounds[0][2] == pytest.approx(0.0, abs=1e-6)
    assert wrap_mesh.bounds[1][2] == pytest.approx(3.0, abs=1e-6)
    assert outline_mesh.bounds[0][2] == pytest.approx(0.0, abs=1e-6)
    assert outline_mesh.bounds[1][2] == pytest.approx(2.0, abs=1e-6)


def test_outer_outline_widens_upward_from_bottom_wall_reference():
    contour = _build_contour_with_hole()
    params = _build_params()
    params.edge_wrap.outline_enabled = True
    params.edge_wrap.outline_width = 1.0
    params.edge_wrap.outline_height = 2.0
    params.edge_wrap.outline_direction = EdgeDirection.OUTER

    builder = EdgeWrapMeshBuilder(PathOffset(), wall_thickness=params.shell.wall_thickness)
    outline_mesh = builder.build_outline([contour], SliceResult(), params)

    assert outline_mesh is not None

    z_min = outline_mesh.bounds[0][2]
    z_max = outline_mesh.bounds[1][2]
    bottom_vertices = outline_mesh.vertices[np.isclose(outline_mesh.vertices[:, 2], z_min)]
    top_vertices = outline_mesh.vertices[np.isclose(outline_mesh.vertices[:, 2], z_max)]

    assert len(bottom_vertices) > 0
    assert len(top_vertices) > 0
    assert bottom_vertices[:, 0].min() == pytest.approx(0.0, abs=0.02)
    assert bottom_vertices[:, 0].max() == pytest.approx(100.0, abs=0.02)
    assert top_vertices[:, 0].min() < bottom_vertices[:, 0].min()
    assert top_vertices[:, 0].max() > bottom_vertices[:, 0].max()
