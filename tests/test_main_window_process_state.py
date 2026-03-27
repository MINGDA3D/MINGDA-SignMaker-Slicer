import os
from pathlib import Path as FsPath

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.types import Contour, Path, Point
from src.ui.canvas_2d import Canvas2D
from src.ui.main_window import MainWindow, TUTORIAL_PLAYLIST_URL


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


def _bounds_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    return not (
        first[2] <= second[0]
        or first[0] >= second[2]
        or first[3] <= second[1]
        or first[1] >= second[3]
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


def test_canvas_marks_out_of_bounds_contour_with_error_color(qapp):
    canvas = Canvas2D()
    contour = _rect_contour(-5, 0, 10, 10, "A")

    canvas.set_contours([contour], center_on_platform=False)

    assert canvas.get_out_of_bounds_indices() == [0]

    pen = canvas._get_path_pen(
        is_selected=False,
        is_hole=False,
        is_out_of_bounds=canvas.is_contour_out_of_bounds(contour),
    )
    assert pen.color().name().lower() == canvas.out_of_bounds_color.name().lower()


def test_import_contours_append_without_clearing_existing_canvas(qapp):
    window = MainWindow()

    try:
        window.contours = [_rect_contour(300, 300, 360, 360, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)
        original_bounds = window.contours[0].outer.bounds

        window._load_contours(
            [_rect_contour(0, 0, 40, 20, "B")],
            FsPath("import.svg"),
        )

        assert len(window.contours) == 2
        assert window.contours[0].outer.bounds == original_bounds

        imported_bounds = window.contours[1].outer.bounds
        assert imported_bounds != (0, 0, 40, 20)
        assert not _bounds_overlap(original_bounds, imported_bounds)
        assert window.canvas.selected_indices == [1]
    finally:
        window.close()


def test_text_generation_appends_without_recentering_existing_canvas(qapp, monkeypatch):
    window = MainWindow()

    class _FakeTextDialog:
        def __init__(self, _parent=None):
            self._contours = [_rect_contour(0, 0, 30, 10, "T")]

        def exec(self):
            return True

        def get_contours(self):
            return self._contours

    try:
        window.contours = [_rect_contour(200, 220, 260, 260, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)
        original_bounds = window.contours[0].outer.bounds

        monkeypatch.setattr("src.ui.text_dialog.TextDialog", _FakeTextDialog)

        window._on_text()

        assert len(window.contours) == 2
        assert window.contours[0].outer.bounds == original_bounds

        text_bounds = window.contours[1].outer.bounds
        assert text_bounds != (0, 0, 30, 10)
        assert not _bounds_overlap(original_bounds, text_bounds)
        assert window.canvas.selected_indices == [1]
    finally:
        window.close()


def test_process_blocked_when_contour_exceeds_platform(qapp, monkeypatch):
    window = MainWindow()
    warnings = []
    run_async_calls = []

    try:
        window.contours = [_rect_contour(790, 0, 810, 20, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)

        monkeypatch.setattr(
            "src.ui.main_window.QMessageBox.warning",
            lambda *args, **kwargs: warnings.append((args, kwargs)) or 0,
        )
        monkeypatch.setattr(
            "src.ui.main_window.run_async",
            lambda *args, **kwargs: run_async_calls.append((args, kwargs)),
        )

        window._on_slice()

        assert run_async_calls == []
        assert warnings
        assert warnings[-1][0][1] == window.tr("Processing Blocked")
        assert "platform size" in warnings[-1][0][2]
        assert window.status_label.text() == window.tr(
            "Processing blocked: contours exceed platform size"
        )
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


def test_menu_tutorial_opens_default_browser(qapp, monkeypatch):
    window = MainWindow()
    opened_urls = []

    try:
        monkeypatch.setattr(
            "src.ui.main_window.QDesktopServices.openUrl",
            lambda url: opened_urls.append(url.toString()) or True,
        )

        window._on_menu_action("tutorial")

        assert opened_urls == [TUTORIAL_PLAYLIST_URL]
    finally:
        window.close()
