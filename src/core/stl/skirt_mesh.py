"""
MINGDA SignMaker - 裙边网格生成器

生成防翘裙边的3D网格。
裙边是围绕字壳底部的梯形结构，用于防止打印时翘边。
"""

from __future__ import annotations
from typing import List, Optional
from copy import copy

import numpy as np
import trimesh

from ..types import Contour, SliceParams
from ..path_offset import PathOffset
from ..skirt_generator import SkirtGenerator, TrapezoidSkirt
from .mesh_utils import MeshUtils


class SkirtMeshBuilder:
    """防翘裙边网格生成器"""

    def __init__(self, path_offset: PathOffset):
        """
        初始化裙边网格生成器

        Args:
            path_offset: 路径偏移工具
        """
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()
        self.skirt_generator = SkirtGenerator()

    def build(self, contours: List[Contour],
              params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建防翘裙边网格

        裙边结构（截面图）：
          字壳 ════════════════════════════════════════════
               ╲          ╱╲          ╱╲          ╱
                ╲        ╱  ╲        ╱  ╲        ╱
                 ╲      ╱    ╲      ╱    ╲      ╱
                  ╲    ╱      ╲    ╱      ╲    ╱
                   ────        ────        ────

        每个梯形是一个3D楔形体：
        - 顶面：贴着字壳底部（z=0到z=skirt_height）
        - 底面：向外延伸的底边
        - 侧面：连接顶边和底边的斜面

        相邻梯形共享斜边，形成连续的波浪形结构。

        Args:
            contours: 轮廓列表
            params: 切片参数

        Returns:
            裙边网格
        """
        if not contours:
            return None

        skirt_params = params.skirt
        skirt_height = skirt_params.height
        meshes = []

        for contour in contours:
            try:
                # 外轮廓：裙边向外延伸
                trapezoids = self.skirt_generator.generate_skirt_3d(
                    contour, skirt_params
                )

                for trap in trapezoids:
                    # 为每个梯形创建3D网格
                    trap_mesh = self._create_trapezoid_mesh(trap, skirt_height)
                    if trap_mesh is not None:
                        meshes.append(trap_mesh)

                # 处理内孔：裙边向孔内延伸（方向相反）
                for hole in contour.holes:
                    # 创建内孔的裙边参数（方向相反）
                    hole_skirt_params = copy(skirt_params)
                    hole_skirt_params.is_outer = False  # 内孔方向相反

                    # 内孔作为临时contour的外轮廓
                    hole_contour = Contour(outer=hole, holes=[])
                    hole_trapezoids = self.skirt_generator.generate_skirt_3d(
                        hole_contour,
                        hole_skirt_params
                    )
                    for trap in hole_trapezoids:
                        trap_mesh = self._create_trapezoid_mesh(trap, skirt_height)
                        if trap_mesh is not None:
                            meshes.append(trap_mesh)

            except Exception as e:
                print(f"Warning: Failed to process contour skirt: {e}")
                continue

        return MeshUtils.merge_meshes(meshes)

    def _create_trapezoid_mesh(self, trap: TrapezoidSkirt,
                               height: float,
                               wall_thickness: float = 0.8) -> Optional[trimesh.Trimesh]:
        """
        为单个梯形创建3D网格（空心轮廓）

        梯形裙边只有3条边：左斜边、底边、右斜边。
        不包含顶边（贴着字壳的边），这样打印后更容易从字壳剥离。

        使用连续路径创建，确保转角处平滑连接无缺口。

        结构：
          字壳 ════════════════════════════════════════════
               ╲          ╱╲          ╱╲          ╱
                ╲        ╱  ╲        ╱  ╲        ╱
                 ╲      ╱    ╲      ╱    ╲      ╱
                  ╲    ╱      ╲    ╱      ╲    ╱
                   ────        ────        ────

        Args:
            trap: 梯形数据
            height: 裙边高度
            wall_thickness: 壁厚

        Returns:
            梯形轮廓网格
        """
        try:
            # 创建连续的3条边路径（不闭��）
            # 顺序：top_right -> bottom_right -> bottom_left -> top_left
            path_points = [
                (trap.top_right.x, trap.top_right.y),
                (trap.bottom_right.x, trap.bottom_right.y),
                (trap.bottom_left.x, trap.bottom_left.y),
                (trap.top_left.x, trap.top_left.y),
            ]

            return self.mesh_utils.create_continuous_wall(path_points, 0, height, wall_thickness)

        except Exception as e:
            print(f"Warning: Failed to create trapezoid mesh: {e}")
            return None
