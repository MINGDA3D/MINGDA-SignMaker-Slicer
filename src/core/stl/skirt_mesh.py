"""
MINGDA SignMaker - Skirt mesh builder

Build skirt STL geometry from the same 2D skirt paths used by slicing.
Closed skirt rings and open connectors are buffered into 2D solids first, then
unioned before extrusion. Connectors use flat caps so the tabs stay rectangular
while still producing a single watertight body after union.
"""

from __future__ import annotations

from typing import List, Optional

import trimesh
from shapely.geometry import GeometryCollection, LineString, LinearRing, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from ..path_offset import PathOffset
from ..skirt_generator import SkirtGenerator
from ..types import Contour, Path, SliceParams, resolve_shell_wall_thickness
from .mesh_utils import MeshUtils


class SkirtMeshBuilder:
    """Build anti-warping skirt meshes."""

    def __init__(self, path_offset: PathOffset):
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()
        self.skirt_generator = SkirtGenerator()

    def build(
        self,
        contours: List[Contour],
        params: SliceParams,
        source_contours: Optional[List[Contour]] = None,
    ) -> Optional[trimesh.Trimesh]:
        if not contours or not params.skirt.enabled:
            return None

        skirt_polygons = []
        all_contours = source_contours if source_contours is not None else contours

        for contour in contours:
            try:
                outer_paths = self.skirt_generator.generate_skirt_clipped(
                    contour=contour,
                    all_contours=all_contours,
                    params=params.skirt,
                    wall_thickness=resolve_shell_wall_thickness(
                        params.shell.line_width,
                        params.shell.wall_count,
                        params.shell.layer_height,
                        wall_thickness=params.shell.wall_thickness,
                    ),
                    path_offset=self.path_offset,
                    path_line_width=(
                        params.machine.nozzle_diameter
                        if params.machine.nozzle_diameter > 0.0
                        else None
                    ),
                )
                skirt_polygons.extend(self._paths_to_polygons(outer_paths))
            except Exception as exc:
                print(f"Warning: Failed to process contour skirt: {exc}")
                continue

        if not skirt_polygons:
            return None

        unioned = unary_union(skirt_polygons)
        meshes = self._extrude_geometry(unioned, params.skirt.height)
        return MeshUtils.merge_meshes(meshes)

    def _paths_to_polygons(self, skirt_paths: List) -> List[Polygon]:
        polygons: List[Polygon] = []

        for skirt_path in skirt_paths:
            polygon = self._buffer_path(
                Path(points=skirt_path.points, is_closed=skirt_path.is_closed),
                skirt_path.line_width,
            )
            if polygon is None:
                continue
            polygons.extend(self._collect_polygons(polygon))

        return polygons

    def _buffer_path(self, path: Path, line_width: float) -> Optional[Polygon]:
        if len(path.points) < 2 or line_width <= 0:
            return None

        coords = [(point.x, point.y) for point in path.points]
        radius = line_width / 2.0

        try:
            if path.is_closed and len(coords) >= 3:
                geometry = LinearRing(coords).buffer(
                    radius, cap_style="round", join_style="round"
                )
            else:
                geometry = LineString(coords).buffer(
                    radius, cap_style="flat", join_style="round"
                )
        except Exception:
            return None

        if not geometry.is_valid:
            geometry = make_valid(geometry)

        if geometry.is_empty:
            return None

        return geometry

    def _collect_polygons(self, geometry) -> List[Polygon]:
        if geometry.is_empty:
            return []

        if isinstance(geometry, Polygon):
            return [geometry] if geometry.area > 1e-6 else []

        if hasattr(geometry, "geoms"):
            polygons: List[Polygon] = []
            for geom in geometry.geoms:
                polygons.extend(self._collect_polygons(geom))
            return polygons

        return []

    def _extrude_geometry(self, geometry, height: float) -> List[trimesh.Trimesh]:
        meshes: List[trimesh.Trimesh] = []

        if isinstance(geometry, Polygon):
            mesh = self.mesh_utils.extrude_polygon(geometry, height, 0.0)
            if mesh is not None:
                meshes.append(mesh)
            return meshes

        if isinstance(geometry, (GeometryCollection,)):
            for geom in geometry.geoms:
                meshes.extend(self._extrude_geometry(geom, height))
            return meshes

        if hasattr(geometry, "geoms"):
            for geom in geometry.geoms:
                meshes.extend(self._extrude_geometry(geom, height))

        return meshes
