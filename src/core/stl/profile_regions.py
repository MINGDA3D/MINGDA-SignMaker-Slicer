"""Shared profile-region normalization for shell and flat-step meshes."""

from __future__ import annotations

from typing import List, Optional, Sequence

from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.validation import make_valid

from ..types import Contour, Path, Point


MIN_POLYGON_AREA = 1e-6


def contour_to_geometry(
    contour: Contour,
    min_polygon_area: float = MIN_POLYGON_AREA,
) -> Optional[BaseGeometry]:
    """Convert a contour into valid Shapely geometry."""
    outer_coords = _closed_coords(contour.outer.points)
    if len(outer_coords) < 4:
        return None

    hole_coords = [
        coords
        for coords in (
            _closed_coords(hole.points) for hole in contour.holes
        )
        if len(coords) >= 4
    ]
    geometry: BaseGeometry = ShapelyPolygon(outer_coords, hole_coords)
    if not geometry.is_valid:
        geometry = make_valid(geometry)
    if geometry.is_empty or geometry.area < min_polygon_area:
        return None
    return geometry


def extract_polygons(
    geometry: Optional[BaseGeometry],
    min_polygon_area: float = MIN_POLYGON_AREA,
) -> List[ShapelyPolygon]:
    """Flatten polygonal parts from valid or repaired geometry."""
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry] if geometry.area > min_polygon_area else []
    if not hasattr(geometry, "geoms"):
        return []

    polygons: List[ShapelyPolygon] = []
    for child in geometry.geoms:
        polygons.extend(extract_polygons(child, min_polygon_area))
    return polygons


def merge_contours_by_nesting(
    contours: Sequence[Contour],
    min_polygon_area: float = MIN_POLYGON_AREA,
) -> List[Contour]:
    """Merge overlaps while retaining strictly nested independent loops."""
    profiles: List[ShapelyPolygon] = []
    for contour in contours:
        geometry = contour_to_geometry(contour, min_polygon_area)
        profiles.extend(extract_polygons(geometry, min_polygon_area))

    return [
        polygon_to_contour(profile)
        for profile in merge_profile_regions_by_nesting(
            profiles,
            min_polygon_area,
        )
    ]


def merge_profile_regions_by_nesting(
    profiles: Sequence[ShapelyPolygon],
    min_polygon_area: float = MIN_POLYGON_AREA,
) -> List[ShapelyPolygon]:
    """Union profiles at each strict nesting depth."""
    profiles_by_depth: dict[int, List[ShapelyPolygon]] = {}
    nesting_depths = profile_nesting_depths(profiles, min_polygon_area)
    for profile, depth in zip(profiles, nesting_depths):
        profiles_by_depth.setdefault(depth, []).append(profile)

    merged_regions: List[ShapelyPolygon] = []
    for depth in sorted(profiles_by_depth):
        depth_region = _valid_union(profiles_by_depth[depth])
        merged_regions.extend(extract_polygons(depth_region, min_polygon_area))
    return merged_regions


def profile_nesting_depths(
    profiles: Sequence[ShapelyPolygon],
    min_polygon_area: float = MIN_POLYGON_AREA,
) -> List[int]:
    """Return strict nesting depths, including collective parent unions."""
    depths = [0] * len(profiles)
    by_descending_area = sorted(
        range(len(profiles)),
        key=lambda index: profiles[index].area,
        reverse=True,
    )

    for profile_index in by_descending_area:
        profile = profiles[profile_index]
        min_x, min_y, max_x, max_y = profile.bounds
        parent_depths = []

        for candidate_index in by_descending_area:
            candidate = profiles[candidate_index]
            if candidate.area <= profile.area + min_polygon_area:
                break

            candidate_bounds = candidate.bounds
            if (
                candidate_bounds[0] > min_x
                or candidate_bounds[1] > min_y
                or candidate_bounds[2] < max_x
                or candidate_bounds[3] < max_y
            ):
                continue
            if candidate.contains_properly(profile):
                parent_depths.append(depths[candidate_index])

        if parent_depths:
            depths[profile_index] = max(parent_depths) + 1

    return _promote_collectively_nested_profiles(profiles, depths)


def polygon_to_contour(polygon: ShapelyPolygon) -> Contour:
    """Convert merged geometry to a consistently wound temporary contour."""
    normalized = orient(polygon, sign=1.0)

    def ring_to_path(ring) -> Path:
        return Path(
            points=[
                Point(float(x), float(y))
                for x, y in list(ring.coords)[:-1]
            ],
            is_closed=True,
        )

    return Contour(
        outer=ring_to_path(normalized.exterior),
        holes=[ring_to_path(ring) for ring in normalized.interiors],
    )


def _promote_collectively_nested_profiles(
    profiles: Sequence[ShapelyPolygon],
    initial_depths: Sequence[int],
) -> List[int]:
    """Promote loops strictly hidden by multiple same-depth profiles."""
    depths = list(initial_depths)

    for _ in profiles:
        snapshot = list(depths)
        indices_by_depth: dict[int, List[int]] = {}
        for profile_index, depth in enumerate(snapshot):
            indices_by_depth.setdefault(depth, []).append(profile_index)

        promotions: set[int] = set()
        for profile_indices in indices_by_depth.values():
            if len(profile_indices) < 2:
                continue

            group_region = _valid_union(
                [profiles[index] for index in profile_indices]
            )
            group_promotions = []
            for profile_index in profile_indices:
                profile = profiles[profile_index]
                if profile.boundary.intersects(group_region.boundary):
                    continue

                other_region = _valid_union(
                    [
                        profiles[index]
                        for index in profile_indices
                        if index != profile_index
                    ]
                )
                if other_region.contains_properly(profile):
                    group_promotions.append(profile_index)

            if len(group_promotions) < len(profile_indices):
                promotions.update(group_promotions)

        if not promotions:
            break
        for profile_index in promotions:
            depths[profile_index] = snapshot[profile_index] + 1

    return depths


def _valid_union(profiles: Sequence[ShapelyPolygon]) -> BaseGeometry:
    """Return valid union geometry for one non-empty profile group."""
    if not profiles:
        raise ValueError("Cannot union an empty profile group")
    region = unary_union(profiles) if len(profiles) > 1 else profiles[0]
    if not region.is_valid:
        region = make_valid(region)
    return region


def _closed_coords(points: Sequence[Point]) -> List[tuple[float, float]]:
    coords = [(point.x, point.y) for point in points]
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords
