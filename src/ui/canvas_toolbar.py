"""MINGDA SignMaker canvas toolbar with progressive complexity."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from src.core.complexity import ComplexityLevel, normalize_complexity_level

from .icon_utils import build_theme_icon
from .theme import COLORS


class CanvasToolbar(QWidget):
    """Centered canvas toolbar backed by actions and Qt overflow handling."""

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
        self.setObjectName("canvasToolbar")
        self.current_tool: str | None = None
        self._complexity_level = ComplexityLevel.BASIC
        self._tool_actions: dict[str, QAction] = {}
        self._tool_levels: dict[str, ComplexityLevel] = {}
        self._group_actions: dict[str, list[QAction]] = {}
        self._group_separators: dict[str, QAction] = {}
        self._icon_actions: list[tuple[QAction, str]] = []
        self._init_ui()
        self._apply_styles()
        self.set_complexity_level(ComplexityLevel.BASIC)

    def _get_icon(self, name: str) -> QIcon:
        icon = build_theme_icon(
            f":/icons/icons/{name}",
            QSize(36, 36),
            light_color=COLORS.accent_primary,
            on_light_color=COLORS.text_on_accent,
            disabled_light_color=COLORS.text_muted,
        )
        disabled_pixmap = self._build_disabled_icon_pixmap(icon)
        if not disabled_pixmap.isNull():
            icon.addPixmap(disabled_pixmap, QIcon.Mode.Disabled, QIcon.State.Off)
            icon.addPixmap(disabled_pixmap, QIcon.Mode.Disabled, QIcon.State.On)
        return icon

    @staticmethod
    def _build_disabled_icon_pixmap(
        icon: QIcon,
        size: QSize = QSize(36, 36),
    ) -> QPixmap:
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
                gray = int(
                    color.red() * 0.299
                    + color.green() * 0.587
                    + color.blue() * 0.114
                )
                color.setRgb(
                    gray,
                    gray,
                    gray,
                    max(0, min(255, int(color.alpha() * 0.55))),
                )
                image.setPixelColor(x, y, color)
        return QPixmap.fromImage(image)

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)
        layout.addStretch(1)

        self._toolbar = QToolBar(self)
        self._toolbar.setObjectName("canvasActionToolbar")
        self._toolbar.setMovable(False)
        self._toolbar.setFloatable(False)
        self._toolbar.setOrientation(Qt.Orientation.Horizontal)
        self._toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._toolbar.setIconSize(QSize(36, 36))
        self._toolbar.setMinimumWidth(0)
        self._toolbar.setFixedHeight(50)
        self._toolbar.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        layout.addWidget(self._toolbar, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

        self._add_group(
            "transform",
            [
                (
                    "move", "btn_move", "move.png", self.tr("Move"),
                    ComplexityLevel.BASIC, self._on_move_clicked, True,
                ),
                (
                    "rotate", "btn_rotate", "rotate.png", self.tr("Rotate"),
                    ComplexityLevel.BASIC, self._on_rotate_clicked, True,
                ),
                (
                    "scale", "btn_scale", "scale.png", self.tr("Scale"),
                    ComplexityLevel.BASIC, self._on_scale_clicked, True,
                ),
            ],
        )
        self._add_group(
            "mirror",
            [
                (
                    "mirror_x", "btn_mirror_x", "mirror_x.png",
                    self.tr("Mirror Horizontal"), ComplexityLevel.BASIC,
                    self.mirror_x_clicked.emit, False,
                ),
                (
                    "mirror_y", "btn_mirror_y", "mirror_y.png",
                    self.tr("Mirror Vertical"), ComplexityLevel.BASIC,
                    self.mirror_y_clicked.emit, False,
                ),
            ],
        )
        self._add_group(
            "boolean",
            [
                (
                    "intersection", "btn_intersection", "intersection.png",
                    self.tr("Intersection"), ComplexityLevel.EXPERT,
                    self.intersection_clicked.emit, False,
                ),
                (
                    "difference", "btn_difference", "difference.png",
                    self.tr("Difference"), ComplexityLevel.EXPERT,
                    self.difference_clicked.emit, False,
                ),
            ],
        )
        self._add_group(
            "grouping",
            [
                (
                    "group", "btn_group", "group.png", self.tr("Group"),
                    ComplexityLevel.ADVANCED, self.group_clicked.emit, False,
                ),
                (
                    "ungroup", "btn_ungroup", "split_objects_dark.png",
                    self.tr("Ungroup"), ComplexityLevel.ADVANCED,
                    self.ungroup_clicked.emit, False,
                ),
                (
                    "release_asset", "btn_release_asset", "explode_asset.svg",
                    self.tr("Explode Asset"), ComplexityLevel.ADVANCED,
                    self.release_asset_clicked.emit, False,
                ),
            ],
        )
        self._add_group(
            "text",
            [
                (
                    "text", "btn_text", "text.svg", self.tr("Text"),
                    ComplexityLevel.BASIC, self.text_clicked.emit, False,
                ),
            ],
        )
        self._add_group(
            "editing",
            [
                (
                    "start_point", "btn_start_point", "start_point.png",
                    self.tr("Start Point"), ComplexityLevel.ADVANCED,
                    self._on_start_point_clicked, True,
                ),
                (
                    "print_order", "btn_order", "print_order.png",
                    self.tr("Print Order"), ComplexityLevel.EXPERT,
                    self._on_print_order_clicked, True,
                ),
                (
                    "screw_hole", "btn_screw_hole", "bottom_hole.png",
                    self.tr("Screw Hole"), ComplexityLevel.ADVANCED,
                    self._on_screw_hole_clicked, True,
                ),
            ],
        )

        self._tool_actions["release_asset"].setEnabled(False)
        self.setFixedHeight(52)

    def _add_group(self, group: str, specs: list[tuple]) -> None:
        if self._group_actions:
            self._group_separators[group] = self._toolbar.addSeparator()
        actions: list[QAction] = []
        for key, attr_name, icon_name, tooltip, level, callback, checkable in specs:
            action = QAction(self._get_icon(icon_name), tooltip, self)
            action.setObjectName(f"canvasToolAction_{key}")
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
            action.setCheckable(checkable)
            action.triggered.connect(
                lambda checked=False, handler=callback: handler()
            )
            self._toolbar.addAction(action)

            button = self._toolbar.widgetForAction(action)
            if isinstance(button, QToolButton):
                button.setObjectName("iconButton")
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setToolTip(tooltip)
                button.setAccessibleName(tooltip)
            setattr(self, attr_name, button)

            self._tool_actions[key] = action
            self._tool_levels[key] = level
            self._icon_actions.append((action, icon_name))
            actions.append(action)
        self._group_actions[group] = actions

    def complexity_level(self) -> ComplexityLevel:
        return self._complexity_level

    def set_complexity_level(self, level: object) -> None:
        """Show all tools available at ``level`` and refresh separators."""
        normalized = normalize_complexity_level(level)
        self._complexity_level = normalized

        current_level = self._tool_levels.get(self.current_tool or "")
        if current_level is not None and current_level > normalized:
            self.clear_tool()

        for key, action in self._tool_actions.items():
            action.setVisible(self._tool_levels[key] <= normalized)

        previous_visible_group = False
        for group, actions in self._group_actions.items():
            group_visible = any(action.isVisible() for action in actions)
            separator = self._group_separators.get(group)
            if separator is not None:
                separator.setVisible(group_visible and previous_visible_group)
            if group_visible:
                previous_visible_group = True
        self._toolbar.updateGeometry()
        self.updateGeometry()

    def visible_tool_keys(self) -> list[str]:
        """Return visible tool keys in toolbar order (primarily for tests)."""
        return [
            key for key, action in self._tool_actions.items()
            if action.isVisible()
        ]

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QWidget#canvasToolbar {{
                background-color: {COLORS.editor_canvas_toolbar_bg};
                border-top: 1px solid {COLORS.editor_canvas_toolbar_accent};
                border-bottom: 1px solid {COLORS.editor_canvas_frame};
                border-left: 1px solid {COLORS.editor_canvas_frame};
                border-right: 1px solid {COLORS.editor_canvas_frame};
            }}
            QToolBar#canvasActionToolbar {{
                background-color: transparent;
                border: none;
                spacing: 8px;
                padding: 5px 0;
            }}
            QToolButton#iconButton,
            QToolButton#qt_toolbar_ext_button {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
                padding: 2px;
            }}
            QToolButton#iconButton:hover,
            QToolButton#qt_toolbar_ext_button:hover {{
                background-color: {COLORS.editor_canvas_bg};
                border-color: {COLORS.editor_canvas_toolbar_accent};
            }}
            QToolButton#iconButton:pressed,
            QToolButton#iconButton:checked {{
                background-color: {COLORS.accent_primary};
                border-color: {COLORS.editor_canvas_toolbar_accent};
            }}
            QToolButton#iconButton:focus,
            QToolButton#qt_toolbar_ext_button:focus {{
                border: 2px solid {COLORS.accent_primary};
            }}
            QToolBar#canvasActionToolbar::separator {{
                background-color: {COLORS.border_hover};
                width: 1px;
                margin: 10px 10px;
            }}
        """)

    def apply_theme(self) -> None:
        for action, icon_name in self._icon_actions:
            action.setIcon(self._get_icon(icon_name))
        self._apply_styles()
        self._toolbar.update()
        self.update()

    def _on_move_clicked(self) -> None:
        self._set_tool_checked("move")
        self.move_clicked.emit()

    def _on_rotate_clicked(self) -> None:
        self._set_tool_checked("rotate")
        self.rotate_clicked.emit()

    def _on_scale_clicked(self) -> None:
        self._set_tool_checked("scale")
        self.scale_clicked.emit()

    def _on_start_point_clicked(self) -> None:
        self._set_tool_checked("start_point")
        self.start_point_clicked.emit()

    def _on_print_order_clicked(self) -> None:
        self._set_tool_checked("print_order")
        self.print_order_clicked.emit()

    def _on_screw_hole_clicked(self) -> None:
        self._set_tool_checked("screw_hole")
        self.screw_hole_clicked.emit()

    def _set_tool_checked(self, tool: str) -> None:
        self.current_tool = tool
        for key in ("move", "rotate", "scale", "start_point", "print_order", "screw_hole"):
            self._tool_actions[key].setChecked(key == tool)

    def clear_tool(self) -> None:
        self.current_tool = None
        for key in ("move", "rotate", "scale", "start_point", "print_order", "screw_hole"):
            self._tool_actions[key].setChecked(False)

    def set_release_asset_enabled(self, enabled: bool) -> None:
        self._tool_actions["release_asset"].setEnabled(enabled)

    def set_screw_hole_enabled(self, enabled: bool) -> None:
        self._tool_actions["screw_hole"].setEnabled(enabled)
        if not enabled:
            self._tool_actions["screw_hole"].setChecked(False)
            if self.current_tool == "screw_hole":
                self.current_tool = None
