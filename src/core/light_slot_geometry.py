from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from shapely.geometry import MultiPolygon, Polygon as ShapelyPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from .path_offset import PathOffset
from .types import Contour, Path, PathType, Point, SliceParams, resolve_shell_wall_thickness


@dataclass
class LightSlotGeometry:
    """Shared 2D light-slot geometry reused by slicing and mesh builders."""

    slot_band_polygons: List[ShapelyPolygon] = field(default_factory=list)
    slot_free_edge_paths: List[Path] = field(default_factory=list)
    center_fill_polygons: List[ShapelyPolygon] = field(default_factory=list)


class LightSlotGeometryBuilder:
    """Build bottom light-slot regions from the real cavity contour at z=0."""

    def __init__(self, path_offset: PathOffset):
        self.path_offset = path_offset

    def build(self, contour: Contour, params: SliceParams) -> LightSlotGeometry:
        base_geometry = self._build_base_interior_geometry(contour, params)
        if base_geometry is None:
            return LightSlotGeometry()

        slot_params = params.light_slot
        slot_enabled = (
            slot_params.enabled
            and slot_params.width > 0.0
            and slot_params.depth > 0.0
            and (slot_params.outer_enabled or slot_params.hole_enabled)
        )

        if not slot_enabled:
            return LightSlotGeometry(
                center_fill_polygons=self._extract_polygons(base_geometry),
            )

        slot_geometries = []
        free_edge_paths: List[Path] = []

        for polygon in self._extract_polygons(base_geometry):
            if slot_params.outer_enabled:
                outer_geometry, outer_free_paths = self._build_outer_slot_geometry(polygon, params)
                if outer_geometry is not None:
                    slot_geometries.append(outer_geometry)
                    free_edge_paths.extend(outer_free_paths)

            if slot_params.hole_enabled:
                for interior in polygon.interiors:
                    hole_geometry, hole_free_paths = self._build_hole_slot_geometry(
                        polygon,
                        list(interior.coords),
                        params,
                    )
                    if hole_geometry is not None:
                        slot_geometries.append(hole_geometry)
                        free_edge_paths.extend(hole_free_paths)

        slot_geometry = self._merge_geometries(slot_geometries)
        center_geometry = base_geometry
        if slot_geometry is not None:
            center_geometry = self._normalize_geometry(base_geometry.difference(slot_geometry))

        return LightSlotGeometry(
            slot_band_polygons=self._extract_polygons(slot_geometry),
            slot_free_edge_paths=free_edge_paths,
            center_fill_polygons=self._extract_polygons(center_geometry),
        )

    def _build_base_interior_geometry(
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

        # 内孔墙体向孔内侧生长，空腔一侧始终以原始孔边为基准。
        hole_region = self._paths_to_geometry(contour.holes)
        if hole_region is not None:
            outer_region = self._normalize_geometry(outer_region.difference(hole_region))

        return outer_region

    def _build_outer_slot_geometry(
        self,
        polygon: ShapelyPolygon,
        params: SliceParams,
    ):
        slot_params = params.light_slot
        wall_gap = max(0.0, slot_params.wall_gap)
        width = max(0.0, slot_params.width)
        exterior_path = self._ring_to_path(list(polygon.exterior.coords), PathType.OUTER)

        start_paths = [exterior_path]
        if wall_gap > 1e-6:
            start_paths = self.path_offset.offset(exterior_path, -wall_gap)
        if not start_paths:
            return None, []

        end_paths = self.path_offset.offset(exterior_path, -(wall_gap + width))
        if not end_paths:
            return None, []

        start_region = self._paths_to_geometry(start_paths)
        end_region = self._paths_to_geometry(end_paths)
        if start_region is None or end_region is None:
            return None, []

        ring_geometry = self._normalize_geometry(start_region.difference(end_region))
        if ring_geometry is None:
            return None, []

        clipped_geometry = self._normalize_geometry(ring_geometry.intersection(polygon))
        if clipped_geometry is None:
            return None, []

        return clipped_geometry, [self._clone_path(path) for path in end_paths]

    def _build_hole_slot_geometry(
        self,
        polygon: ShapelyPolygon,
        hole_coords: List[tuple[float, float]],
        params: SliceParams,
    ):
        slot_params = params.light_slot
        if self._should_skip_hole(hole_coords, params):
            return None, []

        wall_gap = max(0.0, slot_params.wall_gap)
        width = max(0.0, slot_params.width)
        hole_path = self._ring_to_path(hole_coords, PathType.HOLE)

        start_paths = [hole_path]
        if wall_gap > 1e-6:
            start_paths = self.path_offset.offset(hole_path, wall_gap)
        if not start_paths:
            return None, []

        end_paths = self.path_offset.offset(hole_path, wall_gap + width)
        if not end_paths:
            return None, []

        start_region = self._paths_to_geometry(start_paths)
        end_region = self._paths_to_geometry(end_paths)
        if start_region is None or end_region is None:
            return None, []

        ring_geometry = self._normalize_geometry(end_region.difference(start_region))
        if ring_geometry is None:
            return None, []

        clipped_geometry = self._normalize_geometry(ring_geometry.intersection(polygon))
        if clipped_geometry is None:
            return None, []

        free_paths = [
            self._clone_path(path, fallback_path_type=PathType.HOLE)
            for path in end_paths
        ]
        return clipped_geometry, free_paths

    def _should_skip_hole(
        self,
        hole_coords: List[tuple[float, float]],
        params: SliceParams,
    ) -> bool:
        slot_params = params.light_slot
        if not slot_params.auto_skip_small_holes or slot_params.min_hole_span <= 0.0:
            return False

        xs = [coord[0] for coord in hole_coords[:-1] or hole_coords]
        ys = [coord[1] for coord in hole_coords[:-1] or hole_coords]
        if not xs or not ys:
            return True

        span = min(max(xs) - min(xs), max(ys) - min(ys))
        return span < slot_params.min_hole_span

    def _contour_to_polygon(self, contour: Contour) -> Optional[ShapelyPolygon]:
        outer_coords = self._path_coords(contour.outer)
        if len(outer_coords) < 4:
            return None

        hole_coords = [self._path_coords(hole) for hole in contour.holes]
        hole_coords = [coords for coords in hole_coords if len(coords) >= 4]

        polygon = ShapelyPolygon(outer_coords, hole_coords)
        polygon = self._normalize_geometry(polygon)
        if polygon is None or polygon.geom_type != "Polygon":
            return None
        return polygon

    def _path_coords(self, path: Path) -> List[tuple[float, float]]:
        coords = [(point.x, point.y) for point in path.points]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords

    def _ring_to_path(
        self,
        coords: List[tuple[float, float]],
        path_type: PathType,
    ) -> Path:
        if coords and coords[0] == coords[-1]:
            coords = coords[:-1]
        return Path(
            points=[Point(x, y) for x, y in coords],
            path_type=path_type,
            is_closed=True,
        )

    def _paths_to_geometry(self, paths: Iterable[Path]):
        polygons = []
        for path in paths:
            coords = self._path_coords(path)
            if len(coords) < 4:
                continue
            polygon = ShapelyPolygon(coords)
            polygon = self._normalize_geometry(polygon)
            if polygon is not None:
                polygons.append(polygon)

        return self._merge_geometries(polygons)

    def _merge_geometries(self, geometries: Iterable):
        valid_geometries = []
        for geometry in geometries:
            normalized = self._normalize_geometry(geometry)
            if normalized is not None:
                valid_geometries.append(normalized)

        if not valid_geometries:
            return None

        merged = unary_union(valid_geometries)
        return self._normalize_geometry(merged)

    def _extract_polygons(self, geometry) -> List[ShapelyPolygon]:
        if geometry is None:
            return []

        geometry = self._normalize_geometry(geometry)
        if geometry is None:
            return []

        if geometry.geom_type == "Polygon":
            return [geometry]
        if geometry.geom_type == "MultiPolygon":
            return [geom for geom in geometry.geoms if geom.area > 1e-6]
        if geometry.geom_type == "GeometryCollection":
            polygons: List[ShapelyPolygon] = []
            for geom in geometry.geoms:
                polygons.extend(self._extract_polygons(geom))
            return polygons

        return []

    def _normalize_geometry(self, geometry):
        if geometry is None:
            return None
        if not geometry.is_valid:
            geometry = make_valid(geometry)
        if geometry.is_empty or getattr(geometry, "area", 0.0) < 1e-6:
            return None
        return geometry

    def _clone_path(self, path: Path, fallback_path_type: Optional[PathType] = None) -> Path:
        return Path(
            points=[Point(point.x, point.y) for point in path.points],
            path_type=path.path_type if path.path_type is not None else fallback_path_type or PathType.OUTER,
            color=path.color,
            is_closed=path.is_closed,
        )
