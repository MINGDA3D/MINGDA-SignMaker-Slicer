"""Regression tests for lighting across sliced wall/cap boundaries."""

import numpy as np
import pytest
import trimesh

from src.ui.preview_mesh_normals import build_preview_mesh_arrays


def test_sharp_cube_edges_preserve_geometry_and_face_normals() -> None:
    """A side wall must not inherit its horizontal cap's normal."""
    mesh = trimesh.creation.box(extents=(20.0, 30.0, 0.3))
    vertices, normals, faces = build_preview_mesh_arrays(mesh)

    np.testing.assert_array_equal(vertices[faces], mesh.triangles.astype(np.float32))
    expected = np.repeat(mesh.face_normals[:, None, :], 3, axis=1)
    np.testing.assert_allclose(normals[faces], expected, atol=1e-6)
    assert len(vertices) == 24  # Shared within each flat face, split at creases.
    assert vertices.dtype == normals.dtype == np.float32
    assert faces.dtype == np.uint32
    assert all(array.flags.c_contiguous for array in (vertices, normals, faces))


def test_curved_layer_walls_remain_smooth_without_cap_normal_bleed() -> None:
    """Curved sides stay radial rather than becoming flat triangle facets."""
    mesh = trimesh.creation.cylinder(radius=20.0, height=0.3, sections=64)
    vertices, normals, faces = build_preview_mesh_arrays(mesh)
    side_faces = np.abs(mesh.face_normals[:, 2]) < 1e-6
    side_vertices = np.unique(faces[side_faces])
    cap_vertices = np.unique(faces[~side_faces])

    assert not np.intersect1d(side_vertices, cap_vertices).size
    np.testing.assert_allclose(normals[side_vertices, 2], 0.0, atol=1e-7)
    radial = vertices[side_vertices, :2]
    radial = radial / np.linalg.norm(radial, axis=1)[:, None]
    np.testing.assert_allclose(normals[side_vertices, :2], radial, atol=1e-6)
    assert len(vertices) < len(mesh.faces) * 2
    np.testing.assert_array_equal(vertices[faces], mesh.triangles.astype(np.float32))


def test_separate_print_layers_have_identical_wall_shading() -> None:
    """Repeating thin layer caps must not introduce periodic shading waves."""
    layers = []
    for z in (0.15, 0.45, 0.75):
        layer = trimesh.creation.cylinder(radius=20, height=0.3, sections=32)
        layer.apply_translation((0, 0, z))
        layers.append(layer)
    mesh = trimesh.util.concatenate(layers)
    vertices, normals, faces = build_preview_mesh_arrays(mesh)
    side_faces = np.abs(mesh.face_normals[:, 2]) < 1e-6
    side_vertices = np.unique(faces[side_faces])
    np.testing.assert_allclose(normals[side_vertices, 2], 0.0, atol=1e-7)
    xy = vertices[side_vertices, :2]
    np.testing.assert_allclose(
        normals[side_vertices, :2], xy / np.linalg.norm(xy, axis=1)[:, None], atol=1e-6
    )


@pytest.mark.parametrize("empty", [False, True])
def test_empty_or_degenerate_mesh_has_finite_normals(empty: bool) -> None:
    """Invalid face normals cannot leak NaNs into OpenGL arrays."""
    mesh = trimesh.Trimesh(
        vertices=[] if empty else [[0, 0, 0], [1, 0, 0], [2, 0, 0]],
        faces=[] if empty else [[0, 1, 2]],
        process=False,
    )
    vertices, normals, faces = build_preview_mesh_arrays(mesh)
    assert vertices.shape[1:] == normals.shape[1:] == faces.shape[1:] == (3,)
    assert np.isfinite(normals).all()
    if not empty:
        np.testing.assert_allclose(np.linalg.norm(normals, axis=1), 1.0)
        np.testing.assert_array_equal(vertices[faces], mesh.triangles.astype(np.float32))
