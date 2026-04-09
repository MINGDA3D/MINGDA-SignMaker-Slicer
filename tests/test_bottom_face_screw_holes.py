import pytest

from src.core.bottom_face_geometry import BottomFaceGeometryBuilder
from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl.bottom_face_mesh import BottomFaceMeshBuilder
from src.core.types import (
    Contour,
    Path,
    PathRole,
    PathType,
    Point,
    SliceParams,
)


def _rect_contour(x1: float, y1: float, x2: float, y2: float) -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(x1, y1),
                Point(x2, y1),
                Point(x2, y2),
                Point(x1, y2),
            ],
            path_type=PathType.OUTER,
            is_closed=True,
        )
    )


def _bottom_face_params() -> SliceParams:
    params = SliceParams()
    params.shell.height = 10.0
    params.shell.layer_height = 1.0
    params.shell.wall_thickness = 1.2
    params.shell.wall_count = 1
    params.bottom_face.enabled = True
    params.bottom_face.thickness = 2.0
    params.bottom_face.screw_hole_diameter = 4.0
    return params


def test_bottom_face_geometry_subtracts_valid_manual_screw_hole():
    contour = _rect_contour(0.0, 0.0, 100.0, 60.0)
    contour.screw_hole_centers = [Point(50.0, 30.0)]
    params = _bottom_face_params()

    geometry = BottomFaceGeometryBuilder(PathOffset()).build(contour, params)

    assert len(geometry.valid_holes) == 1
    assert len(geometry.invalid_holes) == 0
    assert len(geometry.hole_boundary_paths) == 1
    assert sum(len(polygon.interiors) for polygon in geometry.fill_polygons) == 1


def test_bottom_face_geometry_marks_holes_outside_slot_free_region_invalid():
    contour = _rect_contour(0.0, 0.0, 100.0, 100.0)
    contour.screw_hole_centers = [Point(8.0, 50.0)]
    params = _bottom_face_params()
    params.light_slot.enabled = True
    params.light_slot.width = 8.0
    params.light_slot.depth = 3.0
    params.light_slot.floor_layers = 2
    params.light_slot.wall_gap = 0.0
    params.light_slot.outer_enabled = True
    params.light_slot.hole_enabled = False

    geometry = BottomFaceGeometryBuilder(PathOffset()).build(contour, params)

    assert len(geometry.valid_holes) == 0
    assert len(geometry.invalid_holes) == 1
    assert len(geometry.hole_boundary_paths) == 0


def test_slice_engine_emits_bottom_face_hole_boundary_paths():
    contour = _rect_contour(0.0, 0.0, 100.0, 60.0)
    contour.screw_hole_centers = [Point(50.0, 30.0)]
    params = _bottom_face_params()

    result = SliceEngine().slice([contour], params)
    first_layer = result.layers[0]
    bottom_face_paths = [
        path for path in first_layer.paths if path.role == PathRole.FILL_BOTTOM_FACE
    ]

    assert any(path.is_closed for path in bottom_face_paths)


def test_bottom_face_mesh_volume_decreases_when_screw_hole_is_added():
    solid_contour = _rect_contour(0.0, 0.0, 100.0, 60.0)
    hole_contour = _rect_contour(0.0, 0.0, 100.0, 60.0)
    hole_contour.screw_hole_centers = [Point(50.0, 30.0)]
    params = _bottom_face_params()

    builder = BottomFaceMeshBuilder(PathOffset())
    solid_mesh = builder.build([solid_contour], params)
    hole_mesh = builder.build([hole_contour], params)

    assert solid_mesh is not None
    assert hole_mesh is not None
    assert solid_mesh.volume > hole_mesh.volume
    assert solid_mesh.vertices[:, 2].max() == pytest.approx(2.0, abs=1e-6)
    assert hole_mesh.vertices[:, 2].max() == pytest.approx(2.0, abs=1e-6)
