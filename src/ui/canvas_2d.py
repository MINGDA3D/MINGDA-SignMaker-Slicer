"""
MINGDA SignMaker - 2D画布组件

用于显示和编辑2D轮廓的画布组件，支持：
- 轮廓渲染
- 平移和缩放
- 选择和变换（移动、旋转、缩放）
- 网格背景
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import math

from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
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
    contours_modified = Signal()  # 轮廓被修改信号

    # 撤销/重做相关信号
    transform_started = Signal(str, list)  # 变换开始（操作类型, 索引列表）
    transform_ended = Signal(str, list)    # 变换结束（操作类型, 索引列表）
    delete_requested = Signal(list)        # 请求删除（索引列表）

    # 平台/标尺配置
    PLATFORM_WIDTH = 800    # 平台宽度 (mm)
    PLATFORM_HEIGHT = 1200  # 平台高度 (mm)
    GRID_SPACING = 20       # 网格间距 (mm)
    RULER_WIDTH = 30        # 标尺宽度 (像素)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 视图状态
        self.view_offset = QPointF(0, 0)  # 视图偏移
        self.view_scale = 1.0  # 视图缩放
        self.view_mode = "2d"  # 视图模式

        # 平台尺寸（可配置）
        self.platform_width = self.PLATFORM_WIDTH
        self.platform_height = self.PLATFORM_HEIGHT
        self.grid_spacing = self.GRID_SPACING

        # 数据
        self.contours: List[Contour] = []
        self.selected_indices: List[int] = []
        self.slice_result = None

        # 交互状态
        self.current_tool = "select"  # 当前工具: select, move, rotate, scale
        self.is_panning = False  # 是否正在平移视图
        self.is_transforming = False  # 是否正在变换轮廓
        self.pan_start = QPointF()  # 平移起始点
        self.transform_start = QPointF()  # 变换起始点（世界坐标）
        self.transform_start_screen = QPointF()  # 变换起始点（屏幕坐标）
        self.last_mouse_pos = QPointF()
        self.transform_center = QPointF()  # 变换中心点
        self.accumulated_rotation = 0.0  # 累计旋转角度（用于Shift吸附）

        # 变换追踪（用于撤销/重做）
        self._transform_total_dx = 0.0
        self._transform_total_dy = 0.0
        self._transform_total_angle = 0.0
        self._transform_total_scale = 1.0

        # 样式
        self.bg_color = QColor(COLORS.bg_primary)
        self.grid_color = QColor(40, 50, 60)  # 细网格颜色
        self.grid_major_color = QColor(50, 65, 80)  # 主网格颜色
        self.platform_border_color = QColor(80, 100, 120)  # 平台边框颜色
        self.ruler_bg_color = QColor(20, 28, 35)  # 标尺背景色
        self.ruler_text_color = QColor(120, 140, 160)  # 标尺文字颜色
        self.ruler_tick_color = QColor(80, 100, 120)  # 标尺刻度颜色
        self.contour_color = QColor(COLORS.path_shell)
        self.hole_color = QColor(COLORS.accent_warning)
        self.selected_color = QColor(COLORS.accent_primary)
        self.start_point_color = QColor(COLORS.accent_success)
        self.transform_handle_color = QColor(COLORS.accent_primary)

        # 设置
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _init_view(self):
        """初始化视图，显示整个平台"""
        # 计算缩放比例，使平台适应画布
        margin = 50
        canvas_width = max(self.width() - self.RULER_WIDTH - margin * 2, 100)
        canvas_height = max(self.height() - self.RULER_WIDTH - margin * 2, 100)

        scale_x = canvas_width / self.platform_width
        scale_y = canvas_height / self.platform_height
        self.view_scale = min(scale_x, scale_y)

        # 设置偏移，使平台在画布中居中显示（留出���尺空间）
        platform_screen_width = self.platform_width * self.view_scale
        platform_screen_height = self.platform_height * self.view_scale

        # 计算平台左边缘和底边缘的屏幕位置
        platform_left = self.RULER_WIDTH + margin + (canvas_width - platform_screen_width) / 2
        platform_bottom = self.height() - self.RULER_WIDTH - margin - (canvas_height - platform_screen_height) / 2

        self.view_offset = QPointF(platform_left, platform_bottom)

    def resizeEvent(self, event):
        """窗口大小改变时重新初始化视图"""
        super().resizeEvent(event)
        self._init_view()
        self.update()

    def set_platform_size(self, width: float, height: float, grid_spacing: float = 20):
        """
        设置平台尺寸

        Args:
            width: 平台宽度 (mm)
            height: 平台高度 (mm)
            grid_spacing: 网格间距 (mm)，默认20mm
        """
        self.platform_width = width
        self.platform_height = height
        self.grid_spacing = grid_spacing
        self._init_view()
        self.update()

    def set_contours(self, contours: List[Contour], center_on_platform: bool = True):
        """设置轮廓数据

        Args:
            contours: 轮廓列表
            center_on_platform: 是否将轮廓居中到平台中心
        """
        if center_on_platform and contours:
            self._center_contours_on_platform(contours)
        self.contours = contours
        self.selected_indices = []
        self.update()

    def _center_contours_on_platform(self, contours: List[Contour]):
        """将轮廓居中到平台中心"""
        # 计算所有轮廓的边界框
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for contour in contours:
            bounds = contour.outer.bounds
            min_x = min(min_x, bounds[0])
            min_y = min(min_y, bounds[1])
            max_x = max(max_x, bounds[2])
            max_y = max(max_y, bounds[3])

        if min_x == float('inf'):
            return

        # 计算轮廓中心
        contours_center_x = (min_x + max_x) / 2
        contours_center_y = (min_y + max_y) / 2

        # 计算平台中心
        platform_center_x = self.platform_width / 2
        platform_center_y = self.platform_height / 2

        # 计算偏移量
        offset_x = platform_center_x - contours_center_x
        offset_y = platform_center_y - contours_center_y

        # 移动所有轮廓
        for contour in contours:
            self._offset_path(contour.outer, offset_x, offset_y)
            for hole in contour.holes:
                self._offset_path(hole, offset_x, offset_y)

    def _offset_path(self, path, offset_x: float, offset_y: float):
        """将路径偏移指定距离"""
        for point in path.points:
            point.x += offset_x
            point.y += offset_y

    def set_view_mode(self, mode: str):
        """设置视图模式 (2d/3d)"""
        self.view_mode = mode
        self.update()

    def set_tool(self, tool: str):
        """设置当前工具"""
        self.current_tool = tool
        self._set_tool_cursor()

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
        if not self.selected_indices:
            return

        center = self._get_selection_center()

        for idx in self.selected_indices:
            contour = self.contours[idx]
            self._mirror_path(contour.outer, center, axis)
            for hole in contour.holes:
                self._mirror_path(hole, center, axis)

        self.contours_modified.emit()
        self.update()

    def _mirror_path(self, path: Path, center: QPointF, axis: str):
        """镜像路径"""
        new_points = []
        for p in path.points:
            if axis == "x":
                new_x = 2 * center.x() - p.x
                new_points.append(Point(new_x, p.y))
            else:  # y
                new_y = 2 * center.y() - p.y
                new_points.append(Point(p.x, new_y))
        path.points = new_points

    def move_selected(self, dx: float, dy: float):
        """移动选中的轮廓"""
        if not self.selected_indices:
            return

        for idx in self.selected_indices:
            contour = self.contours[idx]
            self._translate_path(contour.outer, dx, dy)
            for hole in contour.holes:
                self._translate_path(hole, dx, dy)

        self.contours_modified.emit()
        self.update()

    def _translate_path(self, path: Path, dx: float, dy: float):
        """平移路径"""
        path.points = [Point(p.x + dx, p.y + dy) for p in path.points]

    def rotate_selected(self, angle_degrees: float):
        """旋转选中的轮廓（绕选择中心）"""
        if not self.selected_indices:
            return

        center = self._get_selection_center()
        angle_rad = math.radians(angle_degrees)

        for idx in self.selected_indices:
            contour = self.contours[idx]
            self._rotate_path(contour.outer, center, angle_rad)
            for hole in contour.holes:
                self._rotate_path(hole, center, angle_rad)

        self.contours_modified.emit()
        self.update()

    def _rotate_path(self, path: Path, center: QPointF, angle_rad: float):
        """旋转路径"""
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        cx, cy = center.x(), center.y()

        new_points = []
        for p in path.points:
            dx = p.x - cx
            dy = p.y - cy
            new_x = cx + dx * cos_a - dy * sin_a
            new_y = cy + dx * sin_a + dy * cos_a
            new_points.append(Point(new_x, new_y))
        path.points = new_points

    def scale_selected(self, scale_factor: float):
        """缩放选中的轮廓（绕选择中心）"""
        if not self.selected_indices or scale_factor <= 0:
            return

        center = self._get_selection_center()

        for idx in self.selected_indices:
            contour = self.contours[idx]
            self._scale_path(contour.outer, center, scale_factor)
            for hole in contour.holes:
                self._scale_path(hole, center, scale_factor)

        self.contours_modified.emit()
        self.update()

    def _scale_path(self, path: Path, center: QPointF, factor: float):
        """缩放路径"""
        cx, cy = center.x(), center.y()
        new_points = []
        for p in path.points:
            new_x = cx + (p.x - cx) * factor
            new_y = cy + (p.y - cy) * factor
            new_points.append(Point(new_x, new_y))
        path.points = new_points

    def _get_selection_center(self) -> QPointF:
        """获取选中轮廓的中心点"""
        if not self.selected_indices:
            return QPointF(0, 0)

        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for idx in self.selected_indices:
            bounds = self.contours[idx].outer.bounds
            min_x = min(min_x, bounds[0])
            min_y = min(min_y, bounds[1])
            max_x = max(max_x, bounds[2])
            max_y = max(max_y, bounds[3])

        return QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)

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

        # 绘制平台区域（网格）
        self._draw_platform(painter)

        # 应用视图变换
        painter.save()
        painter.translate(self.view_offset)
        painter.scale(self.view_scale, -self.view_scale)  # Y轴翻转

        # 绘制轮廓
        self._draw_contours(painter)

        # 绘制选中状态（边界框和控制手柄）
        self._draw_selection_overlay(painter)

        painter.restore()

        # 绘制标尺（不受变换影响）
        self._draw_rulers(painter)

    def _draw_background(self, painter: QPainter):
        """绘制背景"""
        painter.fillRect(self.rect(), self.bg_color)

    def _draw_platform(self, painter: QPainter):
        """绘制平台区域和网格"""
        # 计算平台在屏幕上的位置
        origin = self._world_to_screen(QPointF(0, 0))
        top_right = self._world_to_screen(QPointF(self.platform_width, self.platform_height))

        platform_left = origin.x()
        platform_bottom = origin.y()
        platform_right = top_right.x()
        platform_top = top_right.y()

        # 绘制平台背景（稍微深一点）
        platform_rect = QRectF(platform_left, platform_top,
                               platform_right - platform_left,
                               platform_bottom - platform_top)
        painter.fillRect(platform_rect, QColor(15, 22, 30))

        # 计算网格间距（屏幕像素）
        grid_screen_spacing = self.grid_spacing * self.view_scale

        # 只有当网格足够大时才绘制
        if grid_screen_spacing >= 3:
            # 绘制细网格线
            pen = QPen(self.grid_color)
            pen.setWidth(1)
            painter.setPen(pen)

            # 垂直线
            for i in range(int(self.platform_width / self.grid_spacing) + 1):
                x_world = i * self.grid_spacing
                x_screen = platform_left + x_world * self.view_scale
                if platform_left <= x_screen <= platform_right:
                    painter.drawLine(int(x_screen), int(platform_top),
                                     int(x_screen), int(platform_bottom))

            # 水平线
            for i in range(int(self.platform_height / self.grid_spacing) + 1):
                y_world = i * self.grid_spacing
                y_screen = platform_bottom - y_world * self.view_scale
                if platform_top <= y_screen <= platform_bottom:
                    painter.drawLine(int(platform_left), int(y_screen),
                                     int(platform_right), int(y_screen))

            # 绘制主网格线（每100mm）
            major_spacing = 100  # mm
            if major_spacing * self.view_scale >= 10:
                pen.setColor(self.grid_major_color)
                pen.setWidth(1)
                painter.setPen(pen)

                # 垂直主网格线
                for i in range(int(self.platform_width / major_spacing) + 1):
                    x_world = i * major_spacing
                    x_screen = platform_left + x_world * self.view_scale
                    if platform_left <= x_screen <= platform_right:
                        painter.drawLine(int(x_screen), int(platform_top),
                                         int(x_screen), int(platform_bottom))

                # 水平主网格线
                for i in range(int(self.platform_height / major_spacing) + 1):
                    y_world = i * major_spacing
                    y_screen = platform_bottom - y_world * self.view_scale
                    if platform_top <= y_screen <= platform_bottom:
                        painter.drawLine(int(platform_left), int(y_screen),
                                         int(platform_right), int(y_screen))

        # 绘制平台边框
        pen = QPen(self.platform_border_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(platform_rect)

    def _draw_rulers(self, painter: QPainter):
        """绘制标尺（紧贴平台边缘）"""
        ruler_width = self.RULER_WIDTH

        # 计算平台在屏幕上的位置
        origin = self._world_to_screen(QPointF(0, 0))
        top_right = self._world_to_screen(QPointF(self.platform_width, self.platform_height))

        platform_left = origin.x()
        platform_bottom = origin.y()
        platform_right = top_right.x()
        platform_top = top_right.y()

        # 标尺位置紧贴平台
        left_ruler_x = platform_left - ruler_width  # 左侧标尺在平台左边
        bottom_ruler_y = platform_bottom  # 底部标尺在平台下边

        # 绘制左侧标尺背景（紧贴平台左边缘）
        left_ruler_rect = QRectF(left_ruler_x, platform_top,
                                  ruler_width, platform_bottom - platform_top)
        painter.fillRect(left_ruler_rect, self.ruler_bg_color)

        # 绘制底部标尺背景（紧贴平台下边缘）
        bottom_ruler_rect = QRectF(platform_left, bottom_ruler_y,
                                    platform_right - platform_left, ruler_width)
        painter.fillRect(bottom_ruler_rect, self.ruler_bg_color)

        # 绘制左下角方块
        corner_rect = QRectF(left_ruler_x, bottom_ruler_y, ruler_width, ruler_width)
        painter.fillRect(corner_rect, self.ruler_bg_color)

        # 设置画笔和字体
        pen = QPen(self.ruler_tick_color)
        pen.setWidth(1)
        painter.setPen(pen)

        from PySide6.QtGui import QFont
        font = QFont("Consolas", 8)
        painter.setFont(font)

        # 计算刻度间距
        tick_spacing = self.grid_spacing  # 每个网格一个小刻度
        major_tick_spacing = 100  # 每100mm一个大刻度（带数字）

        # 绘制底部标尺刻度（X轴）
        for i in range(int(self.platform_width / tick_spacing) + 1):
            x_world = i * tick_spacing
            x_screen = platform_left + x_world * self.view_scale

            if platform_left <= x_screen <= platform_right:
                tick_y = bottom_ruler_y

                if x_world % major_tick_spacing == 0:
                    # 大刻度
                    painter.setPen(pen)
                    painter.drawLine(int(x_screen), int(tick_y),
                                     int(x_screen), int(tick_y + 10))
                    # 绘制数字
                    painter.setPen(self.ruler_text_color)
                    text = str(int(x_world))
                    text_width = len(text) * 6
                    painter.drawText(int(x_screen - text_width / 2), int(tick_y + 22), text)
                else:
                    # 小刻度
                    painter.setPen(pen)
                    painter.drawLine(int(x_screen), int(tick_y),
                                     int(x_screen), int(tick_y + 5))

        # 绘制左侧标尺刻度（Y轴）
        for i in range(int(self.platform_height / tick_spacing) + 1):
            y_world = i * tick_spacing
            y_screen = platform_bottom - y_world * self.view_scale

            if platform_top <= y_screen <= platform_bottom:
                tick_x = platform_left

                if y_world % major_tick_spacing == 0:
                    # 大刻度
                    painter.setPen(pen)
                    painter.drawLine(int(tick_x - 10), int(y_screen),
                                     int(tick_x), int(y_screen))
                    # 绘制数字
                    painter.setPen(self.ruler_text_color)
                    text = str(int(y_world))
                    painter.drawText(int(left_ruler_x + 2), int(y_screen + 4), text)
                else:
                    # 小刻度
                    painter.setPen(pen)
                    painter.drawLine(int(tick_x - 5), int(y_screen),
                                     int(tick_x), int(y_screen))

        # 绘制标尺边框线
        pen.setColor(self.platform_border_color)
        painter.setPen(pen)
        # 左侧标尺右边界
        painter.drawLine(int(platform_left), int(platform_top),
                         int(platform_left), int(platform_bottom + ruler_width))
        # 底部标尺上边界
        painter.drawLine(int(left_ruler_x), int(platform_bottom),
                         int(platform_right), int(platform_bottom))

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

    def _draw_selection_overlay(self, painter: QPainter):
        """绘制选中状态覆盖层（边界框和控制手柄）"""
        if not self.selected_indices:
            return

        # 计算选中轮廓的总边界框
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for idx in self.selected_indices:
            if idx < len(self.contours):
                bounds = self.contours[idx].outer.bounds
                min_x = min(min_x, bounds[0])
                min_y = min(min_y, bounds[1])
                max_x = max(max_x, bounds[2])
                max_y = max(max_y, bounds[3])

        if min_x == float('inf'):
            return

        # 边界框边距
        margin = 5 / self.view_scale

        box_min_x = min_x - margin
        box_min_y = min_y - margin
        box_max_x = max_x + margin
        box_max_y = max_y + margin
        box_width = box_max_x - box_min_x
        box_height = box_max_y - box_min_y

        # 绘制虚线边界框
        pen = QPen(self.selected_color)
        pen.setWidthF(1.5 / self.view_scale)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(box_min_x, box_min_y, box_width, box_height))

        # 绘制控制手柄
        handle_size = 8 / self.view_scale
        handle_half = handle_size / 2

        # 手柄位置：四角 + 四边中点 + 中心
        handles = [
            (box_min_x, box_min_y),  # 左下
            (box_max_x, box_min_y),  # 右下
            (box_max_x, box_max_y),  # 右上
            (box_min_x, box_max_y),  # 左上
            ((box_min_x + box_max_x) / 2, box_min_y),  # 下中
            ((box_min_x + box_max_x) / 2, box_max_y),  # 上中
            (box_min_x, (box_min_y + box_max_y) / 2),  # 左中
            (box_max_x, (box_min_y + box_max_y) / 2),  # 右中
        ]

        # 绘制手柄（白色填充+蓝色边框）
        pen = QPen(self.selected_color)
        pen.setWidthF(1.5 / self.view_scale)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))

        for hx, hy in handles:
            painter.drawRect(QRectF(hx - handle_half, hy - handle_half, handle_size, handle_size))

        # 绘制中心点（旋转中心）
        center_x = (box_min_x + box_max_x) / 2
        center_y = (box_min_y + box_max_y) / 2
        center_radius = 5 / self.view_scale

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), center_radius, center_radius)

        # 十字线
        cross_size = 3 / self.view_scale
        painter.drawLine(
            QPointF(center_x - cross_size, center_y),
            QPointF(center_x + cross_size, center_y)
        )
        painter.drawLine(
            QPointF(center_x, center_y - cross_size),
            QPointF(center_x, center_y + cross_size)
        )

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
        world_pos = self._screen_to_world(event.position())

        if event.button() == Qt.MouseButton.MiddleButton:
            # 中键平移视图
            self.is_panning = True
            self.pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool == "select":
                self._handle_selection(event.position())
            elif self.current_tool in ("move", "rotate", "scale"):
                # 检查是否点击在已选中的轮廓上
                clicked_on_selected = False
                for idx in self.selected_indices:
                    if idx < len(self.contours):
                        if self._point_in_contour(world_pos, self.contours[idx]):
                            clicked_on_selected = True
                            break

                if clicked_on_selected:
                    # 开始变换操作
                    self.is_transforming = True
                    self.transform_start = world_pos
                    self.transform_start_screen = event.position()  # 保存屏幕坐标
                    self.transform_center = self._get_selection_center()
                    self.accumulated_rotation = 0.0  # 累计旋转角度
                    # 重置变换追踪
                    self._transform_total_dx = 0.0
                    self._transform_total_dy = 0.0
                    self._transform_total_angle = 0.0
                    self._transform_total_scale = 1.0
                    # 发出变换开始信号
                    self.transform_started.emit(self.current_tool, list(self.selected_indices))
                    self._set_tool_cursor()
                else:
                    # 点击了其他位置，尝试选择新轮廓
                    self._handle_selection(event.position())

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        pos = event.position()
        world_pos = self._screen_to_world(pos)

        if self.is_panning:
            # 平移视图
            delta = pos - self.pan_start
            self.view_offset += delta
            self.pan_start = pos
            self.update()
        elif self.is_transforming and self.selected_indices:
            # 执行变换
            if self.current_tool == "move":
                dx = world_pos.x() - self.transform_start.x()
                dy = world_pos.y() - self.transform_start.y()
                self.move_selected(dx, dy)
                self._transform_total_dx += dx
                self._transform_total_dy += dy
                self.transform_start = world_pos
            elif self.current_tool == "rotate":
                # 使用水平拖动控制旋转：每100像素 = 45度
                dx_screen = pos.x() - self.last_mouse_pos.x()
                angle_delta = dx_screen * 0.5  # 每像素0.5度

                # Shift键：吸附到15度增量
                if Qt.KeyboardModifier.ShiftModifier in QApplication.keyboardModifiers():
                    self.accumulated_rotation += angle_delta
                    # 当累计超过15度时执行旋转
                    if abs(self.accumulated_rotation) >= 15:
                        snap_angle = 15 * (self.accumulated_rotation // 15)
                        self.rotate_selected(snap_angle)
                        self._transform_total_angle += snap_angle
                        self.accumulated_rotation -= snap_angle
                else:
                    self.rotate_selected(angle_delta)
                    self._transform_total_angle += angle_delta
            elif self.current_tool == "scale":
                # 使用水平拖动控制缩放：向右放大，向左缩小
                dx_screen = pos.x() - self.last_mouse_pos.x()
                scale_factor = 1.0 + dx_screen * 0.005  # 每像素0.5%

                # 限制缩放范围
                scale_factor = max(0.9, min(1.1, scale_factor))

                # Shift键：等比例缩放（保持比例）
                self.scale_selected(scale_factor)
                self._transform_total_scale *= scale_factor
        else:
            # 更新坐标显示
            self.mouse_moved.emit(world_pos.x(), world_pos.y())

        self.last_mouse_pos = pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.is_transforming:
                self.is_transforming = False
                # 发出变换结束信号，携带变换信息
                self.transform_ended.emit(self.current_tool, list(self.selected_indices))
                self._set_tool_cursor()

    def get_transform_delta(self) -> dict:
        """获取累计的变换量（供撤销/重做使用）"""
        return {
            'dx': self._transform_total_dx,
            'dy': self._transform_total_dy,
            'angle': self._transform_total_angle,
            'scale': self._transform_total_scale,
            'center': (self.transform_center.x(), self.transform_center.y())
        }

    def _set_tool_cursor(self):
        """根据当前工具设置光标"""
        cursors = {
            "select": Qt.CursorShape.ArrowCursor,
            "move": Qt.CursorShape.SizeAllCursor,
            "rotate": Qt.CursorShape.CrossCursor,
            "scale": Qt.CursorShape.SizeFDiagCursor,
        }
        self.setCursor(cursors.get(self.current_tool, Qt.CursorShape.ArrowCursor))

    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Delete:
            # 删除选中
            if self.selected_indices:
                self.delete_requested.emit(list(self.selected_indices))
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

        # 找到所有包含点击位置的轮廓
        candidates = []
        for i, contour in enumerate(self.contours):
            if self._point_in_contour(world_pos, contour):
                # 记录轮廓索引和面积
                candidates.append((i, contour.outer.area))

        if candidates:
            # 选择面积最小的轮廓（最内层的）
            candidates.sort(key=lambda x: x[1])
            selected_idx = candidates[0][0]

            if Qt.KeyboardModifier.ControlModifier in QApplication.keyboardModifiers():
                # Ctrl+点击：切换选择
                if selected_idx in self.selected_indices:
                    self.selected_indices.remove(selected_idx)
                else:
                    self.selected_indices.append(selected_idx)
            else:
                # 普通点击：单选
                self.selected_indices = [selected_idx]

            self.contour_selected.emit(selected_idx)
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
