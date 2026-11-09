"""Prepare render-only mesh normals while preserving sharp surface boundaries."""

from __future__ import annotations

import numpy as np
import trimesh


def build_preview_mesh_arrays(
    mesh: trimesh.Trimesh,
    crease_angle_degrees: float = 45.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split sharp-edge vertices and smooth only locally connected face corners.

    Sliced solids contain a horizontal cap at each layer boundary. Averaging
    those cap normals into the wall normals produces repeating light/dark
    waves. Face-corner connectivity keeps caps separate, preserves curved
    walls, and also handles a crease whose two faces reconnect elsewhere on
    the same surface. Triangle coordinates, order, and winding are unchanged.
    """
    faces = np.asarray(mesh.faces, dtype=np.int64)
    if not len(faces):
        empty_vectors = np.empty((0, 3), dtype=np.float32)
        return empty_vectors, empty_vectors.copy(), np.empty((0, 3), dtype=np.uint32)

    face_normals = np.asarray(mesh.face_normals)
    adjacency, shared_edges = trimesh.graph.face_adjacency(
        faces=faces, return_edges=True
    )
    if len(adjacency):
        normal_dot = np.einsum(
            "ij,ij->i", face_normals[adjacency[:, 0]], face_normals[adjacency[:, 1]]
        )
        angle = np.clip(crease_angle_degrees, 0.0, 180.0)
        smooth = normal_dot >= np.cos(np.radians(angle)) - 1e-12
        # Degenerate triangles have no usable normal and must not join a fan.
        smooth &= (face_normals[adjacency] ** 2).sum(axis=2).min(axis=1) > 0.5
        adjacency = adjacency[smooth]
        shared_edges = shared_edges[smooth]

    links = np.empty((len(adjacency) * 2, 2), dtype=np.int64)
    for endpoint in range(2):
        vertex = shared_edges[:, endpoint, None]
        for side in range(2):
            face_indices = adjacency[:, side]
            corner = (faces[face_indices] == vertex).argmax(axis=1)
            links[endpoint::2, side] = face_indices * 3 + corner

    labels = trimesh.graph.connected_component_labels(links, node_count=faces.size)
    _, representatives = np.unique(labels, return_index=True)
    vertices = np.ascontiguousarray(
        np.asarray(mesh.vertices)[faces.reshape(-1)[representatives]], dtype=np.float32
    )
    render_faces = labels.reshape((-1, 3))
    normals = trimesh.geometry.weighted_vertex_normals(
        len(vertices), render_faces, face_normals, np.asarray(mesh.face_angles)
    )
    invalid_normals = ~np.isfinite(normals).all(axis=1) | (
        np.linalg.norm(normals, axis=1) < 1e-12
    )
    normals[invalid_normals] = (0.0, 0.0, 1.0)
    return (
        vertices,
        np.ascontiguousarray(normals, dtype=np.float32),
        np.ascontiguousarray(render_faces, dtype=np.uint32),
    )
