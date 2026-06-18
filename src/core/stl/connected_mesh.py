"""
MINGDA SignMaker - 连襟网格生成器

生成连襟字连接桥的3D网格。
连襟是连接相邻字形的桥梁结构，根据类型（三角形/菱形）生成不同形状。
"""

from __future__ import annotations
from typing import List, Optional
import math

import numpy as np
import trimesh

from ..types import (
    Contour, SliceParams, ConnectedParams, Point,
    EdgeType, BevelDirection, JoinType,
)
from ..path_offset import PathOffset
from ..connected_generator import ConnectedGenerator, ConnectionBridge
from .mesh_utils import MeshUtils


class ConnectedMeshBuilder:
    """连襟字网格生成器"""

    def __init__(self, path_offset: PathOffset):
        """
        初始化连襟网格生成器

        Args:
            path_offset: 路径偏移工具
        """
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()
        self.connected_generator = ConnectedGenerator()

    def build(self, contours: List[Contour],
              params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建连襟网格

        连襟是连接相邻字形的桥梁结构。根据连襟类型（三角形/菱形），
        生成不同形状的3D连接桥。

        结构说明（三角形连襟侧视图）：
            字壳A ════════════════════════════════ 字壳B
                  ╲                            ╱
                   ╲        连襟斜边         ╱
                    ╲                      ╱
                     ╲                    ╱
                      ════════════════════  ← 底座（直边）

        Args:
            contours: 轮廓列表
            params: 切片参数

        Returns:
            连襟网格
        """
        if not contours:
            return None

        # 计算总路径数（外轮廓 + 内孔）
        total_paths = sum(
            1 + len(c.holes or []) for c in contours
        )
        if total_paths < 2:
            return None

        connected_params = params.connected
        if not connected_params.enabled:
            return None

        # 对于斜边字，需要使用底部层的实际轮廓来计算连接桥
        # 连襟从z=0开始，需要考虑斜边在底部的偏移
        contours_for_bridge = self._get_contours_at_z(contours, 0, params)

        # 检测连接桥
        bridges = self.connected_generator.find_connection_bridges(
            contours_for_bridge, connected_params
        )

        if not bridges:
            return None

        meshes = []

        for bridge in bridges:
            bridge_mesh = self._create_bridge_mesh(
                bridge,
                connected_params,
                max(params.shell.layer_height, 0.001),
            )
            if bridge_mesh is not None:
                meshes.append(bridge_mesh)

        return MeshUtils.merge_meshes(meshes)

    def _get_contours_at_z(self, contours: List[Contour], z: float,
                           params: SliceParams) -> List[Contour]:
        """
        获取指定高度的轮廓（考虑斜边/异形边偏移）

        对于斜边字或异形边字，不同高度的轮廓大小不同。这个方法返回应用了
        边缘偏移后的轮廓。

        Args:
            contours: 原始轮廓列表
            z: 目标高度
            params: 切片参数

        Returns:
            偏移后的轮廓列表
        """
        shell = params.shell

        # 直边不需要偏移
        if shell.edge_type == EdgeType.STRAIGHT:
            return contours

        # 计算该高度的偏移量
        if shell.edge_type == EdgeType.CUSTOM:
            offset = self._calculate_custom_edge_offset_at_z(z, shell)
        else:
            offset = self._calculate_bevel_offset_at_z(z, shell)

        if abs(offset) < 0.001:
            return contours

        # 应用偏移到所有轮廓
        result = []
        for contour in contours:
            offset_contour = self._offset_contour_same_direction(contour, offset)
            if offset_contour is not None:
                result.append(offset_contour)

        return result if result else contours

    def _calculate_bevel_offset_at_z(self, z: float, shell) -> float:
        """
        计算斜边在指定高度的偏移量

        Args:
            z: 高度
            shell: 字壳参数

        Returns:
            偏移量（正值表示向外凸出，负值表示向内收缩）
        """
        if shell.edge_type != EdgeType.BEVELED:
            return 0

        total_height = shell.height
        baseplate_thickness = shell.baseplate_thickness
        panel_thickness = shell.panel_thickness
        bevel_width = shell.bevel_width

        # 计算区域边界
        baseplate_top = baseplate_thickness
        panel_bottom = total_height - panel_thickness

        if shell.bevel_direction == BevelDirection.TOP_SMALL:
            # 上小下大：底面保持原始轮廓，向上逐渐内缩
            if z < baseplate_top:
                return 0
            elif z < panel_bottom:
                bevel_height = panel_bottom - baseplate_top
                if bevel_height > 0:
                    progress = (z - baseplate_top) / bevel_height
                    return -progress * bevel_width
                return 0
            else:
                return -bevel_width
        else:
            # 上大下小：底面保持原始轮廓，向上逐渐外扩
            if z < baseplate_top:
                return 0
            elif z < panel_bottom:
                bevel_height = panel_bottom - baseplate_top
                if bevel_height > 0:
                    progress = (z - baseplate_top) / bevel_height
                    return progress * bevel_width
                return 0
            else:
                return bevel_width

    def _calculate_custom_edge_offset_at_z(self, z: float, shell) -> float:
        """
        计算异形边在指定高度的偏移量

        使用EdgeProfile的控制点和插值算法计算偏移。

        Args:
            z: 高度
            shell: 字壳参数

        Returns:
            偏移量（正值表示向外凸出，负值表示向内收缩）
        """
        if shell.edge_type != EdgeType.CUSTOM:
            return 0

        profile = shell.edge_profile
        if not profile:
            return 0

        total_height = shell.height
        bevel_width = shell.bevel_width

        # 归一化高度
        normalized_z = z / total_height if total_height > 0 else 0

        # 使用EdgeProfile的方法获取偏移量
        if profile.control_points:
            return profile.get_offset_at_height(normalized_z, bevel_width, total_height)

        return 0

    def _offset_contour_same_direction(self, contour: Contour,
                                       distance: float) -> Optional[Contour]:
        """
        对整个轮廓进行同方向偏移（外轮廓和内孔同向）

        Args:
            contour: 输入轮廓
            distance: 偏移距离

        Returns:
            偏移后的轮廓
        """
        outer_results = self.path_offset.offset(contour.outer, distance, JoinType.MITER)
        if not outer_results:
            return None

        new_outer = outer_results[0]

        new_holes = []
        for hole in contour.holes:
            hole_results = self.path_offset.offset(hole, distance, JoinType.MITER)
            new_holes.extend(hole_results)

        return Contour(
            outer=new_outer,
            holes=new_holes,
            connected_frames=contour.connected_frames,
            patterns=contour.patterns,
            name=contour.name
        )

    def _create_bridge_mesh(
        self,
        bridge: ConnectionBridge,
        params: ConnectedParams,
        layer_height: float,
    ) -> Optional[trimesh.Trimesh]:
        """
        为单个连接桥创建3D网格

        根据连襟类型生成不同形状：
        - 三角形：底部宽，顶部收窄为线
        - 菱形：中间窄，两端宽

        Args:
            bridge: 连接桥数据
            params: 连襟参数
            layer_height: 使用当前字壳层高切分桥体高度

        Returns:
            连接桥网格
        """
        if not bridge.corners or len(bridge.corners) < 4:
            return None

        try:
            total_height = self.connected_generator.get_total_height(params)

            # 连接桥的两个端点
            point_a = bridge.point_a
            point_b = bridge.point_b

            # 计算连接方向
            dx = point_b.x - point_a.x
            dy = point_b.y - point_a.y
            length = math.sqrt(dx * dx + dy * dy)

            if length < 0.001:
                return None

            # 归一化方向
            dx /= length
            dy /= length

            # 垂直方向（法线）
            nx = -dy
            ny = dx

            meshes = []

            # 分层生成网格
            num_layers = max(1, math.ceil(total_height / layer_height))

            for i in range(num_layers):
                z_bottom = i * layer_height
                z_top = min((i + 1) * layer_height, total_height)

                # 计算当前层的宽度
                width_bottom = self.connected_generator._calculate_width_at_z(
                    z_bottom, params
                )
                width_top = self.connected_generator._calculate_width_at_z(
                    z_top, params
                )

                # 跳过宽度太小的层
                if width_bottom < 0.1 and width_top < 0.1:
                    continue

                # 生成这一层的网格
                layer_mesh = self._create_bridge_layer(
                    point_a, point_b,
                    nx, ny, length,
                    width_bottom, width_top,
                    z_bottom, z_top
                )

                if layer_mesh is not None:
                    meshes.append(layer_mesh)

            return MeshUtils.merge_meshes(meshes)

        except Exception as e:
            print(f"警告：创建连接桥网格失败: {e}")
            return None

    def _create_bridge_layer(self, point_a: Point, point_b: Point,
                             nx: float, ny: float, length: float,
                             width_bottom: float, width_top: float,
                             z_bottom: float, z_top: float) -> Optional[trimesh.Trimesh]:
        """
        创建连接桥的单层网格

        这是一个梯形截面的3D体，宽度从底部到顶部可以变化。

        Args:
            point_a, point_b: 连接桥两端点
            nx, ny: 垂直于连接方向的法线
            length: 连接距离
            width_bottom: 底层宽度
            width_top: 顶层宽度
            z_bottom, z_top: Z坐标范围

        Returns:
            层网格
        """
        try:
            half_w_bottom = width_bottom / 2
            half_w_top = width_top / 2

            # 8个顶点：底层4个 + 顶层4个
            vertices = [
                # 底层 - A侧
                [point_a.x + nx * half_w_bottom, point_a.y + ny * half_w_bottom, z_bottom],  # 0
                [point_a.x - nx * half_w_bottom, point_a.y - ny * half_w_bottom, z_bottom],  # 1
                # 底层 - B侧
                [point_b.x - nx * half_w_bottom, point_b.y - ny * half_w_bottom, z_bottom],  # 2
                [point_b.x + nx * half_w_bottom, point_b.y + ny * half_w_bottom, z_bottom],  # 3
                # 顶层 - A侧
                [point_a.x + nx * half_w_top, point_a.y + ny * half_w_top, z_top],  # 4
                [point_a.x - nx * half_w_top, point_a.y - ny * half_w_top, z_top],  # 5
                # 顶层 - B侧
                [point_b.x - nx * half_w_top, point_b.y - ny * half_w_top, z_top],  # 6
                [point_b.x + nx * half_w_top, point_b.y + ny * half_w_top, z_top],  # 7
            ]

            # 12个三角面
            faces = [
                # 底面 (0-1-2, 0-2-3)
                [0, 2, 1],
                [0, 3, 2],
                # 顶面 (4-5-6, 4-6-7)
                [4, 5, 6],
                [4, 6, 7],
                # 前面 - 左侧 (0-4-7, 0-7-3)
                [0, 4, 7],
                [0, 7, 3],
                # 后面 - 右侧 (1-2-6, 1-6-5)
                [1, 2, 6],
                [1, 6, 5],
                # A端面 (0-1-5, 0-5-4)
                [0, 1, 5],
                [0, 5, 4],
                # B端面 (3-7-6, 3-6-2)
                [3, 7, 6],
                [3, 6, 2],
            ]

            vertices = np.array(vertices)
            faces = np.array(faces)

            return trimesh.Trimesh(vertices=vertices, faces=faces)

        except Exception as e:
            print(f"警告：创建连接桥层失败: {e}")
            return None
