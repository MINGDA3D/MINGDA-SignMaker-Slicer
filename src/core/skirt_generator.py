"""
防翘裙边生成器模块 - v3 重构版

新设计：
- 外轮廓：向外偏移5mm生成裙边环
- 内孔：向内偏移5mm生成裙边环
- 每隔15mm生成一根连接线，连接裙边与壁

结构示意（俯视图）：
  Wall ═══════════════════════════════════
       ║       ║       ║       ║
       ║       ║       ║       ║  <- 连接线（每15mm一根）
  Skirt ───────────────────────────────
"""

import math
from typing import List, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass

from src.core.types import (
    Contour, SkirtParams, LayerPath, PathRole,
    ExtruderType, Point, Path
)

if TYPE_CHECKING:
    from src.core.path_offset import PathOffset

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class SkirtConnection:
    """裙边连接线数据"""
    wall_point: Point      # 壁上的点
    skirt_point: Point     # 裙边上的点


class SkirtMesh:
    """裙边3D网格数据"""

    def __init__(self):
        self.triangles = []

    def add_ring(self, ring_path: Path, height: float):
        """添加裙边环网格（连续实心环）

        Args:
            ring_path: 裙边环路径
            height: 裙边高度（Z方向）
        """
        if np is None:
            return

        points = ring_path.points
        n = len(points)
        if n < 3:
            return

        # 厚度 = 高度 × 2
        thickness = height * 2

        # 生成外环和内环的所有顶点
        outer_bottom = []
        outer_top = []
        inner_bottom = []
        inner_top = []

        for i in range(n):
            p = points[i]

            # 计算该点的法线（向内）
            prev_i = (i - 1) % n
            next_i = (i + 1) % n

            # 前一条边的方向
            dx1 = p.x - points[prev_i].x
            dy1 = p.y - points[prev_i].y
            len1 = (dx1*dx1 + dy1*dy1) ** 0.5
            if len1 > 0.001:
                dx1 /= len1
                dy1 /= len1

            # 后一条边的方向
            dx2 = points[next_i].x - p.x
            dy2 = points[next_i].y - p.y
            len2 = (dx2*dx2 + dy2*dy2) ** 0.5
            if len2 > 0.001:
                dx2 /= len2
                dy2 /= len2

            # 平均法线（向内）
            nx = -(dy1 + dy2) / 2
            ny = (dx1 + dx2) / 2
            nlen = (nx*nx + ny*ny) ** 0.5
            if nlen > 0.001:
                nx /= nlen
                ny /= nlen

            # 外环顶点（在路径上）
            outer_bottom.append(np.array([p.x, p.y, 0.0]))
            outer_top.append(np.array([p.x, p.y, height]))

            # 内环顶点（向内偏移）
            inner_bottom.append(np.array([p.x + nx * thickness, p.y + ny * thickness, 0.0]))
            inner_top.append(np.array([p.x + nx * thickness, p.y + ny * thickness, height]))

        # 生成面
        for i in range(n):
            j = (i + 1) % n

            # 外侧面
            self.triangles.extend([
                [outer_bottom[i], outer_bottom[j], outer_top[j]],
                [outer_bottom[i], outer_top[j], outer_top[i]]
            ])

            # 内侧面
            self.triangles.extend([
                [inner_bottom[i], inner_top[i], inner_bottom[j]],
                [inner_bottom[j], inner_top[i], inner_top[j]]
            ])

            # 顶面
            self.triangles.extend([
                [outer_top[i], outer_top[j], inner_top[j]],
                [outer_top[i], inner_top[j], inner_top[i]]
            ])

            # 底面
            self.triangles.extend([
                [outer_bottom[i], inner_bottom[j], outer_bottom[j]],
                [outer_bottom[i], inner_bottom[i], inner_bottom[j]]
            ])

    def add_connection(self, conn: SkirtConnection, height: float):
        """添加连接线网格（厚度=height×2）"""
        if np is None:
            return

        p1, p2 = conn.wall_point, conn.skirt_point
        dx, dy = p2.x - p1.x, p2.y - p1.y
        length = (dx * dx + dy * dy) ** 0.5

        if length < 0.001:
            return

        # 垂直方向，厚度 = height × 2
        nx, ny = -dy / length, dx / length
        thickness = height * 2

        # 4个底部顶点
        b1 = np.array([p1.x + nx * thickness / 2, p1.y + ny * thickness / 2, 0.0])
        b2 = np.array([p1.x - nx * thickness / 2, p1.y - ny * thickness / 2, 0.0])
        b3 = np.array([p2.x - nx * thickness / 2, p2.y - ny * thickness / 2, 0.0])
        b4 = np.array([p2.x + nx * thickness / 2, p2.y + ny * thickness / 2, 0.0])

        # 4个顶部顶点
        t1 = np.array([p1.x + nx * thickness / 2, p1.y + ny * thickness / 2, height])
        t2 = np.array([p1.x - nx * thickness / 2, p1.y - ny * thickness / 2, height])
        t3 = np.array([p2.x - nx * thickness / 2, p2.y - ny * thickness / 2, height])
        t4 = np.array([p2.x + nx * thickness / 2, p2.y + ny * thickness / 2, height])

        # 4个侧面
        self.triangles.extend([
            [b1, t1, b2], [b2, t1, t2],
            [b2, t2, b3], [b3, t2, t3],
            [b3, t3, b4], [b4, t3, t4],
            [b4, t4, b1], [b1, t4, t1]
        ])

        # 顶面
        self.triangles.extend([
            [t1, t2, t3], [t1, t3, t4]
        ])

        # 底面
        self.triangles.extend([
            [b1, b3, b2], [b1, b4, b3]
        ])

    def get_triangles(self):
        """获取所有三角形"""
        return self.triangles


class SkirtGenerator:
    """防翘裙边生成器 v3

    新算法：
    1. 外轮廓向外偏移5mm，内孔向内偏移5mm
    2. 每隔15mm生成一根连接线
    3. 裙边 = 偏移环 + 连接线
    """

    def generate_skirt_clipped(
        self,
        contour: Contour,
        all_contours: List[Contour],
        params: SkirtParams,
        wall_thickness: float,
        path_offset: 'PathOffset'
    ) -> List[LayerPath]:
        """生成裙边路径（G-code用）"""
        if not params.enabled:
            return []

        result = []

        if params.outer_enabled:
            result.extend(
                self._generate_contour_side_paths(
                    contour, params, path_offset, generate_outer_side=True
                )
            )

        if params.inner_enabled:
            result.extend(
                self._generate_contour_side_paths(
                    contour, params, path_offset, generate_outer_side=False
                )
            )

        return result

    def generate_skirt_3d_clipped(
        self,
        contour: Contour,
        all_contours: List[Contour],
        params: SkirtParams,
        wall_thickness: float,
        path_offset: 'PathOffset'
    ) -> List['SkirtMesh']:
        """生成3D裙边数据（STL用）"""
        if not params.enabled:
            return []

        meshes = []

        if params.outer_enabled:
            meshes.extend(
                self._generate_contour_side_meshes(
                    contour, params, path_offset, generate_outer_side=True
                )
            )

        if params.inner_enabled:
            meshes.extend(
                self._generate_contour_side_meshes(
                    contour, params, path_offset, generate_outer_side=False
                )
            )

        return meshes

    def _generate_contour_side_paths(
        self,
        contour: Contour,
        params: SkirtParams,
        path_offset: 'PathOffset',
        generate_outer_side: bool,
    ) -> List[LayerPath]:
        result: List[LayerPath] = []

        for wall_path, offset_outward in self._iter_boundary_modes(
            contour, generate_outer_side
        ):
            skirt_ring = self._generate_skirt_ring(
                wall_path, 5.0, offset_outward, path_offset
            )
            if skirt_ring:
                result.append(self._path_to_layer_path(skirt_ring, params))

            connections = self._generate_connections(
                wall_path, skirt_ring, 15.0, offset_outward
            )
            for conn in connections:
                result.append(self._connection_to_layer_path(conn, params))

        return result

    def _generate_contour_side_meshes(
        self,
        contour: Contour,
        params: SkirtParams,
        path_offset: 'PathOffset',
        generate_outer_side: bool,
    ) -> List['SkirtMesh']:
        meshes: List['SkirtMesh'] = []

        for wall_path, offset_outward in self._iter_boundary_modes(
            contour, generate_outer_side
        ):
            skirt_ring = self._generate_skirt_ring(
                wall_path, 5.0, offset_outward, path_offset
            )
            if not skirt_ring:
                continue

            mesh = SkirtMesh()
            mesh.add_ring(skirt_ring, params.height)

            connections = self._generate_connections(
                wall_path, skirt_ring, 15.0, offset_outward
            )
            for conn in connections:
                mesh.add_connection(conn, params.height)

            meshes.append(mesh)

        return meshes

    def _iter_boundary_modes(
        self,
        contour: Contour,
        generate_outer_side: bool,
    ) -> List[Tuple[Path, bool]]:
        boundaries: List[Tuple[Path, bool]] = []

        # generate_outer_side=True:
        #   outer contour -> outward, holes -> inward
        # generate_outer_side=False:
        #   outer contour -> inward, holes -> outward
        boundaries.append((contour.outer, generate_outer_side))
        for hole in contour.holes:
            boundaries.append((hole, not generate_outer_side))

        return boundaries

    def _generate_skirt_ring(
        self,
        wall_path: Path,
        offset_distance: float,
        is_outer: bool,
        path_offset: 'PathOffset'
    ) -> Optional[Path]:
        """生成裙边环（偏移轮廓）

        Args:
            wall_path: 壁路径
            offset_distance: 偏移距离（5mm）
            is_outer: True=外轮廓向外偏移，False=内孔向内偏移
            path_offset: 偏移工具
        """
        from src.core.path_offset import JoinType

        # 外轮廓：正偏移（向外）
        # 内孔：负偏移（向内，让孔变小）
        offset = offset_distance if is_outer else -offset_distance
        result = path_offset.offset(wall_path, offset, JoinType.ROUND)
        return result[0] if result else None

    def _generate_connections(
        self,
        wall_path: Path,
        skirt_ring: Optional[Path],
        interval: float,
        is_outer: bool
    ) -> List[SkirtConnection]:
        """生成连接线

        Args:
            wall_path: 壁路径
            skirt_ring: 裙边环路径
            interval: 连接线间距（15mm）
            is_outer: 是否外轮廓
        """
        if not skirt_ring:
            return []

        connections = []
        points = wall_path.points
        n = len(points)

        if n < 2:
            return connections

        # 计算路径总长度
        segment_lengths = []
        cumulative_lengths = [0.0]
        total_length = 0.0

        for i in range(n):
            j = (i + 1) % n
            dx = points[j].x - points[i].x
            dy = points[j].y - points[i].y
            length = math.sqrt(dx * dx + dy * dy)
            segment_lengths.append(length)
            total_length += length
            cumulative_lengths.append(total_length)

        if total_length < interval:
            return connections

        # 沿壁路径每隔15mm取一个点
        num_connections = max(1, int(total_length / interval))
        actual_interval = total_length / num_connections

        signed_area = self._calculate_signed_area(points)
        is_ccw = signed_area > 0

        for i in range(num_connections):
            dist = i * actual_interval

            wall_pos, direction = self._get_point_and_direction_at_distance(
                points, segment_lengths, cumulative_lengths, dist
            )

            if wall_pos is None:
                continue

            wall_point = Point(wall_pos[0], wall_pos[1])

            # 计算法线方向
            if is_ccw == is_outer:
                normal = self._get_outward_normal(direction)
            else:
                normal = self._get_inward_normal(direction)

            # 沿法线方向找裙边环上的最近点
            search_point = Point(
                wall_point.x + normal[0] * 5.0,
                wall_point.y + normal[1] * 5.0
            )

            skirt_point = self._find_nearest_point_on_path(
                search_point, skirt_ring
            )

            connections.append(SkirtConnection(
                wall_point=wall_point,
                skirt_point=skirt_point
            ))

        return connections

    def _path_to_layer_path(self, path: Path, params: SkirtParams) -> LayerPath:
        """将Path转换为LayerPath"""
        return LayerPath(
            points=path.points,
            role=PathRole.SKIRT,
            extruder=ExtruderType.EXTRUDER_1,
            line_width=params.height * 2,
            is_closed=True
        )

    def _connection_to_layer_path(
        self, conn: SkirtConnection, params: SkirtParams
    ) -> LayerPath:
        """将连接线转换为LayerPath"""
        return LayerPath(
            points=[conn.wall_point, conn.skirt_point],
            role=PathRole.SKIRT,
            extruder=ExtruderType.EXTRUDER_1,
            line_width=params.height * 2,
            is_closed=False
        )

    # ================================================================
    # 辅助方法
    # ================================================================

    def _calculate_signed_area(self, points: List[Point]) -> float:
        """计算有向面积（CCW > 0）"""
        area = 0.0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y
        return area / 2.0

    def _get_point_and_direction_at_distance(
        self,
        points: List[Point],
        segment_lengths: List[float],
        cumulative_lengths: List[float],
        distance: float
    ) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """获取路径上指定距离处的点和方向"""
        n = len(points)
        total_length = cumulative_lengths[-1]

        distance = distance % total_length

        for i in range(n):
            if cumulative_lengths[i] <= distance <= cumulative_lengths[i + 1]:
                seg_len = segment_lengths[i]
                if seg_len < 0.001:
                    continue

                t = (distance - cumulative_lengths[i]) / seg_len

                j = (i + 1) % n
                x = points[i].x + t * (points[j].x - points[i].x)
                y = points[i].y + t * (points[j].y - points[i].y)

                dx = points[j].x - points[i].x
                dy = points[j].y - points[i].y
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    dx /= length
                    dy /= length

                return (x, y), (dx, dy)

        return None, None

    def _get_outward_normal(self, direction: Tuple[float, float]) -> Tuple[float, float]:
        """获取外向法线（CCW路径）"""
        dx, dy = direction
        return (dy, -dx)

    def _get_inward_normal(self, direction: Tuple[float, float]) -> Tuple[float, float]:
        """获取内向法线"""
        dx, dy = direction
        return (-dy, dx)

    def _find_nearest_point_on_path(self, point: Point, path: Path) -> Point:
        """在路径上找最近点"""
        best_point = path.points[0]
        best_dist_sq = float('inf')

        n = len(path.points)
        for i in range(n):
            j = (i + 1) % n
            p1 = path.points[i]
            p2 = path.points[j]

            nearest = self._nearest_point_on_segment(point, p1, p2)
            dx = nearest.x - point.x
            dy = nearest.y - point.y
            dist_sq = dx * dx + dy * dy

            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_point = nearest

        return best_point

    def _nearest_point_on_segment(
        self, point: Point, seg_a: Point, seg_b: Point
    ) -> Point:
        """计算点到线段的最近点"""
        ax, ay = seg_a.x, seg_a.y
        bx, by = seg_b.x, seg_b.y
        px, py = point.x, point.y

        dx = bx - ax
        dy = by - ay
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq < 1e-12:
            return seg_a

        t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
        t = max(0.0, min(1.0, t))

        return Point(ax + t * dx, ay + t * dy)

    # ================================================================
    # 向后兼容的旧API（保持接口不变）
    # ================================================================

    def generate_skirt(self, contour: Contour, params: SkirtParams) -> List[LayerPath]:
        """旧API：无裁剪版本（已废弃，保持兼容）"""
        return []

    def generate_skirt_3d(self, contour: Contour, params: SkirtParams) -> List:
        """旧API：3D版本（已废弃，保持兼容）"""
        return []
