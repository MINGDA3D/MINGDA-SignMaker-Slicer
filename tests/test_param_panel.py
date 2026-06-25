import pytest
from PySide6.QtCore import QFile, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.business.printer_profile_manager import DEFAULT_PRINTER_PROFILE_SPECS
from src.core.types import (
    ColorChangePoint,
    EdgeDirection,
    EdgeProfile,
    EdgeType,
    ManufacturingConstraintError,
    PrinterProfile,
    SliceParams,
    default_bed_exclude_area_for_bed,
    format_bed_exclude_area_for_editor,
    normalize_slice_params,
)
from src.ui.param_panel import ParamPanel
from src.ui.theme import set_active_theme
from src.ui.widgets import GuardedComboBox, GuardedDoubleSpinBox


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _owning_group(widget):
    current = widget.parentWidget()
    while current is not None and not isinstance(current, ParamPanel):
        if current.__class__.__name__ == "QGroupBox":
            return current
        current = current.parentWidget()
    return None


def _visible_group_titles(groups):
    return [
        group.title()
        for group in groups
        if hasattr(group, "title") and group.title()
    ]


def _group_by_title(groups, title):
    return next(
        group
        for group in groups
        if hasattr(group, "title") and group.title() == title
    )


def _dispatch_wheel(widget, delta_y: int = 120) -> None:
    event = QWheelEvent(
        QPointF(5, 5),
        QPointF(5, 5),
        QPoint(0, 0),
        QPoint(0, delta_y),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    QApplication.sendEvent(widget, event)
    QApplication.processEvents()


def _select_nozzle_profile(panel: ParamPanel, nozzle_diameter: float) -> None:
    spec = next(
        spec for spec in DEFAULT_PRINTER_PROFILE_SPECS
        if abs(spec["nozzle_diameter"] - nozzle_diameter) < 1e-9
    )
    index = panel.printer_profile_combo.findData(spec["id"])
    assert index >= 0
    panel.printer_profile_combo.setCurrentIndex(index)


def test_guarded_double_spinbox_ignores_wheel_until_focused(qapp):
    container = QWidget()
    layout = QVBoxLayout(container)
    blocker = QPushButton("blocker")
    spinbox = GuardedDoubleSpinBox()
    spinbox.setRange(0.0, 10.0)
    spinbox.setSingleStep(1.0)
    spinbox.setValue(5.0)
    layout.addWidget(blocker)
    layout.addWidget(spinbox)

    try:
        container.show()
        qapp.processEvents()

        blocker.setFocus()
        qapp.processEvents()
        assert spinbox.hasFocus() is False

        _dispatch_wheel(spinbox)
        assert spinbox.value() == pytest.approx(5.0)

        spinbox.setFocus()
        qapp.processEvents()
        assert spinbox.hasFocus() is True

        _dispatch_wheel(spinbox)
        assert spinbox.value() == pytest.approx(6.0)
    finally:
        container.close()


def test_guarded_combobox_ignores_wheel_until_focused(qapp):
    container = QWidget()
    layout = QVBoxLayout(container)
    blocker = QPushButton("blocker")
    combo = GuardedComboBox()
    combo.addItems(["A", "B", "C"])
    combo.setCurrentIndex(1)
    layout.addWidget(blocker)
    layout.addWidget(combo)

    try:
        container.show()
        qapp.processEvents()

        blocker.setFocus()
        qapp.processEvents()
        assert combo.hasFocus() is False

        _dispatch_wheel(combo)
        assert combo.currentIndex() == 1

        combo.setFocus()
        qapp.processEvents()
        assert combo.hasFocus() is True

        _dispatch_wheel(combo)
        assert combo.currentIndex() != 1
    finally:
        container.close()


def test_param_panel_uses_guarded_inputs_for_scroll_sensitive_controls(qapp):
    panel = ParamPanel()

    assert isinstance(panel.height_spin, GuardedDoubleSpinBox)
    assert isinstance(panel.wall_thickness_spin, GuardedDoubleSpinBox)
    assert isinstance(panel.edge_type_combo, GuardedComboBox)
    assert isinstance(panel.printer_profile_combo, GuardedComboBox)


def test_wall_thickness_control_uses_mm_without_exposing_wall_loops(qapp):
    panel = ParamPanel()

    panel.wall_thickness_spin.setValue(12.0)

    assert not hasattr(panel, "wall_count_spin")
    assert panel.wall_thickness_spin.value() == pytest.approx(12.0)


def test_user_visible_param_labels_hide_layer_counts_and_wall_loops(qapp):
    panel = ParamPanel()

    visible_text = "\n".join(
        label.text()
        for label in panel.findChildren(QLabel)
    )

    assert "Wall Loops:" not in visible_text
    assert "Bottom Layers:" not in visible_text
    assert "Bottom Shell Layers:" not in visible_text
    assert "Floor Layers:" not in visible_text
    assert "Top Shell Layers:" not in visible_text
    assert panel.wall_thickness_spin.suffix() == " mm"
    assert panel.bottom_face_thickness.suffix() == " mm"


def test_manufacturing_inputs_have_clear_tooltips(qapp):
    panel = ParamPanel()
    _select_nozzle_profile(panel, 0.8)
    panel.layer_height_spin.setValue(0.3)

    controls = [
        panel.height_spin,
        panel.layer_height_spin,
        panel.width_line_spin,
        panel.wall_thickness_spin,
        panel.baseplate_spin,
        panel.panel_thickness_spin,
        panel.bottom_face_thickness,
        panel.light_slot_depth,
        panel.light_slot_floor_layers,
        panel.top_face_thickness,
        panel.panel_step_height,
        panel.baseplate_step_height,
        panel.skirt_height,
        panel.connected_height,
        panel.connected_base_height,
    ]

    for control in controls:
        tooltip = control.toolTip()
        assert "Meaning:" in tooltip
        assert "Input requirements:" in tooltip

    assert "Current printable range: 0.60-1.20 mm" in panel.width_line_spin.toolTip()
    assert "0.60-60.00 mm" in panel.wall_thickness_spin.toolTip()
    assert "rounded up to the current layer-height grid" in panel.bottom_face_thickness.toolTip()

    panel.width_line_spin.setValue(1.1)

    assert "1.10-110.00 mm" in panel.wall_thickness_spin.toolTip()


def test_primary_groups_follow_requested_order(qapp):
    panel = ParamPanel()

    assert _visible_group_titles(panel._primary_groups) == [
        "Shell Settings",
        "Top Shell",
        "Acrylic Face Slot",
        "Bottom Shells",
        "Back Plate Slot",
        "LED Strip Slot",
        "Bottom Edge Wrap",
        "Anti-Warp Brim",
        "Letter Bridges",
        "DXF Export Compensation",
        "Speed Settings",
        "Temperature Settings",
        "Cooling Settings",
        "Color Change",
        "Prime Tower",
        "Printer Profile",
        "Machine G-code",
    ]


def test_profile_management_buttons_are_hidden_but_profile_fields_stay_editable(qapp):
    panel = ParamPanel()

    assert panel.profile_new_btn.isHidden() is True
    assert panel.profile_duplicate_btn.isHidden() is True
    assert panel.profile_rename_btn.isHidden() is True
    assert panel.profile_delete_btn.isHidden() is True
    assert panel.profile_default_btn.isHidden() is True

    assert panel.printer_profile_combo.isEnabled() is True
    assert panel.profile_bed_width.isEnabled() is True
    assert panel.profile_color_change_template.isEnabled() is True
    assert panel.edit_start_gcode_btn.isEnabled() is True
    assert panel.edit_end_gcode_btn.isEnabled() is True


def test_profile_selector_does_not_show_default_suffix(qapp):
    panel = ParamPanel()

    combo_labels = [
        panel.printer_profile_combo.itemText(index)
        for index in range(panel.printer_profile_combo.count())
    ]

    assert not any("(Default)" in label for label in combo_labels)
    assert DEFAULT_PRINTER_PROFILE_SPECS[0]["name"] in combo_labels


def test_switching_profile_updates_layer_height_and_width_line_when_nozzle_changes(qapp):
    panel = ParamPanel()

    _select_nozzle_profile(panel, 0.4)
    panel.layer_height_spin.setValue(0.2)
    panel.width_line_spin.setValue(0.4)

    _select_nozzle_profile(panel, 0.6)

    assert panel.profile_nozzle_diameter.value() == pytest.approx(0.6)
    assert panel.layer_height_spin.value() == pytest.approx(0.3)
    assert panel.width_line_spin.value() == pytest.approx(0.6)
    assert panel.get_params().shell.layer_height == pytest.approx(0.3)
    assert panel.get_params().shell.line_width == pytest.approx(0.6)


def test_set_params_keeps_active_printer_profile_machine_fields(qapp):
    panel = ParamPanel()
    mini_spec = DEFAULT_PRINTER_PROFILE_SPECS[0]
    index = panel.printer_profile_combo.findData(mini_spec["id"])
    assert index >= 0
    panel.printer_profile_combo.setCurrentIndex(index)

    params = SliceParams()
    params.machine.name = "MIGNDA AD-F4 0.8mm Nozzle"
    params.machine.bed_width = 800.0
    params.machine.bed_depth = 1200.0
    params.machine.bed_height = 100.0
    params.machine.nozzle_diameter = 0.8
    params.machine.bed_exclude_area = default_bed_exclude_area_for_bed(800.0, 1200.0)

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.printer_profile_combo.currentData() == mini_spec["id"]
    assert panel.profile_bed_width.value() == pytest.approx(600.0)
    assert panel.profile_bed_depth.value() == pytest.approx(800.0)
    assert panel.profile_nozzle_diameter.value() == pytest.approx(0.4)
    assert panel.profile_bed_exclude_area.toPlainText() == format_bed_exclude_area_for_editor(
        default_bed_exclude_area_for_bed(600.0, 800.0)
    )
    assert restored.machine.bed_width == pytest.approx(600.0)
    assert restored.machine.bed_depth == pytest.approx(800.0)
    assert restored.machine.nozzle_diameter == pytest.approx(0.4)


def test_print_summary_labels_and_color_change_preview_column_can_shrink_in_narrow_sidebar(qapp):
    panel = ParamPanel()

    assert panel.klipper_commands_group.title() == "Machine G-code"
    assert panel.start_gcode_title.text() == "Machine start G-code"
    assert panel.end_gcode_title.text() == "Machine end G-code"
    assert panel.color_change_hint.wordWrap() is True
    assert panel.color_change_hint.minimumWidth() == 0
    assert panel.color_change_summary.minimumWidth() == 0
    assert isinstance(panel.start_gcode_summary, QPlainTextEdit)
    assert panel.start_gcode_summary.isReadOnly() is True
    assert (
        panel.start_gcode_summary.lineWrapMode()
        == QPlainTextEdit.LineWrapMode.WidgetWidth
    )
    assert panel.start_gcode_summary.minimumHeight() >= 88
    assert isinstance(panel.end_gcode_summary, QPlainTextEdit)
    assert (
        panel.color_change_table.horizontalHeader().sectionResizeMode(2)
        == QHeaderView.ResizeMode.Stretch
    )


def test_machine_gcode_preview_editors_refresh_when_theme_changes(qapp):
    set_active_theme("dark")
    panel = ParamPanel()
    try:
        assert "#0D1117" in panel.start_gcode_summary.styleSheet()

        set_active_theme("light")
        panel.apply_theme()

        assert "#F6F8FB" in panel.start_gcode_summary.styleSheet()
        assert "#F6F8FB" in panel.end_gcode_summary.styleSheet()
        assert "#0D1117" not in panel.start_gcode_summary.styleSheet()
    finally:
        panel.deleteLater()
        set_active_theme("system")


def test_color_change_preview_cells_are_centered_and_action_buttons_split_to_edges(qapp):
    panel = ParamPanel()

    panel.color_enabled.setChecked(True)
    panel._insert_color_change_row(ColorChangePoint(height_mm=0.3, macro_index=1))

    preview_item = panel.color_change_table.item(0, 2)

    assert preview_item is not None
    assert preview_item.textAlignment() == int(Qt.AlignmentFlag.AlignCenter)
    assert panel.color_change_actions_layout.itemAt(0).widget() is panel.add_color_change_btn
    assert panel.color_change_actions_layout.itemAt(1).spacerItem() is not None
    assert panel.color_change_actions_layout.itemAt(2).widget() is panel.remove_color_change_btn


def test_primary_sections_separate_shape_machine_and_print_settings(qapp):
    panel = ParamPanel()

    assert [
        (section["key"], section["title"], _visible_group_titles(section["groups"]))
        for section in panel._primary_sections
    ] == [
        (
            "shape",
            "Shape",
            [
                "Shell Settings",
                "Top Shell",
                "Acrylic Face Slot",
                "Bottom Shells",
                "Back Plate Slot",
                "LED Strip Slot",
                "Bottom Edge Wrap",
                "Anti-Warp Brim",
                "Letter Bridges",
                "DXF Export Compensation",
            ],
        ),
        (
            "machine",
            "Machine",
            [
                "Printer Profile",
            ],
        ),
        (
            "print",
            "Print",
            [
                "Speed Settings",
                "Temperature Settings",
                "Cooling Settings",
                "Color Change",
                "Prime Tower",
                "Machine G-code",
            ],
        ),
    ]


def test_primary_tabs_default_to_shape_and_switch_between_pages(qapp):
    panel = ParamPanel()

    assert isinstance(panel.primary_tabs, QTabWidget)
    assert panel._primary_tabs is panel.primary_tabs
    assert [panel.primary_tabs.tabText(index) for index in range(panel.primary_tabs.count())] == [
        "Shape",
        "Machine",
        "Print",
    ]
    assert panel.primary_tabs.currentIndex() == 0
    assert panel.primary_tabs.currentWidget() is panel._section_widgets_by_key["shape"]
    assert all(
        isinstance(panel._section_widgets_by_key[key], QScrollArea)
        for key in ("shape", "machine", "print")
    )

    machine_index = panel.primary_tabs.indexOf(panel._section_widgets_by_key["machine"])
    print_index = panel.primary_tabs.indexOf(panel._section_widgets_by_key["print"])

    panel.primary_tabs.setCurrentIndex(machine_index)
    assert panel.primary_tabs.currentWidget() is panel._section_widgets_by_key["machine"]

    panel.primary_tabs.setCurrentIndex(print_index)
    assert panel.primary_tabs.currentWidget() is panel._section_widgets_by_key["print"]


def test_shape_page_places_shell_settings_before_feature_tabs(qapp):
    panel = ParamPanel()
    shape_content = panel._section_widgets_by_key["shape"]._content
    shape_layout = shape_content.layout()

    assert shape_layout.itemAt(0).widget() is panel.shell_group
    assert shape_layout.itemAt(1).widget() is panel.shape_feature_tabs
    assert panel.shape_feature_tabs.objectName() == "shape_feature_tabs"
    assert [
        panel.shape_feature_tabs.tabText(index)
        for index in range(panel.shape_feature_tabs.count())
    ] == ["Wall", "Bottom", "Top", "Other"]
    assert all(
        panel.shape_feature_tabs.tabIcon(index).isNull()
        for index in range(panel.shape_feature_tabs.count())
    )

    panel.resize(420, 480)
    panel.show()
    QApplication.processEvents()

    tab_bar = panel.shape_feature_tabs.tabBar()
    widths = [
        tab_bar.tabRect(index).width()
        for index in range(tab_bar.count())
    ]
    assert tab_bar.expanding() is True
    assert max(widths) - min(widths) <= 1


def test_shape_feature_tabs_group_controls_by_mode(qapp):
    panel = ParamPanel()

    assert [
        (section["key"], section["title"], _visible_group_titles(section["groups"]))
        for section in panel._shape_feature_sections
    ] == [
        ("wall", "Wall", []),
        (
            "bottom",
            "Bottom",
            [
                "Bottom Shells",
                "Back Plate Slot",
                "LED Strip Slot",
                "Bottom Edge Wrap",
            ],
        ),
        ("top", "Top", ["Top Shell", "Acrylic Face Slot"]),
        ("other", "Other", ["Anti-Warp Brim", "Letter Bridges", "DXF Export Compensation"]),
    ]


def test_wall_tab_starts_with_edge_type_icons_without_card_title(qapp):
    panel = ParamPanel()
    wall_page = panel._shape_feature_widgets_by_key["wall"]
    wall_layout = wall_page.layout()
    edge_layout = panel.edge_group.layout()

    assert panel.edge_group.objectName() == "wall_edge_type_panel"
    assert not hasattr(panel.edge_group, "title")
    assert wall_layout.itemAt(0).widget() is panel.edge_group
    assert edge_layout.contentsMargins().left() == 0
    assert edge_layout.itemAt(0).widget() is panel.wall_mode_widget


def test_wall_mode_buttons_sync_edge_type_and_parameter_visibility(qapp):
    panel = ParamPanel()

    assert panel.edge_type_combo.isHidden() is True
    assert panel.wall_mode_group.checkedId() == 0
    assert panel.preset_selector.get_selected_preset() == ""

    panel.wall_mode_group.button(1).click()
    assert panel.edge_type_combo.currentData() == EdgeType.BEVELED
    assert panel.bevel_params_widget.isHidden() is False
    assert panel.custom_edge_widget.isHidden() is True
    assert panel.get_params().shell.edge_type == EdgeType.BEVELED

    panel.wall_mode_group.button(2).click()
    assert panel.edge_type_combo.currentData() == EdgeType.CUSTOM
    assert panel.bevel_params_widget.isHidden() is True
    assert panel.custom_edge_widget.isHidden() is False

    panel.wall_mode_group.button(0).click()
    assert panel.edge_type_combo.currentData() == EdgeType.STRAIGHT
    assert panel.bevel_params_widget.isHidden() is True
    assert panel.custom_edge_widget.isHidden() is True


def test_custom_wall_preset_selection_survives_param_restore(qapp):
    panel = ParamPanel()
    preset_names = list(panel.preset_selector._thumbnails.keys())
    target_preset = preset_names[2]

    panel.wall_mode_group.button(2).click()
    panel.preset_selector._on_thumbnail_clicked(target_preset)

    params = panel.get_params()
    assert params.shell.edge_type == EdgeType.CUSTOM
    assert params.shell.edge_profile is not None
    assert params.shell.edge_profile.preset_name == target_preset

    restored_panel = ParamPanel()
    restored_panel.set_params(params)
    restored = restored_panel.get_params()

    assert restored_panel.edge_type_combo.currentData() == EdgeType.CUSTOM
    assert restored_panel.preset_selector.get_selected_preset() == target_preset
    assert restored.shell.edge_profile is not None
    assert restored.shell.edge_profile.preset_name == target_preset


def test_imported_custom_edge_profile_does_not_show_default_preset_selected(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.shell.edge_type = EdgeType.CUSTOM
    params.shell.edge_profile = EdgeProfile.from_control_points(
        [(0.0, 0.0), (0.4, 0.5), (1.0, 1.0)],
        name="Imported DXF",
    )

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.preset_selector.get_selected_preset() == ""
    assert restored.shell.edge_profile is not None
    assert restored.shell.edge_profile.preset_name == ""
    assert restored.shell.edge_profile.name == "Imported DXF"


def test_legacy_preset_profile_without_preset_name_restores_thumbnail(qapp):
    panel = ParamPanel()
    target_preset = list(panel.preset_selector._thumbnails.keys())[2]
    params = SliceParams()
    params.shell.edge_type = EdgeType.CUSTOM
    params.shell.edge_profile = EdgeProfile.from_preset(target_preset)
    params.shell.edge_profile.preset_name = ""

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.preset_selector.get_selected_preset() == target_preset
    assert restored.shell.edge_profile is not None
    assert restored.shell.edge_profile.preset_name == target_preset


def test_top_mode_buttons_are_exclusive_and_write_back_to_params(qapp):
    panel = ParamPanel()

    panel.top_mode_group.button(panel.TOP_MODE_PANEL_V_GROOVE).click()
    params = panel.get_params()

    assert panel.top_face_enabled.isChecked() is False
    assert panel.panel_step_enabled.isChecked() is True
    assert panel.panel_step_v_groove.isChecked() is True
    assert panel.top_face_group.isHidden() is True
    assert panel.panel_step_group.isHidden() is False
    assert params.top_face.enabled is False
    assert params.step.panel_step_enabled is True
    assert params.step.panel_step_is_v_groove is True

    panel.top_mode_group.button(panel.TOP_MODE_FACE).click()
    params = panel.get_params()

    assert panel.top_face_enabled.isChecked() is True
    assert panel.panel_step_enabled.isChecked() is False
    assert panel.panel_step_v_groove.isChecked() is False
    assert params.top_face.enabled is True
    assert params.step.panel_step_enabled is False


def test_bottom_mode_buttons_are_exclusive_and_write_back_to_params(qapp):
    panel = ParamPanel()

    panel.bottom_mode_group.button(panel.BOTTOM_MODE_BASEPLATE_V_GROOVE).click()
    params = panel.get_params()

    assert panel.bottom_face_enabled.isChecked() is False
    assert panel.baseplate_step_enabled.isChecked() is True
    assert panel.baseplate_step_v_groove.isChecked() is True
    assert panel.light_slot_enabled.isChecked() is False
    assert params.bottom_face.enabled is False
    assert params.step.baseplate_step_enabled is True
    assert params.step.baseplate_step_is_v_groove is True

    panel.bottom_mode_group.button(panel.BOTTOM_MODE_OUTLINE).click()
    params = panel.get_params()

    assert panel.baseplate_step_enabled.isChecked() is False
    assert panel.light_slot_enabled.isChecked() is False
    assert panel.wrap_enabled.isChecked() is False
    assert panel.outline_enabled.isChecked() is True
    assert params.step.baseplate_step_enabled is False
    assert params.light_slot.enabled is False
    assert params.edge_wrap.wrap_enabled is False
    assert params.edge_wrap.outline_enabled is True


def test_edge_wrap_bottom_mode_only_shows_matching_option_set(qapp):
    panel = ParamPanel()

    panel.bottom_mode_group.button(panel.BOTTOM_MODE_EDGE_WRAP).click()

    assert panel.edge_wrap_group.isHidden() is False
    assert panel.wrap_options_widget.isHidden() is False
    assert panel.outline_options_widget.isHidden() is True
    assert panel.wrap_outline_separator.isHidden() is True

    panel.bottom_mode_group.button(panel.BOTTOM_MODE_OUTLINE).click()

    assert panel.edge_wrap_group.isHidden() is False
    assert panel.wrap_options_widget.isHidden() is True
    assert panel.outline_options_widget.isHidden() is False
    assert panel.wrap_outline_separator.isHidden() is True


def test_set_params_resolves_legacy_bottom_modes_by_priority(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.bottom_face.enabled = True
    params.step.baseplate_step_enabled = True
    params.step.baseplate_step_is_v_groove = True
    params.light_slot.enabled = True
    params.edge_wrap.wrap_enabled = True
    params.edge_wrap.outline_enabled = True

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.bottom_mode_group.checkedId() == panel.BOTTOM_MODE_FACE
    assert restored.bottom_face.enabled is True
    assert restored.step.baseplate_step_enabled is False
    assert restored.light_slot.enabled is False
    assert restored.edge_wrap.wrap_enabled is False
    assert restored.edge_wrap.outline_enabled is False

    params = SliceParams()
    params.step.baseplate_step_enabled = True
    params.step.baseplate_step_is_v_groove = True
    params.light_slot.enabled = True
    params.edge_wrap.wrap_enabled = True
    params.edge_wrap.outline_enabled = True

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.bottom_mode_group.checkedId() == panel.BOTTOM_MODE_BASEPLATE_V_GROOVE
    assert restored.bottom_face.enabled is False
    assert restored.step.baseplate_step_enabled is True
    assert restored.step.baseplate_step_is_v_groove is True
    assert restored.light_slot.enabled is False
    assert restored.edge_wrap.wrap_enabled is False
    assert restored.edge_wrap.outline_enabled is False


def test_primary_tabs_and_parameter_icons_are_loaded(qapp):
    panel = ParamPanel()

    assert all(
        not panel.primary_tabs.tabIcon(index).isNull()
        for index in range(panel.primary_tabs.count())
    )
    for icon_name in (
        "shape",
        "machine",
        "print",
        "shell_height",
        "layer",
        "line-width",
        "wall_thickness",
        "speed",
        "nozzle_temp",
        "bed_temp",
        "fan",
        "top-step-height",
        "bottom-step-height",
        "top-step-width",
        "bottom-step-width",
    ):
        assert not panel._icon(icon_name).isNull()


def test_primary_tabs_are_equal_width_with_centered_custom_paint(qapp):
    panel = ParamPanel()
    panel.resize(400, 260)
    panel.show()
    QApplication.processEvents()

    tab_bar = panel.primary_tabs.tabBar()
    widths = [
        tab_bar.tabRect(index).width()
        for index in range(tab_bar.count())
    ]

    assert tab_bar.expanding() is True
    assert max(widths) - min(widths) <= 1
    assert not tab_bar.grab().isNull()


def test_parameter_icon_labels_preserve_original_text(qapp):
    panel = ParamPanel()

    visible_text = {
        label.text()
        for label in panel.findChildren(QLabel)
    }

    assert "Shell Height:" in visible_text
    assert "Face Slot Drop:" in visible_text
    assert "Back Plate Slot Height:" in visible_text
    assert "Face Slot Width:" in visible_text
    assert "Back Plate Slot Width:" in visible_text
    assert "Brim Speed:" in visible_text


def test_prime_tower_controls_roundtrip_through_print_settings(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.machine.bed_width = 600.0
    params.machine.bed_depth = 900.0
    params.prime_tower.enabled = True
    params.prime_tower.center_x = 540.0
    params.prime_tower.center_y = 820.0
    params.prime_tower.width = 60.0
    params.prime_tower.depth = 40.0
    params.prime_tower.infill_density_percent = 35

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.prime_tower_group.title() == "Prime Tower"
    assert panel.prime_tower_enabled.isChecked() is True
    assert panel.prime_tower_center_x.isEnabled() is True
    assert panel.prime_tower_center_y.isEnabled() is True
    assert panel.prime_tower_width.isEnabled() is True
    assert panel.prime_tower_depth.isEnabled() is True
    assert panel.prime_tower_infill_density.isEnabled() is True
    assert panel.prime_tower_infill_density.minimum() == 10
    assert panel.prime_tower_infill_density.maximum() == 80
    assert panel.prime_tower_infill_density.singleStep() == 5
    assert restored.prime_tower.enabled is True
    assert restored.prime_tower.center_x == pytest.approx(540.0)
    assert restored.prime_tower.center_y == pytest.approx(820.0)
    assert restored.prime_tower.width == pytest.approx(60.0)
    assert restored.prime_tower.depth == pytest.approx(40.0)
    assert restored.prime_tower.infill_density_percent == 35


def test_step_controls_are_split_between_top_and_bottom_groups(qapp):
    panel = ParamPanel()

    assert panel.step_group is panel.panel_step_group
    assert panel.panel_step_group.title() == "Acrylic Face Slot"
    assert panel.baseplate_step_group.title() == "Back Plate Slot"
    assert _owning_group(panel.panel_step_enabled) is panel.panel_step_group
    assert _owning_group(panel.baseplate_step_enabled) is panel.baseplate_step_group

    panel.top_mode_group.button(panel.TOP_MODE_PANEL_V_GROOVE).click()
    assert panel.panel_step_group.title() == "Acrylic Face V-Groove"

    panel.bottom_mode_group.button(panel.BOTTOM_MODE_BASEPLATE_V_GROOVE).click()
    assert panel.baseplate_step_group.title() == "Back Plate V-Groove"


def test_set_params_restores_wrap_controls_enabled_state(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.edge_wrap.wrap_enabled = True
    params.edge_wrap.wrap_direction = EdgeDirection.OUTER

    panel.set_params(params)

    assert panel.wrap_enabled.isChecked() is True
    assert panel.edge_wrap_group.title() == "Bottom Edge Wrap"
    assert panel.wrap_width.isEnabled() is True
    assert panel.wrap_height.isEnabled() is True
    assert panel.wrap_dir_inner.isEnabled() is True
    assert panel.wrap_dir_outer.isEnabled() is True


def test_wrap_direction_uses_exclusive_icon_buttons(qapp):
    panel = ParamPanel()

    panel.bottom_mode_group.button(panel.BOTTOM_MODE_EDGE_WRAP).click()
    assert panel.wrap_dir_inner.isEnabled() is True
    assert panel.wrap_dir_outer.isEnabled() is True
    assert panel.wrap_dir_group.checkedId() == 0

    panel.wrap_dir_outer.click()
    params = panel.get_params()

    assert panel.wrap_dir_group.checkedId() == 1
    assert panel.wrap_dir_inner.isChecked() is False
    assert panel.wrap_dir_outer.isChecked() is True
    assert params.edge_wrap.wrap_direction == EdgeDirection.OUTER


def test_wrap_size_icons_are_registered(qapp):
    assert QFile.exists(":/icons/icons/params/wrap_width.svg") is True
    assert QFile.exists(":/icons/icons/params/wrap_height.svg") is True


def test_outline_size_icons_are_registered(qapp):
    assert QFile.exists(":/icons/icons/params/outline_width.svg") is True
    assert QFile.exists(":/icons/icons/params/outline_height.svg") is True


def test_light_slot_scope_icons_are_registered(qapp):
    assert QFile.exists(":/icons/icons/params/outer-slot.svg") is True
    assert QFile.exists(":/icons/icons/params/hole-slot.svg") is True


def test_shell_height_icon_is_registered(qapp):
    assert QFile.exists(":/icons/icons/params/shell_height.svg") is True


def test_temperature_settings_roundtrip_through_print_settings(qapp):
    panel = ParamPanel()

    panel.first_layer_nozzle_temp.setValue(235)
    panel.other_layer_nozzle_temp.setValue(220)
    panel.first_layer_bed_temp.setValue(65)
    panel.other_layer_bed_temp.setValue(55)

    params = panel.get_params()

    assert panel.temperature_group.title() == "Temperature Settings"
    assert params.gcode.first_layer_nozzle_temp == 235
    assert params.gcode.other_layer_nozzle_temp == 220
    assert params.gcode.first_layer_bed_temp == 65
    assert params.gcode.other_layer_bed_temp == 55


def test_cooling_settings_roundtrip_through_print_settings(qapp):
    panel = ParamPanel()

    panel.first_layer_fan_percent.setValue(30)
    panel.other_layer_fan_percent.setValue(75)

    params = panel.get_params()

    assert panel.cooling_group.title() == "Cooling Settings"
    assert params.gcode.first_layer_fan_percent == 30
    assert params.gcode.other_layer_fan_percent == 75


def test_cooling_settings_default_to_first_layer_off_and_other_layers_full_speed(qapp):
    panel = ParamPanel()
    params = panel.get_params()

    assert panel.first_layer_fan_percent.value() == 0
    assert panel.other_layer_fan_percent.value() == 100
    assert params.gcode.first_layer_fan_percent == 0
    assert params.gcode.other_layer_fan_percent == 100


def test_width_line_defaults_to_twice_layer_height_and_updates_with_layer_height(qapp):
    panel = ParamPanel()

    assert panel.width_line_spin.value() == pytest.approx(0.6)

    panel.layer_height_spin.setValue(0.4)

    assert panel.width_line_spin.value() == pytest.approx(0.8)


def test_vector_defaults_match_requested_values(qapp):
    panel = ParamPanel()
    params = panel.get_params()

    assert panel.height_spin.value() == pytest.approx(50.1)
    assert panel.layer_height_spin.value() == pytest.approx(0.3)
    assert panel.width_line_spin.value() == pytest.approx(0.6)
    assert panel.wall_thickness_spin.value() == pytest.approx(1.2)
    assert panel.edge_type_combo.currentData() == EdgeType.STRAIGHT
    assert panel.bevel_params_widget.isHidden() is True
    assert panel.panel_step_enabled.isChecked() is False
    assert panel.baseplate_step_enabled.isChecked() is False
    assert panel.skirt_enabled.isChecked() is False
    assert panel.connected_enabled.isChecked() is False
    assert panel.bevel_width_spin.value() == pytest.approx(5.0)
    assert panel.baseplate_spin.value() == pytest.approx(9.0)
    assert panel.panel_thickness_spin.value() == pytest.approx(9.0)
    assert panel.wrap_width.value() == pytest.approx(3.0)
    assert panel.wrap_height.value() == pytest.approx(3.0)
    assert panel.outline_width.value() == pytest.approx(3.0)
    assert panel.outline_height.value() == pytest.approx(3.0)
    assert panel.outline_offset.value() == pytest.approx(0.0)
    assert panel.panel_step_height.value() == pytest.approx(3.0)
    assert panel.baseplate_step_height.value() == pytest.approx(3.0)
    assert panel.skirt_height.value() == pytest.approx(0.3)
    assert panel.skirt_offset.value() == pytest.approx(0.12)
    assert panel.top_face_thickness.value() == pytest.approx(2.4)
    assert panel.bottom_face_thickness.value() == pytest.approx(0.9)
    assert panel.bottom_face_screw_hole_diameter.value() == pytest.approx(5.0)
    assert panel.connected_type.currentData() == "triangle"
    assert panel.connected_width.value() == pytest.approx(5.0)
    assert panel.connected_height.value() == pytest.approx(4.5)
    assert panel.connected_base_height.value() == pytest.approx(4.5)
    assert panel.connected_support_offset.value() == pytest.approx(2.5)
    assert panel.light_slot_width.value() == pytest.approx(7.8)
    assert panel.light_slot_depth.value() == pytest.approx(6.0)
    assert panel.light_slot_floor_layers.value() == pytest.approx(1.5)
    assert panel.light_slot_wall_gap.value() == pytest.approx(0.0)
    assert panel.light_slot_wall_gap.isHidden() is True

    assert params.shell.height == pytest.approx(50.1)
    assert params.shell.wall_count == 2
    assert params.shell.line_width == pytest.approx(0.6)
    assert params.shell.wall_thickness == pytest.approx(1.2)
    assert params.shell.edge_type == EdgeType.STRAIGHT
    assert params.step.panel_step_enabled is False
    assert params.step.baseplate_step_enabled is False
    assert params.skirt.enabled is False
    assert params.connected.enabled is False
    assert params.shell.baseplate_thickness == pytest.approx(9.0)
    assert params.shell.panel_thickness == pytest.approx(9.0)
    assert params.step.panel_step_height == pytest.approx(47.1)
    assert params.step.baseplate_step_height == pytest.approx(3.0)
    assert params.top_face.thickness == pytest.approx(2.4)
    assert params.bottom_face.thickness == pytest.approx(0.9)
    assert params.bottom_face.screw_hole_diameter == pytest.approx(5.0)
    assert params.connected.height == pytest.approx(4.5)
    assert params.connected.base_height == pytest.approx(4.5)
    assert params.light_slot.width == pytest.approx(7.8)
    assert params.light_slot.depth == pytest.approx(6.0)
    assert params.light_slot.floor_layers == 5


def test_width_line_can_be_manually_overridden_and_layer_height_change_recomputes_it(qapp):
    panel = ParamPanel()
    _select_nozzle_profile(panel, 0.8)
    panel.layer_height_spin.setValue(0.3)

    panel.width_line_spin.setValue(1.1)
    assert panel.width_line_spin.value() == pytest.approx(1.1)
    assert panel.get_params().shell.line_width == pytest.approx(1.1)
    assert panel.get_params().shell.wall_thickness == pytest.approx(2.2)

    panel.layer_height_spin.setValue(0.25)

    assert panel.width_line_spin.value() == pytest.approx(0.6)


def test_shell_height_does_not_change_when_layer_height_changes(qapp):
    panel = ParamPanel()

    panel.height_spin.setValue(30.0)
    panel.layer_height_spin.setValue(0.5)

    assert panel.height_spin.value() == pytest.approx(30.0)
    assert panel.get_params().shell.height == pytest.approx(30.0)


def test_shell_height_is_clamped_to_100mm(qapp):
    panel = ParamPanel()

    panel.height_spin.setValue(120.0)

    assert panel.height_spin.value() == pytest.approx(100.0)
    assert panel.get_params().shell.height == pytest.approx(100.0)


def test_set_params_restores_explicit_shell_line_width(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.shell.layer_height = 0.5
    params.shell.line_width = 1.1
    params.shell.wall_count = 2

    panel.set_params(params)

    assert panel.width_line_spin.value() == pytest.approx(1.1)


def test_wall_thickness_resolves_wall_count_and_actual_line_width(qapp):
    panel = ParamPanel()

    _select_nozzle_profile(panel, 0.8)
    panel.layer_height_spin.setValue(0.3)
    panel.width_line_spin.setValue(0.6)
    panel.wall_thickness_spin.setValue(1.3)

    params = panel.get_params()

    assert panel.wall_thickness_spin.value() == pytest.approx(1.8)
    assert params.shell.wall_count == 3
    assert params.shell.line_width == pytest.approx(0.6)
    assert params.shell.wall_thickness == pytest.approx(1.8)


def test_z_height_inputs_snap_up_to_printable_mm(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.3)
    panel.bottom_face_enabled.setChecked(True)
    panel.bottom_face_thickness.setValue(1.0)

    params = panel.get_params()

    assert panel.bottom_face_thickness.value() == pytest.approx(1.2)
    assert params.bottom_face.thickness == pytest.approx(1.2)


def test_wall_thickness_below_one_line_snaps_up_to_line_width(qapp):
    params = SliceParams()
    params.shell.wall_thickness = 0.4
    params.shell.line_width = 0.6
    params.shell.layer_height = 0.3
    params.machine.nozzle_diameter = 0.8

    normalized = normalize_slice_params(params)

    assert normalized.shell.wall_count == 1
    assert normalized.shell.line_width == pytest.approx(0.6)
    assert normalized.shell.wall_thickness == pytest.approx(0.6)


def test_wall_thickness_above_loop_limit_is_rejected(qapp):
    params = SliceParams()
    params.shell.wall_thickness = 60.1
    params.shell.line_width = 0.6
    params.shell.layer_height = 0.3
    params.machine.nozzle_diameter = 0.8

    with pytest.raises(ManufacturingConstraintError, match="0.60-60.00 mm"):
        normalize_slice_params(params)


def test_param_panel_preserves_too_large_wall_thickness_until_strict_validation(qapp):
    panel = ParamPanel()

    _select_nozzle_profile(panel, 0.8)
    panel.layer_height_spin.setValue(0.3)
    panel.width_line_spin.setValue(0.6)
    panel.wall_thickness_spin.setValue(60.1)

    params = panel.get_params()

    assert panel.wall_thickness_spin.value() == pytest.approx(60.1)
    assert params.shell.wall_thickness == pytest.approx(60.1)
    with pytest.raises(ManufacturingConstraintError, match="0.60-60.00 mm"):
        normalize_slice_params(params)


@pytest.mark.parametrize("line_width", [0.4, 1.3])
def test_invalid_line_width_is_rejected_for_default_nozzle_and_layer_height(
    qapp,
    line_width,
):
    params = SliceParams()
    params.shell.wall_thickness = 1.2
    params.shell.line_width = line_width
    params.shell.layer_height = 0.3
    params.machine.nozzle_diameter = 0.8

    with pytest.raises(ManufacturingConstraintError, match="0.60-1.20 mm"):
        normalize_slice_params(params)


def test_set_params_displays_legacy_wall_fields_as_mm_thickness(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.shell.layer_height = 0.5
    params.shell.line_width = 1.1
    params.shell.wall_count = 2

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.width_line_spin.value() == pytest.approx(1.1)
    assert panel.wall_thickness_spin.value() == pytest.approx(2.2)
    assert restored.shell.wall_count == 2
    assert restored.shell.line_width == pytest.approx(1.1)
    assert restored.shell.wall_thickness == pytest.approx(2.2)


def test_set_params_restores_outline_controls_enabled_state(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.edge_wrap.outline_enabled = True
    params.edge_wrap.outline_direction = EdgeDirection.OUTER

    panel.set_params(params)

    assert panel.outline_enabled.isChecked() is True
    assert panel.outline_width.isEnabled() is True
    assert panel.outline_height.isEnabled() is True
    assert panel.outline_offset.isEnabled() is False
    assert panel.outline_offset.isHidden() is True
    assert panel.outline_dir_inner.isEnabled() is True
    assert panel.outline_dir_outer.isEnabled() is True


def test_outline_offset_is_hidden_but_preserved(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.edge_wrap.outline_enabled = True
    params.edge_wrap.outline_offset = 1.5

    panel.set_params(params)
    labels = {label.text() for label in panel.edge_wrap_group.findChildren(QLabel)}
    restored = panel.get_params()

    assert "Outline Offset:" not in labels
    assert panel.outline_offset.isHidden() is True
    assert panel.outline_offset.isEnabled() is False
    assert restored.edge_wrap.outline_offset == pytest.approx(1.5)


def test_outline_direction_uses_exclusive_icon_buttons(qapp):
    panel = ParamPanel()

    panel.bottom_mode_group.button(panel.BOTTOM_MODE_OUTLINE).click()
    assert panel.edge_wrap_group.title() == "Bottom Outline"
    assert panel.outline_dir_inner.isEnabled() is True
    assert panel.outline_dir_outer.isEnabled() is True
    assert panel.outline_dir_inner.icon().isNull() is False
    assert panel.outline_dir_outer.icon().isNull() is False
    assert panel.outline_dir_group.checkedId() == 0

    panel.outline_dir_outer.click()
    params = panel.get_params()

    assert panel.outline_dir_group.checkedId() == 1
    assert panel.outline_dir_inner.isChecked() is False
    assert panel.outline_dir_outer.isChecked() is True
    assert params.edge_wrap.outline_direction == EdgeDirection.OUTER


def test_wrap_outline_mutual_exclusive_updates_control_enabled_state(qapp):
    panel = ParamPanel()

    panel.outline_enabled.setChecked(True)
    assert panel.outline_width.isEnabled() is True

    panel.wrap_enabled.setChecked(True)

    assert panel.wrap_enabled.isChecked() is True
    assert panel.outline_enabled.isChecked() is False
    assert panel.wrap_width.isEnabled() is True
    assert panel.wrap_height.isEnabled() is True
    assert panel.outline_width.isEnabled() is False
    assert panel.outline_height.isEnabled() is False
    assert panel.outline_offset.isEnabled() is False


def test_skirt_group_hides_legacy_fields_and_moves_speed_to_print_settings(qapp):
    panel = ParamPanel()
    skirt_group = _group_by_title(panel._primary_groups, "Anti-Warp Brim")
    speed_group = _group_by_title(panel._primary_groups, "Speed Settings")

    skirt_labels = {label.text() for label in skirt_group.findChildren(QLabel)}
    speed_labels = {label.text() for label in speed_group.findChildren(QLabel)}

    assert "Brim Height:" in skirt_labels
    assert "Breakaway Gap:" in skirt_labels
    assert "Brim Speed:" not in skirt_labels
    assert "Skirt Width:" not in skirt_labels
    assert "Trapezoid Interval:" not in skirt_labels
    assert "Brim Speed:" in speed_labels
    assert _owning_group(panel.skirt_speed) is panel.speed_group


def test_connected_group_hides_support_offset_compat_field(qapp):
    panel = ParamPanel()
    connected_group = _group_by_title(panel._primary_groups, "Letter Bridges")

    connected_labels = {label.text() for label in connected_group.findChildren(QLabel)}

    assert "Bridge Support Offset:" not in connected_labels
    assert panel.connected_support_offset.isHidden() is True
    assert panel.connected_support_offset.isEnabled() is False

    panel.connected_enabled.setChecked(True)

    assert panel.connected_support_offset.isHidden() is True
    assert panel.connected_support_offset.isEnabled() is False


def test_step_group_keeps_geometry_fields_and_moves_speed_to_print_settings(qapp):
    panel = ParamPanel()
    top_step_group = _group_by_title(panel._primary_groups, "Acrylic Face Slot")
    bottom_step_group = _group_by_title(panel._primary_groups, "Back Plate Slot")
    speed_group = _group_by_title(panel._primary_groups, "Speed Settings")

    step_labels = {
        label.text()
        for group in (top_step_group, bottom_step_group)
        for label in group.findChildren(QLabel)
    }
    speed_labels = {label.text() for label in speed_group.findChildren(QLabel)}

    assert "Face Slot Drop:" in step_labels
    assert "Back Plate Slot Height:" in step_labels
    assert "Face Slot Width:" in step_labels
    assert "Back Plate Slot Width:" in step_labels
    assert "Slot/V-Groove Speed:" not in step_labels
    assert "Slot/V-Groove Speed:" in speed_labels
    assert _owning_group(panel.step_speed) is panel.speed_group


def test_hidden_skirt_width_interval_and_visible_speed_are_preserved(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.skirt.enabled = True
    params.skirt.width = 7.5
    params.skirt.interval = 18.0
    params.skirt.height = 0.6
    params.skirt.speed = 23.0
    params.skirt.offset = 0.8

    panel.set_params(params)
    panel.skirt_speed.setValue(26.0)
    panel.skirt_offset.setValue(0.6)

    restored = panel.get_params()

    assert restored.skirt.width == pytest.approx(7.5)
    assert restored.skirt.interval == pytest.approx(18.0)
    assert restored.skirt.speed == pytest.approx(26.0)
    assert restored.skirt.offset == pytest.approx(0.6)


def test_step_speed_roundtrips_through_print_settings(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.step.panel_step_enabled = True
    params.step.print_speed = 34.0

    panel.set_params(params)
    assert panel.step_speed.isEnabled() is True

    panel.step_speed.setValue(41.0)
    restored = panel.get_params()

    assert restored.step.print_speed == pytest.approx(41.0)


def test_step_width_defaults_to_one_point_eight_mm(qapp):
    panel = ParamPanel()

    assert panel.panel_step_width.value() == pytest.approx(1.8)
    assert panel.baseplate_step_width.value() == pytest.approx(1.8)

    restored = panel.get_params()
    assert restored.step.panel_step_width == pytest.approx(1.8)
    assert restored.step.baseplate_step_width == pytest.approx(1.8)


def test_skirt_wall_gap_is_clamped_to_one_mm_in_ui(qapp):
    panel = ParamPanel()

    panel.skirt_enabled.setChecked(True)
    panel.skirt_offset.setValue(2.4)

    assert panel.skirt_offset.value() == pytest.approx(1.0)
    assert panel.get_params().skirt.offset == pytest.approx(1.0)


def test_skirt_wall_gap_defaults_to_point_twelve_mm(qapp):
    panel = ParamPanel()

    assert panel.skirt_offset.value() == pytest.approx(0.12)
    assert panel.get_params().skirt.offset == pytest.approx(0.12)


def test_skirt_sides_are_multi_select_icon_buttons(qapp):
    panel = ParamPanel()

    panel.skirt_enabled.setChecked(True)

    assert isinstance(panel.skirt_outer_enabled, QPushButton)
    assert isinstance(panel.skirt_inner_enabled, QPushButton)
    assert panel.skirt_group.layout().itemAt(1).widget() is panel.skirt_sides_widget
    assert panel.skirt_outer_enabled.isCheckable() is True
    assert panel.skirt_inner_enabled.isCheckable() is True
    assert panel.skirt_outer_enabled.icon().isNull() is False
    assert panel.skirt_inner_enabled.icon().isNull() is False
    assert panel.skirt_outer_enabled.toolTip() == "Outer Brim"
    assert panel.skirt_inner_enabled.toolTip() == "Inner Brim"
    assert panel.skirt_outer_enabled.isEnabled() is True
    assert panel.skirt_inner_enabled.isEnabled() is True
    assert panel.skirt_outer_enabled.isChecked() is True
    assert panel.skirt_inner_enabled.isChecked() is False

    panel.skirt_inner_enabled.click()
    params = panel.get_params()

    assert params.skirt.outer_enabled is True
    assert params.skirt.inner_enabled is True

    panel.skirt_outer_enabled.click()
    params = panel.get_params()

    assert panel.skirt_outer_enabled.isChecked() is False
    assert panel.skirt_inner_enabled.isChecked() is True
    assert params.skirt.outer_enabled is False
    assert params.skirt.inner_enabled is True

    panel.skirt_inner_enabled.click()
    params = panel.get_params()

    assert panel.skirt_outer_enabled.isChecked() is False
    assert panel.skirt_inner_enabled.isChecked() is True
    assert params.skirt.outer_enabled is False
    assert params.skirt.inner_enabled is True


def test_step_speed_stays_enabled_while_any_step_toggle_remains_active(qapp):
    panel = ParamPanel()

    panel.panel_step_enabled.setChecked(True)
    panel.baseplate_step_enabled.setChecked(True)
    assert panel.step_speed.isEnabled() is True

    panel.panel_step_enabled.setChecked(False)
    assert panel.step_speed.isEnabled() is True

    panel.baseplate_step_enabled.setChecked(False)
    assert panel.step_speed.isEnabled() is False


@pytest.mark.parametrize(
    ("configure", "control_names"),
    [
        (
            lambda p: setattr(p.skirt, "enabled", True),
            ("skirt_height", "skirt_speed", "skirt_offset", "skirt_outer_enabled", "skirt_inner_enabled"),
        ),
        (
            lambda p: setattr(p.connected, "enabled", True),
            ("connected_type", "connected_auto_detect", "connected_width", "connected_height", "connected_base_height"),
        ),
        (
            lambda p: setattr(p.step, "panel_step_enabled", True),
            ("panel_step_height", "panel_step_width", "panel_step_v_groove", "step_speed"),
        ),
        (
            lambda p: setattr(p.step, "baseplate_step_enabled", True),
            ("baseplate_step_height", "baseplate_step_width", "baseplate_step_v_groove", "step_speed"),
        ),
        (
            lambda p: setattr(p.bottom_face, "enabled", True),
            ("bottom_face_thickness", "bottom_face_screw_hole_diameter"),
        ),
        (
            lambda p: setattr(p.light_slot, "enabled", True),
            (
                "light_slot_width",
                "light_slot_depth",
                "light_slot_floor_layers",
                "light_slot_outer_enabled",
                "light_slot_hole_enabled",
                "light_slot_auto_skip_small_holes",
            ),
        ),
        (
            lambda p: setattr(p.top_face, "enabled", True),
            ("top_face_thickness",),
        ),
        (
            lambda p: setattr(p.color, "enabled", True),
            ("color_change_table", "add_color_change_btn"),
        ),
    ],
)
def test_set_params_restores_enabled_state_for_other_toggle_groups(qapp, configure, control_names):
    panel = ParamPanel()
    params = SliceParams()
    configure(params)

    panel.set_params(params)

    for control_name in control_names:
        assert getattr(panel, control_name).isEnabled() is True


def test_set_params_restores_color_change_rows_and_summary(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.color.enabled = True
    params.color.change_points = [
        ColorChangePoint(height_mm=10.0, macro_index=3),
        ColorChangePoint(height_mm=20.0, macro_index=1),
    ]

    panel.set_params(params)

    assert panel.color_change_table.rowCount() == 2
    first_height = panel.color_change_table.cellWidget(0, 0)
    first_macro = panel.color_change_table.cellWidget(0, 1)
    second_height = panel.color_change_table.cellWidget(1, 0)
    second_macro = panel.color_change_table.cellWidget(1, 1)

    assert first_height.value() == pytest.approx(10.2)
    assert first_macro.value() == 3
    assert second_height.value() == pytest.approx(20.1)
    assert second_macro.value() == 1
    assert "T3" in panel.color_change_summary.text()
    assert "T1" in panel.color_change_summary.text()


def test_load_project_printer_profile_uses_embedded_snapshot(qapp):
    panel = ParamPanel()
    snapshot = PrinterProfile(
        id="profile-runtime",
        name="Embedded Klipper",
        bed_width=950.0,
        bed_depth=1350.0,
        bed_exclude_area=["0x0,10x0,10x10,0x10"],
        start_gcode="G28\nT0",
        end_gcode="M400",
        color_change_command_template="MACRO_{index}",
    )

    panel.load_project_printer_profile("project-profile", snapshot)

    active_profile = panel.get_active_printer_profile()

    assert panel.get_active_printer_profile_id() == "project-profile"
    assert panel.profile_bed_width.value() == pytest.approx(950.0)
    assert panel.profile_bed_depth.value() == pytest.approx(1350.0)
    assert panel.profile_bed_exclude_area.toPlainText() == format_bed_exclude_area_for_editor(
        snapshot.bed_exclude_area
    )
    assert panel.profile_color_change_template.text() == "MACRO_{index}"
    assert active_profile.name == "Embedded Klipper"
    assert active_profile.bed_exclude_area == snapshot.bed_exclude_area
    assert active_profile.start_gcode == "G28\nT0"
    assert active_profile.end_gcode == "M400"
    assert panel.profile_rename_btn.isEnabled() is False


def test_light_slot_and_baseplate_step_are_mutually_exclusive(qapp):
    panel = ParamPanel()

    panel.light_slot_enabled.setChecked(True)
    assert panel.light_slot_width.isEnabled() is True

    panel.baseplate_step_enabled.setChecked(True)

    assert panel.baseplate_step_enabled.isChecked() is True
    assert panel.light_slot_enabled.isChecked() is False
    assert panel.light_slot_width.isEnabled() is False


def test_light_slot_and_bottom_face_are_mutually_exclusive(qapp):
    panel = ParamPanel()

    panel.bottom_face_enabled.setChecked(True)
    panel.light_slot_enabled.setChecked(True)
    params = panel.get_params()

    assert panel.bottom_face_enabled.isChecked() is False
    assert panel.light_slot_enabled.isChecked() is True
    assert panel.bottom_face_thickness.isEnabled() is False
    assert panel.bottom_face_screw_hole_diameter.isEnabled() is False
    assert panel.light_slot_width.isEnabled() is True
    assert params.bottom_face.enabled is False
    assert params.light_slot.enabled is True


def test_light_slot_outer_and_hole_slots_are_multi_select_icon_buttons(qapp):
    panel = ParamPanel()

    panel.bottom_mode_group.button(panel.BOTTOM_MODE_LIGHT_SLOT).click()

    assert isinstance(panel.light_slot_outer_enabled, QPushButton)
    assert isinstance(panel.light_slot_hole_enabled, QPushButton)
    assert panel.light_slot_group.layout().itemAt(1).widget() is panel.light_slot_scope_widget
    assert panel.light_slot_outer_enabled.isCheckable() is True
    assert panel.light_slot_hole_enabled.isCheckable() is True
    assert panel.light_slot_outer_enabled.icon().isNull() is False
    assert panel.light_slot_hole_enabled.icon().isNull() is False
    assert panel.light_slot_outer_enabled.isEnabled() is True
    assert panel.light_slot_hole_enabled.isEnabled() is True
    assert panel.light_slot_outer_enabled.isChecked() is True
    assert panel.light_slot_hole_enabled.isChecked() is True

    panel.light_slot_outer_enabled.click()
    params = panel.get_params()

    assert panel.light_slot_outer_enabled.isChecked() is False
    assert panel.light_slot_hole_enabled.isChecked() is True
    assert params.light_slot.outer_enabled is False
    assert params.light_slot.hole_enabled is True

    panel.light_slot_outer_enabled.click()
    panel.light_slot_hole_enabled.click()
    params = panel.get_params()

    assert panel.light_slot_outer_enabled.isChecked() is True
    assert panel.light_slot_hole_enabled.isChecked() is False
    assert params.light_slot.outer_enabled is True
    assert params.light_slot.hole_enabled is False

    panel.light_slot_outer_enabled.click()
    params = panel.get_params()

    assert panel.light_slot_outer_enabled.isChecked() is True
    assert panel.light_slot_hole_enabled.isChecked() is False
    assert params.light_slot.outer_enabled is True
    assert params.light_slot.hole_enabled is False


def test_set_params_restores_one_option_for_empty_multi_select_buttons(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.skirt.enabled = True
    params.skirt.outer_enabled = False
    params.skirt.inner_enabled = False
    params.light_slot.enabled = True
    params.light_slot.outer_enabled = False
    params.light_slot.hole_enabled = False

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.skirt_outer_enabled.isChecked() is True
    assert panel.skirt_inner_enabled.isChecked() is False
    assert restored.skirt.outer_enabled is True
    assert restored.skirt.inner_enabled is False
    assert panel.light_slot_outer_enabled.isChecked() is True
    assert panel.light_slot_hole_enabled.isChecked() is False
    assert restored.light_slot.outer_enabled is True
    assert restored.light_slot.hole_enabled is False


def test_bottom_face_screw_hole_diameter_roundtrips_with_bottom_face_params(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.bottom_face.enabled = True
    params.bottom_face.thickness = 1.5
    params.bottom_face.screw_hole_diameter = 6.5

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.bottom_face_screw_hole_diameter.isEnabled() is True
    assert panel.bottom_face_screw_hole_diameter.value() == pytest.approx(6.5)
    assert restored.bottom_face.screw_hole_diameter == pytest.approx(6.5)


def test_set_params_restores_light_slot_floor_thickness_value(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.light_slot.enabled = True
    params.light_slot.floor_layers = 4

    panel.set_params(params)

    assert panel.light_slot_floor_layers.isEnabled() is True
    assert panel.light_slot_floor_layers.value() == pytest.approx(1.2)


def test_set_params_displays_layer_based_heights_as_mm(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.shell.layer_height = 0.5
    params.shell.height = 40.0
    params.shell.baseplate_thickness = 10.0
    params.shell.panel_thickness = 3.0
    params.step.panel_step_enabled = True
    params.step.panel_step_height = 25.0
    params.step.baseplate_step_enabled = True
    params.step.baseplate_step_height = 2.0
    params.bottom_face.enabled = True
    params.bottom_face.thickness = 1.0
    params.light_slot.enabled = True
    params.light_slot.depth = 3.0
    params.top_face.enabled = True
    params.top_face.thickness = 1.5

    panel.set_params(params)

    assert panel.height_spin.value() == pytest.approx(40.0)
    assert panel.baseplate_spin.value() == pytest.approx(10.0)
    assert panel.panel_thickness_spin.value() == pytest.approx(3.0)
    assert panel.panel_step_height.value() == pytest.approx(15.0)
    assert panel.baseplate_step_height.value() == pytest.approx(2.0)
    assert panel.bottom_face_thickness.value() == pytest.approx(1.0)
    assert panel.light_slot_depth.value() == pytest.approx(3.0)
    assert panel.top_face_thickness.value() == pytest.approx(1.5)


def test_set_params_displays_connected_heights_as_mm(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.shell.layer_height = 0.5
    params.connected.enabled = True
    params.connected.height = 3.0
    params.connected.base_height = 2.0

    panel.set_params(params)

    assert panel.connected_height.value() == pytest.approx(3.0)
    assert panel.connected_base_height.value() == pytest.approx(2.0)


def test_get_params_uses_mm_heights_directly(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.height_spin.setValue(30.0)
    panel.baseplate_spin.setValue(20.0)
    panel.panel_thickness_spin.setValue(8.0)
    panel.bottom_face_enabled.setChecked(True)
    panel.bottom_face_thickness.setValue(4.0)
    panel.light_slot_enabled.setChecked(True)
    panel.light_slot_depth.setValue(10.0)
    panel.top_face_enabled.setChecked(True)
    panel.top_face_thickness.setValue(4.0)

    params = panel.get_params()

    assert params.shell.height == pytest.approx(30.0)
    assert params.shell.baseplate_thickness == pytest.approx(20.0)
    assert params.shell.panel_thickness == pytest.approx(8.0)
    assert params.bottom_face.thickness == pytest.approx(4.0)
    assert params.light_slot.depth == pytest.approx(10.0)
    assert params.top_face.thickness == pytest.approx(4.0)


def test_get_params_uses_mm_for_step_heights(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.height_spin.setValue(30.0)
    panel.panel_step_enabled.setChecked(True)
    panel.panel_step_height.setValue(6.0)
    panel.baseplate_step_enabled.setChecked(True)
    panel.baseplate_step_height.setValue(8.0)

    params = panel.get_params()

    assert params.step.panel_step_height == pytest.approx(24.0)
    assert params.step.baseplate_step_height == pytest.approx(8.0)


def test_top_step_distance_is_limited_to_half_shell_height(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.height_spin.setValue(30.0)
    panel.panel_step_height.setValue(16.0)

    assert panel.panel_step_height.maximum() == pytest.approx(15.0)
    assert panel.panel_step_height.value() == pytest.approx(15.0)
    assert panel.get_params().step.panel_step_height == pytest.approx(15.0)


def test_get_params_commits_pending_step_height_text_edits(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.lineEdit().setText("0.25")
    panel.height_spin.lineEdit().setText("40")
    panel.panel_step_enabled.setChecked(True)
    panel.panel_step_height.lineEdit().setText("6")
    panel.baseplate_step_enabled.setChecked(True)
    panel.baseplate_step_height.lineEdit().setText("8")

    params = panel.get_params()

    assert params.shell.layer_height == pytest.approx(0.25)
    assert params.shell.height == pytest.approx(40.0)
    assert params.step.panel_step_height == pytest.approx(34.0)
    assert params.step.baseplate_step_height == pytest.approx(8.0)


def test_get_params_uses_mm_for_connected_heights(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.connected_enabled.setChecked(True)
    panel.connected_height.setValue(12.0)
    panel.connected_base_height.setValue(8.0)

    params = panel.get_params()

    assert params.connected.height == pytest.approx(12.0)
    assert params.connected.base_height == pytest.approx(8.0)
