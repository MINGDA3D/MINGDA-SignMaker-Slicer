# Core algorithms for MINGDA SignMaker

from .types import (
    # 基础几何类型
    Point, Point3D, Path, Contour, EdgeProfile,
    # 层数据
    Layer, LayerPath, LayerInfo,
    # 枚举类型
    PathType, PathRole, EdgeType, ExtruderType, FillPattern, JoinType,
    # 参数类型
    SliceParams, ShellParams, ColorParams, ColorLayerConfig, ColorChangePoint,
    PrimeTowerParams, StepParams, StepConfig, SkirtParams, ConnectedParams,
    EdgeWrapParams, PanelParams, BaseplateParams, GridParams,
    LayoutParams, SpeedParams, GCodeParams, MachineParams, PrinterProfile,
    FillConfig, LayerConfig,
    # 结果类型
    SliceResult, ProjectData, ProjectMeta, Project
)

from .dxf_parser import DXFParser
from .svg_parser import SVGParser
from .path_offset import PathOffset, EndType
from .slice_engine import SliceEngine
from .gcode_writer import GCodeWriter, write_gcode
from .bevel_generator import BevelGenerator
from .step_generator import StepGenerator
from .fill_generator import FillGenerator
from .skirt_generator import SkirtGenerator
from .connected_generator import ConnectedGenerator
from .dxf_writer import DXFWriter, export_baseplate_dxf, export_panel_dxf

__all__ = [
    # 基础几何类型
    'Point', 'Point3D', 'Path', 'Contour', 'EdgeProfile',
    # 层数据
    'Layer', 'LayerPath', 'LayerInfo',
    # 枚举类型
    'PathType', 'PathRole', 'EdgeType', 'ExtruderType', 'FillPattern', 'JoinType',
    # 参数类型
    'SliceParams', 'ShellParams', 'ColorParams', 'ColorLayerConfig', 'ColorChangePoint',
    'PrimeTowerParams', 'StepParams', 'StepConfig', 'SkirtParams', 'ConnectedParams',
    'EdgeWrapParams', 'PanelParams', 'BaseplateParams', 'GridParams',
    'LayoutParams', 'SpeedParams', 'GCodeParams', 'MachineParams', 'PrinterProfile',
    'FillConfig', 'LayerConfig',
    # 结果类型
    'SliceResult', 'ProjectData', 'ProjectMeta', 'Project',
    # 核心类
    'DXFParser', 'SVGParser', 'PathOffset', 'EndType', 'SliceEngine',
    'GCodeWriter', 'write_gcode',
    # 生成器
    'BevelGenerator', 'StepGenerator', 'FillGenerator',
    'SkirtGenerator', 'ConnectedGenerator',
    # DXF写入
    'DXFWriter', 'export_baseplate_dxf', 'export_panel_dxf',
]
