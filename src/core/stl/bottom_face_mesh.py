"""Bottom-face mesh generation."""

from __future__ import annotations

from typing import List, Optional

import trimesh

from ..bottom_face_geometry import BottomFaceGeometryBuilder
from ..path_offset import PathOffset
from ..types import (
    Contour,
    SliceParams,
    is_bottom_face_effective,
    resolve_bottom_face_thickness,
)
from .mesh_utils import MeshUtils


class BottomFaceMeshBuilder:
    """Build the solid bottom closure mesh for STL export and preview."""

    def __init__(self, path_offset: PathOffset):
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()
        self.bottom_face_geometry_builder = BottomFaceGeometryBuilder(path_offset)

    def build(
        self,
        contours: List[Contour],
        params: SliceParams,
    ) -> Optional[trimesh.Trimesh]:
        if not contours:
            return None

        thickness = resolve_bottom_face_thickness(params)
        if not is_bottom_face_effective(params) or thickness <= 0:
            return None

        return self._build_flat_bottom_face(contours, params, thickness)

    def _build_flat_bottom_face(
        self,
        contours: List[Contour],
        params: SliceParams,
        thickness: float,
    ) -> Optional[trimesh.Trimesh]:
        meshes = []
        for contour in contours:
            meshes.extend(
                self._build_bottom_face_meshes_for_contour(
                    contour,
                    params,
                    thickness,
                    0.0,
                )
            )
        return MeshUtils.merge_meshes(meshes)

    def _build_bottom_face_meshes_for_contour(
        self,
        contour: Contour,
        params: SliceParams,
        height: float,
        z_offset: float,
    ) -> List[trimesh.Trimesh]:
        meshes: List[trimesh.Trimesh] = []
        try:
            geometry = self.bottom_face_geometry_builder.build(contour, params)
            for polygon in geometry.fill_polygons:
                mesh = self.mesh_utils.extrude_polygon(polygon, height, z_offset=z_offset)
                if mesh is not None:
                    meshes.append(mesh)
        except Exception as e:
            print(f"Warning: failed to build bottom face geometry: {e}")
        return meshes
