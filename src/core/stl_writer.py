"""
SignMaker Slicer - STL导出模块

使用 trimesh + shapely 将切片结果转换为STL格式的3D模型文件。

STL生成算法（空心字壳）：
1. 每个WALL路径代表壁的中心线
2. 根据壁厚向外/内偏移生成外壁和内壁轮廓
3. 使用 Shapely 创建带孔多边形（外轮廓作为边界，内轮廓作为孔）
4. 使用 trimesh.extrude_polygon 挤出成3D网格
5. 合并所有层的网格并输出为STL文件

包边功能：
- 包边是在字壳顶部添加的一圈边框
- 向内包边：在字壳内侧，围绕字壳的内轮廓
- 向外包边：在字壳外侧，围绕字壳的外轮廓

模块化设计：
本模块将网格生成功能拆分为多个子模块，各司其职：
- mesh_utils: 通用网格工具
- shell_mesh: 字壳网格
- edge_wrap_mesh: 包边/勾边网格
- step_mesh: 台阶网格
- skirt_mesh: 裙边网格
- connected_mesh: 连襟网格
- bottom_face_mesh: 底面封闭网格
"""

from __future__ import annotations
from typing import List, Optional

import trimesh

from .types import Contour, SliceResult, SliceParams
from .path_offset import PathOffset
from .stl import (
    MeshUtils,
    ShellMeshBuilder,
    EdgeWrapMeshBuilder,
    StepMeshBuilder,
    SkirtMeshBuilder,
    ConnectedMeshBuilder,
    BottomFaceMeshBuilder
)


class STLWriter:
    """STL文件生成器（使用trimesh生成空心字壳模型）"""

    def __init__(self, wall_thickness: float = 1.2):
        """
        初始化STL生成器

        Args:
            wall_thickness: 壁厚（mm），用于计算内外轮廓
        """
        self.wall_thickness = wall_thickness
        self.path_offset = PathOffset()

        # 初始化各网格生成器
        self.shell_builder = ShellMeshBuilder(self.path_offset, wall_thickness)
        self.edge_wrap_builder = EdgeWrapMeshBuilder(self.path_offset, wall_thickness)
        self.step_builder = StepMeshBuilder(self.path_offset)
        self.skirt_builder = SkirtMeshBuilder(self.path_offset)
        self.connected_builder = ConnectedMeshBuilder(self.path_offset)
        self.bottom_face_builder = BottomFaceMeshBuilder(self.path_offset)

    def write(self, result: SliceResult, output_path: str,
              binary: bool = True, contours: Optional[List[Contour]] = None,
              params: Optional[SliceParams] = None) -> None:
        """
        生成并写入STL文件

        Args:
            result: 切片结果
            output_path: 输出文件路径
            binary: 是否使用二进制格式（默认True，文件更小）
            contours: 原始轮廓列表（用于生成包边）
            params: 切片参数（用于获取包边设置）
        """
        meshes = []

        # 1. 构建字壳网格
        shell_mesh = self.shell_builder.build(result.layers)
        if shell_mesh is not None:
            meshes.append(shell_mesh)

        # 以下功能需要轮廓和参数
        if contours and params:
            # 2. 构建台阶网格
            step_mesh = self.step_builder.build(contours, result, params)
            if step_mesh is not None:
                meshes.append(step_mesh)

            # 3. 构建包边网格
            if params.edge_wrap.wrap_enabled:
                edge_wrap_mesh = self.edge_wrap_builder.build_wrap(
                    contours, result, params
                )
                if edge_wrap_mesh is not None:
                    meshes.append(edge_wrap_mesh)

            # 4. 构建勾边网格
            if params.edge_wrap.outline_enabled:
                outline_mesh = self.edge_wrap_builder.build_outline(
                    contours, result, params
                )
                if outline_mesh is not None:
                    meshes.append(outline_mesh)

            # 5. 构建防翘裙边网格
            if params.skirt.enabled:
                skirt_mesh = self.skirt_builder.build(contours, params)
                if skirt_mesh is not None:
                    meshes.append(skirt_mesh)

            # 6. 构建连襟网格
            if params.connected.enabled:
                connected_mesh = self.connected_builder.build(contours, params)
                if connected_mesh is not None:
                    meshes.append(connected_mesh)

            # 7. 构建底面封闭网格
            if params.bottom_face.enabled:
                bottom_face_mesh = self.bottom_face_builder.build(contours, params)
                if bottom_face_mesh is not None:
                    meshes.append(bottom_face_mesh)

        # 合并所有网格
        combined_mesh = MeshUtils.merge_meshes(meshes)

        if combined_mesh is None or len(combined_mesh.faces) == 0:
            raise ValueError("无法生成STL：没有有效的几何数据")

        # 写入文件
        if binary:
            combined_mesh.export(output_path, file_type='stl')
        else:
            combined_mesh.export(output_path, file_type='stl_ascii')


def write_stl(result: SliceResult, output_path: str,
              binary: bool = True, wall_thickness: float = 1.2) -> None:
    """
    便捷函数：生成并写入STL文件

    Args:
        result: 切片结果
        output_path: 输出文件路径
        binary: 是否使用二进制格式
        wall_thickness: 壁厚
    """
    writer = STLWriter(wall_thickness=wall_thickness)
    writer.write(result, output_path, binary)
