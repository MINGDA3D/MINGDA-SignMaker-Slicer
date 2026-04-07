from __future__ import annotations

from typing import List, Optional

import trimesh
from shapely.geometry import LinearRing, LineString
from shapely.validation import make_valid

from ..light_slot_geometry import LightSlotGeometryBuilder
from ..path_offset import PathOffset
from ..types import Contour, Path, SliceParams, resolve_shell_line_width
from .mesh_utils import MeshUtils


class LightSlotMeshBuilder:
    """Generate the bottom light-slot mesh for STL export and solid preview."""

    def __init__(self, path_offset: PathOffset):
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()
        self.geometry_builder = LightSlotGeometryBuilder(path_offset)

    def build(
        self,
        contours: List[Contour],
        params: SliceParams,
    ) -> Optional[trimesh.Trimesh]:
        if not contours:
            return None

        slot_params = params.light_slot
        if (
            not slot_params.enabled
            or slot_params.width <= 0.0
            or slot_params.depth <= 0.0
        ):
            return None

        meshes = []
        floor_thickness = min(
            params.shell.layer_height * max(0, slot_params.floor_layers),
            slot_params.depth,
        )
        free_edge_line_width = resolve_shell_line_width(
            params.shell.line_width,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
            wall_count=params.shell.wall_count,
        )

        for contour in contours:
            geometry = self.geometry_builder.build(contour, params)

            if floor_thickness > 0.0:
                for polygon in geometry.slot_band_polygons:
                    mesh = self.mesh_utils.extrude_polygon(polygon, floor_thickness, 0.0)
                    if mesh is not None:
                        meshes.append(mesh)

            for free_edge_path in geometry.slot_free_edge_paths:
                wall_mesh = self._build_free_edge_wall(
                    free_edge_path,
                    free_edge_line_width,
                    slot_params.depth,
                )
                if wall_mesh is not None:
                    meshes.append(wall_mesh)

        return MeshUtils.merge_meshes(meshes)

    def _build_free_edge_wall(
        self,
        path: Path,
        wall_thickness: float,
        height: float,
    ) -> Optional[trimesh.Trimesh]:
        if len(path.points) < 2 or wall_thickness <= 0.0 or height <= 0.0:
            return None

        coords = [(point.x, point.y) for point in path.points]
        geometry = None

        try:
            if path.is_closed and len(coords) >= 3:
                ring = LinearRing(coords)
                geometry = ring.buffer(wall_thickness * 0.5, join_style=2, mitre_limit=2.0)
            else:
                line = LineString(coords)
                geometry = line.buffer(
                    wall_thickness * 0.5,
                    cap_style=2,
                    join_style=2,
                    mitre_limit=2.0,
                )
        except Exception:
            return None

        if geometry is None:
            return None
        if not geometry.is_valid:
            geometry = make_valid(geometry)
        if geometry.is_empty or getattr(geometry, "area", 0.0) < 1e-6:
            return None

        meshes = []
        if geometry.geom_type == "Polygon":
            mesh = self.mesh_utils.extrude_polygon(geometry, height, 0.0)
            if mesh is not None:
                meshes.append(mesh)
        elif geometry.geom_type == "MultiPolygon":
            for polygon in geometry.geoms:
                if polygon.area < 1e-6:
                    continue
                mesh = self.mesh_utils.extrude_polygon(polygon, height, 0.0)
                if mesh is not None:
                    meshes.append(mesh)

        return MeshUtils.merge_meshes(meshes)
