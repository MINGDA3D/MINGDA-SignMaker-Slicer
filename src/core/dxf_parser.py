"""
SignMaker Slicer - DXF文件解析模块

将DXF文件解析为内部Contour数据结构，包括：
- 提取图形实体（LWPOLYLINE, POLYLINE, LINE, SPLINE, ARC, CIRCLE）
- 识别路径颜色并分类（普通轮廓、连襟框、底孔、面板花纹）
- 建立外轮廓与内孔的包含关系
"""

from __future__ import annotations
import math
from typing import List, Tuple, Optional, Dict
from pathlib import Path as FilePath

import ezdxf
from ezdxf.entities import DXFEntity

from .types import Point, Path, Contour, PathType


class DXFParser:
    """DXF文件解析器"""

    # 标准RGB颜色映射（用于识别特殊路径）
    COLOR_MAP: Dict[Tuple[int, int, int], PathType] = {
        (0, 255, 255): PathType.CONNECTED,   # 青色 → 连襟框
        (0, 255, 0): PathType.HOLE,          # 绿色 → 底孔
        (0, 0, 255): PathType.PATTERN,       # 蓝色 → 面板花纹
    }

    # DXF ACI颜色索引到RGB的映射
    ACI_TO_RGB: Dict[int, Tuple[int, int, int]] = {
        0: (0, 0, 0),          # ByBlock
        1: (255, 0, 0),        # 红
        2: (255, 255, 0),      # 黄
        3: (0, 255, 0),        # 绿
        4: (0, 255, 255),      # 青
        5: (0, 0, 255),        # 蓝
        6: (255, 0, 255),      # 紫/品红
        7: (255, 255, 255),    # 白
        8: (128, 128, 128),    # 灰
        9: (192, 192, 192),    # 浅灰
        10: (255, 0, 0),
        11: (255, 127, 127),
        12: (204, 0, 0),
        13: (204, 102, 102),
        14: (153, 0, 0),
        15: (153, 76, 76),
        16: (127, 0, 0),
        17: (127, 63, 63),
        18: (76, 0, 0),
        19: (76, 38, 38),
        20: (255, 63, 0),
        21: (255, 159, 127),
        22: (204, 51, 0),
        23: (204, 127, 102),
        24: (153, 38, 0),
        25: (153, 95, 76),
        30: (255, 127, 0),
        31: (255, 191, 127),
        40: (255, 191, 0),
        41: (255, 223, 127),
        50: (255, 255, 0),
        51: (255, 255, 127),
        60: (191, 255, 0),
        70: (127, 255, 0),
        80: (63, 255, 0),
        90: (0, 255, 0),
        100: (0, 255, 63),
        110: (0, 255, 127),
        120: (0, 255, 191),
        130: (0, 255, 255),
        140: (0, 191, 255),
        150: (0, 127, 255),
        160: (0, 63, 255),
        170: (0, 0, 255),
        180: (63, 0, 255),
        190: (127, 0, 255),
        200: (191, 0, 255),
        210: (255, 0, 255),
        220: (255, 0, 191),
        230: (255, 0, 127),
        240: (255, 0, 63),
        250: (84, 84, 84),
        251: (118, 118, 118),
        252: (152, 152, 152),
        253: (186, 186, 186),
        254: (220, 220, 220),
        255: (255, 255, 255),
        256: (0, 0, 0),        # ByLayer
    }

    # 平滑度控制参数
    DEFAULT_CHORD_ERROR = 0.05  # 默认弦长误差 (mm)，越小越平滑
    MIN_SEGMENTS_PER_ARC = 8    # 每个圆弧最少分段数
    MAX_SEGMENTS_PER_ARC = 360  # 每个圆弧最多分段数

    def __init__(self, arc_resolution: int = 128, spline_resolution: int = 100,
                 chord_error: float = 0.05):
        """
        初始化解析器

        Args:
            arc_resolution: 完整圆的基础分辨率（点数）
            spline_resolution: 样条曲线离散化分辨率
            chord_error: 弦长误差阈值 (mm)，越小越平滑
        """
        self.arc_resolution = arc_resolution
        self.spline_resolution = spline_resolution
        self.chord_error = chord_error

    def parse(self, file_path: str) -> List[Contour]:
        """
        解析DXF文件

        Args:
            file_path: DXF文件路径

        Returns:
            轮廓列表，每个轮廓包含外边界和内孔
        """
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()

        # 1. 提取所有路径实体
        paths = self._extract_all_paths(msp)

        # 2. 分类路径（外轮廓、内孔、特殊路径）
        contours = self._classify_and_group_paths(paths)

        return contours

    def parse_from_bytes(self, data: bytes) -> List[Contour]:
        """
        从字节数据解析DXF

        Args:
            data: DXF文件的字节内容

        Returns:
            轮廓列表
        """
        import io
        stream = io.StringIO(data.decode('utf-8', errors='ignore'))
        doc = ezdxf.read(stream)
        msp = doc.modelspace()

        paths = self._extract_all_paths(msp)
        contours = self._classify_and_group_paths(paths)

        return contours

    def _extract_all_paths(self, msp) -> List[Path]:
        """提取模型空间中的所有路径"""
        paths = []

        for entity in msp:
            path = self._parse_entity(entity)
            if path and len(path.points) >= 3:
                paths.append(path)

        return paths

    def _parse_entity(self, entity: DXFEntity) -> Optional[Path]:
        """解析单个实体"""
        entity_type = entity.dxftype()

        if entity_type == 'LWPOLYLINE':
            return self._parse_lwpolyline(entity)
        elif entity_type == 'POLYLINE':
            return self._parse_polyline(entity)
        elif entity_type == 'LINE':
            return self._parse_line(entity)
        elif entity_type == 'SPLINE':
            return self._parse_spline(entity)
        elif entity_type == 'ARC':
            return self._parse_arc(entity)
        elif entity_type == 'CIRCLE':
            return self._parse_circle(entity)
        elif entity_type == 'ELLIPSE':
            return self._parse_ellipse(entity)

        return None

    def _parse_lwpolyline(self, entity) -> Path:
        """解析轻量多段线"""
        points = []

        # 获取所有点（包括凸度信息）
        vertices = list(entity.get_points(format='xyb'))

        for i, (x, y, bulge) in enumerate(vertices):
            points.append(Point(x, y))

            # 处理圆弧段（bulge != 0）
            if bulge != 0 and i < len(vertices) - 1:
                next_x, next_y, _ = vertices[i + 1]
                arc_points = self._bulge_to_arc_points(
                    Point(x, y), Point(next_x, next_y), bulge
                )
                # 跳过首尾点（避免重复）
                points.extend(arc_points[1:-1])

        # 处理闭合情况
        if entity.closed and len(vertices) > 0:
            last_x, last_y, bulge = vertices[-1]
            first_x, first_y, _ = vertices[0]
            if bulge != 0:
                arc_points = self._bulge_to_arc_points(
                    Point(last_x, last_y), Point(first_x, first_y), bulge
                )
                points.extend(arc_points[1:-1])

        color = self._get_entity_color(entity)
        path_type = self._determine_path_type(color)

        return Path(
            points=points,
            path_type=path_type,
            color=color,
            is_closed=entity.closed
        )

    def _bulge_to_arc_points(self, start: Point, end: Point, bulge: float) -> List[Point]:
        """
        将凸度转换为圆弧点列表

        凸度 = tan(弧度/4)
        正值表示逆时针，负值表示顺时针

        使用自适应分辨率确保平滑度
        """
        # 计算弦长
        dx = end.x - start.x
        dy = end.y - start.y
        chord_length = math.sqrt(dx * dx + dy * dy)

        if chord_length < 1e-10:
            return [start, end]

        # 计算弧高（sagitta）
        sagitta = abs(bulge) * chord_length / 2

        # 计算半径: r = (c²/4 + s²) / (2s)
        radius = (chord_length * chord_length / 4 + sagitta * sagitta) / (2 * sagitta)

        # 计算圆心
        mid_x = (start.x + end.x) / 2
        mid_y = (start.y + end.y) / 2

        # 垂直于弦的方向
        perp_x = -dy / chord_length
        perp_y = dx / chord_length

        # 圆心到弦中点的距离
        h = radius - sagitta

        # 根据凸度符号确定圆心位置
        if bulge > 0:
            center_x = mid_x + h * perp_x
            center_y = mid_y + h * perp_y
        else:
            center_x = mid_x - h * perp_x
            center_y = mid_y - h * perp_y

        # 计算起始和终止角度
        start_angle = math.atan2(start.y - center_y, start.x - center_x)
        end_angle = math.atan2(end.y - center_y, end.x - center_x)

        # 根据凸度符号确定旋转方向
        if bulge > 0:
            # 逆时针
            if end_angle < start_angle:
                end_angle += 2 * math.pi
        else:
            # 顺时针
            if end_angle > start_angle:
                end_angle -= 2 * math.pi

        # 计算圆弧角度范围
        sweep_angle = abs(end_angle - start_angle)

        # 自适应分辨率计算
        # 方法1: 基于角度的基础分段
        base_segments = int(sweep_angle / (2 * math.pi) * self.arc_resolution)

        # 方法2: 基于弦长误差的分段
        # 弦长误差 = r * (1 - cos(theta/2))，其中theta是每个分段的角度
        # 解出: theta = 2 * arccos(1 - error/r)
        if radius > self.chord_error:
            max_angle_per_segment = 2 * math.acos(1 - self.chord_error / radius)
            error_based_segments = int(math.ceil(sweep_angle / max_angle_per_segment))
        else:
            error_based_segments = base_segments

        # 取较大值以确保平滑度
        num_segments = max(base_segments, error_based_segments)

        # 限制范围
        num_segments = max(self.MIN_SEGMENTS_PER_ARC, min(self.MAX_SEGMENTS_PER_ARC, num_segments))

        # 生成圆弧点
        points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            angle = start_angle + t * (end_angle - start_angle)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            points.append(Point(x, y))

        return points

    def _parse_polyline(self, entity) -> Path:
        """解析2D多段线"""
        points = []

        for vertex in entity.vertices:
            if hasattr(vertex.dxf, 'location'):
                loc = vertex.dxf.location
                points.append(Point(loc.x, loc.y))

        color = self._get_entity_color(entity)
        path_type = self._determine_path_type(color)

        return Path(
            points=points,
            path_type=path_type,
            color=color,
            is_closed=entity.is_closed
        )

    def _parse_line(self, entity) -> Optional[Path]:
        """解析直线（通常需要与其他线段连接）"""
        start = entity.dxf.start
        end = entity.dxf.end

        color = self._get_entity_color(entity)

        # 单独的直线无法形成闭合路径，返回两点
        return Path(
            points=[Point(start.x, start.y), Point(end.x, end.y)],
            path_type=PathType.OUTER,
            color=color,
            is_closed=False
        )

    def _parse_spline(self, entity) -> Path:
        """解析样条曲线，使用高精度采样确保平滑度"""
        points = []

        try:
            # 使用ezdxf的样条曲线采样
            # flattening参数是距离容差，使用chord_error确保平滑度
            for point in entity.flattening(self.chord_error):
                points.append(Point(point.x, point.y))
        except Exception:
            # 回退方案：使用控制点进行更密集的采样
            try:
                # 尝试使用更高分辨率的采样
                for point in entity.flattening(0.1):
                    points.append(Point(point.x, point.y))
            except Exception:
                # 最后回退：使用控制点
                for cp in entity.control_points:
                    points.append(Point(cp.x, cp.y))

        color = self._get_entity_color(entity)
        path_type = self._determine_path_type(color)

        return Path(
            points=points,
            path_type=path_type,
            color=color,
            is_closed=entity.closed
        )

    def _parse_arc(self, entity) -> Path:
        """解析圆弧，使用自适应分辨率确保平滑度"""
        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)

        # 处理角度跨越0度的情况
        if end_angle < start_angle:
            end_angle += 2 * math.pi

        points = []
        sweep_angle = end_angle - start_angle

        # 自适应分辨率计算
        # 方法1: 基于角度的基础分段
        base_segments = int(sweep_angle / (2 * math.pi) * self.arc_resolution)

        # 方法2: 基于弦长误差的分段
        if radius > self.chord_error:
            max_angle_per_segment = 2 * math.acos(1 - self.chord_error / radius)
            error_based_segments = int(math.ceil(sweep_angle / max_angle_per_segment))
        else:
            error_based_segments = base_segments

        # 取较大值以确保平滑度
        num_segments = max(base_segments, error_based_segments)
        num_segments = max(self.MIN_SEGMENTS_PER_ARC, min(self.MAX_SEGMENTS_PER_ARC, num_segments))

        for i in range(num_segments + 1):
            t = i / num_segments
            angle = start_angle + t * sweep_angle
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            points.append(Point(x, y))

        color = self._get_entity_color(entity)
        path_type = self._determine_path_type(color)

        return Path(
            points=points,
            path_type=path_type,
            color=color,
            is_closed=False
        )

    def _parse_circle(self, entity) -> Path:
        """解析圆形，使用自适应分辨率确保平滑度"""
        center = entity.dxf.center
        radius = entity.dxf.radius

        # 自适应分辨率计算
        # 方法1: 基础分段数
        base_segments = self.arc_resolution

        # 方法2: 基于弦长误差的分段
        if radius > self.chord_error:
            max_angle_per_segment = 2 * math.acos(1 - self.chord_error / radius)
            error_based_segments = int(math.ceil(2 * math.pi / max_angle_per_segment))
        else:
            error_based_segments = base_segments

        # 取较大值以确保平滑度
        num_segments = max(base_segments, error_based_segments)
        num_segments = max(self.MIN_SEGMENTS_PER_ARC, min(self.MAX_SEGMENTS_PER_ARC, num_segments))

        points = []
        for i in range(num_segments):
            angle = 2 * math.pi * i / num_segments
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            points.append(Point(x, y))

        color = self._get_entity_color(entity)
        path_type = self._determine_path_type(color)

        return Path(
            points=points,
            path_type=path_type,
            color=color,
            is_closed=True
        )

    def _parse_ellipse(self, entity) -> Path:
        """解析椭圆，使用自适应分辨率确保平滑度"""
        center = entity.dxf.center
        major_axis = entity.dxf.major_axis
        ratio = entity.dxf.ratio  # 短轴与长轴的比值

        # 计算长轴长度和角度
        major_length = math.sqrt(major_axis.x ** 2 + major_axis.y ** 2)
        rotation = math.atan2(major_axis.y, major_axis.x)

        # 短轴长度
        minor_length = major_length * ratio

        # 起始和终止参数（椭圆可能是部分弧）
        start_param = entity.dxf.start_param
        end_param = entity.dxf.end_param

        if abs(end_param - start_param) < 0.01:
            end_param = start_param + 2 * math.pi

        sweep_angle = abs(end_param - start_param)

        # 使用较大的轴长度计算分辨率（椭圆曲率在长轴处最大）
        effective_radius = major_length

        # 自适应分辨率计算
        base_segments = int(sweep_angle / (2 * math.pi) * self.arc_resolution)

        if effective_radius > self.chord_error:
            max_angle_per_segment = 2 * math.acos(1 - self.chord_error / effective_radius)
            error_based_segments = int(math.ceil(sweep_angle / max_angle_per_segment))
        else:
            error_based_segments = base_segments

        num_segments = max(base_segments, error_based_segments)
        num_segments = max(self.MIN_SEGMENTS_PER_ARC, min(self.MAX_SEGMENTS_PER_ARC, num_segments))

        points = []
        for i in range(num_segments):
            t = i / num_segments
            param = start_param + t * (end_param - start_param)

            # 椭圆参数方程
            x_local = major_length * math.cos(param)
            y_local = minor_length * math.sin(param)

            # 旋转并平移
            x = center.x + x_local * math.cos(rotation) - y_local * math.sin(rotation)
            y = center.y + x_local * math.sin(rotation) + y_local * math.cos(rotation)
            points.append(Point(x, y))

        color = self._get_entity_color(entity)
        path_type = self._determine_path_type(color)

        is_closed = abs(end_param - start_param - 2 * math.pi) < 0.01

        return Path(
            points=points,
            path_type=path_type,
            color=color,
            is_closed=is_closed
        )

    def _get_entity_color(self, entity) -> Tuple[int, int, int]:
        """获取实体的RGB颜色"""
        try:
            # 优先使用真彩色
            if hasattr(entity.dxf, 'true_color') and entity.dxf.true_color:
                tc = entity.dxf.true_color
                return ((tc >> 16) & 0xFF, (tc >> 8) & 0xFF, tc & 0xFF)

            # 使用ACI颜色索引
            color_index = entity.dxf.color
            if color_index in self.ACI_TO_RGB:
                return self.ACI_TO_RGB[color_index]
        except Exception:
            pass

        return (0, 0, 0)  # 默认黑色

    def _determine_path_type(self, color: Tuple[int, int, int]) -> PathType:
        """根据颜色确定路径类型"""
        # 使用颜色容差匹配
        for target_color, path_type in self.COLOR_MAP.items():
            if self._colors_similar(color, target_color, tolerance=30):
                return path_type
        return PathType.OUTER  # 默认为外轮廓

    def _colors_similar(self, c1: Tuple[int, int, int],
                        c2: Tuple[int, int, int],
                        tolerance: int = 30) -> bool:
        """判断两个颜色是否相近"""
        return all(abs(a - b) <= tolerance for a, b in zip(c1, c2))

    def _classify_and_group_paths(self, paths: List[Path]) -> List[Contour]:
        """
        分类并分组路径

        算法：
        1. 分离特殊路径（连襟框、底孔、花纹）
        2. 对普通路径按面积排序
        3. 使用包含关系判断内外轮廓
        4. 建立轮廓-内孔映射
        """
        # 分离特殊路径
        special_paths: Dict[PathType, List[Path]] = {
            PathType.CONNECTED: [],
            PathType.HOLE: [],
            PathType.PATTERN: [],
        }
        normal_paths: List[Path] = []

        for path in paths:
            if path.path_type in special_paths:
                special_paths[path.path_type].append(path)
            else:
                # 只处理闭合路径
                if path.is_closed or len(path.points) >= 3:
                    normal_paths.append(path)

        # 按面积降序排序（外轮廓通常面积最大）
        normal_paths.sort(key=lambda p: p.area, reverse=True)

        # 建立包含关系
        contours: List[Contour] = []
        used: set = set()

        for i, path in enumerate(normal_paths):
            if i in used:
                continue

            # 这是一个外轮廓
            outer = path
            outer.path_type = PathType.OUTER
            holes: List[Path] = []

            # 查找包含在此轮廓内的路径作为内孔
            for j, inner_path in enumerate(normal_paths):
                if j in used or j == i:
                    continue

                if self._path_contains_path(outer, inner_path):
                    # 检查是否被其他更小的轮廓包含（直接包含关系）
                    is_directly_inside = True
                    for k, middle_path in enumerate(normal_paths):
                        if k in used or k == i or k == j:
                            continue
                        if (self._path_contains_path(outer, middle_path) and
                                self._path_contains_path(middle_path, inner_path)):
                            is_directly_inside = False
                            break

                    if is_directly_inside:
                        inner_path.path_type = PathType.INNER
                        holes.append(inner_path)
                        used.add(j)

            # 创建轮廓对象
            contour = Contour(
                outer=outer,
                holes=holes,
                connected_frames=special_paths[PathType.CONNECTED],
                patterns=special_paths[PathType.PATTERN]
            )
            contours.append(contour)
            used.add(i)

        return contours

    def _path_contains_path(self, outer: Path, inner: Path) -> bool:
        """
        判断outer路径是否完全包含inner路径

        要求inner路径的所有点都在outer路径内部，
        这样才能确定inner是outer的真正内孔，
        而不是两个独立的相邻路径。
        """
        if not inner.points or not outer.points:
            return False

        # 1. 快速检查：边界框是否包含
        inner_bounds = inner.bounds
        outer_bounds = outer.bounds
        if (inner_bounds[0] < outer_bounds[0] or
            inner_bounds[1] < outer_bounds[1] or
            inner_bounds[2] > outer_bounds[2] or
            inner_bounds[3] > outer_bounds[3]):
            return False

        # 2. 检查内部路径的中心点是否在外部路径内
        # 这是关键检查：如果中心点不在内部，那么这不是真正的包含关系
        inner_center = inner.centroid
        if not self._point_in_polygon(inner_center, outer):
            return False

        # 3. 检查路径是否相交（两个独立形状通常会相交）
        if self._paths_intersect(outer, inner):
            return False

        # 4. 检查所有点是否都在outer内部
        # 为了容错边界情况，要求至少90%的点在内部
        inside_count = 0
        total_points = len(inner.points)

        for point in inner.points:
            if self._point_in_polygon(point, outer):
                inside_count += 1

        # 要求至少90%的点在内部才认为是包含关系
        return inside_count >= total_points * 0.9

    def _paths_intersect(self, path1: Path, path2: Path) -> bool:
        """
        检查两条路径是否相交

        如果两条路径的边有交点，则返回True
        """
        n1 = len(path1.points)
        n2 = len(path2.points)

        if n1 < 2 or n2 < 2:
            return False

        # 检查path1的每条边是否与path2的任意边相交
        for i in range(n1):
            p1 = path1.points[i]
            p2 = path1.points[(i + 1) % n1]

            for j in range(n2):
                p3 = path2.points[j]
                p4 = path2.points[(j + 1) % n2]

                if self._segments_intersect(p1, p2, p3, p4):
                    return True

        return False

    def _segments_intersect(self, p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
        """
        检查两条线段是否相交（不包括端点重合的情况）
        """
        def cross(o: Point, a: Point, b: Point) -> float:
            return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

        d1 = cross(p3, p4, p1)
        d2 = cross(p3, p4, p2)
        d3 = cross(p1, p2, p3)
        d4 = cross(p1, p2, p4)

        # 检查是否跨立（符号相反）
        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
           ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
            return True

        return False

    def _point_in_polygon(self, point: Point, polygon: Path) -> bool:
        """
        射线法判断点是否在多边形内

        从点向右发射射线，计算与多边形边的交点数
        奇数交点表示在内部
        """
        x, y = point.x, point.y
        n = len(polygon.points)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon.points[i].x, polygon.points[i].y
            xj, yj = polygon.points[j].x, polygon.points[j].y

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside
