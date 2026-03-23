from pathlib import Path as FsPath

import trimesh

from src.core.stl_writer import STLWriter
from src.core.types import (
    BevelDirection,
    Contour,
    EdgeDirection,
    EdgeType,
    Path,
    PathType,
    Point,
    SliceParams,
    SliceResult,
)
from src.utils.geometry import normalize_path


def _make_contour() -> Contour:
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


def test_beveled_bottom_contours_are_used_for_wrap_and_outline():
    contour = _make_contour()
    params = SliceParams()
    params.shell.height = 30.0
    params.shell.wall_thickness = 1.2
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_SMALL
    params.shell.bevel_width = 5.0
    params.shell.baseplate_thickness = 5.0
    params.shell.panel_thickness = 5.0
    params.edge_wrap.wrap_enabled = True
    params.edge_wrap.outline_enabled = True
    params.edge_wrap.wrap_direction = EdgeDirection.OUTER
    params.edge_wrap.outline_direction = EdgeDirection.OUTER

    writer = STLWriter(wall_thickness=1.2)
    writer.shell_builder.build = lambda layers: trimesh.creation.box(extents=(1.0, 1.0, 1.0))

    captured = {"wrap": None, "outline": None}

    def _capture_wrap(contours_arg, result_arg, params_arg):
        captured["wrap"] = contours_arg
        return None

    def _capture_outline(contours_arg, result_arg, params_arg):
        captured["outline"] = contours_arg
        return None

    writer.edge_wrap_builder.build_wrap = _capture_wrap
    writer.edge_wrap_builder.build_outline = _capture_outline

    output_dir = FsPath("e:/SignMaker Slicer/.tmp_pytest_stl_writer")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "beveled.stl"
    writer.write(SliceResult(), str(output_path), contours=[contour], params=params)

    assert output_path.exists()
    assert captured["wrap"] is not None
    assert captured["outline"] is not None

    wrap_outer_bounds = captured["wrap"][0].outer.bounds
    wrap_hole_bounds = captured["wrap"][0].holes[0].bounds

    assert wrap_outer_bounds == (0.0, 0.0, 100.0, 100.0)
    assert wrap_hole_bounds == (30.0, 30.0, 70.0, 70.0)
    assert captured["outline"][0].outer.bounds == wrap_outer_bounds
    assert captured["outline"][0].holes[0].bounds == wrap_hole_bounds
