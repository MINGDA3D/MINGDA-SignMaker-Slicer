import pytest

from src.core.types import EdgeDirection, SliceParams
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
        "Top Face",
        "Bottom Face",
        "Connected Letters",
        "Light Slot",
        "DXF Export",
    ]


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
            ("color1_height", "color2_height"),
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

    assert panel.height_spin.value() == 80
    assert panel.panel_step_height.value() == 50
    assert panel.baseplate_step_height.value() == 4
    assert panel.bottom_face_thickness.value() == 2
    assert panel.light_slot_depth.value() == 6
    assert panel.top_face_thickness.value() == 3
    assert panel.height_value_label.text() == "40.00 mm"
    assert panel.light_slot_depth_value_label.text() == "3.00 mm"


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
    assert panel.connected_height_value_label.text() == "3.00 mm"
    assert panel.connected_base_height_value_label.text() == "2.00 mm"


def test_get_params_uses_layer_counts_to_derive_mm_heights(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.height_spin.setValue(120)
    panel.bottom_face_enabled.setChecked(True)
    panel.bottom_face_thickness.setValue(4)
    panel.light_slot_enabled.setChecked(True)
    panel.light_slot_depth.setValue(10)
    panel.top_face_enabled.setChecked(True)
    panel.top_face_thickness.setValue(6)

    params = panel.get_params()

    assert params.shell.height == pytest.approx(30.0)
    assert params.bottom_face.thickness == pytest.approx(1.0)
    assert params.light_slot.depth == pytest.approx(2.5)
    assert params.top_face.thickness == pytest.approx(1.5)


def test_get_params_uses_layer_counts_for_step_heights(qapp):
    panel = ParamPanel()

    panel.layer_height_spin.setValue(0.25)
    panel.height_spin.setValue(120)
    panel.panel_step_enabled.setChecked(True)
    panel.panel_step_height.setValue(64)
    panel.baseplate_step_enabled.setChecked(True)
    panel.baseplate_step_height.setValue(8)

    params = panel.get_params()

    assert params.step.panel_step_height == pytest.approx(16.0)
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
