"""
异形边预设图片选择器

使用图片网格替代下拉框，提供更直观的预设选择体验。
直接绘制DXF轮廓线条，显示更清晰。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QScrollArea, QFrame,
    QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QSize, QCoreApplication
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QPainterPath

from src.core.edge_presets import EdgePresetManager


class PresetThumbnail(QFrame):
    """预设缩略图按钮"""

    clicked = Signal(str)  # preset_name

    def __init__(self, preset_info: dict, profile=None, parent=None):
        super().__init__(parent)
        self.preset_name = preset_info["name"]
        self.preset_info = preset_info
        self.profile = profile  # EdgeProfile对象
        self._selected = False

        self.setFixedSize(80, 100)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()
        self._update_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # 图片标签
        self.image_label = QLabel()
        self.image_label.setFixedSize(72, 92)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)

        # 绘制轮廓
        self._draw_profile()

        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        # 设置tooltip显示名称
        display_name = QCoreApplication.translate(
            "EdgePresets", self.preset_info['display_name'])
        description = QCoreApplication.translate(
            "EdgePresets", self.preset_info['description'])
        self.setToolTip(
            f"{display_name}\n"
            f"{description}\n"
            f"{self.tr('Width')}: {self.preset_info['default_width']:.1f}mm"
        )

    def _draw_profile(self):
        """绘制轮廓线条"""
        pixmap = QPixmap(72, 92)
        pixmap.fill(QColor("#1E2430"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置画笔 - 红色轮廓
        pen = QPen(QColor("#FF4444"), 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        if self.profile and self.profile.control_points:
            # 使用控制点绘制
            points = self.profile.control_points
            self._draw_points(painter, points, 72, 92)
        else:
            # 回退：绘制简单斜线
            painter.drawLine(20, 85, 52, 7)

        painter.end()
        self.image_label.setPixmap(pixmap)

    def _draw_points(self, painter: QPainter, points: list, width: int, height: int):
        """根据控制点绘制轮廓，保持正确的宽高比"""
        if not points:
            return

        # 计算边距
        margin = 6
        draw_width = width - 2 * margin
        draw_height = height - 2 * margin

        # 获取原始宽高比（从profile中获取）
        # 控制点已归一化到0-1，需要用original_width/height恢复比例
        orig_width = self.profile.original_width if self.profile else 1.0
        orig_height = self.profile.original_height if self.profile else 1.0

        # 计算真实的宽高比
        aspect_ratio = orig_height / orig_width if orig_width > 0 else 1.0

        # 根据宽高比计算实际绘制尺寸
        # 异形边通常是竖直的（高度远大于宽度）
        if aspect_ratio > draw_height / draw_width:
            # 高度受限，按高度缩放
            actual_height = draw_height
            actual_width = draw_height / aspect_ratio
        else:
            # 宽度受限，按宽度缩放
            actual_width = draw_width
            actual_height = draw_width * aspect_ratio

        # 计算居中偏移
        offset_x = margin + (draw_width - actual_width) / 2
        offset_y = margin + (draw_height - actual_height) / 2

        # 映射点到画布（控制点已归一化到0-1）
        def map_point(p):
            # p[0] 是归一化的x（0-1），p[1] 是归一化的y（0-1）
            px = offset_x + p[0] * actual_width
            # Y轴翻转（Qt的Y轴向下，但我们的Y是从下往上）
            py = offset_y + (1 - p[1]) * actual_height
            return px, py

        # 创建路径
        path = QPainterPath()
        first = map_point(points[0])
        path.moveTo(first[0], first[1])

        for p in points[1:]:
            mp = map_point(p)
            path.lineTo(mp[0], mp[1])

        painter.drawPath(path)

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                PresetThumbnail {
                    background-color: #1E3A5F;
                    border: 2px solid #58A6FF;
                    border-radius: 6px;
                }
                PresetThumbnail:hover {
                    background-color: #254670;
                }
            """)
        else:
            self.setStyleSheet("""
                PresetThumbnail {
                    background-color: #1E2430;
                    border: 1px solid #30363D;
                    border-radius: 6px;
                }
                PresetThumbnail:hover {
                    background-color: #252D38;
                    border: 1px solid #58A6FF;
                }
            """)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.preset_name)
        super().mousePressEvent(event)


class EdgePresetSelector(QWidget):
    """异形边预设选择器（图片网格）"""

    preset_selected = Signal(str)  # preset_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preset_manager = EdgePresetManager()
        self._thumbnails: dict[str, PresetThumbnail] = {}
        self._current_preset = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        # 内容容器
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(6)

        # 收集所有预设（不分类）
        all_presets = self._preset_manager.get_preset_list()

        # 图片网格（每行2个）
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        for i, preset in enumerate(all_presets):
            # 获取EdgeProfile以获取控制点
            profile = self._preset_manager.get_preset_profile(preset["name"])
            thumb = PresetThumbnail(preset, profile)
            thumb.clicked.connect(self._on_thumbnail_clicked)
            grid.addWidget(thumb, i // 2, i % 2)
            self._thumbnails[preset["name"]] = thumb

        content_layout.addWidget(grid_widget)
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # 默认选中第一个
        if self._thumbnails:
            first_name = next(iter(self._thumbnails.keys()))
            self.select_preset(first_name)

    def _on_thumbnail_clicked(self, preset_name: str):
        self.select_preset(preset_name)
        self.preset_selected.emit(preset_name)

    def select_preset(self, preset_name: str):
        """选中指定预设"""
        # 取消之前的选中
        if self._current_preset and self._current_preset in self._thumbnails:
            self._thumbnails[self._current_preset].set_selected(False)

        # 选中新的
        if preset_name in self._thumbnails:
            self._thumbnails[preset_name].set_selected(True)
            self._current_preset = preset_name

    def get_selected_preset(self) -> str:
        """获取当前选中的预设名称"""
        return self._current_preset or ""

    def sizeHint(self):
        return QSize(220, 300)
