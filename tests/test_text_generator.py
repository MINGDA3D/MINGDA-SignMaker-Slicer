from copy import deepcopy

from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union

from src.core.font_manager import FontManager
from src.core.path_offset import PathOffset
from src.core.text_generator import TextGenerator
from src.core.slice_engine import SliceEngine
from src.core.stl import ShellMeshBuilder
from src.core.stl_writer import STLWriter
from src.core.types import (
    BevelDirection,
    EdgeDirection,
    EdgeProfile,
    EdgeType,
    Path,
    PathType,
    Point,
    SliceParams,
    normalize_slice_params,
)
from src.utils.geometry import is_clockwise


def _find_test_font() -> str:
    manager = FontManager()
    for name in (
        "Arial",
        "Calibri",
        "Times New Roman",
        "Microsoft YaHei UI",
        "Microsoft YaHei",
    ):
        path = manager.get_font_path(name)
        if path:
            return path
    return ""


def test_o_glyph_contour_is_normalized():
    font_path = _find_test_font()
    assert font_path, "No suitable system font found for text generator test"

    contours = TextGenerator().generate_text_contours("O", font_path, 30.0, 0.0)

    assert len(contours) == 1
    contour = contours[0]

    assert contour.outer.path_type == PathType.OUTER
    assert not is_clockwise(contour.outer)
    assert len(contour.holes) == 1

    hole = contour.holes[0]
    assert hole.path_type == PathType.INNER
    assert is_clockwise(hole)


def test_multi_hole_glyph_is_split_into_one_contour_with_multiple_holes():
    font_path = _find_test_font()
    assert font_path, "No suitable system font found for text generator test"

    contours = TextGenerator().generate_text_contours("B", font_path, 30.0, 0.0)

    assert len(contours) == 1
    contour = contours[0]
    assert contour.outer.path_type == PathType.OUTER
    assert not is_clockwise(contour.outer)
    assert len(contour.holes) >= 2
    assert all(hole.path_type == PathType.INNER for hole in contour.holes)
    assert all(is_clockwise(hole) for hole in contour.holes)


def test_single_character_with_disconnected_islands_returns_multiple_contours():
    font_path = _find_test_font()
    assert font_path, "No suitable system font found for text generator test"

    contours = TextGenerator().generate_text_contours("i", font_path, 30.0, 0.0)

    assert len(contours) >= 2
    assert all(contour.outer.path_type == PathType.OUTER for contour in contours)
    assert all(not is_clockwise(contour.outer) for contour in contours)
    assert all(len(contour.holes) == 0 for contour in contours)


def test_constructed_nested_loops_create_multiple_depth_aware_contours():
    paths = [
        Path(
            points=[Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)],
            path_type=PathType.OUTER,
            is_closed=True,
        ),
        Path(
            points=[Point(20, 20), Point(80, 20), Point(80, 80), Point(20, 80)],
            path_type=PathType.OUTER,
            is_closed=True,
        ),
        Path(
            points=[Point(35, 35), Point(65, 35), Point(65, 65), Point(35, 65)],
            path_type=PathType.OUTER,
            is_closed=True,
        ),
        Path(
            points=[Point(45, 45), Point(55, 45), Point(55, 55), Point(45, 55)],
            path_type=PathType.OUTER,
            is_closed=True,
        ),
    ]

    contours = TextGenerator._build_contours_from_paths(paths, "X")

    assert len(contours) == 2
    assert contours[0].name == "X"
    assert contours[1].name == "X"
    assert len(contours[0].holes) == 1
    assert len(contours[1].holes) == 1
    assert contours[0].outer.bounds == (0, 0, 100, 100)
    assert contours[0].holes[0].bounds == (20, 20, 80, 80)
    assert contours[1].outer.bounds == (35, 35, 65, 65)
    assert contours[1].holes[0].bounds == (45, 45, 55, 55)
    assert not is_clockwise(contours[0].outer)
    assert is_clockwise(contours[0].holes[0])
    assert not is_clockwise(contours[1].outer)
    assert is_clockwise(contours[1].holes[0])


def test_text_generated_o_exports_with_wrap_and_outline_across_edge_types():
    font_path = _find_test_font()
    assert font_path, "No suitable system font found for text generator test"

    contour = TextGenerator().generate_text_contours("O", font_path, 30.0, 0.0)[0]
    engine = SliceEngine()
    writer = STLWriter(wall_thickness=1.2)

    base = SliceParams()
    base.shell.height = 30.0
    base.shell.layer_height = 0.3
    base.shell.wall_thickness = 1.2
    base.shell.wall_count = 1
    base.shell.baseplate_thickness = 5.0
    base.shell.panel_thickness = 5.0
    base.edge_wrap.wrap_enabled = True
    base.edge_wrap.outline_enabled = True
    base.edge_wrap.wrap_direction = EdgeDirection.OUTER
    base.edge_wrap.outline_direction = EdgeDirection.OUTER
    base.edge_wrap.wrap_width = 2.0
    base.edge_wrap.outline_width = 1.0
    base.edge_wrap.outline_height = 1.0

    output_dir = _repo_tmp_dir("text_generator_stl")

    scenarios = []

    straight = deepcopy(base)
    straight.shell.edge_type = EdgeType.STRAIGHT
    scenarios.append(("straight", straight))

    beveled = deepcopy(base)
    beveled.shell.edge_type = EdgeType.BEVELED
    beveled.shell.bevel_direction = BevelDirection.TOP_SMALL
    beveled.shell.bevel_width = 5.0
    scenarios.append(("beveled", beveled))

    custom = deepcopy(base)
    custom.shell.edge_type = EdgeType.CUSTOM
    custom.shell.bevel_width = 5.0
    custom.shell.edge_profile = EdgeProfile.from_control_points([(0.0, 0.0), (1.0, 1.0)])
    scenarios.append(("custom", custom))

    for name, params in scenarios:
        result = engine.slice([contour], params)
        output_path = output_dir / f"{name}.stl"
        writer.write(result, str(output_path), contours=[contour], params=params)
        assert output_path.exists()
        assert output_path.stat().st_size > 0


def _repo_tmp_dir(name: str):
    from pathlib import Path as FsPath

    path = FsPath("e:/SignMaker Slicer/.tmp_pytest_text_generator") / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_text_x_shell_region_mesh_closes_multi_wall_tip_gaps():
    font_path = _find_test_font()
    assert font_path, "No suitable system font found for text generator test"

    contours = TextGenerator().generate_text_contours("X", font_path, 200.0, 20.0)

    params = SliceParams()
    params.shell.height = 0.3
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.wall_thickness = 2.4
    params.shell.wall_count = 4
    params.shell.baseplate_thickness = 0.0
    params.shell.panel_thickness = 0.0
    params.bottom_face.enabled = False
    params.top_face.enabled = False
    params.skirt.enabled = False
    params = normalize_slice_params(params)

    result = SliceEngine().slice(contours, params)
    builder = ShellMeshBuilder(PathOffset(), params.shell.wall_thickness)
    polygons = builder._build_layer_shell_region_polygons(
        contours,
        result.layers[-1],
        params,
    )
    geometry = unary_union(polygons)

    holes = []
    parts = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)
    for part in parts:
        if part.geom_type == "Polygon":
            holes.extend(ShapelyPolygon(ring) for ring in part.interiors)

    assert polygons
    assert [hole for hole in holes if hole.area < 1.0] == []

    mesh = builder.build(result.layers, contours=contours, params=params)

    assert mesh is not None
    assert mesh.is_watertight
