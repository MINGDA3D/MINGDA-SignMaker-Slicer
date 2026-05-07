from pathlib import Path as FilePath

import pytest
from shapely.geometry import Point as ShapelyPoint
from shapely.ops import unary_union

from src.core.path_offset import PathOffset
from src.core.stl.top_face_mesh import TopFaceMeshBuilder
from src.core.svg_parser import SVGParser
from src.core.top_face_geometry import TopFaceGeometryBuilder
from src.core.types import Contour, Path, PathType, Point, SliceParams


def _rect_path(x1: float, y1: float, x2: float, y2: float, path_type: PathType) -> Path:
    return Path(
        points=[
            Point(x1, y1),
            Point(x2, y1),
            Point(x2, y2),
            Point(x1, y2),
        ],
        path_type=path_type,
        is_closed=True,
    )


def _top_face_params(
    *,
    layer_height: float = 1.0,
    wall_thickness: float = 2.0,
    top_thickness: float = 2.0,
) -> SliceParams:
    params = SliceParams()
    params.shell.height = 10.0
    params.shell.layer_height = layer_height
    params.shell.wall_thickness = wall_thickness
    params.shell.wall_count = 1
    params.top_face.enabled = True
    params.top_face.thickness = top_thickness
    return params


def test_top_face_geometry_preserves_existing_inner_holes():
    contour = Contour(
        outer=_rect_path(0.0, 0.0, 100.0, 60.0, PathType.OUTER),
        holes=[_rect_path(49.0, 29.0, 51.0, 31.0, PathType.HOLE)],
    )
    params = _top_face_params()

    geometry = TopFaceGeometryBuilder(PathOffset()).build(contour, params)
    fill_region = unary_union(geometry.fill_polygons)

    assert geometry.fill_polygons
    assert not fill_region.covers(ShapelyPoint(50.0, 30.0))
    assert fill_region.area == pytest.approx((96.0 * 56.0) - 4.0)


def test_docs_1_02_top_face_mesh_keeps_letter_holes_open():
    docs_svg = FilePath(__file__).resolve().parents[1] / "docs" / "1-02.svg"
    contours = SVGParser().parse(str(docs_svg))
    solid_contours = [Contour(outer=contour.outer, holes=[]) for contour in contours]
    expected_hole_volume = (
        sum(abs(hole.area) for contour in contours for hole in contour.holes)
        * 0.3
    )
    params = _top_face_params(
        layer_height=0.3,
        wall_thickness=1.2,
        top_thickness=0.3,
    )

    builder = TopFaceMeshBuilder(PathOffset())
    solid_mesh = builder.build(solid_contours, params)
    mesh_with_holes = builder.build(contours, params)

    assert expected_hole_volume > 0.0
    assert solid_mesh is not None
    assert mesh_with_holes is not None
    assert solid_mesh.volume - mesh_with_holes.volume == pytest.approx(
        expected_hole_volume,
        rel=1e-3,
        abs=1e-3,
    )
