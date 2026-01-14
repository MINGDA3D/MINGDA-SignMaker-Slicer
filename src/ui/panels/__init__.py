"""
UI参数面板模块

包含所有参数设置面板组件。
"""

from .shell_panel import ShellPanel
from .color_panel import ColorPanel
from .step_panel import StepPanel
from .skirt_panel import SkirtPanel
from .connected_panel import ConnectedPanel
from .edge_wrap_panel import EdgeWrapPanel
from .panel_fill_panel import PanelFillPanel
from .export_panel import ExportPanel
from .speed_panel import SpeedPanel
from .machine_panel import MachinePanel

__all__ = [
    'ShellPanel',
    'ColorPanel',
    'StepPanel',
    'SkirtPanel',
    'ConnectedPanel',
    'EdgeWrapPanel',
    'PanelFillPanel',
    'ExportPanel',
    'SpeedPanel',
    'MachinePanel',
]
