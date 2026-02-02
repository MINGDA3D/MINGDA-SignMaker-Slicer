"""
SignMaker Slicer - 顶面封闭网格生成器

生成顶面封闭的3D网格。
顶面封闭是一个实心平面，位于字壳顶部，填满字壳内部空间。
"""

from __future__ import annotations
from typing import List, Optional

import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid

from ..types import Contour, SliceParams, EdgeType, BevelDirection
from ..path_offset import PathOffset
from .mesh_utils import MeshUtils


class TopFaceMeshBuilder:
    """顶面封闭网格生成器"""

    def __init__(self, path_offset: PathOffset):
        """
        初始化顶面封闭网格生成器

        Args:
            path_offset: 路径偏移工具
        """
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()

    def build(self, contours: List[Contour],
              params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建顶面封闭网格

        顶面封闭是一个实心平面，位于字壳顶部。
        z位置从 (total_height - thickness) 到 total_height。
        使用轮廓的内缩版本（减去壁厚）生成实心顶面，填满字壳内部空间。

        Args:
            contours: 轮廓列表
            params: 切片参数

        Returns:
            顶面网格，如果生成失败则返回None
        """
        if not contours:
            return None

        top_face = params.top_face
        if not top_face.enabled or top_face.thickness <= 0:
            return None

        meshes = []
        thickness = top_face.thickness
        total_height = params.shell.height

        # 顶面的Z起始位置
        z_start = total_height - thickness

        # 计算内缩距离（所有壁的总宽度）
        wall_thickness = params.shell.wall_thickness
        wall_count = params.shell.wall_count
        inset_distance = wall_thickness * wall_count

        for contour in contours:
            try:
                # 获取顶部轮廓（考虑斜边等边缘类型）
                top_contour = self._get_top_contour(contour, params)
                if not top_contour:
                    continue

                # 内缩外轮廓
                inset_outer = self.path_offset.offset(top_contour.outer, -inset_distance)
                if not inset_outer:
                    continue

                for outer_path in inset_outer:
                    outer_coords = [(p.x, p.y) for p in outer_path.points]
                    if len(outer_coords) < 3:
                        continue

                    # 内缩内孔
                    hole_coords_list = []
                    for hole in top_contour.holes:
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
                                    mesh = self.mesh_utils.extrude_polygon(
                                        geom, thickness, z_offset=z_start
                                    )
                                    if mesh is not None:
                                        meshes.append(mesh)
                        else:
                            mesh = self.mesh_utils.extrude_polygon(
                                polygon, thickness, z_offset=z_start
                            )
                            if mesh is not None:
                                meshes.append(mesh)

                    except Exception as e:
                        print(f"警告：创建顶面多边形失败: {e}")
                        continue

            except Exception as e:
                print(f"警告：处理轮廓顶面失败: {e}")
                continue

        return MeshUtils.merge_meshes(meshes)

    def _get_top_contour(self, contour: Contour,
                         params: SliceParams) -> Optional[Contour]:
        """
        获取顶部轮廓

        对于斜边和异形边，顶部轮廓可能与原始轮廓不同。

        Args:
            contour: 原始轮廓
            params: 切片参数

        Returns:
            顶部轮廓
        """
        edge_type = params.shell.edge_type

        if edge_type == EdgeType.STRAIGHT:
            # 直边：直接使用原始轮廓
            return contour

        elif edge_type == EdgeType.BEVELED:
            # 斜边：根据方向确定顶部轮廓
            bevel_direction = params.shell.bevel_direction
            bevel_width = params.shell.bevel_width

            if bevel_direction == BevelDirection.TOP_SMALL:
                # 上小下大：顶部是最小的，需要内缩
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
            else:
                # 上大下小：顶部是最大的，不需要偏移
                return contour

        elif edge_type == EdgeType.CUSTOM:
            # 异形边：根据轮廓在z=total_height处的偏移量
            profile = params.shell.edge_profile
            total_height = params.shell.height
            if profile and profile.control_points:
                # 获取顶部（归一化高度=1.0）的偏移量
                offset = profile.get_offset_at_height(1.0, params.shell.bevel_width, total_height)
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
