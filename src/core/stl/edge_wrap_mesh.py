"""
MINGDA SignMaker - 包边/勾边网格生成器

生成包边和勾边的3D网格：
- 包边：矩形截面，围绕字壳轮廓的环形带
- 勾边：斜坡/楔形截面，下大上小
"""

from __future__ import annotations
from typing import List, Optional

import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid

from ..types import (
    Contour, SliceResult, SliceParams, Point,
    EdgeDirection
)
from ..types import Path as CorePath
from ..path_offset import PathOffset
from .mesh_utils import MeshUtils


class EdgeWrapMeshBuilder:
    """包边勾边网格生成器"""

    def __init__(self, path_offset: PathOffset, wall_thickness: float = 1.2):
        """
        初始化包边勾边网格生成器

        Args:
            path_offset: 路径偏移工具
            wall_thickness: 壁厚（mm）
        """
        self.path_offset = path_offset
        self.wall_thickness = wall_thickness
        self.mesh_utils = MeshUtils()

    def build_wrap(self, contours: List[Contour], result: SliceResult,
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

        Args:
            contours: 轮廓列表
            result: 切片结果
            params: 切片参数

        Returns:
            包边网格
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
                    inner_wall_results = self.path_offset.offset(
                        contour.outer, -self.wall_thickness
                    )
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
                                mesh = self.mesh_utils.extrude_polygon(
                                    geom, wrap_height, wrap_z_start
                                )
                                if mesh is not None:
                                    meshes.append(mesh)
                    elif wrap_polygon.geom_type == 'Polygon':
                        mesh = self.mesh_utils.extrude_polygon(
                            wrap_polygon, wrap_height, wrap_z_start
                        )
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
                            hole_inner_wall_results = self.path_offset.offset(
                                hole, self.wall_thickness
                            )
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
                                    mesh = self.mesh_utils.extrude_polygon(
                                        geom, wrap_height, wrap_z_start
                                    )
                                    if mesh is not None:
                                        meshes.append(mesh)
                        elif hole_wrap_polygon.geom_type == 'Polygon':
                            mesh = self.mesh_utils.extrude_polygon(
                                hole_wrap_polygon, wrap_height, wrap_z_start
                            )
                            if mesh is not None:
                                meshes.append(mesh)

                    except Exception as e:
                        print(f"警告：创建内孔包边失败: {e}")
                        continue

            except Exception as e:
                print(f"警告：处理轮廓包边失败: {e}")
                continue

        return MeshUtils.merge_meshes(meshes)

    def build_outline(self, contours: List[Contour], result: SliceResult,
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

        Args:
            contours: 轮廓列表
            result: 切片结果
            params: 切片参数

        Returns:
            勾边网格
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

        for contour in contours:
            try:
                outer_points = contour.outer.points
                if not outer_points:
                    continue

                # 计算外轮廓的勾边偏移
                if outline_direction == EdgeDirection.INNER:
                    # 内部勾边：从内壁边缘开始
                    offset_bottom = -(self.wall_thickness + outline_offset + outline_width)
                    offset_top = -(self.wall_thickness + outline_offset)
                else:
                    # 外部勾边：从外壁边缘开始
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

        return MeshUtils.merge_meshes(meshes)

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

                except Exception:
                    continue

            return MeshUtils.merge_meshes(meshes)

        except Exception as e:
            print(f"警告：创建实心斜坡楔形失败: {e}")
            return None
