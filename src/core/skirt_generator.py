"""
防翘裙边生成器模块

生成连续梯形防翘裙边，防止打印过程中字壳翘曲。

裙边结构（截面图）：
  字壳 ════════════════════════════════════════════
       ╲          ╱╲          ╱╲          ╱
        ╲        ╱  ╲        ╱  ╲        ╱
         ╲      ╱    ╲      ╱    ╲      ╱
          ╲    ╱      ╲    ╱      ╲    ╱
           ────        ────        ────

相邻梯形共享斜边，形成连续的波浪形防翘结构。
"""

import math
from typing import List, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass

from src.core.types import (
    Contour, SkirtParams, LayerPath, PathRole,
    ExtruderType, Point, Path
)

if TYPE_CHECKING:
    from src.core.path_offset import PathOffset


@dataclass
class TrapezoidSkirt:
    """单个梯形裙边的顶点数据"""
    # 顶边两个点（贴着字壳）
    top_left: Point
    top_right: Point
    # 底边两个点
    bottom_left: Point
    bottom_right: Point


class SkirtGenerator:
    """防翘裙边生成器"""

    def generate_skirt(self, contour: Contour,
                       params: SkirtParams) -> List[LayerPath]:
        """
        生成防翘裙边

        裙边结构：
        - 连续梯形，相邻梯形共享斜边
        - 贴近字壳底部

        Args:
            contour: 字形轮廓
            params: 裙边参数

        Returns:
            裙边路径列表
        """
        paths = []

        if not params.enabled:
            return paths

        # 确定裙边位置（外部或内部）
        if params.is_outer:
            # 外防翘：在外轮廓外部
            skirt_paths = self._generate_outer_skirt(contour.outer, params)
        else:
            # 内防翘：在内孔内部
            for hole in contour.holes:
                skirt_paths = self._generate_inner_skirt(hole, params)
                paths.extend(skirt_paths)
            return paths

        paths.extend(skirt_paths)
        return paths

    def generate_skirt_3d(self, contour: Contour,
                          params: SkirtParams) -> List[TrapezoidSkirt]:
        """
        生成3D梯形裙边数据（用于STL导出）

        Args:
            contour: 字形轮廓
            params: 裙边参数

        Returns:
            梯形裙边列表
        """
        trapezoids = []

        if not params.enabled:
            return trapezoids

        # 始终处理 contour.outer，方向由 is_outer 参数决定
        # is_outer=True: 裙边向外延伸（用于外轮廓）
        # is_outer=False: 裙边向内延伸（用于内孔）
        trapezoids = self._generate_trapezoids_along_path(
            contour.outer, params, is_outer=params.is_outer
        )

        return trapezoids

    def _generate_outer_skirt(self, outer_path: Path,
                              params: SkirtParams) -> List[LayerPath]:
        """
        生成外部防翘裙边的打印路径（G-code用）
        """
        paths = []
        trapezoids = self._generate_trapezoids_along_path(
            outer_path, params, is_outer=True
        )

        # 将梯形转换为打印路径
        # 每个梯形生成一个闭合路径
        for trap in trapezoids:
            points = [
                trap.top_left,
                trap.bottom_left,
                trap.bottom_right,
                trap.top_right
            ]
            layer_path = LayerPath(
                points=points,
                role=PathRole.SKIRT,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=params.extrusion_width,
                is_closed=True
            )
            paths.append(layer_path)

        return paths

    def generate_skirt_clipped(
        self,
        contour: Contour,
        all_contours: List[Contour],
        params: SkirtParams,
        wall_thickness: float,
        path_offset: 'PathOffset'
    ) -> List[LayerPath]:
        """
        生成经过裁剪的防翘裙边（不��犯壁区域）

        算法步骤：
        1. 收集所有轮廓的壁区域作为禁区
        2. 生成原始梯形裙边
        3. 将每个梯形与允许区域做布尔交集，裁剪掉侵入壁的部分

        Args:
            contour: 当前轮廓
            all_contours: 所有轮廓（用于计算禁区）
            params: 裙边参数
            wall_thickness: 壁厚
            path_offset: 路径偏移工具

        Returns:
            裁剪后的裙边路径列表
        """
        if not params.enabled:
            return []

        # Step 1: 构建禁区（排除当前轮廓自身，只包含其他轮廓的壁区域）
        forbidden_zones = self._build_forbidden_zones(
            all_contours, wall_thickness, path_offset,
            exclude_contour=contour, skirt_params=params
        )

        # Step 2: 生成原始梯形
        if params.is_outer:
            raw_trapezoids = self._generate_trapezoids_along_path(
                contour.outer, params, is_outer=True
            )
        else:
            raw_trapezoids = []
            for hole in contour.holes:
                raw_trapezoids.extend(
                    self._generate_trapezoids_along_path(
                        hole, params, is_outer=False
                    )
                )

        if not raw_trapezoids or not forbidden_zones:
            # 没有禁区，直接返回未裁剪的路径
            return self._trapezoids_to_layer_paths(raw_trapezoids, params)

        # Step 3: 裁剪每个梯形
        clipped_paths = []
        for trap in raw_trapezoids:
            trap_path = Path(
                points=[
                    trap.top_left,
                    trap.bottom_left,
                    trap.bottom_right,
                    trap.top_right
                ],
                is_closed=True
            )

            # 从梯形中减去所有禁区
            remaining = path_offset.boolean_difference_multi(
                [trap_path], forbidden_zones
            )

            for clipped in remaining:
                if len(clipped.points) >= 3:
                    layer_path = LayerPath(
                        points=clipped.points,
                        role=PathRole.SKIRT,
                        extruder=ExtruderType.EXTRUDER_1,
                        line_width=params.extrusion_width,
                        is_closed=True
                    )
                    clipped_paths.append(layer_path)

        return clipped_paths

    def generate_skirt_3d_clipped(
        self,
        contour: Contour,
        all_contours: List[Contour],
        params: SkirtParams,
        wall_thickness: float,
        path_offset: 'PathOffset'
    ) -> List[TrapezoidSkirt]:
        """
        生成经过裁剪的3D梯形裙边（用于STL导出）

        与 generate_skirt_clipped 类似，但返回 TrapezoidSkirt 数据。
        对于被裁剪的梯形，跳过整个梯形（因为裁剪后不再是梯形）。

        简化策略：检测梯形是否与禁区重叠，如果重叠则丢弃该梯形。

        Args:
            contour: 当前轮廓
            all_contours: 所有轮廓
            params: 裙边参数
            wall_thickness: 壁厚
            path_offset: 路径偏移工具

        Returns:
            未被裁剪的梯形列表
        """
        if not params.enabled:
            return []

        # 构建禁区（排除当前轮廓自身）
        forbidden_zones = self._build_forbidden_zones(
            all_contours, wall_thickness, path_offset,
            exclude_contour=contour, skirt_params=params
        )

        # 生成原始梯形
        raw_trapezoids = self._generate_trapezoids_along_path(
            contour.outer, params, is_outer=params.is_outer
        )

        if not forbidden_zones:
            return raw_trapezoids

        # 过滤掉与禁区重叠的梯形
        valid_trapezoids = []
        for trap in raw_trapezoids:
            if not self._trapezoid_overlaps_forbidden(trap, forbidden_zones):
                valid_trapezoids.append(trap)

        return valid_trapezoids

    def _point_in_polygon(self, point: Point, polygon: List[Point]) -> bool:
        """
        判断点是否在多边形内部（射线法）

        Args:
            point: 测试点
            polygon: 多边形顶点列表

        Returns:
            True if point is inside polygon
        """
        x, y = point.x, point.y
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0].x, polygon[0].y
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _trapezoid_overlaps_forbidden(
        self,
        trap: TrapezoidSkirt,
        forbidden_zones: List[Path]
    ) -> bool:
        """检查梯形底边中点是否在禁区内（底边是远离字壳的边）"""
        if not forbidden_zones:
            return False

        # 只检测底边中点（远离字壳的边）
        bottom_mid = Point(
            (trap.bottom_left.x + trap.bottom_right.x) / 2,
            (trap.bottom_left.y + trap.bottom_right.y) / 2
        )

        for zone in forbidden_zones:
            if self._point_in_polygon(bottom_mid, zone.points):
                return True

        return False

    def _build_forbidden_zones(
        self,
        all_contours: List[Contour],
        wall_thickness: float,
        path_offset: 'PathOffset',
        exclude_contour: Optional[Contour] = None,
        skirt_params: Optional[SkirtParams] = None
    ) -> List[Path]:
        """
        构建其他轮廓的壁区域作为禁区

        禁区包括：
        - 其他轮廓的外轮廓（防止裙边进入其他字母内部）
        - 所有轮廓的内孔扩展 wall_thickness（防止进入内孔壁区域）

        Args:
            all_contours: 所有轮廓
            wall_thickness: 壁厚
            path_offset: 路径偏移工具
            exclude_contour: 当前正在生成裙边的轮廓（排除其外轮廓）
            skirt_params: 裙边参数（未使用，保留兼容性）

        Returns:
            禁区路径列表
        """
        from src.core.path_offset import JoinType

        forbidden = []

        for contour in all_contours:
            is_current = (exclude_contour is not None and contour is exclude_contour)

            # 其他轮廓的外轮廓直接作为禁区
            if not is_current and len(contour.outer.points) >= 3:
                forbidden.append(contour.outer)

            # 所有轮廓的内孔扩展 wall_thickness
            for hole in contour.holes:
                if len(hole.points) >= 3:
                    expanded_holes = path_offset.offset(
                        hole, wall_thickness, JoinType.ROUND
                    )
                    forbidden.extend(expanded_holes)

        return forbidden

    def _trapezoids_to_layer_paths(
        self,
        trapezoids: List[TrapezoidSkirt],
        params: SkirtParams
    ) -> List[LayerPath]:
        """将梯形列表转换为打印路径列表"""
        paths = []
        for trap in trapezoids:
            points = [
                trap.top_left,
                trap.bottom_left,
                trap.bottom_right,
                trap.top_right
            ]
            layer_path = LayerPath(
                points=points,
                role=PathRole.SKIRT,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=params.extrusion_width,
                is_closed=True
            )
            paths.append(layer_path)
        return paths

    def _generate_inner_skirt(self, hole_path: Path,
                              params: SkirtParams) -> List[LayerPath]:
        """
        生成内部防翘裙边
        """
        paths = []
        trapezoids = self._generate_trapezoids_along_path(
            hole_path, params, is_outer=False
        )

        for trap in trapezoids:
            points = [
                trap.top_left,
                trap.bottom_left,
                trap.bottom_right,
                trap.top_right
            ]
            layer_path = LayerPath(
                points=points,
                role=PathRole.SKIRT,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=params.extrusion_width,
                is_closed=True
            )
            paths.append(layer_path)

        return paths

    def _calculate_signed_area(self, points: List[Point]) -> float:
        """
        计算路径的有向面积

        返回值:
            > 0: 逆时针 (CCW)
            < 0: 顺时针 (CW)
        """
        area = 0.0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y
        return area / 2.0

    def _generate_trapezoids_along_path(self, path: Path,
                                         params: SkirtParams,
                                         is_outer: bool) -> List[TrapezoidSkirt]:
        """
        沿路径生成连续的梯形裙边

        梯形结构：
        - 顶边贴着字壳（路径偏移offset距离处）
        - 底边向外延伸width距离
        - 相邻梯形共享斜边

        Args:
            path: 轮廓路径
            params: 裙边参数
            is_outer: 是否外部轮廓（语义上的，裙边应该向哪个方向延伸）

        Returns:
            梯形列表
        """
        trapezoids = []
        points = path.points
        n = len(points)

        if n < 2:
            return trapezoids

        # 检测路径的实际绕向
        signed_area = self._calculate_signed_area(points)
        is_ccw = signed_area > 0  # 有向面积 > 0 表示逆时针

        # 计算路径总长度和每段的累积长度
        segment_lengths = []
        cumulative_lengths = [0.0]
        total_length = 0.0

        for i in range(n):
            j = (i + 1) % n
            dx = points[j].x - points[i].x
            dy = points[j].y - points[i].y
            length = math.sqrt(dx * dx + dy * dy)
            segment_lengths.append(length)
            total_length += length
            cumulative_lengths.append(total_length)

        if total_length < params.interval:
            return trapezoids

        # 计算梯形数量
        num_trapezoids = max(1, int(math.ceil(total_length / params.interval)))
        actual_interval = total_length / num_trapezoids

        # 裙边参数
        skirt_width = params.width
        skirt_offset = params.offset

        # 生成梯形顶点位置
        # 梯形的顶边端点位于 distance = i * interval 和 (i+1) * interval 处
        for i in range(num_trapezoids):
            # 梯形顶边的两个端点位置（沿路径的距离）
            dist_left = i * actual_interval
            dist_right = min((i + 1) * actual_interval, total_length)

            # 获取两个端点的位置和方向
            pos_left, dir_left = self._get_point_and_direction_at_distance(
                points, segment_lengths, cumulative_lengths, dist_left
            )
            pos_right, dir_right = self._get_point_and_direction_at_distance(
                points, segment_lengths, cumulative_lengths, dist_right
            )

            if pos_left is None or pos_right is None:
                continue

            # 计算法线方向
            # 根据路径的实际绕向和语义方向（is_outer）来确定法线
            #
            # 语义方向：
            # - is_outer=True: 外轮廓，裙边应该向外延伸
            # - is_outer=False: 内孔，裙边应该向孔内延伸
            #
            # 绕向影响：
            # - CCW路径：outward法线 = (dy, -dx)
            # - CW路径：outward法线 = (-dy, dx)（与CCW相反）
            #
            # 组合逻辑：
            # - CCW + is_outer → 使用 outward 法线
            # - CCW + !is_outer → 使用 inward 法线
            # - CW + is_outer → 使用 inward 法线（因为CW翻转了方向）
            # - CW + !is_outer → 使用 outward 法线
            #
            # 简化：如果 is_ccw == is_outer，使用 outward；否则使用 inward
            if is_ccw == is_outer:
                normal_left = self._get_outward_normal(dir_left)
                normal_right = self._get_outward_normal(dir_right)
            else:
                normal_left = self._get_inward_normal(dir_left)
                normal_right = self._get_inward_normal(dir_right)

            # 计算梯形顶边（贴着字壳，考虑offset）
            top_left = Point(
                pos_left[0] + normal_left[0] * skirt_offset,
                pos_left[1] + normal_left[1] * skirt_offset
            )
            top_right = Point(
                pos_right[0] + normal_right[0] * skirt_offset,
                pos_right[1] + normal_right[1] * skirt_offset
            )

            # 计算梯形底边（向外延伸width距离）
            # 底边中点在顶边中点的法线方向上，距离为width
            # 底边宽度小于顶边宽度（形成梯形）

            # 计算顶边中点
            top_mid_x = (top_left.x + top_right.x) / 2
            top_mid_y = (top_left.y + top_right.y) / 2

            # 计算顶边中点的平均法线
            avg_normal_x = (normal_left[0] + normal_right[0]) / 2
            avg_normal_y = (normal_left[1] + normal_right[1]) / 2
            avg_normal_len = math.sqrt(avg_normal_x**2 + avg_normal_y**2)
            if avg_normal_len > 0:
                avg_normal_x /= avg_normal_len
                avg_normal_y /= avg_normal_len

            # 底边中点
            bottom_mid_x = top_mid_x + avg_normal_x * skirt_width
            bottom_mid_y = top_mid_y + avg_normal_y * skirt_width

            # 顶边方向（从左到右）
            top_dir_x = top_right.x - top_left.x
            top_dir_y = top_right.y - top_left.y
            top_length = math.sqrt(top_dir_x**2 + top_dir_y**2)

            if top_length < 0.001:
                continue

            # 归一化
            top_dir_x /= top_length
            top_dir_y /= top_length

            # 底边宽度为顶边宽度的一半（梯形收缩）
            bottom_half_width = top_length / 4

            # 计算底边两个端点
            bottom_left = Point(
                bottom_mid_x - top_dir_x * bottom_half_width,
                bottom_mid_y - top_dir_y * bottom_half_width
            )
            bottom_right = Point(
                bottom_mid_x + top_dir_x * bottom_half_width,
                bottom_mid_y + top_dir_y * bottom_half_width
            )

            trapezoid = TrapezoidSkirt(
                top_left=top_left,
                top_right=top_right,
                bottom_left=bottom_left,
                bottom_right=bottom_right
            )
            trapezoids.append(trapezoid)

        return trapezoids

    def _get_point_and_direction_at_distance(
            self,
            points: List[Point],
            segment_lengths: List[float],
            cumulative_lengths: List[float],
            distance: float
    ) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """
        获取路径上指定距离处的点和方向

        Args:
            points: 路径点
            segment_lengths: 每段长度
            cumulative_lengths: 累积长度
            distance: 沿路径的距离

        Returns:
            (位置, 方向) 元组
        """
        n = len(points)
        total_length = cumulative_lengths[-1]

        # 处理距离超出范围的情况
        distance = distance % total_length

        # 找到对应的线段
        for i in range(n):
            if cumulative_lengths[i] <= distance <= cumulative_lengths[i + 1]:
                # 在第i段
                seg_len = segment_lengths[i]
                if seg_len < 0.001:
                    continue

                # 在线段内的位置
                t = (distance - cumulative_lengths[i]) / seg_len

                j = (i + 1) % n
                # 插值位置
                x = points[i].x + t * (points[j].x - points[i].x)
                y = points[i].y + t * (points[j].y - points[i].y)

                # 方向（线段方向）
                dx = points[j].x - points[i].x
                dy = points[j].y - points[i].y
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    dx /= length
                    dy /= length

                return (x, y), (dx, dy)

        return None, None

    def _get_outward_normal(self, direction: Tuple[float, float]) -> Tuple[float, float]:
        """
        获取朝外的法线（假设路径是逆时针方向）

        对于逆时针路径，朝外的法线 = (dy, -dx)
        例如：方向(1,0)向右 -> 法线(0,-1)向下（朝外）
        """
        dx, dy = direction
        return (dy, -dx)

    def _get_inward_normal(self, direction: Tuple[float, float]) -> Tuple[float, float]:
        """
        获取朝内的法线

        与朝外相反
        """
        dx, dy = direction
        return (-dy, dx)

    def _distribute_along_path(self, path: Path,
                               interval: float) -> List[Tuple[Point, Tuple[float, float]]]:
        """
        沿路径分布裙边位置

        Args:
            path: 轮廓路径
            interval: 裙边间距

        Returns:
            [(位置点, 方向向量), ...] 列表
        """
        positions = []
        points = path.points
        n = len(points)

        if n < 2:
            return positions

        # 计算路径总长度
        total_length = 0
        segment_lengths = []
        for i in range(n):
            j = (i + 1) % n
            length = math.sqrt(
                (points[j].x - points[i].x) ** 2 +
                (points[j].y - points[i].y) ** 2
            )
            segment_lengths.append(length)
            total_length += length

        # 沿路径分布点
        current_distance = interval / 2  # 从半个间距开始
        current_segment = 0
        distance_in_segment = 0

        while current_distance < total_length:
            # 找到当前距离所在的线段
            while (current_segment < n and
                   distance_in_segment + segment_lengths[current_segment] < current_distance):
                distance_in_segment += segment_lengths[current_segment]
                current_segment += 1

            if current_segment >= n:
                break

            # 在当前线段上插值
            i = current_segment
            j = (i + 1) % n
            segment_length = segment_lengths[i]

            if segment_length > 0:
                t = (current_distance - distance_in_segment) / segment_length
                pos = Point(
                    points[i].x + t * (points[j].x - points[i].x),
                    points[i].y + t * (points[j].y - points[i].y)
                )

                # 计算方向向量
                dx = points[j].x - points[i].x
                dy = points[j].y - points[i].y
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    direction = (dx / length, dy / length)
                    positions.append((pos, direction))

            current_distance += interval

        return positions
