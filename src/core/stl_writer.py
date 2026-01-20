"""
SignMaker Slicer - STL导出模块

使用 trimesh + shapely 将切片结果转换为STL格式的3D模型文件。

STL生成算法（空心字壳）：
1. 每个WALL路径代表壁的中心线
2. 根据壁厚向外/内偏移生成外壁和内壁轮廓
3. 使用 Shapely 创建带孔多边形（外轮廓作为边界，内轮廓作为孔）
4. 使用 trimesh.extrude_polygon 挤出成3D网格
5. 合并所有层的网格并输出为STL文件

包边功能：
- 包边是在字壳顶部添加的一圈边框
- 向内包边：在字壳内侧，围绕字壳的内轮廓
- 向外包边：在字壳外侧，围绕字壳的外轮廓
"""

from __future__ import annotations
from typing import List, Optional
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid

from .types import (
    Point, Layer, LayerPath, PathRole, Contour,
    SliceResult, SliceParams, EdgeWrapParams
)
from .path_offset import PathOffset
from .types import Path as CorePath


class STLWriter:
    """STL文件生成器（使用trimesh生成空心字壳模型）"""

    def __init__(self, wall_thickness: float = 1.2):
        """
        初始化STL生成器

        Args:
            wall_thickness: 壁厚（mm），用于计算内外轮廓
        """
        self.wall_thickness = wall_thickness
        self.path_offset = PathOffset()

    def write(self, result: SliceResult, output_path: str,
              binary: bool = True, contours: Optional[List[Contour]] = None,
              params: Optional[SliceParams] = None) -> None:
        """
        生成并写入STL文件

        Args:
            result: 切片结果
            output_path: 输出文件路径
            binary: 是否使用二进制格式（默认True，文件更小）
            contours: 原始轮廓列表（用于生成包边）
            params: 切片参数（用于获取包边设置）
        """
        # 构建3D网格
        combined_mesh = self._build_hollow_mesh(result.layers)

        if combined_mesh is None or len(combined_mesh.faces) == 0:
            raise ValueError("无法生成STL：没有有效的几何数据")

        # 如果启用了包边，添加包边网格
        if contours and params and params.edge_wrap.wrap_enabled:
            edge_wrap_mesh = self._build_edge_wrap_mesh(
                contours, result, params
            )
            if edge_wrap_mesh is not None:
                combined_mesh = trimesh.util.concatenate([combined_mesh, edge_wrap_mesh])

        # 写入文件
        if binary:
            combined_mesh.export(output_path, file_type='stl')
        else:
            combined_mesh.export(output_path, file_type='stl_ascii')

    def _build_hollow_mesh(self, layers: List[Layer]) -> Optional[trimesh.Trimesh]:
        """
        构建空心字壳网格

        算法：
        1. 收集所有层的WALL路径
        2. 计算整体高度范围
        3. 对每个路径生成外轮廓和内轮廓
        4. 使用Shapely创建带孔多边形
        5. 使用trimesh挤出成3D网格
        """
        if not layers:
            return None

        # 收集所有层的壁路径信息
        all_wall_paths = []
        z_min = float('inf')
        z_max = float('-inf')
        wall_thickness = self.wall_thickness

        for layer in layers:
            wall_paths = [p for p in layer.paths if p.role == PathRole.WALL]
            if wall_paths:
                z_bottom = layer.z_height
                z_top = layer.z_height + layer.layer_height
                z_min = min(z_min, z_bottom)
                z_max = max(z_max, z_top)

                # 获取壁厚
                if wall_paths[0].line_width > 0:
                    wall_thickness = wall_paths[0].line_width

                for path in wall_paths:
                    all_wall_paths.append(path)

        if not all_wall_paths or z_min >= z_max:
            return None

        # 使用第一层的路径来生成轮廓（假设所有层��状相同）
        # 对于变化的轮廓，需要更复杂的处理
        first_layer_paths = [p for p in layers[0].paths if p.role == PathRole.WALL]
        if not first_layer_paths:
            return None

        half_wall = wall_thickness / 2
        height = z_max - z_min

        # 收集所有外轮廓和内轮廓
        meshes = []

        for path in first_layer_paths:
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
                    # 外轮廓作为边界，内轮廓作为孔
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

                # 处理MultiPolygon情况（make_valid可能返回MultiPolygon）
                if polygon.geom_type == 'MultiPolygon':
                    for geom in polygon.geoms:
                        if geom.area > 1e-6:
                            mesh = self._extrude_polygon(geom, height, z_min)
                            if mesh is not None:
                                meshes.append(mesh)
                elif polygon.geom_type == 'Polygon':
                    mesh = self._extrude_polygon(polygon, height, z_min)
                    if mesh is not None:
                        meshes.append(mesh)

            except Exception as e:
                # 跳过无法处理的路径
                print(f"警告：无法处理路径: {e}")
                continue

        if not meshes:
            return None

        # 合并所有网格
        if len(meshes) == 1:
            return meshes[0]
        else:
            return trimesh.util.concatenate(meshes)

    def _extrude_polygon(self, polygon: ShapelyPolygon, height: float,
                         z_offset: float = 0.0) -> Optional[trimesh.Trimesh]:
        """
        使用trimesh挤出多边形

        Args:
            polygon: Shapely多边形（可以带孔）
            height: 挤出高度
            z_offset: Z轴偏移

        Returns:
            挤出后的3D网格
        """
        try:
            # 使用trimesh的extrude_polygon函数
            mesh = trimesh.creation.extrude_polygon(polygon, height)

            # 如果有Z偏移，平移网格
            if z_offset != 0:
                mesh.apply_translation([0, 0, z_offset])

            return mesh
        except Exception as e:
            print(f"警告：挤出多边形失败: {e}")
            return None

    def _build_edge_wrap_mesh(self, contours: List[Contour],
                               result: SliceResult,
                               params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建包边网格

        包边结构：
        - 位置：字壳顶部（从 total_height - wrap_height 到 total_height）
        - 形状：围绕字壳轮廓的环形带，向内或向外水平延伸
        - 不增加模型总高度

        包边的3D结构（侧视图）：
        z=30mm  ┌────┬─────────┬────┐  ← 模型顶部
                │包边│   壁    │包边│  ← 包边区域
        z=27mm  └────┤         ├────┘  ← 包边下边缘
                     │   壁    │       ← 正常字壳壁（无包边）
        z=0mm   ─────┴─────────┴─────  ← 模型底部

        内包边：在字壳内壁的内侧向内延伸 wrap_width
        外包边：在字壳外壁的外侧向外延伸 wrap_width
        """
        if not contours:
            return None

        edge_wrap = params.edge_wrap
        wrap_width = edge_wrap.wrap_width
        wrap_height = edge_wrap.wrap_height

        # 获取字壳总高度
        total_height = params.shell.height

        # 包边的z起始位置（从顶部向下 wrap_height 的位置）
        wrap_z_start = total_height - wrap_height

        meshes = []

        for contour in contours:
            try:
                # 获取外轮廓点
                outer_points = contour.outer.points
                if not outer_points:
                    continue

                # 字壳壁的结构：
                # - 壁中心线 = 原始轮廓向内偏移 wall_thickness/2
                # - 外壁边缘 = 壁中心线向外偏移 wall_thickness/2 = 原始轮廓
                # - 内壁边缘 = 壁中心线向内偏移 wall_thickness/2 = 原始轮廓向内偏移 wall_thickness
                #
                # 内包边从内壁边缘开始，向内延伸 wrap_width

                # 内壁边缘（原始轮廓向内偏移整个壁厚）
                inner_wall_results = self.path_offset.offset(contour.outer, -self.wall_thickness)

                if not inner_wall_results:
                    continue

                inner_wall_coords = [(p.x, p.y) for p in inner_wall_results[0].points]
                if inner_wall_coords[0] != inner_wall_coords[-1]:
                    inner_wall_coords.append(inner_wall_coords[0])

                # 内包边：在内壁基础上继续向内延伸 wrap_width
                # 包边外边缘 = 内壁轮廓
                # 包边内边缘 = 内壁轮廓向内偏移 wrap_width
                inner_edge_results = self.path_offset.offset(
                    CorePath(points=[Point(x, y) for x, y in inner_wall_coords[:-1]]),
                    -wrap_width
                )

                if not inner_edge_results:
                    # 如果向内偏移失败（轮廓太小），跳过
                    continue

                inner_edge_coords = [(p.x, p.y) for p in inner_edge_results[0].points]
                if inner_edge_coords[0] != inner_edge_coords[-1]:
                    inner_edge_coords.append(inner_edge_coords[0])

                # 创建包边的环形多边形
                # 外边界：内壁轮廓
                # 内边界（孔）：内壁轮廓向内偏移 wrap_width
                try:
                    wrap_polygon = ShapelyPolygon(inner_wall_coords, [inner_edge_coords])

                    if not wrap_polygon.is_valid:
                        wrap_polygon = make_valid(wrap_polygon)

                    if wrap_polygon.is_empty or wrap_polygon.area < 1e-6:
                        continue

                    # 处理MultiPolygon情况
                    if wrap_polygon.geom_type == 'MultiPolygon':
                        for geom in wrap_polygon.geoms:
                            if geom.area > 1e-6:
                                # 从 wrap_z_start 开始挤出 wrap_height
                                mesh = self._extrude_polygon(geom, wrap_height, wrap_z_start)
                                if mesh is not None:
                                    meshes.append(mesh)
                    elif wrap_polygon.geom_type == 'Polygon':
                        mesh = self._extrude_polygon(wrap_polygon, wrap_height, wrap_z_start)
                        if mesh is not None:
                            meshes.append(mesh)

                except Exception as e:
                    print(f"警告：创建包边多边形失败: {e}")
                    continue

                # 处理内孔的包边
                for hole in contour.holes:
                    try:
                        # 内孔的壁结构：
                        # - 壁中心线 = 内孔轮廓向外偏移 wall_thickness/2
                        # - 内壁边缘（朝向孔内）= 壁中心线向外偏移 wall_thickness/2 = 内孔轮廓向外偏移 wall_thickness
                        # - 外壁边缘（朝向字壳内部）= 壁中心线向内偏移 wall_thickness/2 = 内孔轮廓
                        #
                        # 内孔包边从内壁边缘（朝向孔内）开始，向孔内延伸 wrap_width

                        # 内孔的内壁边缘（内孔轮廓向外偏移整个壁厚）
                        hole_inner_wall_results = self.path_offset.offset(hole, self.wall_thickness)

                        if not hole_inner_wall_results:
                            continue

                        hole_inner_wall_coords = [(p.x, p.y) for p in hole_inner_wall_results[0].points]
                        if hole_inner_wall_coords[0] != hole_inner_wall_coords[-1]:
                            hole_inner_wall_coords.append(hole_inner_wall_coords[0])

                        # 包边向孔内延伸 wrap_width
                        hole_wrap_inner_results = self.path_offset.offset(
                            CorePath(points=[Point(x, y) for x, y in hole_inner_wall_coords[:-1]]),
                            wrap_width
                        )

                        if not hole_wrap_inner_results:
                            continue

                        hole_wrap_inner_coords = [(p.x, p.y) for p in hole_wrap_inner_results[0].points]
                        if hole_wrap_inner_coords[0] != hole_wrap_inner_coords[-1]:
                            hole_wrap_inner_coords.append(hole_wrap_inner_coords[0])

                        # 内孔包边：从内壁边缘到内壁边缘+wrap_width
                        # 外边界：hole_wrap_inner_coords（更靠近孔中心）
                        # 内边界（孔）：hole_inner_wall_coords（内壁边缘）
                        hole_wrap_polygon = ShapelyPolygon(hole_wrap_inner_coords, [hole_inner_wall_coords])

                        if not hole_wrap_polygon.is_valid:
                            hole_wrap_polygon = make_valid(hole_wrap_polygon)

                        if hole_wrap_polygon.is_empty or hole_wrap_polygon.area < 1e-6:
                            continue

                        if hole_wrap_polygon.geom_type == 'MultiPolygon':
                            for geom in hole_wrap_polygon.geoms:
                                if geom.area > 1e-6:
                                    mesh = self._extrude_polygon(geom, wrap_height, wrap_z_start)
                                    if mesh is not None:
                                        meshes.append(mesh)
                        elif hole_wrap_polygon.geom_type == 'Polygon':
                            mesh = self._extrude_polygon(hole_wrap_polygon, wrap_height, wrap_z_start)
                            if mesh is not None:
                                meshes.append(mesh)

                    except Exception as e:
                        print(f"警告：创建内孔包边失败: {e}")
                        continue

            except Exception as e:
                print(f"警告：处理轮廓包边失败: {e}")
                continue

        if not meshes:
            return None

        if len(meshes) == 1:
            return meshes[0]
        else:
            return trimesh.util.concatenate(meshes)


def write_stl(result: SliceResult, output_path: str,
              binary: bool = True, wall_thickness: float = 1.2) -> None:
    """
    便捷函数：生成并写入STL文件

    Args:
        result: 切片结果
        output_path: 输出文件路径
        binary: 是否使用二进制格式
        wall_thickness: 壁厚
    """
    writer = STLWriter(wall_thickness=wall_thickness)
    writer.write(result, output_path, binary)
