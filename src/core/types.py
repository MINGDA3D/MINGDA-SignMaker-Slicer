"""
MINGDA SignMaker - 核心数据类型定义

定义切片器使用的所有基础数据结构，包括：
- 几何类型：Point, Point3D, Path, Contour
- 层数据：Layer, LayerPath
- 参数类型：SliceParams 及其子参数
- 枚举类型：PathType, EdgeType, ExtruderType 等
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
import math
from typing import List, Optional, Tuple, Dict
from uuid import uuid4


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
    PRIME_TOWER = auto()    # Prime tower
    SKIRT = auto()          # 防翘裙边
    STEP = auto()           # 台阶
    V_GROOVE = auto()       # V槽
    FILL_PANEL = auto()     # 面板填充
    FILL_GRID = auto()      # 网格填充
    FILL_BASEPLATE = auto() # 底板填充
    FILL_BOTTOM_FACE = auto()  # 底面封闭填充
    LIGHT_SLOT = auto()     # 灯槽
    FILL_TOP_FACE = auto()     # 顶面封闭填充
    EDGE_WRAP = auto()      # 包边
    OUTLINE = auto()        # 勾边
    CONNECTED = auto()      # 连襟


class EdgeType(Enum):
    """边缘类型"""
    STRAIGHT = auto()   # 直边
    BEVELED = auto()    # 斜边
    CUSTOM = auto()     # 异形边（自定义轮廓）


class EdgeProfileType(Enum):
    """异形边轮廓类型"""
    PRESET = auto()     # 预设模板
    CUSTOM = auto()     # 自定义轮廓
    DXF = auto()        # 从DXF文件加载


class InterpolationType(Enum):
    """插值类型"""
    LINEAR = "linear"       # 线性插值
    CUBIC = "cubic"         # 三次样条插值
    BEZIER = "bezier"       # 贝塞尔曲线插值
    BSPLINE = "bspline"     # B样条插值（兼容INC-S）


class BevelDirection(Enum):
    """斜边方向"""
    TOP_SMALL = auto()  # 上小下大（底面保持原始尺寸，顶部缩小）
    TOP_LARGE = auto()  # 上大下小（底面保持原始尺寸，顶部放大）


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
    start_point_index: int = 0  # 0=自动；1..N 表示显式顶点 0..N-1

    print_order: int = 0

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
        return area / 2

    @property
    def signed_area(self) -> float:
        """计算有符号面积（正=逆时针，负=顺时针）"""
        return self.area

    @property
    def centroid(self) -> Point:
        """计算路径的几何中心（质心）"""
        if not self.points:
            return Point(0, 0)
        n = len(self.points)
        if n == 1:
            return self.points[0]
        if n == 2:
            return Point(
                (self.points[0].x + self.points[1].x) / 2,
                (self.points[0].y + self.points[1].y) / 2
            )

        # 使用多边形质心公式
        cx, cy = 0.0, 0.0
        signed_area = 0.0

        for i in range(n):
            j = (i + 1) % n
            x0, y0 = self.points[i].x, self.points[i].y
            x1, y1 = self.points[j].x, self.points[j].y
            cross = x0 * y1 - x1 * y0
            signed_area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross

        if abs(signed_area) < 1e-10:
            # 退化情况：使用边界框中心
            bounds = self.bounds
            return Point(
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2
            )

        signed_area /= 2
        cx /= (6 * signed_area)
        cy /= (6 * signed_area)
        return Point(cx, cy)

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
    """异形边轮廓定义

    用于定义异形边的轮廓曲线。支持预设模板、自定义绘制和DXF导入三种方式。

    坐标系说明：
    - control_points 使用归一化坐标 [(nx, nz), ...]
    - nx: 水平偏移比例，0.0 = 无偏移，1.0 = 最大偏移（bevel_width）
    - nz: 高度比例，0.0 = 底部，1.0 = 顶部

    示例：
        # 简单斜边：底部无偏移，顶部最大偏移
        control_points = [(0.0, 0.0), (1.0, 1.0)]

        # 圆弧边：使用贝塞尔曲线
        control_points = [(0.0, 0.0), (0.3, 0.5), (1.0, 1.0)]
        interpolation = InterpolationType.BEZIER
    """
    # 轮廓类型
    profile_type: EdgeProfileType = EdgeProfileType.PRESET

    # 预设名称（当 profile_type == PRESET 时使用）
    preset_name: str = ""

    # 控制点列表（归一化坐标）
    # 格式: [(nx, nz), ...] 其中 nx, nz ∈ [0, 1]
    control_points: List[Tuple[float, float]] = field(default_factory=list)

    # 插值方式
    interpolation: InterpolationType = InterpolationType.LINEAR

    # 采样参数
    sample_points: int = 100  # 轮廓曲线采样点数

    # 原始尺寸（从DXF加载时记录）
    original_width: float = 0.0   # 原始宽度 (mm)
    original_height: float = 0.0  # 原始高度 (mm)

    # 来源信息
    source_file: str = ""  # 来源文件路径（DXF导入时记录）
    name: str = ""         # 轮廓名称
    description: str = ""  # 轮廓描述

    # 旧字段（保持兼容）
    points: List[Point] = field(default_factory=list)

    def get_offset_at_height(self, normalized_z: float, bevel_width: float,
                              shell_height: float = 0.0) -> float:
        """
        获取给定高度处的偏移量

        Args:
            normalized_z: 归一化高度 (0.0-1.0)
            bevel_width: 斜边宽度 (mm)，作为最大限制或独立缩放模式的宽度
            shell_height: 字壳高度 (mm)，用于等比例缩放模式

        Returns:
            偏移量 (mm)，正值表示向外凸出
        """
        if not self.control_points:
            return 0.0

        # 计算实际使用的边缘宽度
        # 如果有原始宽高比信息，优先使用等比例缩放
        actual_edge_width = bevel_width
        if self.original_width > 0 and self.original_height > 0 and shell_height > 0:
            # 使用原始宽高比计算等比例缩放的边缘宽度
            aspect_ratio = self.original_width / self.original_height
            proportional_width = shell_height * aspect_ratio
            # 使用等比例计算的宽度，但不超过用户设置的bevel_width
            actual_edge_width = min(proportional_width, bevel_width) if bevel_width > 0 else proportional_width

        # 按Z坐标排序控制点
        sorted_points = sorted(self.control_points, key=lambda p: p[1])

        # 边界情况
        if normalized_z <= sorted_points[0][1]:
            return sorted_points[0][0] * actual_edge_width
        if normalized_z >= sorted_points[-1][1]:
            return sorted_points[-1][0] * actual_edge_width

        # 线性插值查找
        for i in range(len(sorted_points) - 1):
            nx1, nz1 = sorted_points[i]
            nx2, nz2 = sorted_points[i + 1]

            if nz1 <= normalized_z <= nz2:
                if nz2 == nz1:
                    return nx1 * actual_edge_width
                t = (normalized_z - nz1) / (nz2 - nz1)
                nx = nx1 + t * (nx2 - nx1)
                return nx * actual_edge_width

        return 0.0

    @classmethod
    def from_preset(cls, preset_name: str) -> "EdgeProfile":
        """从预设名称创建轮廓（需要配合 edge_presets 模块使用）"""
        return cls(
            profile_type=EdgeProfileType.PRESET,
            preset_name=preset_name,
            name=preset_name
        )

    @classmethod
    def from_control_points(
        cls,
        control_points: List[Tuple[float, float]],
        interpolation: InterpolationType = InterpolationType.LINEAR,
        name: str = "自定义"
    ) -> "EdgeProfile":
        """从控制点创建自定义轮廓"""
        return cls(
            profile_type=EdgeProfileType.CUSTOM,
            control_points=control_points,
            interpolation=interpolation,
            name=name
        )

    def to_dict(self) -> dict:
        """序列化为字典（用于保存）"""
        return {
            "profile_type": self.profile_type.name,
            "preset_name": self.preset_name,
            "control_points": self.control_points,
            "interpolation": self.interpolation.value,
            "sample_points": self.sample_points,
            "original_width": self.original_width,
            "original_height": self.original_height,
            "source_file": self.source_file,
            "name": self.name,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EdgeProfile":
        """从字典反序列化"""
        profile_type = EdgeProfileType[data.get("profile_type", "CUSTOM")]
        interpolation_value = data.get("interpolation", "linear")

        # 处理插值类型
        if isinstance(interpolation_value, str):
            try:
                interpolation = InterpolationType(interpolation_value)
            except ValueError:
                interpolation = InterpolationType.LINEAR
        else:
            interpolation = InterpolationType.LINEAR

        return cls(
            profile_type=profile_type,
            preset_name=data.get("preset_name", ""),
            control_points=data.get("control_points", []),
            interpolation=interpolation,
            sample_points=data.get("sample_points", 100),
            original_width=data.get("original_width", 0.0),
            original_height=data.get("original_height", 0.0),
            source_file=data.get("source_file", ""),
            name=data.get("name", ""),
            description=data.get("description", "")
        )


@dataclass(init=False)
class Contour:
    """轮廓（包含外边界和内孔）"""
    outer: Path = field(default_factory=Path)
    holes: List[Path] = field(default_factory=list)
    connected_frames: List[Path] = field(default_factory=list)  # 连襟框
    patterns: List[Path] = field(default_factory=list)          # 面板花纹
    name: str = ""
    asset_id: str = ""
    asset_name: str = ""
    group_id: str = ""

    def __init__(
        self,
        outer: Optional[Path] = None,
        holes: Optional[List[Path]] = None,
        connected_frames: Optional[List[Path]] = None,
        patterns: Optional[List[Path]] = None,
        name: str = "",
        asset_id: str = "",
        asset_name: str = "",
        group_id: str = "",
        start_point_index: int = 0,
        print_order: int = 0,
    ):
        self.outer = outer if outer is not None else Path()
        self.holes = list(holes) if holes is not None else []
        self.connected_frames = list(connected_frames) if connected_frames is not None else []
        self.patterns = list(patterns) if patterns is not None else []
        self.name = name
        self.asset_id = asset_id
        self.asset_name = asset_name
        self.group_id = group_id
        self.print_order = print_order
        if start_point_index != 0 or self.outer.start_point_index == 0:
            self.outer.start_point_index = start_point_index

    @property
    def start_point_index(self) -> int:
        return self.outer.start_point_index

    @start_point_index.setter
    def start_point_index(self, value: int) -> None:
        self.outer.start_point_index = value

    @property
    def print_order(self) -> int:
        """Compatibility proxy for legacy contour-level print order."""
        return self.outer.print_order

    @print_order.setter
    def print_order(self, value: int) -> None:
        self.outer.print_order = value


def normalize_path_start_point_index(path: Path) -> int:
    """Clamp the stored start-point token to auto or a valid explicit vertex."""
    point_count = len(path.points)
    if point_count <= 0:
        path.start_point_index = 0
        return 0

    if path.start_point_index < 0 or path.start_point_index > point_count:
        path.start_point_index = 0

    return path.start_point_index


def get_path_user_start_point_index(path: Path) -> Optional[int]:
    """Return the explicit user-selected vertex index, or None when auto."""
    point_count = len(path.points)
    if point_count <= 0:
        path.start_point_index = 0
        return None

    stored_index = normalize_path_start_point_index(path)
    if stored_index <= 0:
        return None

    vertex_index = stored_index - 1
    if 0 <= vertex_index < point_count:
        return vertex_index

    path.start_point_index = 0
    return None


def set_path_user_start_point_index(path: Path, point_index: int) -> int:
    """Store an explicit user-selected start-point vertex index."""
    point_count = len(path.points)
    if point_count <= 0:
        path.start_point_index = 0
        return 0
    if point_index < 0 or point_index >= point_count:
        raise ValueError(
            f"Start point index {point_index} out of range for path with {point_count} points."
        )

    path.start_point_index = point_index + 1
    return path.start_point_index


def normalize_contour_start_point_index(contour: Contour) -> int:
    """Normalize the outer and hole start-point tokens for a contour."""
    normalize_path_start_point_index(contour.outer)
    for hole in contour.holes:
        normalize_path_start_point_index(hole)
    return contour.start_point_index


def get_contour_user_start_point_index(contour: Contour) -> Optional[int]:
    return get_path_user_start_point_index(contour.outer)


def set_contour_user_start_point_index(contour: Contour, point_index: int) -> int:
    return set_path_user_start_point_index(contour.outer, point_index)


def get_path_start_point_candidate_indices(
    path: Path,
    *,
    corner_threshold_degrees: float = 150.0,
    fallback_limit: int = 8,
) -> List[int]:
    """Return stable candidate vertex indices for start-point selection/auto-pick."""
    normalize_path_start_point_index(path)
    points = path.points
    point_count = len(points)
    if point_count <= 0:
        return []
    if point_count <= 2:
        explicit_index = get_path_user_start_point_index(path)
        return [explicit_index if explicit_index is not None else 0]

    candidate_indices = _get_sharp_start_point_candidate_indices(
        points,
        corner_threshold_degrees,
    )
    candidate_indices = _dedupe_start_point_candidates(points, candidate_indices)
    if not candidate_indices:
        candidate_indices = _get_fallback_start_point_indices(
            path,
            fallback_limit=fallback_limit,
        )

    explicit_index = get_path_user_start_point_index(path)
    if explicit_index is not None and explicit_index not in candidate_indices:
        candidate_indices.append(explicit_index)

    return sorted(set(candidate_indices))


def get_contour_start_point_candidate_indices(
    contour: Contour,
    *,
    corner_threshold_degrees: float = 150.0,
    fallback_limit: int = 8,
) -> List[int]:
    return get_path_start_point_candidate_indices(
        contour.outer,
        corner_threshold_degrees=corner_threshold_degrees,
        fallback_limit=fallback_limit,
    )


def resolve_path_start_point_index(path: Path) -> int:
    """Resolve the effective start-point vertex index for display and slicing."""
    point_count = len(path.points)
    if point_count <= 0:
        path.start_point_index = 0
        return 0

    explicit_index = get_path_user_start_point_index(path)
    if explicit_index is not None:
        return explicit_index

    points = path.points
    sharp_candidate_indices = _get_sharp_start_point_candidate_indices(points, 150.0)
    sharp_candidate_indices = _dedupe_start_point_candidates(points, sharp_candidate_indices)
    if sharp_candidate_indices:
        return min(
            sharp_candidate_indices,
            key=lambda index: (
                round(_corner_angle_degrees(points, index), 6),
                -points[index].x,
                -points[index].y,
                index,
            ),
        )

    candidate_indices = get_path_start_point_candidate_indices(path)
    if not candidate_indices:
        return 0

    return max(
        candidate_indices,
        key=lambda index: (points[index].x, points[index].y, -index),
    )


def resolve_contour_start_point_index(contour: Contour) -> int:
    return resolve_path_start_point_index(contour.outer)


def migrate_legacy_contour_start_point_index(contour: Contour) -> int:
    """Convert pre-4.3 raw vertex storage to the new 0=auto, 1..N=explicit token."""
    point_count = len(contour.outer.points)
    if point_count <= 0:
        contour.start_point_index = 0
        return 0

    legacy_index = contour.start_point_index
    if legacy_index <= 0:
        contour.start_point_index = 0
    elif legacy_index < point_count:
        contour.start_point_index = legacy_index + 1
    else:
        contour.start_point_index = 0

    return contour.start_point_index


def _is_sharp_corner(
    points: List[Point],
    index: int,
    corner_threshold_degrees: float,
) -> bool:
    """Return True when the vertex interior angle is sharp enough to be a candidate."""
    angle = _corner_angle_degrees(points, index)
    return angle is not None and angle <= corner_threshold_degrees


def _get_sharp_start_point_candidate_indices(
    points: List[Point],
    corner_threshold_degrees: float,
) -> List[int]:
    """Return candidate indices whose interior angle is sharp enough."""
    return [
        index
        for index in range(len(points))
        if _is_sharp_corner(points, index, corner_threshold_degrees)
    ]


def _corner_angle_degrees(points: List[Point], index: int) -> Optional[float]:
    """Return the vertex interior angle in degrees, or None for degenerate vertices."""
    point_count = len(points)
    if point_count < 3:
        return None

    prev_point = points[(index - 1) % point_count]
    current_point = points[index]
    next_point = points[(index + 1) % point_count]

    vec_a_x = prev_point.x - current_point.x
    vec_a_y = prev_point.y - current_point.y
    vec_b_x = next_point.x - current_point.x
    vec_b_y = next_point.y - current_point.y

    len_a = math.hypot(vec_a_x, vec_a_y)
    len_b = math.hypot(vec_b_x, vec_b_y)
    if len_a <= 1e-6 or len_b <= 1e-6:
        return None

    cos_angle = (vec_a_x * vec_b_x + vec_a_y * vec_b_y) / (len_a * len_b)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))


def _dedupe_start_point_candidates(
    points: List[Point],
    candidate_indices: List[int],
) -> List[int]:
    """Filter near-duplicate corner candidates produced by dense curve sampling."""
    if not candidate_indices:
        return []

    kept: List[int] = []
    proximity_threshold = _get_start_point_proximity_threshold(points)
    for candidate_index in candidate_indices:
        candidate_point = points[candidate_index]
        is_duplicate = False
        for kept_index in kept:
            kept_point = points[kept_index]
            if math.hypot(
                candidate_point.x - kept_point.x,
                candidate_point.y - kept_point.y,
            ) <= proximity_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(candidate_index)

    return kept


def _get_start_point_proximity_threshold(points: List[Point]) -> float:
    """Scale duplicate-filter distance with contour size."""
    if not points:
        return 0.5

    xs = [point.x for point in points]
    ys = [point.y for point in points]
    diagonal = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    return max(0.5, min(2.0, diagonal * 0.01))


def _get_fallback_start_point_indices(path: Path, *, fallback_limit: int) -> List[int]:
    """Sample a limited set of vertices when no sharp corners are available."""
    point_count = len(path.points)
    if point_count <= 0:
        return []

    if point_count <= fallback_limit:
        return list(range(point_count))

    return sorted(
        {
            int(round(sample_index * point_count / fallback_limit)) % point_count
            for sample_index in range(fallback_limit)
        }
    )


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
    color_index: int = 0
    paths: List[LayerPath] = field(default_factory=list)


@dataclass
class LayerInfo:
    """层信息（用于规划）"""
    z_height: float              # 层底部高度
    layer_height: float          # 层厚度
    extruder: ExtruderType       # 使用的挤出机
    color_index: int = 0         # 当前逻辑颜色槽位
    is_first_layer: bool = False # 是否首层
    is_step_layer: bool = False  # 是否台阶层
    step_config: Optional[StepConfig] = None  # 台阶配置
    has_skirt: bool = False      # 是否有防翘裙边
    has_edge_wrap: bool = False  # 是否有包边/勾边
    has_bottom_face: bool = False  # 是否有底面填充
    has_top_face: bool = False     # 是否有顶面填充


# =============================================================================
# 参数类型
# =============================================================================

@dataclass
class ShellParams:
    """字壳工艺参数"""
    height: float = 30.0              # 字壳高度 (mm)
    layer_height: float = 0.3         # 层高 (mm)
    line_width: float = 0.0           # 线宽 (mm), <= 0 时自动使用 layer_height * 2
    wall_thickness: float = 0.0       # 总壁厚 (mm), 由 wall_count * line_width 推导
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

    # DXF 导出补偿
    dxf_outer_clearance: float = 1.0   # 外轮廓安装公差：向内缩 (mm)
    dxf_hole_clearance: float = 1.0    # 内孔安装公差：向外扩 (mm)
    dxf_laser_kerf: float = 0.0        # 激光切缝宽度 (mm)，按半径补偿

    # 异形边轮廓
    edge_profile: Optional[EdgeProfile] = None

    # 预打边线（安全线）
    safety_line_count: int = 0        # 安全线数量
    safety_line_offset: float = 5.0   # 安全线偏移距离


@dataclass
class ColorChangePoint:
    """换色点配置"""
    height_mm: float = 10.0
    macro_index: int = 1


@dataclass
class ColorLayerConfig:
    """旧版换色层配置（仅用于兼容历史项目/参数）"""
    height: float = 10.0
    extruder: ExtruderType = ExtruderType.EXTRUDER_1


@dataclass
class ColorParams:
    """Klipper 单喷头换色参数"""
    enabled: bool = False
    change_points: List[ColorChangePoint] = field(default_factory=list)


@dataclass
class PrimeTowerParams:
    """Prime tower parameters."""
    enabled: bool = False
    center_x: float = 770.0
    center_y: float = 1170.0
    width: float = 20.0
    depth: float = 20.0
    infill_density_percent: int = 20


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
    panel_step_height: float = 28.0     # 面板厚度/台阶高度 (mm)
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
    outer_enabled: bool = True        # 外裙边：外轮廓朝外，内孔朝内
    inner_enabled: bool = False       # 内裙边：外轮廓朝内，内孔朝外
    is_outer: bool = True             # 旧参数，保留兼容

    # 以下参数用于G-code生成
    extrusion_width: float = 1.2      # 吐丝宽度
    length: float = 10.0              # 旧参数，保持兼容
    v_opening: float = 5.0            # 旧参数，保持兼容
    line_width: float = 1.2           # 旧参数，保持兼容


class EdgeDirection(Enum):
    """包边/勾边方向"""
    INNER = auto()    # 内部（向内延伸）
    OUTER = auto()    # 外部（向外延伸）


class ConnectedType(Enum):
    """连襟类型"""
    TRIANGLE = auto()   # 三角形连襟
    DIAMOND = auto()    # 菱形连襟


@dataclass
class ConnectedParams:
    """连襟字参数

    连襟是连接相邻字形的桥梁结构，用于将多个离散轮廓连接成一体。

    结构说明（三角形连襟侧视图）：
        字壳A ════════════════════════════════ 字壳B
              ╲                            ╱
               ╲        连襟斜边         ╱
                ╲                      ╱
                 ╲                    ╱
                  ════════════════════  ← 底座（直边）
    """
    enabled: bool = False
    type: str = "triangle"              # 连襟类型: "triangle" 或 "diamond"
    width: float = 5.0                  # 连襟宽度 (mm) - 连接桥的宽度
    height: float = 5.0                 # 斜边高度 (mm) - 顶部斜边的高度
    base_height: float = 5.0            # 底座高度 (mm) - 底部直边的高度
    support_offset: float = 2.5         # 支撑偏移 (mm) - 与字壳边缘的距离
    auto_detect: bool = True            # 自动检测连接点

    # 旧运行时别名，禁止序列化与反序列化
    bridge_width: float = 10.0          # 旧参数，同width
    bridge_height: float = 5.0          # 旧参数，同height


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
class BottomFaceParams:
    """底面封闭参数

    底面封闭用于在字壳底部生成密实填充层，封闭字壳底部。
    只需设置底面厚度，其他参数自动计算。
    """
    enabled: bool = False               # 是否启用底面封闭
    thickness: float = 1.0              # 底面厚度 (mm)，层数自动根据层高计算


@dataclass
class LightSlotParams:
    """底部灯槽参数"""
    enabled: bool = False
    width: float = 8.0
    depth: float = 3.0
    floor_layers: int = 2
    wall_gap: float = 0.0
    outer_enabled: bool = True
    hole_enabled: bool = True
    auto_skip_small_holes: bool = True
    min_hole_span: float = 12.0


@dataclass
class TopFaceParams:
    """顶面封闭参数

    顶面封闭用于在字壳顶部生成密实填充层，封闭字壳顶部。
    只需设置顶面厚度，其他参数自动计算。
    """
    enabled: bool = False               # 是否启用顶面封闭
    thickness: float = 1.0              # 顶面厚度 (mm)，层数自动根据层高计算


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


LEGACY_DEFAULT_START_GCODE = "G28"
LEGACY_DEFAULT_END_GCODE = ""
DEFAULT_START_GCODE_TEMPLATE = (
    "START_PRINT EXTRUDER={nozzle_temperature_initial_layer[0]} "
    "BED=[first_layer_bed_temperature] TOOL=[initial_tool]"
)
DEFAULT_END_GCODE_TEMPLATE = "END_PRINT"


def normalize_default_gcode_scripts(start_gcode: str, end_gcode: str) -> tuple[str, str]:
    if (
        start_gcode == LEGACY_DEFAULT_START_GCODE
        and end_gcode == LEGACY_DEFAULT_END_GCODE
    ):
        return DEFAULT_START_GCODE_TEMPLATE, DEFAULT_END_GCODE_TEMPLATE
    return start_gcode, end_gcode


@dataclass
class GCodeParams:
    """G-code生成参数"""
    machine_type: str = "Klipper"

    # 温度
    first_layer_nozzle_temp: int = 220
    other_layer_nozzle_temp: int = 220
    first_layer_bed_temp: int = 60
    other_layer_bed_temp: int = 60
    first_layer_fan_percent: int = 0
    other_layer_fan_percent: int = 100

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

    # Klipper 脚本
    start_gcode: str = DEFAULT_START_GCODE_TEMPLATE
    end_gcode: str = DEFAULT_END_GCODE_TEMPLATE
    color_change_command_template: str = "T{index}"


@dataclass
class MachineParams:
    """机器设置参数"""
    name: str = "MINGDA"
    bed_width: float = 800.0    # 发光字专用打印平台宽度
    bed_depth: float = 1200.0   # 发光字专用打印平台深度
    bed_height: float = 100.0   # 发光字打印高度
    nozzle_diameter: float = 0.8
    extruder_count: int = 2


@dataclass
class PrinterProfile:
    """打印机档案（独立于切片参数预设）"""
    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "Klipper Default"
    bed_width: float = 800.0
    bed_depth: float = 1200.0
    bed_height: float = 100.0
    nozzle_diameter: float = 0.8
    filament_diameter: float = 1.75
    retract_length: float = 2.0
    retract_speed: float = 40.0
    z_hop_short: float = 0.5
    z_hop_long: float = 5.0
    long_travel_threshold: float = 100.0
    start_gcode: str = DEFAULT_START_GCODE_TEMPLATE
    end_gcode: str = DEFAULT_END_GCODE_TEMPLATE
    color_change_command_template: str = "T{index}"


@dataclass
class SliceParams:
    """切片总参数"""
    shell: ShellParams = field(default_factory=ShellParams)
    color: ColorParams = field(default_factory=ColorParams)
    prime_tower: PrimeTowerParams = field(default_factory=PrimeTowerParams)
    step: StepParams = field(default_factory=StepParams)
    skirt: SkirtParams = field(default_factory=SkirtParams)
    connected: ConnectedParams = field(default_factory=ConnectedParams)
    edge_wrap: EdgeWrapParams = field(default_factory=EdgeWrapParams)
    panel: PanelParams = field(default_factory=PanelParams)
    baseplate: BaseplateParams = field(default_factory=BaseplateParams)
    grid: GridParams = field(default_factory=GridParams)
    bottom_face: BottomFaceParams = field(default_factory=BottomFaceParams)  # 底面封闭
    light_slot: LightSlotParams = field(default_factory=LightSlotParams)  # 灯槽
    top_face: TopFaceParams = field(default_factory=TopFaceParams)  # 顶面封闭
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
    active_printer_profile_id: str = ""
    printer_profile_snapshot: Optional[PrinterProfile] = None


# =============================================================================
# 参数序列化/反序列化辅助函数
# =============================================================================

def _serialize_enum(value) -> str:
    """序列化枚举值"""
    if isinstance(value, Enum):
        return value.name
    return value


def _deserialize_enum(enum_class, value):
    """反序列化枚举值"""
    if value is None:
        return None
    if isinstance(value, enum_class):
        return value
    if isinstance(value, str):
        try:
            return enum_class[value]
        except KeyError:
            # 尝试按值查找
            for member in enum_class:
                if member.value == value:
                    return member
            # 返回默认值
            return list(enum_class)[0]
    return value


def _height_to_layers(height_mm: float, layer_height: float, minimum: int = 1) -> int:
    """Convert a mm height into a stored layer count."""
    if layer_height <= 0:
        return minimum
    return max(minimum, int(round(height_mm / layer_height)))


def _layers_to_height(layers: float, layer_height: float) -> float:
    """Convert a stored layer count back into mm."""
    if layer_height <= 0:
        return 0.0
    return max(0.0, float(layers)) * layer_height


def default_shell_line_width(layer_height: float) -> float:
    """Return the default shell line width derived from layer height."""
    return round(max(layer_height, 0.001) * 2.0, 3)


def resolve_shell_line_width(
    line_width: float,
    layer_height: float,
    wall_thickness: float = 0.0,
    wall_count: int = 1,
) -> float:
    """Resolve the effective single-wall line width."""
    if line_width > 0:
        return line_width
    effective_wall_count = max(1, int(wall_count))
    if wall_thickness > 0:
        return wall_thickness / effective_wall_count
    return default_shell_line_width(layer_height)


def resolve_shell_wall_thickness(
    line_width: float,
    wall_count: int,
    layer_height: float,
    wall_thickness: float = 0.0,
) -> float:
    """Resolve the effective total shell wall thickness."""
    effective_wall_count = max(1, int(wall_count))
    return (
        resolve_shell_line_width(
            line_width,
            layer_height,
            wall_thickness=wall_thickness,
            wall_count=effective_wall_count,
        )
        * effective_wall_count
    )


def _reject_legacy_key(section_name: str, section_data: dict, legacy_key: str, replacement_key: str) -> None:
    """Reject legacy storage keys once a new schema is enabled."""
    if legacy_key in section_data:
        raise ValueError(
            f"Legacy field '{section_name}.{legacy_key}' is no longer supported; "
            f"use '{section_name}.{replacement_key}' instead."
        )


def _reject_legacy_layer_key(section_name: str, section_data: dict, legacy_key: str, layer_key: str) -> None:
    """Reject legacy height-based storage keys once layer-count storage is enabled."""
    _reject_legacy_key(section_name, section_data, legacy_key, layer_key)


def serialize_params(params: SliceParams) -> dict:
    """将 SliceParams 序列化为字典

    支持完整的参数序列化，包括：
    - 所有子参数组
    - 枚举类型转换为字符串
    - EdgeProfile 对象的序列化

    Args:
        params: 切片参数对象

    Returns:
        可以序列化为 JSON 的字典
    """
    def serialize_value(value):
        """递归序列化值"""
        if value is None:
            return None
        if isinstance(value, Enum):
            return value.name
        if isinstance(value, EdgeProfile):
            return value.to_dict()
        if isinstance(value, (list, tuple)):
            return [serialize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        if hasattr(value, '__dataclass_fields__'):
            # dataclass 对象
            result = {}
            for field_name in value.__dataclass_fields__:
                field_value = getattr(value, field_name)
                result[field_name] = serialize_value(field_value)
            return result
        if isinstance(value, Point):
            return {"x": value.x, "y": value.y}
        if isinstance(value, Path):
            return {
                "points": [{"x": p.x, "y": p.y} for p in value.points],
                "path_type": value.path_type.name,
                "color": list(value.color),
                "is_closed": value.is_closed
            }
        return value

    data = {
        "shell": serialize_value(params.shell),
        "color": serialize_value(params.color),
        "prime_tower": serialize_value(params.prime_tower),
        "step": serialize_value(params.step),
        "skirt": serialize_value(params.skirt),
        "connected": serialize_value(params.connected),
        "edge_wrap": serialize_value(params.edge_wrap),
        "panel": serialize_value(params.panel),
        "baseplate": serialize_value(params.baseplate),
        "grid": serialize_value(params.grid),
        "bottom_face": serialize_value(params.bottom_face),
        "light_slot": serialize_value(params.light_slot),
        "top_face": serialize_value(params.top_face),
        "layout": serialize_value(params.layout),
        "speed": serialize_value(params.speed),
        "gcode": serialize_value(params.gcode),
        "machine": serialize_value(params.machine),
    }

    layer_height = max(params.shell.layer_height, 0.001)

    data["shell"]["height_layers"] = _height_to_layers(params.shell.height, layer_height)
    data["shell"]["line_width"] = resolve_shell_line_width(
        params.shell.line_width,
        params.shell.layer_height,
        wall_thickness=params.shell.wall_thickness,
        wall_count=params.shell.wall_count,
    )
    data["shell"]["wall_count"] = max(1, int(params.shell.wall_count))
    data["shell"].pop("wall_thickness", None)
    data["shell"].pop("height", None)

    data["step"]["panel_step_layers"] = _height_to_layers(
        params.step.panel_step_height,
        layer_height,
    )
    data["step"]["baseplate_step_layers"] = _height_to_layers(
        params.step.baseplate_step_height,
        layer_height,
    )
    data["step"]["top_step_layers"] = _height_to_layers(
        params.step.top_step_height,
        layer_height,
    )
    data["step"]["bottom_groove_layers"] = _height_to_layers(
        params.step.bottom_groove_height,
        layer_height,
    )
    data["step"].pop("panel_step_height", None)
    data["step"].pop("baseplate_step_height", None)
    data["step"].pop("top_step_height", None)
    data["step"].pop("bottom_groove_height", None)

    data["connected"]["height_layers"] = _height_to_layers(
        params.connected.height,
        layer_height,
    )
    data["connected"]["base_height_layers"] = _height_to_layers(
        params.connected.base_height,
        layer_height,
    )
    data["connected"].pop("height", None)
    data["connected"].pop("base_height", None)
    data["connected"].pop("bridge_width", None)
    data["connected"].pop("bridge_height", None)

    data["bottom_face"]["thickness_layers"] = _height_to_layers(
        params.bottom_face.thickness,
        layer_height,
    )
    data["bottom_face"].pop("thickness", None)

    data["light_slot"]["depth_layers"] = _height_to_layers(
        params.light_slot.depth,
        layer_height,
    )
    data["light_slot"].pop("depth", None)

    data["top_face"]["thickness_layers"] = _height_to_layers(
        params.top_face.thickness,
        layer_height,
    )
    data["top_face"].pop("thickness", None)

    return data


def deserialize_params(data: dict) -> SliceParams:
    """从字典反序列化为 SliceParams

    Args:
        data: 包含参数数据的字典

    Returns:
        SliceParams 对象
    """
    params = SliceParams()

    if not data:
        params.shell.line_width = resolve_shell_line_width(
            params.shell.line_width,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
            wall_count=params.shell.wall_count,
        )
        params.shell.wall_thickness = resolve_shell_wall_thickness(
            params.shell.line_width,
            params.shell.wall_count,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
        )
        return params

    # Shell 参数
    if "shell" in data:
        shell_data = data["shell"]
        _reject_legacy_layer_key("shell", shell_data, "height", "height_layers")
        params.shell.layer_height = shell_data.get("layer_height", 0.3)
        params.shell.wall_count = max(1, int(shell_data.get("wall_count", 1)))
        params.shell.line_width = resolve_shell_line_width(
            shell_data.get("line_width", 0.0),
            params.shell.layer_height,
            wall_thickness=shell_data.get("wall_thickness", 0.0),
            wall_count=params.shell.wall_count,
        )
        if "height_layers" in shell_data:
            params.shell.height = _layers_to_height(
                shell_data["height_layers"],
                params.shell.layer_height,
            )
        params.shell.wall_thickness = resolve_shell_wall_thickness(
            params.shell.line_width,
            params.shell.wall_count,
            params.shell.layer_height,
            wall_thickness=shell_data.get("wall_thickness", 0.0),
        )
        params.shell.wall_offset = shell_data.get("wall_offset", 0.0)
        params.shell.edge_type = _deserialize_enum(EdgeType, shell_data.get("edge_type", "STRAIGHT"))
        params.shell.bevel_width = shell_data.get("bevel_width", 5.0)
        params.shell.bevel_direction = _deserialize_enum(
            BevelDirection, shell_data.get("bevel_direction", "TOP_SMALL")
        )
        params.shell.baseplate_thickness = shell_data.get("baseplate_thickness", 10.0)
        params.shell.panel_thickness = shell_data.get("panel_thickness", 3.0)
        params.shell.dxf_outer_clearance = shell_data.get("dxf_outer_clearance", 1.0)
        params.shell.dxf_hole_clearance = shell_data.get("dxf_hole_clearance", 1.0)
        params.shell.dxf_laser_kerf = shell_data.get("dxf_laser_kerf", 0.0)
        params.shell.safety_line_count = shell_data.get("safety_line_count", 0)
        params.shell.safety_line_offset = shell_data.get("safety_line_offset", 5.0)

        # EdgeProfile
        if shell_data.get("edge_profile"):
            params.shell.edge_profile = EdgeProfile.from_dict(shell_data["edge_profile"])

    # Color 参数
    if "color" in data:
        color_data = data["color"]
        params.color.enabled = color_data.get("enabled", False)
        if "change_points" in color_data:
            params.color.change_points = []
            for point_data in color_data["change_points"]:
                point = ColorChangePoint(
                    height_mm=point_data.get("height_mm", point_data.get("height", 10.0)),
                    macro_index=max(0, int(point_data.get("macro_index", 1))),
                )
                params.color.change_points.append(point)
        elif "layers" in color_data:
            params.color.change_points = []
            current_height = 0.0
            for layer_data in color_data["layers"]:
                layer = ColorLayerConfig(
                    height=layer_data.get("height", 10.0),
                    extruder=_deserialize_enum(ExtruderType, layer_data.get("extruder", "EXTRUDER_1"))
                )
                current_height += layer.height
                params.color.change_points.append(
                    ColorChangePoint(
                        height_mm=current_height,
                        macro_index=max(0, int(layer.extruder.value) - 1),
                    )
                )

    # Step 参数
    if "step" in data:
        step_data = data["step"]
        _reject_legacy_layer_key("step", step_data, "panel_step_height", "panel_step_layers")
        _reject_legacy_layer_key("step", step_data, "baseplate_step_height", "baseplate_step_layers")
        _reject_legacy_layer_key("step", step_data, "top_step_height", "top_step_layers")
        _reject_legacy_layer_key("step", step_data, "bottom_groove_height", "bottom_groove_layers")
        params.step.enabled = step_data.get("enabled", False)
        params.step.panel_step_enabled = step_data.get("panel_step_enabled", False)
        panel_step_layers = step_data.get("panel_step_layers")
        if panel_step_layers is not None:
            params.step.panel_step_height = _layers_to_height(
                panel_step_layers,
                params.shell.layer_height,
            )
        params.step.panel_step_width = step_data.get("panel_step_width", 3.0)
        params.step.panel_step_is_v_groove = step_data.get("panel_step_is_v_groove", False)
        params.step.baseplate_step_enabled = step_data.get("baseplate_step_enabled", False)
        baseplate_step_layers = step_data.get("baseplate_step_layers")
        if baseplate_step_layers is not None:
            params.step.baseplate_step_height = _layers_to_height(
                baseplate_step_layers,
                params.shell.layer_height,
            )
        params.step.baseplate_step_width = step_data.get("baseplate_step_width", 3.0)
        params.step.baseplate_step_is_v_groove = step_data.get("baseplate_step_is_v_groove", False)
        params.step.top_step_enabled = step_data.get("top_step_enabled", params.step.panel_step_enabled)
        top_step_layers = step_data.get("top_step_layers", panel_step_layers)
        if top_step_layers is not None:
            params.step.top_step_height = _layers_to_height(
                top_step_layers,
                params.shell.layer_height,
            )
        params.step.top_step_width = step_data.get("top_step_width", params.step.panel_step_width)
        params.step.bottom_groove_enabled = step_data.get(
            "bottom_groove_enabled",
            params.step.baseplate_step_enabled,
        )
        bottom_groove_layers = step_data.get("bottom_groove_layers", baseplate_step_layers)
        if bottom_groove_layers is not None:
            params.step.bottom_groove_height = _layers_to_height(
                bottom_groove_layers,
                params.shell.layer_height,
            )
        params.step.bottom_groove_depth = step_data.get(
            "bottom_groove_depth",
            params.step.baseplate_step_width,
        )
        params.step.step_thickness = step_data.get("step_thickness", 0.3)
        params.step.extrusion_width = step_data.get("extrusion_width", 1.2)
        params.step.print_speed = step_data.get("print_speed", 30.0)
        params.step.horizontal_offset = step_data.get("horizontal_offset", 0.0)

    # Prime tower 参数
    if "prime_tower" in data:
        prime_tower_data = data["prime_tower"]
        params.prime_tower.enabled = prime_tower_data.get("enabled", False)
        params.prime_tower.center_x = float(
            prime_tower_data.get("center_x", params.prime_tower.center_x)
        )
        params.prime_tower.center_y = float(
            prime_tower_data.get("center_y", params.prime_tower.center_y)
        )
        params.prime_tower.width = float(
            prime_tower_data.get("width", params.prime_tower.width)
        )
        params.prime_tower.depth = float(
            prime_tower_data.get("depth", params.prime_tower.depth)
        )
        params.prime_tower.infill_density_percent = int(
            prime_tower_data.get(
                "infill_density_percent",
                params.prime_tower.infill_density_percent,
            )
        )

    # Skirt 参数
    if "skirt" in data:
        skirt_data = data["skirt"]
        params.skirt.enabled = skirt_data.get("enabled", False)
        params.skirt.width = skirt_data.get("width", 5.0)
        params.skirt.height = skirt_data.get("height", 0.3)
        params.skirt.offset = skirt_data.get("offset", 0.0)
        params.skirt.interval = skirt_data.get("interval", 10.0)
        legacy_is_outer = skirt_data.get("is_outer", True)
        params.skirt.outer_enabled = skirt_data.get("outer_enabled", legacy_is_outer)
        params.skirt.inner_enabled = skirt_data.get("inner_enabled", not legacy_is_outer and "is_outer" in skirt_data)
        params.skirt.is_outer = legacy_is_outer
        params.skirt.extrusion_width = skirt_data.get("extrusion_width", 1.2)

    # Connected 参数
    if "connected" in data:
        conn_data = data["connected"]
        _reject_legacy_layer_key("connected", conn_data, "height", "height_layers")
        _reject_legacy_layer_key("connected", conn_data, "base_height", "base_height_layers")
        _reject_legacy_key("connected", conn_data, "bridge_width", "width")
        _reject_legacy_key("connected", conn_data, "bridge_height", "height_layers")
        params.connected.enabled = conn_data.get("enabled", False)
        params.connected.type = conn_data.get("type", "triangle")
        params.connected.width = conn_data.get("width", 15.0)
        if "height_layers" in conn_data:
            params.connected.height = _layers_to_height(
                conn_data["height_layers"],
                params.shell.layer_height,
            )
        if "base_height_layers" in conn_data:
            params.connected.base_height = _layers_to_height(
                conn_data["base_height_layers"],
                params.shell.layer_height,
            )
        params.connected.support_offset = conn_data.get("support_offset", 2.5)
        params.connected.auto_detect = conn_data.get("auto_detect", True)
        params.connected.bridge_width = params.connected.width
        params.connected.bridge_height = params.connected.height

    # EdgeWrap 参数
    if "edge_wrap" in data:
        wrap_data = data["edge_wrap"]
        params.edge_wrap.wrap_enabled = wrap_data.get("wrap_enabled", False)
        params.edge_wrap.wrap_width = wrap_data.get("wrap_width", 2.0)
        params.edge_wrap.wrap_height = wrap_data.get("wrap_height", 3.0)
        params.edge_wrap.wrap_direction = _deserialize_enum(
            EdgeDirection, wrap_data.get("wrap_direction", "INNER")
        )
        params.edge_wrap.outline_enabled = wrap_data.get("outline_enabled", False)
        params.edge_wrap.outline_width = wrap_data.get("outline_width", 1.0)
        params.edge_wrap.outline_height = wrap_data.get("outline_height", 1.0)
        params.edge_wrap.outline_offset = wrap_data.get("outline_offset", 0.0)
        params.edge_wrap.outline_direction = _deserialize_enum(
            EdgeDirection, wrap_data.get("outline_direction", "INNER")
        )

    # Panel 参数
    if "panel" in data:
        panel_data = data["panel"]
        params.panel.enabled = panel_data.get("enabled", False)
        params.panel.pattern_enabled = panel_data.get("pattern_enabled", False)
        if "fill_config" in panel_data:
            fc = panel_data["fill_config"]
            params.panel.fill_config.spacing = fc.get("spacing", 5.0)
            params.panel.fill_config.spacing2 = fc.get("spacing2", 3.0)
            params.panel.fill_config.angle = fc.get("angle", 45.0)
            params.panel.fill_config.boundary_distance = fc.get("boundary_distance", 1.0)

    # Baseplate 参数
    if "baseplate" in data:
        bp_data = data["baseplate"]
        params.baseplate.enabled = bp_data.get("enabled", False)
        params.baseplate.thickness = bp_data.get("thickness", 10.0)
        if "fill_config" in bp_data:
            fc = bp_data["fill_config"]
            params.baseplate.fill_config.spacing = fc.get("spacing", 5.0)
            params.baseplate.fill_config.spacing2 = fc.get("spacing2", 3.0)
            params.baseplate.fill_config.angle = fc.get("angle", 45.0)
            params.baseplate.fill_config.boundary_distance = fc.get("boundary_distance", 1.0)

    # Grid 参数
    if "grid" in data:
        grid_data = data["grid"]
        params.grid.enabled = grid_data.get("enabled", False)
        if "fill_config" in grid_data:
            fc = grid_data["fill_config"]
            params.grid.fill_config.spacing = fc.get("spacing", 5.0)
            params.grid.fill_config.spacing2 = fc.get("spacing2", 3.0)
            params.grid.fill_config.angle = fc.get("angle", 45.0)
            params.grid.fill_config.boundary_distance = fc.get("boundary_distance", 1.0)

    # BottomFace 参数
    if "bottom_face" in data:
        bf_data = data["bottom_face"]
        _reject_legacy_layer_key("bottom_face", bf_data, "thickness", "thickness_layers")
        params.bottom_face.enabled = bf_data.get("enabled", False)
        if "thickness_layers" in bf_data:
            params.bottom_face.thickness = _layers_to_height(
                bf_data["thickness_layers"],
                params.shell.layer_height,
            )

    # LightSlot 参数
    if "light_slot" in data:
        light_slot_data = data["light_slot"]
        _reject_legacy_layer_key("light_slot", light_slot_data, "depth", "depth_layers")
        params.light_slot.enabled = light_slot_data.get("enabled", False)
        params.light_slot.width = light_slot_data.get("width", 8.0)
        if "depth_layers" in light_slot_data:
            params.light_slot.depth = _layers_to_height(
                light_slot_data["depth_layers"],
                params.shell.layer_height,
            )
        params.light_slot.floor_layers = light_slot_data.get("floor_layers", 2)
        params.light_slot.wall_gap = light_slot_data.get("wall_gap", 0.0)
        params.light_slot.outer_enabled = light_slot_data.get("outer_enabled", True)
        params.light_slot.hole_enabled = light_slot_data.get("hole_enabled", True)
        params.light_slot.auto_skip_small_holes = light_slot_data.get("auto_skip_small_holes", True)
        params.light_slot.min_hole_span = light_slot_data.get("min_hole_span", 12.0)

    # TopFace 参数
    if "top_face" in data:
        tf_data = data["top_face"]
        _reject_legacy_layer_key("top_face", tf_data, "thickness", "thickness_layers")
        params.top_face.enabled = tf_data.get("enabled", False)
        if "thickness_layers" in tf_data:
            params.top_face.thickness = _layers_to_height(
                tf_data["thickness_layers"],
                params.shell.layer_height,
            )

    # Layout 参数
    if "layout" in data:
        layout_data = data["layout"]
        params.layout.auto_arrange = layout_data.get("auto_arrange", True)
        params.layout.spacing = layout_data.get("spacing", 10.0)
        params.layout.margin = layout_data.get("margin", 20.0)

    # Speed 参数
    if "speed" in data:
        speed_data = data["speed"]
        params.speed.print_speed = speed_data.get("print_speed", 50.0)
        params.speed.travel_speed = speed_data.get("travel_speed", 150.0)
        params.speed.first_layer_speed = speed_data.get("first_layer_speed", 20.0)
        params.speed.wall_speed = speed_data.get("wall_speed", 40.0)
        params.speed.fill_speed = speed_data.get("fill_speed", 60.0)

    # GCode 参数
    if "gcode" in data:
        gcode_data = data["gcode"]
        params.gcode.machine_type = gcode_data.get("machine_type", params.gcode.machine_type)
        params.gcode.first_layer_nozzle_temp = int(
            gcode_data.get(
                "first_layer_nozzle_temp",
                gcode_data.get("extruder1_temp", params.gcode.first_layer_nozzle_temp),
            )
        )
        params.gcode.other_layer_nozzle_temp = int(
            gcode_data.get(
                "other_layer_nozzle_temp",
                gcode_data.get("extruder1_temp", params.gcode.other_layer_nozzle_temp),
            )
        )
        params.gcode.first_layer_bed_temp = int(
            gcode_data.get(
                "first_layer_bed_temp",
                gcode_data.get("bed_temp", params.gcode.first_layer_bed_temp),
            )
        )
        params.gcode.other_layer_bed_temp = int(
            gcode_data.get(
                "other_layer_bed_temp",
                gcode_data.get("bed_temp", params.gcode.other_layer_bed_temp),
            )
        )
        params.gcode.first_layer_fan_percent = int(
            gcode_data.get(
                "first_layer_fan_percent",
                params.gcode.first_layer_fan_percent,
            )
        )
        params.gcode.other_layer_fan_percent = int(
            gcode_data.get(
                "other_layer_fan_percent",
                params.gcode.other_layer_fan_percent,
            )
        )
        params.gcode.retract_length = gcode_data.get("retract_length", 2.0)
        params.gcode.retract_speed = gcode_data.get("retract_speed", 40.0)
        params.gcode.color_change_retract = gcode_data.get("color_change_retract", 30.0)
        params.gcode.color_change_prime = gcode_data.get("color_change_prime", 35.0)
        params.gcode.z_hop_height1 = gcode_data.get("z_hop_height1", 0.5)
        params.gcode.z_hop_height2 = gcode_data.get("z_hop_height2", 5.0)
        params.gcode.distance_threshold = gcode_data.get("distance_threshold", 100.0)
        params.gcode.prime_length = gcode_data.get("prime_length", 5.0)
        params.gcode.filament_diameter = gcode_data.get("filament_diameter", 1.75)
        params.gcode.print_speed = gcode_data.get("print_speed", 50.0)
        params.gcode.travel_speed = gcode_data.get("travel_speed", 150.0)
        params.gcode.first_layer_speed = gcode_data.get("first_layer_speed", 20.0)
        params.gcode.end_z_position = gcode_data.get("end_z_position", 100.0)
        start_gcode = gcode_data.get("start_gcode", params.gcode.start_gcode)
        end_gcode = gcode_data.get("end_gcode", params.gcode.end_gcode)
        (
            params.gcode.start_gcode,
            params.gcode.end_gcode,
        ) = normalize_default_gcode_scripts(start_gcode, end_gcode)
        params.gcode.color_change_command_template = gcode_data.get(
            "color_change_command_template",
            params.gcode.color_change_command_template,
        )

    # Machine 参数
    if "machine" in data:
        machine_data = data["machine"]
        params.machine.name = machine_data.get("name", "MINGDA")
        params.machine.bed_width = machine_data.get("bed_width", 800.0)
        params.machine.bed_depth = machine_data.get("bed_depth", 1200.0)
        params.machine.bed_height = machine_data.get("bed_height", 100.0)
        params.machine.nozzle_diameter = machine_data.get("nozzle_diameter", 0.8)
        params.machine.extruder_count = machine_data.get("extruder_count", 2)

    return params
