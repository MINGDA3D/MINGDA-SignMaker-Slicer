"""
SignMaker Slicer - 2D画布组件

用于显示和编辑2D轮廓的画布组件，支持：
- 轮廓渲染
- 平移和缩放
- 选择和变换
- 网格背景
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import math

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QWheelEvent, QMouseEvent, QKeyEvent, QTransform
)

from src.core.types import Point, Path, Contour, PathType
from .theme import COLORS


class Canvas2D(QWidget):
    """2D画布组件"""

    # 信号
    contour_selected = Signal(int)  # 轮廓选中信号
    mouse_moved = Signal(float, float)  # 鼠标移动信号
    zoom_changed = Signal(float)  # 缩放变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 视图状态
        self.view_offset = QPointF(0, 0)  # 视图偏移
        self.view_scale = 1.0  # 视图缩放
        self.view_mode = "2d"  # 视图模式

        # 数据
        self.contours: List[Contour] = []
        self.selected_indices: List[int] = []
        self.slice_result = None

        # 交互状态
        self.current_tool = "select"  # 当前工具
        self.is_panning = False  # 是否正在平移
        self.pan_start = QPointF()  # 平移起始点
        self.last_mouse_pos = QPointF()

        # 样式
        self.bg_color = QColor(COLORS.bg_primary)
        self.grid_color = QColor(COLORS.border_default)
        self.contour_color = QColor(COLORS.path_shell)
        self.hole_color = QColor(COLORS.accent_warning)
        self.selected_color = QColor(COLORS.accent_primary)
        self.start_point_color = QColor(COLORS.accent_success)

        # 设置
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_contours(self, contours: List[Contour]):
        """设置轮廓数据"""
        self.contours = contours
        self.selected_indices = []
        self.update()

    def set_view_mode(self, mode: str):
        """设置视图模式 (2d/3d)"""
        self.view_mode = mode
        self.update()

    def set_tool(self, tool: str):
        """设置当前工具"""
        self.current_tool = tool

    def fit_view(self):
        """适应视图"""
        if not self.contours:
            return

        # 计算所有轮廓的边界框
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for contour in self.contours:
            bounds = contour.outer.bounds
            min_x = min(min_x, bounds[0])
            min_y = min(min_y, bounds[1])
            max_x = max(max_x, bounds[2])
            max_y = max(max_y, bounds[3])

        if min_x == float('inf'):
            return

        # 计算缩放
        content_width = max_x - min_x
        content_height = max_y - min_y
        margin = 50

        scale_x = (self.width() - 2 * margin) / content_width if content_width > 0 else 1
        scale_y = (self.height() - 2 * margin) / content_height if content_height > 0 else 1
        self.view_scale = min(scale_x, scale_y)

        # 计算偏移（居中）
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.view_offset = QPointF(
            self.width() / 2 - center_x * self.view_scale,
            self.height() / 2 + center_y * self.view_scale  # Y轴翻转
        )

        self.zoom_changed.emit(self.view_scale * 100)
        self.update()

    def mirror_selected(self, axis: str):
        """镜像选中的轮廓"""
        # TODO: 实现镜像功能
        pass

    def boolean_intersection(self):
        """布尔交集"""
        # TODO: 实现布尔交集
        pass

    def boolean_difference(self):
        """布尔差集"""
        # TODO: 实现布尔差集
        pass

    def group_selected(self):
        """组合选中的轮廓"""
        # TODO: 实现组合功能
        pass

    def ungroup_selected(self):
        """打散选中的轮廓"""
        # TODO: 实现打散功能
        pass

    # =========================================================================
    # 绘制
    # =========================================================================

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景
        self._draw_background(painter)

        # 绘制网格
        self._draw_grid(painter)

        # 应用视图变换
        painter.save()
        painter.translate(self.view_offset)
        painter.scale(self.view_scale, -self.view_scale)  # Y轴翻转

        # 绘制轮廓
        self._draw_contours(painter)

        painter.restore()

        # 绘制UI元素（不受变换影响）
        self._draw_ui_overlay(painter)

    def _draw_background(self, painter: QPainter):
        """绘制背景"""
        painter.fillRect(self.rect(), self.bg_color)

    def _draw_grid(self, painter: QPainter):
        """绘制网格"""
        # 计算网格间距（根据缩放调整）
        base_spacing = 10  # mm
        spacing = base_spacing * self.view_scale

        # 确保网格间距在合理范围
        while spacing < 20:
            spacing *= 5
            base_spacing *= 5
        while spacing > 100:
            spacing /= 5
            base_spacing /= 5

        # 绘制次网格
        pen = QPen(self.grid_color)
        pen.setWidth(1)
        painter.setPen(pen)

        # 垂直线
        x_start = int(self.view_offset.x() % spacing)
        for x in range(int(x_start), self.width(), int(spacing)):
            painter.drawLine(x, 0, x, self.height())

        # 水平线
        y_start = int(self.view_offset.y() % spacing)
        for y in range(int(y_start), self.height(), int(spacing)):
            painter.drawLine(0, y, self.width(), y)

        # 绘制主网格（每5个单位）
        pen.setColor(QColor(COLORS.border_hover))
        painter.setPen(pen)

        major_spacing = spacing * 5
        x_start = int(self.view_offset.x() % major_spacing)
        for x in range(int(x_start), self.width(), int(major_spacing)):
            painter.drawLine(x, 0, x, self.height())

        y_start = int(self.view_offset.y() % major_spacing)
        for y in range(int(y_start), self.height(), int(major_spacing)):
            painter.drawLine(0, y, self.width(), y)

        # 绘制原点
        origin_x = int(self.view_offset.x())
        origin_y = int(self.view_offset.y())

        pen.setColor(QColor(COLORS.accent_primary))
        pen.setWidth(2)
        painter.setPen(pen)

        # X轴
        if 0 <= origin_y <= self.height():
            painter.drawLine(0, origin_y, self.width(), origin_y)

        # Y轴
        if 0 <= origin_x <= self.width():
            painter.drawLine(origin_x, 0, origin_x, self.height())

    def _draw_contours(self, painter: QPainter):
        """绘制轮廓"""
        for i, contour in enumerate(self.contours):
            is_selected = i in self.selected_indices

            # 绘制外轮廓
            self._draw_path(painter, contour.outer, is_selected, is_hole=False)

            # 绘制内孔
            for hole in contour.holes:
                self._draw_path(painter, hole, is_selected, is_hole=True)

            # 绘制起始点
            if contour.outer.points:
                start_idx = contour.start_point_index
                if 0 <= start_idx < len(contour.outer.points):
                    self._draw_start_point(painter, contour.outer.points[start_idx])

    def _draw_path(self, painter: QPainter, path: Path,
                   is_selected: bool, is_hole: bool):
        """绘制单个路径"""
        if not path.points:
            return

        # 构建QPainterPath
        qpath = QPainterPath()
        qpath.moveTo(path.points[0].x, path.points[0].y)

        for point in path.points[1:]:
            qpath.lineTo(point.x, point.y)

        if path.is_closed:
            qpath.closeSubpath()

        # 设置画笔
        if is_selected:
            pen = QPen(self.selected_color)
            pen.setWidthF(2 / self.view_scale)
        elif is_hole:
            pen = QPen(self.hole_color)
            pen.setWidthF(1.5 / self.view_scale)
        else:
            pen = QPen(self.contour_color)
            pen.setWidthF(1.5 / self.view_scale)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(qpath)

    def _draw_start_point(self, painter: QPainter, point: Point):
        """绘制起始点"""
        radius = 4 / self.view_scale
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.start_point_color))
        painter.drawEllipse(
            QPointF(point.x, point.y),
            radius, radius
        )

    def _draw_ui_overlay(self, painter: QPainter):
        """绘制UI覆盖层"""
        # 绘制比例尺
        self._draw_scale_bar(painter)

    def _draw_scale_bar(self, painter: QPainter):
        """绘制比例尺"""
        # 计算合适的比例尺长度
        target_length = 100  # 像素
        world_length = target_length / self.view_scale  # mm

        # 取整到合适的值
        nice_values = [1, 2, 5, 10, 20, 50, 100, 200, 500]
        for nice in nice_values:
            if nice >= world_length:
                world_length = nice
                break

        bar_length = world_length * self.view_scale

        # 绘制位置
        x = 20
        y = self.height() - 30

        # 绘制条
        pen = QPen(QColor(COLORS.text_secondary))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(int(x), int(y), int(x + bar_length), int(y))
        painter.drawLine(int(x), int(y - 5), int(x), int(y + 5))
        painter.drawLine(int(x + bar_length), int(y - 5), int(x + bar_length), int(y + 5))

        # 绘制标签
        painter.drawText(int(x + bar_length / 2 - 20), int(y - 10), f"{world_length} mm")

    # =========================================================================
    # 事件处理
    # =========================================================================

    def wheelEvent(self, event: QWheelEvent):
        """滚轮缩放"""
        # 获取鼠标位置
        mouse_pos = event.position()

        # 计算缩放因子
        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9

        # 限制缩放范围
        new_scale = self.view_scale * scale_factor
        if 0.01 < new_scale < 100:
            # 以鼠标位置为中心缩放
            old_world_pos = self._screen_to_world(mouse_pos)

            self.view_scale = new_scale

            new_screen_pos = self._world_to_screen(old_world_pos)
            self.view_offset += mouse_pos - new_screen_pos

            self.zoom_changed.emit(self.view_scale * 100)
            self.update()

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        self.last_mouse_pos = event.position()

        if event.button() == Qt.MouseButton.MiddleButton:
            # 中键平移
            self.is_panning = True
            self.pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool == "select":
                self._handle_selection(event.position())

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        pos = event.position()

        if self.is_panning:
            # 平移视图
            delta = pos - self.pan_start
            self.view_offset += delta
            self.pan_start = pos
            self.update()
        else:
            # 更新坐标显示
            world_pos = self._screen_to_world(pos)
            self.mouse_moved.emit(world_pos.x(), world_pos.y())

        self.last_mouse_pos = pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Delete:
            # 删除选中
            pass
        elif event.key() == Qt.Key.Key_Escape:
            # 取消选择
            self.selected_indices = []
            self.update()
        elif event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # 全选
            self.selected_indices = list(range(len(self.contours)))
            self.update()

    def _handle_selection(self, pos: QPointF):
        """处理选择"""
        world_pos = self._screen_to_world(pos)

        for i, contour in enumerate(self.contours):
            if self._point_in_contour(world_pos, contour):
                if Qt.KeyboardModifier.ControlModifier in QApplication.keyboardModifiers():
                    # Ctrl+点击：切换选择
                    if i in self.selected_indices:
                        self.selected_indices.remove(i)
                    else:
                        self.selected_indices.append(i)
                else:
                    # 普通点击：单选
                    self.selected_indices = [i]

                self.contour_selected.emit(i)
                self.update()
                return

        # 点击空白区域：取消选择
        if Qt.KeyboardModifier.ControlModifier not in QApplication.keyboardModifiers():
            self.selected_indices = []
            self.update()

    def _point_in_contour(self, pos: QPointF, contour: Contour) -> bool:
        """判断点是否在轮廓内"""
        # 简单的边界框检测
        bounds = contour.outer.bounds
        return (bounds[0] <= pos.x() <= bounds[2] and
                bounds[1] <= pos.y() <= bounds[3])

    def _screen_to_world(self, screen_pos: QPointF) -> QPointF:
        """屏幕坐标转世界坐标"""
        x = (screen_pos.x() - self.view_offset.x()) / self.view_scale
        y = -(screen_pos.y() - self.view_offset.y()) / self.view_scale  # Y轴翻转
        return QPointF(x, y)

    def _world_to_screen(self, world_pos: QPointF) -> QPointF:
        """世界坐标转屏幕坐标"""
        x = world_pos.x() * self.view_scale + self.view_offset.x()
        y = -world_pos.y() * self.view_scale + self.view_offset.y()  # Y轴翻转
        return QPointF(x, y)


# 需要导入QApplication
from PySide6.QtWidgets import QApplication
