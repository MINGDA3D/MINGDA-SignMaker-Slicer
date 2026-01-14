"""
业务逻辑层模块

包含切片管理器、项目管理器和预设管理器。
"""

from .slice_manager import SliceManager
from .project_manager import ProjectManager
from .preset_manager import PresetManager

__all__ = ['SliceManager', 'ProjectManager', 'PresetManager']
