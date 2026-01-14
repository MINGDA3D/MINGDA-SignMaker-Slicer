"""
连襟生成器模块

生成连襟字结构，连接相邻字形。
"""

import math
from typing import List, Optional, Tuple
from src.core.types import (
    Contour, ConnectedParams, LayerPath, PathRole,
    ExtruderType, Point, Path, PathType
)
from src.core.path_offset import PathOffset


class ConnectedGenerator:
    """连襟字生成器"""

    def __init__(self, path_offset: Optional[PathOffset] = None):
        self.path_offset = path_offset or PathOffset()

    def generate_connected(self, contours: List[Contour], z: float,
                           params: ConnectedParams) -> List[LayerPath]:
        """
        生成连襟结构

        连襟类型：
        - 三角形连襟：顶部斜边，适合常规使用
        - 菱形连襟：双面斜边，适合双面发光字

        Args:
            contours: 轮廓列表
            z: 当前层高度
            params: 连襟参数

        Returns:
            连襟路径列表
        """
        paths = []

        if not params.enabled:
            return paths

        # 查找所有连襟框
        connected_frames = self._find_connected_frames(contours)

        for frame in connected_frames:
            if params.type == "triangle":
                frame_paths = self._generate_triangle_connected(frame, z, params)
            else:  # diamond
                frame_paths = self._generate_diamond_connected(frame, z, params)

            paths.extend(frame_paths)

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

    def _generate_triangle_connected(self, frame: Path, z: float,
                                     params: ConnectedParams) -> List[LayerPath]:
        """
        生成三角形连襟

        结构：
        ╲      ╱  ← 顶部斜边
         ╲    ╱
          ╲  ╱
           ╲╱
           │    ← 底座直边
           │
        """
        paths = []

        # 计算连襟高度区域
        base_height = params.base_height  # 底座高度
        bevel_height = params.height  # 斜边高度
        total_height = base_height + bevel_height

        if z < base_height:
            # 底座区域：保持原始宽度
            wall_path = self._generate_wall_path(
                frame, params.width, params
            )
            paths.append(wall_path)

        elif z < total_height:
            # 斜边区域：线性收缩
            progress = (z - base_height) / bevel_height
            current_width = params.width * (1 - progress)

            if current_width > 0.1:  # 最小宽度限制
                wall_path = self._generate_wall_path(
                    frame, current_width, params
                )
                paths.append(wall_path)

        return paths

    def _generate_diamond_connected(self, frame: Path, z: float,
                                    params: ConnectedParams) -> List[LayerPath]:
        """
        生成菱形连襟

        结构：
        ╲      ╱
         ╲    ╱   ← 上半部分斜边
          ╲  ╱
           ╲╱     ← 中间最窄
          ╱╲
         ╱  ╲     ← 下半部分斜边
        ╱    ╲
        """
        paths = []

        # 菱形连襟：中间最窄
        total_height = params.base_height + params.height * 2
        mid_height = total_height / 2

        if z < mid_height:
            # 下半部分：逐渐收窄
            progress = z / mid_height
            current_width = params.width * (1 - progress * 0.5)
        else:
            # 上半部分：逐渐展宽
            progress = (z - mid_height) / mid_height
            current_width = params.width * (0.5 + progress * 0.5)

        if current_width > 0.1:
            wall_path = self._generate_wall_path(frame, current_width, params)
            paths.append(wall_path)

        return paths

    def _generate_wall_path(self, frame: Path, width: float,
                            params: ConnectedParams) -> LayerPath:
        """
        根据框架生成壁路径

        Args:
            frame: 连襟框架
            width: 当前宽度
            params: 连襟参数

        Returns:
            壁路径
        """
        # 简化实现：使用框架的偏移路径
        offset_paths = self.path_offset.offset(frame, -params.support_offset)

        if offset_paths:
            points = offset_paths[0].points
        else:
            points = frame.points

        return LayerPath(
            points=points,
            role=PathRole.WALL,
            extruder=ExtruderType.EXTRUDER_1,
            line_width=width
        )

    def _generate_support(self, contour: Contour,
                          params: ConnectedParams) -> List[LayerPath]:
        """
        生成镜像打印时的连襟支撑

        用于反扣工艺时支撑连襟结构
        """
        paths = []

        for frame in contour.connected_frames:
            # 向内偏移生成支撑
            offset_distance = params.support_offset
            support_paths = self.path_offset.offset(frame, -offset_distance)

            for support_path in support_paths:
                layer_path = LayerPath(
                    points=support_path.points,
                    role=PathRole.WALL,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=params.width * 0.3  # 支撑较窄
                )
                paths.append(layer_path)

        return paths

    def calculate_connected_bounds(self, frame: Path,
                                   params: ConnectedParams) -> Tuple[float, float, float, float]:
        """
        计算连襟区域边界

        Returns:
            (min_x, min_y, max_x, max_y)
        """
        xs = [p.x for p in frame.points]
        ys = [p.y for p in frame.points]
        return (min(xs), min(ys), max(xs), max(ys))
