"""
SignMaker Slicer - SVG文件解析模块

使用 svgpathtools 库将SVG文件解析为内部Contour数据结构，包括：
- 提取图形元素（path, rect, circle, ellipse, polygon, polyline, line）
- 识别路径颜色并分类（普通轮廓、连襟框、底孔、面板花纹）
- 建立外轮廓与内孔的包含关系
- 处理SVG变换（transform）
"""

from __future__ import annotations
import math
import re
from typing import List, Tuple, Optional, Dict
from pathlib import Path as FilePath

import svgpathtools
from svgpathtools import svg2paths2, parse_path, Path as SVGPath

from .types import Point, Path, Contour, PathType


class SVGParser:
    """SVG文件解析器（使用svgpathtools库）"""

    # 标准RGB颜色映射（用于识别特殊路径）
    COLOR_MAP: Dict[Tuple[int, int, int], PathType] = {
        (0, 255, 255): PathType.CONNECTED,   # 青色 → 连襟框
        (0, 255, 0): PathType.HOLE,          # 绿色 → 底孔
        (0, 0, 255): PathType.PATTERN,       # 蓝色 → 面板花纹
    }

    # SVG单位到毫米的转换因子（基于96 DPI标准）
    # 参考: https://www.w3.org/TR/css-values-3/#absolute-lengths
    UNIT_TO_MM: Dict[str, float] = {
        'px': 25.4 / 96.0,    # 1px = 0.2646mm (@96dpi)
        'pt': 25.4 / 72.0,    # 1pt = 0.3528mm (72pt/inch)
        'pc': 25.4 / 6.0,     # 1pc = 4.2333mm (6pc/inch)
        'in': 25.4,           # 1in = 25.4mm
        'cm': 10.0,           # 1cm = 10mm
        'mm': 1.0,            # 1mm = 1mm
        '': 25.4 / 96.0,      # 无单位默认按像素处理
    }

    def __init__(self, resolution: int = 100, chord_error: float = 0.1,
                 default_dpi: float = 96.0):
        """
        初始化解析器

        Args:
            resolution: 曲线离散化分辨率（每条曲线的采样点数）
            chord_error: 弦长误差阈值 (mm)，越小越平滑
            default_dpi: 默认DPI（用于解释无单位的SVG坐标），默认96
        """
        self.resolution = resolution
        self.chord_error = chord_error
        self.default_dpi = default_dpi
        # 当前解析时使用的缩放因子（SVG用户单位到毫米）
        self._scale_factor = 25.4 / default_dpi

    def parse(self, file_path: str) -> List[Contour]:
        """
        解析SVG文件

        Args:
            file_path: SVG文件路径

        Returns:
            轮廓列表，每个轮廓包含外边界和内孔
        """
        # 使用svgpathtools解析SVG
        paths, attributes, svg_attributes = svg2paths2(file_path)

        # 计算单位转换的缩放因子
        self._scale_factor = self._calculate_scale_factor(svg_attributes)

        # 提取所有路径
        parsed_paths = self._extract_all_paths(paths, attributes)

        # 分类并分组路径
        contours = self._classify_and_group_paths(parsed_paths)

        return contours

    def _calculate_scale_factor(self, svg_attributes: dict) -> float:
        """
        计算SVG坐标到毫米的缩放因子

        解析SVG的width、height和viewBox属性来确定正确的缩放因子。

        优先级：
        1. 如果width/height有真实单位（mm, cm, in等），使用它们
        2. 如果只有viewBox，按默认DPI转换（假设无单位=像素）

        Args:
            svg_attributes: SVG根元素的属性字典

        Returns:
            缩放因子（乘以此值将SVG坐标转换为毫米）
        """
        if not svg_attributes:
            return 25.4 / self.default_dpi

        # 获取viewBox
        viewbox_str = svg_attributes.get('viewBox', '')
        vb_width, vb_height = None, None
        if viewbox_str:
            vb_parts = viewbox_str.replace(',', ' ').split()
            if len(vb_parts) >= 4:
                try:
                    vb_width = float(vb_parts[2])
                    vb_height = float(vb_parts[3])
                except ValueError:
                    pass

        # 获取width和height属性
        width_str = svg_attributes.get('width', '')
        height_str = svg_attributes.get('height', '')

        # 解析带单位的尺寸
        real_width, width_unit = self._parse_length_with_unit(width_str)
        real_height, height_unit = self._parse_length_with_unit(height_str)

        # 情况1：width/height有真实单位，且有viewBox
        if real_width and width_unit in self.UNIT_TO_MM and vb_width:
            # 将width转换为毫米
            width_mm = real_width * self.UNIT_TO_MM[width_unit]
            # 缩放因子 = 真实毫米 / viewBox单位
            scale = width_mm / vb_width
            return scale

        # 情况2：width/height有真实单位，无viewBox
        if real_width and width_unit in self.UNIT_TO_MM and width_unit != '':
            # 直接使用单位转换（假设SVG坐标与width/height同单位）
            return self.UNIT_TO_MM[width_unit]

        # 情况3：只有数值的width/height（无单位），有viewBox
        if real_width and vb_width:
            # 无单位的width被视为像素，viewBox单位也是像素
            # 缩放因子 = (width像素 / viewBox单位) * (mm/像素)
            scale = (real_width / vb_width) * (25.4 / self.default_dpi)
            return scale

        # 情况4：只有viewBox，无width/height
        if vb_width:
            # viewBox单位视为像素
            return 25.4 / self.default_dpi

        # 默认：按96 DPI转换
        return 25.4 / self.default_dpi

    def _parse_length_with_unit(self, length_str: str) -> Tuple[Optional[float], str]:
        """
        解析带单位的长度字符串

        Args:
            length_str: 如 "100mm", "50px", "3.5in", "200" 等

        Returns:
            (数值, 单位) 元组，如 (100.0, 'mm')
        """
        if not length_str:
            return None, ''

        length_str = length_str.strip()

        # 匹配数值和单位
        match = re.match(r'^([+-]?(?:\d+\.?\d*|\.\d+))([a-zA-Z%]*)$', length_str)
        if match:
            try:
                value = float(match.group(1))
                unit = match.group(2).lower()
                return value, unit
            except ValueError:
                pass

        return None, ''

    def parse_from_string(self, svg_content: str) -> List[Contour]:
        """
        从字符串解析SVG

        Args:
            svg_content: SVG内容字符串

        Returns:
            轮廓列表
        """
        import tempfile
        import os

        # svgpathtools需要文件路径，创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8') as f:
            f.write(svg_content)
            temp_path = f.name

        try:
            return self.parse(temp_path)
        finally:
            os.unlink(temp_path)

    def _extract_all_paths(self, svg_paths: List[SVGPath],
                           attributes: List[dict]) -> List[Path]:
        """提取SVG中的所有路径，自动分割子路径"""
        paths = []

        for svg_path, attrs in zip(svg_paths, attributes):
            if not svg_path:
                continue

            # 应用transform属性
            transform_str = attrs.get('transform', '')
            if transform_str:
                svg_path = self._apply_transform(svg_path, transform_str)

            # 获取颜色（所有子路径共享）
            color = self._get_path_color(attrs)
            path_type = self._determine_path_type(color)

            # 检查是否有fill属性（用于判断开放路径是否应视为闭合）
            has_fill = self._has_fill(attrs)

            # 分割子路径（检测不连续点）
            subpaths = self._split_subpaths(svg_path)

            for subpath in subpaths:
                # 将SVG子路径转换为点列表
                points = self._svg_path_to_points(subpath)

                if len(points) < 3:
                    continue

                # 检查路径是否闭合
                # 根据SVG规范：fill操作会将开放路径视为闭合处理
                is_closed = self._is_path_closed(subpath, points, has_fill)

                path = Path(
                    points=points,
                    path_type=path_type,
                    color=color,
                    is_closed=is_closed
                )
                paths.append(path)

        # SVG坐标系Y轴向下，需要翻转为Y轴向上（与DXF/CAD坐标系一致）
        # 使用实际边界框进行翻转，保持坐标为正值
        self._flip_y_axis(paths)

        return paths

    def _flip_y_axis(self, paths: List[Path]) -> None:
        """
        翻转所有路径的Y轴坐标

        SVG坐标系：原点在左上角，Y轴向下
        CAD坐标系：原点在左下角，Y轴向上

        变换公式：y_new = max_y - y_old + min_y
        这相当于绕Y轴中心线镜像翻转
        """
        if not paths:
            return

        # 找出所有点的Y坐标范围
        all_y = []
        for path in paths:
            for point in path.points:
                all_y.append(point.y)

        if not all_y:
            return

        min_y = min(all_y)
        max_y = max(all_y)

        # 对每个点进行Y轴翻转: y_new = max_y + min_y - y_old
        for path in paths:
            for i, point in enumerate(path.points):
                new_y = max_y + min_y - point.y
                path.points[i] = Point(point.x, new_y)

    def _split_subpaths(self, svg_path: SVGPath) -> List[SVGPath]:
        """
        将包含多个子路径的SVG路径分割为独立的路径

        通过检测不连续点（当前段起点与上一段终点不一致）来识别子路径
        """
        if not svg_path or len(svg_path) == 0:
            return []

        if len(svg_path) == 1:
            return [svg_path]

        subpaths = []
        current_segments = [svg_path[0]]

        for i in range(1, len(svg_path)):
            prev_end = svg_path[i - 1].end
            curr_start = svg_path[i].start

            # 计算不连续距离
            dist = abs(prev_end - curr_start)

            if dist > 0.1:  # 不连续阈值
                # 发现新的子路径，保存当前子路径
                if current_segments:
                    subpath = SVGPath(*current_segments)
                    subpaths.append(subpath)
                current_segments = [svg_path[i]]
            else:
                current_segments.append(svg_path[i])

        # 保存最后一个子路径
        if current_segments:
            subpath = SVGPath(*current_segments)
            subpaths.append(subpath)

        return subpaths

    def _svg_path_to_points(self, svg_path: SVGPath) -> List[Point]:
        """
        将svgpathtools的Path对象转换为点列表

        使用自适应采样确保曲线平滑
        """
        points = []

        for segment in svg_path:
            # 根据曲线类型和长度确定采样点数
            segment_length = segment.length()

            if segment_length < 0.01:
                # 极短的线段，只取端点
                num_samples = 2
            else:
                # 自适应采样：基于弦长误差和曲率
                num_samples = self._calculate_segment_samples(segment, segment_length)

            # 采样曲线上的点
            for i in range(num_samples):
                t = i / max(num_samples - 1, 1)
                try:
                    point = segment.point(t)
                    # svgpathtools返回复数，实部是x，虚部是y
                    x, y = point.real, point.imag

                    # 应用单位转换缩放因子（SVG用户单位 -> 毫米）
                    x *= self._scale_factor
                    y *= self._scale_factor

                    # 避免添加重复点
                    if not points or (abs(points[-1].x - x) > 1e-6 or
                                     abs(points[-1].y - y) > 1e-6):
                        points.append(Point(x, y))
                except Exception:
                    continue

        return points

    def _calculate_segment_samples(self, segment, length: float) -> int:
        """
        计算曲线段的采样点数

        根据曲线类型、长度和曲率自适应调整
        """
        segment_type = type(segment).__name__

        if segment_type == 'Line':
            # 直线只需要2个点
            return 2

        elif segment_type in ['CubicBezier', 'QuadraticBezier']:
            # 贝塞尔曲线：基于长度和曲率估算
            # 基础采样：每个单位长度采样若干点
            base_samples = max(10, int(length / 2))

            # 限制范围
            return min(max(base_samples, 10), 100)

        elif segment_type == 'Arc':
            # 圆弧：基于角度范围
            # 计算弧度
            try:
                # 估算弧的角度范围
                theta = abs(segment.theta2 - segment.theta1)
                # 每10度一个采样点
                arc_samples = max(8, int(theta / 10))
                return min(arc_samples, 72)  # 最多72个点（5度间隔）
            except:
                return max(16, int(length / 2))

        else:
            # 其他类型，使用默认采样
            return max(10, int(length / 2))

    def _is_path_closed(self, svg_path: SVGPath, points: List[Point],
                         has_fill: bool = False) -> bool:
        """
        判断路径是否闭合

        根据SVG规范，fill操作会将开放路径视为闭合处理。
        因此当路径有fill属性时，即使路径没有显式闭合，也应视为闭合。
        """
        if not points or len(points) < 2:
            return False

        # 检查svgpathtools的闭合属性
        try:
            if svg_path.isclosed():
                return True
        except:
            pass

        # 检查首尾点是否接近
        first = points[0]
        last = points[-1]
        distance = math.sqrt((first.x - last.x)**2 + (first.y - last.y)**2)

        # 如果首尾点距离小于1mm，认为闭合
        if distance < 1.0:
            return True

        # 根据SVG规范：如果有fill属性，开放路径应视为闭合
        # 这对于3D打印字壳来说是正确的行为
        if has_fill:
            return True

        return False

    def _has_fill(self, attrs: dict) -> bool:
        """
        检查路径是否有fill属性

        返回True如果路径有有效的fill颜色（不是'none'）
        """
        # 直接检查fill属性
        fill = attrs.get('fill')
        if fill and fill.lower() != 'none':
            return True

        # 检查style中的fill
        style = attrs.get('style', '')
        if style:
            fill_match = re.search(r'fill\s*:\s*([^;]+)', style)
            if fill_match:
                fill_value = fill_match.group(1).strip().lower()
                if fill_value and fill_value != 'none':
                    return True

        # 检查class属性引用的样式（通过颜色判断）
        # 如果路径有颜色且不是纯描边，也认为有fill
        css_class = attrs.get('class', '')
        if css_class:
            # 如果有class，默认认为可能有fill（保守处理）
            # 除非明确指定了stroke且没有fill
            stroke = attrs.get('stroke')
            if not stroke and not fill:
                # 有class但没有显式的stroke或fill，假设有fill
                return True

        return False

    def _get_path_color(self, attrs: dict) -> Tuple[int, int, int]:
        """获取路径的RGB颜色"""
        # 优先使用stroke，其次fill
        color_str = attrs.get('stroke') or attrs.get('fill')

        if not color_str or color_str == 'none':
            # 尝试从style属性中提取
            style = attrs.get('style', '')
            stroke_match = re.search(r'stroke\s*:\s*([^;]+)', style)
            if stroke_match:
                color_str = stroke_match.group(1).strip()
            else:
                fill_match = re.search(r'fill\s*:\s*([^;]+)', style)
                if fill_match:
                    color_str = fill_match.group(1).strip()

        if not color_str or color_str == 'none':
            return (0, 0, 0)

        return self._parse_color(color_str)

    def _parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """解析颜色字符串为RGB"""
        color_str = color_str.strip().lower()

        # 十六进制颜色 #RRGGBB 或 #RGB
        if color_str.startswith('#'):
            hex_str = color_str[1:]
            if len(hex_str) == 3:
                # #RGB -> #RRGGBB
                hex_str = ''.join([c * 2 for c in hex_str])
            if len(hex_str) == 6:
                try:
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    return (r, g, b)
                except ValueError:
                    pass

        # rgb(r, g, b) 格式
        if color_str.startswith('rgb'):
            match = re.search(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_str)
            if match:
                return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

        # 命名颜色
        named_colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'cyan': (0, 255, 255),
            'aqua': (0, 255, 255),
            'magenta': (255, 0, 255),
            'fuchsia': (255, 0, 255),
            'yellow': (255, 255, 0),
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'gray': (128, 128, 128),
            'grey': (128, 128, 128),
            'lime': (0, 255, 0),
            'navy': (0, 0, 128),
            'teal': (0, 128, 128),
            'purple': (128, 0, 128),
            'maroon': (128, 0, 0),
            'olive': (128, 128, 0),
            'silver': (192, 192, 192),
            'orange': (255, 165, 0),
            'pink': (255, 192, 203),
        }
        if color_str in named_colors:
            return named_colors[color_str]

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
        判断outer路径是否��全包含inner路径

        要求inner路径的所有点都在outer路径内部
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
        inner_center = inner.centroid
        if not self._point_in_polygon(inner_center, outer):
            return False

        # 3. 检查路径是否相交
        if self._paths_intersect(outer, inner):
            return False

        # 4. 检查所有点是否都在outer内部
        inside_count = 0
        total_points = len(inner.points)

        for point in inner.points:
            if self._point_in_polygon(point, outer):
                inside_count += 1

        # 要求至少90%的点在内部才认为是包含关系
        return inside_count >= total_points * 0.9

    def _paths_intersect(self, path1: Path, path2: Path) -> bool:
        """检查两条路径是否相交"""
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
        """检查两条线段是否相交（不包括端点重合的情况）"""
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
        射线法判断点是否在多��形内

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

    def _apply_transform(self, svg_path: SVGPath, transform_str: str) -> SVGPath:
        """
        应用SVG transform属性到路径

        支持的变换类型：
        - translate(tx, ty) 或 translate(tx)
        - rotate(angle) 或 rotate(angle, cx, cy)
        - scale(sx, sy) 或 scale(s)
        - matrix(a, b, c, d, e, f)

        SVG transform的顺序是从右到左应用
        """
        if not transform_str:
            return svg_path

        # 解析所有变换（按顺序）
        transforms = self._parse_transform_string(transform_str)

        # SVG transform从右到左应用，所以我们反转列表
        for transform_type, params in reversed(transforms):
            svg_path = self._apply_single_transform(svg_path, transform_type, params)

        return svg_path

    def _parse_transform_string(self, transform_str: str) -> List[Tuple[str, List[float]]]:
        """
        解析SVG transform字符串

        Returns:
            变换列表 [(type, [params]), ...]
        """
        transforms = []

        # 匹配 transform_name(params) 格式
        pattern = r'(\w+)\s*\(([^)]*)\)'
        matches = re.findall(pattern, transform_str)

        for transform_type, params_str in matches:
            # 解析参数（可能用逗号或空格分隔）
            params_str = params_str.replace(',', ' ')
            params = [float(p) for p in params_str.split() if p]
            transforms.append((transform_type.lower(), params))

        return transforms

    def _apply_single_transform(self, svg_path: SVGPath,
                                transform_type: str,
                                params: List[float]) -> SVGPath:
        """应用单个变换到路径"""
        if transform_type == 'translate':
            tx = params[0] if len(params) > 0 else 0
            ty = params[1] if len(params) > 1 else 0
            return svg_path.translated(complex(tx, ty))

        elif transform_type == 'rotate':
            angle = params[0] if len(params) > 0 else 0
            if len(params) >= 3:
                # rotate(angle, cx, cy) - 绕指定点旋转
                cx, cy = params[1], params[2]
                return svg_path.rotated(angle, origin=complex(cx, cy))
            else:
                # rotate(angle) - 绕原点旋转
                return svg_path.rotated(angle, origin=0j)

        elif transform_type == 'scale':
            sx = params[0] if len(params) > 0 else 1
            sy = params[1] if len(params) > 1 else sx
            return svg_path.scaled(complex(sx, sy))

        elif transform_type == 'matrix':
            # matrix(a, b, c, d, e, f) - 仿射变换矩阵
            # [x']   [a c e] [x]
            # [y'] = [b d f] [y]
            # [1 ]   [0 0 1] [1]
            if len(params) >= 6:
                a, b, c, d, e, f = params[:6]
                # svgpathtools没有直接的matrix变换，需要逐段变换
                from svgpathtools import Path as SVGPathClass
                new_segments = []
                for seg in svg_path:
                    new_seg = self._transform_segment_matrix(seg, a, b, c, d, e, f)
                    new_segments.append(new_seg)
                return SVGPathClass(*new_segments)
            return svg_path

        else:
            # 不支持的变换类型，返回原路径
            return svg_path

    def _transform_segment_matrix(self, segment, a: float, b: float, c: float,
                                   d: float, e: float, f: float):
        """使用矩阵变换路径段"""
        def transform_point(p: complex) -> complex:
            x, y = p.real, p.imag
            new_x = a * x + c * y + e
            new_y = b * x + d * y + f
            return complex(new_x, new_y)

        segment_type = type(segment).__name__

        if segment_type == 'Line':
            from svgpathtools import Line
            return Line(transform_point(segment.start), transform_point(segment.end))

        elif segment_type == 'CubicBezier':
            from svgpathtools import CubicBezier
            return CubicBezier(
                transform_point(segment.start),
                transform_point(segment.control1),
                transform_point(segment.control2),
                transform_point(segment.end)
            )

        elif segment_type == 'QuadraticBezier':
            from svgpathtools import QuadraticBezier
            return QuadraticBezier(
                transform_point(segment.start),
                transform_point(segment.control),
                transform_point(segment.end)
            )

        elif segment_type == 'Arc':
            # Arc变换比较复杂，这里简化处理：转换为多段线
            from svgpathtools import Line
            # 采样Arc上的点
            num_samples = 20
            points = [transform_point(segment.point(t / (num_samples - 1)))
                      for t in range(num_samples)]
            # 返回一系列Line段
            lines = [Line(points[i], points[i + 1])
                     for i in range(len(points) - 1)]
            return lines[0] if len(lines) == 1 else lines

        else:
            # 其他类型，尝试通用处理
            return segment
