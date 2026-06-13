import pytest

from src.core.slice_engine import SliceEngine
from src.core.types import (
    BevelDirection,
    Contour,
    EdgeDirection,
    EdgeType,
    Layer,
    LayerPath,
    Path,
    PathRole,
    PathType,
    Point,
    SliceParams,
)
from src.ui.preview_3d import Preview3D, Preview3DWidget


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_preview_focus_tracks_model_center(qapp):
    widget = Preview3DWidget()
    widget.set_bed_size(800.0, 1200.0, 100.0)
    widget.set_layers([
        Layer(
            z_height=0.0,
            layer_height=0.3,
            paths=[
                LayerPath(
                    points=[
                        Point(100.0, 200.0),
                        Point(300.0, 200.0),
                        Point(300.0, 400.0),
                        Point(100.0, 400.0),
                    ],
                    role=PathRole.WALL,
                    is_closed=True,
                )
            ],
        )
    ])

    assert widget._get_focus_center() == pytest.approx((200.0, 300.0, 0.15))


def test_preview_zoom_limit_shrinks_for_large_models(qapp):
    widget = Preview3DWidget()
    widget.set_bed_size(800.0, 1200.0, 100.0)
    widget.set_layers([
        Layer(
            z_height=0.0,
            layer_height=0.3,
            paths=[
                LayerPath(
                    points=[
                        Point(50.0, 50.0),
                        Point(650.0, 50.0),
                        Point(650.0, 650.0),
                        Point(50.0, 650.0),
                    ],
                    role=PathRole.WALL,
                    is_closed=True,
                )
            ],
        )
    ])

    widget.zoom = 50.0
    widget._clamp_zoom_in_place()

    assert widget.zoom < 10.0


def test_preview_top_view_uses_non_parallel_up_vector(qapp):
    widget = Preview3DWidget()
    focus_center = (400.0, 600.0, 0.0)
    camera_pos = (400.0, 600.0, 500.0)

    up_x, up_y, up_z = widget._get_camera_up_vector(camera_pos, focus_center)
    dot = up_x * 0.0 + up_y * 0.0 + up_z * -1.0

    assert (up_x, up_y, up_z) == pytest.approx((0.0, 1.0, 0.0))
    assert abs(dot) < 1e-6


def test_preview_emphasizes_step_like_roles_as_ribbons(qapp):
    widget = Preview3DWidget()

    assert widget._should_draw_ribbon(
        LayerPath(role=PathRole.STEP, line_width=3.0)
    ) is True
    assert widget._should_draw_ribbon(
        LayerPath(role=PathRole.CONNECTED, line_width=8.0)
    ) is True
    assert widget._should_draw_ribbon(
        LayerPath(role=PathRole.WALL, line_width=1.2)
    ) is False


def test_preview_lifts_special_paths_above_wall_plane(qapp):
    widget = Preview3DWidget()
    layer_height = 0.3

    wall_z = widget._get_render_z(
        0.0,
        layer_height,
        LayerPath(role=PathRole.WALL, line_width=1.2),
    )
    step_z = widget._get_render_z(
        0.0,
        layer_height,
        LayerPath(role=PathRole.STEP, line_width=3.0),
    )

    assert wall_z > 0.0
    assert step_z > wall_z


def test_preview_layer_controls_show_z_height_not_layer_numbers(qapp):
    preview = Preview3D()

    preview.set_layers([
        Layer(z_height=0.0, layer_height=0.3),
        Layer(z_height=0.3, layer_height=0.3),
    ])

    assert preview.layer_current_label.text() == "Z 0.60 mm"
    assert preview.layer_total_label.text() == "/ 0.60 mm"

    preview.layer_slider.setValue(0)

    assert preview.layer_current_label.text() == "Z 0.30 mm"
    assert preview.layer_total_label.text() == "/ 0.60 mm"


def test_preview_uses_one_color_for_wall_like_roles(qapp):
    widget = Preview3DWidget()

    wall_color = widget._get_path_color(LayerPath(role=PathRole.WALL), 1.0)
    panel_fill_color = widget._get_path_color(LayerPath(role=PathRole.FILL_PANEL), 1.0)
    top_face_color = widget._get_path_color(LayerPath(role=PathRole.FILL_TOP_FACE), 1.0)
    step_color = widget._get_path_color(LayerPath(role=PathRole.STEP), 1.0)

    assert panel_fill_color == wall_color
    assert top_face_color == wall_color
    assert step_color != wall_color


def test_preview_builds_solid_mesh_parts_for_step_and_connected(qapp):
    contour1 = Contour(
        outer=Path(points=[
            Point(0.0, 0.0),
            Point(20.0, 0.0),
            Point(20.0, 20.0),
            Point(0.0, 20.0),
        ])
    )
    contour2 = Contour(
        outer=Path(points=[
            Point(30.0, 0.0),
            Point(50.0, 0.0),
            Point(50.0, 20.0),
            Point(30.0, 20.0),
        ])
    )

    params = SliceParams()
    params.shell.height = 10.0
    params.shell.layer_height = 1.0
    params.machine.nozzle_diameter = 1.0
    params.step.panel_step_enabled = True
    params.step.panel_step_height = 3.0
    params.step.panel_step_width = 3.0
    params.connected.enabled = True
    params.connected.width = 10.0
    params.connected.height = 3.0
    params.connected.base_height = 3.0
    params.skirt.enabled = True

    result = SliceEngine().slice([contour1, contour2], params)

    widget = Preview3DWidget()
    widget.set_slice_result(result, [contour1, contour2], params)

    names = {part.name for part in widget.mesh_parts}
    assert "wall" in names
    assert "step" in names
    assert "connected" in names
    assert "skirt" in names


def _distance_to_rect_xy(x, y, rect):
    left, bottom, right, top = rect
    if left <= x <= right and bottom <= y <= top:
        return min(x - left, right - x, y - bottom, top - y)
    dx = max(left - x, 0.0, x - right)
    dy = max(bottom - y, 0.0, y - top)
    return (dx * dx + dy * dy) ** 0.5


def test_preview_skirt_mesh_respects_breakaway_gap_from_wall(qapp):
    contour = Contour(
        outer=Path(points=[
            Point(0.0, 0.0),
            Point(40.0, 0.0),
            Point(40.0, 20.0),
            Point(0.0, 20.0),
        ])
    )

    params_no_gap = SliceParams()
    params_no_gap.shell.height = 10.0
    params_no_gap.shell.layer_height = 1.0
    params_no_gap.machine.nozzle_diameter = 1.0
    params_no_gap.skirt.enabled = True
    params_no_gap.skirt.offset = 0.0

    params_gap = SliceParams()
    params_gap.shell.height = 10.0
    params_gap.shell.layer_height = 1.0
    params_gap.machine.nozzle_diameter = 1.0
    params_gap.skirt.enabled = True
    params_gap.skirt.offset = 0.1

    result_no_gap = SliceEngine().slice([contour], params_no_gap)
    result_gap = SliceEngine().slice([contour], params_gap)

    parts_no_gap = Preview3DWidget.build_mesh_parts_for_result(result_no_gap, [contour], params_no_gap)
    parts_gap = Preview3DWidget.build_mesh_parts_for_result(result_gap, [contour], params_gap)

    skirt_no_gap = next(part for part in parts_no_gap if part.name == "skirt")
    skirt_gap = next(part for part in parts_gap if part.name == "skirt")

    no_gap_distance = min(
        _distance_to_rect_xy(vertex[0], vertex[1], (0.0, 0.0, 40.0, 20.0))
        for vertex in skirt_no_gap.vertices
    )
    gap_distance = min(
        _distance_to_rect_xy(vertex[0], vertex[1], (0.0, 0.0, 40.0, 20.0))
        for vertex in skirt_gap.vertices
    )

    assert no_gap_distance == pytest.approx(0.0, abs=1e-6)
    assert gap_distance == pytest.approx(0.1, abs=1e-4)


def test_preview_builds_wrap_and_outline_on_bottom_reference(qapp):
    contour = Contour(
        outer=Path(
            points=[
                Point(0.0, 0.0),
                Point(100.0, 0.0),
                Point(100.0, 100.0),
                Point(0.0, 100.0),
            ],
            path_type=PathType.OUTER,
            is_closed=True,
        )
    )

    params = SliceParams()
    params.shell.height = 30.0
    params.shell.layer_height = 1.0
    params.machine.nozzle_diameter = 1.0
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_SMALL
    params.shell.bevel_width = 5.0
    params.shell.baseplate_thickness = 5.0
    params.shell.panel_thickness = 5.0
    params.edge_wrap.wrap_enabled = True
    params.edge_wrap.wrap_width = 2.0
    params.edge_wrap.wrap_height = 3.0
    params.edge_wrap.wrap_direction = EdgeDirection.OUTER
    params.edge_wrap.outline_enabled = True
    params.edge_wrap.outline_width = 1.0
    params.edge_wrap.outline_height = 2.0
    params.edge_wrap.outline_direction = EdgeDirection.OUTER

    result = SliceEngine().slice([contour], params)

    parts = Preview3DWidget.build_mesh_parts_for_result(result, [contour], params)
    part_map = {part.name: part for part in parts}

    assert "wrap" in part_map
    assert "outline" in part_map
    assert part_map["wrap"].vertices[:, 0].min() == pytest.approx(-2.0, abs=1e-6)
    assert part_map["wrap"].vertices[:, 0].max() == pytest.approx(102.0, abs=1e-6)
    assert part_map["wrap"].vertices[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert part_map["wrap"].vertices[:, 2].max() == pytest.approx(3.0, abs=1e-6)
    assert part_map["outline"].vertices[:, 0].min() == pytest.approx(-1.0, abs=1e-6)
    assert part_map["outline"].vertices[:, 0].max() == pytest.approx(101.0, abs=1e-6)
    assert part_map["outline"].vertices[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert part_map["outline"].vertices[:, 2].max() == pytest.approx(2.0, abs=1e-6)


def test_preview_builds_light_slot_mesh_part(qapp):
    contour = Contour(
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

    params = SliceParams()
    params.shell.height = 10.0
    params.shell.layer_height = 1.0
    params.machine.nozzle_diameter = 1.0
    params.light_slot.enabled = True
    params.light_slot.width = 8.0
    params.light_slot.depth = 3.0

    result = SliceEngine().slice([contour], params)

    parts = Preview3DWidget.build_mesh_parts_for_result(result, [contour], params)
    part_map = {part.name: part for part in parts}

    assert "light_slot" in part_map
    assert part_map["light_slot"].vertices[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert part_map["light_slot"].vertices[:, 2].max() == pytest.approx(3.0, abs=1e-6)
