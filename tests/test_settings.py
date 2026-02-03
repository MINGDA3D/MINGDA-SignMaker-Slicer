"""
MINGDA SignMaker - 设置管理器单元测试
"""

import json
import os
import tempfile
import pytest
from pathlib import Path

from src.core.types import (
    SliceParams, EdgeType, BevelDirection,
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
        assert data["shell"]["height"] == 30.0
        assert data["shell"]["edge_type"] == "STRAIGHT"

    def test_serialize_custom_params(self):
        """测试序列化自定义参数"""
        params = SliceParams()
        params.shell.height = 50.0
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_direction = BevelDirection.TOP_LARGE
        params.skirt.enabled = True
        params.skirt.width = 10.0

        data = serialize_params(params)

        assert data["shell"]["height"] == 50.0
        assert data["shell"]["edge_type"] == "BEVELED"
        assert data["shell"]["bevel_direction"] == "TOP_LARGE"
        assert data["skirt"]["enabled"] is True
        assert data["skirt"]["width"] == 10.0

    def test_deserialize_default_params(self):
        """测试反序列化默认参数"""
        params = SliceParams()
        data = serialize_params(params)
        restored = deserialize_params(data)

        assert restored.shell.height == 30.0
        assert restored.shell.edge_type == EdgeType.STRAIGHT
        assert restored.skirt.enabled is False

    def test_deserialize_custom_params(self):
        """测试反序列化自定义参数"""
        params = SliceParams()
        params.shell.height = 42.0
        params.shell.edge_type = EdgeType.BEVELED
        params.step.enabled = True
        params.step.panel_step_enabled = True
        params.speed.print_speed = 80.0

        data = serialize_params(params)
        restored = deserialize_params(data)

        assert restored.shell.height == 42.0
        assert restored.shell.edge_type == EdgeType.BEVELED
        assert restored.step.enabled is True
        assert restored.step.panel_step_enabled is True
        assert restored.speed.print_speed == 80.0

    def test_roundtrip_all_params(self):
        """测试完整参数的往返序列化"""
        params = SliceParams()

        # 修改各种参数
        params.shell.height = 35.0
        params.shell.wall_thickness = 1.5
        params.color.enabled = True
        params.step.panel_step_enabled = True
        params.skirt.enabled = True
        params.connected.enabled = True
        params.edge_wrap.wrap_enabled = True
        params.bottom_face.enabled = True
        params.top_face.enabled = True
        params.gcode.extruder1_temp = 230
        params.machine.bed_width = 500.0

        data = serialize_params(params)
        restored = deserialize_params(data)

        assert restored.shell.height == 35.0
        assert restored.shell.wall_thickness == 1.5
        assert restored.color.enabled is True
        assert restored.step.panel_step_enabled is True
        assert restored.skirt.enabled is True
        assert restored.connected.enabled is True
        assert restored.edge_wrap.wrap_enabled is True
        assert restored.bottom_face.enabled is True
        assert restored.top_face.enabled is True
        assert restored.gcode.extruder1_temp == 230
        assert restored.machine.bed_width == 500.0

    def test_deserialize_empty_dict(self):
        """测试反序列化空字典"""
        restored = deserialize_params({})
        assert restored.shell.height == 30.0  # 默认值

    def test_deserialize_partial_data(self):
        """测试反序列化部分数据"""
        data = {
            "shell": {"height": 45.0},
            "speed": {"print_speed": 70.0}
        }
        restored = deserialize_params(data)

        assert restored.shell.height == 45.0
        assert restored.speed.print_speed == 70.0
        # 其他参数应使用默认值
        assert restored.skirt.enabled is False


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
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

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
        assert data["params"]["shell"]["height"] == 45.0

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


class TestPresetManagerFull:
    """预设管理器完整参数测试"""

    @pytest.fixture
    def temp_presets_dir(self):
        """创建临时预设目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

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
        params.shell.height = 40.0
        params.skirt.enabled = True
        params.skirt.width = 8.0
        params.step.panel_step_enabled = True
        params.speed.print_speed = 60.0

        pm.save_preset_full("测试预设", params, "这是一个测试预设")

        # 重新加载
        loaded = pm.load_preset("测试预设")

        assert loaded.shell.height == 40.0
        assert loaded.skirt.enabled is True
        assert loaded.skirt.width == 8.0
        assert loaded.step.panel_step_enabled is True
        assert loaded.speed.print_speed == 60.0

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
