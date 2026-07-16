"""Reusable compact selector for the progressive UI complexity level."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QWidget

from src.core.complexity import ComplexityLevel, normalize_complexity_level

from .theme import COLORS


class ComplexitySelector(QWidget):
    """Keyboard-accessible compact menu showing the current UI level."""

    level_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("complexitySelector")
        self._level = ComplexityLevel.BASIC
        self._actions: dict[ComplexityLevel, QAction] = {}
        self._tooltips: dict[ComplexityLevel, str] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.button = QToolButton(self)
        self.button.setObjectName("complexityMenuButton")
        self.button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setFixedHeight(28)
        self.button.setMinimumWidth(92)
        self.button.setMaximumWidth(132)

        self.menu = QMenu(self.button)
        self.menu.setObjectName("complexityMenu")
        self._action_group = QActionGroup(self.menu)
        self._action_group.setExclusive(True)

        for level, text, tooltip in (
            (
                ComplexityLevel.BASIC,
                self.tr("Basic"),
                self.tr("Common production parameters and tools"),
            ),
            (
                ComplexityLevel.ADVANCED,
                self.tr("Advanced"),
                self.tr("Advanced process and editing controls"),
            ),
            (
                ComplexityLevel.EXPERT,
                self.tr("Expert"),
                self.tr("Machine, G-code, and expert geometry controls"),
            ),
        ):
            action = QAction(text, self.menu)
            action.setCheckable(True)
            action.setToolTip(tooltip)
            action.triggered.connect(
                lambda checked=False, selected=level: self._on_level_selected(
                    selected
                )
            )
            self._action_group.addAction(action)
            self.menu.addAction(action)
            self._actions[level] = action
            self._tooltips[level] = tooltip

        self.button.setMenu(self.menu)
        layout.addWidget(self.button)

        self.set_level(ComplexityLevel.BASIC)
        self.apply_theme()

    def level(self) -> ComplexityLevel:
        """Return the selected level."""
        return self._level

    def set_level(self, level: object) -> None:
        """Select a level without emitting ``level_changed``."""
        normalized = normalize_complexity_level(level)
        self._level = normalized
        action = self._actions[normalized]
        action.setChecked(True)
        self.button.setText(action.text())
        self.button.setToolTip(self._tooltips[normalized])
        self.button.setAccessibleName(action.text())

    def _on_level_selected(self, level: ComplexityLevel) -> None:
        normalized = normalize_complexity_level(level)
        if normalized == self._level:
            self.set_level(normalized)
            return
        self.set_level(normalized)
        self.level_changed.emit(normalized)

    def apply_theme(self) -> None:
        """Refresh theme-dependent selector and popup styling."""
        self.setStyleSheet(f"""
            QToolButton#complexityMenuButton {{
                background-color: {COLORS.editor_sidebar_left_bg};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 4px;
                padding: 3px 24px 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QToolButton#complexityMenuButton:hover {{
                background-color: {COLORS.bg_hover};
                color: {COLORS.text_primary};
                border-color: {COLORS.editor_canvas_toolbar_accent};
            }}
            QToolButton#complexityMenuButton:pressed {{
                background-color: {COLORS.bg_selected};
            }}
            QToolButton#complexityMenuButton:focus {{
                border: 2px solid {COLORS.accent_primary};
            }}
            QToolButton#complexityMenuButton::menu-indicator {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                right: 8px;
            }}
            QMenu#complexityMenu {{
                background-color: {COLORS.bg_panel};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu#complexityMenu::item {{
                background-color: transparent;
                padding: 7px 20px 7px 26px;
                border-radius: 4px;
            }}
            QMenu#complexityMenu::item:selected {{
                background-color: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
            QMenu#complexityMenu::indicator {{
                width: 12px;
                height: 12px;
                left: 7px;
            }}
        """)
