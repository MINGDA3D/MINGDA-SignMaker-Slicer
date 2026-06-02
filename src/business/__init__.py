"""
业务逻辑层模块

包含切片管理器、项目管理器、预设管理器、设置管理器和撤销/重做管理器。
"""

from .slice_manager import SliceManager
from .project_manager import ProjectManager
from .preset_manager import PresetManager
from .printer_profile_manager import PrinterProfileManager
from .settings_manager import (
    SettingsManager, init_settings_manager, get_settings_manager
)
from .update_manager import UpdateManager, UpdateInfo, UpdateAsset
from .undo_manager import (
    UndoManager, Command, CompositeCommand,
    MoveCommand, RotateCommand, ScaleCommand, MirrorCommand,
    DeleteCommand, AddContoursCommand, ReplaceContoursCommand,
    ReplaceSelectedContoursCommand,
    TransformCommand
)

__all__ = [
    'SliceManager', 'ProjectManager', 'PresetManager', 'PrinterProfileManager',
    'SettingsManager', 'init_settings_manager', 'get_settings_manager',
    'UpdateManager', 'UpdateInfo', 'UpdateAsset',
    'UndoManager', 'Command', 'CompositeCommand',
    'MoveCommand', 'RotateCommand', 'ScaleCommand', 'MirrorCommand',
    'DeleteCommand', 'AddContoursCommand', 'ReplaceContoursCommand',
    'ReplaceSelectedContoursCommand',
    'TransformCommand'
]
