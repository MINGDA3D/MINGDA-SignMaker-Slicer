import os

import pytest
from PySide6.QtCore import QPointF

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.types import Contour, Path, Point
from src.ui.canvas_2d import Canvas2D
from src.ui.main_window import MainWindow


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


def test_canvas_click_selects_entire_group(qapp):
    canvas = Canvas2D()
    contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
        _rect_contour(40, 0, 50, 10, "C"),
    ]
    contours[0].group_id = "g1"
    contours[1].group_id = "g1"
    canvas.set_contours(contours, center_on_platform=False)

    canvas._handle_selection(canvas._world_to_screen(QPointF(1, 1)))

    assert canvas.selected_indices == [0, 1]


def test_main_window_group_and_ungroup_support_undo(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
        _rect_contour(40, 0, 50, 10, "C"),
    ]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.canvas.selected_indices = [0, 1]

    window._on_group()

    grouped_id = window.contours[0].group_id
    assert grouped_id
    assert window.contours[1].group_id == grouped_id
    assert window.contours[2].group_id == ""

    window._on_undo()
    assert [contour.group_id for contour in window.contours] == ["", "", ""]

    window._on_redo()
    assert window.contours[0].group_id == grouped_id
    assert window.contours[1].group_id == grouped_id

    window.canvas.selected_indices = [0]
    window._on_ungroup()
    assert [contour.group_id for contour in window.contours] == ["", "", ""]

    window._on_undo()
    assert window.contours[0].group_id == grouped_id
    assert window.contours[1].group_id == grouped_id

    window.close()
