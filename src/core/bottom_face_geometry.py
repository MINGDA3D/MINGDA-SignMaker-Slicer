from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import List, Optional

from shapely.geometry import MultiPolygon, Point as ShapelyPoint, Polygon as ShapelyPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from .light_slot_geometry import LightSlotGeometryBuilder
from .path_offset import PathOffset
from .types import Contour, Path, PathType, Point, SliceParams, is_bottom_face_effective


@dataclass
class BottomFaceHolePlacement:
    """One manual screw-hole placement resolved against the bottom face."""

    center: Point
    radius: float
    hole_index: int
    valid: bool = True

    def to_path(self, segments: int = 32) -> Path:
        points = [
            Point(
                self.center.x + self.radius * math.cos(2.0 * math.pi * index / segments),
                self.center.y + self.radius * math.sin(2.0 * math.pi * index / segments),
            )
            for index in range(segments)
        ]
        return Path(points=points, path_type=PathType.HOLE, is_closed=True)


@dataclass
class BottomFaceGeometry:
    """Shared bottom-face geometry reused by slicing, preview, and 2D overlay."""

    placement_polygons: List[ShapelyPolygon] = field(default_factory=list)
    fill_polygons: List[ShapelyPolygon] = field(default_factory=list)
    hole_boundary_paths: List[Path] = field(default_factory=list)
    valid_holes: List[BottomFaceHolePlacement] = field(default_factory=list)
    invalid_holes: List[BottomFaceHolePlacement] = field(default_factory=list)


class BottomFaceGeometryBuilder:
    """Build bottom-face fill geometry after applying manual screw holes."""

    CIRCLE_SEGMENTS = 32
    _BUFFER_RESOLUTION = CIRCLE_SEGMENTS // 4

    def __init__(self, path_offset: PathOffset):
        self.light_slot_geometry_builder = LightSlotGeometryBuilder(path_offset)

    def build(self, contour: Contour, params: SliceParams) -> BottomFaceGeometry:
        if not is_bottom_face_effective(params):
            return BottomFaceGeometry()

        light_slot_geometry = self.light_slot_geometry_builder.build(contour, params)
        base_geometry = self._merge_geometries(light_slot_geometry.center_fill_polygons)
        if base_geometry is None:
            return BottomFaceGeometry()

        placement_polygons = self._extract_polygons(base_geometry)
        radius = max(0.0, params.bottom_face.screw_hole_diameter) / 2.0
        if radius <= 0.0:
            return BottomFaceGeometry(
                placement_polygons=placement_polygons,
                fill_polygons=placement_polygons,
            )

        candidate_geometries: List[ShapelyPolygon] = []
        invalid_indices: set[int] = set()
        for hole_index, center in enumerate(contour.screw_hole_centers):
            hole_geometry = self._build_hole_geometry(center, radius)
            candidate_geometries.append(hole_geometry)
            if not base_geometry.covers(hole_geometry):
                invalid_indices.add(hole_index)

        for first_index, first_geometry in enumerate(candidate_geometries):
            for second_index in range(first_index + 1, len(candidate_geometries)):
                overlap_area = first_geometry.intersection(candidate_geometries[second_index]).area
                if overlap_area > 1e-6:
                    invalid_indices.add(first_index)
                    invalid_indices.add(second_index)

        valid_holes: List[BottomFaceHolePlacement] = []
        invalid_holes: List[BottomFaceHolePlacement] = []
        hole_boundary_paths: List[Path] = []
        valid_geometries: List[ShapelyPolygon] = []
        for hole_index, center in enumerate(contour.screw_hole_centers):
            placement = BottomFaceHolePlacement(
                center=Point(center.x, center.y),
                radius=radius,
                hole_index=hole_index,
                valid=hole_index not in invalid_indices,
            )
            if placement.valid:
                valid_holes.append(placement)
                hole_boundary_paths.append(placement.to_path(self.CIRCLE_SEGMENTS))
                valid_geometries.append(candidate_geometries[hole_index])
            else:
                invalid_holes.append(placement)

        fill_geometry = base_geometry
        merged_holes = self._merge_geometries(valid_geometries)
        if merged_holes is not None:
            fill_geometry = self._normalize_geometry(base_geometry.difference(merged_holes))

        return BottomFaceGeometry(
            placement_polygons=placement_polygons,
            fill_polygons=self._extract_polygons(fill_geometry),
            hole_boundary_paths=hole_boundary_paths,
            valid_holes=valid_holes,
            invalid_holes=invalid_holes,
        )

    def _build_hole_geometry(self, center: Point, radius: float) -> ShapelyPolygon:
        return ShapelyPoint(center.x, center.y).buffer(radius, resolution=self._BUFFER_RESOLUTION)

    def _merge_geometries(
        self,
        geometries: List[ShapelyPolygon | MultiPolygon],
    ) -> Optional[ShapelyPolygon | MultiPolygon]:
        normalized = [self._normalize_geometry(geometry) for geometry in geometries if geometry is not None]
        normalized = [geometry for geometry in normalized if geometry is not None]
        if not normalized:
            return None
        return self._normalize_geometry(unary_union(normalized))

    def _extract_polygons(
        self,
        geometry: Optional[ShapelyPolygon | MultiPolygon],
    ) -> List[ShapelyPolygon]:
        normalized = self._normalize_geometry(geometry)
        if normalized is None:
            return []
        if isinstance(normalized, ShapelyPolygon):
            return [normalized]
        if isinstance(normalized, MultiPolygon):
            return [polygon for polygon in normalized.geoms if polygon.area > 1e-6]
        return []

    @staticmethod
    def _normalize_geometry(
        geometry: Optional[ShapelyPolygon | MultiPolygon],
    ) -> Optional[ShapelyPolygon | MultiPolygon]:
        if geometry is None or geometry.is_empty:
            return None
        if not geometry.is_valid:
            geometry = make_valid(geometry)
        if geometry.is_empty:
            return None
        if isinstance(geometry, (ShapelyPolygon, MultiPolygon)):
            return geometry
        polygons = []
        for child in getattr(geometry, "geoms", []):
            if isinstance(child, ShapelyPolygon) and child.area > 1e-6:
                polygons.append(child)
            elif isinstance(child, MultiPolygon):
                polygons.extend(polygon for polygon in child.geoms if polygon.area > 1e-6)
        if not polygons:
            return None
        if len(polygons) == 1:
            return polygons[0]
        return MultiPolygon(polygons)
