"""
防翘裙边生成器模块

生成连续梯形防翘裙边，防止打印过程中字壳翘曲。

裙边结构（截面图）：
  字壳 ════════════════════════════════════════════
       ╲          ╱╲          ╱╲          ╱
        ╲        ╱  ╲        ╱  ╲        ╱
         ╲      ╱    ╲      ╱    ╲      ╱
          ╲    ╱      ╲    ╱      ╲    ╱
           ────        ────        ────

相邻梯形共享斜边，形成连续的波浪形防翘结构。

重构算法（v2）：
  1. 将轮廓向外偏移 skirt_width，得到裙边外边界
  2. 构建连续的锯齿形裙边多边形（而非独立梯形）
  3. 用布尔差集从裙边中减去禁区（其他轮廓、孔壁）
  4. 裙边在拐角处自然绕着轮廓走，而非被删除
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


@dataclass
class TrapezoidSkirt:
    """单个梯形裙边的顶点数据"""
    # 顶边两个点（贴着字壳）
    top_left: Point
    top_right: Point
    # 底边两个点
    bottom_left: Point
    bottom_right: Point


class SkirtGenerator:
    """防翘裙边生成器

    v2 重构版：使用连续裙边带算法，避免以下问题：
    - 拐角处梯形重叠
    - 拐角处梯形被粗暴删除
    - 梯形与其他轮廓交叉

    核心思想：
    1. 生成连续的锯齿形裙边多边形（一个完整的闭合路径）
    2. 从中减去禁区，保留合法部分
    3. 裙边自然跟随轮廓拐角弯曲
    """

    # ================================================================
    # 公开 API（保持向后兼容）
    # ================================================================

    def generate_skirt(self, contour: Contour,
                       params: SkirtParams) -> List[LayerPath]:
        """
        生成防翘裙边（无裁剪，保持向后兼容）

        Args:
            contour: 字形轮廓
            params: 裙边参数

        Returns:
            裙边路径列表
        """
        paths = []

        if not params.enabled:
            return paths

        if params.is_outer:
            skirt_paths = self._generate_outer_skirt(contour.outer, params)
        else:
            for hole in contour.holes:
                skirt_paths = self._generate_inner_skirt(hole, params)
                paths.extend(skirt_paths)
            return paths

        paths.extend(skirt_paths)
        return paths

    def generate_skirt_3d(self, contour: Contour,
                          params: SkirtParams) -> List[TrapezoidSkirt]:
        """
        生成3D梯形裙边数据（用于STL导出，无裁剪）

        Args:
            contour: 字形轮廓
            params: 裙边参数

        Returns:
            梯形裙边列表
        """
        if not params.enabled:
            return []

        return self._generate_trapezoids_along_path(
            contour.outer, params, is_outer=params.is_outer
        )

    def generate_skirt_clipped(
        self,
        contour: Contour,
        all_contours: List[Contour],
        params: SkirtParams,
        wall_thickness: float,
        path_offset: 'PathOffset'
    ) -> List[LayerPath]:
        """
        生成经过裁剪的防翘裙边（不侵犯壁区域）

        v2 算法：
        1. 生成连续的锯齿形裙边多边形（贴着轮廓的连续带状结构）
        2. 构建禁区（其他轮廓 + 当前轮廓的孔壁 + 当前轮廓自身内部）
        3. 用布尔差集裁剪裙边，保留合法部分
        4. 裙边在拐角处自然跟随轮廓走

        Args:
            contour: 当前轮廓
            all_contours: 所有轮廓（用于计算禁区）
            params: 裙边参数
            wall_thickness: 壁厚
            path_offset: 路径偏移工具

        Returns:
            裁剪后的裙边路径列表
        """
        if not params.enabled:
            return []

        # Step 1: 构建禁区
        forbidden_zones = self._build_forbidden_zones(
            contour, all_contours, wall_thickness, path_offset, params
        )

        # Step 2: 生成连续锯齿裙边多边形列表
        if params.is_outer:
            skirt_polygons = self._generate_continuous_skirt_polygons(
                contour.outer, params, is_outer=True, path_offset=path_offset
            )
        else:
            skirt_polygons = []
            for hole in contour.holes:
                polys = self._generate_continuous_skirt_polygons(
                    hole, params, is_outer=False, path_offset=path_offset
                )
                skirt_polygons.extend(polys)

        if not skirt_polygons:
            return []

        # Step 3: 裁剪裙边
        if forbidden_zones:
            clipped_paths = path_offset.boolean_difference_multi(
                skirt_polygons, forbidden_zones
            )
        else:
            clipped_paths = skirt_polygons

        # Step 4: 转换为 LayerPath
        result = []
        for path in clipped_paths:
            if len(path.points) >= 3:
                layer_path = LayerPath(
                    points=path.points,
                    role=PathRole.SKIRT,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=params.extrusion_width,
                    is_closed=True
                )
                result.append(layer_path)

        return result

    def generate_skirt_3d_clipped(
        self,
        contour: Contour,
        all_contours: List[Contour],
        params: SkirtParams,
        wall_thickness: float,
        path_offset: 'PathOffset'
    ) -> List[TrapezoidSkirt]:
        """
        生成经过裁剪的3D梯形裙边（用于STL导出）

        v2 算法：使用连续裙边带生成，然后检测重叠。
        对于STL，仍然返回 TrapezoidSkirt 列表（保持兼容），
        但使用改进的重叠检测。

        Args:
            contour: 当前轮廓
            all_contours: 所有轮廓
            params: 裙边参数
            wall_thickness: 壁厚
            path_offset: 路径偏移工具

        Returns:
            未被裁剪的梯形列表
        """
        if not params.enabled:
            return []

        # 构建禁区
        forbidden_zones = self._build_forbidden_zones(
            contour, all_contours, wall_thickness, path_offset, params
        )

        # 生成原始梯形（STL仍需要梯形结构）
        raw_trapezoids = self._generate_trapezoids_along_path(
            contour.outer, params, is_outer=params.is_outer
        )

        # 去除同轮廓内重叠
        non_overlapping = self._remove_overlapping_trapezoids(raw_trapezoids)

        if not forbidden_zones:
            return non_overlapping

        # 对STL，用布尔运算检测每个梯形是否与禁区重叠
        valid_trapezoids = []
        for trap in non_overlapping:
            trap_path = Path(
                points=[
                    trap.top_left, trap.bottom_left,
                    trap.bottom_right, trap.top_right
                ],
                is_closed=True
            )
            # 如果差集结果面积和原梯形面积接近，说明没有被裁剪
            remaining = path_offset.boolean_difference_multi(
                [trap_path], forbidden_zones
            )
            original_area = self._polygon_area(trap_path.points)
            remaining_area = sum(
                self._polygon_area(r.points) for r in remaining
            )
            # 保留面积损失小于10%的梯形
            if original_area > 0 and remaining_area / original_area > 0.9:
                valid_trapezoids.append(trap)

        return valid_trapezoids

    # ================================================================
    # 核心算法：连续裙边带生成
    # ================================================================

    def _generate_continuous_skirt_polygons(
        self,
        contour_path: Path,
        params: SkirtParams,
        is_outer: bool,
        path_offset: 'PathOffset'
    ) -> List[Path]:
        """
        生成连续的锯齿形裙边多边形

        算法（每个梯形）：
        1. 沿轮廓等间距取两个端点作为���形的"顶边"（宽边，贴着字壳）
        2. 沿顶边中点的法线方向延伸 width 距离，取较窄的"底边"
        3. 在拐角处，插入轮廓顶点作为额外的内边点
        4. 底边宽度 = 顶边宽度的一半（梯形收缩）
        5. 每个梯形生成一个独立的闭合多边形

        与旧版的区别：
        - 底边使用 pyclipper offset 后的外轮廓来限制最大范围
        - 拐角处插入中间点，确保梯形跟随轮廓走
        - 最终所有梯形合并后再统一裁剪禁区

        Args:
            contour_path: 轮廓路径
            params: 裙边参数
            is_outer: 是否外部裙边
            path_offset: 路径偏移工具

        Returns:
            裙边多边形列表（每个梯形一个闭合多边形）
        """
        points = contour_path.points
        n = len(points)

        if n < 3:
            return []

        # 检测路径绕向
        signed_area = self._calculate_signed_area(points)
        is_ccw = signed_area > 0

        # 计算路径参数
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

        if total_length < params.interval:
            return []

        # 计算梯形数量和间距
        num_trapezoids = max(1, int(math.ceil(total_length / params.interval)))
        actual_interval = total_length / num_trapezoids

        skirt_width = params.width
        skirt_offset = params.offset

        # 决定法线方向
        use_outward = (is_ccw == is_outer)

        # 生成轮廓的外偏移线（用 pyclipper 的 offset 确保拐角处正确）
        # 这个偏移轮廓用于限制裙边的最大外边界
        from src.core.path_offset import JoinType
        offset_distance = skirt_offset + skirt_width
        if not use_outward:
            offset_distance = -offset_distance

        offset_paths = path_offset.offset(contour_path, offset_distance, JoinType.MITER)
        outer_boundary = offset_paths[0] if offset_paths else None

        # 生成每个梯形多边形
        result_polygons = []

        for i in range(num_trapezoids):
            # 梯形顶边的两个端点（沿原始轮廓的距离）
            dist_left = i * actual_interval
            dist_right = min((i + 1) * actual_interval, total_length - 0.001)

            # 获取原始轮廓上的点（内边点）和方向
            inner_left, dir_left = self._get_point_and_direction_at_distance(
                points, segment_lengths, cumulative_lengths, dist_left
            )
            inner_right, dir_right = self._get_point_and_direction_at_distance(
                points, segment_lengths, cumulative_lengths, dist_right
            )

            if inner_left is None or inner_right is None:
                continue

            # 计算法线
            if use_outward:
                nl = self._get_outward_normal(dir_left)
                nr = self._get_outward_normal(dir_right)
            else:
                nl = self._get_inward_normal(dir_left)
                nr = self._get_inward_normal(dir_right)

            # 应用 offset（内边点从轮廓线移到 skirt_offset 处）
            inner_left_pt = Point(
                inner_left[0] + nl[0] * skirt_offset,
                inner_left[1] + nl[1] * skirt_offset
            )
            inner_right_pt = Point(
                inner_right[0] + nr[0] * skirt_offset,
                inner_right[1] + nr[1] * skirt_offset
            )

            # 计算顶边中点和平均法线
            top_mid_x = (inner_left_pt.x + inner_right_pt.x) / 2
            top_mid_y = (inner_left_pt.y + inner_right_pt.y) / 2

            avg_normal_x = (nl[0] + nr[0]) / 2
            avg_normal_y = (nl[1] + nr[1]) / 2
            avg_normal_len = math.sqrt(avg_normal_x**2 + avg_normal_y**2)
            if avg_normal_len > 0.001:
                avg_normal_x /= avg_normal_len
                avg_normal_y /= avg_normal_len
            else:
                avg_normal_x, avg_normal_y = nl

            # 底边中点（沿法线方向延伸 skirt_width）
            bottom_mid_x = top_mid_x + avg_normal_x * skirt_width
            bottom_mid_y = top_mid_y + avg_normal_y * skirt_width

            # 顶边方向
            top_dir_x = inner_right_pt.x - inner_left_pt.x
            top_dir_y = inner_right_pt.y - inner_left_pt.y
            top_length = math.sqrt(top_dir_x**2 + top_dir_y**2)

            if top_length < 0.001:
                continue

            top_dir_x /= top_length
            top_dir_y /= top_length

            # 底边宽度 = 顶边宽度的一半（梯形收缩）
            bottom_half_width = top_length / 4

            # 动态调整底边宽度，避免穿过轮廓内部
            bottom_half_width = self._adjust_bottom_width(
                bottom_mid_x, bottom_mid_y,
                top_dir_x, top_dir_y,
                bottom_half_width,
                points
            )

            if bottom_half_width < 0.3:
                # 拐角太窄，生成三角形而不是完全跳过
                bottom_half_width = 0.0

            # 底边两端点
            outer_left_pt = Point(
                bottom_mid_x - top_dir_x * bottom_half_width,
                bottom_mid_y - top_dir_y * bottom_half_width
            )
            outer_right_pt = Point(
                bottom_mid_x + top_dir_x * bottom_half_width,
                bottom_mid_y + top_dir_y * bottom_half_width
            )

            # 如果底边宽度为0，生成三角形（尖角处的退化梯形）
            if bottom_half_width < 0.01:
                bottom_point = Point(bottom_mid_x, bottom_mid_y)
                outer_left_pt = bottom_point
                outer_right_pt = bottom_point

            # 收集内边上的中间拐角点（如果梯形跨越了轮廓顶点）
            inner_corner_pts = self._collect_contour_points_between(
                points, segment_lengths, cumulative_lengths,
                dist_left, dist_right, skirt_offset,
                use_outward
            )

            # 构建多边形：
            # 内边: inner_left -> [拐角点] -> inner_right（贴着字壳的宽边）
            # 外边: outer_right -> outer_left（远离字壳的窄边）
            poly_points = []

            # 内边（从左到右）
            poly_points.append(inner_left_pt)
            for pt in inner_corner_pts:
                poly_points.append(pt)
            poly_points.append(inner_right_pt)

            # 外边（从右到左）
            if bottom_half_width >= 0.01:
                poly_points.append(outer_right_pt)
                poly_points.append(outer_left_pt)
            else:
                # 三角形：只有一个底点
                poly_points.append(outer_left_pt)

            # 去除过近的重复点
            cleaned = self._remove_duplicate_points(poly_points, min_dist=0.05)
            if len(cleaned) >= 3:
                result_polygons.append(Path(points=cleaned, is_closed=True))

        # 将所有梯形做布尔并集，消除重叠
        if len(result_polygons) > 1:
            merged = path_offset.boolean_union(result_polygons)
            if merged:
                # 再与外边界做交集，确保不超出最大范围
                if outer_boundary and len(outer_boundary.points) >= 3:
                    clipped = path_offset.boolean_intersection_multi(
                        merged, [outer_boundary]
                    )
                    if clipped:
                        return clipped
                return merged

        return result_polygons

    def _collect_contour_points_between(
        self,
        points: List[Point],
        segment_lengths: List[float],
        cumulative_lengths: List[float],
        dist_start: float,
        dist_end: float,
        skirt_offset: float,
        use_outward: bool
    ) -> List[Point]:
        """
        收集 dist_start 和 dist_end 之间的轮廓顶点

        在拐角处，裙边需要跟随轮廓的顶点弯曲。
        这个方法收集两个距离之间经过的所有轮廓顶点。

        Args:
            points: 轮廓点列表
            segment_lengths: 每段长度
            cumulative_lengths: 累积长度
            dist_start: 起始距离
            dist_end: 结束距离
            skirt_offset: 裙边偏移
            use_outward: 是否使用外向法线

        Returns:
            中间轮廓顶点列表（已应用偏移）
        """
        result = []
        n = len(points)

        for i in range(n):
            vertex_dist = cumulative_lengths[i + 1] if i + 1 < len(cumulative_lengths) else cumulative_lengths[-1]

            # 检查顶点是否在范围内（排除端点本身）
            if dist_start < vertex_dist < dist_end:
                vertex_idx = (i + 1) % n
                pt = points[vertex_idx]

                if skirt_offset > 0:
                    # 计算顶点处的法线（取两侧线段法线的角平分线）
                    prev_idx = i
                    next_idx = (vertex_idx + 1) % n

                    dx1 = points[vertex_idx].x - points[prev_idx].x
                    dy1 = points[vertex_idx].y - points[prev_idx].y
                    len1 = math.sqrt(dx1*dx1 + dy1*dy1)

                    dx2 = points[next_idx].x - points[vertex_idx].x
                    dy2 = points[next_idx].y - points[vertex_idx].y
                    len2 = math.sqrt(dx2*dx2 + dy2*dy2)

                    if len1 > 0.001 and len2 > 0.001:
                        dx1 /= len1; dy1 /= len1
                        dx2 /= len2; dy2 /= len2

                        if use_outward:
                            n1 = self._get_outward_normal((dx1, dy1))
                            n2 = self._get_outward_normal((dx2, dy2))
                        else:
                            n1 = self._get_inward_normal((dx1, dy1))
                            n2 = self._get_inward_normal((dx2, dy2))

                        # 角平分线
                        avg_nx = (n1[0] + n2[0]) / 2
                        avg_ny = (n1[1] + n2[1]) / 2
                        avg_len = math.sqrt(avg_nx*avg_nx + avg_ny*avg_ny)
                        if avg_len > 0.001:
                            avg_nx /= avg_len
                            avg_ny /= avg_len

                        result.append(Point(
                            pt.x + avg_nx * skirt_offset,
                            pt.y + avg_ny * skirt_offset
                        ))
                    else:
                        result.append(pt)
                else:
                    result.append(pt)

        return result

    def _collect_outer_points_between(
        self,
        inner_points: List[Point],
        outer_boundary: Path
    ) -> List[Point]:
        """
        对每个内边中间点，在外边界上找到对应的最近点

        Args:
            inner_points: 内边中间点列表
            outer_boundary: 外边界路径

        Returns:
            对应的外边界点列表
        """
        return [
            self._find_nearest_point_on_path(pt, outer_boundary)
            for pt in inner_points
        ]

    def _find_nearest_point_on_path(self, point: Point, path: Path) -> Point:
        """
        在路径上找到离给定点最近的点

        遍历路径的每一条边，计算点到线段的最近距离。

        Args:
            point: 查询点
            path: 目标路径

        Returns:
            路径上的最近点
        """
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

    def _remove_duplicate_points(
        self, points: List[Point], min_dist: float = 0.1
    ) -> List[Point]:
        """移除过近的重复点"""
        if not points:
            return []

        result = [points[0]]
        min_dist_sq = min_dist * min_dist

        for i in range(1, len(points)):
            dx = points[i].x - result[-1].x
            dy = points[i].y - result[-1].y
            if dx * dx + dy * dy >= min_dist_sq:
                result.append(points[i])

        # 检查首尾
        if len(result) > 2:
            dx = result[0].x - result[-1].x
            dy = result[0].y - result[-1].y
            if dx * dx + dy * dy < min_dist_sq:
                result.pop()

        return result

    # ================================================================
    # 禁区构建
    # ================================================================

    def _build_forbidden_zones(
        self,
        current_contour: Contour,
        all_contours: List[Contour],
        wall_thickness: float,
        path_offset: 'PathOffset',
        skirt_params: Optional[SkirtParams] = None
    ) -> List[Path]:
        """
        构建禁区

        禁区包括：
        1. 其他轮廓的外轮廓（防止裙边进入其他字母内部）
        2. 其他轮廓的外轮廓向外扩展 wall_thickness（防止裙边太靠近其他字母壁）
        3. 所有轮廓的内孔扩展 wall_thickness（防止裙边进入孔壁区域）
           - 但对于内孔裙边（is_outer=False），跳过当前正在生成裙边的那个孔
        4. 当前轮廓的内部区域（防止裙边穿入自身内部）——对外裙边

        Args:
            current_contour: 当前轮廓
            all_contours: 所有轮廓
            wall_thickness: 壁厚
            path_offset: 路径偏移工具
            skirt_params: 裙边参数

        Returns:
            禁区路径列表
        """
        from src.core.path_offset import JoinType

        forbidden = []
        is_inner_skirt = skirt_params is not None and not skirt_params.is_outer

        # 对于内孔裙边：current_contour.outer 实际上是某个轮廓的 hole，
        # 需要找到这个 hole 所属的父轮廓，并排除相关禁区
        parent_contour = None
        if is_inner_skirt:
            current_hole_path = current_contour.outer
            for contour in all_contours:
                for hole in contour.holes:
                    if hole is current_hole_path or self._paths_are_same(hole, current_hole_path):
                        parent_contour = contour
                        break
                if parent_contour is not None:
                    break

        for contour in all_contours:
            is_current = (contour is current_contour)
            is_parent = (parent_contour is not None and contour is parent_contour)

            if not is_current and not is_parent and len(contour.outer.points) >= 3:
                # 其他轮廓的外轮廓直接作为禁区
                forbidden.append(contour.outer)

                # 还需要将其他轮廓外扩 wall_thickness，确保裙边不贴着其他字母壁
                expanded = path_offset.offset(
                    contour.outer, wall_thickness, JoinType.ROUND
                )
                forbidden.extend(expanded)

            # 所有轮廓的内孔扩展 wall_thickness
            # 对于内孔裙边：跳过当前轮廓（或父轮廓）的所有内孔，
            # 因为裙边就是要在这些孔内侧生成的
            if is_inner_skirt and (is_current or is_parent):
                pass  # 不把当前/父轮廓的孔加入禁区
            else:
                for hole in contour.holes:
                    if len(hole.points) >= 3:
                        expanded_holes = path_offset.offset(
                            hole, wall_thickness, JoinType.ROUND
                        )
                        forbidden.extend(expanded_holes)

        return forbidden

    @staticmethod
    def _paths_are_same(path_a: Path, path_b: Path) -> bool:
        """判断两个 Path 是否是同一个孔（基于点坐标匹配）"""
        if path_a is path_b:
            return True
        if len(path_a.points) != len(path_b.points):
            return False
        for pa, pb in zip(path_a.points, path_b.points):
            if abs(pa.x - pb.x) > 0.001 or abs(pa.y - pb.y) > 0.001:
                return False
        return True

    # ================================================================
    # 旧版梯形生成（保持兼容，用于 generate_skirt / generate_skirt_3d / STL）
    # ================================================================

    def _generate_outer_skirt(self, outer_path: Path,
                              params: SkirtParams) -> List[LayerPath]:
        """生成外部防翘裙边的打印路径（G-code用，无裁剪）"""
        paths = []
        trapezoids = self._generate_trapezoids_along_path(
            outer_path, params, is_outer=True
        )

        for trap in trapezoids:
            points = [
                trap.top_left,
                trap.bottom_left,
                trap.bottom_right,
                trap.top_right
            ]
            layer_path = LayerPath(
                points=points,
                role=PathRole.SKIRT,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=params.extrusion_width,
                is_closed=True
            )
            paths.append(layer_path)

        return paths

    def _generate_inner_skirt(self, hole_path: Path,
                              params: SkirtParams) -> List[LayerPath]:
        """生成内部防翘裙边"""
        paths = []
        trapezoids = self._generate_trapezoids_along_path(
            hole_path, params, is_outer=False
        )

        for trap in trapezoids:
            points = [
                trap.top_left,
                trap.bottom_left,
                trap.bottom_right,
                trap.top_right
            ]
            layer_path = LayerPath(
                points=points,
                role=PathRole.SKIRT,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=params.extrusion_width,
                is_closed=True
            )
            paths.append(layer_path)

        return paths

    def _trapezoids_to_layer_paths(
        self,
        trapezoids: List[TrapezoidSkirt],
        params: SkirtParams
    ) -> List[LayerPath]:
        """将梯形列表转换为打印路径列表"""
        paths = []
        for trap in trapezoids:
            points = [
                trap.top_left,
                trap.bottom_left,
                trap.bottom_right,
                trap.top_right
            ]
            layer_path = LayerPath(
                points=points,
                role=PathRole.SKIRT,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=params.extrusion_width,
                is_closed=True
            )
            paths.append(layer_path)
        return paths

    # ================================================================
    # 梯形生成算法（用于STL和无裁剪场景）
    # ================================================================

    def _generate_trapezoids_along_path(self, path: Path,
                                         params: SkirtParams,
                                         is_outer: bool) -> List[TrapezoidSkirt]:
        """
        沿路径生成连续的梯形裙边

        Args:
            path: 轮廓路径
            params: 裙边参数
            is_outer: 是否外部轮廓

        Returns:
            梯形列表
        """
        trapezoids = []
        points = path.points
        n = len(points)

        if n < 2:
            return trapezoids

        signed_area = self._calculate_signed_area(points)
        is_ccw = signed_area > 0

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

        if total_length < params.interval:
            return trapezoids

        num_trapezoids = max(1, int(math.ceil(total_length / params.interval)))
        actual_interval = total_length / num_trapezoids

        skirt_width = params.width
        skirt_offset = params.offset

        for i in range(num_trapezoids):
            dist_left = i * actual_interval
            dist_right = min((i + 1) * actual_interval, total_length)

            pos_left, dir_left = self._get_point_and_direction_at_distance(
                points, segment_lengths, cumulative_lengths, dist_left
            )
            pos_right, dir_right = self._get_point_and_direction_at_distance(
                points, segment_lengths, cumulative_lengths, dist_right
            )

            if pos_left is None or pos_right is None:
                continue

            if is_ccw == is_outer:
                normal_left = self._get_outward_normal(dir_left)
                normal_right = self._get_outward_normal(dir_right)
            else:
                normal_left = self._get_inward_normal(dir_left)
                normal_right = self._get_inward_normal(dir_right)

            top_left = Point(
                pos_left[0] + normal_left[0] * skirt_offset,
                pos_left[1] + normal_left[1] * skirt_offset
            )
            top_right = Point(
                pos_right[0] + normal_right[0] * skirt_offset,
                pos_right[1] + normal_right[1] * skirt_offset
            )

            top_mid_x = (top_left.x + top_right.x) / 2
            top_mid_y = (top_left.y + top_right.y) / 2

            avg_normal_x = (normal_left[0] + normal_right[0]) / 2
            avg_normal_y = (normal_left[1] + normal_right[1]) / 2
            avg_normal_len = math.sqrt(avg_normal_x**2 + avg_normal_y**2)
            if avg_normal_len > 0:
                avg_normal_x /= avg_normal_len
                avg_normal_y /= avg_normal_len

            bottom_mid_x = top_mid_x + avg_normal_x * skirt_width
            bottom_mid_y = top_mid_y + avg_normal_y * skirt_width

            top_dir_x = top_right.x - top_left.x
            top_dir_y = top_right.y - top_left.y
            top_length = math.sqrt(top_dir_x**2 + top_dir_y**2)

            if top_length < 0.001:
                continue

            top_dir_x /= top_length
            top_dir_y /= top_length

            bottom_half_width = top_length / 4

            bottom_half_width = self._adjust_bottom_width(
                bottom_mid_x, bottom_mid_y,
                top_dir_x, top_dir_y,
                bottom_half_width,
                points
            )

            if bottom_half_width < 0.5:
                continue

            bottom_left = Point(
                bottom_mid_x - top_dir_x * bottom_half_width,
                bottom_mid_y - top_dir_y * bottom_half_width
            )
            bottom_right = Point(
                bottom_mid_x + top_dir_x * bottom_half_width,
                bottom_mid_y + top_dir_y * bottom_half_width
            )

            trapezoid = TrapezoidSkirt(
                top_left=top_left,
                top_right=top_right,
                bottom_left=bottom_left,
                bottom_right=bottom_right
            )
            trapezoids.append(trapezoid)

        return trapezoids

    # ================================================================
    # 辅助方法
    # ================================================================

    def _calculate_signed_area(self, points: List[Point]) -> float:
        """计算路径的有向面积（> 0 = 逆时针 CCW）"""
        area = 0.0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y
        return area / 2.0

    def _polygon_area(self, points: List[Point]) -> float:
        """计算多边形面积（绝对值）"""
        return abs(self._calculate_signed_area(points))

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
        """获取朝外的法线（假设路径是逆时针方向）"""
        dx, dy = direction
        return (dy, -dx)

    def _get_inward_normal(self, direction: Tuple[float, float]) -> Tuple[float, float]:
        """获取朝内的法线"""
        dx, dy = direction
        return (-dy, dx)

    def _point_in_polygon(self, point: Point, polygon: List[Point]) -> bool:
        """判断点是否在多边形内部（射线法）"""
        x, y = point.x, point.y
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0].x, polygon[0].y
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _adjust_bottom_width(
        self,
        bottom_mid_x: float,
        bottom_mid_y: float,
        dir_x: float,
        dir_y: float,
        initial_width: float,
        polygon: List[Point]
    ) -> float:
        """动态调整梯形底边宽度，避免底边与轮廓边相交"""
        left = Point(bottom_mid_x - dir_x * initial_width, bottom_mid_y - dir_y * initial_width)
        right = Point(bottom_mid_x + dir_x * initial_width, bottom_mid_y + dir_y * initial_width)

        if not self._segment_intersects_polygon(left, right, polygon):
            return initial_width

        min_width = 0.1
        max_width = initial_width
        best_width = min_width

        for _ in range(10):
            mid_width = (min_width + max_width) / 2
            test_left = Point(bottom_mid_x - dir_x * mid_width, bottom_mid_y - dir_y * mid_width)
            test_right = Point(bottom_mid_x + dir_x * mid_width, bottom_mid_y + dir_y * mid_width)

            if self._segment_intersects_polygon(test_left, test_right, polygon):
                max_width = mid_width
            else:
                best_width = mid_width
                min_width = mid_width

        return best_width

    def _segment_intersects_polygon(self, p1: Point, p2: Point, polygon: List[Point]) -> bool:
        """检测线段是否与多边形的边相交"""
        n = len(polygon)
        for i in range(n):
            j = (i + 1) % n
            if self._segments_intersect(p1, p2, polygon[i], polygon[j]):
                return True
        return False

    def _segments_intersect(self, p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
        """检测两条线段是否相交"""
        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        a = (p1.x, p1.y); b = (p2.x, p2.y)
        c = (p3.x, p3.y); d = (p4.x, p4.y)

        d1 = cross(c, d, a)
        d2 = cross(c, d, b)
        d3 = cross(a, b, c)
        d4 = cross(a, b, d)

        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
           ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
            return True

        return False

    def _remove_overlapping_trapezoids(self, trapezoids: List[TrapezoidSkirt]) -> List[TrapezoidSkirt]:
        """去除相互重叠的梯形"""
        if len(trapezoids) <= 1:
            return trapezoids

        result = []
        for trap in trapezoids:
            overlaps = False
            for accepted in result:
                if self._trapezoids_overlap(trap, accepted):
                    overlaps = True
                    break
            if not overlaps:
                result.append(trap)

        return result

    def _trapezoids_overlap(self, t1: TrapezoidSkirt, t2: TrapezoidSkirt) -> bool:
        """检测两个梯形是否重叠"""
        t2_pts = [t2.top_left, t2.bottom_left, t2.bottom_right, t2.top_right]
        t1_pts = [t1.top_left, t1.bottom_left, t1.bottom_right, t1.top_right]

        c1_x = (t1.top_left.x + t1.bottom_left.x + t1.top_right.x + t1.bottom_right.x) / 4
        c1_y = (t1.top_left.y + t1.bottom_left.y + t1.top_right.y + t1.bottom_right.y) / 4
        if self._point_in_polygon(Point(c1_x, c1_y), t2_pts):
            return True

        c2_x = (t2.top_left.x + t2.bottom_left.x + t2.top_right.x + t2.bottom_right.x) / 4
        c2_y = (t2.top_left.y + t2.bottom_left.y + t2.top_right.y + t2.bottom_right.y) / 4
        if self._point_in_polygon(Point(c2_x, c2_y), t1_pts):
            return True

        b1_mid = Point((t1.bottom_left.x + t1.bottom_right.x) / 2, (t1.bottom_left.y + t1.bottom_right.y) / 2)
        if self._point_in_polygon(b1_mid, t2_pts):
            return True

        b2_mid = Point((t2.bottom_left.x + t2.bottom_right.x) / 2, (t2.bottom_left.y + t2.bottom_right.y) / 2)
        if self._point_in_polygon(b2_mid, t1_pts):
            return True

        return False

    def _distribute_along_path(self, path: Path,
                               interval: float) -> List[Tuple[Point, Tuple[float, float]]]:
        """沿路径分布裙边位置（保持兼容）"""
        positions = []
        points = path.points
        n = len(points)

        if n < 2:
            return positions

        total_length = 0
        segment_lengths = []
        for i in range(n):
            j = (i + 1) % n
            length = math.sqrt(
                (points[j].x - points[i].x) ** 2 +
                (points[j].y - points[i].y) ** 2
            )
            segment_lengths.append(length)
            total_length += length

        current_distance = interval / 2
        current_segment = 0
        distance_in_segment = 0

        while current_distance < total_length:
            while (current_segment < n and
                   distance_in_segment + segment_lengths[current_segment] < current_distance):
                distance_in_segment += segment_lengths[current_segment]
                current_segment += 1

            if current_segment >= n:
                break

            i = current_segment
            j = (i + 1) % n
            segment_length = segment_lengths[i]

            if segment_length > 0:
                t = (current_distance - distance_in_segment) / segment_length
                pos = Point(
                    points[i].x + t * (points[j].x - points[i].x),
                    points[i].y + t * (points[j].y - points[i].y)
                )

                dx = points[j].x - points[i].x
                dy = points[j].y - points[i].y
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    direction = (dx / length, dy / length)
                    positions.append((pos, direction))

            current_distance += interval

        return positions
