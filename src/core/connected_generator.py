"""
连襟生成器模块

生成连襟字结构，自动检测并连接相邻字形。

连襟（Connected Letters）是将多个离散的字形轮廓连接成一体的结构，
用于3D打印时保持多个字符的相对位置。

支持两种连襟类型：
- 三角形连襟：顶部斜边收窄，底部较宽，适合常规使用
- 菱形连襟：双向斜边，中间最窄，适合双面发光字

算法说明：
使用最小生成树（MST）算法确保N个轮廓有N-1个连接桥，
形成一个完全连通的整体。
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple
from src.core.types import (
    Contour, ConnectedParams, LayerPath, PathRole,
    ExtruderType, Point, Path, PathType
)
from src.core.path_offset import PathOffset


@dataclass
class ConnectionBridge:
    """连接桥数据结构"""
    contour_a_index: int      # 第一个轮廓索引
    contour_b_index: int      # 第二个轮廓索引
    point_a: Point            # 轮廓A上的连接点
    point_b: Point            # 轮廓B上的连接点
    distance: float           # 连接距离
    # 桥梁的四个角点（用于3D生成）
    corners: List[Point] = None  # [左上, 右上, 右下, 左下]


class UnionFind:
    """并查集，用于Kruskal最小生成树算法"""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        """合并两个集合，返回是否成功（不在同一集合时才成功）"""
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True


class ConnectedGenerator:
    """连襟字生成器

    功能：
    1. 自动检测相邻轮廓之间的最近点
    2. 使用最小生成树算法确保所有轮廓连通（N个轮廓有N-1个连接桥）
    3. 根据z高度计算连襟的宽度变化
    """

    def __init__(self, path_offset: Optional[PathOffset] = None):
        self.path_offset = path_offset or PathOffset()

    def find_connection_bridges(self, contours: List[Contour],
                                 params: ConnectedParams) -> List[ConnectionBridge]:
        """
        使用最小生成树算法查找连接桥

        算法（Kruskal MST）：
        1. 计算所有轮廓对之间的最近距离
        2. 按距离排序
        3. 使用并查集，依次添加边直到所有轮廓连通
        4. 结果是N-1条边（连接桥），确保所有轮廓形成一个连通整体

        Args:
            contours: 轮廓列表
            params: 连襟参数

        Returns:
            连接桥列表（正好N-1个，确保所有轮廓连通）
        """
        n = len(contours)

        if n < 2:
            return []

        # 计算所有轮廓对之间的最近点和距离
        edges = []  # (distance, i, j, point_a, point_b)

        for i in range(n):
            for j in range(i + 1, n):
                result = self._find_closest_points(contours[i], contours[j])
                if result is not None:
                    dist, point_a, point_b = result
                    # 只添加距离在max_gap范围内的边
                    if dist <= params.max_gap:
                        edges.append((dist, i, j, point_a, point_b))

        # 按距离排序
        edges.sort(key=lambda x: x[0])

        # Kruskal算法：使用并查集构建最小生成树
        uf = UnionFind(n)
        bridges = []

        for dist, i, j, point_a, point_b in edges:
            # 尝试合并两个集合
            if uf.union(i, j):
                # 计算连接桥的四个角点
                corners = self._calculate_bridge_corners(point_a, point_b, params.width)

                bridge = ConnectionBridge(
                    contour_a_index=i,
                    contour_b_index=j,
                    point_a=point_a,
                    point_b=point_b,
                    distance=dist,
                    corners=corners
                )
                bridges.append(bridge)

                # 已经有N-1条边，所有轮廓已连通
                if len(bridges) >= n - 1:
                    break

        return bridges

    def _find_closest_points(self, contour_a: Contour,
                              contour_b: Contour) -> Optional[Tuple[float, Point, Point]]:
        """
        查找两个轮廓之间的最近点对

        Args:
            contour_a: 第一个轮廓
            contour_b: 第二个轮廓

        Returns:
            (距离, 点A, 点B) 或 None
        """
        points_a = contour_a.outer.points
        points_b = contour_b.outer.points

        if not points_a or not points_b:
            return None

        min_dist = float('inf')
        best_pair = None

        # 暴力搜索最近点对
        for pa in points_a:
            for pb in points_b:
                dist = math.sqrt((pa.x - pb.x) ** 2 + (pa.y - pb.y) ** 2)
                if dist < min_dist:
                    min_dist = dist
                    best_pair = (pa, pb)

        if best_pair is None:
            return None

        return (min_dist, best_pair[0], best_pair[1])

    def _calculate_bridge_corners(self, point_a: Point, point_b: Point,
                                   width: float) -> List[Point]:
        """
        计算连接桥的四个角点

        桥梁是一个矩形，沿着两个连接点之间的方向延伸，
        垂直方向上有width的宽度。

        Args:
            point_a: 起点
            point_b: 终点
            width: 桥宽度

        Returns:
            [左上(A侧), 右上(A侧), 右下(B侧), 左下(B侧)]
        """
        # 计算方向向量
        dx = point_b.x - point_a.x
        dy = point_b.y - point_a.y
        length = math.sqrt(dx * dx + dy * dy)

        if length < 0.001:
            # 两点重合，无法创建桥
            return []

        # 归一化
        dx /= length
        dy /= length

        # 垂直方向（法线）
        nx = -dy
        ny = dx

        half_width = width / 2

        # 四个角点
        corners = [
            # A侧两个角
            Point(point_a.x + nx * half_width, point_a.y + ny * half_width),
            Point(point_a.x - nx * half_width, point_a.y - ny * half_width),
            # B侧两个角
            Point(point_b.x - nx * half_width, point_b.y - ny * half_width),
            Point(point_b.x + nx * half_width, point_b.y + ny * half_width),
        ]

        return corners

    def generate_connected_layer(self, bridges: List[ConnectionBridge],
                                  z: float, params: ConnectedParams) -> List[LayerPath]:
        """
        为指定高度生成连襟层路径

        根据z高度计算当前层的连襟宽度，生成相应的路径。

        Args:
            bridges: 连接桥列表
            z: 当前层高度
            params: 连襟参数

        Returns:
            该层的连襟路径列表
        """
        paths = []

        if not params.enabled:
            return paths

        total_height = params.base_height + params.height

        for bridge in bridges:
            if not bridge.corners:
                continue

            # 计算当前高度的宽度
            current_width = self._calculate_width_at_z(z, params)

            if current_width < 0.1:
                continue

            # 根据当前宽度缩放角点
            scaled_corners = self._scale_bridge_corners(
                bridge.point_a, bridge.point_b, current_width
            )

            if len(scaled_corners) < 4:
                continue

            # 创建闭合路径
            layer_path = LayerPath(
                points=scaled_corners,
                role=PathRole.CONNECTED,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=params.width,
                is_closed=True
            )
            paths.append(layer_path)

        return paths

    def _calculate_width_at_z(self, z: float, params: ConnectedParams) -> float:
        """
        计算指定高度的连襟宽度

        三角形连襟：底座保持宽度，斜边线性收窄
        菱形连襟：中间最窄，两端较宽

        Args:
            z: 当前高度
            params: 连襟参数

        Returns:
            当前高度的宽度
        """
        base_height = params.base_height
        bevel_height = params.height
        total_height = base_height + bevel_height
        width = params.width

        if params.type == "triangle":
            # 三角形连襟
            if z < base_height:
                # 底座区域：保持原始宽度
                return width
            elif z < total_height:
                # 斜边区域：线性收窄到0
                progress = (z - base_height) / bevel_height
                return width * (1 - progress)
            else:
                return 0.0

        else:  # diamond
            # 菱形连襟：中间最窄
            if params.type == "diamond":
                total_height = base_height + bevel_height * 2
                mid_height = total_height / 2

                if z < mid_height:
                    # 下半部分：逐渐收窄到50%
                    progress = z / mid_height
                    return width * (1 - progress * 0.5)
                else:
                    # 上半部分：逐渐展宽回100%
                    progress = (z - mid_height) / mid_height
                    return width * (0.5 + progress * 0.5)

        return width

    def _scale_bridge_corners(self, point_a: Point, point_b: Point,
                               width: float) -> List[Point]:
        """
        根据指定宽度重新计算桥角点

        Args:
            point_a: 起点
            point_b: 终点
            width: 桥宽度

        Returns:
            缩放后的角点列表
        """
        return self._calculate_bridge_corners(point_a, point_b, width)

    def generate_connected(self, contours: List[Contour], z: float,
                           params: ConnectedParams) -> List[LayerPath]:
        """
        生成连襟结构（主入口函数）

        自动检测相邻轮廓并生成连接。

        Args:
            contours: 轮廓列表
            z: 当前层高度
            params: 连襟参数

        Returns:
            连襟路径列表
        """
        if not params.enabled:
            return []

        # 首先检查是否有预定义的连襟框（从DXF读取）
        if params.auto_detect:
            # 自动检测连接点
            bridges = self.find_connection_bridges(contours, params)
            return self.generate_connected_layer(bridges, z, params)
        else:
            # 使用预定义的连襟框
            return self._generate_from_frames(contours, z, params)

    def _generate_from_frames(self, contours: List[Contour], z: float,
                               params: ConnectedParams) -> List[LayerPath]:
        """
        从预定义的连襟框生成连襟路径

        连襟框是DXF文件中青色标记的闭合路径。

        Args:
            contours: 轮廓列表
            z: 当前层高度
            params: 连襟参数

        Returns:
            连襟路径列表
        """
        paths = []

        # 查找所有连襟框
        connected_frames = self._find_connected_frames(contours)

        for frame in connected_frames:
            current_width = self._calculate_width_at_z(z, params)

            if current_width < 0.1:
                continue

            # 对框进行偏移得到壁路径
            offset_distance = -params.support_offset
            offset_paths = self.path_offset.offset(frame, offset_distance)

            if offset_paths:
                points = offset_paths[0].points
            else:
                points = frame.points

            layer_path = LayerPath(
                points=points,
                role=PathRole.CONNECTED,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=current_width,
                is_closed=True
            )
            paths.append(layer_path)

        return paths

    def _find_connected_frames(self, contours: List[Contour]) -> List[Path]:
        """
        查找连襟框（青色路径）

        从所有轮廓中提取连襟框
        """
        frames = []
        for contour in contours:
            for frame in contour.connected_frames:
                frames.append(frame)
        return frames

    def get_total_height(self, params: ConnectedParams) -> float:
        """
        获取连襟的总高度

        Args:
            params: 连襟参数

        Returns:
            连襟总高度
        """
        if params.type == "diamond":
            return params.base_height + params.height * 2
        else:
            return params.base_height + params.height

    def calculate_connected_bounds(self, bridge: ConnectionBridge,
                                   params: ConnectedParams) -> Tuple[float, float, float, float]:
        """
        计算连接桥区域边界

        Returns:
            (min_x, min_y, max_x, max_y)
        """
        if not bridge.corners:
            return (
                min(bridge.point_a.x, bridge.point_b.x),
                min(bridge.point_a.y, bridge.point_b.y),
                max(bridge.point_a.x, bridge.point_b.x),
                max(bridge.point_a.y, bridge.point_b.y)
            )

        xs = [p.x for p in bridge.corners]
        ys = [p.y for p in bridge.corners]
        return (min(xs), min(ys), max(xs), max(ys))
