"""
MINGDA SignMaker - 设置管理器单元测试
"""

import json
import os
import shutil
import builtins
import uuid
import pytest
from pathlib import Path

from src.core.types import (
    ColorChangePoint, SliceParams, EdgeType, BevelDirection,
    serialize_params, deserialize_params
)
from src.business.preset_manager import PresetManager


class TestSerializeParams:
    """参数序列化测试"""

    def test_serialize_default_params(self):
        """测试序列化默认参数"""
        params = SliceParams()
        data = serialize_params(params)

        assert "shell" in data
        assert "speed" in data
        assert "gcode" in data
        assert "machine" in data
        assert data["shell"]["height_layers"] == 100
        assert data["shell"]["line_width"] == pytest.approx(0.6)
        assert "wall_thickness" not in data["shell"]
        assert "height" not in data["shell"]
        assert data["shell"]["edge_type"] == "STRAIGHT"

    def test_serialize_custom_params(self):
        """测试序列化自定义参数"""
        params = SliceParams()
        params.shell.layer_height = 0.5
        params.shell.line_width = 0.9
        params.shell.height = 50.0
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_direction = BevelDirection.TOP_LARGE
        params.skirt.enabled = True
        params.skirt.width = 10.0
        params.skirt.speed = 27.0
        params.step.print_speed = 36.0

        data = serialize_params(params)

        assert data["shell"]["height_layers"] == 100
        assert data["shell"]["line_width"] == pytest.approx(0.9)
        assert "wall_thickness" not in data["shell"]
        assert "height" not in data["shell"]
        assert data["shell"]["edge_type"] == "BEVELED"
        assert data["shell"]["bevel_direction"] == "TOP_LARGE"
        assert data["skirt"]["enabled"] is True
        assert data["skirt"]["width"] == 10.0
        assert data["skirt"]["speed"] == pytest.approx(27.0)
        assert data["step"]["print_speed"] == pytest.approx(36.0)

    def test_deserialize_default_params(self):
        """测试反序列化默认参数"""
        params = SliceParams()
        data = serialize_params(params)
        restored = deserialize_params(data)

        assert restored.shell.height == 30.0
        assert restored.shell.line_width == pytest.approx(0.6)
        assert restored.shell.wall_thickness == pytest.approx(0.6)
        assert restored.shell.edge_type == EdgeType.STRAIGHT
        assert restored.skirt.enabled is False
        assert restored.skirt.speed == pytest.approx(20.0)
        assert restored.skirt.offset == pytest.approx(0.12)
        assert restored.step.panel_step_width == pytest.approx(1.8)
        assert restored.step.baseplate_step_width == pytest.approx(1.8)
        assert restored.step.print_speed == pytest.approx(30.0)

    def test_deserialize_custom_params(self):
        """测试反序列化自定义参数"""
        params = SliceParams()
        params.shell.height = 42.0
        params.shell.line_width = 1.1
        params.shell.edge_type = EdgeType.BEVELED
        params.bottom_face.screw_hole_diameter = 5.5
        params.step.enabled = True
        params.step.panel_step_enabled = True
        params.step.print_speed = 36.0
        params.speed.print_speed = 80.0
        params.skirt.enabled = True
        params.skirt.speed = 27.0

        data = serialize_params(params)
        restored = deserialize_params(data)

        assert restored.shell.height == 42.0
        assert restored.shell.line_width == pytest.approx(1.1)
        assert restored.shell.edge_type == EdgeType.BEVELED
        assert restored.bottom_face.screw_hole_diameter == pytest.approx(5.5)
        assert restored.step.enabled is True
        assert restored.step.panel_step_enabled is True
        assert restored.step.print_speed == pytest.approx(36.0)
        assert restored.speed.print_speed == 80.0
        assert restored.skirt.speed == pytest.approx(27.0)

    def test_deserialize_shell_line_width_defaults_to_layer_height_double_when_missing(self):
        """测试旧 shell 数据缺少 line_width 时自动按层高两倍补齐"""
        restored = deserialize_params({
            "shell": {
                "layer_height": 0.45,
                "height_layers": 100,
            }
        })

        assert restored.shell.height == pytest.approx(45.0)
        assert restored.shell.line_width == pytest.approx(0.9)
        assert restored.shell.wall_thickness == pytest.approx(0.9)

    def test_deserialize_legacy_wall_thickness_migrates_to_line_width(self):
        """测试旧 shell 数据仅保存 wall_thickness 时会迁移为 line_width * wall_count。"""
        restored = deserialize_params({
            "shell": {
                "layer_height": 0.4,
                "height_layers": 100,
                "wall_count": 3,
                "wall_thickness": 2.4,
            }
        })

        assert restored.shell.line_width == pytest.approx(0.8)
        assert restored.shell.wall_thickness == pytest.approx(2.4)

    def test_deserialize_legacy_skirt_side_flag(self):
        """测试旧版 skirt is_outer 参数兼容"""
        restored = deserialize_params({
            "skirt": {
                "enabled": True,
                "is_outer": False
            }
        })

        assert restored.skirt.enabled is True
        assert restored.skirt.outer_enabled is False
        assert restored.skirt.inner_enabled is True

    def test_serialize_and_deserialize_light_slot_params(self):
        """测试灯槽参数可完整往返序列化"""
        params = SliceParams()
        params.light_slot.enabled = True
        params.light_slot.width = 9.5
        params.light_slot.depth = 4.2
        params.light_slot.floor_layers = 3
        params.light_slot.wall_gap = 0.8
        params.light_slot.outer_enabled = True
        params.light_slot.hole_enabled = False
        params.light_slot.auto_skip_small_holes = False
        params.light_slot.min_hole_span = 16.0

        data = serialize_params(params)
        restored = deserialize_params(data)

        assert data["light_slot"]["depth_layers"] == 14
        assert "depth" not in data["light_slot"]
        assert restored.light_slot.enabled is True
        assert restored.light_slot.width == 9.5
        assert restored.light_slot.depth == 4.2
        assert restored.light_slot.floor_layers == 3
        assert restored.light_slot.wall_gap == 0.8
        assert restored.light_slot.outer_enabled is True
        assert restored.light_slot.hole_enabled is False
        assert restored.light_slot.auto_skip_small_holes is False
        assert restored.light_slot.min_hole_span == 16.0

    def test_serialize_and_deserialize_connected_params(self):
        """测试连接字高度参数以层数字段往返序列化"""
        params = SliceParams()
        params.shell.layer_height = 0.5
        params.connected.enabled = True
        params.connected.width = 12.0
        params.connected.height = 3.0
        params.connected.base_height = 2.0
        params.connected.support_offset = 1.5

        data = serialize_params(params)
        restored = deserialize_params(data)

        assert data["connected"]["height_layers"] == 6
        assert data["connected"]["base_height_layers"] == 4
        assert "height" not in data["connected"]
        assert "base_height" not in data["connected"]
        assert "bridge_width" not in data["connected"]
        assert "bridge_height" not in data["connected"]
        assert restored.connected.enabled is True
        assert restored.connected.width == 12.0
        assert restored.connected.height == 3.0
        assert restored.connected.base_height == 2.0
        assert restored.connected.support_offset == 1.5

    def test_serialize_and_deserialize_prime_tower_params(self):
        """æµ‹è¯• Prime tower å‚æ•°å¯å®Œæ•´å¾€è¿”åºåˆ—åŒ–"""
        params = SliceParams()
        params.prime_tower.enabled = True
        params.prime_tower.center_x = 512.5
        params.prime_tower.center_y = 860.0
        params.prime_tower.width = 48.0
        params.prime_tower.depth = 36.0
        params.prime_tower.infill_density_percent = 35

        data = serialize_params(params)
        restored = deserialize_params(data)

        assert data["prime_tower"]["enabled"] is True
        assert data["prime_tower"]["center_x"] == pytest.approx(512.5)
        assert data["prime_tower"]["center_y"] == pytest.approx(860.0)
        assert data["prime_tower"]["width"] == pytest.approx(48.0)
        assert data["prime_tower"]["depth"] == pytest.approx(36.0)
        assert data["prime_tower"]["infill_density_percent"] == 35
        assert restored.prime_tower.enabled is True
        assert restored.prime_tower.center_x == pytest.approx(512.5)
        assert restored.prime_tower.center_y == pytest.approx(860.0)
        assert restored.prime_tower.width == pytest.approx(48.0)
        assert restored.prime_tower.depth == pytest.approx(36.0)
        assert restored.prime_tower.infill_density_percent == 35

    def test_roundtrip_all_params(self):
        """测试完整参数的往返序列化"""
        params = SliceParams()

        # 修改各种参数
        params.shell.layer_height = 0.5
        params.shell.line_width = 1.1
        params.shell.height = 35.0
        params.shell.wall_count = 2
        params.shell.wall_thickness = 9.9
        params.color.enabled = True
        params.step.panel_step_enabled = True
        params.skirt.enabled = True
        params.connected.enabled = True
        params.edge_wrap.wrap_enabled = True
        params.bottom_face.enabled = True
        params.light_slot.enabled = True
        params.top_face.enabled = True
        params.gcode.first_layer_nozzle_temp = 235
        params.gcode.other_layer_nozzle_temp = 225
        params.gcode.first_layer_bed_temp = 65
        params.gcode.other_layer_bed_temp = 55
        params.gcode.first_layer_fan_percent = 30
        params.gcode.other_layer_fan_percent = 80
        params.machine.bed_width = 500.0

        data = serialize_params(params)
        restored = deserialize_params(data)

        assert restored.shell.height == 35.0
        assert restored.shell.line_width == pytest.approx(1.1)
        assert "wall_thickness" not in data["shell"]
        assert restored.shell.wall_thickness == pytest.approx(2.2)
        assert restored.color.enabled is True
        assert restored.step.panel_step_enabled is True
        assert restored.skirt.enabled is True
        assert restored.connected.enabled is True
        assert restored.edge_wrap.wrap_enabled is True
        assert restored.bottom_face.enabled is True
        assert restored.light_slot.enabled is True
        assert restored.top_face.enabled is True
        assert restored.gcode.first_layer_nozzle_temp == 235
        assert restored.gcode.other_layer_nozzle_temp == 225
        assert restored.gcode.first_layer_bed_temp == 65
        assert restored.gcode.other_layer_bed_temp == 55
        assert restored.gcode.first_layer_fan_percent == 30
        assert restored.gcode.other_layer_fan_percent == 80
        assert restored.machine.bed_width == 500.0

    def test_deserialize_empty_dict(self):
        """测试反序列化空字典"""
        restored = deserialize_params({})
        assert restored.shell.height == 30.0  # 默认值
        assert restored.shell.line_width == pytest.approx(0.6)
        assert restored.shell.wall_thickness == pytest.approx(0.6)

    def test_deserialize_partial_data(self):
        """测试反序列化部分数据"""
        data = {
            "shell": {"height_layers": 150},
            "speed": {"print_speed": 70.0}
        }
        restored = deserialize_params(data)

        assert restored.shell.height == 45.0
        assert restored.speed.print_speed == 70.0
        # 其他参数应使用默认值
        assert restored.skirt.enabled is False

    def test_deserialize_rejects_legacy_layer_height_fields(self):
        """测试旧的高度字段不再兼容"""
        with pytest.raises(ValueError, match="shell.height"):
            deserialize_params({
                "shell": {
                    "height": 30.0,
                    "layer_height": 0.3,
                }
            })

    def test_deserialize_rejects_legacy_connected_height_fields(self):
        """测试连接字旧高度字段不再兼容"""
        with pytest.raises(ValueError, match="connected.height"):
            deserialize_params({
                "shell": {
                    "layer_height": 0.5,
                },
                "connected": {
                    "height": 3.0,
                },
            })

    def test_deserialize_rejects_legacy_connected_bridge_fields(self):
        """测试连接字旧桥接字段不再兼容"""
        with pytest.raises(ValueError, match="connected.bridge_width"):
            deserialize_params({
                "shell": {
                    "layer_height": 0.5,
                },
                "connected": {
                    "bridge_width": 12.0,
                },
            })

        with pytest.raises(ValueError, match="connected.bridge_height"):
            deserialize_params({
                "shell": {
                    "layer_height": 0.5,
                },
                "connected": {
                    "bridge_height": 3.0,
                },
            })


    def test_serialize_and_deserialize_klipper_color_change_fields(self):
        """æµ‹è¯• Klipper æ¢è‰²ç‚¹å’Œ G-code è„šæœ¬å­—æ®µå¾€è¿”åºåˆ—åŒ–"""
        params = SliceParams()
        params.color.enabled = True
        params.color.change_points = [
            ColorChangePoint(height_mm=10.0, macro_index=3),
            ColorChangePoint(height_mm=20.0, macro_index=1),
        ]
        params.gcode.start_gcode = "G28\nT0"
        params.gcode.end_gcode = "M400"
        params.gcode.color_change_command_template = "MACRO_{index}"

        data = serialize_params(params)
        restored = deserialize_params(data)

        assert data["color"]["change_points"] == [
            {"height_mm": 10.0, "macro_index": 3},
            {"height_mm": 20.0, "macro_index": 1},
        ]
        assert restored.color.enabled is True
        assert [point.height_mm for point in restored.color.change_points] == [10.0, 20.0]
        assert [point.macro_index for point in restored.color.change_points] == [3, 1]
        assert restored.gcode.start_gcode == "G28\nT0"
        assert restored.gcode.end_gcode == "M400"
        assert restored.gcode.color_change_command_template == "MACRO_{index}"

    def test_deserialize_legacy_color_layers_migrates_to_manual_change_points(self):
        """æµ‹è¯•æ—§ç‰ˆ color.layers è¿ç§»ä¸ºæ‰‹åŠ¨æ¢è‰²ç‚¹"""
        restored = deserialize_params({
            "shell": {
                "layer_height": 0.5,
                "height_layers": 100,
            },
            "color": {
                "enabled": True,
                "layers": [
                    {"height": 10.0, "extruder": "EXTRUDER_2"},
                    {"height": 5.0, "extruder": "EXTRUDER_1"},
                ],
            },
        })

        assert restored.color.enabled is True
        assert [point.height_mm for point in restored.color.change_points] == [10.0, 15.0]
        assert [point.macro_index for point in restored.color.change_points] == [1, 0]

    def test_deserialize_legacy_gcode_temperature_fields_migrates_to_first_and_other_layer_settings(self):
        restored = deserialize_params({
            "gcode": {
                "extruder1_temp": 228,
                "bed_temp": 62,
            }
        })

        assert restored.gcode.first_layer_nozzle_temp == 228
        assert restored.gcode.other_layer_nozzle_temp == 228
        assert restored.gcode.first_layer_bed_temp == 62
        assert restored.gcode.other_layer_bed_temp == 62

    def test_deserialize_legacy_default_gcode_scripts_upgrades_to_start_and_end_print(self):
        restored = deserialize_params(
            {
                "gcode": {
                    "start_gcode": "G28",
                    "end_gcode": "",
                }
            }
        )

        assert (
            restored.gcode.start_gcode
            == "START_PRINT EXTRUDER={nozzle_temperature_initial_layer[0]} "
            "BED=[first_layer_bed_temperature] TOOL=[initial_tool]"
        )
        assert restored.gcode.end_gcode == "END_PRINT"


class TestSettingsManagerWithQt:
    """设置管理器测试（需要 QApplication）"""

    @pytest.fixture
    def qapp(self):
        """创建 QApplication（如果需要）"""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        base_dir = Path.cwd() / ".tmp_pytest_settings"
        base_dir.mkdir(parents=True, exist_ok=True)
        tmpdir = base_dir / f"case_{uuid.uuid4().hex}"
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            yield str(tmpdir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_init_settings_manager(self, qapp, temp_config_dir):
        """测试初始化设置管理器"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)

        # 默认没有保存的参数
        assert sm.get_last_params() is None

    def test_set_and_get_params(self, qapp, temp_config_dir):
        """测试设置和获取参数"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)

        params = SliceParams()
        params.shell.layer_height = 0.5
        params.shell.height = 55.0
        params.skirt.enabled = True

        sm.set_last_params(params)
        restored = sm.get_last_params()

        assert restored.shell.height == 55.0
        assert restored.skirt.enabled is True

    def test_params_persistence(self, qapp, temp_config_dir):
        """测试参数持久化"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)

        params = SliceParams()
        params.shell.height = 60.0
        sm.set_last_params(params)

        # 创建新实例验证持久化
        sm2 = SettingsManager(temp_config_dir)
        restored = sm2.get_last_params()

        assert restored.shell.height == 60.0

    def test_params_saved_to_json_file(self, qapp, temp_config_dir):
        """测试参数保存到 JSON 文件"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)

        params = SliceParams()
        params.shell.height = 45.0
        sm.set_last_params(params)

        # 验证文件存在
        params_file = Path(temp_config_dir) / "slice_params.json"
        assert params_file.exists()

        # 验证文件内容
        with open(params_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data["version"] == SettingsManager.CONFIG_VERSION
        assert data["params"]["shell"]["height_layers"] == 150
        assert "height" not in data["params"]["shell"]

    def test_set_last_params_returns_false_on_write_error(self, qapp, temp_config_dir, monkeypatch):
        """测试保存参数失败时返回 False，而不是抛异常"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)
        params = SliceParams()

        real_open = builtins.open

        def failing_open(path, *args, **kwargs):
            if Path(path) == Path(temp_config_dir) / "slice_params.json":
                raise PermissionError("denied")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", failing_open)

        assert sm.set_last_params(params) is False

    def test_get_last_params_returns_none_on_read_error(self, qapp, temp_config_dir, monkeypatch):
        """测试读取损坏或无权限的参数文件时返回 None"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)
        params_file = Path(temp_config_dir) / "slice_params.json"
        params_file.write_text("{}", encoding="utf-8")

        real_open = builtins.open

        def failing_open(path, *args, **kwargs):
            if Path(path) == params_file:
                raise PermissionError("denied")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", failing_open)

        assert sm.get_last_params() is None

    def test_default_config_dir_uses_platform_app_config_location(self, qapp, temp_config_dir, monkeypatch):
        """测试未显式传入目录时使用平台用户配置目录"""
        from src.business.settings_manager import SettingsManager

        expected_root = Path(temp_config_dir) / "app_config_root"
        monkeypatch.setattr(
            "src.business.settings_manager.QStandardPaths.writableLocation",
            lambda *_: str(expected_root)
        )

        sm = SettingsManager()

        expected_dir = expected_root / SettingsManager.ORGANIZATION / SettingsManager.APPLICATION
        assert sm._config_dir == expected_dir
        assert sm._params_file == expected_dir / "slice_params.json"

    def test_get_config_dir_returns_resolved_config_path(self, qapp, temp_config_dir):
        from src.business.settings_manager import SettingsManager

        sm = SettingsManager(temp_config_dir)

        assert sm.get_config_dir() == Path(temp_config_dir).resolve()

    def test_get_last_params_migrates_legacy_file(self, qapp, temp_config_dir):
        """测试会从旧的应用目录配置文件迁移到新目录"""
        from src.business.settings_manager import SettingsManager

        base_dir = Path(temp_config_dir)
        target_dir = base_dir / "new_config"
        legacy_dir = base_dir / "legacy_config"
        legacy_dir.mkdir(parents=True, exist_ok=True)

        legacy_file = legacy_dir / "slice_params.json"
        params = SliceParams()
        params.shell.height = 66.0
        legacy_file.write_text(
            json.dumps({
                "version": SettingsManager.CONFIG_VERSION,
                "last_modified": "2026-03-22T00:00:00",
                "params": serialize_params(params),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        sm = SettingsManager(str(target_dir))
        sm._legacy_params_files = [legacy_file]

        restored = sm.get_last_params()

        assert restored is not None
        assert restored.shell.height == 66.0
        assert (target_dir / "slice_params.json").exists()

    def test_language_uses_qsettings(self, qapp, temp_config_dir):
        """测试语言设置使用 QSettings"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)

        sm.set_language("en_US")
        assert sm.get_language() == "en_US"

        sm.set_language("zh_CN")
        assert sm.get_language() == "zh_CN"

    def test_recent_files(self, qapp, temp_config_dir):
        """测试最近文件列表"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)

        sm.add_recent_file("C:/test/file1.dxf")
        sm.add_recent_file("C:/test/file2.dxf")

        recent = sm.get_recent_files()
        assert len(recent) == 2
        assert "file2.dxf" in recent[0]  # 最新的在前面

    def test_recent_files_deduplication(self, qapp, temp_config_dir):
        """测试最近文件去重"""
        from src.business.settings_manager import SettingsManager
        sm = SettingsManager(temp_config_dir)

        sm.add_recent_file("C:/test/file1.dxf")
        sm.add_recent_file("C:/test/file2.dxf")
        sm.add_recent_file("C:/test/file1.dxf")  # 重复添加

        recent = sm.get_recent_files()
        assert len(recent) == 2
        assert "file1.dxf" in recent[0]  # 重复的应该移到最前面


    def test_set_and_get_active_printer_profile_id(self, qapp, temp_config_dir):
        """æµ‹è¯•å½“å‰æ‰“å°æœºæ¡£æ¡ˆ ID æŒä¹…åŒ–"""
        from src.business.settings_manager import SettingsManager

        sm = SettingsManager(temp_config_dir)
        sm.set_active_printer_profile_id("klipper-profile-1")

        sm2 = SettingsManager(temp_config_dir)

        assert sm.get_active_printer_profile_id() == "klipper-profile-1"
        assert sm2.get_active_printer_profile_id() == "klipper-profile-1"

    def test_primary_export_format_defaults_to_gcode(self, qapp, temp_config_dir):
        """测试标题栏主导出格式默认值。"""
        from src.business.settings_manager import SettingsManager

        sm = SettingsManager(temp_config_dir)

        assert sm.get_primary_export_format() == "gcode"

    def test_primary_export_format_persists(self, qapp, temp_config_dir):
        """测试标题栏主导出格式会持久化到 QSettings。"""
        from src.business.settings_manager import SettingsManager

        sm = SettingsManager(temp_config_dir)
        sm.set_primary_export_format("stl")

        sm2 = SettingsManager(temp_config_dir)

        assert sm.get_primary_export_format() == "stl"
        assert sm2.get_primary_export_format() == "stl"

    def test_primary_export_format_falls_back_to_gcode_for_invalid_value(self, qapp, temp_config_dir):
        """测试非法导出格式会回退到默认 G-code。"""
        from src.business.settings_manager import SettingsManager

        sm = SettingsManager(temp_config_dir)
        sm.set_primary_export_format("invalid")

        assert sm.get_primary_export_format() == "gcode"


class TestPresetManagerFull:
    """预设管理器完整参数测试"""

    @pytest.fixture
    def temp_presets_dir(self):
        """创建临时预设目录"""
        base_dir = Path.cwd() / ".tmp_pytest_presets"
        base_dir.mkdir(parents=True, exist_ok=True)
        tmpdir = base_dir / f"case_{uuid.uuid4().hex}"
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            yield str(tmpdir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_load_builtin_preset(self, temp_presets_dir):
        """测试加载内置预设"""
        pm = PresetManager(temp_presets_dir)

        params = pm.load_preset("标准斜边字")
        assert params.shell.height == 30.0
        assert params.shell.edge_type == EdgeType.BEVELED

    def test_save_and_load_full_preset(self, temp_presets_dir):
        """测试保存和加载完整预设"""
        pm = PresetManager(temp_presets_dir)

        params = SliceParams()
        params.shell.layer_height = 0.5
        params.shell.height = 40.0
        params.skirt.enabled = True
        params.skirt.width = 8.0
        params.step.panel_step_enabled = True
        params.step.print_speed = 36.0
        params.speed.print_speed = 60.0

        pm.save_preset_full("测试预设", params, "这是一个测试预设")

        # 重新加载
        loaded = pm.load_preset("测试预设")

        assert loaded.shell.height == 40.0
        assert loaded.skirt.enabled is True
        assert loaded.skirt.width == 8.0
        assert loaded.step.panel_step_enabled is True
        assert loaded.step.print_speed == pytest.approx(36.0)
        assert loaded.speed.print_speed == 60.0

        with open(Path(temp_presets_dir) / "测试预设.preset", "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["version"] == PresetManager.PRESET_VERSION
        assert saved["shell"]["height_layers"] == 80
        assert "height" not in saved["shell"]

    def test_save_shell_only_preset_uses_layer_count_fields(self, temp_presets_dir):
        """测试仅 shell 预设也写入层数字段"""
        pm = PresetManager(temp_presets_dir)
        params = SliceParams()
        params.shell.layer_height = 0.5
        params.shell.height = 36.0

        pm.save_preset("仅壳体预设", params, full_params=False)

        with open(Path(temp_presets_dir) / "仅壳体预设.preset", "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["version"] == PresetManager.PRESET_VERSION
        assert saved["shell"]["height_layers"] == 72
        assert "height" not in saved["shell"]

    def test_preset_info(self, temp_presets_dir):
        """测试获取预设信息"""
        pm = PresetManager(temp_presets_dir)

        info = pm.get_preset_info("标准直边字")
        assert info["name"] == "标准直边字"
        assert info["is_builtin"] is True

    def test_user_vs_builtin_presets(self, temp_presets_dir):
        """测试用户预设和内置预设区分"""
        pm = PresetManager(temp_presets_dir)

        params = SliceParams()
        pm.save_preset("用户预设1", params)

        builtin = pm.get_builtin_presets()
        user = pm.get_user_presets()

        assert "标准直边字" in builtin
        assert "用户预设1" in user
        assert "用户预设1" not in builtin

    def test_delete_user_preset(self, temp_presets_dir):
        """测试删除用户预设"""
        pm = PresetManager(temp_presets_dir)

        params = SliceParams()
        pm.save_preset("临时预设", params)

        assert "临时预设" in pm.list_presets()

        pm.delete_preset("临时预设")
        assert "临时预设" not in pm.list_presets()

    def test_cannot_delete_builtin(self, temp_presets_dir):
        """测试不能删除内置预设"""
        pm = PresetManager(temp_presets_dir)

        with pytest.raises(ValueError):
            pm.delete_preset("标准直边字")

    def test_export_import_preset(self, temp_presets_dir):
        """测试导出和导入预设"""
        pm = PresetManager(temp_presets_dir)

        # 创建预设
        params = SliceParams()
        params.shell.layer_height = 0.5
        params.shell.height = 38.0
        pm.save_preset_full("导出测试", params)

        # 导出
        export_path = os.path.join(temp_presets_dir, "exported.preset")
        pm.export_preset("导出测试", export_path)

        # 删除原预设
        pm.delete_preset("导出测试")
        assert "导出测试" not in pm.list_presets()

        # 导入
        imported_name = pm.import_preset(export_path, "导入的预设")
        assert imported_name == "导入的预设"

        loaded = pm.load_preset("导入的预设")
        assert loaded.shell.height == 38.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
