"""Prime tower generation and validation helpers."""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import QCoreApplication
from shapely.geometry import LineString, LinearRing, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from .path_offset import JoinType, PathOffset
from .types import (
    Contour,
    Layer,
    LayerInfo,
    LayerPath,
    MachineParams,
    Path,
    PathRole,
    Point,
    SliceParams,
    resolve_shell_line_width,
)


class PrimeTowerValidationError(ValueError):
    """Raised when prime tower placement is invalid."""


class PrimeTowerGenerator:
    """Generate prime tower geometry from slice parameters."""

    WALL_COUNT = 2
    DEFAULT_MARGIN = 20.0

    def __init__(self, path_offset: PathOffset):
        self.path_offset = path_offset

    @classmethod
    def default_center(
        cls,
        machine: MachineParams,
        width: float = 20.0,
        depth: float = 20.0,
    ) -> tuple[float, float]:
        return (
            max(width / 2.0, float(machine.bed_width) - cls.DEFAULT_MARGIN - width / 2.0),
            max(depth / 2.0, float(machine.bed_depth) - cls.DEFAULT_MARGIN - depth / 2.0),
        )

    @staticmethod
    def get_bounds(params: SliceParams) -> tuple[float, float, float, float]:
        prime_tower = params.prime_tower
        half_width = prime_tower.width / 2.0
        half_depth = prime_tower.depth / 2.0
        return (
            prime_tower.center_x - half_width,
            prime_tower.center_y - half_depth,
            prime_tower.center_x + half_width,
            prime_tower.center_y + half_depth,
        )

    def build_contour(self, params: SliceParams) -> Contour:
        min_x, min_y, max_x, max_y = self.get_bounds(params)
        return Contour(
            outer=Path(
                points=[
                    Point(min_x, min_y),
                    Point(max_x, min_y),
                    Point(max_x, max_y),
                    Point(min_x, max_y),
                ],
                is_closed=True,
            ),
            name="prime-tower",
        )

    def build_footprint_polygon(self, params: SliceParams) -> Polygon:
        contour = self.build_contour(params)
        coords = [(point.x, point.y) for point in contour.outer.points]
        coords.append(coords[0])
        return Polygon(coords)

    def build_contours_geometry(self, contours: List[Contour]):
        """Build a lightweight 2D occupancy geometry from source contours."""
        geometries = []
        for contour in contours:
            geometry = self._contour_to_geometry(contour)
            if geometry is not None:
                geometries.append(geometry)

        if not geometries:
            return Polygon()

        merged = unary_union(geometries)
        normalized = self._normalize_polygonal_geometry(merged)
        return normalized if normalized is not None else Polygon()

    def validate(self, params: SliceParams, occupancy_geometry=None) -> None:
        prime_tower = params.prime_tower
        if not prime_tower.enabled:
            return

        if prime_tower.width <= 0.0 or prime_tower.depth <= 0.0:
            raise PrimeTowerValidationError(
                QCoreApplication.translate(
                    "PrimeTowerGenerator",
                    "Prime tower width and depth must be greater than zero.",
                )
            )

        if not 10 <= int(prime_tower.infill_density_percent) <= 80:
            raise PrimeTowerValidationError(
                QCoreApplication.translate(
                    "PrimeTowerGenerator",
                    "Prime tower infill density must stay between 10% and 80%.",
                )
            )

        line_width = resolve_shell_line_width(
            params.shell.line_width,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
            wall_count=params.shell.wall_count,
        )
        minimum_dimension = self.WALL_COUNT * 2 * line_width
        if prime_tower.width <= minimum_dimension or prime_tower.depth <= minimum_dimension:
            raise PrimeTowerValidationError(
                QCoreApplication.translate(
                    "PrimeTowerGenerator",
                    "Prime tower size must be large enough for two walls and sparse infill.",
                )
            )

        min_x, min_y, max_x, max_y = self.get_bounds(params)
        machine = params.machine
        if (
            min_x < 0.0
            or min_y < 0.0
            or max_x > float(machine.bed_width)
            or max_y > float(machine.bed_depth)
        ):
            raise PrimeTowerValidationError(
                QCoreApplication.translate(
                    "PrimeTowerGenerator",
                    "Prime tower must stay within the printer bed.",
                )
            )

        footprint = self.build_footprint_polygon(params)
        if occupancy_geometry is not None and not occupancy_geometry.is_empty:
            if footprint.intersects(occupancy_geometry):
                raise PrimeTowerValidationError(
                    QCoreApplication.translate(
                        "PrimeTowerGenerator",
                        "Prime tower overlaps existing printable geometry.",
                    )
                )

    def generate_layer_paths(
        self,
        info: LayerInfo,
        params: SliceParams,
        fill_path_generator: Callable[[Contour, float, float, float, object], List[LayerPath]],
    ) -> List[LayerPath]:
        if not params.prime_tower.enabled:
            return []

        line_width = resolve_shell_line_width(
            params.shell.line_width,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
            wall_count=params.shell.wall_count,
        )
        contour = self.build_contour(params)

        paths = self._generate_wall_paths(contour.outer, info, line_width)

        inset_contour = self.path_offset.offset_contour(
            contour,
            -(self.WALL_COUNT * line_width),
            JoinType.MITER,
        )
        if inset_contour is not None:
            density = max(params.prime_tower.infill_density_percent / 100.0, 0.01)
            fill_spacing = line_width / density
            layer_index = int(round(info.z_height / info.layer_height)) if info.layer_height > 0.0 else 0
            fill_angle = 45.0 if layer_index % 2 == 0 else 135.0
            fill_paths = fill_path_generator(
                inset_contour,
                fill_spacing,
                fill_angle,
                line_width,
                info.extruder,
            )
            for path in fill_paths:
                path.role = PathRole.PRIME_TOWER
            paths.extend(fill_paths)

        return paths

    def build_occupied_geometry(self, layers: List[Layer]):
        polygons = []
        for layer in layers:
            for path in layer.paths:
                if path.role == PathRole.PRIME_TOWER:
                    continue
                geometry = self._buffer_layer_path(path)
                if geometry is None or geometry.is_empty:
                    continue
                polygons.append(geometry)

        if not polygons:
            return Polygon()

        occupied = unary_union(polygons)
        if not occupied.is_valid:
            occupied = make_valid(occupied)
        return occupied

    def _contour_to_geometry(self, contour: Contour):
        outer_coords = self._path_coords(contour.outer)
        if len(outer_coords) < 4:
            return None

        hole_coords = [self._path_coords(hole) for hole in contour.holes]
        hole_coords = [coords for coords in hole_coords if len(coords) >= 4]

        polygon = Polygon(outer_coords, hole_coords)
        return self._normalize_polygonal_geometry(polygon)

    @staticmethod
    def _path_coords(path: Path) -> List[tuple[float, float]]:
        coords = [(point.x, point.y) for point in path.points]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords

    def _normalize_polygonal_geometry(self, geometry):
        if geometry is None or geometry.is_empty:
            return None

        if not geometry.is_valid:
            geometry = make_valid(geometry)
        if geometry.is_empty:
            return None

        if geometry.geom_type in {"Polygon", "MultiPolygon"}:
            return geometry

        if geometry.geom_type != "GeometryCollection":
            return None

        polygonal_parts = []
        for part in geometry.geoms:
            normalized = self._normalize_polygonal_geometry(part)
            if normalized is not None:
                polygonal_parts.append(normalized)

        if not polygonal_parts:
            return None

        merged = unary_union(polygonal_parts)
        if not merged.is_valid:
            merged = make_valid(merged)
        if merged.is_empty:
            return None
        return merged if merged.geom_type in {"Polygon", "MultiPolygon"} else None

    def _generate_wall_paths(
        self,
        loop_path: Path,
        info: LayerInfo,
        line_width: float,
    ) -> List[LayerPath]:
        paths: List[LayerPath] = []
        for wall_index in range(self.WALL_COUNT):
            offset_distance = -(line_width / 2.0 + wall_index * line_width)
            offset_results = self.path_offset.offset(
                loop_path,
                offset_distance,
                JoinType.MITER,
            )
            for offset_path in offset_results:
                paths.append(
                    LayerPath(
                        points=list(offset_path.points),
                        role=PathRole.PRIME_TOWER,
                        extruder=info.extruder,
                        line_width=line_width,
                        is_closed=True,
                    )
                )
        return paths

    def _buffer_layer_path(self, path: LayerPath):
        if len(path.points) < 2 or path.line_width <= 0.0:
            return None

        coords = [(point.x, point.y) for point in path.points]
        radius = path.line_width / 2.0

        try:
            if path.is_closed and len(coords) >= 3:
                geometry = LinearRing(coords).buffer(
                    radius,
                    join_style="mitre",
                    mitre_limit=2.0,
                )
            else:
                geometry = LineString(coords).buffer(
                    radius,
                    cap_style="round",
                    join_style="round",
                )
        except Exception:
            return None

        if not geometry.is_valid:
            geometry = make_valid(geometry)
        return geometry
