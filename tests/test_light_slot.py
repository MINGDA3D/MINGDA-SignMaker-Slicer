import pytest

from src.core.edge_presets import EdgePresetManager
from src.core.light_slot_geometry import LightSlotGeometryBuilder
from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl.light_slot_mesh import LightSlotMeshBuilder
from src.core.types import Contour, EdgeProfile, EdgeType, BevelDirection, Path, PathRole, PathType, Point, SliceParams


def _build_outer_with_hole():
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


def _default_params():
    params = SliceParams()
    params.shell.height = 10.0
    params.shell.layer_height = 1.0
    params.shell.wall_thickness = 1.2
    params.shell.wall_count = 1
    params.light_slot.enabled = True
    params.light_slot.width = 8.0
    params.light_slot.depth = 3.0
    params.light_slot.wall_gap = 0.0
    params.light_slot.outer_enabled = True
    params.light_slot.hole_enabled = True
    params.light_slot.auto_skip_small_holes = True
    params.light_slot.min_hole_span = 12.0
    return params


def test_light_slot_geometry_expands_outer_inward_and_hole_outward():
    contour = _build_outer_with_hole()
    params = _default_params()

    geometry = LightSlotGeometryBuilder(PathOffset()).build(contour, params)
    bounds = sorted(path.bounds for path in geometry.slot_free_edge_paths)

    assert len(bounds) == 2
    assert bounds[0] == pytest.approx((9.2, 9.2, 90.8, 90.8), abs=1e-6)
    assert bounds[1] == pytest.approx((22.0, 22.0, 78.0, 78.0), abs=1e-6)

    hole_slot_polygon = next(
        polygon for polygon in geometry.slot_band_polygons
        if len(polygon.interiors) == 1 and polygon.bounds[0] > 10.0
    )
    assert hole_slot_polygon.bounds == pytest.approx((22.0, 22.0, 78.0, 78.0), abs=1e-6)
    assert hole_slot_polygon.interiors[0].bounds == pytest.approx((30.0, 30.0, 70.0, 70.0), abs=1e-6)


def test_light_slot_auto_skips_small_holes():
    contour = Contour(
        outer=_build_outer_with_hole().outer,
        holes=[
            Path(
                points=[
                    Point(40.0, 40.0),
                    Point(48.0, 40.0),
                    Point(48.0, 48.0),
                    Point(40.0, 48.0),
                ],
                path_type=PathType.HOLE,
                is_closed=True,
            )
        ],
    )
    params = _default_params()

    geometry = LightSlotGeometryBuilder(PathOffset()).build(contour, params)

    assert len(geometry.slot_free_edge_paths) == 1
    assert geometry.slot_free_edge_paths[0].bounds == pytest.approx(
        (9.2, 9.2, 90.8, 90.8),
        abs=1e-6,
    )


def test_slice_generates_light_slot_only_on_bottom_layers():
    contour = _build_outer_with_hole()
    params = _default_params()
    result = SliceEngine().slice([contour], params)

    light_slot_by_layer = []
    for layer in result.layers:
        layer_paths = [path for path in layer.paths if path.role == PathRole.LIGHT_SLOT]
        light_slot_by_layer.append((layer.z_height, layer_paths))

    assert [z for z, paths in light_slot_by_layer if paths] == pytest.approx([0.0, 1.0, 2.0])

    first_layer_paths = light_slot_by_layer[0][1]
    assert any(path.is_closed for path in first_layer_paths)
    assert any(not path.is_closed for path in first_layer_paths)

    for _, layer_paths in light_slot_by_layer[1:3]:
        assert layer_paths
        assert all(path.is_closed for path in layer_paths)


def test_bottom_face_and_light_slot_coexist_without_covering_slot_band():
    contour = _build_outer_with_hole()
    params = _default_params()
    params.bottom_face.enabled = True
    params.bottom_face.thickness = 2.0

    result = SliceEngine().slice([contour], params)
    first_layer = result.layers[0]

    light_slot_paths = [path for path in first_layer.paths if path.role == PathRole.LIGHT_SLOT]
    bottom_face_paths = [path for path in first_layer.paths if path.role == PathRole.FILL_BOTTOM_FACE]

    assert light_slot_paths
    assert bottom_face_paths

    all_bottom_face_points = [point for path in bottom_face_paths for point in path.points]
    assert all(point.x >= 9.19 for point in all_bottom_face_points)
    assert all(point.x <= 90.81 for point in all_bottom_face_points)
    assert all(point.y >= 9.19 for point in all_bottom_face_points)
    assert all(point.y <= 90.81 for point in all_bottom_face_points)


def test_light_slot_mesh_builder_uses_requested_depth():
    contour = _build_outer_with_hole()
    params = _default_params()

    mesh = LightSlotMeshBuilder(PathOffset()).build([contour], params)

    assert mesh is not None
    assert mesh.vertices[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert mesh.vertices[:, 2].max() == pytest.approx(3.0, abs=1e-6)


@pytest.mark.parametrize(
    ("configure", "expected_outer", "expected_hole", "expected_slot_bounds"),
    [
        (
            lambda p: setattr(p.shell, "edge_type", EdgeType.STRAIGHT),
            (0.0, 0.0, 100.0, 100.0),
            (30.0, 30.0, 70.0, 70.0),
            [(9.2, 9.2, 90.8, 90.8), (22.0, 22.0, 78.0, 78.0)],
        ),
        (
            lambda p: (
                setattr(p.shell, "edge_type", EdgeType.BEVELED),
                setattr(p.shell, "bevel_direction", BevelDirection.TOP_LARGE),
                setattr(p.shell, "bevel_width", 5.0),
                setattr(p.shell, "baseplate_thickness", 10.0),
                setattr(p.shell, "panel_thickness", 3.0),
            ),
            (0.0, 0.0, 100.0, 100.0),
            (30.0, 30.0, 70.0, 70.0),
            [(9.2, 9.2, 90.8, 90.8), (22.0, 22.0, 78.0, 78.0)],
        ),
        (
            lambda p: (
                setattr(p.shell, "edge_type", EdgeType.CUSTOM),
                setattr(p.shell, "bevel_width", 6.0),
                setattr(
                    p.shell,
                    "edge_profile",
                    EdgeProfile.from_control_points([(0.2, 0.0), (0.5, 0.35), (1.0, 1.0)]),
                ),
            ),
            (-1.2, -1.2, 101.2, 101.2),
            (28.8, 28.8, 71.2, 71.2),
            [(8.0, 8.0, 92.0, 92.0), (20.8, 20.8, 79.2, 79.2)],
        ),
    ],
)
def test_light_slot_aligns_with_bottom_reference_for_edge_types(
    configure,
    expected_outer,
    expected_hole,
    expected_slot_bounds,
):
    contour = _build_outer_with_hole()
    params = _default_params()
    configure(params)

    engine = SliceEngine()
    bottom_contour = engine._apply_edge_profile(contour, 0.0, params.shell)
    assert bottom_contour is not None
    assert bottom_contour.outer.bounds == pytest.approx(expected_outer, abs=1e-6)
    assert bottom_contour.holes[0].bounds == pytest.approx(expected_hole, abs=1e-6)

    geometry = LightSlotGeometryBuilder(PathOffset()).build(bottom_contour, params)
    actual_slot_bounds = sorted(path.bounds for path in geometry.slot_free_edge_paths)

    assert actual_slot_bounds == pytest.approx(expected_slot_bounds, abs=1e-6)


def test_light_slot_supports_preset_custom_edge_profiles():
    profile = EdgePresetManager().get_preset_profile("arc_single")
    assert profile is not None

    contour = _build_outer_with_hole()
    params = _default_params()
    params.shell.edge_type = EdgeType.CUSTOM
    params.shell.edge_profile = profile
    params.shell.bevel_width = profile.original_width

    bottom_contour = SliceEngine()._apply_edge_profile(contour, 0.0, params.shell)
    assert bottom_contour is not None

    mesh = LightSlotMeshBuilder(PathOffset()).build([bottom_contour], params)
    assert mesh is not None
    assert mesh.vertices[:, 2].max() == pytest.approx(3.0, abs=1e-6)
