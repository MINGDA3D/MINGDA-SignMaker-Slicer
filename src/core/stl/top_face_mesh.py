"""
MINGDA SignMaker - 顶面封闭网格生成器

生成顶面封闭的3D网格。
顶面封闭是一个实心平面，位于字壳顶部，填满字壳内部空间。
"""

from __future__ import annotations
from typing import List, Optional

import trimesh

from ..top_face_geometry import TopFaceGeometryBuilder
from ..types import (
    Contour,
    SliceParams,
)
from ..path_offset import PathOffset
from .mesh_utils import MeshUtils


class TopFaceMeshBuilder:
    """顶面封闭网格生成器"""

    def __init__(self, path_offset: PathOffset):
        """
        初始化顶面封闭网格生成器

        Args:
            path_offset: 路径偏移工具
        """
        self.path_offset = path_offset
        self.mesh_utils = MeshUtils()
        self.top_face_geometry_builder = TopFaceGeometryBuilder(path_offset)

    def build(self, contours: List[Contour],
              params: SliceParams) -> Optional[trimesh.Trimesh]:
        """
        构建顶面封闭网格

        顶面封闭是一个实心平面，位于字壳顶部。
        z位置从 (total_height - thickness) 到 total_height。
        使用轮廓的内缩版本（减去壁厚）生成实心顶面，填满字壳内部空间。

        Args:
            contours: 已经过边缘变换的轮廓列表（z=total_height处）
            params: 切片参数

        Returns:
            顶面网格，如果生成失败则返回None
        """
        if not contours:
            return None

        top_face = params.top_face
        if not top_face.enabled or top_face.thickness <= 0:
            return None

        meshes = []
        thickness = top_face.thickness
        total_height = params.shell.height

        # 顶面的Z起始位置
        z_start = total_height - thickness

        for contour in contours:
            try:
                geometry = self.top_face_geometry_builder.build(contour, params)
                for polygon in geometry.fill_polygons:
                    mesh = self.mesh_utils.extrude_polygon(
                        polygon, thickness, z_offset=z_start
                    )
                    if mesh is not None:
                        meshes.append(mesh)

            except Exception as e:
                print(f"警告：处理轮廓顶面失败: {e}")
                continue

        return MeshUtils.merge_meshes(meshes)
