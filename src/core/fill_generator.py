"""
填充生成器模块

生成各类填充图案：面板填充、网格填充、底板填充。
"""

import math
from typing import List, Optional, Tuple
from src.core.types import (
    Contour, PanelParams, GridParams, BaseplateParams,
    LayerPath, PathRole, ExtruderType, Point, Path, FillConfig
)
from src.core.path_offset import PathOffset


class FillGenerator:
    """填充图案生成器"""

    def __init__(self, path_offset: Optional[PathOffset] = None):
        self.path_offset = path_offset or PathOffset()

    def generate_panel_fill(self, contour: Contour,
                            params: PanelParams) -> List[LayerPath]:
        """
        生成面板填充

        面板填充结构：
        1. 正面（1类填充）：较大间距，形成孔洞
        2. 背面（2类填充）：较小间距，遮光
        """
        paths = []

        if not params.enabled:
            return paths

        # 内缩边界
        fill_contour = self.path_offset.offset_contour(
            contour, -params.fill_config.boundary_distance
        )
        if not fill_contour:
            return paths

        # 正面填充
        front_paths = self._generate_line_fill(
            fill_contour,
            params.fill_config.spacing,
            params.fill_config.angle,
            params.front_layer.extrusion_width
        )
        for path in front_paths:
            path.role = PathRole.FILL_PANEL
            path.extruder = params.front_layer.extruder or ExtruderType.EXTRUDER_1
        paths.extend(front_paths)

        # 背面填充（交叉角度）
        back_angle = params.fill_config.angle + 90
        back_paths = self._generate_line_fill(
            fill_contour,
            params.fill_config.spacing2,
            back_angle,
            params.back_layer.extrusion_width
        )
        for path in back_paths:
            path.role = PathRole.FILL_PANEL
            path.extruder = params.back_layer.extruder or ExtruderType.EXTRUDER_1
        paths.extend(back_paths)

        return paths

    def generate_grid_fill(self, contour: Contour,
                           params: GridParams) -> List[LayerPath]:
        """
        生成网格填充

        网格用于灌胶工艺，需要形成规则的方格
        """
        paths = []

        if not params.enabled:
            return paths

        fill_contour = self.path_offset.offset_contour(
            contour, -params.fill_config.boundary_distance
        )
        if not fill_contour:
            return paths

        # 生成水平线
        h_paths = self._generate_line_fill(
            fill_contour,
            params.fill_config.spacing,
            0,  # 水平
            params.layer.extrusion_width
        )

        # 生成垂直线
        v_paths = self._generate_line_fill(
            fill_contour,
            params.fill_config.spacing,
            90,  # 垂直
            params.layer.extrusion_width
        )

        for path in h_paths + v_paths:
            path.role = PathRole.FILL_GRID
        paths.extend(h_paths)
        paths.extend(v_paths)

        return paths

    def generate_baseplate_fill(self, contour: Contour,
                                params: BaseplateParams) -> List[LayerPath]:
        """
        生成底板填充

        底板填充需要密实，防止漏光
        """
        paths = []

        if not params.enabled:
            return paths

        fill_contour = self.path_offset.offset_contour(
            contour, -params.fill_config.boundary_distance
        )
        if not fill_contour:
            return paths

        # 密实填充
        fill_paths = self._generate_line_fill(
            fill_contour,
            params.fill_config.spacing,
            params.fill_config.angle,
            params.layer.extrusion_width
        )

        for path in fill_paths:
            path.role = PathRole.FILL_BASEPLATE
        paths.extend(fill_paths)

        return paths

    def _generate_line_fill(self, contour: Contour, spacing: float,
                            angle: float, line_width: float) -> List[LayerPath]:
        """
        生成线性填充

        算法：
        1. 旋转轮廓到水平方向
        2. 生成等间距水平扫描线
        3. 与轮廓求交
        4. 连接相邻线段（减少空走）
        5. 反向旋转恢复
        """
        if spacing <= 0:
            return []

        # 获取边界框
        min_x, min_y, max_x, max_y = contour.outer.bounds

        # 扩展边界（确保覆盖旋转后的区域）
        diagonal = math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # 旋转角度（弧度）
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        # 生成扫描线
        scan_lines = []
        y = center_y - diagonal / 2
        while y < center_y + diagonal / 2:
            # 旋转后的扫描线端点
            x1 = center_x - diagonal
            x2 = center_x + diagonal

            # 旋转回原坐标系
            start = Point(
                center_x + (x1 - center_x) * cos_a - (y - center_y) * sin_a,
                center_y + (x1 - center_x) * sin_a + (y - center_y) * cos_a
            )
            end = Point(
                center_x + (x2 - center_x) * cos_a - (y - center_y) * sin_a,
                center_y + (x2 - center_x) * sin_a + (y - center_y) * cos_a
            )

            scan_lines.append((start, end))
            y += spacing

        # 与轮廓求交
        clipped_segments = self._clip_lines_to_contour(scan_lines, contour)

        # 连接相邻线段
        connected_paths = self._connect_segments(clipped_segments)

        # 创建LayerPath对象
        paths = []
        for segment_points in connected_paths:
            if len(segment_points) >= 2:
                path = LayerPath(
                    points=segment_points,
                    role=PathRole.FILL_PANEL,
                    line_width=line_width,
                    is_closed=False
                )
                paths.append(path)

        return paths

    def _clip_lines_to_contour(self, lines: List[Tuple[Point, Point]],
                               contour: Contour) -> List[Tuple[Point, Point]]:
        """
        裁剪线段到轮廓内部

        使用线段-多边形求交算法
        """
        clipped = []

        for start, end in lines:
            intersections = self._line_polygon_intersections(
                start, end, contour.outer
            )

            # 配对交点形成线段
            if len(intersections) >= 2:
                intersections.sort(
                    key=lambda p: (p.x - start.x) ** 2 + (p.y - start.y) ** 2
                )
                for i in range(0, len(intersections) - 1, 2):
                    clipped.append((intersections[i], intersections[i + 1]))

        return clipped

    def _line_polygon_intersections(self, start: Point, end: Point,
                                    polygon: Path) -> List[Point]:
        """计算线段与多边形的所有交点"""
        intersections = []
        n = len(polygon.points)

        for i in range(n):
            j = (i + 1) % n
            p1 = polygon.points[i]
            p2 = polygon.points[j]

            intersection = self._line_line_intersection(start, end, p1, p2)
            if intersection:
                intersections.append(intersection)

        return intersections

    def _line_line_intersection(self, p1: Point, p2: Point,
                                p3: Point, p4: Point) -> Optional[Point]:
        """
        计算两线段的交点

        使用参数方程法
        """
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y
        x4, y4 = p4.x, p4.y

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return Point(x, y)

        return None

    def _connect_segments(self, segments: List[Tuple[Point, Point]]) -> List[List[Point]]:
        """
        连接相邻线段减少空走

        使用贪心算法：每次选择最近的下一个线段
        """
        if not segments:
            return []

        # 简单实现：按Y坐标排序，交替方向连接
        sorted_segments = sorted(segments, key=lambda s: s[0].y)

        connected = []
        current_path = []
        reverse_next = False

        for seg in sorted_segments:
            start, end = seg
            if reverse_next:
                start, end = end, start

            if current_path:
                # 检查是否可以连接
                last_point = current_path[-1]
                distance = math.sqrt(
                    (start.x - last_point.x) ** 2 +
                    (start.y - last_point.y) ** 2
                )

                if distance > 5:  # 超过阈值，开始新路径
                    if len(current_path) >= 2:
                        connected.append(current_path)
                    current_path = [start, end]
                else:
                    current_path.extend([start, end])
            else:
                current_path = [start, end]

            reverse_next = not reverse_next

        if len(current_path) >= 2:
            connected.append(current_path)

        return connected
