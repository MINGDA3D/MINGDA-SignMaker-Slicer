"""
MINGDA SignMaker - 路径偏移模块

使用pyclipper库进行路径的内/外偏移操作，支持：
- 单路径偏移（内缩/外扩）
- 轮廓偏移（外轮廓和内孔方向相反）
- 多次偏移（用于多壁生成）
- 布尔运算（并集、差集、交集）
- 路径简化和清理
"""

from __future__ import annotations
from typing import List, Tuple, Optional
from enum import Enum

import pyclipper

from .types import Point, Path, Contour, PathType, JoinType


class EndType(Enum):
    """端点类型"""
    CLOSED_POLYGON = pyclipper.ET_CLOSEDPOLYGON
    CLOSED_LINE = pyclipper.ET_CLOSEDLINE
    OPEN_ROUND = pyclipper.ET_OPENROUND
    OPEN_SQUARE = pyclipper.ET_OPENSQUARE
    OPEN_BUTT = pyclipper.ET_OPENBUTT


# pyclipper JoinType映射
PYCLIPPER_JOIN_TYPE = {
    JoinType.MITER: pyclipper.JT_MITER,
    JoinType.ROUND: pyclipper.JT_ROUND,
    JoinType.SQUARE: pyclipper.JT_SQUARE,
}


class PathOffset:
    """路径偏移处理器"""

    SCALE = 1000  # 缩放因子（pyclipper使用整数运算）
    MITER_LIMIT = 2.0  # 尖角限制
    ARC_TOLERANCE = 0.25  # 圆弧容差

    def __init__(self, scale: float = 1000, miter_limit: float = 2.0):
        """
        初始化偏移处理器

        Args:
            scale: 坐标缩放因子（pyclipper使用整数）
            miter_limit: 尖角限制
        """
        self.scale = scale
        self.miter_limit = miter_limit

    def offset(self, path: Path, distance: float,
               join_type: JoinType = JoinType.MITER) -> List[Path]:
        """
        对单个路径进行偏移

        Args:
            path: 输入路径
            distance: 偏移距离（正=外扩，负=内缩）
            join_type: 拐角处理方式

        Returns:
            偏移后的路径列表（可能产生多个或为空）
        """
        if not path.points or len(path.points) < 3:
            return []

        # 转换为整数坐标
        scaled_path = self._scale_path(path)

        # 创建偏移器
        pco = pyclipper.PyclipperOffset()
        pco.MiterLimit = self.miter_limit
        pco.ArcTolerance = self.ARC_TOLERANCE * self.scale

        # 添加路径
        pyclipper_join = PYCLIPPER_JOIN_TYPE.get(join_type, pyclipper.JT_MITER)
        end_type = EndType.CLOSED_POLYGON.value if path.is_closed else EndType.OPEN_ROUND.value

        try:
            pco.AddPath(scaled_path, pyclipper_join, end_type)
        except Exception:
            return []

        # 执行偏移
        scaled_distance = distance * self.scale
        try:
            solution = pco.Execute(scaled_distance)
        except Exception:
            return []

        # 转换回浮点坐标
        result_paths = []
        for scaled_result in solution:
            points = [Point(p[0] / self.scale, p[1] / self.scale)
                      for p in scaled_result]
            if len(points) >= 3:
                result_paths.append(Path(
                    points=points,
                    path_type=path.path_type,
                    is_closed=True
                ))

        return result_paths

    def offset_contour(self, contour: Contour, distance: float,
                       join_type: JoinType = JoinType.MITER) -> Optional[Contour]:
        """
        对整个轮廓进行偏移

        外轮廓和内孔的偏移方向相反：
        - 外扩时：外轮廓向外，内孔向内
        - 内缩时：外轮廓向内，内孔向外

        Args:
            contour: 输入轮廓
            distance: 偏移距离
            join_type: 拐角处理方式

        Returns:
            偏移后的轮廓，如果消失则返回None
        """
        # 偏移外轮廓
        outer_results = self.offset(contour.outer, distance, join_type)
        if not outer_results:
            return None

        new_outer = outer_results[0]

        # 偏移内孔（方向相反）
        new_holes = []
        for hole in contour.holes:
            hole_results = self.offset(hole, -distance, join_type)
            new_holes.extend(hole_results)

        return Contour(
            outer=new_outer,
            holes=new_holes,
            connected_frames=contour.connected_frames,
            patterns=contour.patterns,
            name=contour.name
        )

    def multi_offset(self, path: Path, distances: List[float],
                     join_type: JoinType = JoinType.MITER) -> List[List[Path]]:
        """
        对路径进行多次偏移（用于多壁生成）

        Args:
            path: 输入路径
            distances: 偏移距离列表

        Returns:
            每个偏移距离对应的路径列表
        """
        results = []
        for distance in distances:
            offset_paths = self.offset(path, distance, join_type)
            results.append(offset_paths)
        return results

    def inward_offsets(self, path: Path, offset_distance: float,
                       count: int, join_type: JoinType = JoinType.MITER) -> List[Path]:
        """
        生成多个向内偏移的路径（用于生成多壁）

        Args:
            path: 输入路径
            offset_distance: 每次偏移的距离
            count: 偏移次数

        Returns:
            所有偏移路径的列表
        """
        all_paths = []
        current_paths = [path]

        for i in range(count):
            next_paths = []
            for p in current_paths:
                offset_result = self.offset(p, -offset_distance, join_type)
                next_paths.extend(offset_result)
                all_paths.extend(offset_result)
            current_paths = next_paths
            if not current_paths:
                break

        return all_paths

    def boolean_union(self, paths: List[Path]) -> List[Path]:
        """
        布尔并集运算

        将多个路径合并为一个或多个不重叠的路径
        """
        if not paths:
            return []

        pc = pyclipper.Pyclipper()

        for i, path in enumerate(paths):
            if len(path.points) < 3:
                continue
            scaled = self._scale_path(path)
            try:
                if i == 0:
                    pc.AddPath(scaled, pyclipper.PT_SUBJECT, True)
                else:
                    pc.AddPath(scaled, pyclipper.PT_CLIP, True)
            except Exception:
                continue

        try:
            solution = pc.Execute(pyclipper.CT_UNION,
                                  pyclipper.PFT_NONZERO,
                                  pyclipper.PFT_NONZERO)
        except Exception:
            return []

        return self._unscale_paths(solution)

    def boolean_difference(self, subject: Path, clip: Path) -> List[Path]:
        """
        布尔差集运算

        从subject中减去clip区域
        """
        if len(subject.points) < 3 or len(clip.points) < 3:
            return [subject] if len(subject.points) >= 3 else []

        pc = pyclipper.Pyclipper()

        try:
            pc.AddPath(self._scale_path(subject), pyclipper.PT_SUBJECT, True)
            pc.AddPath(self._scale_path(clip), pyclipper.PT_CLIP, True)
        except Exception:
            return [subject]

        try:
            solution = pc.Execute(pyclipper.CT_DIFFERENCE,
                                  pyclipper.PFT_NONZERO,
                                  pyclipper.PFT_NONZERO)
        except Exception:
            return [subject]

        return self._unscale_paths(solution)

    def boolean_difference_multi(self, subjects: List[Path],
                                  clips: List[Path]) -> List[Path]:
        """
        多路径布尔差集运算

        从所有subjects中减去所有clips区域
        """
        valid_subjects = [s for s in subjects if len(s.points) >= 3]
        valid_clips = [c for c in clips if len(c.points) >= 3]

        if not valid_subjects:
            return []
        if not valid_clips:
            return valid_subjects

        pc = pyclipper.Pyclipper()

        try:
            for s in valid_subjects:
                pc.AddPath(self._scale_path(s), pyclipper.PT_SUBJECT, True)
            for c in valid_clips:
                pc.AddPath(self._scale_path(c), pyclipper.PT_CLIP, True)
        except Exception:
            return valid_subjects

        try:
            solution = pc.Execute(pyclipper.CT_DIFFERENCE,
                                  pyclipper.PFT_NONZERO,
                                  pyclipper.PFT_NONZERO)
        except Exception:
            return valid_subjects

        return self._unscale_paths(solution)

    def boolean_intersection_multi(self, subjects: List[Path],
                                    clips: List[Path]) -> List[Path]:
        """
        多路径布尔交集运算

        返回所有subjects与所有clips的重叠区域
        """
        valid_subjects = [s for s in subjects if len(s.points) >= 3]
        valid_clips = [c for c in clips if len(c.points) >= 3]

        if not valid_subjects or not valid_clips:
            return []

        pc = pyclipper.Pyclipper()

        try:
            for s in valid_subjects:
                pc.AddPath(self._scale_path(s), pyclipper.PT_SUBJECT, True)
            for c in valid_clips:
                pc.AddPath(self._scale_path(c), pyclipper.PT_CLIP, True)
        except Exception:
            return []

        try:
            solution = pc.Execute(pyclipper.CT_INTERSECTION,
                                  pyclipper.PFT_NONZERO,
                                  pyclipper.PFT_NONZERO)
        except Exception:
            return []

        return self._unscale_paths(solution)

    def boolean_intersection(self, subject: Path, clip: Path) -> List[Path]:
        """
        布尔交集运算

        返回subject和clip的重叠区域
        """
        if len(subject.points) < 3 or len(clip.points) < 3:
            return []

        pc = pyclipper.Pyclipper()

        try:
            pc.AddPath(self._scale_path(subject), pyclipper.PT_SUBJECT, True)
            pc.AddPath(self._scale_path(clip), pyclipper.PT_CLIP, True)
        except Exception:
            return []

        try:
            solution = pc.Execute(pyclipper.CT_INTERSECTION,
                                  pyclipper.PFT_NONZERO,
                                  pyclipper.PFT_NONZERO)
        except Exception:
            return []

        return self._unscale_paths(solution)

    def boolean_xor(self, subject: Path, clip: Path) -> List[Path]:
        """
        布尔异或运算

        返回subject和clip的非重叠区域
        """
        if len(subject.points) < 3 or len(clip.points) < 3:
            return []

        pc = pyclipper.Pyclipper()

        try:
            pc.AddPath(self._scale_path(subject), pyclipper.PT_SUBJECT, True)
            pc.AddPath(self._scale_path(clip), pyclipper.PT_CLIP, True)
        except Exception:
            return []

        try:
            solution = pc.Execute(pyclipper.CT_XOR,
                                  pyclipper.PFT_NONZERO,
                                  pyclipper.PFT_NONZERO)
        except Exception:
            return []

        return self._unscale_paths(solution)

    def simplify_path(self, path: Path, tolerance: float = 0.1) -> Path:
        """
        简化路径（移除共线点和过近点）

        Args:
            path: 输入路径
            tolerance: 简化容差

        Returns:
            简化后的路径
        """
        if len(path.points) < 3:
            return path

        scaled = self._scale_path(path)
        try:
            simplified = pyclipper.SimplifyPolygon(
                scaled,
                pyclipper.PFT_NONZERO
            )
        except Exception:
            return path

        if simplified and len(simplified) > 0:
            points = [Point(p[0] / self.scale, p[1] / self.scale)
                      for p in simplified[0]]
            if len(points) >= 3:
                return Path(
                    points=points,
                    path_type=path.path_type,
                    color=path.color,
                    is_closed=path.is_closed
                )

        return path

    def clean_path(self, path: Path, distance: float = 0.1) -> Path:
        """
        清理路径（移除过近的点）

        Args:
            path: 输入路径
            distance: 最小点距离

        Returns:
            清理后的路径
        """
        if len(path.points) < 3:
            return path

        scaled = self._scale_path(path)
        try:
            cleaned = pyclipper.CleanPolygon(scaled, distance * self.scale)
        except Exception:
            return path

        if cleaned and len(cleaned) >= 3:
            points = [Point(p[0] / self.scale, p[1] / self.scale)
                      for p in cleaned]
            return Path(
                points=points,
                path_type=path.path_type,
                color=path.color,
                is_closed=path.is_closed
            )

        return path

    def minkowski_sum(self, path: Path, pattern: Path) -> List[Path]:
        """
        Minkowski和运算

        用pattern沿着path的边界滑动生成的区域

        Args:
            path: 基础路径
            pattern: 滑动图案（通常是圆形）

        Returns:
            结果路径列表
        """
        if len(path.points) < 3 or len(pattern.points) < 3:
            return [path]

        scaled_path = self._scale_path(path)
        scaled_pattern = self._scale_path(pattern)

        try:
            solution = pyclipper.MinkowskiSum(
                scaled_pattern, scaled_path, True
            )
        except Exception:
            return [path]

        return self._unscale_paths(solution)

    def _scale_path(self, path: Path) -> List[Tuple[int, int]]:
        """将路径坐标缩放为整数"""
        return [(int(p.x * self.scale), int(p.y * self.scale))
                for p in path.points]

    def _unscale_paths(self, scaled_paths: List) -> List[Path]:
        """将整数坐标转换回浮点路径"""
        result = []
        for scaled in scaled_paths:
            if len(scaled) < 3:
                continue
            points = [Point(p[0] / self.scale, p[1] / self.scale)
                      for p in scaled]
            result.append(Path(points=points, is_closed=True))
        return result

    def create_round_brush(self, radius: float, segments: int = 16) -> Path:
        """
        创建圆形画笔（用于Minkowski运算）

        Args:
            radius: 圆形半径
            segments: 分段数

        Returns:
            圆形路径
        """
        import math
        points = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            points.append(Point(x, y))

        return Path(points=points, is_closed=True)
