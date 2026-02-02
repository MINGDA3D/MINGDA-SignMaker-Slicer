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
    SliceResult, SliceParams, EdgeWrapParams, EdgeDirection,
    ConnectedParams, EdgeType, BevelDirection, EdgeProfile
)
from .path_offset import PathOffset
from .types import Path as CorePath
from .skirt_generator import SkirtGenerator, TrapezoidSkirt
from .connected_generator import ConnectedGenerator, ConnectionBridge


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
        self.skirt_generator = SkirtGenerator()
        self.connected_generator = ConnectedGenerator()

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

        # 如果启用了台阶，添加台阶网格
        if contours and params:
            step_mesh = self._build_step_mesh(contours, result, params)
            if step_mesh is not None:
                combined_mesh = trimesh.util.concatenate([combined_mesh, step_mesh])

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

        # 如果启用了防翘裙边，添加裙边网格
        if contours and params and params.skirt.enabled:
            skirt_mesh = self._build_skirt_mesh(contours, params)
            if skirt_mesh is not None:
                combined_mesh = trimesh.util.concatenate([combined_mesh, skirt_mesh])

        # 如果启用了连襟字，添加连襟网格
        if contours and params and params.connected.enabled:
            connected_mesh = self._build_connected_mesh(contours, params)
            if connected_mesh is not None:
                combined_mesh = trimesh.util.concatenate([combined_mesh, connected_mesh])

        # 如果启用了底面封闭，添加底面网格
        if contours and params and params.bottom_face.enabled:
            bottom_face_mesh = self._build_bottom_face_mesh(contours, params)
            if bottom_face_mesh is not None:
                combined_mesh = trimesh.util.concatenate([combined_mesh, bottom_face_mesh])

        # 写入文件
        if binary:
            combined_mesh.export(output_path, file_type='stl')
        else:
            combined_mesh.export(output_path, file_type='stl_ascii')

    def _build_hollow_mesh(self, layers: List[Layer]) -> Optional[trimesh.Trimesh]:
        """
        构建空心字壳网格

        算法（支持斜边变化轮廓）：
        1. 收集所有层的WALL路径
        2. 对每一层生成外轮廓和内轮廓
        3. 逐层挤出生成3D网格
        4. 合并所有层的网格
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
                                mesh = self._extrude_polygon(geom, layer_height, z_bottom)
                                if mesh is not None:
                                    meshes.append(mesh)
                    elif polygon.geom_type == 'Polygon':
                        mesh = self._extrude_polygon(polygon, layer_height, z_bottom)
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

    def _build_step_mesh(self, contours: List[Contour],
                          result: SliceResult,
                          params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建台阶网格

        台阶是在字壳内侧向内凸出的环形薄平台，用于支撑面板或底板。
        台阶只有一层厚度（step_thickness），不是一个高度很大的块。

        台阶结构（截面图）：
            ┌──────────────────────┐  ← 顶部 (total_height)
            │                      │
            │  ┌────────────────┐  │  ← 面板台阶位置 (total_height - panel_step_height)
            │  │  ← 薄薄一层    │  │     面板放在这个平台上
            │  │                │  │
            │  │    空心部分    │  │  ← 字壳主体
            │  │                │  │
            │  │  ← 薄薄一层    │  │     底板放在这个平台上
            │  └────────────────┘  │  ← 底板台阶位置 (baseplate_step_height)
            │                      │
            └──────────────────────┘  ← 底部 (0)

        Args:
            contours: 原始轮廓列表
            result: 切片结果
            params: 切片参数

        Returns:
            台阶网格
        """
        meshes = []
        total_height = params.shell.height
        wall_thickness = params.shell.wall_thickness

        # 台阶厚度（一层高度）
        step_thickness = params.step.step_thickness if params.step.step_thickness > 0 else 0.3

        for contour in contours:
            try:
                outer_points = contour.outer.points
                if not outer_points:
                    continue

                # 计算壁的内边缘（从中心线向内偏移半个壁厚）
                # 或者使用完整的内壁偏移
                inner_wall_results = self.path_offset.offset(contour.outer, -wall_thickness)
                if not inner_wall_results:
                    continue

                inner_wall_coords = [(p.x, p.y) for p in inner_wall_results[0].points]
                if inner_wall_coords[0] != inner_wall_coords[-1]:
                    inner_wall_coords.append(inner_wall_coords[0])

                # ===== 面板台阶（顶部）=====
                # 位置：用户直接设置的高度值
                if params.step.panel_step_enabled:
                    panel_z = params.step.panel_step_height
                    # 验证高度是否合法
                    if panel_z >= total_height:
                        print(f"警告：面板台阶高度({panel_z}mm)超过模型高度({total_height}mm)，跳过")
                    elif panel_z < 0:
                        print(f"警告：面板台阶高度({panel_z}mm)不能为负数，跳过")
                    else:
                        panel_mesh = self._create_thin_step_ring(
                            inner_wall_coords,
                            step_width=params.step.panel_step_width,
                            step_thickness=step_thickness,
                            z_position=panel_z,
                            is_hole=False
                        )
                        if panel_mesh is not None:
                            meshes.append(panel_mesh)

                # ===== 底板台阶（底部）=====
                # 位置：用户直接设置的高度值
                if params.step.baseplate_step_enabled:
                    baseplate_z = params.step.baseplate_step_height
                    # 验证高度是否合法
                    if baseplate_z >= total_height:
                        print(f"警告：底板台阶高度({baseplate_z}mm)超过模型高度({total_height}mm)，跳过")
                    elif baseplate_z < 0:
                        print(f"警告：底板台阶高度({baseplate_z}mm)不能为负数，跳过")
                    else:
                        baseplate_mesh = self._create_thin_step_ring(
                            inner_wall_coords,
                            step_width=params.step.baseplate_step_width,
                            step_thickness=step_thickness,
                            z_position=baseplate_z,
                            is_hole=False
                        )
                        if baseplate_mesh is not None:
                            meshes.append(baseplate_mesh)

                # ===== 处理内孔的台阶 =====
                for hole in contour.holes:
                    # 内孔的壁内边缘（向外偏移）
                    hole_inner_results = self.path_offset.offset(hole, wall_thickness)
                    if not hole_inner_results:
                        continue

                    hole_inner_coords = [(p.x, p.y) for p in hole_inner_results[0].points]
                    if hole_inner_coords[0] != hole_inner_coords[-1]:
                        hole_inner_coords.append(hole_inner_coords[0])

                    # 面板台阶（内孔）
                    if params.step.panel_step_enabled:
                        panel_z = params.step.panel_step_height
                        if 0 <= panel_z < total_height:
                            hole_panel_mesh = self._create_thin_step_ring(
                                hole_inner_coords,
                                step_width=params.step.panel_step_width,
                                step_thickness=step_thickness,
                                z_position=panel_z,
                                is_hole=True
                            )
                            if hole_panel_mesh is not None:
                                meshes.append(hole_panel_mesh)

                    # 底板台阶（内孔）
                    if params.step.baseplate_step_enabled:
                        baseplate_z = params.step.baseplate_step_height
                        if 0 <= baseplate_z < total_height:
                            hole_baseplate_mesh = self._create_thin_step_ring(
                                hole_inner_coords,
                                step_width=params.step.baseplate_step_width,
                                step_thickness=step_thickness,
                                z_position=baseplate_z,
                                is_hole=True
                            )
                            if hole_baseplate_mesh is not None:
                                meshes.append(hole_baseplate_mesh)

            except Exception as e:
                print(f"警告：处理轮廓台阶失败: {e}")
                continue

        if not meshes:
            return None

        if len(meshes) == 1:
            return meshes[0]
        else:
            return trimesh.util.concatenate(meshes)

    def _create_thin_step_ring(self, wall_inner_coords: list,
                                step_width: float,
                                step_thickness: float,
                                z_position: float,
                                is_hole: bool = False) -> Optional[trimesh.Trimesh]:
        """
        创建薄台阶环形网格

        台阶是一个薄的环形实心体：
        - 外边缘：壁的内边缘
        - 内边缘：壁的内边缘向内偏移step_width
        - 厚度：step_thickness（很薄，如0.3mm）

        Args:
            wall_inner_coords: 壁内边缘坐标列表
            step_width: 台阶宽度（向内延伸的距离）
            step_thickness: 台阶厚度
            z_position: 台阶底部Z位置
            is_hole: 是否是内孔的台阶（方向相反）

        Returns:
            台阶网格
        """
        try:
            from .types import Point

            # 外边缘坐标
            outer_ring_coords = wall_inner_coords

            # 计算内边缘（向内偏移step_width）
            outer_path = CorePath(points=[Point(c[0], c[1]) for c in wall_inner_coords[:-1]])

            if is_hole:
                # 内孔的台阶：向孔内延伸（正偏移，让孔变小）
                # 内孔的"内部"是孔的中心方向，所以用正偏移
                inner_results = self.path_offset.offset(outer_path, step_width)
            else:
                # 外轮廓的台阶：向字壳内部延伸（负偏移）
                inner_results = self.path_offset.offset(outer_path, -step_width)

            if not inner_results:
                return None

            inner_ring_coords = [(p.x, p.y) for p in inner_results[0].points]
            if inner_ring_coords[0] != inner_ring_coords[-1]:
                inner_ring_coords.append(inner_ring_coords[0])

            # 创建环形多边形
            # 对于外轮廓：outer_ring_coords 是外边界，inner_ring_coords 是内孔
            # 对于内孔：由于正偏移，inner_ring_coords 更小，所以它是孔
            #          outer_ring_coords 是壁内边缘，是外边界
            # 两种情况的多边形构建方式相同
            ring_polygon = ShapelyPolygon(outer_ring_coords, [inner_ring_coords])

            if not ring_polygon.is_valid:
                ring_polygon = make_valid(ring_polygon)

            if ring_polygon.is_empty or ring_polygon.area < 1e-6:
                return None

            # 处理可能的几何类型
            meshes = []
            if ring_polygon.geom_type == 'MultiPolygon':
                for geom in ring_polygon.geoms:
                    if geom.area > 1e-6:
                        mesh = self._extrude_polygon(geom, step_thickness, z_position)
                        if mesh is not None:
                            meshes.append(mesh)
            elif ring_polygon.geom_type == 'Polygon':
                mesh = self._extrude_polygon(ring_polygon, step_thickness, z_position)
                if mesh is not None:
                    meshes.append(mesh)
            elif ring_polygon.geom_type == 'GeometryCollection':
                for geom in ring_polygon.geoms:
                    if geom.geom_type == 'Polygon' and geom.area > 1e-6:
                        mesh = self._extrude_polygon(geom, step_thickness, z_position)
                        if mesh is not None:
                            meshes.append(mesh)

            if not meshes:
                return None

            if len(meshes) == 1:
                return meshes[0]
            else:
                return trimesh.util.concatenate(meshes)

        except Exception as e:
            print(f"警告：创建台阶网格失败: {e}")
            return None

    def _build_skirt_mesh(self, contours: List[Contour],
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
                    from copy import copy
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

        if not meshes:
            return None

        if len(meshes) == 1:
            return meshes[0]
        else:
            return trimesh.util.concatenate(meshes)

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
            # 创建连续的3条边路径（不闭合）
            # 顺序：top_right -> bottom_right -> bottom_left -> top_left
            path_points = [
                (trap.top_right.x, trap.top_right.y),
                (trap.bottom_right.x, trap.bottom_right.y),
                (trap.bottom_left.x, trap.bottom_left.y),
                (trap.top_left.x, trap.top_left.y),
            ]

            return self._create_continuous_wall(path_points, 0, height, wall_thickness)

        except Exception as e:
            print(f"Warning: Failed to create trapezoid mesh: {e}")
            return None

    def _create_continuous_wall(self, path_points: list,
                                 z_bottom: float, z_top: float,
                                 thickness: float) -> Optional[trimesh.Trimesh]:
        """
        沿路径创建连续的薄壁结构，转角处平滑连接

        Args:
            path_points: 路径点列表 [(x, y), ...]
            z_bottom: 底部Z坐标
            z_top: 顶部Z坐标
            thickness: 壁厚

        Returns:
            连续墙壁网格
        """
        import math

        n = len(path_points)
        if n < 2:
            return None

        half_t = thickness / 2
        vertices = []
        faces = []

        # 计算每个点的平均法线（用于平滑转角）
        normals = []
        for i in range(n):
            # 计算当前点的法线
            if i == 0:
                # 第一个点：只用下一段的法线
                dx = path_points[1][0] - path_points[0][0]
                dy = path_points[1][1] - path_points[0][1]
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0.001:
                    nx, ny = -dy / length, dx / length
                else:
                    nx, ny = 0, 1
            elif i == n - 1:
                # 最后一个点：只用上一段的法线
                dx = path_points[n-1][0] - path_points[n-2][0]
                dy = path_points[n-1][1] - path_points[n-2][1]
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0.001:
                    nx, ny = -dy / length, dx / length
                else:
                    nx, ny = 0, 1
            else:
                # 中间点：使用相邻两段的平均法线
                # 前一段
                dx1 = path_points[i][0] - path_points[i-1][0]
                dy1 = path_points[i][1] - path_points[i-1][1]
                len1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
                if len1 > 0.001:
                    nx1, ny1 = -dy1 / len1, dx1 / len1
                else:
                    nx1, ny1 = 0, 1

                # 后一段
                dx2 = path_points[i+1][0] - path_points[i][0]
                dy2 = path_points[i+1][1] - path_points[i][1]
                len2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
                if len2 > 0.001:
                    nx2, ny2 = -dy2 / len2, dx2 / len2
                else:
                    nx2, ny2 = 0, 1

                # 平均法线
                nx = (nx1 + nx2) / 2
                ny = (ny1 + ny2) / 2
                avg_len = math.sqrt(nx * nx + ny * ny)
                if avg_len > 0.001:
                    nx /= avg_len
                    ny /= avg_len

            normals.append((nx, ny))

        # 为每个点生成4个顶点（内外两侧，上下两层）
        for i in range(n):
            x, y = path_points[i]
            nx, ny = normals[i]

            # 外侧底层
            vertices.append([x + nx * half_t, y + ny * half_t, z_bottom])
            # 外侧顶层
            vertices.append([x + nx * half_t, y + ny * half_t, z_top])
            # 内侧底层
            vertices.append([x - nx * half_t, y - ny * half_t, z_bottom])
            # 内侧顶层
            vertices.append([x - nx * half_t, y - ny * half_t, z_top])

        # 生成面（连接相邻点）
        for i in range(n - 1):
            base = i * 4
            next_base = (i + 1) * 4

            # 外侧面
            faces.append([base + 0, next_base + 0, next_base + 1])
            faces.append([base + 0, next_base + 1, base + 1])

            # 内侧面
            faces.append([base + 2, base + 3, next_base + 3])
            faces.append([base + 2, next_base + 3, next_base + 2])

            # 顶面
            faces.append([base + 1, next_base + 1, next_base + 3])
            faces.append([base + 1, next_base + 3, base + 3])

            # 底面
            faces.append([base + 0, base + 2, next_base + 2])
            faces.append([base + 0, next_base + 2, next_base + 0])

        # 添加两端的封口面
        # 起始端
        faces.append([0, 1, 3])
        faces.append([0, 3, 2])

        # 结束端
        end_base = (n - 1) * 4
        faces.append([end_base + 0, end_base + 2, end_base + 3])
        faces.append([end_base + 0, end_base + 3, end_base + 1])

        vertices = np.array(vertices)
        faces = np.array(faces)

        return trimesh.Trimesh(vertices=vertices, faces=faces)

    def _create_wall_segment(self, x1: float, y1: float, x2: float, y2: float,
                              z_bottom: float, z_top: float,
                              thickness: float) -> Optional[trimesh.Trimesh]:
        """
        创建一段墙壁（薄壁矩形）

        Args:
            x1, y1: 起点
            x2, y2: 终点
            z_bottom: 底部Z坐标
            z_top: 顶部Z坐标
            thickness: 壁厚

        Returns:
            墙壁网格
        """
        import math

        # 计算边的方向
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)

        if length < 0.001:
            return None

        # 归一化方向
        dx /= length
        dy /= length

        # 法线方向（垂直于边）
        nx = -dy
        ny = dx

        # 半壁厚
        half_t = thickness / 2

        # 8个顶点（内外两侧，上下两层）
        vertices = np.array([
            # 外侧底层
            [x1 + nx * half_t, y1 + ny * half_t, z_bottom],  # 0
            [x2 + nx * half_t, y2 + ny * half_t, z_bottom],  # 1
            # 外侧顶层
            [x1 + nx * half_t, y1 + ny * half_t, z_top],     # 2
            [x2 + nx * half_t, y2 + ny * half_t, z_top],     # 3
            # 内侧底层
            [x1 - nx * half_t, y1 - ny * half_t, z_bottom],  # 4
            [x2 - nx * half_t, y2 - ny * half_t, z_bottom],  # 5
            # 内侧顶层
            [x1 - nx * half_t, y1 - ny * half_t, z_top],     # 6
            [x2 - nx * half_t, y2 - ny * half_t, z_top],     # 7
        ])

        # 12个三角面
        faces = np.array([
            # 外侧面
            [0, 1, 3],
            [0, 3, 2],
            # 内侧面
            [4, 6, 7],
            [4, 7, 5],
            # 顶面
            [2, 3, 7],
            [2, 7, 6],
            # 底面
            [0, 4, 5],
            [0, 5, 1],
            # 左端面
            [0, 2, 6],
            [0, 6, 4],
            # 右端面
            [1, 5, 7],
            [1, 7, 3],
        ])

        return trimesh.Trimesh(vertices=vertices, faces=faces)

    def _build_connected_mesh(self, contours: List[Contour],
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
            bridge_mesh = self._create_bridge_mesh(bridge, connected_params)
            if bridge_mesh is not None:
                meshes.append(bridge_mesh)

        if not meshes:
            return None

        if len(meshes) == 1:
            return meshes[0]
        else:
            return trimesh.util.concatenate(meshes)

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
            # 上小下大：底部不收缩，向上逐渐收缩
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
            # 上大下小：底部收缩，向上逐渐扩展
            if z < baseplate_top:
                return -bevel_width
            elif z < panel_bottom:
                bevel_height = panel_bottom - baseplate_top
                if bevel_height > 0:
                    progress = (z - baseplate_top) / bevel_height
                    return -bevel_width * (1 - progress)
                return 0
            else:
                return 0

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
        from .types import JoinType

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

    def _create_bridge_mesh(self, bridge: ConnectionBridge,
                             params: ConnectedParams) -> Optional[trimesh.Trimesh]:
        """
        为单个连接桥创建3D网格

        根据连襟类型生成不同形状：
        - 三角形：底部宽，顶部收窄为线
        - 菱形：中间窄，两端宽

        Args:
            bridge: 连接桥数据
            params: 连襟参数

        Returns:
            连接桥网格
        """
        import math

        if not bridge.corners or len(bridge.corners) < 4:
            return None

        try:
            # 获取连襟尺寸参数
            base_height = params.base_height  # 底座高度
            bevel_height = params.height       # 斜边高度
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
            layer_height = 0.3  # 每层高度
            num_layers = max(1, int(total_height / layer_height))

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

            if not meshes:
                return None

            if len(meshes) == 1:
                return meshes[0]
            else:
                return trimesh.util.concatenate(meshes)

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

    def _build_bottom_face_mesh(self, contours: List[Contour],
                                 params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建底面封闭网格

        底面封闭是一个实心平面，位于字壳底部 z=0 到 z=thickness。
        使用轮廓的内缩版本（减去壁厚）生成实心底面，填满字壳内部空间。

        Args:
            contours: 轮廓列表
            params: 切片参数

        Returns:
            底面网格，如果生成失败则返回None
        """
        if not contours:
            return None

        bottom_face = params.bottom_face
        if not bottom_face.enabled or bottom_face.thickness <= 0:
            return None

        meshes = []
        thickness = bottom_face.thickness

        # 计算内缩距离（所有壁的总宽度）
        wall_thickness = params.shell.wall_thickness
        wall_count = params.shell.wall_count
        inset_distance = wall_thickness * wall_count

        for contour in contours:
            try:
                # 获取底部轮廓（考虑斜边等边缘类型）
                bottom_contour = self._get_bottom_contour(contour, params)
                if not bottom_contour:
                    continue

                # 内缩外轮廓
                inset_outer = self.path_offset.offset(bottom_contour.outer, -inset_distance)
                if not inset_outer:
                    continue

                for outer_path in inset_outer:
                    outer_coords = [(p.x, p.y) for p in outer_path.points]
                    if len(outer_coords) < 3:
                        continue

                    # 内缩内孔
                    hole_coords_list = []
                    for hole in bottom_contour.holes:
                        # 内孔需要向外扩展（正偏移）以保持正确的孔形状
                        inset_holes = self.path_offset.offset(hole, inset_distance)
                        for inset_hole in inset_holes:
                            hole_coords = [(p.x, p.y) for p in inset_hole.points]
                            if len(hole_coords) >= 3:
                                hole_coords_list.append(hole_coords)

                    # 创建Shapely多边形
                    try:
                        if hole_coords_list:
                            polygon = ShapelyPolygon(outer_coords, hole_coords_list)
                        else:
                            polygon = ShapelyPolygon(outer_coords)

                        # 验证多边形
                        if not polygon.is_valid:
                            polygon = make_valid(polygon)

                        if polygon.is_empty or polygon.area < 1e-6:
                            continue

                        # 处理MultiPolygon情况
                        if polygon.geom_type == 'MultiPolygon':
                            for geom in polygon.geoms:
                                if geom.area >= 1e-6:
                                    mesh = self._extrude_polygon(geom, thickness, z_offset=0)
                                    if mesh is not None:
                                        meshes.append(mesh)
                        else:
                            mesh = self._extrude_polygon(polygon, thickness, z_offset=0)
                            if mesh is not None:
                                meshes.append(mesh)

                    except Exception as e:
                        print(f"警告：创建底面多边形失败: {e}")
                        continue

            except Exception as e:
                print(f"警告：处理轮廓底面失败: {e}")
                continue

        if not meshes:
            return None

        if len(meshes) == 1:
            return meshes[0]
        else:
            return trimesh.util.concatenate(meshes)

    def _get_bottom_contour(self, contour: Contour,
                            params: SliceParams) -> Optional[Contour]:
        """
        获取底部轮廓

        对于斜边和异形边，底部轮廓可能与原始轮廓不同。

        Args:
            contour: 原始轮廓
            params: 切片参数

        Returns:
            底部轮廓
        """
        edge_type = params.shell.edge_type

        if edge_type == EdgeType.STRAIGHT:
            # 直边：直接使用原始轮廓
            return contour

        elif edge_type == EdgeType.BEVELED:
            # 斜边：根据方向确定底部轮廓
            bevel_direction = params.shell.bevel_direction
            bevel_width = params.shell.bevel_width

            if bevel_direction == BevelDirection.TOP_SMALL:
                # 上小下大：底部是最大的，不需要偏移
                return contour
            else:
                # 上大下小：底部是最小的，需要内缩
                offset_outer = self.path_offset.offset(contour.outer, -bevel_width)
                if not offset_outer:
                    return None

                offset_holes = []
                for hole in contour.holes:
                    offset_hole = self.path_offset.offset(hole, -bevel_width)
                    offset_holes.extend(offset_hole)

                return Contour(
                    outer=offset_outer[0],
                    holes=offset_holes,
                    name=contour.name
                )

        elif edge_type == EdgeType.CUSTOM:
            # 异形边：根据轮廓在z=0处的偏移量
            profile = params.shell.edge_profile
            if profile and profile.control_points:
                offset = profile.get_offset_at_height(0, params.shell.bevel_width,
                                                       params.shell.height)
                if abs(offset) > 0.001:
                    offset_outer = self.path_offset.offset(contour.outer, offset)
                    if not offset_outer:
                        return None

                    offset_holes = []
                    for hole in contour.holes:
                        offset_hole = self.path_offset.offset(hole, offset)
                        offset_holes.extend(offset_hole)

                    return Contour(
                        outer=offset_outer[0],
                        holes=offset_holes,
                        name=contour.name
                    )
            return contour

        return contour


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
