"""
防翘裙边生成器模块

生成V型防翘裙边，防止打印过程中字壳翘曲。
"""

import math
from typing import List, Optional, Tuple
from src.core.types import (
    Contour, SkirtParams, LayerPath, PathRole,
    ExtruderType, Point, Path
)


class SkirtGenerator:
    """防翘裙边生成器"""

    def generate_skirt(self, contour: Contour,
                       params: SkirtParams) -> List[LayerPath]:
        """
        生成防翘裙边

        裙边结构：
        - V型开口，贴近字壳底部
        - 间隔分布在轮廓周围

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

    def _generate_outer_skirt(self, outer_path: Path,
                              params: SkirtParams) -> List[LayerPath]:
        """
        生成外部防翘裙边
        """
        paths = []

        # 沿路径分布裙边位置
        positions = self._distribute_along_path(outer_path, params.length)

        for start_pos, direction in positions:
            # 生成V型裙边
            v_points = self._generate_v_shape(
                start_pos, direction, params, is_outer=True
            )

            if v_points:
                layer_path = LayerPath(
                    points=v_points,
                    role=PathRole.SKIRT,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=params.extrusion_width,
                    is_closed=False
                )
                paths.append(layer_path)

        return paths

    def _generate_inner_skirt(self, hole_path: Path,
                              params: SkirtParams) -> List[LayerPath]:
        """
        生成内部防翘裙边
        """
        paths = []

        # 沿路径分布裙边位置
        positions = self._distribute_along_path(hole_path, params.length)

        for start_pos, direction in positions:
            # 生成V型裙边（方向相反）
            v_points = self._generate_v_shape(
                start_pos, direction, params, is_outer=False
            )

            if v_points:
                layer_path = LayerPath(
                    points=v_points,
                    role=PathRole.SKIRT,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=params.extrusion_width,
                    is_closed=False
                )
                paths.append(layer_path)

        return paths

    def _generate_v_shape(self, start: Point, direction: Tuple[float, float],
                          params: SkirtParams, is_outer: bool) -> List[Point]:
        """
        生成单个V型裙边的点序列

        Args:
            start: 起始点
            direction: 方向向量（单位向量）
            params: 裙边参数
            is_outer: 是否外部裙边

        Returns:
            V型裙边的点列表
        """
        dx, dy = direction

        # 法线方向（垂直于路径方向）
        if is_outer:
            # 外部裙边：法线朝外
            nx, ny = -dy, dx
        else:
            # 内部裙边：法线朝内
            nx, ny = dy, -dx

        # V型参数
        width = params.width
        v_opening = params.v_opening
        line_width = params.line_width

        # 计算V型的三个关键点
        # 起点（贴近字壳）
        p1 = Point(
            start.x + nx * line_width,
            start.y + ny * line_width
        )

        # V型顶点（最外点）
        p2 = Point(
            start.x + nx * (line_width + width),
            start.y + ny * (line_width + width)
        )

        # V型开口点
        half_opening = v_opening / 2
        p1_left = Point(
            p1.x - dx * half_opening,
            p1.y - dy * half_opening
        )
        p1_right = Point(
            p1.x + dx * half_opening,
            p1.y + dy * half_opening
        )

        return [p1_left, p2, p1_right]

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
