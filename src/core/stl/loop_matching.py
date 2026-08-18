"""Geometry-based matching helpers for closed sliced loops."""

from __future__ import annotations

from typing import Optional, Sequence

from shapely.geometry import LineString

from ..types import Point


def closed_loop_spacing_score(
    reference_points: Sequence[Point],
    candidate_points: Sequence[Point],
    expected_distance: float,
) -> tuple[float, float, float, float]:
    """Score two loops by spacing, area scale, and centroid proximity."""
    reference_line = _closed_line(reference_points)
    candidate_line = _closed_line(candidate_points)
    if reference_line is None or candidate_line is None:
        return (float("inf"), float("inf"), float("inf"), float("inf"))

    boundary_distance = reference_line.distance(candidate_line)
    spacing_error = abs(boundary_distance - max(expected_distance, 0.0))
    area_delta = abs(
        _polygon_area(reference_points) - _polygon_area(candidate_points)
    )
    reference_centroid = _vertex_centroid(reference_points)
    candidate_centroid = _vertex_centroid(candidate_points)
    centroid_distance = (
        (reference_centroid.x - candidate_centroid.x) ** 2
        + (reference_centroid.y - candidate_centroid.y) ** 2
    ) ** 0.5
    return spacing_error, area_delta, centroid_distance, boundary_distance


def _closed_line(points: Sequence[Point]) -> Optional[LineString]:
    if len(points) < 2:
        return None

    coords = [(point.x, point.y) for point in points]
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    try:
        line = LineString(coords)
    except (TypeError, ValueError):
        return None
    if line.is_empty or line.length <= 1e-9:
        return None
    return line


def _polygon_area(points: Sequence[Point]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point.x * next_point.y - next_point.x * point.y
    return abs(area) * 0.5


def _vertex_centroid(points: Sequence[Point]) -> Point:
    if not points:
        return Point(0.0, 0.0)
    count = len(points)
    return Point(
        sum(point.x for point in points) / count,
        sum(point.y for point in points) / count,
    )
