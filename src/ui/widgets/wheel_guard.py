"""Widgets that ignore mouse-wheel changes until explicitly focused."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class _WheelGuardMixin:
    """Prevent accidental wheel-based value changes while scrolling panels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
            return

        event.ignore()


class GuardedSpinBox(_WheelGuardMixin, QSpinBox):
    """Integer spin box that only reacts to wheel events when focused."""


class GuardedDoubleSpinBox(_WheelGuardMixin, QDoubleSpinBox):
    """Floating-point spin box that only reacts to wheel events when focused."""


class GuardedComboBox(_WheelGuardMixin, QComboBox):
    """Combo box that only reacts to wheel events when focused."""
