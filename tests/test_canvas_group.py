import os

import pytest
from PySide6.QtCore import QPointF

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.types import Contour, Path, Point
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
