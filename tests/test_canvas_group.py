import math
import os

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.types import (
    Contour,
    Path,
    Point,
    get_contour_user_start_point_index,
    get_path_user_start_point_index,
    resolve_path_start_point_index,
    resolve_contour_start_point_index,
)
from src.ui.canvas_2d import Canvas2D
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
