import pytest

from src.core.types import ColorChangePoint, EdgeDirection, PrinterProfile, SliceParams
from src.ui.param_panel import ParamPanel


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
        "Color Change",
        "Top Face",
        "Bottom Face",
        "Connected Letters",
        "Light Slot",
        "Printer Profile",
        "Klipper Commands",
        "DXF Export",
    ]


def test_primary_sections_separate_vector_machine_and_print_settings(qapp):
    panel = ParamPanel()

    assert [
        (section["key"], section["title"], [group.title() for group in section["groups"]])
        for section in panel._primary_sections
    ] == [
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
            "machine",
            "Machine Settings",
            [
                "Printer Profile",
            ],
        ),
        (
            "print",
            "Print Settings",
            [
                "Speed Settings",
                "Temperature Settings",
                "Color Change",
                "Klipper Commands",
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


def test_width_line_defaults_to_twice_layer_height_and_updates_with_layer_height(qapp):
    panel = ParamPanel()

    assert panel.width_line_spin.value() == pytest.approx(0.6)

    panel.layer_height_spin.setValue(0.4)

    assert panel.width_line_spin.value() == pytest.approx(0.8)


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


@pytest.mark.parametrize(
    ("configure", "control_names"),
    [
        (
            lambda p: setattr(p.skirt, "enabled", True),
            ("skirt_width", "skirt_height", "skirt_interval", "skirt_offset", "skirt_outer_enabled", "skirt_inner_enabled"),
        ),
        (
            lambda p: setattr(p.connected, "enabled", True),
            ("connected_type", "connected_auto_detect", "connected_width", "connected_height", "connected_base_height", "connected_support_offset"),
        ),
        (
            lambda p: setattr(p.step, "panel_step_enabled", True),
            ("panel_step_height", "panel_step_width", "panel_step_v_groove"),
        ),
        (
            lambda p: setattr(p.step, "baseplate_step_enabled", True),
            ("baseplate_step_height", "baseplate_step_width", "baseplate_step_v_groove"),
        ),
        (
            lambda p: setattr(p.bottom_face, "enabled", True),
            ("bottom_face_thickness",),
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
    assert panel.light_slot_width.isEnabled() is True


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
