"""
MINGDA SignMaker - 台阶网格生成器

生成台阶（面板台阶/底板台阶）的3D网格。
台阶是在字壳内侧向内凸出的环形薄平台，用于支撑面板或底板。
"""

from __future__ import annotations
from typing import List, Optional

import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid

from ..types import Contour, SliceResult, SliceParams, Point
from ..types import Path as CorePath
from ..path_offset import PathOffset
from .mesh_utils import MeshUtils


class StepMeshBuilder:
    """台阶网格生成器"""

    def __init__(self, path_offset: PathOffset):
        """
        初始化台阶网格生成器

        Args:
            path_offset: 路径偏移工具
        """
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()

    def build(self, contours: List[Contour], result: SliceResult,
              params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建台阶网格

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

                # 计算壁的内边缘
                inner_wall_results = self.path_offset.offset(contour.outer, -wall_thickness)
                if not inner_wall_results:
                    continue

                inner_wall_coords = [(p.x, p.y) for p in inner_wall_results[0].points]
                if inner_wall_coords[0] != inner_wall_coords[-1]:
                    inner_wall_coords.append(inner_wall_coords[0])

                # ===== 面板台阶（顶部）=====
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

        return MeshUtils.merge_meshes(meshes)

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
            # 外边缘坐标
            outer_ring_coords = wall_inner_coords

            # 计算内边缘（向内偏移step_width）
            outer_path = CorePath(points=[Point(c[0], c[1]) for c in wall_inner_coords[:-1]])

            if is_hole:
                # 内孔的台阶：向孔内延伸（正偏移，让孔变小）
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
                        mesh = self.mesh_utils.extrude_polygon(geom, step_thickness, z_position)
                        if mesh is not None:
                            meshes.append(mesh)
            elif ring_polygon.geom_type == 'Polygon':
                mesh = self.mesh_utils.extrude_polygon(ring_polygon, step_thickness, z_position)
                if mesh is not None:
                    meshes.append(mesh)
            elif ring_polygon.geom_type == 'GeometryCollection':
                for geom in ring_polygon.geoms:
                    if geom.geom_type == 'Polygon' and geom.area > 1e-6:
                        mesh = self.mesh_utils.extrude_polygon(geom, step_thickness, z_position)
                        if mesh is not None:
                            meshes.append(mesh)

            return MeshUtils.merge_meshes(meshes)

        except Exception as e:
            print(f"警告：创建台阶网格失败: {e}")
            return None
