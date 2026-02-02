"""
SignMaker Slicer - 字壳网格生成器

生成空心字壳的3D网格，支持逐层挤出。
"""

from __future__ import annotations
from typing import List, Optional

import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid

from ..types import Layer, LayerPath, PathRole, Point
from ..types import Path as CorePath
from ..path_offset import PathOffset
from .mesh_utils import MeshUtils


class ShellMeshBuilder:
    """空心字壳网格生成器"""

    def __init__(self, path_offset: PathOffset, wall_thickness: float = 1.2):
        """
        初始化字壳网格生成器

        Args:
            path_offset: 路径偏移工具
            wall_thickness: 壁厚（mm）
        """
        self.path_offset = path_offset
        self.wall_thickness = wall_thickness
        self.mesh_utils = MeshUtils()

    def build(self, layers: List[Layer]) -> Optional[trimesh.Trimesh]:
        """
        构建空心字壳网格

        算法（支持斜边变化轮廓）：
        1. 收集所有层的WALL路径
        2. 对每一层生成外轮廓和内轮廓
        3. 逐层挤出生成3D网格
        4. 合并所有层的网格

        Args:
            layers: 层数据列表

        Returns:
            空心字壳网格
        """
        if not layers:
            return None

        # 收集所有层信息
        wall_thickness = self.wall_thickness
        meshes = []

        for layer in layers:
            wall_paths = [p for p in layer.paths if p.role == PathRole.WALL]
            if not wall_paths:
                continue

            z_bottom = layer.z_height
            layer_height = layer.layer_height

            # 获取壁厚
            if wall_paths[0].line_width > 0:
                wall_thickness = wall_paths[0].line_width

            half_wall = wall_thickness / 2

            for path in wall_paths:
                # 将路径转换为Path对象用于偏移
                core_path = CorePath(points=path.points)

                # 向外偏移得到外轮廓
                outer_results = self.path_offset.offset(core_path, half_wall)
                # 向内偏移得到内轮廓
                inner_results = self.path_offset.offset(core_path, -half_wall)

                if not outer_results:
                    continue

                outer_points = outer_results[0].points

                # 转换为坐标列表
                outer_coords = [(p.x, p.y) for p in outer_points]

                # 确保多边形闭合
                if outer_coords[0] != outer_coords[-1]:
                    outer_coords.append(outer_coords[0])

                try:
                    if inner_results:
                        # 有内轮廓，创建带孔的多边形（空心）
                        inner_points = inner_results[0].points
                        inner_coords = [(p.x, p.y) for p in inner_points]

                        # 确保内轮廓闭合
                        if inner_coords[0] != inner_coords[-1]:
                            inner_coords.append(inner_coords[0])

                        # 创建带孔的Shapely多边形
                        polygon = ShapelyPolygon(outer_coords, [inner_coords])
                    else:
                        # 没有内轮廓，创建实心多边形
                        polygon = ShapelyPolygon(outer_coords)

                    # 验证并修复多边形
                    if not polygon.is_valid:
                        polygon = make_valid(polygon)

                    # 跳过空的或无效的多边形
                    if polygon.is_empty or polygon.area < 1e-6:
                        continue

                    # 处理MultiPolygon情况
                    if polygon.geom_type == 'MultiPolygon':
                        for geom in polygon.geoms:
                            if geom.area > 1e-6:
                                mesh = self.mesh_utils.extrude_polygon(
                                    geom, layer_height, z_bottom
                                )
                                if mesh is not None:
                                    meshes.append(mesh)
                    elif polygon.geom_type == 'Polygon':
                        mesh = self.mesh_utils.extrude_polygon(
                            polygon, layer_height, z_bottom
                        )
                        if mesh is not None:
                            meshes.append(mesh)

                except Exception as e:
                    # 跳过无法处理的路径
                    print(f"警告：无法处理路径: {e}")
                    continue

        return MeshUtils.merge_meshes(meshes)
