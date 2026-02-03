"""
MINGDA SignMaker - 设置管理器

采用混合架构：
- QSettings: 窗口几何、UI状态等简单设置（平台原生存储）
- JSON文件: 切片参数、预设等复杂设置（便于备份和迁移）

参考了 PrusaSlicer 和 Cura 的实现方式，3D切片软件通常使用文件存储
切片参数，因为：
1. 参数结构复杂，有多层嵌套
2. 用户需要备份、迁移、分享配置
3. 便于调试和手动编辑
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from PySide6.QtCore import QSettings, QByteArray
from PySide6.QtWidgets import QMainWindow

from src.core.types import SliceParams, serialize_params, deserialize_params


class SettingsManager:
    """设置管理器

    混合架构：
    - 使用 QSettings 保存窗口状态（利用Qt的跨平台特性）
    - 使用 JSON 文件保存切片参数（便于备份和迁移）

    这种方式结合了两者的优点：
    - QSettings: 自动处理平台差异，适合简单的 UI 状态
    - JSON: 人类可读，易于备份/分享，适合复杂的业务参数
    """

    # 配置文件版本，用于未来的格式升级
    CONFIG_VERSION = "1.1"

    # 最近文件列表的最大数量
    MAX_RECENT_FILES = 10

    # QSettings 组织和应用名称
    ORGANIZATION = "MINGDA"
    APPLICATION = "SignMaker"

    def __init__(self, config_dir: Optional[str] = None):
        """初始化设置管理器

        Args:
            config_dir: 配置目录路径，默认为项目根目录下的 config 目录
        """
        # JSON 配置文件路径
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = Path(__file__).parent.parent.parent / "config"

        self._config_file = self._config_dir / "settings.json"

        # QSettings 用于窗口状态
        self._qsettings = QSettings(self.ORGANIZATION, self.APPLICATION)

        # JSON 设置缓存（切片参数等）
        self._json_settings: Dict[str, Any] = self._get_default_json_settings()

        # 加载 JSON 设置
        self._load_json_settings()

    def _get_default_json_settings(self) -> Dict[str, Any]:
        """获取默认 JSON 设置"""
        return {
            "version": self.CONFIG_VERSION,
            "language": "zh_CN",
            "last_used_params": None,
            "recent_files": [],
            "export": {
                "last_export_dir": None,
                "last_gcode_filename": None
            },
            "last_modified": None
        }

    def _load_json_settings(self):
        """从 JSON 文件加载设置"""
        if not self._config_file.exists():
            return

        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            # 合并加载的设置到默认设置中
            self._merge_settings(self._json_settings, loaded)

        except Exception as e:
            print(f"[SettingsManager] 加载 JSON 设置失败: {e}")

    def _merge_settings(self, target: dict, source: dict):
        """递归合并设置"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_settings(target[key], value)
            else:
                target[key] = value

    def _save_json_settings(self):
        """保存 JSON 设置到文件"""
        try:
            # 确保配置目录存在
            self._config_dir.mkdir(parents=True, exist_ok=True)

            # 更新最后修改时间
            self._json_settings["last_modified"] = datetime.now().isoformat()

            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._json_settings, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[SettingsManager] 保存 JSON 设置失败: {e}")

    # =========================================================================
    # 窗口状态（使用 QSettings）
    # =========================================================================

    def save_window_state(self, window: QMainWindow):
        """保存窗口状态

        使用 QSettings 保存窗口几何信息和状态，这是 Qt 推荐的做法。
        QSettings 会自动处理不同平台的存储位置。

        Args:
            window: 主窗口实例
        """
        self._qsettings.beginGroup("MainWindow")
        self._qsettings.setValue("geometry", window.saveGeometry())
        self._qsettings.setValue("state", window.saveState())
        self._qsettings.setValue("maximized", window.isMaximized())
        self._qsettings.endGroup()

    def restore_window_state(self, window: QMainWindow) -> bool:
        """恢复窗口状态

        Args:
            window: 主窗口实例

        Returns:
            是否成功恢复（如果没有保存的状态则返回 False）
        """
        self._qsettings.beginGroup("MainWindow")
        geometry = self._qsettings.value("geometry")
        state = self._qsettings.value("state")
        maximized = self._qsettings.value("maximized", False, type=bool)
        self._qsettings.endGroup()

        if geometry:
            window.restoreGeometry(geometry)
            if state:
                window.restoreState(state)
            if maximized:
                window.showMaximized()
            return True
        return False

    def get_window_geometry(self) -> Dict[str, Any]:
        """获取窗口几何信息（兼容旧接口）"""
        self._qsettings.beginGroup("MainWindow")
        result = {
            "maximized": self._qsettings.value("maximized", False, type=bool)
        }
        self._qsettings.endGroup()
        return result

    def set_window_geometry(self, width: int, height: int,
                            x: Optional[int] = None, y: Optional[int] = None,
                            maximized: bool = False):
        """保存窗口几何信息（兼容旧接口）

        注意：推荐使用 save_window_state() 代替此方法
        """
        self._qsettings.beginGroup("MainWindow")
        self._qsettings.setValue("maximized", maximized)
        self._qsettings.endGroup()

    # =========================================================================
    # UI 设置（使用 QSettings）
    # =========================================================================

    def get_ui_setting(self, key: str, default: Any = None, value_type: type = None) -> Any:
        """获取 UI 设置

        Args:
            key: 设置键
            default: 默认值
            value_type: 值类型

        Returns:
            设置值
        """
        self._qsettings.beginGroup("UI")
        if value_type:
            value = self._qsettings.value(key, default, type=value_type)
        else:
            value = self._qsettings.value(key, default)
        self._qsettings.endGroup()
        return value

    def set_ui_setting(self, key: str, value: Any):
        """设置 UI 设置

        Args:
            key: 设置键
            value: 设置值
        """
        self._qsettings.beginGroup("UI")
        self._qsettings.setValue(key, value)
        self._qsettings.endGroup()

    def get_ui_settings(self) -> Dict[str, Any]:
        """获取所有 UI 设置"""
        self._qsettings.beginGroup("UI")
        keys = self._qsettings.childKeys()
        result = {key: self._qsettings.value(key) for key in keys}
        self._qsettings.endGroup()

        # 提供默认值
        result.setdefault("left_panel_width", 280)
        result.setdefault("right_panel_width", 250)
        result.setdefault("show_3d_preview", False)
        return result

    def get_left_panel_width(self) -> int:
        """获取左侧面板宽度"""
        return self.get_ui_setting("left_panel_width", 280, int)

    def set_left_panel_width(self, width: int):
        """设置左侧面板宽度"""
        self.set_ui_setting("left_panel_width", width)

    def get_right_panel_width(self) -> int:
        """获取右侧面板宽度"""
        return self.get_ui_setting("right_panel_width", 250, int)

    def set_right_panel_width(self, width: int):
        """设置右侧面板宽度"""
        self.set_ui_setting("right_panel_width", width)

    # =========================================================================
    # 语言设置（使用 JSON，因为 TranslationManager 也需要访问）
    # =========================================================================

    def get_language(self) -> str:
        """获取当前语言代码"""
        return self._json_settings.get("language", "zh_CN")

    def set_language(self, lang_code: str):
        """设置语言代码"""
        self._json_settings["language"] = lang_code
        self._save_json_settings()

    # =========================================================================
    # 切片参数（使用 JSON，复杂结构便于备份迁移）
    # =========================================================================

    def get_last_params(self) -> Optional[SliceParams]:
        """获取最后使用的切片参数

        Returns:
            SliceParams 对象，如果没有保存的参数则返回 None
        """
        params_data = self._json_settings.get("last_used_params")
        if params_data:
            try:
                return deserialize_params(params_data)
            except Exception as e:
                print(f"[SettingsManager] 反序列化参数失败: {e}")
        return None

    def set_last_params(self, params: SliceParams):
        """保存最后使用的切片参数

        Args:
            params: 切片参数对象
        """
        try:
            self._json_settings["last_used_params"] = serialize_params(params)
            self._save_json_settings()
        except Exception as e:
            print(f"[SettingsManager] 序列化参数失败: {e}")

    def clear_last_params(self):
        """清除保存的切片参数"""
        self._json_settings["last_used_params"] = None
        self._save_json_settings()

    # =========================================================================
    # 最近文件（使用 JSON）
    # =========================================================================

    def get_recent_files(self) -> List[str]:
        """获取最近打开的文件列表"""
        return self._json_settings.get("recent_files", [])

    def add_recent_file(self, file_path: str):
        """添加文件到最近文件列表"""
        recent = self._json_settings.get("recent_files", [])

        # 规范化路径
        file_path = str(Path(file_path).resolve())

        # 如果文件已在列表中，移除旧的
        if file_path in recent:
            recent.remove(file_path)

        # 添加到列表开头
        recent.insert(0, file_path)

        # 限制列表长度
        self._json_settings["recent_files"] = recent[:self.MAX_RECENT_FILES]
        self._save_json_settings()

    def remove_recent_file(self, file_path: str):
        """从最近文件列表中移除文件"""
        recent = self._json_settings.get("recent_files", [])
        file_path = str(Path(file_path).resolve())
        if file_path in recent:
            recent.remove(file_path)
            self._json_settings["recent_files"] = recent
            self._save_json_settings()

    def clear_recent_files(self):
        """清除最近文件列表"""
        self._json_settings["recent_files"] = []
        self._save_json_settings()

    # =========================================================================
    # 导出设置（使用 JSON）
    # =========================================================================

    def get_last_export_dir(self) -> Optional[str]:
        """获取最后的导出目录"""
        return self._json_settings.get("export", {}).get("last_export_dir")

    def set_last_export_dir(self, dir_path: str):
        """设置最后的导出目录"""
        if "export" not in self._json_settings:
            self._json_settings["export"] = {}
        self._json_settings["export"]["last_export_dir"] = str(Path(dir_path).resolve())
        self._save_json_settings()

    # =========================================================================
    # 通用设置访问（JSON）
    # =========================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """获取 JSON 设置值

        Args:
            key: 设置键（支持点号分隔的嵌套键）
            default: 默认值
        """
        keys = key.split(".")
        value = self._json_settings
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        """设置 JSON 值

        Args:
            key: 设置键（支持点号分隔的嵌套键）
            value: 设置值
        """
        keys = key.split(".")
        target = self._json_settings
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self._save_json_settings()

    def save(self):
        """手动保存所有设置"""
        self._save_json_settings()
        self._qsettings.sync()

    # =========================================================================
    # 配置导出/导入（便于备份和迁移）
    # =========================================================================

    def export_config(self, file_path: str):
        """导出完整配置到文件

        Args:
            file_path: 导出文件路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self._json_settings, f, ensure_ascii=False, indent=2)

    def import_config(self, file_path: str):
        """从文件导入配置

        Args:
            file_path: 配置文件路径
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            imported = json.load(f)

        # 合并导入的设置
        self._merge_settings(self._json_settings, imported)
        self._save_json_settings()


# 全局设置管理器实例
_settings_manager: Optional[SettingsManager] = None


def init_settings_manager(config_dir: Optional[str] = None) -> SettingsManager:
    """初始化全局设置管理器

    Args:
        config_dir: 配置目录路径

    Returns:
        设置管理器实例
    """
    global _settings_manager
    _settings_manager = SettingsManager(config_dir)
    return _settings_manager


def get_settings_manager() -> Optional[SettingsManager]:
    """获取全局设置管理器实例"""
    return _settings_manager
