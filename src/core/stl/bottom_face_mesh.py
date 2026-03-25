"""
MINGDA SignMaker - 底面封闭网格生成器

生成底面封闭的3D网格。
底面封闭是一个实心平面，位于字壳底部，填满字壳内部空间。
"""

from __future__ import annotations
from typing import List, Optional

import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid

from ..light_slot_geometry import LightSlotGeometryBuilder
from ..types import Contour, SliceParams, EdgeType, BevelDirection
from ..path_offset import PathOffset
from .mesh_utils import MeshUtils


class BottomFaceMeshBuilder:
    """底面封闭网格生成器"""

    def __init__(self, path_offset: PathOffset):
        """
        初始化底面封闭网格生成器

        Args:
            path_offset: 路径偏移工具
        """
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()
        self.light_slot_geometry_builder = LightSlotGeometryBuilder(path_offset)

    def build(self, contours: List[Contour],
              params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建底面封闭网格

        底面封闭是一个实心平面，位于字壳底部 z=0 到 z=thickness。
        使用轮廓的内缩版本（减去壁厚）生成实心底面，填满字壳内部空间。

        Args:
            contours: 已经过边缘变换的轮廓列表（z=0处）
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

        if params.light_slot.enabled:
            for contour in contours:
                try:
                    geometry = self.light_slot_geometry_builder.build(contour, params)
                    for polygon in geometry.center_fill_polygons:
                        mesh = self.mesh_utils.extrude_polygon(polygon, thickness, z_offset=0)
                        if mesh is not None:
                            meshes.append(mesh)
                except Exception as e:
                    print(f"警告：处理灯槽共存底面失败: {e}")
                    continue

            return MeshUtils.merge_meshes(meshes)

        # 计算内缩距离（所有壁的总宽度）
        wall_thickness = params.shell.wall_thickness
        wall_count = params.shell.wall_count
        inset_distance = wall_thickness * wall_count

        for contour in contours:
            try:
                # 内缩外轮廓
                inset_outer = self.path_offset.offset(contour.outer, -inset_distance)
                if not inset_outer:
                    continue

                for outer_path in inset_outer:
                    outer_coords = [(p.x, p.y) for p in outer_path.points]
                    if len(outer_coords) < 3:
                        continue

                    # 内缩内孔（使用负偏移，和墙壁生成保持一致）
                    hole_coords_list = []
                    for hole in contour.holes:
                        # 内孔也向内收缩（负偏移），和墙壁生成方向一致
                        inset_holes = self.path_offset.offset(hole, -inset_distance)
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
                                    mesh = self.mesh_utils.extrude_polygon(
                                        geom, thickness, z_offset=0
                                    )
                                    if mesh is not None:
                                        meshes.append(mesh)
                        else:
                            mesh = self.mesh_utils.extrude_polygon(
                                polygon, thickness, z_offset=0
                            )
                            if mesh is not None:
                                meshes.append(mesh)

                    except Exception as e:
                        print(f"警告：创建底面多边形失败: {e}")
                        continue

            except Exception as e:
                print(f"警告：处理轮廓底面失败: {e}")
                continue

        return MeshUtils.merge_meshes(meshes)
