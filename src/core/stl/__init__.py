"""
STL生成子模块

将STL网格生成功能按职责拆分为多个模块：
- mesh_utils: 网格工具类（基础几何操作）
- shell_mesh: 字壳网格生成器
- edge_wrap_mesh: 包边/勾边网格生成器
- step_mesh: 台阶网格生成器
- skirt_mesh: 裙边网格生成器
- connected_mesh: 连襟网格生成器
- bottom_face_mesh: 底面封闭网格生成器
- top_face_mesh: 顶面封闭网格生成器
"""

from .mesh_utils import MeshUtils
from .shell_mesh import ShellMeshBuilder
from .edge_wrap_mesh import EdgeWrapMeshBuilder
from .step_mesh import StepMeshBuilder
from .skirt_mesh import SkirtMeshBuilder
from .connected_mesh import ConnectedMeshBuilder
from .bottom_face_mesh import BottomFaceMeshBuilder
from .top_face_mesh import TopFaceMeshBuilder

__all__ = [
    'MeshUtils',
    'ShellMeshBuilder',
    'EdgeWrapMeshBuilder',
    'StepMeshBuilder',
    'SkirtMeshBuilder',
    'ConnectedMeshBuilder',
    'BottomFaceMeshBuilder',
    'TopFaceMeshBuilder',
]
