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

from ..types import (
    Contour,
    SliceResult,
    SliceParams,
    Point,
    Layer,
    LayerPath,
    PathRole,
    resolve_shell_wall_thickness,
)
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
        """Build flat step meshes from contours and V-groove meshes from sliced layers."""
        meshes = []
        meshes.extend(
            self._build_flat_step_meshes(
                contours,
                params,
                panel_contours=panel_contours,
                baseplate_contours=baseplate_contours,
            )
        )
        meshes.extend(self._build_v_groove_meshes_from_slices(result, params))

        return MeshUtils.merge_meshes(meshes)

    def _build_flat_step_meshes(
        self,
        contours: List[Contour],
        params: SliceParams,
        panel_contours: Optional[List[Contour]] = None,
        baseplate_contours: Optional[List[Contour]] = None,
    ) -> List[trimesh.Trimesh]:
        """Build ordinary flat step meshes with the original thin-ring behavior."""
        meshes = []
        total_height = params.shell.height
        wall_thickness = resolve_shell_wall_thickness(
            params.shell.line_width,
            params.shell.wall_count,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
        )
        step_thickness = params.shell.layer_height + 0.1

        panel_contours_to_use = panel_contours if panel_contours else contours
        baseplate_contours_to_use = baseplate_contours if baseplate_contours else contours

        for contour_idx, contour in enumerate(contours):
            try:
                if not contour.outer.points:
                    continue

                if (
                    params.step.panel_step_enabled
                    and not params.step.panel_step_is_v_groove
                    and contour_idx < len(panel_contours_to_use)
                ):
                    panel_z = params.step.panel_step_height
                    min_panel_z = total_height / 2
                    if panel_z < min_panel_z:
                        panel_z = min_panel_z
                    if 0 <= panel_z < total_height:
                        meshes.extend(
                            self._build_flat_step_meshes_for_contour(
                                panel_contours_to_use[contour_idx],
                                step_width=params.step.panel_step_width,
                                step_thickness=step_thickness,
                                z_position=panel_z,
                                wall_thickness=wall_thickness,
                            )
                        )

                if (
                    params.step.baseplate_step_enabled
                    and not params.step.baseplate_step_is_v_groove
                    and contour_idx < len(baseplate_contours_to_use)
                ):
                    baseplate_z = params.step.baseplate_step_height
                    max_baseplate_z = total_height / 2
                    if baseplate_z > max_baseplate_z:
                        baseplate_z = max_baseplate_z
                    if 0 <= baseplate_z < total_height:
                        meshes.extend(
                            self._build_flat_step_meshes_for_contour(
                                baseplate_contours_to_use[contour_idx],
                                step_width=params.step.baseplate_step_width,
                                step_thickness=step_thickness,
                                z_position=baseplate_z,
                                wall_thickness=wall_thickness,
                            )
                        )

            except Exception as e:
                print(f"警告：处理轮廓台阶失败: {e}")
                continue

        return meshes

    def _build_flat_step_meshes_for_contour(
        self,
        contour: Contour,
        step_width: float,
        step_thickness: float,
        z_position: float,
        wall_thickness: float,
    ) -> List[trimesh.Trimesh]:
        """Build one contour's ordinary flat step meshes."""
        meshes = []

        inner_wall_results = self.path_offset.offset(contour.outer, -wall_thickness)
        if inner_wall_results:
            inner_wall_coords = [(p.x, p.y) for p in inner_wall_results[0].points]
            if inner_wall_coords and inner_wall_coords[0] != inner_wall_coords[-1]:
                inner_wall_coords.append(inner_wall_coords[0])

            outer_mesh = self._create_thin_step_ring(
                inner_wall_coords,
                step_width=step_width,
                step_thickness=step_thickness,
                z_position=z_position,
                is_hole=False,
            )
            if outer_mesh is not None:
                meshes.append(outer_mesh)

        for hole in contour.holes:
            hole_wall_results = self.path_offset.offset(hole, wall_thickness)
            hole_wall_path = hole_wall_results[0] if hole_wall_results else hole
            hole_inner_coords = [(p.x, p.y) for p in hole_wall_path.points]
            if hole_inner_coords and hole_inner_coords[0] != hole_inner_coords[-1]:
                hole_inner_coords.append(hole_inner_coords[0])

            hole_mesh = self._create_thin_step_ring(
                hole_inner_coords,
                step_width=step_width,
                step_thickness=step_thickness,
                z_position=z_position,
                is_hole=True,
            )
            if hole_mesh is not None:
                meshes.append(hole_mesh)

        return meshes

    def _build_v_groove_meshes_from_slices(
        self,
        result: SliceResult,
        params: SliceParams,
    ) -> List[trimesh.Trimesh]:
        """Build V-groove meshes by matching sliced grooves to same-layer walls."""
        meshes = []

        for layer in result.layers:
            wall_paths = [
                path for path in layer.paths
                if path.role == PathRole.WALL and path.is_closed and len(path.points) >= 3
            ]
            if not wall_paths:
                continue

            for path in layer.paths:
                if (
                    path.role != PathRole.V_GROOVE
                    or not path.is_closed
                    or len(path.points) < 3
                    or path.line_width <= 0.0
                ):
                    continue

                wall_path = self._match_step_to_wall_path(path, wall_paths)
                if wall_path is None:
                    continue

                wall_inner_coords = self._calculate_inner_wall_from_path(
                    wall_path,
                    wall_path.line_width if wall_path.line_width > 0.0 else params.shell.line_width,
                    reference_path=path,
                )
                mesh = self._create_thin_step_ring(
                    wall_inner_coords,
                    step_width=path.line_width,
                    step_thickness=layer.layer_height,
                    z_position=layer.z_height,
                    is_hole=self._is_hole_step_path(path, wall_path),
                )
                if mesh is not None:
                    meshes.append(mesh)

        return meshes

    def _match_step_to_wall_path(
        self,
        step_path: LayerPath,
        wall_paths: List[LayerPath],
    ) -> Optional[LayerPath]:
        """Find the closest wall loop for one step/v-groove ring."""
        if not wall_paths:
            return None

        step_centroid = self._calculate_centroid(step_path.points)
        return min(
            wall_paths,
            key=lambda wall_path: self._distance_between_points(
                step_centroid,
                self._calculate_centroid(wall_path.points),
            ),
        )

    def _is_hole_step_path(self, step_path: LayerPath, wall_path: LayerPath) -> bool:
        """Hole steps expand away from the matched wall loop instead of shrinking inward."""
        return self._polygon_area(step_path.points) > self._polygon_area(wall_path.points)

    def _polygon_area(self, points: List[Point]) -> float:
        """Compute the absolute polygon area for a closed path."""
        if len(points) < 3:
            return 0.0

        area = 0.0
        for i, point in enumerate(points):
            next_point = points[(i + 1) % len(points)]
            area += point.x * next_point.y - next_point.x * point.y
        return abs(area) * 0.5

    def _distance_between_points(self, p1: Point, p2: Point) -> float:
        """Euclidean distance helper for path matching."""
        return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5

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
        self,
        wall_path: LayerPath,
        wall_thickness: float,
        reference_path: Optional[LayerPath] = None,
    ) -> List[tuple]:
        """从WALL路径计算朝向台阶空腔一侧的壁边缘

        切片里的 WALL 路径是壁的中心线。外轮廓需要回退半个线宽，
        内孔则需要前进半个线宽，才能还原出台阶真正依附的空腔侧边缘。
        """
        inner_path = CorePath(points=wall_path.points)
        half_wall = max(wall_thickness, 0.0) / 2.0

        if half_wall > 1e-6:
            offset_distance = -half_wall
            if reference_path is not None and reference_path.points:
                offset_distance = half_wall if self._is_hole_step_path(reference_path, wall_path) else -half_wall

            inner_results = self.path_offset.offset(inner_path, offset_distance)
            if inner_results:
                if reference_path is not None and reference_path.points:
                    reference_centroid = self._calculate_centroid(reference_path.points)
                    chosen_path = min(
                        inner_results,
                        key=lambda candidate: self._distance_between_points(
                            reference_centroid,
                            candidate.centroid,
                        ),
                    )
                else:
                    chosen_path = max(inner_results, key=lambda candidate: abs(candidate.area))

                inner_coords = [(p.x, p.y) for p in chosen_path.points]
                if inner_coords and inner_coords[0] != inner_coords[-1]:
                    inner_coords.append(inner_coords[0])
                return inner_coords

        inner_coords = [(p.x, p.y) for p in wall_path.points]
        if inner_coords and inner_coords[0] != inner_coords[-1]:
            inner_coords.append(inner_coords[0])

        return inner_coords
