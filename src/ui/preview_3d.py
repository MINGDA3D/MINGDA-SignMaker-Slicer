"""
3D预览组件

使用 PyOpenGL 渲染切片结果的3D预览，支持：
- 分层显示切片路径
- 鼠标交互（旋转/缩放/平移）
- 打印平台网格
- 坐标轴指示器
- 层数滑块控制
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel,
    QPushButton, QFrame, QSizePolicy, QCheckBox
)
from PySide6.QtGui import QMouseEvent, QWheelEvent, QPainter, QPen, QColor
from .busy_dialog import SpinnerWidget

try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from OpenGL.GL import *
    from OpenGL.GLU import *
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    QOpenGLWidget = QWidget  # Fallback

from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl import (
    ShellMeshBuilder,
    StepMeshBuilder,
    SkirtMeshBuilder,
    PrimeTowerMeshBuilder,
    ConnectedMeshBuilder,
    EdgeWrapMeshBuilder,
    BottomFaceMeshBuilder,
    LightSlotMeshBuilder,
    TopFaceMeshBuilder,
)
from src.core.types import (
    Contour,
    Layer,
    LayerPath,
    PathRole,
    Point,
    ExtruderType,
    SliceParams,
    SliceResult,
    BedExcludeAreaInput,
    parse_bed_exclude_area,
    normalize_slice_params,
    is_bottom_face_effective,
    resolve_u_shape_profile_start_z,
)


# 颜色定义（根据挤出机类型）
EXTRUDER_COLORS = {
    ExtruderType.EXTRUDER_1: (0.231, 0.510, 0.965, 1.0),  # 蓝色 #3B82F6
    ExtruderType.EXTRUDER_2: (0.925, 0.282, 0.600, 1.0),  # 粉色 #EC4899
    ExtruderType.EXTRUDER_3: (0.961, 0.620, 0.043, 1.0),  # 橙色 #F59E0B
}

WALL_COLOR = (0.357, 0.702, 0.980, 1.0)                  # 统一墙体蓝
STEP_COLOR = (1.000, 0.471, 0.180, 0.98)                 # 台阶亮橙
V_GROOVE_COLOR = (1.000, 0.320, 0.120, 0.98)             # V槽偏红橙
CONNECTED_COLOR = (0.100, 0.960, 0.960, 1.0)             # 连字亮青
SKIRT_COLOR = (1.000, 0.671, 0.122, 0.95)                # 裙边亮琥珀
LIGHT_SLOT_COLOR = (0.969, 0.741, 0.247, 0.98)           # 灯槽暖金

PRIME_TOWER_COLOR = (0.149, 0.737, 0.612, 0.98)

WALL_LIKE_ROLES = {
    PathRole.WALL,
    PathRole.FILL_PANEL,
    PathRole.FILL_GRID,
    PathRole.FILL_BASEPLATE,
    PathRole.FILL_BOTTOM_FACE,
    PathRole.FILL_TOP_FACE,
}

# 路径角色颜色
ROLE_COLORS = {
    PathRole.WALL: WALL_COLOR,
    PathRole.PRIME_TOWER: PRIME_TOWER_COLOR,
    PathRole.SAFETY_LINE: (0.650, 0.710, 0.780, 0.75),   # 冷灰
    PathRole.SKIRT: SKIRT_COLOR,
    PathRole.STEP: STEP_COLOR,
    PathRole.V_GROOVE: V_GROOVE_COLOR,
    PathRole.FILL_PANEL: WALL_COLOR,
    PathRole.FILL_GRID: WALL_COLOR,
    PathRole.FILL_BASEPLATE: WALL_COLOR,
    PathRole.FILL_BOTTOM_FACE: WALL_COLOR,
    PathRole.LIGHT_SLOT: LIGHT_SLOT_COLOR,
    PathRole.FILL_TOP_FACE: WALL_COLOR,
    PathRole.EDGE_WRAP: WALL_COLOR,
    PathRole.OUTLINE: WALL_COLOR,
    PathRole.CONNECTED: CONNECTED_COLOR,
}

RIBBON_ROLES = {
    PathRole.PRIME_TOWER,
    PathRole.SKIRT,
    PathRole.STEP,
    PathRole.V_GROOVE,
    PathRole.CONNECTED,
}

ROLE_Z_LIFTS = {
    PathRole.WALL: 0.020,
    PathRole.PRIME_TOWER: 0.035,
    PathRole.SAFETY_LINE: 0.025,
    PathRole.FILL_PANEL: 0.030,
    PathRole.FILL_GRID: 0.030,
    PathRole.FILL_BASEPLATE: 0.030,
    PathRole.FILL_BOTTOM_FACE: 0.030,
    PathRole.LIGHT_SLOT: 0.045,
    PathRole.FILL_TOP_FACE: 0.030,
    PathRole.STEP: 0.055,
    PathRole.V_GROOVE: 0.060,
    PathRole.CONNECTED: 0.075,
    PathRole.SKIRT: 0.080,
    PathRole.EDGE_WRAP: 0.040,
    PathRole.OUTLINE: 0.040,
}


@dataclass
class PreviewMeshPart:
    """Prepared mesh part for OpenGL preview rendering."""
    name: str
    color: Tuple[float, float, float, float]
    vertices: np.ndarray
    vertex_normals: np.ndarray
    faces: np.ndarray
    face_min_z: np.ndarray
    face_max_z: np.ndarray
    sorted_face_min_z: np.ndarray
    sorted_face_indices_flat: np.ndarray
    all_face_indices_flat: np.ndarray


class Preview3DWidget(QOpenGLWidget):
    """3D预览 OpenGL 组件"""

    layer_changed = Signal(int)  # 当前显示层变化
    DEFAULT_FOV = 45.0
    MIN_ZOOM = 0.1
    MAX_ZOOM = 50.0

    def __init__(self, parent=None):
        super().__init__(parent)

        # 切片数据
        self.layers: List[Layer] = []
        self.current_layer: int = 0
        self.show_all_layers: bool = True  # 显示所有层还是只显示当前层
        self.mesh_parts: List[PreviewMeshPart] = []
        self._mesh_cache_key: Optional[Tuple[int, int, int]] = None

        # 视图参数
        self.rotation_x: float = 30.0   # X轴旋转（俯仰）
        self.rotation_z: float = 45.0   # Z轴旋转（偏航）
        self.zoom: float = 1.0
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0

        # 打印平台尺寸 (mm) - 发光字专用
        self.bed_width: float = 800.0   # X方向
        self.bed_depth: float = 1200.0  # Y方向
        self.bed_height: float = 100.0  # Z方向最大高度

        # 模型边界信息
        self.unprintable_polygons: List[List[Point]] = []
        self.model_center: Tuple[float, float, float] = (0, 0, 0)
        self.model_size: float = 100.0

        # 鼠标交互
        self._last_pos: QPoint = QPoint()
        self._mouse_button: Qt.MouseButton = Qt.MouseButton.NoButton

        # 显示选项
        self.show_grid: bool = True
        self.show_axes: bool = True
        self.show_platform: bool = True
        self.line_width: float = 2.0  # 增加线宽便于查看

        # 设置焦点策略以接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 设置最小尺寸
        self.setMinimumSize(400, 300)

    def set_layers(self, layers: List[Layer]):
        """设置切片层数据"""
        self.layers = layers
        self.mesh_parts = []
        self._mesh_cache_key = None
        self.current_layer = len(layers) - 1 if layers else 0
        # 计算模型边界框用于居中显示
        self._calculate_bounds()
        self._clamp_zoom_in_place()
        self.update()

    def clear_scene(self):
        """Clear preview content while keeping the widget ready for async loading."""
        self.layers = []
        self.mesh_parts = []
        self._mesh_cache_key = None
        self.current_layer = 0
        self._calculate_bounds()
        self._clamp_zoom_in_place()
        self.update()

    def set_slice_result(
        self,
        result: SliceResult,
        contours: Optional[List[Contour]] = None,
        params: Optional[SliceParams] = None,
    ):
        """Set sliced layers and, when possible, build solid preview meshes."""
        self.layers = result.layers if result else []
        self.current_layer = len(self.layers) - 1 if self.layers else 0
        cache_key = self._get_mesh_cache_key(result, contours, params)
        if self._mesh_cache_key != cache_key:
            self.mesh_parts = self.build_mesh_parts_for_result(result, contours, params)
            self._mesh_cache_key = cache_key
        self._calculate_bounds()
        self._clamp_zoom_in_place()
        self.update()

    def set_prebuilt_mesh_parts(
        self,
        result: SliceResult,
        mesh_parts: List[PreviewMeshPart],
        contours: Optional[List[Contour]] = None,
        params: Optional[SliceParams] = None,
    ):
        """Apply mesh parts built off the UI thread."""
        self.layers = result.layers if result else []
        self.current_layer = len(self.layers) - 1 if self.layers else 0
        self.mesh_parts = mesh_parts
        self._mesh_cache_key = self._get_mesh_cache_key(result, contours, params)
        self._calculate_bounds()
        self._clamp_zoom_in_place()
        self.update()

    def has_cached_mesh_parts(
        self,
        result: Optional[SliceResult],
        contours: Optional[List[Contour]],
        params: Optional[SliceParams],
    ) -> bool:
        """Return whether the solid preview for this scene is already cached."""
        return self._mesh_cache_key == self._get_mesh_cache_key(result, contours, params)

    @staticmethod
    def _get_mesh_cache_key(
        result: Optional[SliceResult],
        contours: Optional[List[Contour]],
        params: Optional[SliceParams],
    ) -> Tuple[int, Tuple[int, ...], int]:
        """Build a stable cache key for solid preview meshes."""
        contour_ids = tuple(id(contour) for contour in contours) if contours else ()
        return (id(result), contour_ids, id(params))

    @staticmethod
    def build_mesh_parts_for_result(
        result: Optional[SliceResult],
        contours: Optional[List[Contour]],
        params: Optional[SliceParams],
    ) -> List[PreviewMeshPart]:
        """Build solid component meshes for wall/step/connected/skirt preview."""
        if result is None or not result.layers or not contours or params is None:
            return []

        params = normalize_slice_params(params)
        path_offset = PathOffset()
        wall_thickness = params.shell.wall_thickness
        shell_builder = ShellMeshBuilder(path_offset, wall_thickness)
        step_builder = StepMeshBuilder(path_offset)
        skirt_builder = SkirtMeshBuilder(path_offset)
        prime_tower_builder = PrimeTowerMeshBuilder()
        connected_builder = ConnectedMeshBuilder(path_offset)
        edge_wrap_builder = EdgeWrapMeshBuilder(path_offset, wall_thickness)
        bottom_face_builder = BottomFaceMeshBuilder(path_offset)
        light_slot_builder = LightSlotMeshBuilder(path_offset)
        top_face_builder = TopFaceMeshBuilder(path_offset)
        temp_engine = SliceEngine()

        parts: List[PreviewMeshPart] = []

        shell_mesh = shell_builder.build(result.layers)
        Preview3DWidget._append_mesh_part(parts, "wall", shell_mesh, WALL_COLOR)

        if params.prime_tower.enabled:
            prime_tower_mesh = prime_tower_builder.build(result.layers)
            Preview3DWidget._append_mesh_part(parts, "prime_tower", prime_tower_mesh, PRIME_TOWER_COLOR)

        top_contours = Preview3DWidget._get_transformed_contours_at_z(
            contours, params.shell.height, temp_engine, params
        )
        bottom_contours = Preview3DWidget._get_transformed_contours_at_z(
            contours, 0.0, temp_engine, params
        )
        source_bottom_contours = bottom_contours if bottom_contours else contours

        panel_contours: List[Contour] = []
        baseplate_contours: List[Contour] = []
        u_flat_height = resolve_u_shape_profile_start_z(params.shell)
        if params.step.panel_step_enabled or params.step.baseplate_step_enabled:
            panel_z = params.step.panel_step_height
            baseplate_z = params.step.baseplate_step_height
            for contour in contours:
                if params.step.panel_step_enabled:
                    panel_contour = temp_engine._apply_edge_profile(
                        contour,
                        panel_z,
                        params.shell,
                        u_flat_height=u_flat_height,
                    )
                    if panel_contour is not None:
                        panel_contours.append(panel_contour)
                if params.step.baseplate_step_enabled:
                    baseplate_contour = temp_engine._apply_edge_profile(
                        contour,
                        baseplate_z,
                        params.shell,
                        u_flat_height=u_flat_height,
                    )
                    if baseplate_contour is not None:
                        baseplate_contours.append(baseplate_contour)

        if params.step.panel_step_enabled or params.step.baseplate_step_enabled:
            step_mesh = step_builder.build(
                contours,
                result,
                params,
                panel_contours=panel_contours,
                baseplate_contours=baseplate_contours,
            )
            Preview3DWidget._append_mesh_part(parts, "step", step_mesh, STEP_COLOR)

        if params.skirt.enabled:
            skirt_mesh = skirt_builder.build(
                source_bottom_contours,
                params,
                source_contours=source_bottom_contours,
            )
            Preview3DWidget._append_mesh_part(parts, "skirt", skirt_mesh, SKIRT_COLOR)

        if params.connected.enabled:
            connected_mesh = connected_builder.build(contours, params)
            Preview3DWidget._append_mesh_part(parts, "connected", connected_mesh, CONNECTED_COLOR)

        if is_bottom_face_effective(params):
            bottom_face_mesh = bottom_face_builder.build(source_bottom_contours, params)
            Preview3DWidget._append_mesh_part(parts, "bottom_face", bottom_face_mesh, WALL_COLOR)

        if params.light_slot.enabled:
            light_slot_mesh = light_slot_builder.build(source_bottom_contours, params)
            Preview3DWidget._append_mesh_part(parts, "light_slot", light_slot_mesh, LIGHT_SLOT_COLOR)

        if params.top_face.enabled:
            top_face_mesh = top_face_builder.build(top_contours if top_contours else contours, params)
            Preview3DWidget._append_mesh_part(parts, "top_face", top_face_mesh, WALL_COLOR)

        if params.edge_wrap.wrap_enabled:
            wrap_mesh = edge_wrap_builder.build_wrap(
                source_bottom_contours,
                result,
                params,
            )
            Preview3DWidget._append_mesh_part(parts, "wrap", wrap_mesh, WALL_COLOR)

        if params.edge_wrap.outline_enabled:
            outline_mesh = edge_wrap_builder.build_outline(
                source_bottom_contours,
                result,
                params,
            )
            Preview3DWidget._append_mesh_part(parts, "outline", outline_mesh, WALL_COLOR)

        return parts

    @staticmethod
    def _append_mesh_part(
        parts: List[PreviewMeshPart],
        name: str,
        mesh,
        color: Tuple[float, float, float, float],
    ):
        """Convert trimesh geometry into OpenGL-ready arrays."""
        if mesh is None or getattr(mesh, "faces", None) is None or len(mesh.faces) == 0:
            return

        vertices = np.ascontiguousarray(np.asarray(mesh.vertices, dtype=np.float32))
        vertex_normals = np.ascontiguousarray(np.asarray(mesh.vertex_normals, dtype=np.float32))
        faces = np.ascontiguousarray(np.asarray(mesh.faces, dtype=np.uint32))
        face_vertices_z = vertices[faces][:, :, 2]
        sort_order = np.argsort(face_vertices_z.min(axis=1), kind="stable")

        parts.append(
            PreviewMeshPart(
                name=name,
                color=color,
                vertices=vertices,
                vertex_normals=vertex_normals,
                faces=faces,
                face_min_z=face_vertices_z.min(axis=1),
                face_max_z=face_vertices_z.max(axis=1),
                sorted_face_min_z=np.ascontiguousarray(face_vertices_z.min(axis=1)[sort_order]),
                sorted_face_indices_flat=np.ascontiguousarray(faces[sort_order].reshape(-1)),
                all_face_indices_flat=np.ascontiguousarray(faces.reshape(-1)),
            )
        )

    @staticmethod
    def _get_transformed_contours_at_z(
        contours: List[Contour],
        z: float,
        temp_engine: SliceEngine,
        params: SliceParams,
    ) -> List[Contour]:
        """Apply edge transforms at a target height to match STL mesh logic."""
        transformed_contours: List[Contour] = []
        u_flat_height = resolve_u_shape_profile_start_z(params.shell)
        for contour in contours:
            transformed = temp_engine._apply_edge_profile(
                contour,
                z,
                params.shell,
                u_flat_height=u_flat_height,
            )
            if transformed is not None:
                transformed_contours.append(transformed)
        return transformed_contours

    def _calculate_bounds(self):
        """计算模型边界框"""
        if not self.layers and not self.mesh_parts:
            self.model_center = (0, 0, 0)
            self.model_size = 100
            return

        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

        for part in self.mesh_parts:
            if part.vertices.size == 0:
                continue
            min_x = min(min_x, float(np.min(part.vertices[:, 0])))
            max_x = max(max_x, float(np.max(part.vertices[:, 0])))
            min_y = min(min_y, float(np.min(part.vertices[:, 1])))
            max_y = max(max_y, float(np.max(part.vertices[:, 1])))
            min_z = min(min_z, float(np.min(part.vertices[:, 2])))
            max_z = max(max_z, float(np.max(part.vertices[:, 2])))

        for layer in self.layers:
            z = layer.z_height
            min_z = min(min_z, z)
            max_z = max(max_z, z + layer.layer_height)

            for path in layer.paths:
                for point in path.points:
                    min_x = min(min_x, point.x)
                    max_x = max(max_x, point.x)
                    min_y = min(min_y, point.y)
                    max_y = max(max_y, point.y)

        if min_x == float('inf'):
            self.model_center = (0, 0, 0)
            self.model_size = 100
            return

        self.model_center = (
            (min_x + max_x) / 2,
            (min_y + max_y) / 2,
            (min_z + max_z) / 2
        )
        self.model_size = max(max_x - min_x, max_y - min_y, max_z - min_z, 1)

    def set_current_layer(self, layer_index: int):
        """设置当前显示层"""
        if 0 <= layer_index < len(self.layers):
            self.current_layer = layer_index
            self.layer_changed.emit(layer_index)
            self.update()

    def set_bed_size(
        self,
        width: float,
        depth: float,
        height: float,
        bed_exclude_area: BedExcludeAreaInput = None,
    ):
        """设置打印平台尺寸"""
        self.bed_width = width
        self.bed_depth = depth
        self.bed_height = height
        self.unprintable_polygons = parse_bed_exclude_area(bed_exclude_area)
        self._clamp_zoom_in_place()
        self.update()

    def set_unprintable_regions(self, bed_exclude_area: BedExcludeAreaInput):
        self.unprintable_polygons = parse_bed_exclude_area(bed_exclude_area)
        self.update()

    def reset_view(self):
        """重置视图到默认位置"""
        self.rotation_x = 30.0
        self.rotation_z = 45.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._clamp_zoom_in_place()
        self.update()

    def _get_focus_center(self) -> Tuple[float, float, float]:
        """获取当前相机焦点。存在模型时优先对准模型，而不是平台中心。"""
        if self.layers:
            return self.model_center
        return (self.bed_width / 2, self.bed_depth / 2, self.bed_height / 2)

    def _get_focus_radius(self) -> float:
        """获取焦点附近需要保持可见的安全半径。"""
        if not self.layers:
            return 50.0
        return max(self.model_size * 0.75, 10.0)

    def _get_scene_radius(self, focus_center: Tuple[float, float, float]) -> float:
        """估算从焦点到整个平台和模型的最大距离，用于投影和默认观察距离。"""
        fx, fy, fz = focus_center
        corners = (
            (0.0, 0.0, 0.0),
            (self.bed_width, 0.0, 0.0),
            (0.0, self.bed_depth, 0.0),
            (self.bed_width, self.bed_depth, 0.0),
            (0.0, 0.0, self.bed_height),
            (self.bed_width, 0.0, self.bed_height),
            (0.0, self.bed_depth, self.bed_height),
            (self.bed_width, self.bed_depth, self.bed_height),
        )

        platform_radius = max(
            math.sqrt((x - fx) ** 2 + (y - fy) ** 2 + (z - fz) ** 2)
            for x, y, z in corners
        )
        return max(platform_radius, self._get_focus_radius())

    def _get_base_view_distance(self) -> float:
        """根据当前场景尺寸计算默认观察距离。"""
        scene_radius = self._get_scene_radius(self._get_focus_center())
        half_fov = math.radians(self.DEFAULT_FOV / 2.0)
        return max(100.0, scene_radius / math.tan(half_fov) * 1.15)

    def _get_zoom_limits(self) -> Tuple[float, float]:
        """根据模型尺寸给缩放设置动态上限，避免相机贴到空场景后只剩黑屏。"""
        base_distance = self._get_base_view_distance()
        focus_radius = self._get_focus_radius()
        half_fov = math.radians(self.DEFAULT_FOV / 2.0)
        min_view_distance = max(10.0, focus_radius * 0.35 / math.tan(half_fov))
        max_zoom = max(1.0, min(self.MAX_ZOOM, base_distance / min_view_distance))
        return (self.MIN_ZOOM, max_zoom)

    def _clamp_zoom_value(self, zoom: float) -> float:
        min_zoom, max_zoom = self._get_zoom_limits()
        return max(min_zoom, min(max_zoom, zoom))

    def _clamp_zoom_in_place(self):
        self.zoom = self._clamp_zoom_value(self.zoom)

    def _get_camera_distance(self) -> float:
        """获取应用缩放限制后的观察距离。"""
        self._clamp_zoom_in_place()
        return self._get_base_view_distance() / self.zoom

    def _get_camera_up_vector(
        self,
        camera_pos: Tuple[float, float, float],
        focus_center: Tuple[float, float, float],
    ) -> Tuple[float, float, float]:
        """为 gluLookAt 计算稳定的 up 向量，避免顶视/底视时和视线共线。"""
        cam_x, cam_y, cam_z = camera_pos
        cx, cy, cz = focus_center

        forward_x = cx - cam_x
        forward_y = cy - cam_y
        forward_z = cz - cam_z
        forward_len = math.sqrt(forward_x ** 2 + forward_y ** 2 + forward_z ** 2)
        if forward_len <= 1e-9:
            return (0.0, 1.0, 0.0)

        forward_x /= forward_len
        forward_y /= forward_len
        forward_z /= forward_len

        ref_up = (0.0, 0.0, 1.0)
        if abs(forward_z) > 0.98:
            ref_up = (0.0, 1.0, 0.0)

        side_x = forward_y * ref_up[2] - forward_z * ref_up[1]
        side_y = forward_z * ref_up[0] - forward_x * ref_up[2]
        side_z = forward_x * ref_up[1] - forward_y * ref_up[0]
        side_len = math.sqrt(side_x ** 2 + side_y ** 2 + side_z ** 2)
        if side_len <= 1e-9:
            return (0.0, 1.0, 0.0)

        side_x /= side_len
        side_y /= side_len
        side_z /= side_len

        up_x = side_y * forward_z - side_z * forward_y
        up_y = side_z * forward_x - side_x * forward_z
        up_z = side_x * forward_y - side_y * forward_x
        return (up_x, up_y, up_z)

    def set_view_preset(self, preset: str):
        """设置预设视角"""
        presets = {
            "front": (0, 0),      # 正视图
            "back": (0, 180),     # 后视图
            "left": (0, -90),     # 左视图
            "right": (0, 90),     # 右视图
            "top": (90, 0),       # 俯视图
            "bottom": (-90, 0),   # 仰视图
            "iso": (30, 45),      # 等轴测
        }
        if preset in presets:
            self.rotation_x, self.rotation_z = presets[preset]
            self.update()

    # =========================================================================
    # OpenGL 渲染
    # =========================================================================

    def initializeGL(self):
        """初始化 OpenGL 上下文"""
        if not OPENGL_AVAILABLE:
            return

        # 设置背景色（深蓝色）
        glClearColor(0.051, 0.067, 0.090, 1.0)  # #0D1117

        # 启用深度测试
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_NORMALIZE)

        # 启用线条平滑
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

        # 启用混合（用于透明度）
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # 设置线宽
        glLineWidth(self.line_width)

    def resizeGL(self, width: int, height: int):
        """调整 OpenGL 视口"""
        if not OPENGL_AVAILABLE:
            return

        glViewport(0, 0, width, height)
        self._setup_projection()

    def paintGL(self):
        """渲染场景"""
        if not OPENGL_AVAILABLE:
            return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # 设置投影矩阵
        self._setup_projection()

        # 设置模型视图矩阵
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # 计算观察距离和焦点
        cx, cy, cz = self._get_focus_center()
        view_distance = self._get_camera_distance()

        # 设置相机位置（使用简化的视角计算）
        # 将角度转换为弧度
        pitch = math.radians(self.rotation_x)
        yaw = math.radians(self.rotation_z)

        # 计算相机位置（球坐标系）
        cam_x = cx + view_distance * math.cos(pitch) * math.sin(yaw)
        cam_y = cy - view_distance * math.cos(pitch) * math.cos(yaw)
        cam_z = cz + view_distance * math.sin(pitch)
        up_x, up_y, up_z = self._get_camera_up_vector((cam_x, cam_y, cam_z), (cx, cy, cz))

        gluLookAt(
            cam_x, cam_y, cam_z,  # 相机位置
            cx, cy, cz,           # 观察点（模型中心）
            up_x, up_y, up_z      # 上方向
        )

        # 应用平移
        glTranslatef(self.pan_x, self.pan_y, 0)

        # 绘制场景 - 平台从原点开始，不居中
        if self.show_platform:
            glDisable(GL_LIGHTING)
            self._draw_platform()

        if self.show_grid:
            glDisable(GL_LIGHTING)
            self._draw_grid()

        if self.show_axes:
            # 坐标轴在原点显示
            glDisable(GL_LIGHTING)
            self._draw_axes_at(0, 0, 0)

        if self.mesh_parts:
            self._configure_lighting(cam_x, cam_y, cam_z, cx, cy, cz)
            self._draw_mesh_parts()
            glDisable(GL_LIGHTING)
        else:
            # 绘制切片层
            glDisable(GL_LIGHTING)
            self._draw_layers()

    def _setup_projection(self):
        """设置投影矩阵"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        width = self.width()
        height = self.height()
        if height == 0:
            height = 1

        aspect = width / height
        fov = self.DEFAULT_FOV
        view_distance = self._get_camera_distance()
        scene_radius = self._get_scene_radius(self._get_focus_center())

        # 近远裁剪面跟随相机距离，避免近距离放大时深度精度过差或整屏被裁掉。
        near = max(0.5, view_distance * 0.02)
        far = max(near + 100.0, view_distance + scene_radius * 2.5)

        gluPerspective(fov, aspect, near, far)

    def _draw_platform(self):
        """绘制打印平台（从原点开始，不居中）"""
        w = self.bed_width
        d = self.bed_depth
        h = self.bed_height

        # 1. 绘制完整的3D打印区域边框（绿色立方体框架）
        glColor4f(0.3, 0.8, 0.3, 0.8)  # 绿色
        glLineWidth(2.0)

        # 底面四条边
        glBegin(GL_LINE_LOOP)
        glVertex3f(0, 0, 0)
        glVertex3f(w, 0, 0)
        glVertex3f(w, d, 0)
        glVertex3f(0, d, 0)
        glEnd()

        # 顶面四条边
        glBegin(GL_LINE_LOOP)
        glVertex3f(0, 0, h)
        glVertex3f(w, 0, h)
        glVertex3f(w, d, h)
        glVertex3f(0, d, h)
        glEnd()

        # 四条竖边
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, h)

        glVertex3f(w, 0, 0)
        glVertex3f(w, 0, h)

        glVertex3f(w, d, 0)
        glVertex3f(w, d, h)

        glVertex3f(0, d, 0)
        glVertex3f(0, d, h)
        glEnd()

        # 2. 平台表面（深色半透明）
        glColor4f(0.1, 0.12, 0.15, 0.2)
        glBegin(GL_QUADS)
        glVertex3f(0, 0, 0)
        glVertex3f(w, 0, 0)
        glVertex3f(w, d, 0)
        glVertex3f(0, d, 0)
        glEnd()

        self._draw_unprintable_regions()
        glLineWidth(self.line_width)

    def _draw_unprintable_regions(self):
        """Draw bed-exclude regions as translucent red polygons on the platform."""
        if not self.unprintable_polygons:
            return

        z = 0.05
        glColor4f(1.0, 0.32, 0.32, 0.32)
        for polygon in self.unprintable_polygons:
            if len(polygon) < 3:
                continue
            glBegin(GL_POLYGON)
            for point in polygon:
                glVertex3f(point.x, point.y, z)
            glEnd()

        glColor4f(1.0, 0.42, 0.42, 0.85)
        glLineWidth(1.2)
        for polygon in self.unprintable_polygons:
            if len(polygon) < 3:
                continue
            glBegin(GL_LINE_LOOP)
            for point in polygon:
                glVertex3f(point.x, point.y, z + 0.02)
            glEnd()

    def _draw_grid(self):
        """绘制网格（从原点开始，20mm间距）"""
        w = self.bed_width
        d = self.bed_depth
        grid_spacing = 20.0  # 20mm 网格间距

        glColor4f(0.2, 0.25, 0.3, 0.4)
        glLineWidth(1.0)
        glBegin(GL_LINES)

        # Y方向线（平行于Y轴）
        x = 0.0
        while x <= w:
            glVertex3f(x, 0, 0)
            glVertex3f(x, d, 0)
            x += grid_spacing

        # X方向线（平行于X轴）
        y = 0.0
        while y <= d:
            glVertex3f(0, y, 0)
            glVertex3f(w, y, 0)
            y += grid_spacing

        glEnd()
        glLineWidth(self.line_width)

    def _draw_axes_at(self, cx: float, cy: float, cz: float):
        """绘制坐标轴（在指定位置）"""
        # 坐标轴长度固定为100mm，便于识别
        axis_length = 100.0

        glLineWidth(3.0)
        glBegin(GL_LINES)

        # X轴 - 红色
        glColor4f(1.0, 0.3, 0.3, 1.0)
        glVertex3f(cx, cy, cz)
        glVertex3f(cx + axis_length, cy, cz)

        # Y轴 - 绿色
        glColor4f(0.3, 1.0, 0.3, 1.0)
        glVertex3f(cx, cy, cz)
        glVertex3f(cx, cy + axis_length, cz)

        # Z轴 - 蓝色
        glColor4f(0.3, 0.3, 1.0, 1.0)
        glVertex3f(cx, cy, cz)
        glVertex3f(cx, cy, cz + axis_length)

        glEnd()
        glLineWidth(self.line_width)

    def _configure_lighting(
        self,
        cam_x: float,
        cam_y: float,
        cam_z: float,
        cx: float,
        cy: float,
        cz: float,
    ):
        """Configure basic directional lighting for solid mesh preview."""
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glShadeModel(GL_SMOOTH)

        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.28, 0.30, 0.34, 1.0))

        key_light_pos = (cam_x + 180.0, cam_y - 220.0, cam_z + 260.0, 1.0)
        fill_light_pos = (cx - 260.0, cy + 180.0, cz + 220.0, 1.0)

        glLightfv(GL_LIGHT0, GL_POSITION, key_light_pos)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.92, 0.92, 0.92, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (0.12, 0.12, 0.12, 1.0))

        glLightfv(GL_LIGHT1, GL_POSITION, fill_light_pos)
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.45, 0.48, 0.52, 1.0))
        glLightfv(GL_LIGHT1, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))

    def _get_mesh_clip_range(self) -> Tuple[float, float]:
        """Translate the layer slider into a visible Z range for solid meshes."""
        if not self.layers:
            return (0.0, float("inf"))

        current = self.layers[self.current_layer]
        layer_bottom = current.z_height
        layer_top = current.z_height + current.layer_height

        if self.show_all_layers:
            return (0.0, layer_top)
        return (layer_bottom, layer_top)

    def _draw_mesh_parts(self):
        """Render real 3D meshes for shell, steps, connected letters and skirt."""
        if not self.mesh_parts:
            return

        clip_bottom, clip_top = self._get_mesh_clip_range()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        try:
            for part in self.mesh_parts:
                if self.show_all_layers:
                    face_count = np.searchsorted(
                        part.sorted_face_min_z,
                        clip_top + 1e-6,
                        side="right",
                    )
                    if face_count <= 0:
                        continue
                    if face_count >= len(part.faces):
                        indices = part.all_face_indices_flat
                    else:
                        indices = part.sorted_face_indices_flat[:face_count * 3]
                else:
                    visible_mask = (
                        (part.face_max_z >= clip_bottom - 1e-6) &
                        (part.face_min_z <= clip_top + 1e-6)
                    )
                    if not np.any(visible_mask):
                        continue
                    indices = np.ascontiguousarray(part.faces[visible_mask].reshape(-1))

                glColor4f(*part.color)
                glVertexPointer(3, GL_FLOAT, 0, part.vertices)
                glNormalPointer(GL_FLOAT, 0, part.vertex_normals)
                glDrawElements(GL_TRIANGLES, int(indices.size), GL_UNSIGNED_INT, indices)
        finally:
            glDisableClientState(GL_NORMAL_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)

    def _should_draw_ribbon(self, path: LayerPath) -> bool:
        """Render wider special structures as flat bands so they stay visible."""
        return path.role in RIBBON_ROLES and path.line_width > 0.0

    def _get_render_z(self, layer_z: float, layer_height: float, path: LayerPath) -> float:
        """Lift paths slightly above the platform/layer plane to avoid z-fighting."""
        max_lift = max(layer_height * 0.45, 0.02)
        return layer_z + min(ROLE_Z_LIFTS.get(path.role, 0.03), max_lift)

    def _get_outline_width(self, path: LayerPath) -> float:
        """Scale outline width from real path width while keeping walls readable."""
        return max(1.6, min(6.0, 1.25 + path.line_width * 0.30))

    def _get_fill_color(self, path: LayerPath, alpha_mult: float) -> Tuple[float, float, float, float]:
        """Use a softer fill below the crisp outline for emphasis roles."""
        r, g, b, a = self._get_path_color(path, alpha_mult)
        return (r, g, b, min(0.70, max(0.22, a * 0.45)))

    def _draw_path_outline(self, path: LayerPath, z: float):
        """Draw the centerline outline for a path."""
        if path.is_closed:
            glBegin(GL_LINE_LOOP)
        else:
            glBegin(GL_LINE_STRIP)

        for point in path.points:
            glVertex3f(point.x, point.y, z)

        glEnd()

    def _draw_path_ribbon(self, path: LayerPath, z: float):
        """Approximate wide paths with XY-plane quads so inner steps remain visible."""
        if len(path.points) < 2:
            return

        half_width = max(path.line_width * 0.5, 0.2)
        segment_count = len(path.points) if path.is_closed else len(path.points) - 1

        glBegin(GL_QUADS)
        for i in range(segment_count):
            p1 = path.points[i]
            p2 = path.points[(i + 1) % len(path.points)] if path.is_closed else path.points[i + 1]

            dx = p2.x - p1.x
            dy = p2.y - p1.y
            length = math.sqrt(dx * dx + dy * dy)
            if length <= 1e-9:
                continue

            nx = -dy / length * half_width
            ny = dx / length * half_width

            glVertex3f(p1.x + nx, p1.y + ny, z)
            glVertex3f(p1.x - nx, p1.y - ny, z)
            glVertex3f(p2.x - nx, p2.y - ny, z)
            glVertex3f(p2.x + nx, p2.y + ny, z)
        glEnd()

    def _draw_layers(self):
        """绘制切片层"""
        if not self.layers:
            # 没有切片数据时不绘制任何东西
            return

        # 确定要绘制的层范围
        if self.show_all_layers:
            start_layer = 0
            end_layer = self.current_layer + 1
        else:
            start_layer = self.current_layer
            end_layer = self.current_layer + 1

        glLineWidth(self.line_width)

        for layer_idx in range(start_layer, min(end_layer, len(self.layers))):
            layer = self.layers[layer_idx]
            z = layer.z_height

            # 当前层高亮显示
            alpha_mult = 1.0 if layer_idx == self.current_layer else 0.6

            for path in layer.paths:
                if not path.points:
                    continue

                render_z = self._get_render_z(z, layer.layer_height, path)

                if self._should_draw_ribbon(path):
                    glColor4f(*self._get_fill_color(path, alpha_mult))
                    self._draw_path_ribbon(path, render_z)

                glColor4f(*self._get_path_color(path, alpha_mult))
                glLineWidth(self._get_outline_width(path))
                self._draw_path_outline(path, render_z)

        glLineWidth(self.line_width)

    def _draw_test_cube(self):
        """绘制测试立方体（当没有切片数据时）"""
        size = 50.0

        glColor4f(0.5, 0.8, 0.5, 1.0)
        glLineWidth(2.0)

        # 底面
        glBegin(GL_LINE_LOOP)
        glVertex3f(-size, -size, 0)
        glVertex3f(size, -size, 0)
        glVertex3f(size, size, 0)
        glVertex3f(-size, size, 0)
        glEnd()

        # 顶面
        glBegin(GL_LINE_LOOP)
        glVertex3f(-size, -size, size)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, size)
        glEnd()

        # 竖边
        glBegin(GL_LINES)
        glVertex3f(-size, -size, 0)
        glVertex3f(-size, -size, size)
        glVertex3f(size, -size, 0)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, 0)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, 0)
        glVertex3f(-size, size, size)
        glEnd()

    def _get_path_color(self, path: LayerPath, alpha_mult: float = 1.0) -> Tuple[float, float, float, float]:
        """获取路径颜色"""
        # 优先使用角色颜色
        if path.role in ROLE_COLORS:
            r, g, b, a = ROLE_COLORS[path.role]
            return (r, g, b, a * alpha_mult)

        # 其次使用挤出机颜色
        if path.extruder in EXTRUDER_COLORS:
            r, g, b, a = EXTRUDER_COLORS[path.extruder]
            return (r, g, b, a * alpha_mult)

        # 默认颜色
        return (0.5, 0.5, 0.5, alpha_mult)

    # =========================================================================
    # 鼠标交互
    # =========================================================================

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        self._last_pos = event.position().toPoint()
        self._mouse_button = event.button()

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        pos = event.position().toPoint()
        dx = pos.x() - self._last_pos.x()
        dy = pos.y() - self._last_pos.y()

        if self._mouse_button == Qt.MouseButton.LeftButton:
            # 左键拖拽：旋转
            self.rotation_z += dx * 0.5
            self.rotation_x += dy * 0.5
            # 限制俯仰角度
            self.rotation_x = max(-90, min(90, self.rotation_x))
            self.update()

        elif self._mouse_button == Qt.MouseButton.MiddleButton:
            # 中键拖拽：平移
            scale = max(self.bed_width, self.bed_depth) / self.width() / self.zoom
            self.pan_x += dx * scale
            self.pan_y -= dy * scale
            self.update()

        elif self._mouse_button == Qt.MouseButton.RightButton:
            # 右键拖拽：缩放
            self.zoom *= 1.0 + dy * 0.005
            self._clamp_zoom_in_place()
            self.update()

        self._last_pos = pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        self._mouse_button = Qt.MouseButton.NoButton

    def wheelEvent(self, event: QWheelEvent):
        """鼠标滚轮：缩放"""
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        self.zoom *= factor
        self._clamp_zoom_in_place()
        self.update()


class Preview3D(QWidget):
    """3D预览面板（包含OpenGL视图和控制器）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部工具栏（显示选项）
        # Temporarily disable the non-functional top preview toolbar.

        # 3D预览组件（直接占满中间区域）
        self.gl_widget = Preview3DWidget(self)
        self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.gl_widget, 1)

        self._loading_overlay = QFrame(self)
        self._loading_overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(13, 17, 23, 210);
                border: 1px solid #30363D;
                border-radius: 12px;
            }
            QLabel {
                color: #C9D1D9;
                font-size: 13px;
            }
        """)
        overlay_layout = QVBoxLayout(self._loading_overlay)
        overlay_layout.setContentsMargins(20, 18, 20, 18)
        overlay_layout.setSpacing(12)
        self._loading_spinner = SpinnerWidget(36, self._loading_overlay)
        overlay_layout.addWidget(self._loading_spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        self._loading_label = QLabel(self.tr("Loading 3D preview..."))
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(self._loading_label)
        self._loading_overlay.hide()
        self._loading_overlay.raise_()

        # 底部控制栏
        control_bar = self._create_control_bar()
        layout.addWidget(control_bar)

    def resizeEvent(self, event):
        """Keep the loading overlay centered above the preview area."""
        super().resizeEvent(event)
        width = 240
        height = 120
        x = max(0, (self.width() - width) // 2)
        y = max(0, (self.height() - height) // 2)
        self._loading_overlay.setGeometry(x, y, width, height)
        self._loading_overlay.raise_()

    def set_loading(self, loading: bool, message: Optional[str] = None):
        """Show or hide a non-blocking loading indicator on top of the preview."""
        if message:
            self._loading_label.setText(message)

        if loading:
            self._loading_overlay.show()
            self._loading_overlay.raise_()
            self._loading_spinner.show()
        else:
            self._loading_overlay.hide()

    def _create_top_toolbar(self) -> QFrame:
        """创建顶部工具栏（显示选项）"""
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border-bottom: 1px solid #30363D;
            }
            QCheckBox {
                color: #C9D1D9;
                padding: 6px 12px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #30363D;
                border-radius: 3px;
                background-color: #0D1117;
            }
            QCheckBox::indicator:checked {
                background-color: #58A6FF;
                border-color: #58A6FF;
            }
            QCheckBox::indicator:hover {
                border-color: #58A6FF;
            }
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # 显示选项复选框
        self.cb_outer_wall = QCheckBox(self.tr("外壳"))
        self.cb_outer_wall.setChecked(True)
        self.cb_outer_wall.toggled.connect(self._on_display_option_changed)
        layout.addWidget(self.cb_outer_wall)

        self.cb_inner_wall = QCheckBox(self.tr("内壳"))
        self.cb_inner_wall.setChecked(True)
        self.cb_inner_wall.toggled.connect(self._on_display_option_changed)
        layout.addWidget(self.cb_inner_wall)

        self.cb_fill = QCheckBox(self.tr("填充"))
        self.cb_fill.setChecked(True)
        self.cb_fill.toggled.connect(self._on_display_option_changed)
        layout.addWidget(self.cb_fill)

        self.cb_solid = QCheckBox(self.tr("实边"))
        self.cb_solid.setChecked(True)
        self.cb_solid.toggled.connect(self._on_display_option_changed)
        layout.addWidget(self.cb_solid)

        self.cb_color_change = QCheckBox(self.tr("换色"))
        self.cb_color_change.setChecked(True)
        self.cb_color_change.toggled.connect(self._on_display_option_changed)
        layout.addWidget(self.cb_color_change)

        self.cb_bottom = QCheckBox(self.tr("底面"))
        self.cb_bottom.setChecked(True)
        self.cb_bottom.toggled.connect(self._on_display_option_changed)
        layout.addWidget(self.cb_bottom)

        self.cb_top = QCheckBox(self.tr("顶面"))
        self.cb_top.setChecked(True)
        self.cb_top.toggled.connect(self._on_display_option_changed)
        layout.addWidget(self.cb_top)

        layout.addStretch()

        # 右侧工具按钮
        search_btn = QPushButton(self.tr("图层编辑"))
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #30363D;
                border-color: #58A6FF;
            }
        """)
        layout.addWidget(search_btn)

        filter_btn = QPushButton(self.tr("层数编辑"))
        filter_btn.setStyleSheet(search_btn.styleSheet())
        layout.addWidget(filter_btn)

        return toolbar

    def _on_display_option_changed(self):
        """显示选项变化时的处理"""
        # TODO: 根据复选框状态过滤显示的路径类型
        self.gl_widget.update()

    def _create_control_bar(self) -> QFrame:
        """创建底部控制栏"""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border-top: 1px solid #30363D;
            }
            QPushButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 48px;
                min-height: 32px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #30363D;
                border-color: #58A6FF;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #0D1117;
                border-color: #58A6FF;
            }
            QLabel {
                color: #8B949E;
                font-size: 12px;
            }
            QSlider::groove:horizontal {
                background: #21262D;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #58A6FF;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #58A6FF;
                border-radius: 3px;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 左侧：视角切换按钮（正、俯、侧、透）
        self.btn_front = QPushButton(self.tr("正"))
        self.btn_front.setCheckable(True)
        self.btn_front.clicked.connect(lambda: self._set_view_and_highlight("front"))
        layout.addWidget(self.btn_front)

        self.btn_top = QPushButton(self.tr("俯"))
        self.btn_top.setCheckable(True)
        self.btn_top.clicked.connect(lambda: self._set_view_and_highlight("top"))
        layout.addWidget(self.btn_top)

        self.btn_side = QPushButton(self.tr("侧"))
        self.btn_side.setCheckable(True)
        self.btn_side.clicked.connect(lambda: self._set_view_and_highlight("right"))
        layout.addWidget(self.btn_side)

        self.btn_iso = QPushButton(self.tr("透"))
        self.btn_iso.setCheckable(True)
        self.btn_iso.setChecked(True)  # 默认等轴测视图
        self.btn_iso.clicked.connect(lambda: self._set_view_and_highlight("iso"))
        layout.addWidget(self.btn_iso)

        # 存储视图按钮以便管理选中状态
        self.view_buttons = [self.btn_front, self.btn_top, self.btn_side, self.btn_iso]

        layout.addSpacing(20)

        # 中间：坐标和速度显示
        self.coord_label = QLabel("X: 342.652    Y: 521.196    Z: 26.700")
        self.coord_label.setStyleSheet("color: #C9D1D9; font-family: Consolas;")
        layout.addWidget(self.coord_label)

        layout.addSpacing(20)

        self.speed_label = QLabel("Speed:    50")
        self.speed_label.setStyleSheet("color: #8B949E; font-family: Consolas;")
        layout.addWidget(self.speed_label)

        layout.addStretch()

        # 右侧：层数控制
        self.layer_slider = QSlider(Qt.Orientation.Horizontal)
        self.layer_slider.setMinimum(0)
        self.layer_slider.setMaximum(0)
        self.layer_slider.setMinimumWidth(150)
        self.layer_slider.valueChanged.connect(self._on_layer_changed)
        layout.addWidget(self.layer_slider)

        # 层数显示（使用渐变色）
        layer_info_widget = QWidget()
        layer_info_layout = QVBoxLayout(layer_info_widget)
        layer_info_layout.setContentsMargins(8, 0, 0, 0)
        layer_info_layout.setSpacing(2)

        self.layer_current_label = QLabel("Z --")
        self.layer_current_label.setStyleSheet("color: #58A6FF; font-size: 16px; font-weight: bold;")
        layer_info_layout.addWidget(self.layer_current_label)

        self.layer_total_label = QLabel("")
        self.layer_total_label.setStyleSheet("color: #8B949E; font-size: 10px;")
        layer_info_layout.addWidget(self.layer_total_label)
        self._layer_count_hint = 0

        layout.addWidget(layer_info_widget)

        return bar

    def _set_view_and_highlight(self, preset: str):
        """设置视图并高亮对应按钮"""
        # 取消所有按钮的选中���态
        for btn in self.view_buttons:
            btn.setChecked(False)

        # 设置当前按钮为选中
        if preset == "front":
            self.btn_front.setChecked(True)
        elif preset == "top":
            self.btn_top.setChecked(True)
        elif preset == "right":
            self.btn_side.setChecked(True)
        elif preset == "iso":
            self.btn_iso.setChecked(True)

        # 设置视图
        self.gl_widget.set_view_preset(preset)

    def _on_layer_changed(self, value: int):
        """层数滑块变化"""
        self.gl_widget.set_current_layer(value)
        total = len(self.gl_widget.layers) or self._layer_count_hint
        self._update_layer_info(total, value)
        return

        # 更新层数显示
        self.layer_current_label.setText(str(value + 1))

        # 计算百分比
        if total > 0:
            percentage = ((value + 1) / total) * 100
            self.layer_total_label.setText(f"{percentage:.1f}%")
        else:
            self.layer_total_label.setText("0.0%")

    def set_layers(self, layers: List[Layer]):
        """设置切片层数据"""
        self.gl_widget.set_layers(layers)

        # 更新滑块范围
        total = len(layers)
        self._sync_layer_controls(total, total - 1)
        return
        self.layer_slider.setMaximum(max(0, total - 1))
        self.layer_slider.setValue(max(0, total - 1))

        # 更新层数显示
        self.layer_current_label.setText(str(total))
        if total > 0:
            self.layer_total_label.setText("100.0%")
        else:
            self.layer_total_label.setText("0.0%")

    def clear_scene(self):
        """Clear current preview content before async loading a new scene."""
        self.gl_widget.clear_scene()
        self.set_layer_count(0)

    def set_layer_count(self, total: int, layers: Optional[List[Layer]] = None):
        """Update layer controls without forcing synchronous scene processing."""
        if layers is not None:
            self.gl_widget.set_layers(layers)
            total = len(layers)
        self._sync_layer_controls(total, total - 1)
        return
        self.layer_slider.setMaximum(max(0, total - 1))
        self.layer_slider.setValue(max(0, total - 1))
        self.layer_current_label.setText(str(total))
        self.layer_total_label.setText("100.0%" if total > 0 else "0.0%")

    def set_slice_result(
        self,
        result: SliceResult,
        contours: Optional[List[Contour]] = None,
        params: Optional[SliceParams] = None,
    ):
        """Set sliced data and optional solid meshes for the 3D preview."""
        self.gl_widget.set_slice_result(result, contours, params)

        total = len(self.gl_widget.layers)
        self._sync_layer_controls(total, total - 1)
        return
        self.layer_slider.setMaximum(max(0, total - 1))
        self.layer_slider.setValue(max(0, total - 1))

        self.layer_current_label.setText(str(total))
        if total > 0:
            self.layer_total_label.setText("100.0%")
        else:
            self.layer_total_label.setText("0.0%")

    def set_prebuilt_mesh_parts(
        self,
        result: SliceResult,
        mesh_parts: List[PreviewMeshPart],
        contours: Optional[List[Contour]] = None,
        params: Optional[SliceParams] = None,
    ):
        """Apply mesh parts prepared in a worker thread."""
        self.gl_widget.set_prebuilt_mesh_parts(result, mesh_parts, contours, params)

        total = len(self.gl_widget.layers)
        self._sync_layer_controls(total, total - 1)
        return
        self.layer_slider.setMaximum(max(0, total - 1))
        self.layer_slider.setValue(max(0, total - 1))

        self.layer_current_label.setText(str(total))
        if total > 0:
            self.layer_total_label.setText("100.0%")
        else:
            self.layer_total_label.setText("0.0%")

    def has_cached_mesh_parts(
        self,
        result: Optional[SliceResult],
        contours: Optional[List[Contour]],
        params: Optional[SliceParams],
    ) -> bool:
        """Return whether the current preview mesh cache matches the scene."""
        return self.gl_widget.has_cached_mesh_parts(result, contours, params)

    def set_bed_size(
        self,
        width: float,
        depth: float,
        height: float,
        bed_exclude_area: BedExcludeAreaInput = None,
    ):
        """设置打印平台尺寸"""
        self.gl_widget.set_bed_size(width, depth, height, bed_exclude_area)

    def set_unprintable_regions(self, bed_exclude_area: BedExcludeAreaInput):
        self.gl_widget.set_unprintable_regions(bed_exclude_area)

    def _update_layer_info(self, total: int, current_index: int):
        """Refresh current Z-height labels without exposing layer counts."""
        layers = self.gl_widget.layers
        if total > 0 and layers:
            current_index = max(0, min(current_index, total - 1))
            layer = layers[current_index]
            current_z = layer.z_height + layer.layer_height
            total_height = max(
                item.z_height + item.layer_height
                for item in layers
            )
            self.layer_current_label.setText(f"Z {current_z:.2f} mm")
            self.layer_total_label.setText(f"/ {total_height:.2f} mm")
        elif total > 0:
            self.layer_current_label.setText("Z --")
            self.layer_total_label.setText("")
        else:
            self.layer_current_label.setText("Z --")
            self.layer_total_label.setText("")

    def _sync_layer_controls(
        self,
        total: int,
        current_index: int,
        layers: Optional[List[Layer]] = None,
    ):
        """Synchronize slider state with the current layer summary."""
        if layers is not None:
            total = len(layers)

        current_index = max(0, min(current_index, total - 1)) if total > 0 else 0
        self._layer_count_hint = total

        self.layer_slider.blockSignals(True)
        try:
            self.layer_slider.setMaximum(max(0, total - 1))
            self.layer_slider.setValue(current_index)
        finally:
            self.layer_slider.blockSignals(False)

        self._update_layer_info(total, current_index)

    def _on_layer_changed(self, value: int):
        """å±‚æ•°æ»‘å—å˜åŒ–"""
        self.gl_widget.set_current_layer(value)
        total = len(self.gl_widget.layers) or self._layer_count_hint
        self._update_layer_info(total, value)

    def set_layers(self, layers: List[Layer]):
        """è®¾ç½®åˆ‡ç‰‡å±‚æ•°æ®"""
        self.gl_widget.set_layers(layers)
        total = len(layers)
        self._sync_layer_controls(total, total - 1)

    def set_layer_count(self, total: int, layers: Optional[List[Layer]] = None):
        """Update layer controls without forcing synchronous scene processing."""
        if layers is not None:
            self.gl_widget.set_layers(layers)
            total = len(layers)
        self._sync_layer_controls(total, total - 1)

    def set_slice_result(
        self,
        result: SliceResult,
        contours: Optional[List[Contour]] = None,
        params: Optional[SliceParams] = None,
    ):
        """Set sliced data and optional solid meshes for the 3D preview."""
        self.gl_widget.set_slice_result(result, contours, params)
        total = len(self.gl_widget.layers)
        self._sync_layer_controls(total, total - 1)

    def set_prebuilt_mesh_parts(
        self,
        result: SliceResult,
        mesh_parts: List[PreviewMeshPart],
        contours: Optional[List[Contour]] = None,
        params: Optional[SliceParams] = None,
    ):
        """Apply mesh parts prepared in a worker thread."""
        self.gl_widget.set_prebuilt_mesh_parts(result, mesh_parts, contours, params)
        total = len(self.gl_widget.layers)
        self._sync_layer_controls(total, total - 1)
