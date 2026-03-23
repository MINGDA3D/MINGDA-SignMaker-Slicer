"""
MINGDA SignMaker - 包边/勾边网格生成器

生成包边和勾边的3D网格：
- 包边：矩形截面，围绕字壳轮廓的环形带
- 勾边：斜坡/楔形截面，下窄上宽
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
        - 位置：字壳底板区域（从 z=0 到 wrap_height）
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

        # 包边固定生成在底板区域，直接从 z=0 向上生长
        wrap_z_start = 0.0

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
                        hole_rings = self._build_hole_wrap_rings(
                            hole, wrap_width, wrap_direction
                        )
                        if not hole_rings:
                            continue
                        hole_outer_ring, hole_inner_ring = hole_rings

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
        - 勾边：斜坡/楔形截面，下窄上宽

        方向选择：
        - 内部（INNER）：从内壁向内延伸
        - 外部（OUTER）：从外壁向外延伸

        勾边的3D结构（侧视图）- 下窄上宽：

        z=outline_height ──╱──┤        ├──╲  ← 勾边顶部（向外/内放宽）
                         ╱  │   壁   │  ╲
                        ╱   │        │   ╲
        z=0            ────┴────────┴────  ← 勾边底部（贴墙起步）

        底部：与壁边缘齐平
        顶部：延伸 outline_width

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

        # 勾边固定生成在底板区域，顶部与底板包边高度一致
        z_bottom = 0.0
        z_top = outline_height

        meshes = []

        for contour in contours:
            try:
                outer_points = contour.outer.points
                if not outer_points:
                    continue

                # 计算外轮廓的勾边偏移
                if outline_direction == EdgeDirection.INNER:
                    # 内部勾边：底部贴内壁，向上逐渐向内放宽
                    offset_bottom = -(self.wall_thickness + outline_offset)
                    offset_top = -(self.wall_thickness + outline_offset + outline_width)
                else:
                    # 外部勾边：底部贴外壁，向上逐渐向外放宽
                    offset_bottom = outline_offset
                    offset_top = outline_offset + outline_width

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
                    hole_offset_bottom, hole_offset_top = self._get_hole_outline_offsets(
                        outline_width, outline_offset, outline_direction
                    )

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

        关键：基准边缘固定在底部贴墙位置（offset_bottom），只有外扩边缘逐渐变化。
        这样形成的是一个实心的楔形，而不是空心的壳。

        楔形截面示意：
            外边缘（最宽）
               ↑
            ┌──────╱ ← 顶部
            │     ╱
            │    ╱  ← 斜坡（外边缘逐渐变化）
            │   ╱
            └──┘ ← 底部
               ↓
            基准边缘（固定）

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

            # 分层数量同时受高度和横向扩张量约束：
            # 这样可以让底部更贴墙，避免首层就出现明显外扩。
            height_diff = abs(z_top - z_bottom)
            offset_diff = abs(offset_top - offset_bottom)
            num_slices = max(
                4,
                min(400, int(max(height_diff / 0.02, offset_diff / 0.02)) + 1)
            )
            slice_height = height_diff / num_slices

            # ====== 关键：底部贴墙的基准边缘固定不动 ======
            if abs(offset_bottom) < 0.001:
                base_coords = [(p.x, p.y) for p in path.points]
            else:
                base_results = self.path_offset.offset(path, offset_bottom)
                if not base_results:
                    return None
                base_coords = [(p.x, p.y) for p in base_results[0].points]

            # 确保闭合
            if base_coords[0] != base_coords[-1]:
                base_coords.append(base_coords[0])

            # 对每一层生成环形挤出
            for i in range(num_slices):
                z_low = z_bottom + i * slice_height

                # 外扩边缘从底部基准逐渐变化到顶部最终宽度。
                # 使用上边界插值，确保最顶层能达到完整 outline_width。
                t = (i + 1) / num_slices
                offset_outer = offset_bottom + t * (offset_top - offset_bottom)

                # 获取变化边缘坐标
                if abs(offset_outer) < 0.001:
                    current_coords = [(p.x, p.y) for p in path.points]
                else:
                    current_results = self.path_offset.offset(path, offset_outer)
                    if not current_results:
                        continue
                    current_coords = [(p.x, p.y) for p in current_results[0].points]

                # 确保闭合
                if current_coords[0] != current_coords[-1]:
                    current_coords.append(current_coords[0])

                # 检查变化边缘和基准边缘是否有足够的差异
                if abs(offset_outer - offset_bottom) < 1e-4:
                    continue

                # 创建环形多边形
                try:
                    base_polygon = ShapelyPolygon(base_coords)
                    current_polygon = ShapelyPolygon(current_coords)

                    if not base_polygon.is_valid:
                        base_polygon = make_valid(base_polygon)
                    if not current_polygon.is_valid:
                        current_polygon = make_valid(current_polygon)

                    if base_polygon.is_empty or current_polygon.is_empty:
                        continue

                    if base_polygon.area >= current_polygon.area:
                        ring_polygon = base_polygon.difference(current_polygon)
                    else:
                        ring_polygon = current_polygon.difference(base_polygon)

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

    def _build_hole_wrap_rings(self, hole: CorePath, wrap_width: float,
                               wrap_direction: EdgeDirection):
        """计算内孔包边的外环/内环坐标。内孔方向语义与外轮廓相反。"""
        if wrap_direction == EdgeDirection.INNER:
            inner_ring = self._closed_coords(hole)
            wrap_results = self.path_offset.offset(hole, wrap_width)
            if not wrap_results:
                return None
            outer_ring = self._closed_coords(wrap_results[0])
            return outer_ring, inner_ring

        hole_wall_results = self.path_offset.offset(hole, -self.wall_thickness)
        if not hole_wall_results:
            return None

        hole_wall = hole_wall_results[0]
        outer_ring = self._closed_coords(hole_wall)
        wrap_results = self.path_offset.offset(hole_wall, -wrap_width)
        if not wrap_results:
            return None
        inner_ring = self._closed_coords(wrap_results[0])
        return outer_ring, inner_ring

    def _get_hole_outline_offsets(self, outline_width: float,
                                  outline_offset: float,
                                  outline_direction: EdgeDirection) -> tuple[float, float]:
        """计算内孔勾边底部/顶部偏移。内孔方向语义与外轮廓相反。"""
        if outline_direction == EdgeDirection.INNER:
            return (
                outline_offset,
                outline_offset + outline_width,
            )
        return (
            -(self.wall_thickness + outline_offset),
            -(self.wall_thickness + outline_offset + outline_width),
        )

    @staticmethod
    def _closed_coords(path: CorePath) -> List[tuple[float, float]]:
        coords = [(p.x, p.y) for p in path.points]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords
