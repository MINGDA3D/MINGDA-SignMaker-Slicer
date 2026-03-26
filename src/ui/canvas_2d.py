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

from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication, QMenu
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QWheelEvent, QMouseEvent, QKeyEvent, QTransform, QKeySequence
)

from src.core.contour_classifier import classify_paths_by_nesting
from src.core.path_offset import PathOffset
from src.core.types import Point, Path, Contour, PathType
from src.utils.geometry import normalize_path
from .theme import COLORS


class Canvas2D(QWidget):
    """2D画布组件"""

    # 信号
    contour_selected = Signal(int)  # 轮廓选中信号
    selection_cleared = Signal()    # 选择清除信号
    mouse_moved = Signal(float, float)  # 鼠标移动信号
    zoom_changed = Signal(float)  # 缩放变化信号
    contours_modified = Signal()  # 轮廓被修改信号

    # 撤销/重做相关信号
    transform_started = Signal(str, list)  # 变换开始（操作类型, 索引列表）
    transform_ended = Signal(str, list)    # 变换结束（操作类型, 索引列表）
    delete_requested = Signal(list)        # 请求删除（索引列表）

    # 右键菜单信号
    select_all_requested = Signal()        # 全选
    mirror_requested = Signal(str)         # 镜像（"x" 或 "y"）
    fit_view_requested = Signal()          # 适应视图
    reset_view_requested = Signal()        # 重置视图

    # 平台/标尺配置
    PLATFORM_WIDTH = 800    # 平台宽度 (mm)
    PLATFORM_HEIGHT = 1200  # 平台高度 (mm)
    GRID_SPACING = 20       # 网格间距 (mm)
    RULER_WIDTH = 30        # 标尺宽度 (像素)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("canvas")

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
        self._path_offset = PathOffset()

        # 交互状态
        self.current_tool = "select"  # 当前工具: select, move, rotate, scale
        self.is_panning = False  # 是否正在平移视图
        self.is_transforming = False  # 是否正在变换轮廓
        self.pan_start = QPointF()  # 平移起始点
        self._pan_button_down = False  # 右键/中键已按下，等待判定是否为平移
        self._pan_origin = QPointF()   # 按下时的位置（用于阈值判定）
        self._pan_button = Qt.MouseButton.NoButton  # 记录触发平移的按键
        self._PAN_THRESHOLD = 4  # 拖动超过4像素才视为平移（避免误触）
        self.transform_start = QPointF()  # 变换起始点（世界坐标）
        self.transform_start_screen = QPointF()  # 变换起始点（屏幕坐标）
        self.last_mouse_pos = QPointF()
        self.transform_center = QPointF()  # 变换中心点

        # 旋转Gizmo状态（OrcaSlicer风格）
        self._rotate_gizmo_radius = 0.0    # 旋转圆环半径（屏幕像素）
        self._rotate_start_angle = 0.0     # 拖动开始时的鼠标极角（弧度）
        self._rotate_current_angle = 0.0   # 当前鼠标极角（弧度）
        self._rotate_base_angle = 0.0      # 拖动开始前的累计旋转角度
        self._rotate_hovering_grabber = False  # 鼠标是否悬停在Grabber上
        self._GIZMO_RADIUS_OFFSET = 30     # 圆环半径比包围球多出的像素数
        self._GRABBER_RADIUS = 8           # Grabber手柄半径（像素）
        self._SNAP_COARSE_STEPS = 8        # 粗吸附：45度
        self._SNAP_FINE_STEPS = 72         # 细吸附：5度

        # 变换追踪（用于撤销/重做）
        self._transform_total_dx = 0.0
        self._transform_total_dy = 0.0
        self._transform_total_angle = 0.0
        self._transform_total_scale = 1.0
        # 累计旋转角度（跨多次操作，用于面板显示）
        self._cumulative_angle = 0.0

        # 样式
        self.bg_color = QColor(COLORS.editor_canvas_bg)
        self.platform_bg_color = QColor(COLORS.editor_canvas_platform_bg)
        self.frame_color = QColor(COLORS.editor_canvas_frame)
        self.grid_color = QColor(36, 47, 59)  # 细网格颜色
        self.grid_major_color = QColor(50, 64, 79)  # 主网格颜色
        self.platform_border_color = QColor(92, 115, 138)  # 平台边框颜色
        self.ruler_bg_color = QColor(16, 24, 33)  # 标尺背景色
        self.ruler_text_color = QColor(120, 140, 160)  # 标尺文字颜色
        self.ruler_tick_color = QColor(92, 115, 138)  # 标尺刻度颜色
        self.contour_color = QColor(COLORS.path_shell)
        self.hole_color = QColor(COLORS.accent_warning)
        self.selected_color = QColor(COLORS.accent_primary)
        self.start_point_color = QColor(COLORS.accent_success)
        self.transform_handle_color = QColor(COLORS.accent_primary)
        self.rotate_gizmo_color = QColor(88, 166, 255, 180)  # 旋转圆环颜色
        self.rotate_arc_color = QColor(88, 166, 255, 120)    # 旋转角度弧颜色
        self.rotate_snap_color = QColor(88, 166, 255, 60)    # 吸附参考线颜色

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
        self.set_selected_indices([], update_view=False)
        self.update()

    def _normalize_selected_indices(self, indices: List[int]) -> List[int]:
        """过滤非法索引并去重，保持现有顺序。"""
        normalized: List[int] = []
        seen = set()
        for idx in indices:
            if 0 <= idx < len(self.contours) and idx not in seen:
                normalized.append(idx)
                seen.add(idx)
        return normalized

    def set_selected_indices(
        self,
        indices: List[int],
        active_index: Optional[int] = None,
        update_view: bool = True,
    ):
        """统一更新选中状态，并发出对应信号。"""
        self.selected_indices = self._normalize_selected_indices(indices)

        if self.selected_indices:
            emit_index = active_index
            if emit_index not in self.selected_indices:
                emit_index = self.selected_indices[0]
            self.contour_selected.emit(emit_index)
        else:
            self.selection_cleared.emit()

        if update_view:
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
        self._rotate_base_angle = 0.0  # 切换工具时重置旋转Gizmo
        self._rotate_hovering_grabber = False
        self._set_tool_cursor()
        self.update()

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
        """缩放选中的轮廓（绕选择中心，等比例）"""
        self.scale_selected_xy(scale_factor, scale_factor)

    def scale_selected_xy(self, sx: float, sy: float):
        """缩放选中的轮廓（绕选择中心，X/Y独立）"""
        if not self.selected_indices or sx <= 0 or sy <= 0:
            return

        center = self._get_selection_center()

        for idx in self.selected_indices:
            contour = self.contours[idx]
            self._scale_path_xy(contour.outer, center, sx, sy)
            for hole in contour.holes:
                self._scale_path_xy(hole, center, sx, sy)

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

    def _scale_path_xy(self, path: Path, center: QPointF, sx: float, sy: float):
        """缩放路径（X/Y独立）"""
        cx, cy = center.x(), center.y()
        new_points = []
        for p in path.points:
            new_x = cx + (p.x - cx) * sx
            new_y = cy + (p.y - cy) * sy
            new_points.append(Point(new_x, new_y))
        path.points = new_points

    def get_selection_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """获取选中轮廓的边界框 (min_x, min_y, max_x, max_y)"""
        if not self.selected_indices:
            return None

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
            return None
        return (min_x, min_y, max_x, max_y)

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
        result = self.build_boolean_intersection_result()
        if result is None:
            return
        selected, result_contours = result
        self._replace_selected_contours(selected, result_contours)

    def boolean_difference(self):
        """布尔差集"""
        result = self.build_boolean_difference_result()
        if result is None:
            return
        selected, result_contours = result
        self._replace_selected_contours(selected, result_contours)

    def build_boolean_intersection_result(
        self,
    ) -> Optional[Tuple[List[int], List[Contour]]]:
        """计算交集结果，但不直接修改当前轮廓。"""
        selected = self._get_valid_selected_indices()
        if len(selected) < 2:
            return None

        result_paths = self._contour_to_boolean_paths(self.contours[selected[0]])
        for idx in selected[1:]:
            clip_paths = self._contour_to_boolean_paths(self.contours[idx])
            result_paths = self._path_offset.boolean_intersection_multi(
                result_paths,
                clip_paths,
            )
            if not result_paths:
                break

        result_contours = self._boolean_paths_to_contours(
            result_paths,
            self.contours[selected[0]],
        )
        return selected, result_contours

    def build_boolean_difference_result(
        self,
    ) -> Optional[Tuple[List[int], List[Contour]]]:
        """计算差集结果，但不直接修改当前轮廓。"""
        selected = self._get_valid_selected_indices()
        if len(selected) < 2:
            return None

        subject_paths = self._contour_to_boolean_paths(self.contours[selected[0]])
        clip_paths: List[Path] = []
        for idx in selected[1:]:
            clip_paths.extend(self._contour_to_boolean_paths(self.contours[idx]))

        result_paths = self._path_offset.boolean_difference_multi(
            subject_paths,
            clip_paths,
        )
        result_contours = self._boolean_paths_to_contours(
            result_paths,
            self.contours[selected[0]],
        )
        return selected, result_contours

    def group_selected(self):
        """组合选中的轮廓"""
        selected = self.get_group_target_indices()
        if len(selected) < 2:
            return

        group_id = self._generate_group_id()
        for idx in selected:
            self.contours[idx].group_id = group_id

        self.set_selected_indices(selected, active_index=selected[0], update_view=False)
        self.contours_modified.emit()
        self.update()

    def ungroup_selected(self):
        """打散选中的轮廓"""
        selected = self.get_ungroup_target_indices()
        if not selected:
            return

        for idx in selected:
            self.contours[idx].group_id = ""

        self.set_selected_indices(selected, active_index=selected[0], update_view=False)
        self.contours_modified.emit()
        self.update()

    def _get_valid_selected_indices(self) -> List[int]:
        """返回仍然存在的选中索引，保持当前选择顺序。"""
        return [
            idx for idx in self.selected_indices
            if 0 <= idx < len(self.contours)
        ]

    def get_group_target_indices(self) -> List[int]:
        """返回当前选中对象及其所在组的完整索引集合。"""
        return self.expand_indices_to_groups(self._get_valid_selected_indices())

    def get_ungroup_target_indices(self) -> List[int]:
        """返回当前选中且属于某个组的完整索引集合。"""
        expanded = self.expand_indices_to_groups(self._get_valid_selected_indices())
        return [
            idx for idx in expanded
            if self._get_group_id(self.contours[idx])
        ]

    def expand_indices_to_groups(self, indices: List[int]) -> List[int]:
        """将索引扩展为完整的组选中集合。"""
        expanded: List[int] = []
        seen = set()

        for idx in indices:
            if not (0 <= idx < len(self.contours)):
                continue

            related = self._get_group_member_indices_for_index(idx)
            for related_idx in related:
                if related_idx not in seen:
                    seen.add(related_idx)
                    expanded.append(related_idx)

        return expanded

    def _contour_to_boolean_paths(self, contour: Contour) -> List[Path]:
        """将轮廓转换为布尔运算用的闭合 loop 列表。"""
        paths = [
            normalize_path(self._clone_path(contour.outer, PathType.OUTER))
        ]
        for hole in contour.holes:
            paths.append(normalize_path(self._clone_path(hole, PathType.INNER)))
        return paths

    def _boolean_paths_to_contours(
        self,
        paths: List[Path],
        template: Optional[Contour] = None,
    ) -> List[Contour]:
        """将布尔运算返回的 loop 重建为轮廓。"""
        contours = classify_paths_by_nesting(paths)
        if template is None:
            return contours

        if len(contours) == 1:
            contours[0].name = template.name
            contours[0].start_point_index = template.start_point_index
            contours[0].print_order = template.print_order
        elif template.name:
            for i, contour in enumerate(contours, start=1):
                contour.name = f"{template.name}-{i}"

        return contours

    def _replace_selected_contours(
        self,
        selected: List[int],
        new_contours: List[Contour],
    ):
        """用布尔运算结果替换原选中轮廓。"""
        if not selected:
            return

        selected_set = set(selected)
        insert_at = min(selected)
        updated = [
            contour for i, contour in enumerate(self.contours)
            if i not in selected_set
        ]
        updated[insert_at:insert_at] = new_contours
        self.contours[:] = updated

        if new_contours:
            self.set_selected_indices(
                list(range(insert_at, insert_at + len(new_contours))),
                active_index=insert_at,
                update_view=False,
            )
        else:
            self.set_selected_indices([], update_view=False)

        self.contours_modified.emit()
        self.update()

    def _clone_path(self, path: Path, path_type: PathType) -> Path:
        """复制路径并设置布尔运算所需的类型。"""
        return Path(
            points=[Point(p.x, p.y) for p in path.points],
            path_type=path_type,
            color=path.color,
            is_closed=path.is_closed,
        )

    def _get_group_id(self, contour: Contour) -> str:
        """获取轮廓的 group id。"""
        return getattr(contour, "group_id", "")

    def _get_group_member_indices(self, group_id: str) -> List[int]:
        """获取组内所有成员索引。"""
        if not group_id:
            return []

        return [
            i for i, contour in enumerate(self.contours)
            if self._get_group_id(contour) == group_id
        ]

    def _get_group_member_indices_for_index(self, index: int) -> List[int]:
        """获取某个轮廓对应的完整组选中集合。"""
        if not (0 <= index < len(self.contours)):
            return []

        group_id = self._get_group_id(self.contours[index])
        if not group_id:
            return [index]

        members = self._get_group_member_indices(group_id)
        return members if members else [index]

    def _generate_group_id(self) -> str:
        """生成新的组 id。"""
        import uuid

        return uuid.uuid4().hex

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

        # 绘制旋转Gizmo（屏幕坐标，不受世界变换影响）
        if self.current_tool == "rotate" and self.selected_indices:
            self._draw_rotate_gizmo(painter)

        # 绘制标尺（不受变换影响）
        self._draw_rulers(painter)

    def _draw_background(self, painter: QPainter):
        """绘制背景"""
        painter.fillRect(self.rect(), self.bg_color)
        painter.setPen(QPen(self.frame_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

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
        painter.fillRect(platform_rect, self.platform_bg_color)

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

    def _draw_rotate_gizmo(self, painter: QPainter):
        """绘制OrcaSlicer风格的旋转Gizmo（屏幕坐标系）"""
        center_world = self._get_selection_center()
        center_screen = self._world_to_screen(center_world)
        cx, cy = center_screen.x(), center_screen.y()

        # 计算圆环半径：基于选中区域的包围球 + 偏移
        radius = self._calc_gizmo_radius()
        self._rotate_gizmo_radius = radius

        is_dragging = self.is_transforming and getattr(self, '_active_drag_tool', None) == "rotate"

        # --- 1. 绘制旋转圆环 ---
        pen = QPen(self.rotate_gizmo_color)
        pen.setWidthF(2.0 if not is_dragging else 2.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # --- 2. 绘制45度吸附参考线（内区域）---
        if self._rotate_hovering_grabber or is_dragging:
            pen_snap = QPen(self.rotate_snap_color)
            pen_snap.setWidthF(1.0)
            painter.setPen(pen_snap)
            coarse_inner = radius / 3.0
            coarse_outer = radius * 2.0 / 3.0
            for i in range(self._SNAP_COARSE_STEPS):
                angle = i * 2 * math.pi / self._SNAP_COARSE_STEPS
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                painter.drawLine(
                    QPointF(cx + cos_a * coarse_inner, cy - sin_a * coarse_inner),
                    QPointF(cx + cos_a * coarse_outer, cy - sin_a * coarse_outer)
                )

        # --- 3. 绘制刻度线（圆环边缘，每5度一个）---
        if self._rotate_hovering_grabber or is_dragging:
            pen_tick = QPen(self.rotate_gizmo_color)
            pen_tick.setWidthF(1.0)
            painter.setPen(pen_tick)
            for i in range(self._SNAP_FINE_STEPS):
                angle = i * 2 * math.pi / self._SNAP_FINE_STEPS
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                # 每10度（偶数索引）较长刻度
                tick_len = 8 if (i % 2 == 0) else 4
                r_inner = radius - tick_len
                painter.drawLine(
                    QPointF(cx + cos_a * r_inner, cy - sin_a * r_inner),
                    QPointF(cx + cos_a * radius, cy - sin_a * radius)
                )

        # --- 4. 拖动中：绘制参考线和角度弧 ---
        if is_dragging:
            # 参考线（起始方向）
            pen_ref = QPen(self.rotate_gizmo_color)
            pen_ref.setWidthF(1.0)
            pen_ref.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen_ref)
            ref_angle = self._rotate_start_angle
            painter.drawLine(
                QPointF(cx, cy),
                QPointF(cx + math.cos(ref_angle) * radius,
                        cy - math.sin(ref_angle) * radius)
            )

            # 当前方向线
            pen_cur = QPen(self.selected_color)
            pen_cur.setWidthF(1.5)
            painter.setPen(pen_cur)
            cur_angle = self._rotate_current_angle
            painter.drawLine(
                QPointF(cx, cy),
                QPointF(cx + math.cos(cur_angle) * radius,
                        cy - math.sin(cur_angle) * radius)
            )

            # 角度弧
            swept = cur_angle - ref_angle
            # 归一化到 [-π, π]
            while swept > math.pi:
                swept -= 2 * math.pi
            while swept < -math.pi:
                swept += 2 * math.pi

            arc_radius = radius * 0.4
            arc_path = QPainterPath()
            segments = max(2, int(abs(swept) / (math.pi / 32)))
            start = ref_angle
            for j in range(segments + 1):
                t = start + swept * j / segments
                px = cx + math.cos(t) * arc_radius
                py = cy - math.sin(t) * arc_radius
                if j == 0:
                    arc_path.moveTo(px, py)
                else:
                    arc_path.lineTo(px, py)

            pen_arc = QPen(self.rotate_arc_color)
            pen_arc.setWidthF(3.0)
            painter.setPen(pen_arc)
            painter.drawPath(arc_path)

            # 角度文本
            angle_deg = math.degrees(swept)
            text = f"{angle_deg:+.1f}°"
            from PySide6.QtGui import QFont
            font = QFont("Consolas", 11)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            # 文本位置在弧的中间方向
            mid_angle = ref_angle + swept / 2
            text_r = arc_radius + 18
            text_x = cx + math.cos(mid_angle) * text_r
            text_y = cy - math.sin(mid_angle) * text_r
            painter.drawText(int(text_x - 25), int(text_y + 5), text)

        # --- 5. 绘制Grabber手柄 ---
        grabber_r = radius * 1.12  # 手柄在圆环外15%处
        if is_dragging:
            grabber_angle = self._rotate_current_angle
        else:
            # 非拖动状态：手柄在0度方向（或上一次旋转后的位置）
            grabber_angle = self._rotate_base_angle
        gx = cx + math.cos(grabber_angle) * grabber_r
        gy = cy - math.sin(grabber_angle) * grabber_r

        # 手柄到圆心的连线
        pen_conn = QPen(self.rotate_gizmo_color)
        pen_conn.setWidthF(1.0)
        painter.setPen(pen_conn)
        painter.drawLine(QPointF(cx, cy), QPointF(gx, gy))

        # 手柄圆点
        if self._rotate_hovering_grabber or is_dragging:
            painter.setBrush(QBrush(self.selected_color))
            pen_g = QPen(QColor(255, 255, 255))
        else:
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            pen_g = QPen(self.rotate_gizmo_color)
        pen_g.setWidthF(2.0)
        painter.setPen(pen_g)
        painter.drawEllipse(QPointF(gx, gy), self._GRABBER_RADIUS, self._GRABBER_RADIUS)

    def _calc_gizmo_radius(self) -> float:
        """计算旋转Gizmo的圆环半径（屏幕像素）"""
        if not self.selected_indices:
            return 60.0

        # 计算选中区域在屏幕上的包围球半径
        center = self._get_selection_center()
        max_dist_sq = 0.0
        for idx in self.selected_indices:
            if idx < len(self.contours):
                bounds = self.contours[idx].outer.bounds
                # 检查四个角到中心的距离
                for bx, by in [(bounds[0], bounds[1]), (bounds[2], bounds[1]),
                                (bounds[2], bounds[3]), (bounds[0], bounds[3])]:
                    dx = bx - center.x()
                    dy = by - center.y()
                    max_dist_sq = max(max_dist_sq, dx * dx + dy * dy)

        world_radius = math.sqrt(max_dist_sq) if max_dist_sq > 0 else 30.0
        screen_radius = world_radius * self.view_scale
        return max(60.0, screen_radius + self._GIZMO_RADIUS_OFFSET)

    def _screen_angle_to_center(self, screen_pos: QPointF) -> float:
        """计算屏幕点相对于选区中心的极角（弧度，屏幕坐标系，Y向上）"""
        center_screen = self._world_to_screen(self._get_selection_center())
        dx = screen_pos.x() - center_screen.x()
        dy = -(screen_pos.y() - center_screen.y())  # 屏幕Y向下→翻转为Y向上
        return math.atan2(dy, dx)

    def _screen_dist_to_center(self, screen_pos: QPointF) -> float:
        """计算屏幕点到选区中心的距离（像素）"""
        center_screen = self._world_to_screen(self._get_selection_center())
        dx = screen_pos.x() - center_screen.x()
        dy = screen_pos.y() - center_screen.y()
        return math.sqrt(dx * dx + dy * dy)

    def _snap_rotation_angle(self, angle: float, mouse_dist: float) -> float:
        """根据鼠标到中心距离进行角度吸附（OrcaSlicer距离分区吸附）

        Args:
            angle: 原始角度（弧度）
            mouse_dist: 鼠标到旋转中心的屏幕距离

        Returns:
            吸附后的角度（弧度）
        """
        radius = self._rotate_gizmo_radius
        coarse_inner = radius / 3.0
        coarse_outer = radius * 2.0 / 3.0
        fine_inner = radius - 10
        fine_outer = radius + 10

        if coarse_inner <= mouse_dist <= coarse_outer:
            # 粗吸附区域：45度
            step = 2 * math.pi / self._SNAP_COARSE_STEPS
            return step * round(angle / step)
        elif fine_inner <= mouse_dist <= fine_outer:
            # 细吸附区域：5度
            step = 2 * math.pi / self._SNAP_FINE_STEPS
            return step * round(angle / step)
        else:
            # 自由旋转
            return angle

    def _is_on_grabber(self, screen_pos: QPointF) -> bool:
        """判断屏幕点是否在旋转Grabber手柄上"""
        if not self.selected_indices:
            return False
        center_screen = self._world_to_screen(self._get_selection_center())
        radius = self._calc_gizmo_radius()
        grabber_r = radius * 1.12
        angle = self._rotate_base_angle
        gx = center_screen.x() + math.cos(angle) * grabber_r
        gy = center_screen.y() - math.sin(angle) * grabber_r
        dx = screen_pos.x() - gx
        dy = screen_pos.y() - gy
        # 点击区域比手柄视觉半径稍大，更容易点击
        hit_radius = self._GRABBER_RADIUS + 4
        return (dx * dx + dy * dy) <= hit_radius * hit_radius

    def _is_on_ring(self, screen_pos: QPointF) -> bool:
        """判断屏幕点是否在旋转圆环附近"""
        if not self.selected_indices:
            return False
        dist = self._screen_dist_to_center(screen_pos)
        radius = self._calc_gizmo_radius()
        return abs(dist - radius) <= 12  # 圆环12像素容差

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

        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            # 中键/右键按下：记录位置，等移动超过阈值后才开始平移
            self._pan_button_down = True
            self._pan_button = event.button()
            self._pan_origin = event.position()
            self.pan_start = event.position()
        elif event.button() == Qt.MouseButton.LeftButton:
            # 先检查是否点击在已选中的轮廓上（支持直接拖动）
            clicked_on_selected = False
            if self.selected_indices:
                for idx in self.selected_indices:
                    if idx < len(self.contours):
                        if self._point_in_contour(world_pos, self.contours[idx]):
                            clicked_on_selected = True
                            break

            if clicked_on_selected and self.current_tool in ("select", "move"):
                # 在选择模式下点击已选中轮廓，开始拖动移动
                self.is_transforming = True
                self._active_drag_tool = "move"  # 记录实际的拖动工具
                self.transform_start = world_pos
                self.transform_start_screen = event.position()
                self.transform_center = self._get_selection_center()
                # 重置变换追踪
                self._transform_total_dx = 0.0
                self._transform_total_dy = 0.0
                self._transform_total_angle = 0.0
                self._transform_total_scale = 1.0
                # 发出变换开始信号
                self.transform_started.emit("move", list(self.selected_indices))
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            elif self.current_tool == "rotate" and self.selected_indices and self._is_on_grabber(event.position()):
                # 旋转工具：点击Grabber开始旋转
                self.is_transforming = True
                self._active_drag_tool = "rotate"
                self.transform_center = self._get_selection_center()
                self._rotate_start_angle = self._screen_angle_to_center(event.position())
                self._rotate_current_angle = self._rotate_start_angle
                # 重置变换追踪
                self._transform_total_dx = 0.0
                self._transform_total_dy = 0.0
                self._transform_total_angle = 0.0
                self._transform_total_scale = 1.0
                # 发出变换开始信号
                self.transform_started.emit("rotate", list(self.selected_indices))
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif clicked_on_selected and self.current_tool == "scale":
                # 缩放工具
                self.is_transforming = True
                self._active_drag_tool = "scale"
                self.transform_start = world_pos
                self.transform_start_screen = event.position()
                self.transform_center = self._get_selection_center()
                # 重置变换追踪
                self._transform_total_dx = 0.0
                self._transform_total_dy = 0.0
                self._transform_total_angle = 0.0
                self._transform_total_scale = 1.0
                # 发出变换开始信号
                self.transform_started.emit("scale", list(self.selected_indices))
                self._set_tool_cursor()
            else:
                # 点击了其他位置，尝试选择新轮廓
                self._handle_selection(event.position())

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        pos = event.position()
        world_pos = self._screen_to_world(pos)

        if self._pan_button_down and not self.is_panning:
            # 判断是否超过拖动阈值
            delta = pos - self._pan_origin
            distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
            if distance >= self._PAN_THRESHOLD:
                # 超过阈值，正式进入平移模式
                self.is_panning = True
                self.pan_start = pos  # 从当前位置开始平移（避免跳跃）
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

        if self.is_panning:
            # 平移视图
            delta = pos - self.pan_start
            self.view_offset += delta
            self.pan_start = pos
            self.update()
        elif self.is_transforming and self.selected_indices:
            # 执行变换 - 使用实际的拖动工具
            active_tool = getattr(self, '_active_drag_tool', self.current_tool)
            if active_tool == "move":
                dx = world_pos.x() - self.transform_start.x()
                dy = world_pos.y() - self.transform_start.y()
                self.move_selected(dx, dy)
                self._transform_total_dx += dx
                self._transform_total_dy += dy
                self.transform_start = world_pos
            elif active_tool == "rotate":
                # OrcaSlicer风格：基于鼠标极角控制旋转
                raw_angle = self._screen_angle_to_center(pos)
                mouse_dist = self._screen_dist_to_center(pos)
                snapped_angle = self._snap_rotation_angle(raw_angle, mouse_dist)
                self._rotate_current_angle = snapped_angle

                # 计算相对于上一帧的增量
                angle_delta = snapped_angle - self._rotate_start_angle
                # 归一化到 [-π, π]
                while angle_delta > math.pi:
                    angle_delta -= 2 * math.pi
                while angle_delta < -math.pi:
                    angle_delta += 2 * math.pi

                # 计算从拖动开始到现在的总旋转
                # 先反转之前已应用的旋转，再应用新的总旋转
                prev_total = self._transform_total_angle
                new_total_deg = math.degrees(angle_delta)
                delta_deg = new_total_deg - prev_total
                if abs(delta_deg) > 0.001:
                    self.rotate_selected(delta_deg)
                    self._transform_total_angle = new_total_deg
                self.update()
            elif active_tool == "scale":
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

            # 旋转工具：更新Grabber悬停状态
            if self.current_tool == "rotate" and self.selected_indices:
                was_hovering = self._rotate_hovering_grabber
                self._rotate_hovering_grabber = self._is_on_grabber(pos) or self._is_on_ring(pos)
                if was_hovering != self._rotate_hovering_grabber:
                    self.update()  # 悬停状态改变时重绘

        self.last_mouse_pos = pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            was_panning = self.is_panning
            self.is_panning = False
            self._pan_button_down = False
            self._pan_button = Qt.MouseButton.NoButton
            self._set_tool_cursor()

            if not was_panning and event.button() == Qt.MouseButton.RightButton:
                # 未超过阈值，视为右键单击 → 弹出右键菜单
                self._show_context_menu(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.is_transforming:
                active_tool = getattr(self, '_active_drag_tool', self.current_tool)
                # 旋转结束时更新Grabber基准角度
                if active_tool == "rotate":
                    self._rotate_base_angle = self._rotate_current_angle
                self.is_transforming = False
                # 发出变换结束信号
                self.transform_ended.emit(active_tool, list(self.selected_indices))
                self._active_drag_tool = None  # 清除
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

    def _show_context_menu(self, global_pos):
        """显示右键菜单"""
        menu = QMenu(self)
        has_selection = bool(self.selected_indices)
        has_contours = bool(self.contours)

        # ---- 选中时的操作 ----
        if has_selection:
            # 删除
            act_delete = menu.addAction(self.tr("Delete"))
            act_delete.setShortcut(QKeySequence(Qt.Key.Key_Delete))
            act_delete.triggered.connect(
                lambda: self.delete_requested.emit(list(self.selected_indices)))

            menu.addSeparator()

            # 镜像
            mirror_menu = menu.addMenu(self.tr("Mirror"))
            act_mirror_x = mirror_menu.addAction(self.tr("Mirror X"))
            act_mirror_x.triggered.connect(lambda: self.mirror_requested.emit("x"))
            act_mirror_y = mirror_menu.addAction(self.tr("Mirror Y"))
            act_mirror_y.triggered.connect(lambda: self.mirror_requested.emit("y"))

            menu.addSeparator()

        # ---- 通用操作 ----
        # 全选
        act_select_all = menu.addAction(self.tr("Select All"))
        act_select_all.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_A))
        act_select_all.setEnabled(has_contours)
        act_select_all.triggered.connect(self._select_all)

        menu.addSeparator()

        # 适应视图
        act_fit = menu.addAction(self.tr("Fit View"))
        act_fit.setEnabled(has_contours)
        act_fit.triggered.connect(self.fit_view_requested.emit)

        # 重置视图
        act_reset = menu.addAction(self.tr("Reset View"))
        act_reset.triggered.connect(self.reset_view_requested.emit)

        menu.exec(global_pos)

    def _select_all(self):
        """全选所有轮廓"""
        self.set_selected_indices(list(range(len(self.contours))))

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
            self.set_selected_indices([])
        elif event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # 全选
            self._select_all()
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            # 方向键移动选中的轮廓
            if self.selected_indices:
                # Shift键：大步移动（10mm），普通：小步移动（1mm）
                step = 10.0 if Qt.KeyboardModifier.ShiftModifier in event.modifiers() else 1.0
                dx, dy = 0.0, 0.0
                if event.key() == Qt.Key.Key_Left:
                    dx = -step
                elif event.key() == Qt.Key.Key_Right:
                    dx = step
                elif event.key() == Qt.Key.Key_Up:
                    dy = step
                elif event.key() == Qt.Key.Key_Down:
                    dy = -step

                # 发出变换信号用于撤销/重做
                self.transform_started.emit("move", list(self.selected_indices))
                self._transform_total_dx = dx
                self._transform_total_dy = dy
                self.move_selected(dx, dy)
                self.transform_ended.emit("move", list(self.selected_indices))

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
            target_indices = self._get_group_member_indices_for_index(selected_idx)

            if Qt.KeyboardModifier.ControlModifier in QApplication.keyboardModifiers():
                # Ctrl+点击：切换选择
                if all(idx in self.selected_indices for idx in target_indices):
                    self.selected_indices = [
                        idx for idx in self.selected_indices
                        if idx not in target_indices
                    ]
                else:
                    existing = set(self.selected_indices)
                    self.selected_indices.extend(
                        idx for idx in target_indices
                        if idx not in existing
                    )
            else:
                # 普通点击：单选
                self.selected_indices = list(target_indices)

            self.set_selected_indices(
                self.selected_indices,
                active_index=selected_idx,
            )
            return

        # 点击空白区域：取消选择
        if Qt.KeyboardModifier.ControlModifier not in QApplication.keyboardModifiers():
            self.set_selected_indices([])

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
