"""Bottom-face mesh generation."""

from __future__ import annotations

import math
from typing import List, Optional

import trimesh

from ..bottom_face_geometry import BottomFaceGeometryBuilder
from ..path_offset import PathOffset
from ..types import (
    Contour,
    EdgeType,
    JoinType,
    SliceParams,
    calculate_u_shape_offset_at_z,
    is_bottom_face_effective,
    resolve_bottom_face_thickness,
    resolve_u_shape_profile_start_z,
    U_SHAPE_FINE_LAYER_HEIGHT,
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

        if params.shell.edge_type == EdgeType.U_SHAPED:
            return self._build_u_shaped_bottom_face(contours, params, thickness)

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

    def _build_u_shaped_bottom_face(
        self,
        contours: List[Contour],
        params: SliceParams,
        thickness: float,
    ) -> Optional[trimesh.Trimesh]:
        configured_layer_height = params.shell.layer_height if params.shell.layer_height > 0 else thickness
        layer_height = min(configured_layer_height, U_SHAPE_FINE_LAYER_HEIGHT)
        if layer_height <= 0:
            return None

        meshes = []
        layer_count = max(1, math.ceil(thickness / layer_height))
        for layer_index in range(layer_count):
            z_offset = layer_index * layer_height
            if z_offset >= thickness:
                break

            segment_height = min(layer_height, thickness - z_offset)
            if segment_height <= 1e-9:
                continue

            for contour in contours:
                transformed_contour = self._u_shaped_contour_at_z(
                    contour,
                    z_offset,
                    params,
                    flat_height=resolve_u_shape_profile_start_z(params.shell),
                )
                if transformed_contour is None:
                    continue
                meshes.extend(
                    self._build_bottom_face_meshes_for_contour(
                        transformed_contour,
                        params,
                        segment_height,
                        z_offset,
                    )
                )

        return MeshUtils.merge_meshes(meshes)

    def _u_shaped_contour_at_z(
        self,
        contour: Contour,
        z: float,
        params: SliceParams,
        flat_height: float = 0.0,
    ) -> Optional[Contour]:
        offset = calculate_u_shape_offset_at_z(z, params.shell, flat_height)
        if abs(offset) < 0.001:
            return contour
        return self.path_offset.offset_contour_outer_expand_holes_shrink(
            contour,
            offset,
            JoinType.MITER,
        )

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
