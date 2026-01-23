"""
SignMaker Slicer - 核心数据类型定义

定义切片器使用的所有基础数据结构，包括：
- 几何类型：Point, Point3D, Path, Contour
- 层数据：Layer, LayerPath
- 参数类型：SliceParams 及其子参数
- 枚举类型：PathType, EdgeType, ExtruderType 等
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple, Dict


# =============================================================================
# 枚举类型
# =============================================================================

class PathType(Enum):
    """路径类型"""
    OUTER = auto()      # 外轮廓
    INNER = auto()      # 内孔
    CONNECTED = auto()  # 连襟框（青色）
    HOLE = auto()       # 底孔（绿色）
    PATTERN = auto()    # 面板花纹（蓝色）


class PathRole(Enum):
    """路径角色（打印时的用途）"""
    WALL = auto()           # 壁/外墙
    SAFETY_LINE = auto()    # 预打边线/安全线
    SKIRT = auto()          # 防翘裙边
    STEP = auto()           # 台阶
    V_GROOVE = auto()       # V槽
    FILL_PANEL = auto()     # 面板填充
    FILL_GRID = auto()      # 网格填充
    FILL_BASEPLATE = auto() # 底板填充
    EDGE_WRAP = auto()      # 包边
    OUTLINE = auto()        # 勾边
    CONNECTED = auto()      # 连襟


class EdgeType(Enum):
    """边缘类型"""
    STRAIGHT = auto()   # 直边
    BEVELED = auto()    # 斜边
    CUSTOM = auto()     # 异形边（自定义轮廓）


class BevelDirection(Enum):
    """斜边方向"""
    TOP_SMALL = auto()  # 上小下大（底部大，顶部小）
    TOP_LARGE = auto()  # 上大下小（底部小，顶部大）


class ExtruderType(Enum):
    """挤出机类型"""
    EXTRUDER_1 = 1
    EXTRUDER_2 = 2
    EXTRUDER_3 = 3


class FillPattern(Enum):
    """填充图案"""
    LINES = auto()      # 线性填充
    GRID = auto()       # 网格填充
    ZIGZAG = auto()     # 之字形填充
    CONCENTRIC = auto() # 同心圆填充


class JoinType(Enum):
    """拐角连接类型（用于路径偏移）"""
    MITER = auto()   # 尖角
    ROUND = auto()   # 圆角
    SQUARE = auto()  # 方角


# =============================================================================
# 基础几何类型
# =============================================================================

@dataclass
class Point:
    """2D点"""
    x: float
    y: float

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return False
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __hash__(self) -> int:
        return hash((round(self.x, 6), round(self.y, 6)))

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def to_int_tuple(self, scale: float = 1000) -> Tuple[int, int]:
        """转换为整数元组（用于pyclipper）"""
        return (int(self.x * scale), int(self.y * scale))


@dataclass
class Point3D:
    """3D点"""
    x: float
    y: float
    z: float

    def to_2d(self) -> Point:
        return Point(self.x, self.y)


@dataclass
class Path:
    """路径（点序列）"""
    points: List[Point] = field(default_factory=list)
    path_type: PathType = PathType.OUTER
    color: Tuple[int, int, int] = (0, 0, 0)  # RGB颜色
    is_closed: bool = True

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """获取边界框 (min_x, min_y, max_x, max_y)"""
        if not self.points:
            return (0, 0, 0, 0)
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))

    @property
    def area(self) -> float:
        """计算面积（Shoelace公式）"""
        n = len(self.points)
        if n < 3:
            return 0
        area = 0
        for i in range(n):
            j = (i + 1) % n
            area += self.points[i].x * self.points[j].y
            area -= self.points[j].x * self.points[i].y
        return abs(area) / 2

    @property
    def length(self) -> float:
        """计算路径长度"""
        import math
        total = 0
        n = len(self.points)
        for i in range(n):
            j = (i + 1) % n if self.is_closed else i + 1
            if j >= n:
                break
            dx = self.points[j].x - self.points[i].x
            dy = self.points[j].y - self.points[i].y
            total += math.sqrt(dx * dx + dy * dy)
        return total

    def to_tuple_list(self) -> List[Tuple[float, float]]:
        """转换为元组列表"""
        return [p.to_tuple() for p in self.points]

    def to_int_tuple_list(self, scale: float = 1000) -> List[Tuple[int, int]]:
        """转换为整数元组列表（用于pyclipper）"""
        return [p.to_int_tuple(scale) for p in self.points]


@dataclass
class EdgeProfile:
    """异形边轮廓定义"""
    # points 是 [(normalized_height, offset), ...] 的列表
    # normalized_height: 0.0 = 底部, 1.0 = 顶部
    # offset: 负值表示内缩
    points: List[Point] = field(default_factory=list)
    name: str = ""


@dataclass
class Contour:
    """轮廓（包含外边界和内孔）"""
    outer: Path = field(default_factory=Path)
    holes: List[Path] = field(default_factory=list)
    connected_frames: List[Path] = field(default_factory=list)  # 连襟框
    patterns: List[Path] = field(default_factory=list)          # 面板花纹
    name: str = ""
    # 用户设置的属性
    start_point_index: int = 0  # 起始点索引
    print_order: int = 0        # 打印顺序


# =============================================================================
# 层数据类型
# =============================================================================

@dataclass
class LayerPath:
    """层路径（打印路径）"""
    points: List[Point] = field(default_factory=list)
    role: PathRole = PathRole.WALL
    extruder: ExtruderType = ExtruderType.EXTRUDER_1
    line_width: float = 1.2
    is_closed: bool = True
    speed_multiplier: float = 1.0  # 速度倍率


@dataclass
class Layer:
    """打印层"""
    z_height: float = 0.0           # 层底部高度
    layer_height: float = 0.3       # 层厚度
    extruder: ExtruderType = ExtruderType.EXTRUDER_1
    paths: List[LayerPath] = field(default_factory=list)


@dataclass
class LayerInfo:
    """层信息（用于规划）"""
    z_height: float              # 层底部高度
    layer_height: float          # 层厚度
    extruder: ExtruderType       # 使用的挤出机
    is_first_layer: bool = False # 是否首层
    is_step_layer: bool = False  # 是否台阶层
    step_config: Optional[StepConfig] = None  # 台阶配置
    has_skirt: bool = False      # 是否有防翘裙边
    has_edge_wrap: bool = False  # 是否有包边/勾边


# =============================================================================
# 参数类型
# =============================================================================

@dataclass
class ShellParams:
    """字壳工艺参数"""
    height: float = 30.0              # 字壳高度 (mm)
    layer_height: float = 0.3         # 层高 (mm)
    wall_thickness: float = 1.2       # 壁厚 (mm)
    wall_count: int = 1               # 壁数量（走线次数）
    wall_offset: float = 0.0          # 壁偏移

    # 边缘类型
    edge_type: EdgeType = EdgeType.STRAIGHT

    # 斜边参数
    bevel_width: float = 5.0          # 斜边宽度 (mm) - 水平方向的收缩/扩展量
    bevel_direction: BevelDirection = BevelDirection.TOP_SMALL  # 斜边方向

    # 底板和面板厚度
    baseplate_thickness: float = 10.0  # 底板厚度 (mm) - 底部直边区域高度
    panel_thickness: float = 3.0       # 面板厚度 (mm) - 顶部直边区域高度

    # 异形边轮廓
    edge_profile: Optional[EdgeProfile] = None

    # 预打边线（安全线）
    safety_line_count: int = 0        # 安全线数量
    safety_line_offset: float = 5.0   # 安全线偏移距离


@dataclass
class ColorLayerConfig:
    """换色层配置"""
    height: float = 10.0              # 层高度 (mm)
    extruder: ExtruderType = ExtruderType.EXTRUDER_1


@dataclass
class ColorParams:
    """换色层参数"""
    enabled: bool = False
    layers: List[ColorLayerConfig] = field(default_factory=list)


@dataclass
class StepConfig:
    """单个台阶配置"""
    enabled: bool = True
    position: float = 0.0             # 台阶位置（高度）
    width: float = 3.0                # 台阶宽度
    height: float = 2.0               # 台阶高度
    is_v_groove: bool = False         # 是否为V槽


@dataclass
class StepParams:
    """台阶/V槽参数

    支持三种台阶类型：
    1. 面板台阶 (panel_step) - 在字壳顶部，用于安装亚克力面板
    2. 底板台阶 (baseplate_step) - 在字壳底部，用于安装底板
    3. 自定义台阶 (steps) - 用户可在任意位置添加的台阶
    """
    enabled: bool = False

    # 面板台阶（顶部）- 用于安装面板
    panel_step_enabled: bool = False
    panel_step_height: float = 3.0      # 面板厚度/台阶高度 (mm)
    panel_step_width: float = 3.0       # 台阶向内延伸宽度 (mm)
    panel_step_is_v_groove: bool = False  # 是否为V槽

    # 底板台阶（底部）- 用于安装底板
    baseplate_step_enabled: bool = False
    baseplate_step_height: float = 3.0  # 底板厚度/台阶高度 (mm)
    baseplate_step_width: float = 3.0   # 台阶向内延伸宽度 (mm)
    baseplate_step_is_v_groove: bool = False  # 是否为V槽

    # 自定义台阶列表
    steps: List[StepConfig] = field(default_factory=list)

    # 兼容旧参数（将逐步弃用）
    top_step_enabled: bool = False
    top_step_height: float = 2.0
    top_step_width: float = 3.0
    bottom_groove_enabled: bool = False
    bottom_groove_height: float = 2.0
    bottom_groove_depth: float = 3.0

    # 打印参数
    step_thickness: float = 0.3        # 台阶层高（用于V槽分层）
    extrusion_width: float = 1.2       # 台阶吐丝宽度
    print_speed: float = 30.0          # 台阶打印速度 (mm/s)
    horizontal_offset: float = 0.0     # 喷头水平偏移


@dataclass
class SkirtParams:
    """防翘裙边参数

    裙边结构（截面图）：
      字壳 ════════════════════════════════════════════
           ╲          ╱╲          ╱╲          ╱
            ╲        ╱  ╲        ╱  ╲        ╱
             ╲      ╱    ╲      ╱    ╲      ╱
              ╲    ╱      ╲    ╱      ╲    ╱
               ────        ────        ────

    相邻梯形共享斜边，形成连续的波浪形防翘结构。
    """
    enabled: bool = False
    width: float = 5.0                # 裙边宽度 (mm) - 梯形底部宽度
    height: float = 0.3               # 裙边高度 (mm) - 用于STL导出，最小0.2
    offset: float = 0.0               # 距离轮廓的偏移 (mm) - 通常为0，贴着字壳
    interval: float = 10.0            # 梯形间距 (mm) - 相邻梯形顶边的中心距离
    is_outer: bool = True             # 是否外部裙边（True=外部，False=内部孔）

    # 以下参数用于G-code生成
    extrusion_width: float = 1.2      # 吐丝宽度
    length: float = 10.0              # 旧参数，保持兼容
    v_opening: float = 5.0            # 旧参数，保持兼容
    line_width: float = 1.2           # 旧参数，保持兼容


class EdgeDirection(Enum):
    """包边/勾边方向"""
    INNER = auto()    # 内部（向内延伸）
    OUTER = auto()    # 外部（向外延伸）


@dataclass
class ConnectedParams:
    """连襟字参数"""
    enabled: bool = False
    bridge_width: float = 10.0        # 连接桥宽度
    bridge_height: float = 5.0        # 连接桥高度


@dataclass
class EdgeWrapParams:
    """包边/勾边参数"""
    wrap_enabled: bool = False        # 包边开启
    wrap_width: float = 2.0           # 包边宽度
    wrap_height: float = 3.0          # 包边高度
    wrap_direction: EdgeDirection = EdgeDirection.INNER  # 包边方向

    outline_enabled: bool = False     # 勾边开启
    outline_width: float = 1.0        # 勾边宽度
    outline_height: float = 1.0       # 勾边高度（厚度）
    outline_offset: float = 0.0       # 勾边偏移
    outline_direction: EdgeDirection = EdgeDirection.INNER  # 勾边方向


@dataclass
class FillConfig:
    """填充配置"""
    spacing: float = 5.0              # 填充间距
    spacing2: float = 3.0             # 第二层填充间距
    angle: float = 45.0               # 填充角度
    boundary_distance: float = 1.0    # 边界距离


@dataclass
class LayerConfig:
    """层配置"""
    extrusion_width: float = 0.4
    extruder: Optional[ExtruderType] = None


@dataclass
class PanelParams:
    """面板设置参数"""
    enabled: bool = False
    fill_config: FillConfig = field(default_factory=FillConfig)
    front_layer: LayerConfig = field(default_factory=LayerConfig)
    back_layer: LayerConfig = field(default_factory=LayerConfig)
    # 花纹支持
    pattern_enabled: bool = False
    pattern_paths: List[Path] = field(default_factory=list)


@dataclass
class BaseplateParams:
    """底板设置参数"""
    enabled: bool = False
    thickness: float = 10.0
    fill_config: FillConfig = field(default_factory=FillConfig)
    layer: LayerConfig = field(default_factory=LayerConfig)


@dataclass
class GridParams:
    """网格填充参数（灌胶用）"""
    enabled: bool = False
    fill_config: FillConfig = field(default_factory=FillConfig)
    layer: LayerConfig = field(default_factory=LayerConfig)


@dataclass
class LayoutParams:
    """排版设置参数"""
    auto_arrange: bool = True
    spacing: float = 10.0             # 字间距
    margin: float = 20.0              # 边距


@dataclass
class SpeedParams:
    """速度设置参数"""
    print_speed: float = 50.0         # 打印速度 (mm/s)
    travel_speed: float = 150.0       # 空走速度 (mm/s)
    first_layer_speed: float = 20.0   # 首层速度 (mm/s)
    wall_speed: float = 40.0          # 壁速度
    fill_speed: float = 60.0          # 填充速度


@dataclass
class GCodeParams:
    """G-code生成参数"""
    machine_type: str = "MINGDA"

    # 温度
    extruder1_temp: int = 220
    extruder2_temp: int = 220
    extruder3_temp: int = 0
    bed_temp: int = 60

    # 回抽
    retract_length: float = 2.0
    retract_speed: float = 40.0

    # 换色
    color_change_retract: float = 30.0
    color_change_prime: float = 35.0

    # Z轴抬升
    z_hop_height1: float = 0.5        # 短距离抬升
    z_hop_height2: float = 5.0        # 长距离抬升
    distance_threshold: float = 100.0  # 距离阈值

    # 打料
    prime_length: float = 5.0

    # 线材
    filament_diameter: float = 1.75

    # 速度（从SpeedParams复制）
    print_speed: float = 50.0
    travel_speed: float = 150.0
    first_layer_speed: float = 20.0

    # 结束位置
    end_z_position: float = 100.0


@dataclass
class MachineParams:
    """机器设置参数"""
    name: str = "MINGDA"
    bed_width: float = 400.0
    bed_depth: float = 400.0
    bed_height: float = 500.0
    nozzle_diameter: float = 0.8
    extruder_count: int = 2


@dataclass
class SliceParams:
    """切片总参数"""
    shell: ShellParams = field(default_factory=ShellParams)
    color: ColorParams = field(default_factory=ColorParams)
    step: StepParams = field(default_factory=StepParams)
    skirt: SkirtParams = field(default_factory=SkirtParams)
    connected: ConnectedParams = field(default_factory=ConnectedParams)
    edge_wrap: EdgeWrapParams = field(default_factory=EdgeWrapParams)
    panel: PanelParams = field(default_factory=PanelParams)
    baseplate: BaseplateParams = field(default_factory=BaseplateParams)
    grid: GridParams = field(default_factory=GridParams)
    layout: LayoutParams = field(default_factory=LayoutParams)
    speed: SpeedParams = field(default_factory=SpeedParams)
    gcode: GCodeParams = field(default_factory=GCodeParams)
    machine: MachineParams = field(default_factory=MachineParams)


# =============================================================================
# 结果类型
# =============================================================================

@dataclass
class SliceResult:
    """切片结果"""
    layers: List[Layer] = field(default_factory=list)
    total_layers: int = 0
    total_height: float = 0.0
    estimated_time: float = 0.0       # 预估打印时间 (秒)
    estimated_filament: float = 0.0   # 预估线材长度 (米)
    filament_per_extruder: Dict[ExtruderType, float] = field(default_factory=dict)


@dataclass
class ProjectData:
    """项目数据（保存/加载用）"""
    contours: List[Contour] = field(default_factory=list)
    params: SliceParams = field(default_factory=SliceParams)
    file_path: str = ""
    name: str = ""


@dataclass
class ProjectMeta:
    """项目元数据"""
    name: str = ""
    created_at: str = ""
    modified_at: str = ""
    version: str = "1.0"
    author: str = ""
    description: str = ""


@dataclass
class Project:
    """项目（包含元数据和数据）"""
    meta: ProjectMeta = field(default_factory=ProjectMeta)
    contours: List[Contour] = field(default_factory=list)
    params: SliceParams = field(default_factory=SliceParams)
    gcode_params: GCodeParams = field(default_factory=GCodeParams)
