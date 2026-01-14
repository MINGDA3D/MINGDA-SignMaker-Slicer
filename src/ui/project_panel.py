"""
SignMaker Slicer - 项目面板组件

显示项目中的轮廓列表，支持：
- 轮廓列表显示
- 选择和排序
- 可见性控制
"""

from __future__ import annotations
from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
    QFrame
)
from PySide6.QtCore import Qt, Signal

from src.core.types import Contour
from .theme import COLORS


class ProjectPanel(QWidget):
    """项目面板"""

    contour_selected = Signal(int)  # 轮廓选中信号
    order_changed = Signal(list)  # 顺序变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        self._contours: List[Contour] = []

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel("项目")
        title.setProperty("heading", True)
        title.setStyleSheet(f"""
            padding: 12px;
            background-color: {COLORS.bg_secondary};
            border-bottom: 1px solid {COLORS.border_default};
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(title)

        # 工具栏
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            background-color: {COLORS.bg_secondary};
            border-bottom: 1px solid {COLORS.border_default};
            padding: 4px;
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(4)

        # 全选按钮
        select_all_btn = QPushButton("全选")
        select_all_btn.setFixedHeight(24)
        select_all_btn.clicked.connect(self._on_select_all)
        toolbar_layout.addWidget(select_all_btn)

        # 反选按钮
        invert_btn = QPushButton("反选")
        invert_btn.setFixedHeight(24)
        invert_btn.clicked.connect(self._on_invert_selection)
        toolbar_layout.addWidget(invert_btn)

        toolbar_layout.addStretch()

        layout.addWidget(toolbar)

        # 轮廓列表
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS.bg_primary};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {COLORS.border_default};
            }}
            QListWidget::item:hover {{
                background-color: {COLORS.bg_hover};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS.bg_selected};
                color: {COLORS.text_primary};
            }}
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.list_widget)

        # 信息区域
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            background-color: {COLORS.bg_secondary};
            border-top: 1px solid {COLORS.border_default};
            padding: 8px;
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(4)

        self.count_label = QLabel("轮廓数量: 0")
        self.count_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 11px;")
        info_layout.addWidget(self.count_label)

        self.selected_label = QLabel("已选择: 0")
        self.selected_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 11px;")
        info_layout.addWidget(self.selected_label)

        layout.addWidget(info_frame)

    def update_contours(self, contours: List[Contour]):
        """更新轮廓列表"""
        self._contours = contours
        self.list_widget.clear()

        for i, contour in enumerate(contours):
            # 计算轮廓信息
            bounds = contour.outer.bounds
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]

            name = contour.name if contour.name else f"轮廓 {i + 1}"
            text = f"{name}\n{width:.1f} × {height:.1f} mm"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.list_widget.addItem(item)

        self.count_label.setText(f"轮廓数量: {len(contours)}")
        self._update_selection_count()

    def _on_item_clicked(self, item: QListWidgetItem):
        """项目点击"""
        index = item.data(Qt.ItemDataRole.UserRole)
        self.contour_selected.emit(index)
        self._update_selection_count()

    def _on_select_all(self):
        """全选"""
        self.list_widget.selectAll()
        self._update_selection_count()

    def _on_invert_selection(self):
        """反选"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setSelected(not item.isSelected())
        self._update_selection_count()

    def _update_selection_count(self):
        """更新选择计数"""
        count = len(self.list_widget.selectedItems())
        self.selected_label.setText(f"已选择: {count}")

    def get_selected_indices(self) -> List[int]:
        """获取选中的索引"""
        indices = []
        for item in self.list_widget.selectedItems():
            index = item.data(Qt.ItemDataRole.UserRole)
            indices.append(index)
        return indices
