import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.types import Contour, Path, Point
from src.ui.canvas_2d import Canvas2D


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _rect_contour(x1: float, y1: float, x2: float, y2: float, name: str = "") -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(x1, y1),
                Point(x2, y1),
                Point(x2, y2),
                Point(x1, y2),
            ],
            is_closed=True,
        ),
        name=name,
    )


def test_canvas_boolean_intersection_replaces_selection(qapp):
    canvas = Canvas2D()
    canvas.set_contours(
        [
            _rect_contour(0, 0, 10, 10, "A"),
            _rect_contour(5, 5, 15, 15, "B"),
        ],
        center_on_platform=False,
    )
    canvas.selected_indices = [0, 1]

    canvas.boolean_intersection()

    assert len(canvas.contours) == 1
    assert canvas.selected_indices == [0]
    result = canvas.contours[0]
    assert result.name == "A"
    assert result.holes == []
    assert result.outer.bounds == pytest.approx((5.0, 5.0, 10.0, 10.0))
    assert abs(result.outer.area) == pytest.approx(25.0)


def test_canvas_boolean_difference_rebuilds_hole(qapp):
    canvas = Canvas2D()
    canvas.set_contours(
        [
            _rect_contour(0, 0, 20, 20, "Base"),
            _rect_contour(5, 5, 15, 15, "Cut"),
        ],
        center_on_platform=False,
    )
    canvas.selected_indices = [0, 1]

    canvas.boolean_difference()

    assert len(canvas.contours) == 1
    assert canvas.selected_indices == [0]
    result = canvas.contours[0]
    assert result.name == "Base"
    assert len(result.holes) == 1
    assert abs(result.outer.area) == pytest.approx(400.0)
    assert abs(result.holes[0].area) == pytest.approx(100.0)
