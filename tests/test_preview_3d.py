import pytest

from src.core.slice_engine import SliceEngine
from src.core.types import (
    Contour,
    Layer,
    LayerPath,
    Path,
    PathRole,
    Point,
    SliceParams,
)
from src.ui.preview_3d import Preview3DWidget


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
