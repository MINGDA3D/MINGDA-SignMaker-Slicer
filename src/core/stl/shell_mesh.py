"""
MINGDA SignMaker shell mesh generation.

The preferred path builds each layer from closed contour regions, similar to a
CAD shell operation: material = profile - inward_offset(profile, wall_thickness).
The legacy WALL-centerline ribbon builder remains as a fallback for callers that
do not have source contours and slicing parameters.
"""

from __future__ import annotations

from typing import List, Optional

import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from ..path_offset import PathOffset
from ..types import (
    Contour,
    Layer,
    LayerPath,
    PathRole,
    Point,
    SliceParams,
    resolve_shell_wall_thickness,
)
from ..types import Path as CorePath
from .mesh_utils import MeshUtils


class ShellMeshBuilder:
    """Build hollow sign-letter shell meshes."""

    MIN_POLYGON_AREA = 1e-6
    TRIANGULATION_SIMPLIFY_TOLERANCE = 1e-6

    def __init__(self, path_offset: PathOffset, wall_thickness: float = 1.2):
        self.path_offset = path_offset
        self.wall_thickness = wall_thickness
        self.mesh_utils = MeshUtils()

    def build(
        self,
        layers: List[Layer],
        contours: Optional[List[Contour]] = None,
        params: Optional[SliceParams] = None,
    ) -> Optional[trimesh.Trimesh]:
        """Build shell mesh from contour regions, falling back to WALL ribbons."""
        if not layers:
            return None

        if contours and params:
            mesh = self._build_from_contour_regions(layers, contours, params)
            if mesh is not None:
                return mesh

        return self._build_from_wall_paths(layers)

    def _build_from_contour_regions(
        self,
        layers: List[Layer],
        contours: List[Contour],
        params: SliceParams,
    ) -> Optional[trimesh.Trimesh]:
        from ..slice_engine import SliceEngine

        temp_engine = SliceEngine()
        meshes: List[trimesh.Trimesh] = []

        for layer in layers:
            if not any(path.role == PathRole.WALL for path in layer.paths):
                continue

            polygons = self._build_layer_shell_region_polygons(
                contours,
                layer,
                params,
                temp_engine,
            )
            for polygon in polygons:
                mesh = self.mesh_utils.extrude_polygon(
                    polygon,
                    layer.layer_height,
                    layer.z_height,
                )
                if mesh is not None:
                    meshes.append(mesh)

        return MeshUtils.merge_meshes(meshes)

    def _build_layer_shell_region_polygons(
        self,
        contours: List[Contour],
        layer: Layer,
        params: SliceParams,
        temp_engine=None,
    ) -> List[ShapelyPolygon]:
        """Return material regions for one layer using contour shelling."""
        if not any(path.role == PathRole.WALL for path in layer.paths):
            return []

        if temp_engine is None:
            from ..slice_engine import SliceEngine

            temp_engine = SliceEngine()

        wall_thickness = resolve_shell_wall_thickness(
            params.shell.line_width,
            params.shell.wall_count,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
        )
        if wall_thickness <= 0.0:
            return []

        profiles: List[ShapelyPolygon] = []
        for contour in contours:
            transformed = temp_engine._apply_edge_profile(
                contour,
                layer.z_height,
                params.shell,
            )
            if transformed is None:
                continue
            profile = self._contour_to_polygon(transformed)
            if profile is not None:
                profiles.extend(self._extract_polygons(profile))

        if not profiles:
            return []

        profile_region = unary_union(profiles) if len(profiles) > 1 else profiles[0]
        if not profile_region.is_valid:
            profile_region = make_valid(profile_region)

        return self._build_profile_shell_region(profile_region, wall_thickness)

    def _build_contour_shell_region(
        self,
        contour: Contour,
        wall_thickness: float,
    ) -> List[ShapelyPolygon]:
        profile = self._contour_to_polygon(contour)
        if profile is None:
            return []

        return self._build_profile_shell_region(profile, wall_thickness)

    def _build_profile_shell_region(
        self,
        profile,
        wall_thickness: float,
    ) -> List[ShapelyPolygon]:
        cavity = profile.buffer(
            -wall_thickness,
            join_style=2,
            mitre_limit=self.path_offset.miter_limit,
        )
        if not cavity.is_valid:
            cavity = make_valid(cavity)

        if cavity.is_empty or cavity.area < self.MIN_POLYGON_AREA:
            shell_region = profile
        else:
            shell_region = profile.difference(cavity)

        if not shell_region.is_valid:
            shell_region = make_valid(shell_region)

        shell_region = self._remove_tiny_holes(
            shell_region,
            self._tiny_hole_area_threshold(wall_thickness),
        )
        shell_region = self._stabilize_for_triangulation(shell_region)

        return self._extract_polygons(shell_region)

    def _contour_to_polygon(self, contour: Contour):
        outer_coords = self._closed_coords(contour.outer.points)
        if len(outer_coords) < 4:
            return None

        hole_coords = [
            coords
            for coords in (self._closed_coords(hole.points) for hole in contour.holes)
            if len(coords) >= 4
        ]

        polygon = ShapelyPolygon(outer_coords, hole_coords)
        if not polygon.is_valid:
            polygon = make_valid(polygon)
        if polygon.is_empty or polygon.area < self.MIN_POLYGON_AREA:
            return None
        return polygon

    def _build_from_wall_paths(self, layers: List[Layer]) -> Optional[trimesh.Trimesh]:
        meshes: List[trimesh.Trimesh] = []

        for layer in layers:
            wall_paths = [p for p in layer.paths if p.role == PathRole.WALL]
            if not wall_paths:
                continue

            for path in wall_paths:
                polygon = self._build_wall_path_polygon(path)
                if polygon is None:
                    continue

                for geom in self._extract_polygons(polygon):
                    mesh = self.mesh_utils.extrude_polygon(
                        geom,
                        layer.layer_height,
                        layer.z_height,
                    )
                    if mesh is not None:
                        meshes.append(mesh)

        return MeshUtils.merge_meshes(meshes)

    def _build_wall_path_polygon(self, path: LayerPath):
        if len(path.points) < 3:
            return None

        wall_thickness = path.line_width if path.line_width > 0.0 else self.wall_thickness
        half_wall = wall_thickness / 2
        core_path = CorePath(points=path.points, is_closed=path.is_closed)

        outer_results = self.path_offset.offset(core_path, half_wall)
        inner_results = self.path_offset.offset(core_path, -half_wall)
        if not outer_results:
            return None

        outer_coords = self._closed_coords(outer_results[0].points)
        if len(outer_coords) < 4:
            return None

        try:
            if inner_results:
                inner_coords = self._closed_coords(inner_results[0].points)
                polygon = (
                    ShapelyPolygon(outer_coords, [inner_coords])
                    if len(inner_coords) >= 4
                    else ShapelyPolygon(outer_coords)
                )
            else:
                polygon = ShapelyPolygon(outer_coords)

            if not polygon.is_valid:
                polygon = make_valid(polygon)
            if polygon.is_empty or polygon.area < self.MIN_POLYGON_AREA:
                return None
            return polygon
        except Exception as exc:
            print(f"Warning: cannot build shell wall path polygon: {exc}")
            return None

    @staticmethod
    def _closed_coords(points: List[Point]) -> List[tuple]:
        coords = [(point.x, point.y) for point in points]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords

    def _extract_polygons(self, geometry) -> List[ShapelyPolygon]:
        if geometry is None or geometry.is_empty:
            return []

        if geometry.geom_type == "Polygon":
            if geometry.area > self.MIN_POLYGON_AREA:
                return [geometry]
            return []

        if hasattr(geometry, "geoms"):
            polygons: List[ShapelyPolygon] = []
            for child in geometry.geoms:
                polygons.extend(self._extract_polygons(child))
            return polygons

        return []

    @staticmethod
    def _tiny_hole_area_threshold(wall_thickness: float) -> float:
        if wall_thickness <= 0.0:
            return 0.0
        return min(0.05, max(1e-6, wall_thickness * wall_thickness * 0.01))

    def _remove_tiny_holes(self, geometry, min_hole_area: float):
        if min_hole_area <= 0.0 or geometry is None or geometry.is_empty:
            return geometry

        if geometry.geom_type == "Polygon":
            kept_interiors = []
            for ring in geometry.interiors:
                if ShapelyPolygon(ring).area >= min_hole_area:
                    kept_interiors.append(ring)

            if len(kept_interiors) == len(geometry.interiors):
                return geometry

            cleaned = ShapelyPolygon(geometry.exterior, kept_interiors)
            if not cleaned.is_valid:
                cleaned = make_valid(cleaned)
            return cleaned

        if hasattr(geometry, "geoms"):
            cleaned_parts = [
                self._remove_tiny_holes(child, min_hole_area)
                for child in geometry.geoms
            ]
            cleaned_parts = [
                child for child in cleaned_parts
                if child is not None and not child.is_empty
            ]
            if not cleaned_parts:
                return geometry
            return unary_union(cleaned_parts) if len(cleaned_parts) > 1 else cleaned_parts[0]

        return geometry

    def _stabilize_for_triangulation(self, geometry):
        if geometry is None or geometry.is_empty:
            return geometry

        stabilized = geometry.simplify(
            self.TRIANGULATION_SIMPLIFY_TOLERANCE,
            preserve_topology=True,
        )
        if not stabilized.is_valid:
            stabilized = make_valid(stabilized)
        return stabilized
