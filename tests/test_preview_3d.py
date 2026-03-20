import pytest

from src.core.types import Layer, LayerPath, PathRole, Point
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
