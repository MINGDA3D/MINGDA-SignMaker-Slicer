"""
MINGDA SignMaker - 几何工具模块

提供通用几何计算函数。
"""

from __future__ import annotations
import math
from typing import List, Tuple, Optional

from src.core.types import Point, Path


def distance(p1: Point, p2: Point) -> float:
    """计算两点间距离"""
    return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)


def path_length(path: Path) -> float:
    """计算路径总长度"""
    total = 0
    n = len(path.points)
    for i in range(n):
        j = (i + 1) % n if path.is_closed else i + 1
        if j >= n:
            break
        total += distance(path.points[i], path.points[j])
    return total


def path_area(path: Path) -> float:
    """计算路径围成的面积（Shoelace公式）"""
    n = len(path.points)
    if n < 3:
        return 0

    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += path.points[i].x * path.points[j].y
        area -= path.points[j].x * path.points[i].y

    return abs(area) / 2


def path_centroid(path: Path) -> Point:
    """计算路径质心"""
    n = len(path.points)
    if n == 0:
        return Point(0, 0)

    cx = sum(p.x for p in path.points) / n
    cy = sum(p.y for p in path.points) / n
    return Point(cx, cy)


def path_bounds(path: Path) -> Tuple[float, float, float, float]:
    """计算路径边界框 (min_x, min_y, max_x, max_y)"""
    if not path.points:
        return (0, 0, 0, 0)

    xs = [p.x for p in path.points]
    ys = [p.y for p in path.points]
    return (min(xs), min(ys), max(xs), max(ys))


def is_clockwise(path: Path) -> bool:
    """判断路径是否顺时针方向"""
    area = 0
    n = len(path.points)
    for i in range(n):
        j = (i + 1) % n
        area += path.points[i].x * path.points[j].y
        area -= path.points[j].x * path.points[i].y
    return area < 0


def reverse_path(path: Path) -> Path:
    """反转路径方向"""
    return Path(
        points=list(reversed(path.points)),
        path_type=path.path_type,
        color=path.color,
        is_closed=path.is_closed
    )


def point_in_polygon(point: Point, polygon: Path) -> bool:
    """射线法判断点是否在多边形内"""
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


def rotate_point(point: Point, center: Point, angle_deg: float) -> Point:
    """绕中心点旋转"""
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    dx = point.x - center.x
    dy = point.y - center.y

    new_x = center.x + dx * cos_a - dy * sin_a
    new_y = center.y + dx * sin_a + dy * cos_a

    return Point(new_x, new_y)


def rotate_path(path: Path, center: Point, angle_deg: float) -> Path:
    """旋转整个路径"""
    rotated_points = [rotate_point(p, center, angle_deg) for p in path.points]
    return Path(
        points=rotated_points,
        path_type=path.path_type,
        color=path.color,
        is_closed=path.is_closed
    )


def scale_path(path: Path, center: Point, scale: float) -> Path:
    """缩放路径"""
    scaled_points = [
        Point(
            center.x + (p.x - center.x) * scale,
            center.y + (p.y - center.y) * scale
        )
        for p in path.points
    ]
    return Path(
        points=scaled_points,
        path_type=path.path_type,
        color=path.color,
        is_closed=path.is_closed
    )


def translate_path(path: Path, dx: float, dy: float) -> Path:
    """平移路径"""
    translated_points = [Point(p.x + dx, p.y + dy) for p in path.points]
    return Path(
        points=translated_points,
        path_type=path.path_type,
        color=path.color,
        is_closed=path.is_closed
    )


def mirror_path_x(path: Path, center_x: float = 0) -> Path:
    """X轴镜像"""
    mirrored_points = [Point(2 * center_x - p.x, p.y) for p in path.points]
    return Path(
        points=mirrored_points,
        path_type=path.path_type,
        color=path.color,
        is_closed=path.is_closed
    )


def mirror_path_y(path: Path, center_y: float = 0) -> Path:
    """Y轴镜像"""
    mirrored_points = [Point(p.x, 2 * center_y - p.y) for p in path.points]
    return Path(
        points=mirrored_points,
        path_type=path.path_type,
        color=path.color,
        is_closed=path.is_closed
    )


def point_to_line_distance(point: Point, line_start: Point, line_end: Point) -> float:
    """计算点到线段的距离"""
    dx = line_end.x - line_start.x
    dy = line_end.y - line_start.y

    if dx == 0 and dy == 0:
        return distance(point, line_start)

    t = max(0, min(1, (
        (point.x - line_start.x) * dx +
        (point.y - line_start.y) * dy
    ) / (dx * dx + dy * dy)))

    proj = Point(
        line_start.x + t * dx,
        line_start.y + t * dy
    )

    return distance(point, proj)


def simplify_path_rdp(path: Path, epsilon: float) -> Path:
    """
    Douglas-Peucker算法简化路径

    Args:
        path: 输入路径
        epsilon: 简化阈值（距离）

    Returns:
        简化后的路径
    """
    if len(path.points) <= 2:
        return path

    # 找到距离首尾连线最远的点
    start = path.points[0]
    end = path.points[-1]

    max_dist = 0
    max_index = 0

    for i in range(1, len(path.points) - 1):
        dist = point_to_line_distance(path.points[i], start, end)
        if dist > max_dist:
            max_dist = dist
            max_index = i

    # 如果最大距离大于阈值，递归简化
    if max_dist > epsilon:
        left_path = Path(points=path.points[:max_index + 1])
        right_path = Path(points=path.points[max_index:])

        left_simplified = simplify_path_rdp(left_path, epsilon)
        right_simplified = simplify_path_rdp(right_path, epsilon)

        return Path(
            points=left_simplified.points[:-1] + right_simplified.points,
            path_type=path.path_type,
            color=path.color,
            is_closed=path.is_closed
        )
    else:
        return Path(
            points=[start, end],
            path_type=path.path_type,
            color=path.color,
            is_closed=path.is_closed
        )


def normalize_path(path: Path) -> Path:
    """
    归一化路径：确保外轮廓逆时针，内孔顺时针

    Args:
        path: 输入路径

    Returns:
        归一化后的路径
    """
    from src.core.types import PathType

    if path.path_type == PathType.OUTER:
        # 外轮廓应该逆时针
        if is_clockwise(path):
            return reverse_path(path)
    elif path.path_type == PathType.INNER:
        # 内孔应该顺时针
        if not is_clockwise(path):
            return reverse_path(path)

    return path


def create_rectangle(x: float, y: float, width: float, height: float) -> Path:
    """创建矩形路径"""
    return Path(
        points=[
            Point(x, y),
            Point(x + width, y),
            Point(x + width, y + height),
            Point(x, y + height)
        ],
        is_closed=True
    )


def create_circle(center_x: float, center_y: float,
                  radius: float, segments: int = 64) -> Path:
    """创建圆形路径"""
    points = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append(Point(x, y))

    return Path(points=points, is_closed=True)


def create_rounded_rectangle(x: float, y: float, width: float, height: float,
                              radius: float, segments_per_corner: int = 8) -> Path:
    """创建圆角矩形路径"""
    points = []

    # 限制圆角半径
    max_radius = min(width, height) / 2
    r = min(radius, max_radius)

    # 右下角
    for i in range(segments_per_corner):
        angle = -math.pi / 2 + math.pi / 2 * i / (segments_per_corner - 1)
        px = x + width - r + r * math.cos(angle)
        py = y + r + r * math.sin(angle)
        points.append(Point(px, py))

    # 右上角
    for i in range(segments_per_corner):
        angle = 0 + math.pi / 2 * i / (segments_per_corner - 1)
        px = x + width - r + r * math.cos(angle)
        py = y + height - r + r * math.sin(angle)
        points.append(Point(px, py))

    # 左上角
    for i in range(segments_per_corner):
        angle = math.pi / 2 + math.pi / 2 * i / (segments_per_corner - 1)
        px = x + r + r * math.cos(angle)
        py = y + height - r + r * math.sin(angle)
        points.append(Point(px, py))

    # 左下角
    for i in range(segments_per_corner):
        angle = math.pi + math.pi / 2 * i / (segments_per_corner - 1)
        px = x + r + r * math.cos(angle)
        py = y + r + r * math.sin(angle)
        points.append(Point(px, py))

    return Path(points=points, is_closed=True)
