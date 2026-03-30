"""
MINGDA SignMaker - 设置管理器

架构设计：
- JSON文件（用户配置目录下的 slice_params.json）: 保存切片参数（layout 除外，复杂结构便于备份迁移）
- QSettings (平台原生): 语言、窗口状态、UI设置、最近文件等

这样避免了多个模块同时写入同一个文件导致的冲突。
"""

import json
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QMainWindow

from src.core.types import LayoutParams, SliceParams, serialize_params, deserialize_params


class SettingsManager:
    """设置管理器

    混合架构：
    - JSON 文件: 保存切片参数（layout 除外，便于备份和迁移）
    - QSettings: 语言、窗口状态、UI设置等（平台原生存储）
    """

    # 配置文件版本
    CONFIG_VERSION = "3.0"

    # 最近文件列表的最大数量
    MAX_RECENT_FILES = 10

    # QSettings 组织和应用名称
    ORGANIZATION = "MINGDA"
    APPLICATION = "SignMaker"

    def __init__(self, config_dir: Optional[str] = None):
        """初始化设置管理器"""
        # JSON 配置文件路径（只用于切片参数）
        if config_dir:
            self._config_dir = Path(config_dir)
            self._legacy_params_files: List[Path] = []
            self._qsettings = QSettings(
                str(self._config_dir / "ui_settings.ini"),
                QSettings.Format.IniFormat
            )
        else:
            self._config_dir = self._get_default_config_dir()
            self._qsettings = QSettings(self.ORGANIZATION, self.APPLICATION)

        self._params_file = self._config_dir / "slice_params.json"
        if not config_dir:
            self._legacy_params_files = self._get_legacy_params_files()

    @classmethod
    def _get_default_config_dir(cls) -> Path:
        """获取默认配置目录。

        打包后的程序不能依赖应用目录可写，因此默认落到平台的用户配置目录。
        """
        config_root = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.GenericConfigLocation
        )
        if config_root:
            return Path(config_root) / cls.ORGANIZATION / cls.APPLICATION

        return Path.home() / ".config" / cls.ORGANIZATION / cls.APPLICATION

    def _get_legacy_params_files(self) -> List[Path]:
        """返回旧版本可能使用过的参数文件位置。

        旧逻辑把参数固定写到项目/应用目录下的 config 目录。
        新版本优先使用用户配置目录，但仍尝试迁移旧文件。
        """
        legacy_dirs = [
            Path(__file__).resolve().parent.parent.parent / "config",
        ]
        if getattr(sys, "frozen", False):
            legacy_dirs.append(Path(sys.executable).resolve().parent / "config")

        legacy_files: List[Path] = []
        seen = set()
        current_target = str(self._params_file.resolve(strict=False))

        for config_dir in legacy_dirs:
            params_file = config_dir / "slice_params.json"
            resolved = str(params_file.resolve(strict=False))
            if resolved == current_target or resolved in seen:
                continue
            seen.add(resolved)
            legacy_files.append(params_file)

        return legacy_files

    def _migrate_legacy_params_file(self) -> bool:
        """将旧位置的参数文件迁移到用户配置目录。"""
        if self._params_file.exists():
            return True

        for legacy_file in self._legacy_params_files:
            if not legacy_file.exists():
                continue

            try:
                import shutil

                self._config_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy_file, self._params_file)
                return True
            except Exception:
                continue

        return False

    # =========================================================================
    # 切片参数（使用 JSON 文件）
    # =========================================================================

    def has_saved_layout_params(self) -> bool:
        """判断是否已保存排版参数。"""
        return any(
            self._qsettings.contains(key)
            for key in (
                "Layout/auto_arrange",
                "Layout/spacing",
                "Layout/margin",
            )
        )

    def get_layout_params(self) -> Optional[LayoutParams]:
        """获取保存在 QSettings 中的排版参数。"""
        if not self.has_saved_layout_params():
            return None
        return LayoutParams(
            auto_arrange=self._qsettings.value("Layout/auto_arrange", True, type=bool),
            spacing=self._qsettings.value("Layout/spacing", 10.0, type=float),
            margin=self._qsettings.value("Layout/margin", 20.0, type=float),
        )

    def set_layout_params(self, layout: LayoutParams):
        """将排版参数保存到 QSettings。"""
        self._qsettings.setValue("Layout/auto_arrange", bool(layout.auto_arrange))
        self._qsettings.setValue("Layout/spacing", float(layout.spacing))
        self._qsettings.setValue("Layout/margin", float(layout.margin))

    def clear_layout_params(self):
        """清除保存在 QSettings 中的排版参数。"""
        self._qsettings.remove("Layout")

    def _merge_saved_layout(self, params: Optional[SliceParams]) -> Optional[SliceParams]:
        """将 QSettings 中的排版参数合并到切片参数。"""
        saved_layout = self.get_layout_params()
        if params is None:
            if saved_layout is None:
                return None
            params = SliceParams()
        if saved_layout is not None:
            params.layout = saved_layout
        return params

    def get_last_params(self) -> Optional[SliceParams]:
        """获取最后使用的切片参数"""
        if not self._params_file.exists():
            self._migrate_legacy_params_file()
        params: Optional[SliceParams] = None
        if not self._params_file.exists():
            return self._merge_saved_layout(None)

        try:
            with open(self._params_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            params_data = data.get("params")
            if params_data:
                params = deserialize_params(params_data)
                if not self.has_saved_layout_params():
                    self.set_layout_params(params.layout)
        except Exception:
            return self._merge_saved_layout(None)
        return self._merge_saved_layout(params)

    def set_last_params(self, params: SliceParams) -> bool:
        """保存最后使用的切片参数"""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            self.set_layout_params(params.layout)

            params_data = serialize_params(params)
            params_data.pop("layout", None)

            data = {
                "version": self.CONFIG_VERSION,
                "last_modified": datetime.now().isoformat(),
                "params": params_data
            }

            with open(self._params_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def clear_last_params(self):
        """清除保存的切片参数"""
        try:
            if self._params_file.exists():
                self._params_file.unlink()
        except Exception:
            pass
        self.clear_layout_params()

    # =========================================================================
    # 语言设置（使用 QSettings）
    # =========================================================================

    def get_language(self) -> str:
        """获取当前语言代码"""
        return self._qsettings.value("language", "zh_CN", type=str)

    def set_language(self, lang_code: str):
        """设置语言代码"""
        self._qsettings.setValue("language", lang_code)

    # =========================================================================
    # 窗口状态（使用 QSettings）
    # =========================================================================

    def save_window_state(self, window: QMainWindow):
        """保存窗口状态"""
        self._qsettings.beginGroup("MainWindow")
        self._qsettings.setValue("geometry", window.saveGeometry())
        self._qsettings.setValue("state", window.saveState())
        self._qsettings.setValue("maximized", window.isMaximized())
        self._qsettings.endGroup()

    def restore_window_state(self, window: QMainWindow) -> bool:
        """恢复窗口状态"""
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

    # =========================================================================
    # UI 设置（使用 QSettings）
    # =========================================================================

    def get_left_panel_width(self) -> int:
        """获取左侧面板宽度"""
        return self._qsettings.value("UI/left_panel_width", 280, type=int)

    def set_left_panel_width(self, width: int):
        """设置左侧面板宽度"""
        self._qsettings.setValue("UI/left_panel_width", width)

    def get_right_panel_width(self) -> int:
        """获取右侧面板宽度"""
        return self._qsettings.value("UI/right_panel_width", 250, type=int)

    def set_right_panel_width(self, width: int):
        """设置右侧面板宽度"""
        self._qsettings.setValue("UI/right_panel_width", width)

    def get_show_3d_preview(self) -> bool:
        """获取是否显示3D预览"""
        return self._qsettings.value("UI/show_3d_preview", False, type=bool)

    def set_show_3d_preview(self, show: bool):
        """设置是否显示3D预览"""
        self._qsettings.setValue("UI/show_3d_preview", show)

    def get_active_printer_profile_id(self) -> str:
        """获取当前激活的打印机档案 ID。"""
        return self._qsettings.value("PrinterProfile/active_id", "", type=str)

    def set_active_printer_profile_id(self, profile_id: str):
        """记录当前激活的打印机档案 ID。"""
        self._qsettings.setValue("PrinterProfile/active_id", profile_id)

    # =========================================================================
    # 最近文件（使用 QSettings）
    # =========================================================================

    def get_recent_files(self) -> List[str]:
        """获取最近打开的文件列表"""
        size = self._qsettings.beginReadArray("RecentFiles")
        files = []
        for i in range(size):
            self._qsettings.setArrayIndex(i)
            path = self._qsettings.value("path", "", type=str)
            if path:
                files.append(path)
        self._qsettings.endArray()
        return files

    def _write_recent_files(self, files: List[str]):
        """写回最近文件列表。"""
        self._qsettings.beginWriteArray("RecentFiles")
        for i, path in enumerate(files):
            self._qsettings.setArrayIndex(i)
            self._qsettings.setValue("path", path)
        self._qsettings.endArray()

    def add_recent_file(self, file_path: str):
        """添加文件到最近文件列表"""
        file_path = str(Path(file_path).resolve())
        recent = self.get_recent_files()

        # 去重
        if file_path in recent:
            recent.remove(file_path)

        # 添加到开头
        recent.insert(0, file_path)

        # 限制数量
        recent = recent[:self.MAX_RECENT_FILES]

        # 保存
        self._write_recent_files(recent)

    def remove_recent_file(self, file_path: str):
        """从最近文件列表移除指定文件。"""
        file_path = str(Path(file_path).resolve())
        recent = [path for path in self.get_recent_files() if path != file_path]
        self._write_recent_files(recent)

    def clear_recent_files(self):
        """清除最近文件列表"""
        self._write_recent_files([])

    # =========================================================================
    # 文件对话框目录（使用 QSettings）
    # =========================================================================

    @staticmethod
    def _normalize_dir_path(dir_path: str) -> Optional[str]:
        """规范化目录路径。"""
        if not dir_path:
            return None
        return str(Path(dir_path).expanduser().resolve(strict=False))

    def _get_dialog_dir(self, key: str, *, legacy_key: Optional[str] = None) -> Optional[str]:
        """读取记忆的对话框目录，并兼容旧键。"""
        dir_path = self._qsettings.value(key, None, type=str)
        if dir_path:
            return dir_path
        if legacy_key:
            return self._qsettings.value(legacy_key, None, type=str)
        return None

    def _set_dialog_dir(self, key: str, dir_path: str, *, legacy_key: Optional[str] = None):
        """写入记忆的对话框目录，并回写旧键保持兼容。"""
        normalized = self._normalize_dir_path(dir_path)
        if not normalized:
            return
        self._qsettings.setValue(key, normalized)
        if legacy_key:
            self._qsettings.setValue(legacy_key, normalized)

    def get_last_open_dir(self) -> Optional[str]:
        """获取最后一次打开文件使用的目录。"""
        return self._get_dialog_dir("Dialog/last_open_dir", legacy_key="Import/last_dir")

    def set_last_open_dir(self, dir_path: str):
        """设置最后一次打开文件使用的目录。"""
        self._set_dialog_dir("Dialog/last_open_dir", dir_path, legacy_key="Import/last_dir")

    def get_last_save_dir(self) -> Optional[str]:
        """获取最后一次保存文件使用的目录。"""
        return self._get_dialog_dir("Dialog/last_save_dir", legacy_key="Export/last_dir")

    def set_last_save_dir(self, dir_path: str):
        """设置最后一次保存文件使用的目录。"""
        self._set_dialog_dir("Dialog/last_save_dir", dir_path, legacy_key="Export/last_dir")

    def get_last_export_dir(self) -> Optional[str]:
        """兼容旧名称：获取最后的导出目录。"""
        return self.get_last_save_dir()

    def set_last_export_dir(self, dir_path: str):
        """兼容旧名称：设置最后的导出目录。"""
        self.set_last_save_dir(dir_path)

    def get_last_import_dir(self) -> Optional[str]:
        """兼容旧名称：获取最后的导入目录。"""
        return self.get_last_open_dir()

    def set_last_import_dir(self, dir_path: str):
        """兼容旧名称：设置最后的导入目录。"""
        self.set_last_open_dir(dir_path)

    # =========================================================================
    # 文字生成设置（使用 QSettings）
    # =========================================================================

    def get_text_font(self) -> str:
        """获取文字生成的字体名称"""
        return self._qsettings.value("TextGen/font", "", type=str)

    def set_text_font(self, font_name: str):
        """设置文字生成的字体名称"""
        self._qsettings.setValue("TextGen/font", font_name)

    def get_text_size(self) -> int:
        """获取文字生成的字体大小"""
        return self._qsettings.value("TextGen/size", 100, type=int)

    def set_text_size(self, size: int):
        """设置文字生成的字体大小"""
        self._qsettings.setValue("TextGen/size", size)

    def get_text_spacing(self) -> float:
        """获取文字生成的字符间距"""
        return self._qsettings.value("TextGen/spacing", 10.0, type=float)

    def set_text_spacing(self, spacing: float):
        """设置文字生成的字符间距"""
        self._qsettings.setValue("TextGen/spacing", spacing)

    # =========================================================================
    # 参数备份/恢复（便于迁移）
    # =========================================================================

    def export_params(self, file_path: str):
        """导出切片参数到指定文件"""
        if self._params_file.exists():
            import shutil
            shutil.copy(self._params_file, file_path)

    def import_params(self, file_path: str):
        """从文件导入切片参数"""
        import shutil
        self._config_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(file_path, self._params_file)

    def sync(self):
        """同步设置到存储"""
        self._qsettings.sync()


# 全局设置管理器实例
_settings_manager: Optional[SettingsManager] = None


def init_settings_manager(config_dir: Optional[str] = None) -> SettingsManager:
    """初始化全局设置管理器"""
    global _settings_manager
    _settings_manager = SettingsManager(config_dir)
    return _settings_manager


def get_settings_manager() -> Optional[SettingsManager]:
    """获取全局设置管理器实例"""
    return _settings_manager
