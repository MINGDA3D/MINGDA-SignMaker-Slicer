import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.types import Contour, Path, Point
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


def _mark_processed(window: MainWindow) -> None:
    window.slice_result = object()
    window._sync_export_stl_state()


def test_export_requires_reprocess_after_param_change(qapp, monkeypatch):
    window = MainWindow()
    messages = []

    try:
        _mark_processed(window)
        assert window.title_bar.btn_export_stl.isEnabled() is True

        monkeypatch.setattr(
            "src.ui.main_window.QMessageBox.information",
            lambda *args, **kwargs: messages.append((args, kwargs)) or 0,
        )

        window.param_panel.height_spin.setValue(window.param_panel.height_spin.value() + 1.0)

        assert window.slice_result is None
        assert window.title_bar.btn_export_stl.isEnabled() is True

        window.title_bar.btn_export_stl.click()

        assert messages
        assert messages[-1][0][2] == window.tr("Please process first")
    finally:
        window.close()


def test_manual_contour_move_invalidates_processed_result(qapp):
    window = MainWindow()

    try:
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.canvas.set_selected_indices([0])
        _mark_processed(window)

        window.canvas.move_selected(5.0, 0.0)

        assert window.slice_result is None
        assert window.title_bar.btn_export_stl.isEnabled() is True
    finally:
        window.close()


def test_delete_invalidates_processed_result(qapp):
    window = MainWindow()

    try:
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)
        _mark_processed(window)

        window._on_delete_requested([0])

        assert window.contours == []
        assert window.slice_result is None
        assert window.title_bar.btn_export_stl.isEnabled() is True
    finally:
        window.close()


def test_preview_auto_processes_when_contours_exist_and_result_missing(qapp, monkeypatch):
    window = MainWindow()
    calls = []

    try:
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)

        monkeypatch.setattr(window, "_on_slice", lambda: calls.append("slice"))

        window._on_nav_changed("preview")

        assert calls == ["slice"]
        assert window.current_main_view == "editor"
        assert window.current_view == "3d"
    finally:
        window.close()


def test_preview_does_not_auto_process_without_contours(qapp, monkeypatch):
    window = MainWindow()
    calls = []
    preview_prepared = []

    try:
        monkeypatch.setattr(window, "_on_slice", lambda: calls.append("slice"))
        monkeypatch.setattr(
            "src.ui.main_window.QTimer.singleShot",
            lambda _delay, callback: preview_prepared.append(callback.__name__),
        )

        window._on_nav_changed("preview")

        assert calls == []
        assert preview_prepared == ["_prepare_preview_3d"]
        assert window.current_main_view == "editor"
        assert window.current_view == "3d"
    finally:
        window.close()
