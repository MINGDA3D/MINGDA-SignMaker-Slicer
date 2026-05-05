"""
边缘生成器模块

根据高度计算轮廓偏移，生成直边、斜边、异形边效果。
"""

from typing import Optional, List
from src.core.types import (
    Contour, ShellParams, EdgeType, EdgeProfile, Point,
    calculate_u_shape_offset_at_z,
)
from src.core.path_offset import PathOffset


class BevelGenerator:
    """边缘生成器"""

    def __init__(self, path_offset: Optional[PathOffset] = None):
        self.path_offset = path_offset or PathOffset()

    def apply_edge_profile(self, contour: Contour, z: float,
                           params: ShellParams) -> Optional[Contour]:
        """
        根据边缘类型和高度应用轮廓变换

        Args:
            contour: 原始轮廓
            z: 当前层高度
            params: 字壳参数

        Returns:
            变换后的轮廓（可能缩小到消失返回None）
        """
        if params.edge_type == EdgeType.STRAIGHT:
            return self._apply_straight_edge(contour, z, params)
        elif params.edge_type == EdgeType.BEVELED:
            return self._apply_beveled_edge(contour, z, params)
        elif params.edge_type == EdgeType.CUSTOM:
            return self._apply_custom_edge(contour, z, params)
        elif params.edge_type == EdgeType.U_SHAPED:
            return self._apply_u_shaped_edge(contour, z, params)
        else:
            return contour

    def _apply_straight_edge(self, contour: Contour, z: float,
                             params: ShellParams) -> Contour:
        """
        直边处理

        直边字壳从底到顶保持相同尺寸
        """
        return contour

    def _apply_beveled_edge(self, contour: Contour, z: float,
                            params: ShellParams) -> Optional[Contour]:
        """
        斜边处理

        斜边结构：
        ┌─────────┐ ← 面板位置（最内收缩）
        │ ╲     ╱ │
        │  ╲   ╱  │ ← 斜边区域（线性收缩）
        │   ╲ ╱   │
        │    │    │ ← 底板区域（不收缩）
        └────┴────┘

        收缩方向：从外向内
        """
        baseplate_top = params.baseplate_thickness
        bevel_end = baseplate_top + params.bevel_width
        max_offset = params.bevel_width  # 最大内缩距离

        if z < baseplate_top:
            # 底板区域：不收缩
            offset = 0
        elif z < bevel_end:
            # 斜边区域：线性收缩
            progress = (z - baseplate_top) / params.bevel_width
            offset = -progress * max_offset
        else:
            # 面板区域：保持最大收缩
            offset = -max_offset

        if abs(offset) < 0.001:
            return contour

        # 应用偏移
        return self.path_offset.offset_contour(contour, offset)

    def _apply_u_shaped_edge(self, contour: Contour, z: float,
                             params: ShellParams) -> Optional[Contour]:
        offset = calculate_u_shape_offset_at_z(z, params)
        if abs(offset) < 0.001:
            return contour
        return self.path_offset.offset_contour(contour, offset)

    def _apply_custom_edge(self, contour: Contour, z: float,
                           params: ShellParams) -> Optional[Contour]:
        """
        异形边处理

        根据EdgeProfile定义的点序列进行插值
        """
        if not params.edge_profile:
            return contour

        profile = params.edge_profile
        total_height = params.height

        # 归一化高度
        normalized_z = z / total_height if total_height > 0 else 0

        # 在profile中查找对应的偏移量
        offset = self._interpolate_profile(profile, normalized_z)

        if abs(offset) < 0.001:
            return contour

        return self.path_offset.offset_contour(contour, offset)

    def _interpolate_profile(self, profile: EdgeProfile,
                             normalized_z: float) -> float:
        """
        在异形边轮廓中插值

        profile.points 是 [(normalized_height, offset), ...] 的列表
        """
        points = profile.points
        if not points:
            return 0

        # 找到z所在的区间
        for i in range(len(points) - 1):
            z1, offset1 = points[i].x, points[i].y
            z2, offset2 = points[i + 1].x, points[i + 1].y

            if z1 <= normalized_z <= z2:
                # 线性插值
                t = (normalized_z - z1) / (z2 - z1) if z2 != z1 else 0
                return offset1 + t * (offset2 - offset1)

        # 超出范围，使用边界值
        if normalized_z < points[0].x:
            return points[0].y
        return points[-1].y

    def get_preview_profile(self, params: ShellParams) -> List[Point]:
        """
        获取边缘预览轮廓（用于UI显示）

        返回边缘截面的2D点序列
        """
        height = params.height
        steps = 50
        points = []

        for i in range(steps + 1):
            z = height * i / steps
            if params.edge_type == EdgeType.STRAIGHT:
                offset = 0
            elif params.edge_type == EdgeType.BEVELED:
                baseplate_top = params.baseplate_thickness
                bevel_end = baseplate_top + params.bevel_width

                if z < baseplate_top:
                    offset = 0
                elif z < bevel_end:
                    progress = (z - baseplate_top) / params.bevel_width
                    offset = progress * params.bevel_width
                else:
                    offset = params.bevel_width
            elif params.edge_type == EdgeType.U_SHAPED:
                offset = calculate_u_shape_offset_at_z(z, params)
            else:
                offset = 0

            points.append(Point(offset, z))

        return points

    def calculate_offset_at_height(self, z: float,
                                   params: ShellParams) -> float:
        """计算给定高度的偏移量"""
        if params.edge_type == EdgeType.STRAIGHT:
            return 0

        elif params.edge_type == EdgeType.BEVELED:
            baseplate_top = params.baseplate_thickness
            bevel_end = baseplate_top + params.bevel_width
            max_offset = params.bevel_width

            if z < baseplate_top:
                return 0
            elif z < bevel_end:
                progress = (z - baseplate_top) / params.bevel_width
                return -progress * max_offset
            else:
                return -max_offset

        elif params.edge_type == EdgeType.CUSTOM and params.edge_profile:
            normalized_z = z / params.height if params.height > 0 else 0
            return self._interpolate_profile(params.edge_profile, normalized_z)

        elif params.edge_type == EdgeType.U_SHAPED:
            return calculate_u_shape_offset_at_z(z, params)

        return 0
