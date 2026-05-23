import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QHeaderView, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from src.business.printer_profile_manager import DEFAULT_PRINTER_PROFILE_SPECS
from src.core.types import ColorChangePoint, EdgeDirection, EdgeType, PrinterProfile, SliceParams
from src.ui.param_panel import ParamPanel
from src.ui.widgets import GuardedComboBox, GuardedDoubleSpinBox, GuardedSpinBox


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
    assert isinstance(panel.wall_count_spin, GuardedSpinBox)
    assert isinstance(panel.edge_type_combo, GuardedComboBox)
    assert isinstance(panel.printer_profile_combo, GuardedComboBox)


def test_primary_groups_follow_requested_order(qapp):
    panel = ParamPanel()

    assert [group.title() for group in panel._primary_groups] == [
        "Shell Settings",
        "Edge Type",
        "Edge Wrap/Outline",
        "Step/V-Groove",
        "Anti-Warping Skirt",
        "Speed Settings",
        "Temperature Settings",
        "Cooling Settings",
        "Color Change",
        "Prime Tower",
        "Top Face",
        "Bottom Face",
        "Connected Letters",
        "Light Slot",
        "Printer Profile",
        "Machine G-code",
        "DXF Export",
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

    panel.layer_height_spin.setValue(0.2)
    panel.width_line_spin.setValue(0.4)

    target_index = panel.printer_profile_combo.findData(DEFAULT_PRINTER_PROFILE_SPECS[2]["id"])
    assert target_index >= 0

    panel.printer_profile_combo.setCurrentIndex(target_index)

    assert panel.profile_nozzle_diameter.value() == pytest.approx(0.8)
    assert panel.layer_height_spin.value() == pytest.approx(0.4)
    assert panel.width_line_spin.value() == pytest.approx(0.8)
    assert panel.get_params().shell.layer_height == pytest.approx(0.4)
    assert panel.get_params().shell.line_width == pytest.approx(0.8)


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


def test_primary_sections_separate_vector_machine_and_print_settings(qapp):
    panel = ParamPanel()

    assert [
        (section["key"], section["title"], [group.title() for group in section["groups"]])
        for section in panel._primary_sections
    ] == [
        (
            "machine",
            "Machine Settings",
            [
                "Printer Profile",
            ],
        ),
        (
            "vector",
            "2D Vector Settings",
            [
                "Shell Settings",
                "Edge Type",
                "Edge Wrap/Outline",
                "Step/V-Groove",
                "Anti-Warping Skirt",
                "Top Face",
                "Bottom Face",
                "Connected Letters",
                "Light Slot",
                "DXF Export",
            ],
        ),
        (
            "print",
            "Print Settings",
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


def test_primary_sections_can_be_collapsed_and_expanded(qapp):
    panel = ParamPanel()
    vector_section = panel._section_widgets_by_key["vector"]
    toggle_button = vector_section._toggle_button
    body = vector_section._body

    assert toggle_button.text() == "- 2D Vector Settings"
    assert body.isHidden() is False

    toggle_button.click()

    assert toggle_button.text() == "+ 2D Vector Settings"
    assert body.isHidden() is True

    toggle_button.click()

    assert toggle_button.text() == "- 2D Vector Settings"
    assert body.isHidden() is False


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


def test_step_controls_share_single_primary_group(qapp):
    panel = ParamPanel()

    assert panel.step_group.title() == "Step/V-Groove"
    assert _owning_group(panel.panel_step_enabled) is panel.step_group
    assert _owning_group(panel.baseplate_step_enabled) is panel.step_group


def test_set_params_restores_wrap_controls_enabled_state(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.edge_wrap.wrap_enabled = True
    params.edge_wrap.wrap_direction = EdgeDirection.OUTER

    panel.set_params(params)

    assert panel.wrap_enabled.isChecked() is True
    assert panel.wrap_width.isEnabled() is True
    assert panel.wrap_height.isEnabled() is True
    assert panel.wrap_dir_inner.isEnabled() is True
    assert panel.wrap_dir_outer.isEnabled() is True


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

    assert panel.height_spin.value() == pytest.approx(50.0)
    assert panel.layer_height_spin.value() == pytest.approx(0.3)
    assert panel.width_line_spin.value() == pytest.approx(0.6)
    assert panel.wall_count_spin.value() == 2
    assert panel.edge_type_combo.currentData() == EdgeType.STRAIGHT
    assert panel.bevel_params_widget.isHidden() is True
    assert panel.panel_step_enabled.isChecked() is False
    assert panel.baseplate_step_enabled.isChecked() is False
    assert panel.skirt_enabled.isChecked() is False
    assert panel.connected_enabled.isChecked() is False
    assert panel.bevel_width_spin.value() == pytest.approx(5.0)
    assert panel.baseplate_spin.value() == 30
    assert panel.panel_thickness_spin.value() == 30
    assert panel.wrap_width.value() == pytest.approx(3.0)
    assert panel.wrap_height.value() == pytest.approx(3.0)
    assert panel.outline_width.value() == pytest.approx(3.0)
    assert panel.outline_height.value() == pytest.approx(3.0)
    assert panel.outline_offset.value() == pytest.approx(0.0)
    assert panel.panel_step_height.value() == pytest.approx(47.0)
    assert panel.baseplate_step_height.value() == 10
    assert panel.skirt_height.value() == pytest.approx(0.3)
    assert panel.skirt_offset.value() == pytest.approx(0.12)
    assert panel.top_face_thickness.value() == 8
    assert panel.u_arc_height_spin.value() == 20
    assert panel.u_bottom_layers_spin.value() == 3
    assert panel.bottom_face_thickness.value() == 3
    assert panel.bottom_face_screw_hole_diameter.value() == pytest.approx(5.0)
    assert panel.connected_type.currentData() == "triangle"
    assert panel.connected_width.value() == pytest.approx(5.0)
    assert panel.connected_height.value() == 15
    assert panel.connected_base_height.value() == 15
    assert panel.connected_support_offset.value() == pytest.approx(2.5)
    assert panel.light_slot_width.value() == pytest.approx(7.8)
    assert panel.light_slot_depth.value() == 20
    assert panel.light_slot_floor_layers.value() == 5
    assert panel.light_slot_wall_gap.value() == pytest.approx(0.0)

    assert params.shell.height == pytest.approx(50.0)
    assert params.shell.wall_count == 2
    assert params.shell.wall_thickness == pytest.approx(1.2)
    assert params.shell.edge_type == EdgeType.STRAIGHT
    assert params.step.panel_step_enabled is False
    assert params.step.baseplate_step_enabled is False
    assert params.skirt.enabled is False
    assert params.connected.enabled is False
    assert params.shell.baseplate_thickness == pytest.approx(9.0)
    assert params.shell.panel_thickness == pytest.approx(9.0)
    assert params.shell.u_arc_height == pytest.approx(6.0)
    assert params.shell.u_bottom_layers == 3
    assert params.step.panel_step_height == pytest.approx(47.0)
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

    panel.width_line_spin.setValue(1.1)
    assert panel.get_params().shell.line_width == pytest.approx(1.1)

    panel.layer_height_spin.setValue(0.25)

    assert panel.width_line_spin.value() == pytest.approx(0.5)


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
    params.shell.line_width = 1.3

    panel.set_params(params)

    assert panel.width_line_spin.value() == pytest.approx(1.3)


def test_wall_thickness_is_derived_from_width_line_and_wall_count(qapp):
    panel = ParamPanel()

    panel.width_line_spin.setValue(0.8)
    panel.wall_count_spin.setValue(3)

    params = panel.get_params()

    assert not hasattr(panel, "wall_thickness_spin")
    assert params.shell.wall_thickness == pytest.approx(2.4)


def test_u_shape_edge_roundtrips_arc_height_as_layer_count(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.shell.layer_height = 0.5
    params.shell.edge_type = EdgeType.U_SHAPED
    params.shell.u_arc_height = 2.5
    params.shell.u_bottom_layers = 4
    params.bottom_face.enabled = False
    params.bottom_face.thickness = 1.5

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.u_shape_params_widget.isHidden() is False
    assert panel.u_arc_height_spin.value() == 5
    assert panel.u_bottom_layers_spin.value() == 4
    assert panel.bottom_face_thickness.value() == 3
    assert panel.bottom_face_thickness.isEnabled() is False
    assert panel.bottom_face_screw_hole_diameter.isEnabled() is False
    assert restored.shell.edge_type == EdgeType.U_SHAPED
    assert restored.shell.u_arc_height == pytest.approx(2.5)
    assert restored.shell.u_bottom_layers == 4
    assert restored.bottom_face.enabled is False
    assert restored.bottom_face.thickness == pytest.approx(1.5)


def test_set_params_recomputes_wall_thickness_from_line_width_and_wall_count(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.shell.layer_height = 0.5
    params.shell.line_width = 1.1
    params.shell.wall_count = 2
    params.shell.wall_thickness = 9.9

    panel.set_params(params)
    restored = panel.get_params()

    assert panel.width_line_spin.value() == pytest.approx(1.1)
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
    assert panel.outline_offset.isEnabled() is True
    assert panel.outline_dir_inner.isEnabled() is True
    assert panel.outline_dir_outer.isEnabled() is True


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
    skirt_group = next(group for group in panel._primary_groups if group.title() == "Anti-Warping Skirt")
    speed_group = next(group for group in panel._primary_groups if group.title() == "Speed Settings")

    skirt_labels = {label.text() for label in skirt_group.findChildren(QLabel)}
    speed_labels = {label.text() for label in speed_group.findChildren(QLabel)}

    assert "Skirt Height:" in skirt_labels
    assert "Wall Gap:" in skirt_labels
    assert "Skirt Speed:" not in skirt_labels
    assert "Skirt Width:" not in skirt_labels
    assert "Trapezoid Interval:" not in skirt_labels
    assert "Skirt Speed:" in speed_labels
    assert _owning_group(panel.skirt_speed) is panel.speed_group


def test_step_group_keeps_geometry_fields_and_moves_speed_to_print_settings(qapp):
    panel = ParamPanel()
    step_group = next(group for group in panel._primary_groups if group.title() == "Step/V-Groove")
    speed_group = next(group for group in panel._primary_groups if group.title() == "Speed Settings")

    step_labels = {label.text() for label in step_group.findChildren(QLabel)}
    speed_labels = {label.text() for label in speed_group.findChildren(QLabel)}

    assert "Step Height:" in step_labels
    assert "Step Width:" in step_labels
    assert "Step Speed:" not in step_labels
    assert "Step Speed:" in speed_labels
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
            ("connected_type", "connected_auto_detect", "connected_width", "connected_height", "connected_base_height", "connected_support_offset"),
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
                "light_slot_wall_gap",
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

    assert first_height.value() == pytest.approx(10.0)
    assert first_macro.value() == 3
    assert second_height.value() == pytest.approx(20.0)
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
        start_gcode="G28\nT0",
        end_gcode="M400",
        color_change_command_template="MACRO_{index}",
    )

    panel.load_project_printer_profile("project-profile", snapshot)

    active_profile = panel.get_active_printer_profile()

    assert panel.get_active_printer_profile_id() == "project-profile"
    assert panel.profile_bed_width.value() == pytest.approx(950.0)
    assert panel.profile_bed_depth.value() == pytest.approx(1350.0)
    assert panel.profile_color_change_template.text() == "MACRO_{index}"
    assert active_profile.name == "Embedded Klipper"
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


def test_light_slot_and_bottom_face_can_coexist(qapp):
    panel = ParamPanel()

    panel.bottom_face_enabled.setChecked(True)
    panel.light_slot_enabled.setChecked(True)

    assert panel.bottom_face_enabled.isChecked() is True
    assert panel.light_slot_enabled.isChecked() is True
    assert panel.bottom_face_thickness.isEnabled() is True
    assert panel.bottom_face_screw_hole_diameter.isEnabled() is True
    assert panel.light_slot_width.isEnabled() is True


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


def test_set_params_restores_light_slot_floor_layers_value(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.light_slot.enabled = True
    params.light_slot.floor_layers = 4

    panel.set_params(params)

    assert panel.light_slot_floor_layers.isEnabled() is True
    assert panel.light_slot_floor_layers.value() == 4


def test_set_params_converts_layer_based_heights_to_layer_counts(qapp):
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
    assert panel.baseplate_spin.value() == 20
    assert panel.panel_thickness_spin.value() == 6
    assert panel.panel_step_height.value() == pytest.approx(25.0)
    assert panel.baseplate_step_height.value() == 4
    assert panel.bottom_face_thickness.value() == 2
    assert panel.light_slot_depth.value() == 6
    assert panel.top_face_thickness.value() == 3


def test_set_params_converts_connected_heights_to_layer_counts(qapp):
    panel = ParamPanel()
    params = SliceParams()
    params.shell.layer_height = 0.5
    params.connected.enabled = True
    params.connected.height = 3.0
    params.connected.base_height = 2.0

    panel.set_params(params)

    assert panel.connected_height.value() == 6
    assert panel.connected_base_height.value() == 4


def test_get_params_uses_layer_counts_to_derive_mm_heights(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.height_spin.setValue(30.0)
    panel.baseplate_spin.setValue(20)
    panel.panel_thickness_spin.setValue(8)
    panel.bottom_face_enabled.setChecked(True)
    panel.bottom_face_thickness.setValue(4)
    panel.light_slot_enabled.setChecked(True)
    panel.light_slot_depth.setValue(10)
    panel.top_face_enabled.setChecked(True)
    panel.top_face_thickness.setValue(4)

    params = panel.get_params()

    assert params.shell.height == pytest.approx(30.0)
    assert params.shell.baseplate_thickness == pytest.approx(5.0)
    assert params.shell.panel_thickness == pytest.approx(2.0)
    assert params.bottom_face.thickness == pytest.approx(1.0)
    assert params.light_slot.depth == pytest.approx(2.5)
    assert params.top_face.thickness == pytest.approx(1.0)


def test_get_params_uses_layer_counts_for_step_heights(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.height_spin.setValue(30.0)
    panel.panel_step_enabled.setChecked(True)
    panel.panel_step_height.setValue(16.0)
    panel.baseplate_step_enabled.setChecked(True)
    panel.baseplate_step_height.setValue(8)

    params = panel.get_params()

    assert params.step.panel_step_height == pytest.approx(16.0)
    assert params.step.baseplate_step_height == pytest.approx(2.0)


def test_get_params_commits_pending_step_height_text_edits(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.lineEdit().setText("0.25")
    panel.height_spin.lineEdit().setText("40")
    panel.panel_step_enabled.setChecked(True)
    panel.panel_step_height.lineEdit().setText("24")
    panel.baseplate_step_enabled.setChecked(True)
    panel.baseplate_step_height.lineEdit().setText("8")

    params = panel.get_params()

    assert params.shell.layer_height == pytest.approx(0.25)
    assert params.shell.height == pytest.approx(40.0)
    assert params.step.panel_step_height == pytest.approx(24.0)
    assert params.step.baseplate_step_height == pytest.approx(2.0)


def test_get_params_uses_layer_counts_for_connected_heights(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.connected_enabled.setChecked(True)
    panel.connected_height.setValue(12)
    panel.connected_base_height.setValue(8)

    params = panel.get_params()

    assert params.connected.height == pytest.approx(3.0)
    assert params.connected.base_height == pytest.approx(2.0)
