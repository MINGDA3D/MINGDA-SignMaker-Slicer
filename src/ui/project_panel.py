"""
MINGDA SignMaker - 项目面板组件

显示项目中的图形列表，支持：
- 图形列表显示（带颜色标识）
- 选择和删除
- 导入图形
"""

from __future__ import annotations
from typing import List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

from src.core.types import Contour
from .theme import COLORS


class ShapeListItem(QFrame):
    """图形列表项"""

    clicked = Signal(int)  # 点击信号
    delete_clicked = Signal(int)  # 删除信号

    # 预定义颜色列表
    COLORS = [
        "#E91E63",  # 粉红
        "#9C27B0",  # 紫色
        "#3F51B5",  # 靛蓝
        "#2196F3",  # 蓝色
        "#00BCD4",  # 青色
        "#4CAF50",  # 绿色
        "#FF9800",  # 橙色
        "#F44336",  # 红色
    ]

    def __init__(self, index: int, name: str, color_index: int = 0, parent=None):
        super().__init__(parent)
        self.index = index
        self.name = name
        self._selected = False
        self._color = self.COLORS[color_index % len(self.COLORS)]
        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(0)

        # 左侧颜色条
        self.color_bar = QFrame()
        self.color_bar.setFixedWidth(4)
        self.color_bar.setStyleSheet(f"background-color: {self._color}; border-radius: 2px;")
        layout.addWidget(self.color_bar)

        # 名称标签
        self.name_label = QLabel(self.name)
        self.name_label.setStyleSheet(f"""
            color: {COLORS.text_primary};
            font-size: 13px;
            padding: 12px;
        """)
        layout.addWidget(self.name_label, 1)

        # 删除按钮
        self.delete_btn = QPushButton()
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setIconSize(QSize(18, 18))

        # 使用图标
        icon_path = Path(__file__).parent.parent.parent / "resources" / "icons" / "delete.png"
        if icon_path.exists():
            self.delete_btn.setIcon(QIcon(str(icon_path)))
        else:
            self.delete_btn.setText("×")

        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.2);
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.index))
        layout.addWidget(self.delete_btn)

        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_styles(self):
        """应用样式"""
        self._update_style()

    def _update_style(self):
        """更新样式"""
        if self._selected:
            self.setStyleSheet(f"""
                ShapeListItem {{
                    background-color: {COLORS.bg_secondary};
                    border: 1px solid #1F6FEB;
                    border-radius: 4px;
                    margin: 2px 4px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ShapeListItem {{
                    background-color: {COLORS.bg_secondary};
                    border: 1px solid {COLORS.border_default};
                    border-radius: 4px;
                    margin: 2px 4px;
                }}
                ShapeListItem:hover {{
                    border-color: {COLORS.border_hover};
                }}
            """)

    def set_selected(self, selected: bool):
        """设置选中状态"""
        self._selected = selected
        self._update_style()

    def is_selected(self) -> bool:
        """是否选中"""
        return self._selected

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


class ProjectPanel(QWidget):
    """项目面板"""

    contour_selected = Signal(int)  # 轮廓选中信号
    contour_deleted = Signal(int)  # 轮廓删除信号
    import_clicked = Signal()  # 导入点击信号
    order_changed = Signal(list)  # 顺序变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        self._contours: List[Contour] = []
        self._items: List[ShapeListItem] = []
        self._selected_index: int = -1

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel(self.tr("Shape List"))
        title.setStyleSheet(f"""
            padding: 12px;
            background-color: {COLORS.bg_primary};
            color: {COLORS.text_primary};
            font-size: 13px;
        """)
        layout.addWidget(title)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS.bg_primary};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS.bg_primary};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS.border_default};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS.border_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        # 列表容器
        self.list_container = QWidget()
        self.list_container.setStyleSheet(f"background-color: {COLORS.bg_primary};")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(4, 4, 4, 4)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()

        scroll_area.setWidget(self.list_container)
        layout.addWidget(scroll_area, 1)

        # 导入按钮
        import_btn = QPushButton(self.tr("+ Import Shape"))
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setFixedHeight(52)
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.bg_secondary};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 4px;
                margin: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bg_hover};
                border-color: {COLORS.border_hover};
                color: {COLORS.text_primary};
            }}
        """)
        import_btn.clicked.connect(self.import_clicked.emit)
        layout.addWidget(import_btn)

    def update_contours(self, contours: List[Contour]):
        """更新轮廓列表"""
        self._contours = contours

        # 清除现有项
        for item in self._items:
            item.deleteLater()
        self._items.clear()

        # 移除stretch
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新项
        for i, contour in enumerate(contours):
            name = contour.name if contour.name else self.tr("Letter-{index}").format(index=i + 1)
            item = ShapeListItem(i, name, i)
            item.clicked.connect(self._on_item_clicked)
            item.delete_clicked.connect(self._on_item_delete)
            self.list_layout.addWidget(item)
            self._items.append(item)

        # 添加stretch
        self.list_layout.addStretch()

        # 更新选中状态
        if self._selected_index >= 0 and self._selected_index < len(self._items):
            self._items[self._selected_index].set_selected(True)

    def _on_item_clicked(self, index: int):
        """项目点击"""
        # 取消之前的选中
        if self._selected_index >= 0 and self._selected_index < len(self._items):
            self._items[self._selected_index].set_selected(False)

        # 选中新项
        self._selected_index = index
        if index >= 0 and index < len(self._items):
            self._items[index].set_selected(True)

        self.contour_selected.emit(index)

    def _on_item_delete(self, index: int):
        """删除项目"""
        self.contour_deleted.emit(index)

    def get_selected_indices(self) -> List[int]:
        """获取选中的索引"""
        if self._selected_index >= 0:
            return [self._selected_index]
        return []

    def set_selected(self, index: int):
        """设置选中项"""
        # 取消之前的选中
        if self._selected_index >= 0 and self._selected_index < len(self._items):
            self._items[self._selected_index].set_selected(False)

        # 选中新项
        self._selected_index = index
        if index >= 0 and index < len(self._items):
            self._items[index].set_selected(True)

    def clear_selection(self):
        """清除选择"""
        if self._selected_index >= 0 and self._selected_index < len(self._items):
            self._items[self._selected_index].set_selected(False)
        self._selected_index = -1
