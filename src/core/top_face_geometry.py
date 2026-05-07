from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from shapely.geometry import MultiPolygon, Polygon as ShapelyPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from .path_offset import PathOffset
from .types import (
    Contour,
    Path,
    Point,
    SliceParams,
    resolve_shell_wall_thickness,
)


@dataclass
class TopFaceGeometry:
    """Top-face fill polygons after preserving existing inner holes."""

    fill_polygons: List[ShapelyPolygon] = field(default_factory=list)


class TopFaceGeometryBuilder:
    """Build top-face fill geometry from the real cavity boundary."""

    def __init__(self, path_offset: PathOffset):
        self.path_offset = path_offset

    def build(self, contour: Contour, params: SliceParams) -> TopFaceGeometry:
        if not params.top_face.enabled:
            return TopFaceGeometry()

        fill_geometry = self._build_interior_geometry(contour, params)
        return TopFaceGeometry(fill_polygons=self._extract_polygons(fill_geometry))

    def _build_interior_geometry(
        self,
        contour: Contour,
        params: SliceParams,
    ) -> Optional[ShapelyPolygon | MultiPolygon]:
        inset_distance = resolve_shell_wall_thickness(
            params.shell.line_width,
            params.shell.wall_count,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
        )
        if inset_distance > 0.0:
            outer_paths = self.path_offset.offset(contour.outer, -inset_distance)
        else:
            outer_paths = [self._clone_path(contour.outer)]

        outer_region = self._paths_to_geometry(outer_paths)
        if outer_region is None:
            return None

        hole_region = self._paths_to_geometry(contour.holes)
        if hole_region is not None:
            outer_region = self._normalize_geometry(outer_region.difference(hole_region))

        return outer_region

    def _paths_to_geometry(
        self,
        paths: List[Path],
    ) -> Optional[ShapelyPolygon | MultiPolygon]:
        polygons = []
        for path in paths:
            coords = self._path_coords(path)
            if len(coords) < 4:
                continue
            geometry = self._normalize_geometry(ShapelyPolygon(coords))
            if geometry is None:
                continue
            if isinstance(geometry, ShapelyPolygon):
                polygons.append(geometry)
            elif isinstance(geometry, MultiPolygon):
                polygons.extend(polygon for polygon in geometry.geoms if polygon.area > 1e-6)

        if not polygons:
            return None
        return self._normalize_geometry(unary_union(polygons))

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

    def _path_coords(self, path: Path) -> List[tuple[float, float]]:
        coords = [(point.x, point.y) for point in path.points]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords

    def _clone_path(self, path: Path) -> Path:
        return Path(
            points=[Point(point.x, point.y) for point in path.points],
            path_type=path.path_type,
            color=path.color,
            is_closed=path.is_closed,
            start_point_index=path.start_point_index,
            print_order=path.print_order,
        )

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
