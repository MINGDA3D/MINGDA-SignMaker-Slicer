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
    QPushButton, QFrame, QSizePolicy
)
from PySide6.QtGui import QMouseEvent, QWheelEvent

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

        # 打印平台尺寸 (mm)
        self.bed_width: float = 400.0
        self.bed_depth: float = 400.0
        self.bed_height: float = 500.0

        # 鼠标交互
        self._last_pos: QPoint = QPoint()
        self._mouse_button: Qt.MouseButton = Qt.MouseButton.NoButton

        # 显示选项
        self.show_grid: bool = True
        self.show_axes: bool = True
        self.show_platform: bool = True
        self.line_width: float = 1.5

        # 设置焦点策略以接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 设置最小尺寸
        self.setMinimumSize(400, 300)

    def set_layers(self, layers: List[Layer]):
        """设置切片层数据"""
        self.layers = layers
        self.current_layer = len(layers) - 1 if layers else 0
        self.update()

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

        # 计算观察距离
        view_distance = max(self.bed_width, self.bed_depth) * 1.5 / self.zoom

        # 设置相机位置
        gluLookAt(
            0, -view_distance, view_distance * 0.5,  # 相机位置
            0, 0, 0,                                  # 观察点
            0, 0, 1                                   # 上方向
        )

        # 应用平移
        glTranslatef(self.pan_x, self.pan_y, 0)

        # 应用旋转
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_z, 0, 0, 1)

        # 绘制场景
        if self.show_platform:
            self._draw_platform()

        if self.show_grid:
            self._draw_grid()

        if self.show_axes:
            self._draw_axes()

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
        far = 5000.0

        gluPerspective(fov, aspect, near, far)

    def _draw_platform(self):
        """绘制打印平台"""
        hw = self.bed_width / 2
        hd = self.bed_depth / 2

        # 平台边框
        glColor4f(0.3, 0.4, 0.5, 1.0)
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        glVertex3f(-hw, -hd, 0)
        glVertex3f(hw, -hd, 0)
        glVertex3f(hw, hd, 0)
        glVertex3f(-hw, hd, 0)
        glEnd()

        # 平台表面（半透明）
        glColor4f(0.15, 0.2, 0.25, 0.3)
        glBegin(GL_QUADS)
        glVertex3f(-hw, -hd, 0)
        glVertex3f(hw, -hd, 0)
        glVertex3f(hw, hd, 0)
        glVertex3f(-hw, hd, 0)
        glEnd()

        glLineWidth(self.line_width)

    def _draw_grid(self):
        """绘制网格"""
        hw = self.bed_width / 2
        hd = self.bed_depth / 2
        grid_spacing = 20.0  # 20mm 网格

        glColor4f(0.2, 0.25, 0.3, 0.5)
        glLineWidth(1.0)
        glBegin(GL_LINES)

        # X方向线
        y = -hd
        while y <= hd:
            glVertex3f(-hw, y, 0)
            glVertex3f(hw, y, 0)
            y += grid_spacing

        # Y方向线
        x = -hw
        while x <= hw:
            glVertex3f(x, -hd, 0)
            glVertex3f(x, hd, 0)
            x += grid_spacing

        glEnd()
        glLineWidth(self.line_width)

    def _draw_axes(self):
        """绘制坐标轴"""
        axis_length = 50.0

        glLineWidth(2.0)
        glBegin(GL_LINES)

        # X轴 - 红色
        glColor4f(1.0, 0.2, 0.2, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(axis_length, 0, 0)

        # Y轴 - 绿色
        glColor4f(0.2, 1.0, 0.2, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, axis_length, 0)

        # Z轴 - 蓝色
        glColor4f(0.2, 0.2, 1.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, axis_length)

        glEnd()
        glLineWidth(self.line_width)

    def _draw_layers(self):
        """绘制切片层"""
        if not self.layers:
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

        # 3D预览组件
        self.gl_widget = Preview3DWidget(self)
        self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.gl_widget, 1)

        # 底部控制栏
        control_bar = self._create_control_bar()
        layout.addWidget(control_bar)

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
                padding: 4px 8px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #30363D;
                border-color: #58A6FF;
            }
            QPushButton:pressed {
                background-color: #0D1117;
            }
            QLabel {
                color: #8B949E;
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
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # 视角预设按钮
        view_label = QLabel("视角:")
        layout.addWidget(view_label)

        for name, preset in [("俯视", "top"), ("正视", "front"), ("侧视", "right"), ("等轴", "iso")]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, p=preset: self.gl_widget.set_view_preset(p))
            layout.addWidget(btn)

        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.gl_widget.reset_view)
        layout.addWidget(reset_btn)

        layout.addStretch()

        # 层数控制
        self.layer_label = QLabel("层: 0/0")
        layout.addWidget(self.layer_label)

        self.layer_slider = QSlider(Qt.Orientation.Horizontal)
        self.layer_slider.setMinimum(0)
        self.layer_slider.setMaximum(0)
        self.layer_slider.setMinimumWidth(200)
        self.layer_slider.valueChanged.connect(self._on_layer_changed)
        layout.addWidget(self.layer_slider)

        # 显示模式切换
        self.show_all_btn = QPushButton("显示全部")
        self.show_all_btn.setCheckable(True)
        self.show_all_btn.setChecked(True)
        self.show_all_btn.clicked.connect(self._toggle_show_all)
        layout.addWidget(self.show_all_btn)

        return bar

    def _on_layer_changed(self, value: int):
        """层数滑块变化"""
        self.gl_widget.set_current_layer(value)
        total = len(self.gl_widget.layers)
        self.layer_label.setText(f"层: {value + 1}/{total}")

    def _toggle_show_all(self, checked: bool):
        """切换显示模式"""
        self.gl_widget.show_all_layers = checked
        self.show_all_btn.setText("显示全部" if checked else "单层显示")
        self.gl_widget.update()

    def set_layers(self, layers: List[Layer]):
        """设置切片层数据"""
        self.gl_widget.set_layers(layers)

        # 更新滑块范围
        total = len(layers)
        self.layer_slider.setMaximum(max(0, total - 1))
        self.layer_slider.setValue(max(0, total - 1))
        self.layer_label.setText(f"层: {total}/{total}")

    def set_bed_size(self, width: float, depth: float, height: float):
        """设置打印平台尺寸"""
        self.gl_widget.set_bed_size(width, depth, height)
