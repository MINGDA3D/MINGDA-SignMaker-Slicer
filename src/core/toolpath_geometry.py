"""Nominal material footprints shared by toolpath preview and mesh generation.

The input coordinates and line widths remain unrounded. G-code serializes XY
and WIDTH to three decimals; comparisons against exported G-code should allow
that quantization (at least 0.001 mm per boundary, more at mitered corners).
"""

from __future__ import annotations

import math
from typing import Iterable, Optional

from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

from .types import LayerPath


def path_footprint(path: LayerPath, miter_limit: float = 2.0) -> Optional[BaseGeometry]:
    """Sweep the requested line width along one actual printable centerline.

    Closed paths retain their enclosed voids; open paths use flat end caps.
    Repeated points are harmless, while non-finite or degenerate paths are
    ignored rather than inventing printable material between invalid points.
    """
    if not math.isfinite(path.line_width) or path.line_width <= 0.0:
        return None

    coords: list[tuple[float, float]] = []
    for point in path.points:
        if not math.isfinite(point.x) or not math.isfinite(point.y):
            return None
        coordinate = (point.x, point.y)
        if not coords or coordinate != coords[-1]:
            coords.append(coordinate)

    minimum_points = 3 if path.is_closed else 2
    if len(set(coords)) < minimum_points:
        return None
    if path.is_closed and coords[0] != coords[-1]:
        coords.append(coords[0])

    footprint = LineString(coords).buffer(
        path.line_width / 2.0,
        cap_style=2,
        join_style=2,
        mitre_limit=miter_limit,
    )
    if not footprint.is_valid:
        footprint = make_valid(footprint)
    if footprint.is_empty or footprint.area <= 0.0:
        return None
    return footprint


def union_path_footprints(
    paths: Iterable[LayerPath],
    miter_limit: float = 2.0,
) -> Optional[BaseGeometry]:
    """Union deposited material once, including overlapping or split paths."""
    footprints = []
    for path in paths:
        footprint = path_footprint(path, miter_limit=miter_limit)
        if footprint is not None:
            footprints.append(footprint)
    if not footprints:
        return None

    geometry = unary_union(footprints)
    if not geometry.is_valid:
        geometry = make_valid(geometry)
    return None if geometry.is_empty else geometry
