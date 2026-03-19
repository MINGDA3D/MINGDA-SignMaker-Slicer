"""
MINGDA SignMaker - 台阶网格生成器

生成台阶（面板台阶/底板台阶）的3D网格。
台阶是在字壳内侧向内凸出的环形薄平台，用于支撑面板或底板。
"""

from __future__ import annotations
from typing import List, Optional, Dict

import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from ..types import Contour, SliceResult, SliceParams, Point, Layer, LayerPath, PathRole
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
              params: SliceParams,
              panel_contours: Optional[List[Contour]] = None,
              baseplate_contours: Optional[List[Contour]] = None) -> Optional[trimesh.Trimesh]:
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
            panel_contours: 面板台阶高度处经过边缘变换后的轮廓
            baseplate_contours: 底板台阶高度处经过边缘变换后的轮廓

        Returns:
            台阶网格
        """
        meshes = []
        total_height = params.shell.height
        wall_thickness = params.shell.wall_thickness

        # 台阶厚度 = 层高 + 0.1mm
        step_thickness = params.shell.layer_height + 0.1

        # 从切片结果中提取台阶层的壁位置
        contour_wall_positions = self._extract_wall_positions_at_step_layers(
            result, params, total_height, contours
        )

        # 使用变换后的轮廓（如果提供）或原始轮廓
        panel_contours_to_use = panel_contours if panel_contours else contours
        baseplate_contours_to_use = baseplate_contours if baseplate_contours else contours

        for contour_idx, contour in enumerate(contours):
            try:
                outer_points = contour.outer.points
                if not outer_points:
                    continue

                # ===== 面板台阶（顶部）=====
                if params.step.panel_step_enabled and contour_idx < len(panel_contours_to_use):
                    panel_z = params.step.panel_step_height
                    min_panel_z = total_height / 2
                    if panel_z < min_panel_z:
                        panel_z = min_panel_z
                    if 0 <= panel_z < total_height:
                        # 使用变换后的轮廓
                        transformed_contour = panel_contours_to_use[contour_idx]
                        inner_wall_results = self.path_offset.offset(transformed_contour.outer, -wall_thickness)
                        if inner_wall_results:
                            inner_wall_coords = [(p.x, p.y) for p in inner_wall_results[0].points]
                            if inner_wall_coords and inner_wall_coords[0] != inner_wall_coords[-1]:
                                inner_wall_coords.append(inner_wall_coords[0])

                            panel_mesh = self._create_thin_step_ring(
                                inner_wall_coords,
                                step_width=params.step.panel_step_width,
                                step_thickness=step_thickness,
                                z_position=panel_z,
                                is_hole=False
                            )
                            if panel_mesh is not None:
                                meshes.append(panel_mesh)

                        # 处理内孔
                        for hole in transformed_contour.holes:
                            # 内孔的壁内边缘就是变换后的孔本身
                            hole_inner_coords = [(p.x, p.y) for p in hole.points]
                            if hole_inner_coords and hole_inner_coords[0] != hole_inner_coords[-1]:
                                hole_inner_coords.append(hole_inner_coords[0])

                            hole_panel_mesh = self._create_thin_step_ring(
                                hole_inner_coords,
                                step_width=params.step.panel_step_width,
                                step_thickness=step_thickness,
                                z_position=panel_z,
                                is_hole=True
                            )
                            if hole_panel_mesh is not None:
                                meshes.append(hole_panel_mesh)

                # ===== 底板台阶（底部）=====
                if params.step.baseplate_step_enabled and contour_idx < len(baseplate_contours_to_use):
                    baseplate_z = params.step.baseplate_step_height
                    max_baseplate_z = total_height / 2
                    if baseplate_z > max_baseplate_z:
                        baseplate_z = max_baseplate_z
                    if 0 <= baseplate_z < total_height:
                        # 使用变换后的轮廓
                        transformed_contour = baseplate_contours_to_use[contour_idx]
                        inner_wall_results = self.path_offset.offset(transformed_contour.outer, -wall_thickness)
                        if inner_wall_results:
                            inner_wall_coords = [(p.x, p.y) for p in inner_wall_results[0].points]
                            if inner_wall_coords and inner_wall_coords[0] != inner_wall_coords[-1]:
                                inner_wall_coords.append(inner_wall_coords[0])

                            baseplate_mesh = self._create_thin_step_ring(
                                inner_wall_coords,
                                step_width=params.step.baseplate_step_width,
                                step_thickness=step_thickness,
                                z_position=baseplate_z,
                                is_hole=False
                            )
                            if baseplate_mesh is not None:
                                meshes.append(baseplate_mesh)

                        # 处理内孔
                        for hole in transformed_contour.holes:
                            # 内孔的壁内边缘就是变换后的孔本身
                            hole_inner_coords = [(p.x, p.y) for p in hole.points]
                            if hole_inner_coords and hole_inner_coords[0] != hole_inner_coords[-1]:
                                hole_inner_coords.append(hole_inner_coords[0])

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
            ring_polygon = self._build_step_ring_geometry(
                wall_inner_coords,
                step_width=step_width,
                is_hole=is_hole
            )

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

    def _build_step_ring_geometry(self, wall_inner_coords: list,
                                  step_width: float,
                                  is_hole: bool = False):
        """构建台阶环形区域，正确处理内缩后分裂成多个岛的情况。"""
        if not wall_inner_coords or len(wall_inner_coords) < 4:
            return None

        outer_ring_coords = wall_inner_coords
        if outer_ring_coords[0] != outer_ring_coords[-1]:
            outer_ring_coords = outer_ring_coords + [outer_ring_coords[0]]

        base_polygon = ShapelyPolygon(outer_ring_coords)
        if not base_polygon.is_valid:
            base_polygon = make_valid(base_polygon)

        if base_polygon.is_empty or base_polygon.area < 1e-6:
            return None

        outer_path = CorePath(points=[Point(c[0], c[1]) for c in outer_ring_coords[:-1]])
        offset_dist = step_width if is_hole else -step_width
        inner_results = self.path_offset.offset(outer_path, offset_dist)

        offset_polygons = []
        for result in inner_results:
            inner_ring_coords = [(p.x, p.y) for p in result.points]
            if len(inner_ring_coords) < 3:
                continue
            if inner_ring_coords[0] != inner_ring_coords[-1]:
                inner_ring_coords.append(inner_ring_coords[0])

            inner_polygon = ShapelyPolygon(inner_ring_coords)
            if not inner_polygon.is_valid:
                inner_polygon = make_valid(inner_polygon)
            if inner_polygon.is_empty or inner_polygon.area < 1e-6:
                continue
            offset_polygons.append(inner_polygon)

        if not offset_polygons:
            return base_polygon if not is_hole else None

        offset_region = unary_union(offset_polygons)
        ring_polygon = (
            offset_region.difference(base_polygon)
            if is_hole
            else base_polygon.difference(offset_region)
        )

        if not ring_polygon.is_valid:
            ring_polygon = make_valid(ring_polygon)

        return ring_polygon

    def _extract_wall_positions_at_step_layers(
        self, result: SliceResult, params: SliceParams, total_height: float, contours: List[Contour]
    ) -> Dict[int, Dict[str, List[LayerPath]]]:
        """从切片结果中提取台阶层的壁路径位置"""
        baseplate_z = params.step.baseplate_step_height
        panel_z = params.step.panel_step_height
        layer_height = params.shell.layer_height

        max_baseplate_z = total_height / 2
        if baseplate_z > max_baseplate_z:
            baseplate_z = max_baseplate_z
        min_panel_z = total_height / 2
        if panel_z < min_panel_z:
            panel_z = min_panel_z

        contour_positions = {}
        tolerance = layer_height * 0.6

        for layer in result.layers:
            z = layer.z_height

            if params.step.baseplate_step_enabled and abs(z - baseplate_z) < tolerance:
                self._extract_wall_paths_from_layer(layer, contour_positions, 'baseplate', contours)

            if params.step.panel_step_enabled and abs(z - panel_z) < tolerance:
                self._extract_wall_paths_from_layer(layer, contour_positions, 'panel', contours)

        return contour_positions

    def _extract_wall_paths_from_layer(
        self, layer: Layer, contour_positions: Dict, step_type: str, contours: List[Contour]
    ):
        """从层中提取WALL路径，按轮廓分组"""
        wall_paths = [p for p in layer.paths if p.role == PathRole.WALL]

        for path in wall_paths:
            if not path.points:
                continue

            path_centroid = self._calculate_centroid(path.points)
            contour_idx = self._find_closest_contour(path_centroid, contours)

            if contour_idx not in contour_positions:
                contour_positions[contour_idx] = {}
            if step_type not in contour_positions[contour_idx]:
                contour_positions[contour_idx][step_type] = []

            contour_positions[contour_idx][step_type].append(path)

    def _calculate_centroid(self, points: List[Point]) -> Point:
        """计算点集的质心"""
        if not points:
            return Point(0, 0)
        x_sum = sum(p.x for p in points)
        y_sum = sum(p.y for p in points)
        n = len(points)
        return Point(x_sum / n, y_sum / n)

    def _find_closest_contour(self, point: Point, contours: List[Contour]) -> int:
        """找到距离点最近的轮廓索引"""
        min_dist = float('inf')
        closest_idx = 0

        for idx, contour in enumerate(contours):
            centroid = contour.outer.centroid
            dist = ((point.x - centroid.x) ** 2 + (point.y - centroid.y) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest_idx = idx

        return closest_idx

    def _calculate_inner_wall_from_path(
        self, wall_path: LayerPath, wall_thickness: float
    ) -> List[tuple]:
        """从WALL路径计算壁的内边缘

        WALL路径通常是壁的内边缘，直接使用即可
        """
        inner_coords = [(p.x, p.y) for p in wall_path.points]
        if inner_coords and inner_coords[0] != inner_coords[-1]:
            inner_coords.append(inner_coords[0])

        return inner_coords
