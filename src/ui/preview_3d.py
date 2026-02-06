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
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel,
    QPushButton, QFrame, QSizePolicy, QCheckBox
)
from PySide6.QtGui import QMouseEvent, QWheelEvent, QPainter, QPen, QColor

try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from OpenGL.GL import *
    from OpenGL.GLU import *
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    QOpenGLWidget = QWidget  # Fallback

from src.core.types import Layer, LayerPath, PathRole, ExtruderType


# 颜色定义（根据挤出机类型）
EXTRUDER_COLORS = {
    ExtruderType.EXTRUDER_1: (0.231, 0.510, 0.965, 1.0),  # 蓝色 #3B82F6
    ExtruderType.EXTRUDER_2: (0.925, 0.282, 0.600, 1.0),  # 粉色 #EC4899
    ExtruderType.EXTRUDER_3: (0.961, 0.620, 0.043, 1.0),  # 橙色 #F59E0B
}

# 路径角色颜色
ROLE_COLORS = {
    PathRole.WALL: (0.231, 0.510, 0.965, 1.0),           # 蓝色
    PathRole.SAFETY_LINE: (0.5, 0.5, 0.5, 0.8),          # 灰色
    PathRole.SKIRT: (0.0, 0.8, 0.4, 0.9),                # 绿色
    PathRole.STEP: (0.8, 0.6, 0.2, 1.0),                 # 棕色
    PathRole.V_GROOVE: (0.8, 0.4, 0.2, 1.0),             # 深棕色
    PathRole.FILL_PANEL: (0.4, 0.6, 0.9, 0.6),           # 浅蓝色半透明
    PathRole.FILL_GRID: (0.4, 0.9, 0.6, 0.6),            # 浅绿色半透明
    PathRole.FILL_BASEPLATE: (0.6, 0.6, 0.6, 0.6),       # 灰色半透明
    PathRole.EDGE_WRAP: (0.9, 0.4, 0.4, 1.0),            # 红色
    PathRole.OUTLINE: (0.9, 0.9, 0.2, 1.0),              # 黄色
    PathRole.CONNECTED: (0.0, 0.9, 0.9, 1.0),            # 青色
}


class Preview3DWidget(QOpenGLWidget):
    """3D预览 OpenGL 组件"""

    layer_changed = Signal(int)  # 当前显示层变化

    def __init__(self, parent=None):
        super().__init__(parent)

        # 切片数据
        self.layers: List[Layer] = []
        self.current_layer: int = 0
        self.show_all_layers: bool = True  # 显示所有层还是只显示当前层

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
        self.current_layer = len(layers) - 1 if layers else 0
        # 计算模型边界框用于居中显示
        self._calculate_bounds()
        self.update()

    def _calculate_bounds(self):
        """计算模型边界框"""
        if not self.layers:
            self.model_center = (0, 0, 0)
            self.model_size = 100
            return

        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

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

    def set_bed_size(self, width: float, depth: float, height: float):
        """设置打印平台尺寸"""
        self.bed_width = width
        self.bed_depth = depth
        self.bed_height = height
        self.update()

    def reset_view(self):
        """重置视图到默认位置"""
        self.rotation_x = 30.0
        self.rotation_z = 45.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.update()

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

        # 计算观察距离和中心点
        # 使用打印平台中心作为观察点，而不是模型中心
        platform_center_x = self.bed_width / 2
        platform_center_y = self.bed_depth / 2
        platform_center_z = self.bed_height / 2

        # 观察距离基于平台尺寸
        platform_diagonal = math.sqrt(self.bed_width**2 + self.bed_depth**2 + self.bed_height**2)
        view_distance = platform_diagonal * 1.5 / self.zoom

        cx, cy, cz = platform_center_x, platform_center_y, platform_center_z

        # 设置相机位置（使用简化的视角计算）
        # 将角度转换为弧度
        pitch = math.radians(self.rotation_x)
        yaw = math.radians(self.rotation_z)

        # 计算相机位置（球坐标系）
        cam_x = cx + view_distance * math.cos(pitch) * math.sin(yaw)
        cam_y = cy - view_distance * math.cos(pitch) * math.cos(yaw)
        cam_z = cz + view_distance * math.sin(pitch)

        gluLookAt(
            cam_x, cam_y, cam_z,  # 相机位置
            cx, cy, cz,           # 观察点（模型中心）
            0, 0, 1               # 上方向
        )

        # 应用平移
        glTranslatef(self.pan_x, self.pan_y, 0)

        # 绘制场景 - 平台从原点开始，不居中
        if self.show_platform:
            self._draw_platform()

        if self.show_grid:
            self._draw_grid()

        if self.show_axes:
            # 坐标轴在原点显示
            self._draw_axes_at(0, 0, 0)

        # 绘制切片层
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
        fov = 45.0
        near = 1.0
        far = 50000.0  # 增大远裁剪面以适应大坐标

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

        glLineWidth(self.line_width)

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

                # 获取颜色
                color = self._get_path_color(path, alpha_mult)
                glColor4f(*color)

                # 绘制路径
                if path.is_closed:
                    glBegin(GL_LINE_LOOP)
                else:
                    glBegin(GL_LINE_STRIP)

                for point in path.points:
                    glVertex3f(point.x, point.y, z)

                glEnd()

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
            self.zoom = max(0.1, min(10.0, self.zoom))
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
        self.zoom = max(0.1, min(10.0, self.zoom))
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
        top_toolbar = self._create_top_toolbar()
        layout.addWidget(top_toolbar)

        # 3D预览组件（直接占满中间区域）
        self.gl_widget = Preview3DWidget(self)
        self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.gl_widget, 1)

        # 底部控制栏
        control_bar = self._create_control_bar()
        layout.addWidget(control_bar)

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

        self.layer_current_label = QLabel("1")
        self.layer_current_label.setStyleSheet("color: #58A6FF; font-size: 16px; font-weight: bold;")
        layer_info_layout.addWidget(self.layer_current_label)

        self.layer_total_label = QLabel("24.7%")
        self.layer_total_label.setStyleSheet("color: #8B949E; font-size: 10px;")
        layer_info_layout.addWidget(self.layer_total_label)

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
        total = len(self.gl_widget.layers)

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
        self.layer_slider.setMaximum(max(0, total - 1))
        self.layer_slider.setValue(max(0, total - 1))

        # 更新层数显示
        self.layer_current_label.setText(str(total))
        if total > 0:
            self.layer_total_label.setText("100.0%")
        else:
            self.layer_total_label.setText("0.0%")

    def set_bed_size(self, width: float, depth: float, height: float):
        """设置打印平台尺寸"""
        self.gl_widget.set_bed_size(width, depth, height)
