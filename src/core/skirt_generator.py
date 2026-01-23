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
from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.core.types import (
    Contour, SkirtParams, LayerPath, PathRole,
    ExtruderType, Point, Path
)


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
            is_outer: 是否外部轮廓

        Returns:
            梯形列表
        """
        trapezoids = []
        points = path.points
        n = len(points)

        if n < 2:
            return trapezoids

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
        num_trapezoids = max(1, int(total_length / params.interval))
        actual_interval = total_length / num_trapezoids

        # 裙边参数
        skirt_width = params.width
        skirt_offset = params.offset

        # 生成梯形顶点位置
        # 梯形的顶边端点位于 distance = i * interval 和 (i+1) * interval 处
        for i in range(num_trapezoids):
            # 梯形顶边的两个端点位置（沿路径的距离）
            dist_left = i * actual_interval
            dist_right = ((i + 1) * actual_interval) % total_length

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
            # 外部裙边：法线朝外（从路径向外延伸）
            # 内部裙边（孔）：法线朝内（向孔中心延伸）
            # 注意：内孔路径方向可能与外轮廓相同（都是逆时针），
            # 所以需要反转法线方向让裙边向孔内延伸
            if is_outer:
                # 外轮廓：法线朝外
                normal_left = self._get_outward_normal(dir_left)
                normal_right = self._get_outward_normal(dir_right)
            else:
                # 内孔：法线朝外的反方向（向孔中心）
                out_left = self._get_outward_normal(dir_left)
                out_right = self._get_outward_normal(dir_right)
                normal_left = (-out_left[0], -out_left[1])
                normal_right = (-out_right[0], -out_right[1])

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
