"""
MINGDA SignMaker - 画布工具栏

嵌入在画布区域顶部的工具栏，包含：
- 左侧：变换工具、镜像、布尔操作、组合操作
- 右侧：参数设置下拉菜单
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFrame, QLabel
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap

from .theme import COLORS


class CanvasToolbar(QWidget):
    """画布工具栏"""

    # 信号
    move_clicked = Signal()
    rotate_clicked = Signal()
    scale_clicked = Signal()
    mirror_x_clicked = Signal()
    mirror_y_clicked = Signal()
    intersection_clicked = Signal()
    difference_clicked = Signal()
    group_clicked = Signal()
    ungroup_clicked = Signal()
    release_asset_clicked = Signal()
    text_clicked = Signal()
    start_point_clicked = Signal()
    print_order_clicked = Signal()
    screw_hole_clicked = Signal()
    slice_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tool = None
        self._init_ui()
        self._apply_styles()

    def _get_icon(self, name: str) -> QIcon:
        """获取图标"""
        icon = QIcon(f":/icons/icons/{name}")
        disabled_pixmap = self._build_disabled_icon_pixmap(icon)
        if not disabled_pixmap.isNull():
            icon.addPixmap(disabled_pixmap, QIcon.Mode.Disabled, QIcon.State.Off)
            icon.addPixmap(disabled_pixmap, QIcon.Mode.Disabled, QIcon.State.On)
        return icon

    @staticmethod
    def _build_disabled_icon_pixmap(icon: QIcon, size: QSize = QSize(36, 36)) -> QPixmap:
        """Create a clearly dimmed disabled icon variant."""
        base = icon.pixmap(size, QIcon.Mode.Normal, QIcon.State.Off)
        if base.isNull():
            return base

        image = base.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                if color.alpha() == 0:
                    continue
                gray = int(color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114)
                color.setRgb(gray, gray, gray, max(0, min(255, int(color.alpha() * 0.55))))
                image.setPixelColor(x, y, color)
        return QPixmap.fromImage(image)

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # ========== 左侧弹性空间（居中用）==========
        layout.addStretch(1)

        # ========== 变换工具 ==========
        self.btn_move = self._create_icon_button("move.png", self.tr("Move"))
        self.btn_move.setCheckable(True)
        self.btn_move.clicked.connect(self._on_move_clicked)
        layout.addWidget(self.btn_move)

        self.btn_rotate = self._create_icon_button("rotate.png", self.tr("Rotate"))
        self.btn_rotate.setCheckable(True)
        self.btn_rotate.clicked.connect(self._on_rotate_clicked)
        layout.addWidget(self.btn_rotate)

        self.btn_scale = self._create_icon_button("scale.png", self.tr("Scale"))
        self.btn_scale.setCheckable(True)
        self.btn_scale.clicked.connect(self._on_scale_clicked)
        layout.addWidget(self.btn_scale)

        layout.addWidget(self._create_separator())

        # ========== 镜像 ==========
        self.btn_mirror_x = self._create_icon_button("mirror_x.png", self.tr("Mirror Horizontal"))
        self.btn_mirror_x.clicked.connect(self.mirror_x_clicked.emit)
        layout.addWidget(self.btn_mirror_x)

        self.btn_mirror_y = self._create_icon_button("mirror_y.png", self.tr("Mirror Vertical"))
        self.btn_mirror_y.clicked.connect(self.mirror_y_clicked.emit)
        layout.addWidget(self.btn_mirror_y)

        layout.addWidget(self._create_separator())

        # ========== 布尔操作 ==========
        self.btn_intersection = self._create_icon_button("intersection.png", self.tr("Intersection"))
        self.btn_intersection.clicked.connect(self.intersection_clicked.emit)
        layout.addWidget(self.btn_intersection)

        self.btn_difference = self._create_icon_button("difference.png", self.tr("Difference"))
        self.btn_difference.clicked.connect(self.difference_clicked.emit)
        layout.addWidget(self.btn_difference)

        layout.addWidget(self._create_separator())

        # ========== 组合操作 ==========
        self.btn_group = self._create_icon_button("group.png", self.tr("Group"))
        self.btn_group.clicked.connect(self.group_clicked.emit)
        layout.addWidget(self.btn_group)

        self.btn_ungroup = self._create_icon_button("split_objects_dark.png", self.tr("Ungroup"))
        self.btn_ungroup.clicked.connect(self.ungroup_clicked.emit)
        layout.addWidget(self.btn_ungroup)

        self.btn_release_asset = self._create_icon_button(
            "explode_asset.svg",
            self.tr("Explode Asset"),
        )
        self.btn_release_asset.clicked.connect(self.release_asset_clicked.emit)
        layout.addWidget(self.btn_release_asset)
        self.btn_release_asset.setEnabled(False)

        layout.addWidget(self._create_separator())

        # ========== 文字生成 ==========
        self.btn_text = self._create_icon_button("text.svg", self.tr("Text"))
        self.btn_text.clicked.connect(self.text_clicked.emit)
        layout.addWidget(self.btn_text)

        # ========== 起始点/顺序/视图居中 ==========
        layout.addWidget(self._create_separator())

        self.btn_start_point = self._create_icon_button("start_point.png", self.tr("Start Point"))
        self.btn_start_point.setCheckable(True)
        self.btn_start_point.clicked.connect(self._on_start_point_clicked)
        layout.addWidget(self.btn_start_point)

        self.btn_order = self._create_icon_button("print_order.png", self.tr("Print Order"))
        self.btn_order.setCheckable(True)
        self.btn_order.clicked.connect(self._on_print_order_clicked)
        layout.addWidget(self.btn_order)

        self.btn_screw_hole = self._create_icon_button("bottom_hole.png", self.tr("Screw Hole"))
        self.btn_screw_hole.setCheckable(True)
        self.btn_screw_hole.clicked.connect(self._on_screw_hole_clicked)
        layout.addWidget(self.btn_screw_hole)

        # ========== 右侧弹性空间（居中用）==========
        layout.addStretch(1)

        self.setFixedHeight(52)

    def _create_icon_button(self, icon_name: str, tooltip: str) -> QPushButton:
        """创建图标按钮"""
        btn = QPushButton()
        btn.setObjectName("iconButton")
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIconSize(QSize(36, 36))
        btn.setIcon(self._get_icon(icon_name))
        return btn

    def _create_separator(self) -> QFrame:
        """创建分隔符"""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("separator")
        sep.setFixedWidth(1)
        return sep

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet(f"""
            CanvasToolbar {{
                background-color: {COLORS.editor_canvas_toolbar_bg};
                border-top: 1px solid {COLORS.editor_canvas_toolbar_accent};
                border-bottom: 1px solid {COLORS.editor_canvas_frame};
                border-left: 1px solid {COLORS.editor_canvas_frame};
                border-right: 1px solid {COLORS.editor_canvas_frame};
                border-radius: 0;
            }}

            /* 图标按钮 */
            QPushButton#iconButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
                padding: 2px;
            }}
            QPushButton#iconButton:hover {{
                background-color: {COLORS.editor_canvas_bg};
                border-color: {COLORS.editor_canvas_toolbar_accent};
            }}
            QPushButton#iconButton:disabled {{
                background-color: transparent;
                border-color: transparent;
            }}
            QPushButton#iconButton:pressed {{
                background-color: #30363D;
            }}
            QPushButton#iconButton:checked {{
                background-color: #1F6FEB;
                border-color: {COLORS.editor_canvas_toolbar_accent};
            }}

            /* 分隔符 */
            QFrame#separator {{
                background-color: {COLORS.editor_canvas_toolbar_accent};
                margin: 8px 8px;
            }}
        """)

    def _on_move_clicked(self):
        """移动工具点击"""
        self._set_tool_checked("move")
        self.move_clicked.emit()

    def _on_rotate_clicked(self):
        """旋转工具点击"""
        self._set_tool_checked("rotate")
        self.rotate_clicked.emit()

    def _on_scale_clicked(self):
        """缩放工具点击"""
        self._set_tool_checked("scale")
        self.scale_clicked.emit()

    def _on_start_point_clicked(self):
        """起始点工具点击"""
        self._set_tool_checked("start_point")
        self.start_point_clicked.emit()

    def _on_print_order_clicked(self):
        """打印顺序工具点击"""
        self._set_tool_checked("print_order")
        self.print_order_clicked.emit()

    def _on_screw_hole_clicked(self):
        """Manual screw-hole tool clicked."""
        self._set_tool_checked("screw_hole")
        self.screw_hole_clicked.emit()

    def _set_tool_checked(self, tool: str):
        """设置工具选中状态"""
        self.current_tool = tool
        self.btn_move.setChecked(tool == "move")
        self.btn_rotate.setChecked(tool == "rotate")
        self.btn_scale.setChecked(tool == "scale")
        self.btn_start_point.setChecked(tool == "start_point")
        self.btn_order.setChecked(tool == "print_order")
        self.btn_screw_hole.setChecked(tool == "screw_hole")

    def clear_tool(self):
        """清除工具选择"""
        self.current_tool = None
        self.btn_move.setChecked(False)
        self.btn_rotate.setChecked(False)
        self.btn_scale.setChecked(False)
        self.btn_start_point.setChecked(False)
        self.btn_order.setChecked(False)
        self.btn_screw_hole.setChecked(False)

    def set_release_asset_enabled(self, enabled: bool):
        """Enable explode only when the current selection can use it."""
        self.btn_release_asset.setEnabled(enabled)

    def set_screw_hole_enabled(self, enabled: bool):
        """Enable the manual screw-hole tool only when bottom-face editing is available."""
        self.btn_screw_hole.setEnabled(enabled)
        if not enabled:
            self.btn_screw_hole.setChecked(False)
