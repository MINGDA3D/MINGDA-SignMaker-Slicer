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
    SliceResult, SliceParams, EdgeWrapParams, EdgeDirection
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

        # 如果启用了勾边，添加勾边网格
        if contours and params and params.edge_wrap.outline_enabled:
            outline_mesh = self._build_outline_mesh(
                contours, result, params
            )
            if outline_mesh is not None:
                combined_mesh = trimesh.util.concatenate([combined_mesh, outline_mesh])

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
        - 形状：围绕字壳轮廓的环形带，矩形截面（上下宽度相同）
        - 不增加模型总高度

        方向选择：
        - 内部（INNER）：从内壁向内延伸
        - 外部（OUTER）：从外壁向外延伸
        """
        if not contours:
            return None

        edge_wrap = params.edge_wrap
        wrap_width = edge_wrap.wrap_width
        wrap_height = edge_wrap.wrap_height
        wrap_direction = edge_wrap.wrap_direction

        # 获取字壳总高度
        total_height = params.shell.height

        # 包边的z起始位置
        wrap_z_start = total_height - wrap_height

        meshes = []

        for contour in contours:
            try:
                outer_points = contour.outer.points
                if not outer_points:
                    continue

                if wrap_direction == EdgeDirection.INNER:
                    # 内部包边：从内壁向内延伸
                    # 内壁边缘 = 原始轮廓向内偏移 wall_thickness
                    inner_wall_results = self.path_offset.offset(contour.outer, -self.wall_thickness)
                    if not inner_wall_results:
                        continue

                    outer_ring_coords = [(p.x, p.y) for p in inner_wall_results[0].points]
                    if outer_ring_coords[0] != outer_ring_coords[-1]:
                        outer_ring_coords.append(outer_ring_coords[0])

                    # 包边内边缘 = 内壁向内偏移 wrap_width
                    inner_edge_results = self.path_offset.offset(
                        CorePath(points=[Point(x, y) for x, y in outer_ring_coords[:-1]]),
                        -wrap_width
                    )
                    if not inner_edge_results:
                        continue

                    inner_ring_coords = [(p.x, p.y) for p in inner_edge_results[0].points]
                    if inner_ring_coords[0] != inner_ring_coords[-1]:
                        inner_ring_coords.append(inner_ring_coords[0])

                else:
                    # 外部包边：从外壁向外延伸
                    # 外壁边缘 = 原始轮廓
                    inner_ring_coords = [(p.x, p.y) for p in outer_points]
                    if inner_ring_coords[0] != inner_ring_coords[-1]:
                        inner_ring_coords.append(inner_ring_coords[0])

                    # 包边外边缘 = 外壁向外偏移 wrap_width
                    outer_edge_results = self.path_offset.offset(contour.outer, wrap_width)
                    if not outer_edge_results:
                        continue

                    outer_ring_coords = [(p.x, p.y) for p in outer_edge_results[0].points]
                    if outer_ring_coords[0] != outer_ring_coords[-1]:
                        outer_ring_coords.append(outer_ring_coords[0])

                # 创建包边的环形多边形
                try:
                    wrap_polygon = ShapelyPolygon(outer_ring_coords, [inner_ring_coords])

                    if not wrap_polygon.is_valid:
                        wrap_polygon = make_valid(wrap_polygon)

                    if wrap_polygon.is_empty or wrap_polygon.area < 1e-6:
                        continue

                    if wrap_polygon.geom_type == 'MultiPolygon':
                        for geom in wrap_polygon.geoms:
                            if geom.area > 1e-6:
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
                        if wrap_direction == EdgeDirection.INNER:
                            # 内孔内部包边：从内孔的内壁向孔内延伸
                            hole_inner_wall_results = self.path_offset.offset(hole, self.wall_thickness)
                            if not hole_inner_wall_results:
                                continue

                            hole_inner_ring = [(p.x, p.y) for p in hole_inner_wall_results[0].points]
                            if hole_inner_ring[0] != hole_inner_ring[-1]:
                                hole_inner_ring.append(hole_inner_ring[0])

                            hole_wrap_results = self.path_offset.offset(
                                CorePath(points=[Point(x, y) for x, y in hole_inner_ring[:-1]]),
                                wrap_width
                            )
                            if not hole_wrap_results:
                                continue

                            hole_outer_ring = [(p.x, p.y) for p in hole_wrap_results[0].points]
                            if hole_outer_ring[0] != hole_outer_ring[-1]:
                                hole_outer_ring.append(hole_outer_ring[0])

                        else:
                            # 内孔外部包边：从内孔轮廓向外延伸
                            hole_outer_ring = [(p.x, p.y) for p in hole.points]
                            if hole_outer_ring[0] != hole_outer_ring[-1]:
                                hole_outer_ring.append(hole_outer_ring[0])

                            hole_wrap_results = self.path_offset.offset(hole, -wrap_width)
                            if not hole_wrap_results:
                                continue

                            hole_inner_ring = [(p.x, p.y) for p in hole_wrap_results[0].points]
                            if hole_inner_ring[0] != hole_inner_ring[-1]:
                                hole_inner_ring.append(hole_inner_ring[0])

                        hole_wrap_polygon = ShapelyPolygon(hole_outer_ring, [hole_inner_ring])

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

    def _build_outline_mesh(self, contours: List[Contour],
                             result: SliceResult,
                             params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建勾边网格（斜坡形状）

        勾边与包边的区别：
        - 包边：矩形截面，上下宽度相同
        - 勾边：斜坡/楔形截面，下大上小

        方向选择：
        - 内部（INNER）：从内壁向内延伸
        - 外部（OUTER）：从外壁向外延伸

        勾边的3D结构（侧视图）- 下大上小：

        z=30mm  ──────┬────────┬──────  ← 模型顶部（勾边与壁齐平）
                      │        │
        z=27mm  ────╱─┤        ├─╲────  ← 勾边底部（向外/内延伸）
                   ╱  │   壁   │  ╲
                  ╱   │        │   ╲
        z=0mm   ──────┴────────┴──────  ← 模型底部

        底部：延伸 outline_width
        顶部：与壁边缘齐平
        """
        if not contours:
            return None

        edge_wrap = params.edge_wrap
        outline_width = edge_wrap.outline_width
        outline_height = edge_wrap.outline_height
        outline_offset = edge_wrap.outline_offset
        outline_direction = edge_wrap.outline_direction

        # 获取字壳总高度
        total_height = params.shell.height

        # 勾边的z高度范围
        z_bottom = total_height - outline_height  # 勾边底部
        z_top = total_height                       # 勾边顶部

        meshes = []

        # 根据方向确定偏移符号
        # 内部：负偏移（向内）
        # 外部：正偏移（向外）
        if outline_direction == EdgeDirection.INNER:
            direction_sign = -1
        else:
            direction_sign = 1

        for contour in contours:
            try:
                outer_points = contour.outer.points
                if not outer_points:
                    continue

                # 计算外轮廓的勾边偏移
                # 对于外轮廓：
                # - 外部方向：正偏移向外
                # - 内部方向：需要从内壁开始
                if outline_direction == EdgeDirection.INNER:
                    # 内部勾边：从内壁边缘开始
                    # 底部偏移 = -(wall_thickness + outline_offset + outline_width)
                    # 顶部偏移 = -(wall_thickness + outline_offset)
                    offset_bottom = -(self.wall_thickness + outline_offset + outline_width)
                    offset_top = -(self.wall_thickness + outline_offset)
                else:
                    # 外部勾边：从外壁边缘开始
                    # 底部偏移 = outline_offset + outline_width
                    # 顶部偏移 = outline_offset
                    offset_bottom = outline_offset + outline_width
                    offset_top = outline_offset

                outline_mesh = self._build_sloped_ring(
                    contour.outer,
                    z_bottom, z_top,
                    offset_bottom,
                    offset_top,
                    is_outer=True
                )
                if outline_mesh is not None:
                    meshes.append(outline_mesh)

                # 处理内孔的勾边
                for hole in contour.holes:
                    if outline_direction == EdgeDirection.INNER:
                        # 内孔内部勾边：从内孔内壁向孔内延伸
                        hole_offset_bottom = self.wall_thickness + outline_offset + outline_width
                        hole_offset_top = self.wall_thickness + outline_offset
                    else:
                        # 内孔外部勾边：从内孔外壁向字壳内部延伸
                        hole_offset_bottom = -(outline_offset + outline_width)
                        hole_offset_top = -outline_offset

                    hole_outline_mesh = self._build_sloped_ring(
                        hole,
                        z_bottom, z_top,
                        hole_offset_bottom,
                        hole_offset_top,
                        is_outer=False
                    )
                    if hole_outline_mesh is not None:
                        meshes.append(hole_outline_mesh)

            except Exception as e:
                print(f"警告：处理轮廓勾边失败: {e}")
                continue

        if not meshes:
            return None

        if len(meshes) == 1:
            return meshes[0]
        else:
            return trimesh.util.concatenate(meshes)

    def _build_sloped_ring(self, path: CorePath,
                           z_bottom: float, z_top: float,
                           offset_bottom: float, offset_top: float,
                           is_outer: bool = True) -> Optional[trimesh.Trimesh]:
        """
        构建实心斜坡楔形网格

        使用分层挤出方法：将斜坡分成多个薄层，每层使用Shapely环形多边形挤出。

        关键：内边缘固定在壁的位置（offset_top），只有外边缘逐渐变化。
        这样形成的是一个实心的楔形，而不是空心的壳。

        楔形截面示意：
            内边缘（固定）
               ↓
            ┌──┐ ← 顶部
            │   ╲
            │    ╲  ← 斜坡（外边缘逐渐变化）
            │     ╲
            └──────╲ ← 底部
               ↑
            外边缘（最宽）

        Args:
            path: 原始轮廓路径（壁边缘位置）
            z_bottom: 底部Z高度
            z_top: 顶部Z高度
            offset_bottom: 底部偏移量（正=向外，负=向内）
            offset_top: 顶部偏移量（正=向外，负=向内）
            is_outer: 是否为外轮廓（影响环形多边形的构建方式）

        Returns:
            实心斜坡楔形的trimesh网格
        """
        if not path.points:
            return None

        try:
            meshes = []

            # 分层数量 - 每层0.05mm，斜坡更光滑
            height_diff = abs(z_top - z_bottom)
            num_slices = max(4, min(200, int(height_diff / 0.05) + 1))
            slice_height = height_diff / num_slices

            # ====== 关键：内边缘固定在壁的位置 ======
            if abs(offset_top) < 0.001:
                inner_coords = [(p.x, p.y) for p in path.points]
            else:
                inner_results = self.path_offset.offset(path, offset_top)
                if not inner_results:
                    return None
                inner_coords = [(p.x, p.y) for p in inner_results[0].points]

            # 确保闭合
            if inner_coords[0] != inner_coords[-1]:
                inner_coords.append(inner_coords[0])

            # 对每一层生成环形挤出
            for i in range(num_slices):
                z_low = z_bottom + i * slice_height

                # 外边缘从 offset_bottom 逐渐变化到 offset_top
                t = i / num_slices
                offset_outer = offset_bottom + t * (offset_top - offset_bottom)

                # 获取外边缘坐标
                if abs(offset_outer) < 0.001:
                    outer_coords = [(p.x, p.y) for p in path.points]
                else:
                    outer_results = self.path_offset.offset(path, offset_outer)
                    if not outer_results:
                        continue
                    outer_coords = [(p.x, p.y) for p in outer_results[0].points]

                # 确保闭合
                if outer_coords[0] != outer_coords[-1]:
                    outer_coords.append(outer_coords[0])

                # 检查外边缘和内边缘是否有足够的差异
                # 如果差异太小，跳过这一层（已经接近顶部）
                if abs(offset_outer - offset_top) < 0.01:
                    continue

                # 创建环形多边形
                try:
                    if is_outer:
                        # 外轮廓：外边缘是边界，内边缘是孔
                        ring_polygon = ShapelyPolygon(outer_coords, [inner_coords])
                    else:
                        # 内轮廓（孔）：内边缘是边界，外边缘是孔
                        ring_polygon = ShapelyPolygon(inner_coords, [outer_coords])

                    if not ring_polygon.is_valid:
                        ring_polygon = make_valid(ring_polygon)

                    if ring_polygon.is_empty or ring_polygon.area < 1e-6:
                        continue

                    # 处理可能的MultiPolygon
                    polygons = []
                    if ring_polygon.geom_type == 'MultiPolygon':
                        polygons = list(ring_polygon.geoms)
                    elif ring_polygon.geom_type == 'Polygon':
                        polygons = [ring_polygon]
                    elif ring_polygon.geom_type == 'GeometryCollection':
                        for geom in ring_polygon.geoms:
                            if geom.geom_type == 'Polygon' and geom.area > 1e-6:
                                polygons.append(geom)

                    for poly in polygons:
                        if poly.area > 1e-6:
                            layer_mesh = trimesh.creation.extrude_polygon(poly, slice_height)
                            layer_mesh.apply_translation([0, 0, z_low])
                            meshes.append(layer_mesh)

                except Exception as e:
                    continue

            if not meshes:
                return None

            if len(meshes) == 1:
                return meshes[0]
            else:
                return trimesh.util.concatenate(meshes)

        except Exception as e:
            print(f"警告：创建实心斜坡楔形失败: {e}")
            return None

    def _create_ruled_surface(self, coords1: list, z1: float,
                               coords2: list, z2: float,
                               flip_normals: bool = False) -> Optional[trimesh.Trimesh]:
        """
        创建两个轮廓之间的直纹面

        使用轮廓的参数化（弧长）对应来处理点数不同的情况。

        Args:
            coords1: 第一个轮廓坐标列表
            z1: 第一个轮廓的Z高度
            coords2: 第二个轮廓坐标列表
            z2: 第二个轮廓的Z高度
            flip_normals: 是否翻转法向

        Returns:
            直纹面网格
        """
        import math

        if not coords1 or not coords2:
            return None

        try:
            # 计算轮廓的累积弧长参数
            def compute_arc_params(coords):
                n = len(coords)
                lengths = [0.0]
                for i in range(1, n):
                    dx = coords[i][0] - coords[i-1][0]
                    dy = coords[i][1] - coords[i-1][1]
                    lengths.append(lengths[-1] + math.sqrt(dx*dx + dy*dy))
                # 加上闭合段
                dx = coords[0][0] - coords[-1][0]
                dy = coords[0][1] - coords[-1][1]
                total = lengths[-1] + math.sqrt(dx*dx + dy*dy)
                # 归一化到[0, 1]
                if total > 1e-9:
                    return [l / total for l in lengths], total
                return lengths, 0.0

            params1, total1 = compute_arc_params(coords1)
            params2, total2 = compute_arc_params(coords2)

            if total1 < 1e-9 or total2 < 1e-9:
                return None

            # 使用统一的采样点数
            n_samples = max(len(coords1), len(coords2), 100)

            # 在轮廓上按参数采样
            def sample_point(coords, params, t):
                """在归一化参数t处采样轮廓上的点"""
                n = len(coords)
                t = t % 1.0  # 确保t在[0, 1)范围内

                # 找到t所在的段
                for i in range(n - 1):
                    if params[i] <= t <= params[i + 1]:
                        if params[i + 1] - params[i] < 1e-9:
                            return coords[i]
                        s = (t - params[i]) / (params[i + 1] - params[i])
                        x = coords[i][0] + s * (coords[i + 1][0] - coords[i][0])
                        y = coords[i][1] + s * (coords[i + 1][1] - coords[i][1])
                        return (x, y)

                # t在最后一段（从最后一点到第一点）
                if params[-1] <= t <= 1.0:
                    if 1.0 - params[-1] < 1e-9:
                        return coords[-1]
                    s = (t - params[-1]) / (1.0 - params[-1])
                    x = coords[-1][0] + s * (coords[0][0] - coords[-1][0])
                    y = coords[-1][1] + s * (coords[0][1] - coords[-1][1])
                    return (x, y)

                return coords[0]

            # 生成采样点和面
            vertices = []
            faces = []

            for i in range(n_samples):
                t = i / n_samples
                p1 = sample_point(coords1, params1, t)
                p2 = sample_point(coords2, params2, t)

                # 添加顶点对（底部点和顶部点）
                vertices.append([p1[0], p1[1], z1])
                vertices.append([p2[0], p2[1], z2])

            # 生成三角面
            for i in range(n_samples):
                i_next = (i + 1) % n_samples

                # 当前段的顶点索引
                v1_curr = i * 2      # 底部当前
                v2_curr = i * 2 + 1  # 顶部当前
                v1_next = i_next * 2      # 底部下一个
                v2_next = i_next * 2 + 1  # 顶部下一个

                if flip_normals:
                    # 法向朝内
                    faces.append([v1_curr, v2_next, v1_next])
                    faces.append([v1_curr, v2_curr, v2_next])
                else:
                    # 法向朝外
                    faces.append([v1_curr, v1_next, v2_next])
                    faces.append([v1_curr, v2_next, v2_curr])

            vertices = np.array(vertices)
            faces = np.array(faces)

            return trimesh.Trimesh(vertices=vertices, faces=faces)

        except Exception as e:
            print(f"警告：创建直纹面失败: {e}")
            return None

    def _resample_coords(self, coords: List[tuple], target_n: int) -> List[tuple]:
        """
        重采样坐标点到指定数量

        Args:
            coords: 原始坐标列表 [(x, y), ...]
            target_n: 目标点数

        Returns:
            重采样后的坐标列表
        """
        import math

        if len(coords) == target_n:
            return coords

        # 计算原始路径的累积长度
        lengths = [0.0]
        for i in range(1, len(coords)):
            dx = coords[i][0] - coords[i-1][0]
            dy = coords[i][1] - coords[i-1][1]
            lengths.append(lengths[-1] + math.sqrt(dx*dx + dy*dy))

        # 闭合路径的总长度
        dx = coords[0][0] - coords[-1][0]
        dy = coords[0][1] - coords[-1][1]
        total_length = lengths[-1] + math.sqrt(dx*dx + dy*dy)

        if total_length < 1e-6:
            return coords[:target_n] if len(coords) >= target_n else coords

        # 按等距重采样
        new_coords = []
        for i in range(target_n):
            target_dist = (i / target_n) * total_length

            # 找到对应的线段
            for j in range(len(lengths) - 1):
                if lengths[j] <= target_dist <= lengths[j + 1]:
                    # 在 j 和 j+1 之间插值
                    t = (target_dist - lengths[j]) / (lengths[j + 1] - lengths[j]) if lengths[j + 1] != lengths[j] else 0
                    x = coords[j][0] + t * (coords[j + 1][0] - coords[j][0])
                    y = coords[j][1] + t * (coords[j + 1][1] - coords[j][1])
                    new_coords.append((x, y))
                    break
            else:
                # 在最后一段（回到起点）
                remaining = target_dist - lengths[-1]
                segment_length = total_length - lengths[-1]
                t = remaining / segment_length if segment_length > 0 else 0
                x = coords[-1][0] + t * (coords[0][0] - coords[-1][0])
                y = coords[-1][1] + t * (coords[0][1] - coords[-1][1])
                new_coords.append((x, y))

        return new_coords


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
