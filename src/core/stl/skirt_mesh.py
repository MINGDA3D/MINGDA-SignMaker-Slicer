"""
MINGDA SignMaker - 裙边网格生成器 v3

新设计：
- 外轮廓向外偏移5mm生成裙边环
- 内孔向内偏移5mm生成裙边环
- 每隔15mm生成连接线
"""

from __future__ import annotations
from typing import List, Optional
from copy import copy

import numpy as np
import trimesh

from ..types import Contour, SliceParams, Point, Path
from ..path_offset import PathOffset
from ..skirt_generator import SkirtGenerator
from .mesh_utils import MeshUtils


class SkirtMeshBuilder:
    """防翘裙边网格生成器 v3"""

    def __init__(self, path_offset: PathOffset):
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()
        self.skirt_generator = SkirtGenerator()

    def build(self, contours: List[Contour],
              params: SliceParams) -> Optional[trimesh.Trimesh]:
        """构建防翘裙边网格（新设计：环+连接线）"""
        if not contours:
            return None

        skirt_params = params.skirt
        skirt_height = skirt_params.height
        meshes = []

        for contour in contours:
            try:
                # 外轮廓裙边
                skirt_meshes = self.skirt_generator.generate_skirt_3d_clipped(
                    contour=contour,
                    all_contours=contours,
                    params=skirt_params,
                    wall_thickness=params.shell.wall_thickness,
                    path_offset=self.path_offset
                )

                for skirt_mesh in skirt_meshes:
                    for tri in skirt_mesh.get_triangles():
                        mesh = trimesh.Trimesh(vertices=tri, faces=[[0, 1, 2]])
                        meshes.append(mesh)

                # 内孔裙边
                for hole in contour.holes:
                    hole_skirt_params = copy(skirt_params)
                    hole_skirt_params.is_outer = False
                    hole_contour = Contour(outer=hole, holes=[])

                    hole_meshes = self.skirt_generator.generate_skirt_3d_clipped(
                        contour=hole_contour,
                        all_contours=contours,
                        params=hole_skirt_params,
                        wall_thickness=params.shell.wall_thickness,
                        path_offset=self.path_offset
                    )

                    for skirt_mesh in hole_meshes:
                        for tri in skirt_mesh.get_triangles():
                            mesh = trimesh.Trimesh(vertices=tri, faces=[[0, 1, 2]])
                            meshes.append(mesh)

            except Exception as e:
                print(f"Warning: Failed to process contour skirt: {e}")
                continue

        return MeshUtils.merge_meshes(meshes)
