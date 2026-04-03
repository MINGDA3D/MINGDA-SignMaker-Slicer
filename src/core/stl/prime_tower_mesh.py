"""Build prime tower mesh from sliced prime tower paths."""

from __future__ import annotations

from typing import List

import trimesh
from shapely.geometry import GeometryCollection, LineString, LinearRing, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from ..types import Layer, Path, PathRole
from .mesh_utils import MeshUtils


class PrimeTowerMeshBuilder:
    """Build prime tower meshes from actual layer paths."""

    def __init__(self):
        self.mesh_utils = MeshUtils()

    def build(self, layers: List[Layer]) -> trimesh.Trimesh | None:
        meshes: List[trimesh.Trimesh] = []

        for layer in layers:
            prime_paths = [path for path in layer.paths if path.role == PathRole.PRIME_TOWER]
            if not prime_paths:
                continue

            polygons: List[Polygon] = []
            for prime_path in prime_paths:
                geometry = self._buffer_path(
                    Path(points=prime_path.points, is_closed=prime_path.is_closed),
                    prime_path.line_width,
                )
                if geometry is None or geometry.is_empty:
                    continue
                polygons.extend(self._collect_polygons(geometry))

            if not polygons:
                continue

            unioned = unary_union(polygons)
            meshes.extend(self._extrude_geometry(unioned, layer.layer_height, layer.z_height))

        return MeshUtils.merge_meshes(meshes)

    def _buffer_path(self, path: Path, line_width: float):
        if len(path.points) < 2 or line_width <= 0.0:
            return None

        coords = [(point.x, point.y) for point in path.points]
        radius = line_width / 2.0

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

    def _extrude_geometry(self, geometry, height: float, z_offset: float) -> List[trimesh.Trimesh]:
        meshes: List[trimesh.Trimesh] = []

        if isinstance(geometry, Polygon):
            mesh = self.mesh_utils.extrude_polygon(geometry, height, z_offset)
            if mesh is not None:
                meshes.append(mesh)
            return meshes

        if isinstance(geometry, GeometryCollection):
            for geom in geometry.geoms:
                meshes.extend(self._extrude_geometry(geom, height, z_offset))
            return meshes

        if hasattr(geometry, "geoms"):
            for geom in geometry.geoms:
                meshes.extend(self._extrude_geometry(geom, height, z_offset))

        return meshes
