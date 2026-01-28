"""
SignMaker Slicer - 画布工具栏

嵌入在画布区域顶部的工具栏，包含：
- 左侧：撤销/重做、变换工具、镜像、布尔操作、组合操作、视图切换
- 右侧：参数设置下拉菜单
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFrame, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from pathlib import Path


class CanvasToolbar(QWidget):
    """画布工具栏"""

    # 信号
    undo_clicked = Signal()
    redo_clicked = Signal()
    move_clicked = Signal()
    rotate_clicked = Signal()
    scale_clicked = Signal()
    mirror_x_clicked = Signal()
    mirror_y_clicked = Signal()
    intersection_clicked = Signal()
    difference_clicked = Signal()
    group_clicked = Signal()
    ungroup_clicked = Signal()
    view_changed = Signal(str)  # "2d" or "3d"
    slice_clicked = Signal()
    param_toggle_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tool = None
        self.current_view = "2d"
        self._init_ui()
        self._apply_styles()

    def _get_icon_path(self, name: str) -> str:
        """获取图标路径"""
        icon_dir = Path(__file__).parent.parent.parent / "docs" / "images"
        icon_path = icon_dir / name
        if icon_path.exists():
            return str(icon_path)
        return ""

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # ========== 撤销/重做 ==========
        self.btn_undo = self._create_icon_button("撤销.png", "撤销")
        self.btn_undo.clicked.connect(self.undo_clicked.emit)
        layout.addWidget(self.btn_undo)

        self.btn_redo = self._create_icon_button("重做.png", "重做")
        self.btn_redo.clicked.connect(self.redo_clicked.emit)
        layout.addWidget(self.btn_redo)

        layout.addWidget(self._create_separator())

        # ========== 变换工具 ==========
        self.btn_move = self._create_icon_button("move.png", "移动")
        self.btn_move.setCheckable(True)
        self.btn_move.clicked.connect(self._on_move_clicked)
        layout.addWidget(self.btn_move)

        self.btn_rotate = self._create_icon_button("rotate.png", "旋转")
        self.btn_rotate.setCheckable(True)
        self.btn_rotate.clicked.connect(self._on_rotate_clicked)
        layout.addWidget(self.btn_rotate)

        self.btn_scale = self._create_icon_button("scale.png", "缩放")
        self.btn_scale.setCheckable(True)
        self.btn_scale.clicked.connect(self._on_scale_clicked)
        layout.addWidget(self.btn_scale)

        layout.addWidget(self._create_separator())

        # ========== 镜像 ==========
        self.btn_mirror_x = self._create_icon_button("mirror_x.png", "水平镜像")
        self.btn_mirror_x.clicked.connect(self.mirror_x_clicked.emit)
        layout.addWidget(self.btn_mirror_x)

        self.btn_mirror_y = self._create_icon_button("mirror_y.png", "垂直镜像")
        self.btn_mirror_y.clicked.connect(self.mirror_y_clicked.emit)
        layout.addWidget(self.btn_mirror_y)

        layout.addWidget(self._create_separator())

        # ========== 布尔操作 ==========
        self.btn_intersection = self._create_icon_button("交集.png", "交集")
        self.btn_intersection.clicked.connect(self.intersection_clicked.emit)
        layout.addWidget(self.btn_intersection)

        self.btn_difference = self._create_icon_button("差集.png", "差集")
        self.btn_difference.clicked.connect(self.difference_clicked.emit)
        layout.addWidget(self.btn_difference)

        layout.addWidget(self._create_separator())

        # ========== 组合操作 ==========
        self.btn_group = self._create_icon_button("组合.png", "组合")
        self.btn_group.clicked.connect(self.group_clicked.emit)
        layout.addWidget(self.btn_group)

        self.btn_ungroup = self._create_icon_button("split_objects_dark.png", "打散")
        self.btn_ungroup.clicked.connect(self.ungroup_clicked.emit)
        layout.addWidget(self.btn_ungroup)

        layout.addWidget(self._create_separator())

        # ========== 起始点/顺序 ==========
        self.btn_start_point = self._create_icon_button("起始点.png", "起始点")
        layout.addWidget(self.btn_start_point)

        self.btn_order = self._create_icon_button("顺序.png", "打印顺序")
        layout.addWidget(self.btn_order)

        layout.addWidget(self._create_separator())

        # ========== 视图居中 ==========
        self.btn_center = self._create_icon_button("画面中心.png", "居中")
        layout.addWidget(self.btn_center)

        layout.addWidget(self._create_separator())

        # ========== 2D/3D 视图切换 ==========
        self.btn_2d = self._create_text_button("2D")
        self.btn_2d.setCheckable(True)
        self.btn_2d.setChecked(True)
        self.btn_2d.clicked.connect(lambda: self._on_view_changed("2d"))
        layout.addWidget(self.btn_2d)

        self.btn_3d = self._create_text_button("3D")
        self.btn_3d.setCheckable(True)
        self.btn_3d.clicked.connect(lambda: self._on_view_changed("3d"))
        layout.addWidget(self.btn_3d)

        # ========== 弹性空间 ==========
        layout.addStretch(1)

        # ========== 参数设置 ==========
        self.btn_params = QPushButton("▼ 参数设置")
        self.btn_params.setObjectName("paramButton")
        self.btn_params.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_params.clicked.connect(self.param_toggle_clicked.emit)
        layout.addWidget(self.btn_params)

        self.setFixedHeight(36)

    def _create_icon_button(self, icon_name: str, tooltip: str) -> QPushButton:
        """创建图标按钮"""
        btn = QPushButton()
        btn.setObjectName("iconButton")
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        icon_path = self._get_icon_path(icon_name)
        if icon_path:
            btn.setIcon(QIcon(icon_path))
        else:
            # 如果没有图标，使用文字
            btn.setText(tooltip[:2])

        return btn

    def _create_text_button(self, text: str) -> QPushButton:
        """创建文字按钮"""
        btn = QPushButton(text)
        btn.setObjectName("textButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.setStyleSheet("""
            CanvasToolbar {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 4px;
            }

            /* 图标按钮 */
            QPushButton#iconButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                padding: 4px;
            }
            QPushButton#iconButton:hover {
                background-color: #21262D;
            }
            QPushButton#iconButton:pressed {
                background-color: #30363D;
            }
            QPushButton#iconButton:checked {
                background-color: #1F6FEB;
            }

            /* 文字按钮 */
            QPushButton#textButton {
                background-color: transparent;
                color: #8B949E;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#textButton:hover {
                background-color: #21262D;
                color: #C9D1D9;
            }
            QPushButton#textButton:checked {
                background-color: #1F6FEB;
                color: #FFFFFF;
            }

            /* 参数按钮 */
            QPushButton#paramButton {
                background-color: transparent;
                color: #58A6FF;
                border: 1px solid #30363D;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton#paramButton:hover {
                background-color: #21262D;
                border-color: #58A6FF;
            }

            /* 分隔符 */
            QFrame#separator {
                background-color: #30363D;
                margin: 6px 4px;
            }
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

    def _set_tool_checked(self, tool: str):
        """设置工具选中状态"""
        self.current_tool = tool
        self.btn_move.setChecked(tool == "move")
        self.btn_rotate.setChecked(tool == "rotate")
        self.btn_scale.setChecked(tool == "scale")

    def _on_view_changed(self, view: str):
        """视图切换"""
        self.current_view = view
        self.btn_2d.setChecked(view == "2d")
        self.btn_3d.setChecked(view == "3d")
        self.view_changed.emit(view)

    def set_view(self, view: str):
        """设置当前视图"""
        self.current_view = view
        self.btn_2d.setChecked(view == "2d")
        self.btn_3d.setChecked(view == "3d")

    def clear_tool(self):
        """清除工具选择"""
        self.current_tool = None
        self.btn_move.setChecked(False)
        self.btn_rotate.setChecked(False)
        self.btn_scale.setChecked(False)
