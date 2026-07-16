from PySide6.QtWidgets import QApplication, QToolButton
import pytest

from src.core.complexity import (
    ComplexityLevel,
    required_complexity_for_project,
)
from src.core.types import (
    Contour,
    EdgeProfile,
    EdgeProfileType,
    EdgeType,
    Path,
    Point,
    serialize_params,
    SliceParams,
)
from src.ui.canvas_toolbar import CanvasToolbar
from src.ui.complexity_selector import ComplexitySelector
from src.ui.main_window import MainWindow
from src.ui.param_panel import ParamPanel
from src.ui.title_bar import TitleBar


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_required_complexity_detects_opt_in_features_only():
    params = SliceParams()
    assert required_complexity_for_project(params).level == ComplexityLevel.BASIC
    assert "complexity" not in serialize_params(params)

    params.skirt.enabled = True
    requirement = required_complexity_for_project(params)
    assert requirement.level == ComplexityLevel.ADVANCED
    assert "Anti-warp brim" in requirement.features

    params.prime_tower.enabled = True
    requirement = required_complexity_for_project(params)
    assert requirement.level == ComplexityLevel.EXPERT
    assert "Prime tower" in requirement.features


def test_required_complexity_detects_contour_edits_and_imported_edges():
    params = SliceParams()
    contour = Contour()
    contour.screw_hole_centers.append(Point(1, 2))
    contour.outer.print_order = 2

    requirement = required_complexity_for_project(params, [contour])
    assert requirement.level == ComplexityLevel.EXPERT
    assert "Manual screw holes" in requirement.features
    assert "Custom print order" in requirement.features

    params.shell.edge_type = EdgeType.CUSTOM
    params.shell.edge_profile = EdgeProfile(
        profile_type=EdgeProfileType.CUSTOM,
        source_file="profile.dxf",
    )
    assert required_complexity_for_project(params).level == ComplexityLevel.EXPERT


def test_param_panel_levels_are_cumulative_without_emitting_params_changed(qapp):
    panel = ParamPanel()
    emissions = []
    panel.params_changed.connect(lambda: emissions.append(True))
    shell_form = panel._form_rows[panel.width_line_spin]
    profile_form = panel._form_rows[panel.profile_retract_length]
    other_index = panel.shape_feature_tabs.indexOf(
        panel._shape_feature_widgets_by_key["other"]
    )

    panel.set_complexity_level(ComplexityLevel.BASIC)
    assert shell_form.isRowVisible(panel.width_line_spin) is False
    assert panel.wall_mode_buttons[2].isHidden() is True
    assert panel.shape_feature_tabs.isTabVisible(other_index) is False

    panel.set_complexity_level(ComplexityLevel.ADVANCED)
    assert shell_form.isRowVisible(panel.width_line_spin) is True
    assert panel.wall_mode_buttons[2].isHidden() is False
    assert panel.import_dxf_btn.isHidden() is True
    assert panel.shape_feature_tabs.isTabVisible(other_index) is True

    panel.set_complexity_level(ComplexityLevel.EXPERT)
    assert panel.import_dxf_btn.isHidden() is False
    assert profile_form.isRowVisible(panel.profile_retract_length) is True
    assert emissions == []


def test_param_panel_warns_without_changing_hidden_feature_values(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.skirt.enabled = True
    requirement = required_complexity_for_project(params)

    panel.set_hidden_feature_context(requirement)
    panel.set_complexity_level(ComplexityLevel.BASIC)

    assert panel.complexity_banner.isHidden() is False
    assert "Advanced" in panel.complexity_banner_label.text()
    assert panel.get_params().skirt.enabled is False

    # Loading the project value remains independent from visibility.
    panel.set_params(params)
    panel.set_hidden_feature_context(required_complexity_for_project(panel.get_params()))
    assert panel.get_params().skirt.enabled is True
    assert panel.complexity_banner.isHidden() is False


def test_compact_complexity_selector_uses_one_menu_button(qapp):
    selector = ComplexitySelector()
    changes = []
    selector.level_changed.connect(changes.append)

    assert selector.findChildren(QToolButton) == [selector.button]
    assert selector.button.menu() is selector.menu
    assert selector.button.text() == selector._actions[ComplexityLevel.BASIC].text()

    selector._actions[ComplexityLevel.ADVANCED].trigger()
    assert selector.level() == ComplexityLevel.ADVANCED
    assert selector.button.text() == selector._actions[ComplexityLevel.ADVANCED].text()
    assert changes == [ComplexityLevel.ADVANCED]

    selector.set_level(ComplexityLevel.EXPERT)
    assert selector.level() == ComplexityLevel.EXPERT
    assert changes == [ComplexityLevel.ADVANCED]


def test_complexity_selector_lives_in_settings_header_not_title_bar(qapp):
    title_bar = TitleBar()
    panel = ParamPanel()

    assert title_bar.findChild(ComplexitySelector) is None
    assert panel.complexity_selector.parent() is panel.header
    panel.set_complexity_level(ComplexityLevel.ADVANCED)
    assert panel.complexity_selector.level() == ComplexityLevel.ADVANCED
    assert title_bar.get_complexity_level() == ComplexityLevel.BASIC

    title_bar.deleteLater()
    panel.deleteLater()


def test_canvas_toolbar_filters_actions_by_level_and_preserves_context_state(qapp):
    toolbar = CanvasToolbar()
    assert toolbar.visible_tool_keys() == [
        "move", "rotate", "scale", "mirror_x", "mirror_y", "text"
    ]

    toolbar.set_release_asset_enabled(True)
    toolbar.set_complexity_level(ComplexityLevel.ADVANCED)
    assert toolbar.visible_tool_keys() == [
        "move", "rotate", "scale", "mirror_x", "mirror_y",
        "group", "ungroup", "release_asset", "text", "start_point", "screw_hole",
    ]
    assert toolbar.btn_release_asset.isEnabled() is True

    toolbar.set_complexity_level(ComplexityLevel.EXPERT)
    assert "intersection" in toolbar.visible_tool_keys()
    assert "difference" in toolbar.visible_tool_keys()
    assert "print_order" in toolbar.visible_tool_keys()
    assert isinstance(toolbar.btn_order, QToolButton)


def test_canvas_toolbar_uses_qt_overflow_extension_at_narrow_width(qapp):
    toolbar = CanvasToolbar()
    toolbar.set_complexity_level(ComplexityLevel.EXPERT)
    toolbar.resize(320, 52)
    toolbar.show()
    qapp.processEvents()

    extension = toolbar.findChild(QToolButton, "qt_toolbar_ext_button")
    assert extension is not None
    assert extension.isVisible() is True

    toolbar.close()


def test_canvas_toolbar_centers_visible_actions_in_canvas_area(qapp):
    toolbar = CanvasToolbar()
    toolbar.resize(1000, 52)
    toolbar.show()
    qapp.processEvents()

    inner_geometry = toolbar._toolbar.geometry()
    left_space = inner_geometry.left()
    right_space = toolbar.width() - inner_geometry.right() - 1
    assert abs(left_space - right_space) <= 1

    toolbar.close()


@pytest.mark.parametrize(
    ("level", "expected_structure"),
    [
        (
            ComplexityLevel.BASIC,
            [
                "move", "rotate", "scale", "|", "mirror_x", "mirror_y", "|",
                "text",
            ],
        ),
        (
            ComplexityLevel.ADVANCED,
            [
                "move", "rotate", "scale", "|", "mirror_x", "mirror_y", "|",
                "group", "ungroup", "release_asset", "|", "text", "|",
                "start_point", "screw_hole",
            ],
        ),
        (
            ComplexityLevel.EXPERT,
            [
                "move", "rotate", "scale", "|", "mirror_x", "mirror_y", "|",
                "intersection", "difference", "|", "group", "ungroup",
                "release_asset", "|", "text", "|", "start_point",
                "print_order", "screw_hole",
            ],
        ),
    ],
)
def test_canvas_toolbar_separators_only_split_visible_groups(
    qapp, level, expected_structure
):
    toolbar = CanvasToolbar()
    toolbar.resize(1000, 52)
    toolbar.set_complexity_level(level)
    toolbar.show()
    qapp.processEvents()

    action_keys = {action: key for key, action in toolbar._tool_actions.items()}
    structure = [
        "|" if action.isSeparator() else action_keys[action]
        for action in toolbar._toolbar.actions()
        if action.isVisible()
    ]
    assert structure == expected_structure
    assert structure[0] != "|"
    assert structure[-1] != "|"
    assert all(current != following for current, following in zip(structure, structure[1:]))

    toolbar.close()


def test_main_window_syncs_level_without_invalidating_processed_result(qapp, monkeypatch):
    window = MainWindow()
    saved_levels = []
    monkeypatch.setattr(
        window.settings_manager,
        "set_complexity_level",
        lambda level: saved_levels.append(level),
    )
    processed_result = object()
    window.slice_result = processed_result
    window._params_modified = False

    window.param_panel.complexity_selector._actions[
        ComplexityLevel.EXPERT
    ].trigger()

    assert window._complexity_level == ComplexityLevel.EXPERT
    assert window.title_bar.get_complexity_level() == ComplexityLevel.EXPERT
    assert window.param_panel.complexity_level() == ComplexityLevel.EXPERT
    assert window.canvas_toolbar.complexity_level() == ComplexityLevel.EXPERT
    assert window.slice_result is processed_result
    assert window._params_modified is False
    assert saved_levels == [ComplexityLevel.EXPERT]

    window.deleteLater()


def test_lowering_level_exits_tools_that_become_hidden(qapp, monkeypatch):
    window = MainWindow()
    monkeypatch.setattr(
        window.settings_manager,
        "set_complexity_level",
        lambda _level: None,
    )
    window.contours = [
        Contour(
            outer=Path(
                points=[Point(0, 0), Point(20, 0), Point(20, 20), Point(0, 20)]
            )
        )
    ]
    window.canvas.set_contours(window.contours, center_on_platform=False)

    window._on_complexity_level_changed(ComplexityLevel.EXPERT)
    window._enter_print_order_mode()
    assert window.canvas.current_tool == "print_order"
    window._on_complexity_level_changed(ComplexityLevel.ADVANCED)
    assert window.canvas.current_tool == "select"

    window._on_start_point_tool()
    assert window.canvas.current_tool == "start_point"
    window._on_complexity_level_changed(ComplexityLevel.BASIC)
    assert window.canvas.current_tool == "select"

    window.deleteLater()
