from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pyclipper

from src.utils.geometry import normalize_path

from .types import Contour, Path, PathType, Point


_CLIPPER_SCALE = 1000.0
_AREA_EPSILON = 1e-6
_POINT_EPSILON = 1e-9


@dataclass
class _LoopNode:
    path: Path
    parent: Optional[int] = None
    children: List[int] = field(default_factory=list)
    depth: int = 0


def classify_paths_by_nesting(paths: List[Path]) -> List[Contour]:
    """Build contours from closed loops using containment depth parity."""
    loops = _prepare_loops(paths)
    if not loops:
        return []

    nodes = [_LoopNode(path=path) for path in loops]

    for i, node in enumerate(nodes):
        parent_index: Optional[int] = None
        parent_area: Optional[float] = None
        for j, candidate in enumerate(nodes):
            if i == j:
                continue
            if not _path_contains_path(candidate.path, node.path):
                continue
            candidate_area = abs(candidate.path.area)
            if parent_area is None or candidate_area < parent_area:
                parent_area = candidate_area
                parent_index = j

        node.parent = parent_index
        if parent_index is not None:
            nodes[parent_index].children.append(i)

    for i, node in enumerate(nodes):
        depth = 0
        parent = node.parent
        while parent is not None:
            depth += 1
            parent = nodes[parent].parent
        nodes[i].depth = depth

    contours: List[Contour] = []
    for node in nodes:
        if node.depth % 2 != 0:
            continue

        holes = []
        for child_index in node.children:
            child = nodes[child_index]
            if child.depth == node.depth + 1 and child.depth % 2 == 1:
                hole = _clone_path(child.path, PathType.INNER)
                holes.append(normalize_path(hole))

        contour = Contour(
            outer=normalize_path(_clone_path(node.path, PathType.OUTER)),
            holes=holes,
        )
        contours.append(contour)

    contours.sort(key=lambda contour: abs(contour.outer.area), reverse=True)
    return contours


def classify_paths_by_fill_rule(paths: List[Path], fill_rule: str = "nonzero") -> List[Contour]:
    """Resolve SVG filled regions for one fill context and convert to contours."""
    loops = _prepare_loops(paths)
    if not loops:
        return []

    pc = pyclipper.Pyclipper()
    for path in loops:
        pc.AddPath(_scale_path(path), pyclipper.PT_SUBJECT, True)

    fill_type = pyclipper.PFT_EVENODD if fill_rule == "evenodd" else pyclipper.PFT_NONZERO
    solution = pc.Execute2(pyclipper.CT_UNION, fill_type, fill_type)
    contours = _poly_tree_to_contours(solution, loops[0].color)
    contours.sort(key=lambda contour: abs(contour.outer.area), reverse=True)
    return contours


def repair_contours(contours: List[Contour]) -> List[Contour]:
    """Conservatively rebuild outer/hole relations within each saved contour."""
    repaired: List[Contour] = []

    for contour in contours:
        loops = [contour.outer, *contour.holes]
        rebuilt = classify_paths_by_nesting(loops)

        if not rebuilt:
            repaired.append(_normalize_existing_contour(contour))
            continue

        for rebuilt_contour in rebuilt:
            rebuilt_contour.connected_frames = list(contour.connected_frames)
            rebuilt_contour.patterns = list(contour.patterns)
            rebuilt_contour.name = contour.name
            rebuilt_contour.start_point_index = contour.start_point_index
            rebuilt_contour.print_order = contour.print_order
            repaired.append(rebuilt_contour)

    return repaired


def path_contains_path(outer: Path, inner: Path) -> bool:
    """Return True when `outer` fully contains `inner` without edge crossing."""
    prepared_outer = _prepare_loop(outer)
    prepared_inner = _prepare_loop(inner)
    if prepared_outer is None or prepared_inner is None:
        return False
    return _path_contains_path(prepared_outer, prepared_inner)


def _poly_tree_to_contours(node, color) -> List[Contour]:
    contours: List[Contour] = []

    for child in node.Childs:
        contours.extend(_poly_node_to_contours(child, color))

    return contours


def _poly_node_to_contours(node, color) -> List[Contour]:
    contours: List[Contour] = []

    current_path = _poly_node_to_path(node, color)
    if current_path is not None and not node.IsHole:
        holes = []
        for child in node.Childs:
            if child.IsHole:
                hole_path = _poly_node_to_path(child, color)
                if hole_path is not None:
                    holes.append(normalize_path(_clone_path(hole_path, PathType.INNER)))

        contour = Contour(
            outer=normalize_path(_clone_path(current_path, PathType.OUTER)),
            holes=holes,
        )
        contours.append(contour)

    for child in node.Childs:
        contours.extend(_poly_node_to_contours(child, color))

    return contours


def _poly_node_to_path(node, color) -> Optional[Path]:
    contour = getattr(node, "Contour", None)
    if not contour or len(contour) < 3:
        return None

    points = [Point(x / _CLIPPER_SCALE, y / _CLIPPER_SCALE) for x, y in contour]
    path = Path(points=points, color=color, is_closed=True)
    return _prepare_loop(path)


def _prepare_loops(paths: List[Path]) -> List[Path]:
    loops: List[Path] = []
    for path in paths:
        prepared = _prepare_loop(path)
        if prepared is not None:
            loops.append(prepared)
    return loops


def _prepare_loop(path: Path) -> Optional[Path]:
    if not path.is_closed or len(path.points) < 3:
        return None

    cleaned_points: List[Point] = []
    for point in path.points:
        if cleaned_points and _points_equal(cleaned_points[-1], point):
            continue
        cleaned_points.append(Point(point.x, point.y))

    if len(cleaned_points) >= 2 and _points_equal(cleaned_points[0], cleaned_points[-1]):
        cleaned_points.pop()

    if len(cleaned_points) < 3:
        return None

    prepared = Path(
        points=cleaned_points,
        path_type=path.path_type,
        color=path.color,
        is_closed=True,
    )
    if abs(prepared.area) < _AREA_EPSILON:
        return None
    return prepared


def _normalize_existing_contour(contour: Contour) -> Contour:
    outer = _prepare_loop(contour.outer) or contour.outer
    holes = [hole for hole in (_prepare_loop(h) for h in contour.holes) if hole is not None]

    normalized = Contour(
        outer=normalize_path(_clone_path(outer, PathType.OUTER)),
        holes=[normalize_path(_clone_path(hole, PathType.INNER)) for hole in holes],
        connected_frames=list(contour.connected_frames),
        patterns=list(contour.patterns),
        name=contour.name,
        start_point_index=contour.start_point_index,
        print_order=contour.print_order,
    )
    return normalized


def _clone_path(path: Path, path_type: Optional[PathType] = None) -> Path:
    return Path(
        points=[Point(point.x, point.y) for point in path.points],
        path_type=path.path_type if path_type is None else path_type,
        color=path.color,
        is_closed=path.is_closed,
    )


def _scale_path(path: Path):
    return [
        (int(round(point.x * _CLIPPER_SCALE)), int(round(point.y * _CLIPPER_SCALE)))
        for point in path.points
    ]


def _points_equal(a: Point, b: Point) -> bool:
    return abs(a.x - b.x) < _POINT_EPSILON and abs(a.y - b.y) < _POINT_EPSILON


def _path_contains_path(outer: Path, inner: Path) -> bool:
    if not outer.points or not inner.points:
        return False

    outer_bounds = outer.bounds
    inner_bounds = inner.bounds
    if (
        inner_bounds[0] < outer_bounds[0]
        or inner_bounds[1] < outer_bounds[1]
        or inner_bounds[2] > outer_bounds[2]
        or inner_bounds[3] > outer_bounds[3]
    ):
        return False

    if _paths_intersect(outer, inner):
        return False

    if not _point_in_polygon(inner.centroid, outer):
        return False

    inside_count = sum(1 for point in inner.points if _point_in_polygon(point, outer))
    return inside_count >= len(inner.points) * 0.9


def _paths_intersect(path1: Path, path2: Path) -> bool:
    if len(path1.points) < 2 or len(path2.points) < 2:
        return False

    for i in range(len(path1.points)):
        p1 = path1.points[i]
        p2 = path1.points[(i + 1) % len(path1.points)]
        for j in range(len(path2.points)):
            p3 = path2.points[j]
            p4 = path2.points[(j + 1) % len(path2.points)]
            if _segments_intersect(p1, p2, p3, p4):
                return True
    return False


def _segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    def cross(o: Point, a: Point, b: Point) -> float:
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

    d1 = cross(p3, p4, p1)
    d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3)
    d4 = cross(p1, p2, p4)

    return (
        ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0))
        and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
    )


def _point_in_polygon(point: Point, polygon: Path) -> bool:
    x, y = point.x, point.y
    inside = False
    j = len(polygon.points) - 1

    for i in range(len(polygon.points)):
        xi, yi = polygon.points[i].x, polygon.points[i].y
        xj, yj = polygon.points[j].x, polygon.points[j].y

        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside
