import os
import shutil
import uuid
from pathlib import Path as FsPath

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.types import Contour, Path, Point
from src.ui.canvas_2d import Canvas2D
from src.ui.main_window import MainWindow, TUTORIAL_PLAYLIST_URL
from src.ui.title_bar import TitleBar
from src.ui.widgets import GuardedDoubleSpinBox
from PySide6.QtWidgets import QMessageBox


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def workspace_tmp_dir():
    tmpdir = FsPath.cwd() / f".tmp_main_window_state_{uuid.uuid4().hex}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


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


def _rect_contour_with_hole(
    outer_x1: float,
    outer_y1: float,
    outer_x2: float,
    outer_y2: float,
    hole_x1: float,
    hole_y1: float,
    hole_x2: float,
    hole_y2: float,
    name: str = "",
) -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(outer_x1, outer_y1),
                Point(outer_x2, outer_y1),
                Point(outer_x2, outer_y2),
                Point(outer_x1, outer_y2),
            ],
            is_closed=True,
        ),
        holes=[
            Path(
                points=[
                    Point(hole_x1, hole_y1),
                    Point(hole_x2, hole_y1),
                    Point(hole_x2, hole_y2),
                    Point(hole_x1, hole_y2),
                ],
                is_closed=True,
            )
        ],
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
        window.deleteLater()


def test_transform_panel_uses_guarded_spinboxes(qapp):
    window = MainWindow()

    try:
        assert isinstance(window.transform_x, GuardedDoubleSpinBox)
        assert isinstance(window.transform_y, GuardedDoubleSpinBox)
        assert isinstance(window.transform_angle, GuardedDoubleSpinBox)
        assert isinstance(window.scale_x_pct, GuardedDoubleSpinBox)
        assert isinstance(window.scale_y_pct, GuardedDoubleSpinBox)
        assert isinstance(window.scale_w, GuardedDoubleSpinBox)
        assert isinstance(window.scale_h, GuardedDoubleSpinBox)
    finally:
        window.deleteLater()


def test_default_gcode_export_filename_includes_profile_name_and_sanitizes_invalid_chars(qapp):
    window = MainWindow()

    try:
        window.current_file = r"E:\workspace\sample_project.smp"

        default_name = window._build_default_gcode_filename('MIGNDA AD/F4 0.6mm:Nozzle')

        assert default_name == "sample_project - MIGNDA AD_F4 0.6mm_Nozzle.gcode"
    finally:
        window.deleteLater()


def test_title_bar_primary_export_button_tracks_selected_format(qapp):
    title_bar = TitleBar()
    changed_formats = []
    triggered = []

    try:
        title_bar.export_format_changed.connect(changed_formats.append)
        title_bar.export_gcode_clicked.connect(lambda: triggered.append("gcode"))
        title_bar.export_stl_clicked.connect(lambda: triggered.append("stl"))

        assert title_bar.get_primary_export_format() == TitleBar.EXPORT_GCODE
        title_bar.btn_export_stl.click()
        assert triggered == ["gcode"]

        title_bar._export_stl_action.trigger()

        assert changed_formats == ["stl"]
        assert triggered == ["gcode"]
        assert title_bar.get_primary_export_format() == TitleBar.EXPORT_STL

        title_bar.btn_export_stl.click()
        assert triggered[-1] == "stl"
    finally:
        title_bar.deleteLater()


def test_primary_export_selection_persists_across_main_window_instances(
    qapp, monkeypatch, workspace_tmp_dir
):
    from src.business.settings_manager import init_settings_manager as real_init_settings_manager

    settings_dir = workspace_tmp_dir / "config"
    messages = []

    monkeypatch.setattr(
        "src.ui.main_window.init_settings_manager",
        lambda: real_init_settings_manager(str(settings_dir)),
    )
    monkeypatch.setattr(
        "src.ui.main_window.QMessageBox.information",
        lambda *args, **kwargs: messages.append((args, kwargs)) or 0,
    )

    first_window = MainWindow()

    try:
        assert first_window.title_bar.get_primary_export_format() == TitleBar.EXPORT_GCODE

        first_window.title_bar._export_stl_action.trigger()

        assert first_window.settings_manager.get_primary_export_format() == TitleBar.EXPORT_STL
        assert first_window.title_bar.get_primary_export_format() == TitleBar.EXPORT_STL
        assert messages == []

        first_window.title_bar.btn_export_stl.click()

        assert messages
        assert messages[-1][0][2] == first_window.tr("Please process first")
    finally:
        first_window.deleteLater()

    second_window = MainWindow()

    try:
        assert second_window.settings_manager.get_primary_export_format() == TitleBar.EXPORT_STL
        assert second_window.title_bar.get_primary_export_format() == TitleBar.EXPORT_STL
    finally:
        second_window.deleteLater()


def test_save_project_blocked_when_canvas_has_no_graphics(qapp, monkeypatch):
    window = MainWindow()
    messages = []
    save_as_calls = []

    try:
        monkeypatch.setattr(
            "src.ui.main_window.QMessageBox.information",
            lambda *args, **kwargs: messages.append((args, kwargs)) or 0,
        )
        monkeypatch.setattr(
            window,
            "_on_save_as",
            lambda: save_as_calls.append(True),
        )

        window._on_save_project()

        assert save_as_calls == []
        assert messages
        assert messages[-1][0][2] == window.tr("Please import or create graphics before saving")
    finally:
        window.deleteLater()


def test_close_confirmation_uses_custom_translated_buttons(qapp, monkeypatch):
    window = MainWindow()
    captured = {}

    try:
        def _fake_exec(message_box):
            captured["texts"] = {button.text() for button in message_box.buttons()}
            captured["default"] = message_box.defaultButton().text()
            captured["escape"] = message_box.escapeButton().text()
            return 0

        monkeypatch.setattr("src.ui.main_window.QMessageBox.exec", _fake_exec)

        assert window._confirm_close_with_unsaved_changes() == QMessageBox.StandardButton.Cancel
        assert captured["texts"] == {
            window.tr("Save"),
            window.tr("Discard"),
            window.tr("Cancel"),
        }
        assert captured["default"] == window.tr("Save")
        assert captured["escape"] == window.tr("Cancel")
    finally:
        window.deleteLater()


def test_close_with_unsaved_changes_saves_current_project(qapp, monkeypatch, workspace_tmp_dir):
    window = MainWindow()
    saved_paths = []

    try:
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.param_panel.height_spin.setValue(window.param_panel.height_spin.value() + 1.0)
        project_path = workspace_tmp_dir / "dirty_project.smp"
        window.current_file = str(project_path)

        monkeypatch.setattr(
            window,
            "_confirm_close_with_unsaved_changes",
            lambda: QMessageBox.StandardButton.Save,
        )

        def _fake_save(file_path: str) -> bool:
            saved_paths.append(file_path)
            window._set_project_save_point()
            return True

        monkeypatch.setattr(window, "_save_project", _fake_save)

        assert window._handle_unsaved_changes_before_close() is True
        assert saved_paths == [str(project_path)]
    finally:
        window.deleteLater()


def test_close_with_unsaved_changes_uses_save_as_for_non_project_path(qapp, monkeypatch):
    window = MainWindow()
    save_as_calls = []

    try:
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.param_panel.height_spin.setValue(window.param_panel.height_spin.value() + 1.0)
        window.current_file = "import.svg"

        monkeypatch.setattr(
            window,
            "_confirm_close_with_unsaved_changes",
            lambda: QMessageBox.StandardButton.Save,
        )

        def _fake_save_as() -> None:
            save_as_calls.append(True)
            window._set_project_save_point()

        monkeypatch.setattr(window, "_on_save_as", _fake_save_as)

        assert window._handle_unsaved_changes_before_close() is True
        assert save_as_calls == [True]
    finally:
        window.deleteLater()


def test_close_with_unsaved_changes_can_cancel_exit(qapp, monkeypatch):
    window = MainWindow()
    save_calls = []

    try:
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.param_panel.height_spin.setValue(window.param_panel.height_spin.value() + 1.0)

        monkeypatch.setattr(
            window,
            "_confirm_close_with_unsaved_changes",
            lambda: QMessageBox.StandardButton.Cancel,
        )
        monkeypatch.setattr(
            window,
            "_save_project",
            lambda *_args, **_kwargs: save_calls.append(True) or True,
        )

        assert window._handle_unsaved_changes_before_close() is False
        assert save_calls == []
    finally:
        window._set_project_save_point()
        window.deleteLater()


def test_close_with_unsaved_changes_can_discard_exit(qapp, monkeypatch):
    window = MainWindow()
    save_calls = []

    try:
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.param_panel.height_spin.setValue(window.param_panel.height_spin.value() + 1.0)

        monkeypatch.setattr(
            window,
            "_confirm_close_with_unsaved_changes",
            lambda: QMessageBox.StandardButton.Discard,
        )
        monkeypatch.setattr(
            window,
            "_save_project",
            lambda *_args, **_kwargs: save_calls.append(True) or True,
        )

        assert window._handle_unsaved_changes_before_close() is True
        assert save_calls == []
    finally:
        window.deleteLater()


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
        window.deleteLater()


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
        window.deleteLater()


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
        assert window.current_transform_mode == "move"
        assert window.canvas_toolbar.current_tool == "move"
        assert window.canvas_toolbar.btn_move.isChecked() is True
        assert window.canvas.current_tool == "move"
    finally:
        window.deleteLater()


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
        assert window.current_transform_mode == "move"
        assert window.canvas_toolbar.current_tool == "move"
        assert window.canvas_toolbar.btn_move.isChecked() is True
        assert window.canvas.current_tool == "move"
    finally:
        window.deleteLater()


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
        window.deleteLater()


def test_canvas_shows_prime_tower_overlay_without_live_validation(qapp, monkeypatch):
    window = MainWindow()
    validation_calls = []

    try:
        window.contours = [_rect_contour(0, 0, 40, 40, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)

        params = window.param_panel.get_params()
        params.prime_tower.enabled = True
        params.prime_tower.center_x = 20.0
        params.prime_tower.center_y = 20.0
        params.prime_tower.width = 40.0
        params.prime_tower.depth = 40.0
        window.param_panel.set_params(params)
        window.slice_params = params

        monkeypatch.setattr(
            window,
            "_get_prime_tower_validation_error",
            lambda *args, **kwargs: validation_calls.append((args, kwargs)) or None,
        )
        window._refresh_prime_tower_overlay(params)

        assert validation_calls == []
        assert window.canvas.prime_tower_bounds == pytest.approx((0.0, 0.0, 40.0, 40.0))
        assert window.canvas.prime_tower_invalid is False
    finally:
        window.deleteLater()


def test_process_blocked_when_prime_tower_overlaps_model(qapp, monkeypatch):
    window = MainWindow()
    warnings = []
    run_async_calls = []

    try:
        window.contours = [_rect_contour(0, 0, 40, 40, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)

        params = window.param_panel.get_params()
        params.prime_tower.enabled = True
        params.prime_tower.center_x = 20.0
        params.prime_tower.center_y = 20.0
        params.prime_tower.width = 40.0
        params.prime_tower.depth = 40.0
        window.param_panel.set_params(params)

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
        assert "Prime tower overlaps existing printable geometry." in warnings[-1][0][2]
        assert window.status_label.text().startswith(window.tr("Processing Blocked"))
    finally:
        window.deleteLater()


def test_process_allows_prime_tower_inside_contour_hole(qapp, monkeypatch):
    window = MainWindow()
    warnings = []
    run_async_calls = []

    try:
        window.contours = [_rect_contour_with_hole(0, 0, 100, 100, 30, 30, 70, 70, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)

        params = window.param_panel.get_params()
        params.prime_tower.enabled = True
        params.prime_tower.center_x = 50.0
        params.prime_tower.center_y = 50.0
        params.prime_tower.width = 20.0
        params.prime_tower.depth = 20.0
        window.param_panel.set_params(params)

        monkeypatch.setattr(
            "src.ui.main_window.QMessageBox.warning",
            lambda *args, **kwargs: warnings.append((args, kwargs)) or 0,
        )
        monkeypatch.setattr(
            "src.ui.main_window.run_async",
            lambda *args, **kwargs: run_async_calls.append((args, kwargs)),
        )

        window._on_slice()

        assert warnings == []
        assert len(run_async_calls) == 1
    finally:
        window.deleteLater()


def test_process_blocked_when_prime_tower_touches_model_boundary(qapp, monkeypatch):
    window = MainWindow()
    warnings = []
    run_async_calls = []

    try:
        window.contours = [_rect_contour(0, 0, 40, 40, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)

        params = window.param_panel.get_params()
        params.prime_tower.enabled = True
        params.prime_tower.center_x = 50.0
        params.prime_tower.center_y = 20.0
        params.prime_tower.width = 20.0
        params.prime_tower.depth = 20.0
        window.param_panel.set_params(params)

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
        assert "Prime tower overlaps existing printable geometry." in warnings[-1][0][2]
    finally:
        window.deleteLater()


def test_process_uses_lightweight_prime_tower_validation(qapp, monkeypatch):
    window = MainWindow()
    warnings = []
    run_async_calls = []
    heavy_validation_calls = []

    try:
        window.contours = [_rect_contour(0, 0, 40, 40, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)

        params = window.param_panel.get_params()
        params.prime_tower.enabled = True
        params.prime_tower.center_x = 80.0
        params.prime_tower.center_y = 80.0
        params.prime_tower.width = 20.0
        params.prime_tower.depth = 20.0
        window.param_panel.set_params(params)

        monkeypatch.setattr(
            window.slice_engine,
            "validate_prime_tower_placement",
            lambda *args, **kwargs: heavy_validation_calls.append((args, kwargs)),
        )
        monkeypatch.setattr(
            "src.ui.main_window.QMessageBox.warning",
            lambda *args, **kwargs: warnings.append((args, kwargs)) or 0,
        )
        monkeypatch.setattr(
            "src.ui.main_window.run_async",
            lambda *args, **kwargs: run_async_calls.append((args, kwargs)),
        )

        window._on_slice()

        assert warnings == []
        assert heavy_validation_calls == []
        assert len(run_async_calls) == 1
    finally:
        window.deleteLater()


def test_transform_panel_hidden_on_home_and_preview_pages(qapp, monkeypatch):
    window = MainWindow()

    try:
        window.show()
        qapp.processEvents()
        window._on_nav_changed("project")
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)
        window.project_panel.update_contours(window.contours)
        window.canvas.set_selected_indices([0])
        qapp.processEvents()

        assert window.transform_panel.isVisible() is True

        window._on_nav_changed("home")
        qapp.processEvents()

        assert window.current_main_view == "home"
        assert window.transform_panel.isVisible() is False

        window._on_nav_changed("project")
        qapp.processEvents()

        assert window.current_main_view == "editor"
        assert window.current_view == "2d"
        assert window.transform_panel.isVisible() is True

        monkeypatch.setattr(window, "_on_slice", lambda: None)

        window._on_nav_changed("preview")
        qapp.processEvents()

        assert window.current_main_view == "editor"
        assert window.current_view == "3d"
        assert window.transform_panel.isVisible() is False
    finally:
        window.deleteLater()


def test_preview_auto_processes_when_contours_exist_and_result_missing(qapp, monkeypatch):
    window = MainWindow()
    calls = []
    loading_calls = []

    try:
        window.contours = [_rect_contour(0, 0, 10, 10, "A")]
        window.canvas.set_contours(window.contours, center_on_platform=False)

        monkeypatch.setattr(window, "_on_slice", lambda: calls.append("slice"))
        monkeypatch.setattr(
            window.preview_3d,
            "set_loading",
            lambda *args, **kwargs: loading_calls.append((args, kwargs)),
        )

        window._on_nav_changed("preview")

        assert calls == ["slice"]
        assert loading_calls == []
        assert window.current_main_view == "editor"
        assert window.current_view == "3d"
    finally:
        window.deleteLater()


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
        window.deleteLater()


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
        window.deleteLater()
