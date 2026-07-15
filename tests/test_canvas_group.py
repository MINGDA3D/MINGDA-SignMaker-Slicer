import math
import os

import pytest
from PySide6.QtCore import QEvent, QPointF, QSize, Qt
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtTest import QTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.types import (
    Contour,
    Path,
    Point,
    SliceParams,
    default_bed_exclude_area_for_bed,
    get_contour_user_start_point_index,
    get_path_user_start_point_index,
    resolve_path_start_point_index,
    resolve_contour_start_point_index,
)
from src.business.undo_manager import AddContoursCommand
from src.ui.canvas_2d import Canvas2D
from src.ui.canvas_toolbar import CanvasToolbar
from src.ui.main_window import MainWindow
from src.ui.project_panel import _ProjectListItem


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


def test_canvas_marks_bed_exclude_area_overlap_out_of_bounds(qapp):
    canvas = Canvas2D()
    canvas.set_platform_size(800.0, 1200.0)
    canvas.set_unprintable_regions(default_bed_exclude_area_for_bed(800.0, 1200.0))
    safe_contour = _rect_contour(100.0, 100.0, 120.0, 120.0)
    blocked_contour = _rect_contour(780.0, 10.0, 790.0, 30.0)

    canvas.set_contours([safe_contour, blocked_contour], center_on_platform=False)

    assert canvas.is_contour_out_of_bounds(safe_contour) is False
    assert canvas.is_contour_out_of_bounds(blocked_contour) is True
    assert canvas.get_out_of_bounds_indices() == [1]


def _circle_contour(
    center_x: float,
    center_y: float,
    radius: float,
    *,
    segments: int = 32,
    name: str = "",
) -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(
                    center_x + radius * math.cos(2 * math.pi * i / segments),
                    center_y + radius * math.sin(2 * math.pi * i / segments),
                )
                for i in range(segments)
            ],
            is_closed=True,
        ),
        name=name,
    )


def _rect_contour_with_hole(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    hole_x1: float,
    hole_y1: float,
    hole_x2: float,
    hole_y2: float,
    name: str = "",
) -> Contour:
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


def _enable_bottom_face(window: MainWindow, *, diameter: float = 4.0) -> None:
    params = SliceParams()
    params.bottom_face.enabled = True
    params.bottom_face.thickness = 1.0
    params.bottom_face.screw_hole_diameter = diameter
    window.slice_params = params
    window._refresh_prime_tower_overlay(params)
    window.canvas_toolbar.set_screw_hole_enabled(True)


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


def test_canvas_start_point_candidates_use_sharp_corners_for_rectangle(qapp):
    canvas = Canvas2D()
    contour = _rect_contour(0, 0, 10, 10, "Rect")

    assert canvas.get_start_point_candidate_indices(contour) == [0, 1, 2, 3]


def test_canvas_start_point_candidates_fall_back_to_sampled_points_for_smooth_contour(qapp):
    canvas = Canvas2D()
    contour = _circle_contour(0, 0, 10, segments=32, name="Circle")

    candidates = canvas.get_start_point_candidate_indices(contour)

    assert 0 < len(candidates) <= canvas.START_POINT_FALLBACK_LIMIT
    assert resolve_contour_start_point_index(contour) in candidates
    assert len(candidates) == len(set(candidates))


def test_canvas_hole_start_point_candidates_and_default(qapp):
    canvas = Canvas2D()
    contour = _rect_contour_with_hole(0, 0, 30, 30, 10, 10, 20, 20, "HoleRect")

    candidates = canvas.get_start_point_candidate_indices(contour.holes[0])

    assert candidates == [0, 1, 2, 3]
    assert resolve_path_start_point_index(contour.holes[0]) in candidates


def test_auto_start_point_prefers_sharpest_corner():
    contour = Contour(
        outer=Path(
            points=[
                Point(0, 0),
                Point(10, 0),
                Point(5, 20),
            ],
            is_closed=True,
        ),
        name="SharpTriangle",
    )

    assert resolve_contour_start_point_index(contour) == 2


def test_canvas_set_contours_normalizes_invalid_start_point_index(qapp):
    canvas = Canvas2D()
    contour = _rect_contour(0, 0, 10, 10, "Rect")
    contour.start_point_index = 99

    canvas.set_contours([contour], center_on_platform=False)

    assert contour.start_point_index == 0


def test_canvas_click_selects_entire_asset(qapp):
    canvas = Canvas2D()
    contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
        _rect_contour(40, 0, 50, 10, "C"),
    ]
    contours[0].asset_id = "asset-1"
    contours[0].asset_name = "logo.svg"
    contours[1].asset_id = "asset-1"
    contours[1].asset_name = "logo.svg"
    canvas.set_contours(contours, center_on_platform=False)

    canvas._handle_selection(canvas._world_to_screen(QPointF(1, 1)))

    assert canvas.selected_indices == [0, 1]


def test_canvas_selection_syncs_project_panel(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
        _rect_contour(40, 0, 50, 10, "C"),
    ]
    window.contours[0].group_id = "g1"
    window.contours[1].group_id = "g1"
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window.canvas._handle_selection(window.canvas._world_to_screen(QPointF(1, 1)))

    assert window.canvas.selected_indices == [0, 1]
    assert window.project_panel.get_selected_indices() == [0, 1]

    window.deleteLater()


def test_project_panel_asset_selection_syncs_canvas(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
        _rect_contour(40, 0, 50, 10, "C"),
    ]
    window.contours[0].asset_id = "asset-1"
    window.contours[0].asset_name = "logo.svg"
    window.contours[1].asset_id = "asset-1"
    window.contours[1].asset_name = "logo.svg"
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window.project_panel._on_asset_clicked("asset-1")

    assert window.project_panel.get_selected_indices() == [0, 1]
    assert window.canvas.selected_indices == [0, 1]

    window.project_panel._on_asset_toggled("asset-1")
    window.project_panel._on_item_clicked(1)

    assert window.project_panel.get_selected_indices() == [1]
    assert window.canvas.selected_indices == [1]

    window.deleteLater()


def test_project_panel_selection_syncs_canvas(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
        _rect_contour(40, 0, 50, 10, "C"),
    ]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window.project_panel._on_item_clicked(1)

    assert window.project_panel.get_selected_indices() == [1]
    assert window.canvas.selected_indices == [1]

    window.deleteLater()


def test_main_window_release_asset_supports_undo(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
        _rect_contour(40, 0, 50, 10, "C"),
    ]
    window.contours[0].asset_id = "asset-1"
    window.contours[0].asset_name = "logo.svg"
    window.contours[1].asset_id = "asset-1"
    window.contours[1].asset_name = "logo.svg"
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.canvas.selected_indices = [0]

    window._on_release_asset()

    assert [contour.asset_id for contour in window.contours] == ["", "", ""]
    assert [contour.asset_name for contour in window.contours] == ["", "", ""]

    window._on_undo()
    assert window.contours[0].asset_id == "asset-1"
    assert window.contours[1].asset_id == "asset-1"
    assert window.contours[0].asset_name == "logo.svg"
    assert window.contours[1].asset_name == "logo.svg"

    window.deleteLater()


def test_project_panel_hides_release_button_for_single_contour_asset(qapp):
    window = MainWindow()
    window.contours = [_rect_contour(0, 0, 10, 10, "A")]
    window.contours[0].asset_id = "asset-1"
    window.contours[0].asset_name = "logo.svg"
    window.project_panel.update_contours(window.contours)

    asset_row = next(row for row in window.project_panel._rows if row.kind == "asset")

    assert asset_row.item.release_btn is None

    window.deleteLater()


def test_canvas_toolbar_disables_release_button_for_single_contour_asset(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
    ]
    window.contours[0].asset_id = "asset-1"
    window.contours[0].asset_name = "logo.svg"
    window.contours[1].asset_id = "asset-1"
    window.contours[1].asset_name = "logo.svg"
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window._apply_contour_selection([0])

    assert window.canvas_toolbar.btn_release_asset.isEnabled() is True

    single_window = MainWindow()
    single_window.contours = [_rect_contour(0, 0, 10, 10, "A")]
    single_window.contours[0].asset_id = "asset-2"
    single_window.contours[0].asset_name = "logo.svg"
    single_window.canvas.set_contours(single_window.contours, center_on_platform=False)
    single_window.project_panel.update_contours(single_window.contours)

    single_window._apply_contour_selection([0])

    assert single_window.canvas_toolbar.btn_release_asset.isEnabled() is False
    assert single_window.canvas_toolbar.btn_release_asset.isHidden() is False

    window.deleteLater()
    single_window.deleteLater()


def test_start_point_mode_toggles_from_toolbar_and_escape(qapp):
    window = MainWindow()
    window.contours = [_rect_contour(0, 0, 10, 10, "A")]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window._on_start_point_tool()

    assert window.canvas.current_tool == "start_point"
    assert window.canvas_toolbar.btn_start_point.isChecked() is True

    escape_event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )
    window.canvas.keyPressEvent(escape_event)

    assert window.canvas.current_tool == "select"
    assert window.canvas_toolbar.btn_start_point.isChecked() is False

    window.deleteLater()


def test_screw_hole_button_uses_distinct_disabled_icon_variant(qapp):
    toolbar = CanvasToolbar()

    normal = toolbar.btn_screw_hole.icon().pixmap(
        QSize(36, 36),
        QIcon.Mode.Normal,
        QIcon.State.Off,
    )
    toolbar.set_screw_hole_enabled(False)
    disabled = toolbar.btn_screw_hole.icon().pixmap(
        QSize(36, 36),
        QIcon.Mode.Disabled,
        QIcon.State.Off,
    )

    assert toolbar.btn_screw_hole.isEnabled() is False
    assert not disabled.isNull()

    normal_image = normal.toImage()
    disabled_image = disabled.toImage()
    assert any(
        normal_image.pixel(x, y) != disabled_image.pixel(x, y)
        for y in range(normal_image.height())
        for x in range(normal_image.width())
    )

    toolbar.deleteLater()


def test_start_point_click_updates_only_target_contour_and_is_undoable(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10, "A"),
        _rect_contour(20, 0, 30, 10, "B"),
    ]
    window.contours[0].asset_id = "asset-1"
    window.contours[0].asset_name = "logo.svg"
    window.contours[1].asset_id = "asset-1"
    window.contours[1].asset_name = "logo.svg"
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.slice_result = object()

    window._on_start_point_tool()
    target_point = window.contours[0].outer.points[2]
    handled = window.canvas._handle_start_point_click(
        window.canvas._world_to_screen(QPointF(target_point.x, target_point.y))
    )

    assert handled is True
    assert window.contours[0].start_point_index == 3
    assert window.contours[1].start_point_index == 0
    assert get_contour_user_start_point_index(window.contours[0]) == 2
    assert window.canvas.selected_indices == [0]
    assert window.undo_manager.can_undo is True
    assert window.slice_result is None

    window._on_undo()

    assert window.contours[0].start_point_index == 0

    window.deleteLater()


def test_start_point_click_can_explicitly_store_first_vertex(qapp):
    window = MainWindow()
    window.contours = [_rect_contour(0, 0, 10, 10, "A")]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window._on_start_point_tool()
    target_point = window.contours[0].outer.points[0]
    handled = window.canvas._handle_start_point_click(
        window.canvas._world_to_screen(QPointF(target_point.x, target_point.y))
    )

    assert handled is True
    assert window.contours[0].start_point_index == 1
    assert get_contour_user_start_point_index(window.contours[0]) == 0

    window.deleteLater()


def test_start_point_click_updates_hole_only_and_is_undoable(qapp):
    window = MainWindow()
    window.contours = [_rect_contour_with_hole(0, 0, 40, 40, 10, 10, 20, 20, "A")]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.slice_result = object()

    window._on_start_point_tool()
    target_point = window.contours[0].holes[0].points[2]
    handled = window.canvas._handle_start_point_click(
        window.canvas._world_to_screen(QPointF(target_point.x, target_point.y))
    )

    assert handled is True
    assert window.contours[0].start_point_index == 0
    assert window.contours[0].holes[0].start_point_index == 3
    assert get_path_user_start_point_index(window.contours[0].holes[0]) == 2
    assert window.canvas.selected_indices == [0]
    assert window.undo_manager.can_undo is True
    assert window.slice_result is None

    window._on_undo()

    assert window.contours[0].holes[0].start_point_index == 0

    window.deleteLater()


def test_print_order_mode_toggles_from_toolbar_and_escape(qapp):
    window = MainWindow()
    window.contours = [_rect_contour(0, 0, 10, 10, "A")]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window._on_print_order_tool()

    assert window.canvas.current_tool == "print_order"
    assert window.canvas_toolbar.btn_order.isChecked() is True

    escape_event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )
    window.canvas.keyPressEvent(escape_event)

    assert window.canvas.current_tool == "select"
    assert window.canvas_toolbar.btn_order.isChecked() is False

    window.deleteLater()


def test_screw_hole_mode_toggles_from_toolbar_and_escape(qapp):
    window = MainWindow()
    window.contours = [_rect_contour(0, 0, 40, 40, "A")]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    _enable_bottom_face(window)

    assert window.canvas_toolbar.btn_screw_hole.isEnabled() is True

    window._on_screw_hole_tool()

    assert window.canvas.current_tool == "screw_hole"
    assert window.canvas_toolbar.btn_screw_hole.isChecked() is True

    escape_event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )
    window.canvas.keyPressEvent(escape_event)

    assert window.canvas.current_tool == "select"
    assert window.canvas_toolbar.btn_screw_hole.isChecked() is False

    window.deleteLater()


def test_screw_hole_edit_session_commits_as_single_undo_step(qapp):
    window = MainWindow()
    window.contours = [_rect_contour(0, 0, 40, 40, "A")]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    _enable_bottom_face(window)

    window._on_screw_hole_tool()
    window._on_screw_hole_add_requested(10.0, 10.0)
    window._on_screw_hole_move_requested(0, 0, 15.0, 15.0)

    assert window.contours[0].screw_hole_centers == [Point(15.0, 15.0)]
    assert window.undo_manager.can_undo is False

    window._exit_screw_hole_mode()

    assert window.undo_manager.can_undo is True

    window._on_undo()
    assert window.contours[0].screw_hole_centers == []

    window._on_redo()
    assert window.contours[0].screw_hole_centers == [Point(15.0, 15.0)]

    window.deleteLater()


def test_screw_hole_delete_key_removes_only_active_hole(qapp):
    window = MainWindow()
    contour = _rect_contour(0, 0, 40, 40, "A")
    contour.screw_hole_centers = [Point(10.0, 10.0)]
    window.contours = [contour]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    _enable_bottom_face(window)

    window._on_screw_hole_tool()
    window.show()
    window.canvas.repaint()
    qapp.processEvents()

    click_pos = window.canvas._world_to_screen(QPointF(10.0, 10.0)).toPoint()
    QTest.mouseClick(window.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, click_pos)
    qapp.processEvents()

    assert window.canvas.current_tool == "screw_hole"
    assert window.canvas._selected_screw_hole == (0, 0)
    assert window.canvas.selected_indices == []

    delete_event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Delete,
        Qt.KeyboardModifier.NoModifier,
    )
    window.canvas.keyPressEvent(delete_event)

    assert len(window.contours) == 1
    assert window.contours[0].screw_hole_centers == []

    window.deleteLater()


def test_screw_hole_click_keeps_edit_mode_and_does_not_select_contour(qapp):
    window = MainWindow()
    contour = _rect_contour(0, 0, 40, 40, "A")
    contour.screw_hole_centers = [Point(10.0, 10.0)]
    window.contours = [contour]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    _enable_bottom_face(window)

    window._on_screw_hole_tool()
    window.show()
    window.canvas.repaint()
    qapp.processEvents()

    click_pos = window.canvas._world_to_screen(QPointF(10.0, 10.0)).toPoint()
    QTest.mouseClick(window.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, click_pos)
    qapp.processEvents()

    assert window.canvas.current_tool == "screw_hole"
    assert window.canvas_toolbar.btn_screw_hole.isChecked() is True
    assert window.canvas._selected_screw_hole == (0, 0)
    assert window.canvas.selected_indices == []

    window.deleteLater()


def test_screw_hole_target_prefers_smallest_nested_contour(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 60, 60, "outer"),
        _rect_contour(20, 20, 40, 40, "inner"),
    ]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    _enable_bottom_face(window)

    window._on_screw_hole_tool()
    window._on_screw_hole_add_requested(30.0, 30.0)

    assert window.contours[0].screw_hole_centers == []
    assert window.contours[1].screw_hole_centers == [Point(30.0, 30.0)]

    window.deleteLater()


def test_deleting_contour_clears_its_screw_hole_overlay(qapp):
    window = MainWindow()
    contour = _rect_contour(0, 0, 40, 40, "A")
    contour.screw_hole_centers = [Point(10.0, 10.0)]
    window.contours = [contour]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    _enable_bottom_face(window)

    window._refresh_screw_hole_overlay()
    assert len(window.canvas._screw_hole_overlay) == 1

    window._on_delete_requested([0])

    assert window.contours == []
    assert window.canvas._screw_hole_overlay == []

    window.deleteLater()


def test_canvas_transforms_keep_screw_hole_centers_in_sync(qapp):
    move_canvas = Canvas2D()
    move_contour = _rect_contour(0, 0, 10, 10, "move")
    move_contour.screw_hole_centers = [Point(2.0, 2.0)]
    move_canvas.set_contours([move_contour], center_on_platform=False)
    move_canvas.set_selected_indices([0], update_view=False)
    move_canvas.move_selected(3.0, 4.0)
    assert move_canvas.contours[0].screw_hole_centers == [Point(5.0, 6.0)]

    rotate_canvas = Canvas2D()
    rotate_contour = _rect_contour(0, 0, 10, 10, "rotate")
    rotate_contour.screw_hole_centers = [Point(2.0, 2.0)]
    rotate_canvas.set_contours([rotate_contour], center_on_platform=False)
    rotate_canvas.set_selected_indices([0], update_view=False)
    rotate_canvas.rotate_selected(90.0)
    rotated_point = rotate_canvas.contours[0].screw_hole_centers[0]
    assert rotated_point.x == pytest.approx(8.0)
    assert rotated_point.y == pytest.approx(2.0)

    scale_canvas = Canvas2D()
    scale_contour = _rect_contour(0, 0, 10, 10, "scale")
    scale_contour.screw_hole_centers = [Point(2.0, 4.0)]
    scale_canvas.set_contours([scale_contour], center_on_platform=False)
    scale_canvas.set_selected_indices([0], update_view=False)
    scale_canvas.scale_selected_xy(2.0, 0.5)
    scaled_point = scale_canvas.contours[0].screw_hole_centers[0]
    assert scaled_point.x == pytest.approx(-1.0)
    assert scaled_point.y == pytest.approx(4.5)

    mirror_canvas = Canvas2D()
    mirror_contour = _rect_contour(0, 0, 10, 10, "mirror")
    mirror_contour.screw_hole_centers = [Point(2.0, 4.0)]
    mirror_canvas.set_contours([mirror_contour], center_on_platform=False)
    mirror_canvas.set_selected_indices([0], update_view=False)
    mirror_canvas.mirror_selected("x")
    assert mirror_canvas.contours[0].screw_hole_centers == [Point(8.0, 4.0)]


def test_scale_panel_percent_change_is_undoable_after_adding_contour(qapp):
    window = MainWindow()
    contour = _rect_contour(0, 0, 10, 10, "Text")

    def selected_width() -> float:
        bounds = window.contours[0].outer.bounds
        return bounds[2] - bounds[0]

    assert window.undo_manager.push(
        AddContoursCommand(window.contours, [contour], "Add Text")
    )
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.canvas.set_selected_indices([0], update_view=False)

    window._on_scale_tool()
    window.scale_x_pct.setValue(200.0)
    window._on_scale_pct_changed(window.scale_x_pct)

    assert len(window.contours) == 1
    assert selected_width() == pytest.approx(20.0)
    assert window.undo_manager.get_undo_history(2)[0] == window.tr("Scale")

    window._on_undo()

    assert len(window.contours) == 1
    assert selected_width() == pytest.approx(10.0)
    assert window.scale_x_pct.value() == pytest.approx(100.0)
    assert window.scale_y_pct.value() == pytest.approx(100.0)

    window._on_redo()

    assert len(window.contours) == 1
    assert selected_width() == pytest.approx(20.0)
    assert window.scale_x_pct.value() == pytest.approx(200.0)
    assert window.scale_y_pct.value() == pytest.approx(200.0)

    window.deleteLater()


def test_print_order_click_prioritizes_hole_and_commits_as_one_undo_step(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour_with_hole(0, 0, 40, 40, 10, 10, 20, 20, "A"),
        _rect_contour(60, 0, 80, 20, "B"),
    ]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.slice_result = object()

    window._on_print_order_tool()

    hole_click = window.canvas._world_to_screen(QPointF(15, 15))
    assert window.canvas._find_print_order_loop_at(hole_click) == (0, 0)

    handled = window.canvas._handle_print_order_click(hole_click)

    assert handled is True
    assert window.contours[0].holes[0].print_order == 1
    assert window.contours[0].outer.print_order == 2
    assert window.contours[1].outer.print_order == 3
    assert window.canvas.selected_indices == [0]
    assert window.undo_manager.can_undo is False
    assert window.slice_result is None

    outer_b_click = window.canvas._world_to_screen(QPointF(70, 10))
    assert window.canvas._handle_print_order_click(outer_b_click) is True
    assert window.contours[0].holes[0].print_order == 1
    assert window.contours[1].outer.print_order == 2
    assert window.contours[0].outer.print_order == 3

    window._exit_print_order_mode()

    assert window.undo_manager.can_undo is True

    window._on_undo()

    assert window.contours[0].outer.print_order == 0
    assert window.contours[0].holes[0].print_order == 0
    assert window.contours[1].outer.print_order == 0

    window.deleteLater()


def test_print_order_badges_do_not_overlap_for_concentric_loops(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour_with_hole(0, 0, 40, 40, 10, 10, 20, 20, "A"),
        _rect_contour(60, 0, 80, 20, "B"),
    ]
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window._on_print_order_tool()
    badge_layout = window.canvas._build_print_order_badge_layout()

    assert [order for order, _target, _rect in badge_layout] == [1, 2, 3]

    rects = [rect for _order, _target, rect in badge_layout]
    assert len(rects) == 3
    assert rects[0].intersects(rects[1]) is False
    assert rects[0].intersects(rects[2]) is False
    assert rects[1].intersects(rects[2]) is False

    window.deleteLater()


def test_main_window_release_asset_ignores_single_contour_asset(qapp):
    window = MainWindow()
    window.contours = [_rect_contour(0, 0, 10, 10, "A")]
    window.contours[0].asset_id = "asset-1"
    window.contours[0].asset_name = "logo.svg"
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.canvas.selected_indices = [0]

    window._on_release_asset()

    assert window.contours[0].asset_id == "asset-1"
    assert window.contours[0].asset_name == "logo.svg"
    assert window.contours[0].name == "A"
    assert window.undo_manager.can_undo is False

    window.deleteLater()


def test_project_list_item_label_has_room_for_underscores(qapp):
    item = _ProjectListItem(1, "Coca-Cola_1")
    item.show()
    qapp.processEvents()

    assert (
        item.name_label.contentsRect().height()
        >= item.name_label.fontMetrics().lineSpacing()
    )

    item.deleteLater()


def test_project_list_item_keeps_action_button_visible_with_long_name(qapp):
    title = "UGG EXPRESS dxf signmaker_dxf_10"
    item = _ProjectListItem(1, title)
    item.resize(300, 44)
    item.show()
    qapp.processEvents()

    assert item.minimumSizeHint().width() <= 300
    assert item.delete_btn.geometry().right() <= item.rect().right()
    assert len(item.name_label.text()) < len(title)
    assert item.name_label.toolTip() == title

    item.deleteLater()


def test_project_list_asset_row_shows_name_at_project_panel_min_width(qapp):
    title = "UGG EXPRESS dxf signmaker.dxf"
    item = _ProjectListItem(
        "asset",
        title,
        secondary_text="(10)",
        collapsible=True,
        expanded=False,
        releasable=True,
    )
    item.resize(300, 44)
    item.show()
    qapp.processEvents()

    assert item.name_label.text()
    assert item.name_label.text().startswith("UGG")
    assert item.delete_btn.geometry().right() <= item.rect().right()

    item.deleteLater()


def test_main_window_project_panel_uses_readable_width_range(qapp):
    window = MainWindow()

    assert window.project_panel.minimumWidth() == 300
    assert window.project_panel.maximumWidth() == 420

    window.deleteLater()


def test_main_window_release_asset_names_contours_from_file_stem_without_duplicates(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10),
        _rect_contour(20, 0, 30, 10),
        _rect_contour(40, 0, 50, 10, "logo_1"),
    ]
    window.contours[0].asset_id = "asset-1"
    window.contours[0].asset_name = "logo.svg"
    window.contours[1].asset_id = "asset-1"
    window.contours[1].asset_name = "logo.svg"
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.canvas.selected_indices = [0]

    window._on_release_asset()

    assert [contour.name for contour in window.contours] == [
        "logo_svg_1",
        "logo_svg_2",
        "logo_1",
    ]
    assert [contour.asset_id for contour in window.contours] == ["", "", ""]
    assert [contour.asset_name for contour in window.contours] == ["", "", ""]

    window._on_undo()

    assert [contour.name for contour in window.contours] == ["", "", "logo_1"]
    assert [contour.asset_id for contour in window.contours] == ["asset-1", "asset-1", ""]
    assert [contour.asset_name for contour in window.contours] == ["logo.svg", "logo.svg", ""]

    window.deleteLater()


def test_main_window_duplicate_import_names_get_unique_asset_names(qapp):
    window = MainWindow()

    first_batch = [
        _rect_contour(0, 0, 10, 10),
        _rect_contour(20, 0, 30, 10),
    ]
    window._assign_asset_metadata(first_batch, "logo.svg")
    window.contours.extend(first_batch)

    second_batch = [
        _rect_contour(40, 0, 50, 10),
        _rect_contour(60, 0, 70, 10),
    ]
    window._assign_asset_metadata(second_batch, "logo.svg")
    window.contours.extend(second_batch)

    assert [contour.asset_name for contour in first_batch] == ["logo.svg", "logo.svg"]
    assert [contour.asset_name for contour in second_batch] == ["logo_2.svg", "logo_2.svg"]

    window.deleteLater()


def test_main_window_release_duplicate_import_uses_unique_asset_stem(qapp):
    window = MainWindow()
    window.contours = [
        _rect_contour(0, 0, 10, 10),
        _rect_contour(20, 0, 30, 10),
    ]
    window.contours[0].asset_id = "asset-2"
    window.contours[0].asset_name = "logo_2.svg"
    window.contours[1].asset_id = "asset-2"
    window.contours[1].asset_name = "logo_2.svg"
    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)
    window.canvas.selected_indices = [0]

    window._on_release_asset()

    assert [contour.name for contour in window.contours] == [
        "logo_2_svg_1",
        "logo_2_svg_2",
    ]

    window.deleteLater()


def test_main_window_duplicate_text_names_use_same_suffix_rule(qapp):
    window = MainWindow()

    first_batch = [_rect_contour(0, 0, 10, 10)]
    window._assign_asset_metadata(first_batch, "Text: ABC")
    window.contours.extend(first_batch)

    second_batch = [_rect_contour(20, 0, 30, 10)]
    window._assign_asset_metadata(second_batch, "Text: ABC")
    window.contours.extend(second_batch)

    third_batch = [_rect_contour(40, 0, 50, 10)]
    window._assign_asset_metadata(third_batch, "Text: ABC")

    assert [contour.asset_name for contour in first_batch] == ["Text: ABC"]
    assert [contour.asset_name for contour in second_batch] == ["Text: ABC_2"]
    assert [contour.asset_name for contour in third_batch] == ["Text: ABC_3"]

    window.deleteLater()


def test_main_window_release_same_stem_different_suffixes_uses_suffix_prefix(qapp):
    window = MainWindow()

    svg_batch = [
        _rect_contour(0, 0, 10, 10),
        _rect_contour(20, 0, 30, 10),
    ]
    window._assign_asset_metadata(svg_batch, "logo.svg")
    window.contours.extend(svg_batch)

    dxf_batch = [
        _rect_contour(40, 0, 50, 10),
        _rect_contour(60, 0, 70, 10),
    ]
    window._assign_asset_metadata(dxf_batch, "logo.dxf")
    window.contours.extend(dxf_batch)

    window.canvas.set_contours(window.contours, center_on_platform=False)
    window.project_panel.update_contours(window.contours)

    window.canvas.selected_indices = [0]
    window._on_release_asset()
    assert [contour.name for contour in window.contours[:2]] == [
        "logo_svg_1",
        "logo_svg_2",
    ]

    window.canvas.selected_indices = [2]
    window._on_release_asset()
    assert [contour.name for contour in window.contours] == [
        "logo_svg_1",
        "logo_svg_2",
        "logo_dxf_1",
        "logo_dxf_2",
    ]

    window.deleteLater()


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

    window.deleteLater()
