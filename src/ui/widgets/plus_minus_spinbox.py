"""
MINGDA SignMaker - Plus/Minus SpinBox Widget

自定义数值输入控件，使用左右布局的 +/- 按钮
布局: [ - ]  输入框  [ + ]
"""

import os
from typing import Union
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QSizePolicy, QLabel
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QDoubleValidator, QIntValidator, QIcon

from src.ui.theme import COLORS, LAYOUT

# 确保资源已加载
try:
    import resources.rc_resources
except ImportError:
    pass


class PlusMinusSpinBox(QWidget):
    """带有左右 +/- 按钮的数值输入控件（浮点数版本）"""

    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 参数
        self._value = 0.0
        self._minimum = 0.0
        self._maximum = 100.0
        self._single_step = 1.0
        self._decimals = 2
        self._suffix = ""
        self._secondary_text = ""

        self._init_ui()
        self._apply_style()
        self._update_display()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 减号按钮 - 使用 SVG 图标
        self._minus_btn = QPushButton()
        self._minus_btn.setIcon(QIcon(":/icons/icons/minus.svg"))
        self._minus_btn.setIconSize(QSize(16, 16))
        self._minus_btn.setFixedSize(28, 28)
        self._minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minus_btn.setAutoRepeat(True)
        self._minus_btn.setAutoRepeatDelay(300)
        self._minus_btn.setAutoRepeatInterval(50)
        self._minus_btn.clicked.connect(self._on_minus)
        layout.addWidget(self._minus_btn)

        # 输入框
        self._line_edit = QLineEdit()
        self._line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._line_edit.setFixedHeight(28)
        self._line_edit.editingFinished.connect(self._on_editing_finished)
        layout.addWidget(self._line_edit)

        self._secondary_label = QLabel(self._line_edit)
        self._secondary_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._secondary_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._secondary_label.hide()

        # 加号按钮 - 使用 SVG 图标
        self._plus_btn = QPushButton()
        self._plus_btn.setIcon(QIcon(":/icons/icons/plus.svg"))
        self._plus_btn.setIconSize(QSize(16, 16))
        self._plus_btn.setFixedSize(28, 28)
        self._plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._plus_btn.setAutoRepeat(True)
        self._plus_btn.setAutoRepeatDelay(300)
        self._plus_btn.setAutoRepeatInterval(50)
        self._plus_btn.clicked.connect(self._on_plus)
        layout.addWidget(self._plus_btn)

    def _apply_style(self):
        """应用样式"""
        # 按钮样式 - 使用 SVG 图标
        btn_style = f"""
            QPushButton {{
                background-color: #3D4850;
                border: 1px solid #5A6570;
            }}
            QPushButton:hover {{
                background-color: {COLORS.accent_primary};
                border-color: {COLORS.accent_primary};
            }}
            QPushButton:pressed {{
                background-color: #79B8FF;
                border-color: #79B8FF;
            }}
            QPushButton:disabled {{
                background-color: {COLORS.bg_panel};
                border-color: {COLORS.border_default};
            }}
        """

        # 减号按钮 - 左侧圆角
        self._minus_btn.setStyleSheet(btn_style + f"""
            QPushButton {{
                border-top-left-radius: {LAYOUT.radius_md}px;
                border-bottom-left-radius: {LAYOUT.radius_md}px;
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
                border-right: none;
            }}
        """)

        # 加号按钮 - 右侧圆角
        self._plus_btn.setStyleSheet(btn_style + f"""
            QPushButton {{
                border-top-right-radius: {LAYOUT.radius_md}px;
                border-bottom-right-radius: {LAYOUT.radius_md}px;
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
                border-left: none;
            }}
        """)

        # 输入框样式 - 无圆角
        self._line_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.bg_primary};
                border: 1px solid #5A6570;
                border-left: none;
                border-right: none;
                border-radius: 0;
                padding: 4px 8px;
                color: {COLORS.text_primary};
                font-family: "Consolas";
            }}
            QLineEdit:hover {{
                border-color: {COLORS.accent_primary};
            }}
            QLineEdit:focus {{
                border-color: {COLORS.accent_primary};
            }}
            QLineEdit:disabled {{
                background-color: {COLORS.bg_secondary};
                color: {COLORS.text_muted};
                border-color: {COLORS.border_default};
            }}
        """)

        self._secondary_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS.text_muted};
                background: transparent;
                padding-right: 8px;
                font-size: 11px;
            }}
        """)

    def _update_secondary_display(self):
        """Update helper text rendered inside the input box."""
        if self._secondary_text:
            self._secondary_label.setText(self._secondary_text)
            self._secondary_label.show()
            reserve = self._secondary_label.fontMetrics().horizontalAdvance(
                self._secondary_text
            ) + 18
            self._line_edit.setTextMargins(8, 0, reserve, 0)
            self._line_edit.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self._secondary_label.setGeometry(
                0, 0, self._line_edit.width(), self._line_edit.height()
            )
        else:
            self._secondary_label.hide()
            self._line_edit.setTextMargins(8, 0, 8, 0)
            self._line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _display_text(self) -> str:
        """Return the canonical text rendered in the line edit."""
        if self._decimals > 0:
            text = f"{self._value:.{self._decimals}f}"
        else:
            text = str(int(self._value))

        if self._suffix:
            text += f" {self._suffix}"
        return text

    def _update_display(self):
        """更新显示"""
        self._line_edit.setText(self._display_text())
        self._update_secondary_display()

        # 更新按钮状态
        self._minus_btn.setEnabled(self._value > self._minimum and self.isEnabled())
        self._plus_btn.setEnabled(self._value < self._maximum and self.isEnabled())

    def _on_minus(self):
        """减少值"""
        new_value = max(self._minimum, self._value - self._single_step)
        if new_value != self._value:
            self._value = new_value
            self._update_display()
            self.valueChanged.emit(self._value)

    def _on_plus(self):
        """增加值"""
        new_value = min(self._maximum, self._value + self._single_step)
        if new_value != self._value:
            self._value = new_value
            self._update_display()
            self.valueChanged.emit(self._value)

    def _on_editing_finished(self):
        """输入完成"""
        self.commit_pending_edit()

    def has_pending_edit(self) -> bool:
        """Return whether the line edit contains an uncommitted value."""
        return self._line_edit.text().strip() != self._display_text()

    def commit_pending_edit(self, emit_signal: bool = True):
        """Commit the current line-edit text into the stored value."""
        text = self._line_edit.text()

        # 移除后缀
        if self._suffix and text.endswith(self._suffix):
            text = text[:-len(self._suffix)]
        text = text.strip()

        try:
            value = float(text)
            value = max(self._minimum, min(self._maximum, value))
            if value != self._value:
                self._value = value
                self._update_display()
                if emit_signal:
                    self.valueChanged.emit(self._value)
            else:
                self._update_display()  # 恢复格式
        except ValueError:
            self._update_display()  # 恢复原值

    # ===== 公共接口 =====

    def value(self) -> float:
        """获取当前值"""
        return self._value

    def setValue(self, value: float):
        """设置值"""
        value = max(self._minimum, min(self._maximum, value))
        if value != self._value:
            self._value = value
            self._update_display()
            self.valueChanged.emit(self._value)
        else:
            self._update_display()

    def minimum(self) -> float:
        return self._minimum

    def setMinimum(self, minimum: float):
        self._minimum = minimum
        if self._value < self._minimum:
            self.setValue(self._minimum)
        else:
            self._update_display()

    def maximum(self) -> float:
        return self._maximum

    def setMaximum(self, maximum: float):
        self._maximum = maximum
        if self._value > self._maximum:
            self.setValue(self._maximum)
        else:
            self._update_display()

    def setRange(self, minimum: float, maximum: float):
        """设置范围"""
        self._minimum = minimum
        self._maximum = maximum
        self._value = max(self._minimum, min(self._maximum, self._value))
        self._update_display()

    def singleStep(self) -> float:
        return self._single_step

    def setSingleStep(self, step: float):
        self._single_step = step

    def decimals(self) -> int:
        return self._decimals

    def setDecimals(self, decimals: int):
        self._decimals = decimals
        self._update_display()

    def suffix(self) -> str:
        return self._suffix

    def setSuffix(self, suffix: str):
        self._suffix = suffix.strip()
        self._update_display()

    def secondaryText(self) -> str:
        """Get helper text rendered inside the input box."""
        return self._secondary_text

    def setSecondaryText(self, text: str):
        """Set helper text rendered inside the input box."""
        self._secondary_text = text.strip()
        self._update_secondary_display()

    def setEnabled(self, enabled: bool):
        """设置启用状态"""
        super().setEnabled(enabled)
        self._minus_btn.setEnabled(enabled and self._value > self._minimum)
        self._plus_btn.setEnabled(enabled and self._value < self._maximum)
        self._line_edit.setEnabled(enabled)
        self._secondary_label.setEnabled(enabled)

    def resizeEvent(self, event):
        """Keep helper text aligned when the widget is resized."""
        super().resizeEvent(event)
        self._update_secondary_display()


class PlusMinusIntSpinBox(PlusMinusSpinBox):
    """整数版本的 Plus/Minus SpinBox"""

    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDecimals(0)
        self.setSingleStep(1)

    def value(self) -> int:
        return int(self._value)

    def setValue(self, value: int):
        super().setValue(float(value))

    def _on_editing_finished(self):
        """输入完成 - 整数版本"""
        self.commit_pending_edit()

    def commit_pending_edit(self, emit_signal: bool = True):
        """Commit the current line-edit text into the stored integer value."""
        text = self._line_edit.text()

        if self._suffix and text.endswith(self._suffix):
            text = text[:-len(self._suffix)]
        text = text.strip()

        try:
            value = int(float(text))
            value = max(int(self._minimum), min(int(self._maximum), value))
            if value != self._value:
                self._value = float(value)
                self._update_display()
                if emit_signal:
                    self.valueChanged.emit(int(self._value))
            else:
                self._update_display()
        except ValueError:
            self._update_display()

    def _on_minus(self):
        """减少值"""
        new_value = max(self._minimum, self._value - self._single_step)
        if new_value != self._value:
            self._value = new_value
            self._update_display()
            self.valueChanged.emit(int(self._value))

    def _on_plus(self):
        """增加值"""
        new_value = min(self._maximum, self._value + self._single_step)
        if new_value != self._value:
            self._value = new_value
            self._update_display()
            self.valueChanged.emit(int(self._value))
