"""
MINGDA SignMaker - 参数面板组件

用于设置切片参数的面板，包含：
- 字壳工艺参数
- 换色层设置
- 台阶/V槽设置
- 其他参数分组
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel,
    QComboBox, QCheckBox, QGroupBox, QFrame,
    QPushButton, QFormLayout, QRadioButton, QButtonGroup,
    QSpinBox, QDoubleSpinBox, QAbstractSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QInputDialog,
    QSizePolicy, QMessageBox, QLineEdit, QPlainTextEdit, QTabWidget, QLayout,
    QTabBar,
)
from PySide6.QtCore import Qt, Signal, QCoreApplication, QSize
from PySide6.QtGui import QIcon, QPainter, QColor, QCursor, QFont

from resources import rc_resources  # noqa: F401

from src.core.types import (
    SliceParams, EdgeType, ExtruderType, EdgeDirection, BevelDirection,
    EdgeProfile, PrinterProfile, ColorChangePoint, default_shell_line_width, resolve_shell_line_width,
    height_to_layer_count_up,
    normalize_slice_params,
    resolve_shell_wall_plan,
    snap_height_up_to_layer_grid,
    wall_line_width_limits,
    wall_thickness_limits_for_line_width,
    default_bed_exclude_area_for_bed,
    format_bed_exclude_area_for_editor,
    is_default_bed_exclude_area,
    normalize_bed_exclude_area,
)
from src.core.prime_tower import PrimeTowerGenerator
from src.business.settings_manager import get_settings_manager
from src.business.printer_profile_manager import (
    PrinterProfileManager,
    apply_printer_profile_to_params,
    clone_printer_profile,
    printer_profile_from_params,
)
from src.core.edge_presets import EdgePresetManager, ProfileCategory
from src.ui.widgets import (
    EdgePresetSelector,
    GuardedComboBox,
    GuardedDoubleSpinBox,
    GuardedSpinBox,
)
from .theme import COLORS


class _IconTextTabBar(QTabBar):
    """Draw equal-width tabs with the icon and text centered as one group."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def tabSizeHint(self, index):  # noqa: N802 - Qt override
        size = super().tabSizeHint(index)
        if self.count() > 0 and self.width() > 0:
            size.setWidth(max(1, self.width() // self.count()))
        return size

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        hovered_index = self.tabAt(self.mapFromGlobal(QCursor.pos()))
        icon_size = self.iconSize()
        spacing = 8

        for index in range(self.count()):
            rect = self.tabRect(index)
            selected = index == self.currentIndex()
            hovered = index == hovered_index and not selected

            if hovered:
                painter.fillRect(rect, QColor(COLORS.editor_list_item_bg))

            font = self.font()
            font.setWeight(QFont.Weight.DemiBold if selected else QFont.Weight.Medium)
            painter.setFont(font)
            painter.setPen(QColor(COLORS.text_primary if selected else COLORS.text_muted))

            text = self.tabText(index)
            text_width = painter.fontMetrics().horizontalAdvance(text)
            icon_width = icon_size.width()
            group_width = icon_width + spacing + text_width
            group_x = rect.x() + max(0, (rect.width() - group_width) // 2)
            content_height = max(0, rect.height() - 2)
            icon_y = rect.y() + max(0, (content_height - icon_size.height()) // 2)

            pixmap = self.tabIcon(index).pixmap(icon_size)
            painter.drawPixmap(group_x, icon_y, pixmap)

            text_rect = rect.adjusted(
                group_x + icon_width + spacing - rect.x(),
                0,
                0,
                -2,
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )

            if selected:
                underline_rect = rect.adjusted(0, rect.height() - 2, 0, 0)
                painter.fillRect(underline_rect, QColor(COLORS.editor_canvas_toolbar_accent))


class ParamPanel(QWidget):
    """参数面板"""

    params_changed = Signal()  # 参数变化信号

    TOP_MODE_NONE = 0
    TOP_MODE_FACE = 1
    TOP_MODE_PANEL_STEP = 2
    TOP_MODE_PANEL_V_GROOVE = 3

    BOTTOM_MODE_NONE = 0
    BOTTOM_MODE_FACE = 1
    BOTTOM_MODE_BASEPLATE_STEP = 2
    BOTTOM_MODE_BASEPLATE_V_GROOVE = 3
    BOTTOM_MODE_LIGHT_SLOT = 4
    BOTTOM_MODE_EDGE_WRAP = 5
    BOTTOM_MODE_OUTLINE = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("paramPanel")

        # 参数
        self._params = SliceParams()
        self._profile_manager = PrinterProfileManager()
        self._runtime_profile: Optional[PrinterProfile] = None
        self._runtime_profile_label = self.tr("Project Snapshot")
        self._active_profile_id = ""
        self._updating_profile_ui = False
        self._profile_management_buttons_enabled = False

        # 异形边预设管理器
        self._preset_manager = EdgePresetManager()
        self._current_profile = None

        # 初始化UI
        self._init_ui()
        self._load_initial_printer_profile()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel(self.tr("Settings"))
        title.setProperty("heading", True)
        title.setStyleSheet(f"""
            padding: 12px 12px 12px 14px;
            background-color: {COLORS.editor_sidebar_left_header_bg};
            border-bottom: 1px solid {COLORS.editor_sidebar_left_accent};
            border-left: 4px solid {COLORS.editor_sidebar_left_accent};
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(title)

        # 添加一级参数分组
        self.shell_group = self._create_shell_group()
        self.edge_group = self._create_edge_group()
        self.edge_wrap_group = self._create_edge_wrap_group()
        self.step_group = self._create_step_group()
        self.skirt_group = self._create_skirt_group()
        self.speed_group = self._create_speed_group()
        self.temperature_group = self._create_temperature_group()
        self.cooling_group = self._create_cooling_group()
        self.color_group = self._create_color_group()
        self.prime_tower_group = self._create_prime_tower_group()
        self.top_face_group = self._create_top_face_group()
        self.bottom_face_group = self._create_bottom_face_group()
        self.connected_group = self._create_connected_group()
        self.light_slot_group = self._create_light_slot_group()
        self.printer_profile_group = self._create_printer_profile_group()
        self.klipper_commands_group = self._create_klipper_commands_group()
        self.dxf_export_group = self._create_dxf_export_group()
        self.top_mode_widget = self._create_top_mode_widget()
        self.bottom_mode_widget = self._create_bottom_mode_widget()

        self._primary_groups = [
            self.shell_group,
            self.edge_group,
            self.top_face_group,
            self.panel_step_group,
            self.bottom_face_group,
            self.baseplate_step_group,
            self.light_slot_group,
            self.edge_wrap_group,
            self.skirt_group,
            self.connected_group,
            self.dxf_export_group,
            self.speed_group,
            self.temperature_group,
            self.cooling_group,
            self.color_group,
            self.prime_tower_group,
            self.printer_profile_group,
            self.klipper_commands_group,
        ]

        self._shape_groups = [
            self.shell_group,
            self.edge_group,
            self.top_face_group,
            self.panel_step_group,
            self.bottom_face_group,
            self.baseplate_step_group,
            self.light_slot_group,
            self.edge_wrap_group,
            self.skirt_group,
            self.connected_group,
            self.dxf_export_group,
        ]
        self._vector_groups = self._shape_groups
        self._machine_groups = [
            self.printer_profile_group,
        ]
        self._print_groups = [
            self.speed_group,
            self.temperature_group,
            self.cooling_group,
            self.color_group,
            self.prime_tower_group,
            self.klipper_commands_group,
        ]
        self._primary_sections = [
            {
                "key": "shape",
                "icon": "shape",
                "title": self.tr("Shape"),
                "tooltip": self.tr(
                    "Geometry and sign shell settings"
                ),
                "groups": self._shape_groups,
            },
            {
                "key": "machine",
                "icon": "machine",
                "title": self.tr("Machine"),
                "tooltip": self.tr(
                    "Printer profile and hardware settings"
                ),
                "groups": self._machine_groups,
            },
            {
                "key": "print",
                "icon": "print",
                "title": self.tr("Print"),
                "tooltip": self.tr(
                    "Speed, temperature, cooling, color, and G-code settings"
                ),
                "groups": self._print_groups,
            },
        ]

        self.primary_tabs = QTabWidget()
        self.primary_tabs.setTabBar(_IconTextTabBar(self.primary_tabs))
        self.primary_tabs.setObjectName("primarySettingsTabs")
        self.primary_tabs.setDocumentMode(True)
        self.primary_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.primary_tabs.setUsesScrollButtons(False)
        self.primary_tabs.tabBar().setExpanding(True)
        self.primary_tabs.tabBar().setDrawBase(False)
        self.primary_tabs.setIconSize(QSize(22, 22))
        self.primary_tabs.setStyleSheet(f"""
            QTabWidget#primarySettingsTabs {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
            }}
            QTabWidget#primarySettingsTabs::pane {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
                padding: 0;
                margin: 0;
            }}
            QTabWidget#primarySettingsTabs::tab-bar {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
            }}
            QTabWidget#primarySettingsTabs QTabBar {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
            }}
            QTabWidget#primarySettingsTabs QTabBar::base {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
            }}
            QTabWidget#primarySettingsTabs QTabBar::tab {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
                border-bottom: 2px solid transparent;
                color: {COLORS.text_muted};
                font-size: 12px;
                font-weight: 500;
                min-width: 84px;
                padding: 10px 8px 8px 8px;
            }}
            QTabWidget#primarySettingsTabs QTabBar::tab:selected {{
                background-color: {COLORS.editor_sidebar_left_bg};
                color: {COLORS.text_primary};
                border-bottom: 2px solid {COLORS.editor_canvas_toolbar_accent};
                font-weight: 600;
            }}
            QTabWidget#primarySettingsTabs QTabBar::tab:hover:!selected {{
                background-color: {COLORS.editor_list_item_bg};
                color: {COLORS.text_secondary};
            }}
        """)
        self._primary_tabs = self.primary_tabs
        self._section_widgets = []
        self._section_widgets_by_key = {}
        for section in self._primary_sections:
            if section["key"] == "shape":
                tab_page = self._create_shape_settings_tab_page()
            else:
                tab_page = self._create_settings_tab_page(
                    key=section["key"],
                    groups=section["groups"],
                )
            self._section_widgets.append(tab_page)
            self._section_widgets_by_key[section["key"]] = tab_page
            tab_index = self.primary_tabs.addTab(
                tab_page,
                self._icon(section["icon"]),
                section["title"],
            )
            self.primary_tabs.setTabToolTip(tab_index, section["tooltip"])

        self.primary_tabs.setCurrentIndex(0)
        layout.addWidget(self.primary_tabs, 1)
        self._sync_top_mode_from_controls()
        self._sync_bottom_mode_from_controls()
        self._sync_shape_mode_group_visibility()
        self._sync_layer_based_controls()
        self._update_prime_tower_coordinate_ranges()

    def _create_settings_tab_page(
        self,
        *,
        key: str,
        groups: list[QGroupBox],
    ) -> QScrollArea:
        """Create one scrollable top-level settings tab."""
        scroll = QScrollArea()
        scroll.setObjectName(f"{key}SettingsTab")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea#{scroll.objectName()} {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
            }}
            QScrollArea#{scroll.objectName()} > QWidget > QWidget {{
                background-color: {COLORS.editor_sidebar_left_bg};
            }}
        """)

        content = QWidget()
        content.setObjectName(f"{key}SettingsTabContent")
        content.setStyleSheet(f"background-color: {COLORS.editor_sidebar_left_bg};")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        for group in groups:
            content_layout.addWidget(group)
        content_layout.addStretch()

        scroll.setWidget(content)
        scroll._content = content
        scroll._groups = groups
        return scroll

    def _create_shape_settings_tab_page(self) -> QScrollArea:
        """Create the Shape page with Shell Settings followed by feature tabs."""
        scroll = QScrollArea()
        scroll.setObjectName("shapeSettingsTab")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea#shapeSettingsTab {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
            }}
            QScrollArea#shapeSettingsTab > QWidget > QWidget {{
                background-color: {COLORS.editor_sidebar_left_bg};
            }}
        """)

        content = QWidget()
        content.setObjectName("shapeSettingsTabContent")
        content.setStyleSheet(f"background-color: {COLORS.editor_sidebar_left_bg};")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)
        content_layout.addWidget(self.shell_group)

        self.shape_feature_tabs = QTabWidget()
        self.shape_feature_tabs.setObjectName("shape_feature_tabs")
        self.shape_feature_tabs.setDocumentMode(True)
        self.shape_feature_tabs.setUsesScrollButtons(False)
        self.shape_feature_tabs.tabBar().setExpanding(True)
        self.shape_feature_tabs.tabBar().setDrawBase(False)
        self.shape_feature_tabs.setStyleSheet(f"""
            QTabWidget#shape_feature_tabs {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
            }}
            QTabWidget#shape_feature_tabs::pane {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
                padding-top: 10px;
            }}
            QTabWidget#shape_feature_tabs QTabBar::tab {{
                background-color: {COLORS.editor_sidebar_left_bg};
                border: none;
                border-bottom: 2px solid transparent;
                color: {COLORS.text_muted};
                font-size: 12px;
                font-weight: 500;
                padding: 9px 2px 7px 2px;
            }}
            QTabWidget#shape_feature_tabs QTabBar::tab:selected {{
                color: {COLORS.text_primary};
                border-bottom: 2px solid {COLORS.editor_canvas_toolbar_accent};
                font-weight: 600;
            }}
            QTabWidget#shape_feature_tabs QTabBar::tab:hover:!selected {{
                background-color: {COLORS.editor_list_item_bg};
                color: {COLORS.text_secondary};
            }}
        """)

        self._shape_feature_sections = [
            {
                "key": "wall",
                "title": self.tr("Wall"),
                "mode_widget": None,
                "groups": [self.edge_group],
            },
            {
                "key": "top",
                "title": self.tr("Top"),
                "mode_widget": self.top_mode_widget,
                "groups": [self.top_face_group, self.panel_step_group],
            },
            {
                "key": "bottom",
                "title": self.tr("Bottom"),
                "mode_widget": self.bottom_mode_widget,
                "groups": [
                    self.bottom_face_group,
                    self.baseplate_step_group,
                    self.light_slot_group,
                    self.edge_wrap_group,
                ],
            },
            {
                "key": "other",
                "title": self.tr("Other"),
                "mode_widget": None,
                "groups": [
                    self.skirt_group,
                    self.connected_group,
                    self.dxf_export_group,
                ],
            },
        ]
        self._shape_feature_widgets_by_key = {}
        for section in self._shape_feature_sections:
            page = self._create_feature_tab_content(
                section["key"],
                section["mode_widget"],
                section["groups"],
            )
            self._shape_feature_widgets_by_key[section["key"]] = page
            self.shape_feature_tabs.addTab(page, section["title"])

        content_layout.addWidget(self.shape_feature_tabs)
        content_layout.addStretch()

        scroll.setWidget(content)
        scroll._content = content
        scroll._groups = self._shape_groups
        return scroll

    def _create_feature_tab_content(
        self,
        key: str,
        mode_widget: Optional[QWidget],
        groups: list[QGroupBox],
    ) -> QWidget:
        page = QWidget()
        page.setObjectName(f"shape_{key}_tab_content")
        page.setStyleSheet(f"background-color: {COLORS.editor_sidebar_left_bg};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        if mode_widget is not None:
            layout.addWidget(mode_widget)
        for group in groups:
            layout.addWidget(group)
        layout.addStretch()
        page._groups = groups
        return page

    def _icon(self, name: str) -> QIcon:
        """Load a parameter-panel icon from Qt resources."""
        return QIcon(f":/icons/icons/params/{name}.svg")

    def _icon_label(self, icon_name: str, text: str) -> QWidget:
        """Create a compact form label that keeps the original text discoverable."""
        label_widget = QWidget()
        label_widget.setObjectName("paramIconLabel")
        label_widget.setMinimumWidth(0)
        label_widget.setMaximumWidth(136)
        label_widget.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Preferred,
        )
        label_widget.setToolTip(text)

        row = QHBoxLayout(label_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_label = QLabel()
        icon_label.setObjectName("paramRowIcon")
        icon_label.setFixedSize(24, 24)
        icon_label.setPixmap(self._icon(icon_name).pixmap(24, 24))
        row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        text_label = QLabel(text)
        text_label.setObjectName("paramRowText")
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_label.setWordWrap(True)
        text_label.setMinimumWidth(0)
        text_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        row.addWidget(text_label, 1)

        return label_widget

    def _add_icon_row(
        self,
        form: QFormLayout,
        icon_name: str,
        text: str,
        field: QWidget | QLayout,
    ) -> None:
        """Add a form row with a 24px icon while preserving the visible label text."""
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.addRow(self._icon_label(icon_name, text), field)

    def _create_mode_button_group(
        self,
        object_name: str,
        options: list[tuple[int, str, str]],
        checked_id: int,
    ) -> tuple[QWidget, QButtonGroup, dict[int, QPushButton]]:
        """Create an exclusive icon-button mode selector."""
        container = QWidget()
        container.setObjectName(object_name)
        container.setStyleSheet(f"""
            QPushButton[shapeModeButton="true"] {{
                background-color: {COLORS.editor_list_item_bg};
                border: 1px solid {COLORS.border_default};
                border-radius: 6px;
                padding: 6px;
            }}
            QPushButton[shapeModeButton="true"]:checked {{
                background-color: {COLORS.editor_canvas_toolbar_accent};
                border-color: {COLORS.editor_canvas_toolbar_accent};
            }}
            QPushButton[shapeModeButton="true"]:hover:!checked {{
                border-color: {COLORS.text_muted};
            }}
        """)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        button_group = QButtonGroup(self)
        button_group.setObjectName(f"{object_name}_group")
        button_group.setExclusive(True)

        buttons: dict[int, QPushButton] = {}
        for mode_id, tooltip, icon_name in options:
            button = QPushButton()
            button.setObjectName(f"{object_name}_{mode_id}")
            button.setCheckable(True)
            button.setIcon(self._icon(icon_name))
            button.setIconSize(QSize(22, 22))
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setMinimumHeight(40)
            button.setProperty("shapeModeButton", True)
            layout.addWidget(button)
            button_group.addButton(button, mode_id)
            buttons[mode_id] = button

        if checked_id in buttons:
            buttons[checked_id].setChecked(True)

        return container, button_group, buttons

    def _set_button_group_checked(
        self,
        button_group: QButtonGroup,
        mode_id: int,
    ) -> None:
        button = button_group.button(mode_id)
        if button is None or button.isChecked():
            return
        button_group.blockSignals(True)
        try:
            button.setChecked(True)
        finally:
            button_group.blockSignals(False)

    @staticmethod
    def _set_checked_silent(checkbox: QCheckBox, checked: bool) -> None:
        checkbox.blockSignals(True)
        try:
            checkbox.setChecked(checked)
        finally:
            checkbox.blockSignals(False)

    def _create_top_mode_widget(self) -> QWidget:
        widget, group, buttons = self._create_mode_button_group(
            "top_mode_buttons",
            [
                (self.TOP_MODE_NONE, self.tr("None"), "shape"),
                (self.TOP_MODE_FACE, self.tr("Top Face"), "face-top"),
                (self.TOP_MODE_PANEL_STEP, self.tr("Panel Step"), "step"),
                (self.TOP_MODE_PANEL_V_GROOVE, self.tr("Panel V-Groove"), "bevel"),
            ],
            self.TOP_MODE_NONE,
        )
        self.top_mode_group = group
        self.top_mode_buttons = buttons
        group.idClicked.connect(self._on_top_mode_selected)
        return widget

    def _create_bottom_mode_widget(self) -> QWidget:
        widget, group, buttons = self._create_mode_button_group(
            "bottom_mode_buttons",
            [
                (self.BOTTOM_MODE_NONE, self.tr("None"), "shape"),
                (self.BOTTOM_MODE_FACE, self.tr("Bottom Face"), "face-bottom"),
                (self.BOTTOM_MODE_BASEPLATE_STEP, self.tr("Baseplate Step"), "step"),
                (self.BOTTOM_MODE_BASEPLATE_V_GROOVE, self.tr("Baseplate V-Groove"), "bevel"),
                (self.BOTTOM_MODE_LIGHT_SLOT, self.tr("Light Slot"), "light-slot"),
                (self.BOTTOM_MODE_EDGE_WRAP, self.tr("Edge Wrap"), "wrap"),
                (self.BOTTOM_MODE_OUTLINE, self.tr("Outline"), "outline"),
            ],
            self.BOTTOM_MODE_NONE,
        )
        self.bottom_mode_group = group
        self.bottom_mode_buttons = buttons
        group.idClicked.connect(self._on_bottom_mode_selected)
        return widget

    def _create_double_spinbox(self, decimals: int = 2) -> QDoubleSpinBox:
        """Create a standard floating-point input without custom plus/minus buttons."""
        spinbox = GuardedDoubleSpinBox()
        spinbox.setDecimals(decimals)
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setKeyboardTracking(False)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return spinbox

    def _create_int_spinbox(self) -> QSpinBox:
        """Create a standard integer input without custom plus/minus buttons."""
        spinbox = GuardedSpinBox()
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setKeyboardTracking(False)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return spinbox

    def _parameter_tooltip(self, meaning: str, requirements: str) -> str:
        """Build a consistent two-part tooltip for parameter inputs."""
        return self.tr("Meaning: {meaning}\nInput requirements: {requirements}").format(
            meaning=meaning,
            requirements=requirements,
        )

    def _z_height_tooltip(self, meaning: str, minimum: float, maximum: float) -> str:
        """Build a tooltip for Z-height values that snap to the layer grid."""
        return self._parameter_tooltip(
            meaning,
            self.tr(
                "{minimum:.2f}-{maximum:.2f} mm. This value is rounded up to the current "
                "layer-height grid before preview, STL export, and G-code export. "
                "Example: 1.0 mm at 0.3 mm layer height becomes 1.2 mm."
            ).format(minimum=minimum, maximum=maximum),
        )

    def _configure_z_height_spin(
        self,
        spinbox: QDoubleSpinBox,
        minimum: float,
        maximum: float,
        value: float,
        enabled: bool = True,
        meaning: Optional[str] = None,
    ) -> None:
        """Initialize a printable Z-height spinbox in millimeters."""
        spinbox.setRange(minimum, maximum)
        spinbox.setValue(value)
        spinbox.setSingleStep(0.1)
        spinbox.setSuffix(" mm")
        spinbox.setEnabled(enabled)
        spinbox.setToolTip(
            self._z_height_tooltip(
                meaning or self.tr("Z-height used by this feature."),
                minimum,
                maximum,
            )
        )

    def _current_layer_height(self) -> float:
        """Return the currently selected layer height."""
        if hasattr(self, "layer_height_spin"):
            return max(self.layer_height_spin.value(), 0.001)
        return 0.3

    def _current_nozzle_diameter(self) -> float:
        """Return the currently selected nozzle diameter."""
        if hasattr(self, "profile_nozzle_diameter"):
            return max(self.profile_nozzle_diameter.value(), 0.001)
        return max(self._params.machine.nozzle_diameter, 0.001)

    def _derived_width_line(self, layer_height: Optional[float] = None) -> float:
        """Return the default width line for the given layer height."""
        effective_layer_height = self._current_layer_height() if layer_height is None else layer_height
        line_width = default_shell_line_width(effective_layer_height)
        min_line_width, max_line_width = wall_line_width_limits(
            self._current_nozzle_diameter(),
            effective_layer_height,
        )
        return min(max(line_width, min_line_width), max_line_width)

    def _height_to_layers(self, height_mm: float, minimum: int = 1) -> int:
        """Convert a mm height to the next printable layer count."""
        return height_to_layer_count_up(
            height_mm,
            self._current_layer_height(),
            minimum=minimum,
        )

    def _snapped_height(self, height_mm: float, minimum_layers: int = 0) -> float:
        """Return the next printable mm value for a Z-height setting."""
        return snap_height_up_to_layer_grid(
            height_mm,
            self._current_layer_height(),
            minimum_layers=minimum_layers,
        )

    def _set_spin_value_silent(self, spinbox: QAbstractSpinBox, value: float) -> None:
        """Set a spinbox value without emitting valueChanged."""
        spinbox.blockSignals(True)
        try:
            spinbox.setValue(value)
        finally:
            spinbox.blockSignals(False)

    def _snap_spinbox_to_layer_grid(
        self,
        spinbox: QDoubleSpinBox,
        minimum_layers: int = 0,
    ) -> None:
        snapped = self._snapped_height(spinbox.value(), minimum_layers)
        snapped = min(max(snapped, spinbox.minimum()), spinbox.maximum())
        if not math.isclose(spinbox.value(), snapped, abs_tol=1e-9):
            self._set_spin_value_silent(spinbox, snapped)

    def _sync_wall_thickness_step(self) -> None:
        """Use the current line width as the natural wall-thickness increment."""
        if hasattr(self, "width_line_spin") and hasattr(self, "wall_thickness_spin"):
            self.wall_thickness_spin.setSingleStep(
                max(float(self.width_line_spin.value()), 0.01)
            )
            self._sync_wall_tooltips()

    def _sync_wall_tooltips(self) -> None:
        """Refresh tooltips whose valid ranges depend on nozzle, layer height, or line width."""
        if hasattr(self, "width_line_spin"):
            min_line_width, max_line_width = wall_line_width_limits(
                self._current_nozzle_diameter(),
                self._current_layer_height(),
            )
            self.width_line_spin.setToolTip(
                self._parameter_tooltip(
                    self.tr("Actual extrusion width used for each shell wall path."),
                    self.tr(
                        "Current printable range: {minimum:.2f}-{maximum:.2f} mm. "
                        "Formula: min = max(0.75 * nozzle diameter, 1.20 * layer height); "
                        "max = 1.50 * nozzle diameter. Values outside this range block slicing and export."
                    ).format(minimum=min_line_width, maximum=max_line_width),
                )
            )

        if hasattr(self, "width_line_spin") and hasattr(self, "wall_thickness_spin"):
            min_wall_thickness, max_wall_thickness = wall_thickness_limits_for_line_width(
                self.width_line_spin.value()
            )
            self.wall_thickness_spin.setToolTip(
                self._parameter_tooltip(
                    self.tr("Final total XY shell wall thickness."),
                    self.tr(
                        "Valid printable range for the current Line Width: {minimum:.2f}-{maximum:.2f} mm. "
                        "The value is rounded up to a whole multiple of Line Width; "
                        "the internal wall path count may not exceed 100. Values above the range block slicing and export."
                    ).format(minimum=min_wall_thickness, maximum=max_wall_thickness),
                )
            )

    def _color_change_height_tooltip(self) -> str:
        return self._parameter_tooltip(
            self.tr("Z height where the printer should run the selected color-change macro."),
            self.tr(
                "{minimum:.2f}-100.00 mm. The value is rounded up to the current layer-height grid before preview and G-code export."
            ).format(minimum=self._current_layer_height()),
        )

    def _sync_color_change_row_tooltips(self) -> None:
        if not hasattr(self, "color_change_table"):
            return
        for row in range(self.color_change_table.rowCount()):
            height_spin = self.color_change_table.cellWidget(row, 0)
            if isinstance(height_spin, QDoubleSpinBox):
                height_spin.setToolTip(self._color_change_height_tooltip())

    def _snap_color_change_rows_to_layer_grid(self) -> None:
        for row in range(self.color_change_table.rowCount()):
            height_spin = self.color_change_table.cellWidget(row, 0)
            if isinstance(height_spin, QDoubleSpinBox):
                self._snap_spinbox_to_layer_grid(height_spin, minimum_layers=1)

    def _snap_z_controls_to_layer_grid(self) -> None:
        """Snap all user-facing Z-height controls to printable millimeters."""
        controls: list[tuple[QDoubleSpinBox, int]] = [
            (self.height_spin, 1),
            (self.baseplate_spin, 0),
            (self.panel_thickness_spin, 0),
            (self.u_arc_height_spin, 1),
            (self.u_bottom_layers_spin, 0),
            (self.panel_step_height, 1),
            (self.baseplate_step_height, 1),
            (self.skirt_height, 1),
            (self.connected_height, 1),
            (self.connected_base_height, 1),
            (self.bottom_face_thickness, 1),
            (self.light_slot_depth, 1),
            (self.light_slot_floor_layers, 1),
            (self.top_face_thickness, 1),
        ]
        for spinbox, minimum_layers in controls:
            self._snap_spinbox_to_layer_grid(spinbox, minimum_layers)
        self._snap_color_change_rows_to_layer_grid()
        self._update_color_change_summary()

    def _sync_layer_based_controls(self):
        """Refresh limits and steps for layer-grid-aligned millimeter parameters."""
        if not hasattr(self, "layer_height_spin"):
            return

        layer_height = self._current_layer_height()

        for name in (
            "height_spin",
            "baseplate_spin",
            "panel_thickness_spin",
            "u_arc_height_spin",
            "u_bottom_layers_spin",
            "bottom_face_thickness",
            "light_slot_depth",
            "light_slot_floor_layers",
            "top_face_thickness",
            "skirt_height",
        ):
            widget = getattr(self, name, None)
            if isinstance(widget, QDoubleSpinBox):
                widget.setSingleStep(layer_height)

        if hasattr(self, "panel_step_height") and hasattr(self, "baseplate_step_height"):
            self._update_step_ranges()
            self.panel_step_height.setSingleStep(layer_height)
            self.baseplate_step_height.setSingleStep(layer_height)

        if hasattr(self, "connected_height") and hasattr(self, "connected_base_height"):
            self.connected_height.setSingleStep(layer_height)
            self.connected_base_height.setSingleStep(layer_height)

        self._sync_wall_tooltips()
        self._sync_color_change_row_tooltips()

    def _on_layer_height_changed(self, value: float):
        """Keep Line Width synced to the current Layer Height."""
        if hasattr(self, "width_line_spin"):
            self.width_line_spin.blockSignals(True)
            self.width_line_spin.setValue(self._derived_width_line(value))
            self.width_line_spin.blockSignals(False)
        self._sync_wall_thickness_step()
        self._sync_layer_based_controls()
        self._snap_z_controls_to_layer_grid()
        self._on_param_changed()

    def _on_line_width_changed(self, _value: float = 0.0):
        """Handle actual line-width changes before resolving wall thickness."""
        self._sync_wall_thickness_step()
        self._on_param_changed()

    def _create_shell_group(self) -> QGroupBox:
        """创建字壳工艺参数组"""
        group = QGroupBox(self.tr("Shell Settings"))
        layout = QFormLayout(group)
        layout.setSpacing(8)

        # 字壳高度
        self.height_spin = self._create_double_spinbox()
        self.height_spin.setRange(0.1, 100.0)
        self.height_spin.setValue(50.0)
        self.height_spin.setSingleStep(0.1)
        self.height_spin.setSuffix(" mm")
        self.height_spin.setToolTip(
            self._z_height_tooltip(
                self.tr("Total printed height of the sign shell."),
                0.1,
                100.0,
            )
        )
        self.height_spin.valueChanged.connect(self._on_param_changed)
        self.height_spin.valueChanged.connect(self._update_step_ranges)
        self._add_icon_row(layout, "height", self.tr("Shell Height:"), self.height_spin)

        # 层高
        self.layer_height_spin = self._create_double_spinbox()
        self.layer_height_spin.setRange(0.1, 1.0)
        self.layer_height_spin.setValue(0.3)
        self.layer_height_spin.setSingleStep(0.05)
        self.layer_height_spin.setSuffix(" mm")
        self.layer_height_spin.setToolTip(
            self._parameter_tooltip(
                self.tr("Vertical thickness of each printed layer; it also defines the Z snapping grid."),
                self.tr(
                    "0.10-1.00 mm. Smaller values improve vertical detail and increase print time. "
                    "Changing this value rounds Z-height parameters up to the new grid and recomputes the default Line Width."
                ),
            )
        )
        self.layer_height_spin.valueChanged.connect(self._on_layer_height_changed)
        self._add_icon_row(layout, "layer", self.tr("Layer Height:"), self.layer_height_spin)

        # 线宽
        self.width_line_spin = self._create_double_spinbox()
        self.width_line_spin.setRange(0.1, 3.0)
        self.width_line_spin.setValue(self._derived_width_line())
        self.width_line_spin.setSingleStep(0.05)
        self.width_line_spin.setSuffix(" mm")
        self.width_line_spin.valueChanged.connect(self._on_line_width_changed)
        self._add_icon_row(layout, "line-width", self.tr("Line Width:"), self.width_line_spin)

        # 壁数量
        self.wall_thickness_spin = self._create_double_spinbox()
        self.wall_thickness_spin.setRange(0.1, 300.0)
        self.wall_thickness_spin.setValue(1.2)
        self.wall_thickness_spin.setSingleStep(self.width_line_spin.value())
        self.wall_thickness_spin.setSuffix(" mm")
        self.wall_thickness_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "wall", self.tr("Wall Thickness:"), self.wall_thickness_spin)
        self._sync_wall_tooltips()

        return group

    def _create_edge_group(self) -> QGroupBox:
        """创建边缘类型参数组"""
        group = QGroupBox(self.tr("Edge Type"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 边缘类型选择
        self.edge_type_combo = GuardedComboBox()
        self.edge_type_combo.setObjectName("edge_type_combo")
        self.edge_type_combo.addItem(self.tr("Straight"), EdgeType.STRAIGHT)
        self.edge_type_combo.addItem(self.tr("Beveled"), EdgeType.BEVELED)
        self.edge_type_combo.addItem(self.tr("U Shape"), EdgeType.U_SHAPED)
        self.edge_type_combo.addItem(self.tr("Custom"), EdgeType.CUSTOM)
        self.edge_type_combo.setVisible(False)
        self.edge_type_combo.currentIndexChanged.connect(self._on_edge_type_changed)
        self.wall_mode_widget, self.wall_mode_group, self.wall_mode_buttons = self._create_mode_button_group(
            "wall_mode_buttons",
            [
                (0, self.tr("Straight"), "wall"),
                (1, self.tr("Beveled"), "bevel"),
                (2, self.tr("U Shape"), "arc"),
                (3, self.tr("Custom"), "profile"),
            ],
            0,
        )
        self._wall_mode_edge_types = {
            0: EdgeType.STRAIGHT,
            1: EdgeType.BEVELED,
            2: EdgeType.U_SHAPED,
            3: EdgeType.CUSTOM,
        }
        self.wall_mode_group.idClicked.connect(self._on_wall_mode_selected)
        layout.addWidget(self.wall_mode_widget)

        # ===== 斜边参数容器 =====
        self.bevel_params_widget = QWidget()
        bevel_layout = QFormLayout(self.bevel_params_widget)
        bevel_layout.setContentsMargins(0, 8, 0, 0)
        bevel_layout.setSpacing(8)

        # 斜边方向
        self.bevel_direction_combo = GuardedComboBox()
        self.bevel_direction_combo.addItem(self.tr("Top Small"), BevelDirection.TOP_SMALL)
        self.bevel_direction_combo.addItem(self.tr("Top Large"), BevelDirection.TOP_LARGE)
        self.bevel_direction_combo.currentIndexChanged.connect(self._on_param_changed)
        self._add_icon_row(bevel_layout, "direction", self.tr("Bevel Direction:"), self.bevel_direction_combo)

        self.bevel_direction_hint = QLabel(
            self.tr("Original contour is always based on the bottom face (z=0).")
        )
        self.bevel_direction_hint.setWordWrap(True)
        self.bevel_direction_hint.setStyleSheet("color: #8B949E; font-size: 12px;")
        bevel_layout.addRow("", self.bevel_direction_hint)

        # 斜边宽度
        self.bevel_width_spin = self._create_double_spinbox()
        self.bevel_width_spin.setRange(0, 50)
        self.bevel_width_spin.setValue(5)
        self.bevel_width_spin.setSuffix(" mm")
        self.bevel_width_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(bevel_layout, "bevel", self.tr("Bevel Width:"), self.bevel_width_spin)

        # 底板厚度
        self.baseplate_spin = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.baseplate_spin,
            0.0,
            50.0,
            9.0,
            meaning=self.tr("Straight bottom section height used for the baseplate side of the shell."),
        )
        self.baseplate_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(bevel_layout, "baseplate", self.tr("Baseplate Thickness:"), self.baseplate_spin)

        # 面板厚度
        self.panel_thickness_spin = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.panel_thickness_spin,
            0.0,
            20.0,
            9.0,
            meaning=self.tr("Straight top section height reserved for the face panel side of the shell."),
        )
        self.panel_thickness_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(bevel_layout, "panel", self.tr("Panel Thickness:"), self.panel_thickness_spin)

        layout.addWidget(self.bevel_params_widget)
        self.bevel_params_widget.setVisible(False)

        # ===== U形边参数容器 =====
        self.u_shape_params_widget = QWidget()
        u_shape_layout = QFormLayout(self.u_shape_params_widget)
        u_shape_layout.setContentsMargins(0, 8, 0, 0)
        u_shape_layout.setSpacing(8)

        self.u_arc_height_spin = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.u_arc_height_spin,
            0.1,
            50.0,
            6.0,
            meaning=self.tr("Vertical height of the curved U-shaped edge profile."),
        )
        self.u_arc_height_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(u_shape_layout, "arc", self.tr("Arc Height:"), self.u_arc_height_spin)

        self.u_bottom_layers_spin = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.u_bottom_layers_spin,
            0.0,
            30.0,
            0.9,
            meaning=self.tr("Solid bottom thickness under the U-shaped profile."),
        )
        self.u_bottom_layers_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(u_shape_layout, "face-bottom", self.tr("Bottom Solid Thickness:"), self.u_bottom_layers_spin)

        layout.addWidget(self.u_shape_params_widget)
        self.u_shape_params_widget.setVisible(False)

        # ===== 异形边参数容器 =====
        self.custom_edge_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_edge_widget)
        custom_layout.setContentsMargins(0, 8, 0, 0)
        custom_layout.setSpacing(8)

        # 预设模板标签
        preset_label = QLabel(self.tr("Preset Templates:"))
        preset_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        custom_layout.addWidget(preset_label)

        # 预设图片选择器
        self.preset_selector = EdgePresetSelector()
        self.preset_selector.setMinimumHeight(200)
        self.preset_selector.preset_selected.connect(self._on_preset_changed)
        custom_layout.addWidget(self.preset_selector)

        # 导入DXF按钮
        btn_layout = QHBoxLayout()
        self.import_dxf_btn = QPushButton(self.tr("Import DXF..."))
        self.import_dxf_btn.setToolTip(self.tr("Import custom edge profile from DXF file"))
        self.import_dxf_btn.clicked.connect(self._on_import_dxf)
        btn_layout.addWidget(self.import_dxf_btn)
        btn_layout.addStretch()
        custom_layout.addLayout(btn_layout)

        # 当前轮廓信息
        info_layout = QFormLayout()
        self.profile_info_label = QLabel(self.tr("No profile selected"))
        self.profile_info_label.setStyleSheet("color: #888;")
        self._add_icon_row(info_layout, "profile", self.tr("Current Profile:"), self.profile_info_label)
        custom_layout.addLayout(info_layout)

        layout.addWidget(self.custom_edge_widget)
        self.custom_edge_widget.setVisible(False)

        default_edge_index = self.edge_type_combo.findData(EdgeType.STRAIGHT)
        if default_edge_index >= 0:
            self.edge_type_combo.blockSignals(True)
            self.edge_type_combo.setCurrentIndex(default_edge_index)
            self.edge_type_combo.blockSignals(False)
            self.bevel_params_widget.setVisible(False)

        return group

    def _create_dxf_export_group(self) -> QGroupBox:
        """创建 DXF 导出补偿参数组"""
        group = QGroupBox(self.tr("DXF Export"))
        layout = QFormLayout(group)
        layout.setSpacing(8)

        self.dxf_outer_clearance_spin = self._create_double_spinbox()
        self.dxf_outer_clearance_spin.setRange(0, 10)
        self.dxf_outer_clearance_spin.setValue(1.0)
        self.dxf_outer_clearance_spin.setSingleStep(0.1)
        self.dxf_outer_clearance_spin.setSuffix(" mm")
        self.dxf_outer_clearance_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "clearance", self.tr("Outer Clearance:"), self.dxf_outer_clearance_spin)

        self.dxf_hole_clearance_spin = self._create_double_spinbox()
        self.dxf_hole_clearance_spin.setRange(0, 10)
        self.dxf_hole_clearance_spin.setValue(1.0)
        self.dxf_hole_clearance_spin.setSingleStep(0.1)
        self.dxf_hole_clearance_spin.setSuffix(" mm")
        self.dxf_hole_clearance_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "clearance", self.tr("Hole Clearance:"), self.dxf_hole_clearance_spin)

        self.dxf_laser_kerf_spin = self._create_double_spinbox()
        self.dxf_laser_kerf_spin.setRange(0, 2)
        self.dxf_laser_kerf_spin.setValue(0.0)
        self.dxf_laser_kerf_spin.setSingleStep(0.01)
        self.dxf_laser_kerf_spin.setSuffix(" mm")
        self.dxf_laser_kerf_spin.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "kerf", self.tr("Laser Kerf:"), self.dxf_laser_kerf_spin)

        return group

    def _create_bottom_face_group(self) -> QGroupBox:
        """创建底面封闭参数组"""
        group = QGroupBox(self.tr("Bottom Face"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.bottom_face_enabled = QCheckBox(self.tr("Enable Bottom Face"))
        self.bottom_face_enabled.setObjectName("bottom_face_enabled")
        self.bottom_face_enabled.setVisible(False)
        self.bottom_face_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.bottom_face_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        # 底面厚度
        self.bottom_face_thickness = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.bottom_face_thickness,
            0.1,
            10.0,
            0.9,
            enabled=False,
            meaning=self.tr("Printed solid bottom face thickness used to close the shell bottom."),
        )
        self.bottom_face_thickness.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "face-bottom", self.tr("Bottom Face Thickness:"), self.bottom_face_thickness)

        self.bottom_face_screw_hole_diameter = self._create_double_spinbox()
        self.bottom_face_screw_hole_diameter.setRange(0.1, 100.0)
        self.bottom_face_screw_hole_diameter.setSingleStep(0.5)
        self.bottom_face_screw_hole_diameter.setSuffix(" mm")
        self.bottom_face_screw_hole_diameter.setValue(5.0)
        self.bottom_face_screw_hole_diameter.setEnabled(False)
        self.bottom_face_screw_hole_diameter.setToolTip(
            self._parameter_tooltip(
                self.tr("Diameter of screw holes generated in the bottom face."),
                self.tr("0.10-100.00 mm. Use a value larger than the screw shaft and smaller than nearby wall spacing."),
            )
        )
        self.bottom_face_screw_hole_diameter.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "screw-hole", self.tr("Screw Hole Diameter:"), self.bottom_face_screw_hole_diameter)

        layout.addLayout(form)

        # 启用/禁用控件联动
        self.bottom_face_enabled.stateChanged.connect(
            lambda: self._toggle_bottom_face_controls(self.bottom_face_enabled.isChecked())
        )
        # 与 Baseplate Step (Bottom) 互斥
        self.bottom_face_enabled.stateChanged.connect(self._on_bottom_face_toggled)
        self.bottom_face_enabled.stateChanged.connect(self._sync_bottom_mode_from_controls)
        self._sync_bottom_face_availability()

        return group

    def _on_bottom_face_toggled(self):
        """底面封闭启用时，自动关闭底板台阶（互斥）"""
        if self.bottom_face_enabled.isChecked() and hasattr(self, 'baseplate_step_enabled'):
            if self.baseplate_step_enabled.isChecked():
                self.baseplate_step_enabled.blockSignals(True)
                self.baseplate_step_enabled.setChecked(False)
                self._toggle_baseplate_step_controls(False)
                self.baseplate_step_enabled.blockSignals(False)
                self._on_param_changed()

    def _on_baseplate_step_toggled(self):
        """底板台阶启用时，自动关闭冲突的底部结构。"""
        if self.baseplate_step_enabled.isChecked() and hasattr(self, 'bottom_face_enabled'):
            if self.bottom_face_enabled.isChecked():
                self.bottom_face_enabled.blockSignals(True)
                self.bottom_face_enabled.setChecked(False)
                self._toggle_bottom_face_controls(False)
                self.bottom_face_enabled.blockSignals(False)
                self._on_param_changed()
        if self.baseplate_step_enabled.isChecked() and hasattr(self, 'light_slot_enabled'):
            if self.light_slot_enabled.isChecked():
                self.light_slot_enabled.blockSignals(True)
                self.light_slot_enabled.setChecked(False)
                self._toggle_light_slot_controls(False)
                self.light_slot_enabled.blockSignals(False)
                self._on_param_changed()

    def _is_u_shape_edge_selected(self) -> bool:
        return (
            hasattr(self, "edge_type_combo")
            and self.edge_type_combo.currentData() == EdgeType.U_SHAPED
        )

    def _sync_bottom_face_availability(self) -> None:
        """Apply edge-type restrictions to explicit bottom-face controls."""
        if not hasattr(self, "bottom_face_enabled"):
            return

        is_u_shape = self._is_u_shape_edge_selected()
        if is_u_shape and self.bottom_face_enabled.isChecked():
            self.bottom_face_enabled.blockSignals(True)
            self.bottom_face_enabled.setChecked(False)
            self.bottom_face_enabled.blockSignals(False)

        self.bottom_face_enabled.setEnabled(not is_u_shape)
        if hasattr(self, "bottom_mode_buttons"):
            self.bottom_mode_buttons[self.BOTTOM_MODE_FACE].setEnabled(not is_u_shape)
        self._toggle_bottom_face_controls(self.bottom_face_enabled.isChecked())
        self._sync_bottom_mode_from_controls()

    def _toggle_bottom_face_controls(self, enabled: bool):
        """切换底面封闭控件的启用状态"""
        enabled = enabled and not self._is_u_shape_edge_selected()
        self.bottom_face_thickness.setEnabled(enabled)
        self.bottom_face_screw_hole_diameter.setEnabled(enabled)

    def _create_light_slot_group(self) -> QGroupBox:
        """创建灯槽参数组"""
        group = QGroupBox(self.tr("Light Slot"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.light_slot_enabled = QCheckBox(self.tr("Enable Light Slot"))
        self.light_slot_enabled.setObjectName("light_slot_enabled")
        self.light_slot_enabled.setVisible(False)
        self.light_slot_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.light_slot_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        self.light_slot_width = self._create_double_spinbox()
        self.light_slot_width.setRange(0.5, 50.0)
        self.light_slot_width.setValue(7.8)
        self.light_slot_width.setSingleStep(0.5)
        self.light_slot_width.setSuffix(" mm")
        self.light_slot_width.setEnabled(False)
        self.light_slot_width.setToolTip(
            self._parameter_tooltip(
                self.tr("XY width of the LED light slot cut along eligible contours."),
                self.tr("0.50-50.00 mm. Choose a value that fits the LED strip and leaves enough wall material."),
            )
        )
        self.light_slot_width.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "light-slot", self.tr("Slot Width:"), self.light_slot_width)

        self.light_slot_depth = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.light_slot_depth,
            0.1,
            20.0,
            6.0,
            enabled=False,
            meaning=self.tr("Vertical depth of the light slot from the shell opening side."),
        )
        self.light_slot_depth.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "height", self.tr("Slot Depth:"), self.light_slot_depth)

        self.light_slot_floor_layers = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.light_slot_floor_layers,
            0.1,
            20.0,
            1.5,
            enabled=False,
            meaning=self.tr("Solid material thickness left under the light slot floor."),
        )
        self.light_slot_floor_layers.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "floor", self.tr("Floor Thickness:"), self.light_slot_floor_layers)

        self.light_slot_wall_gap = self._create_double_spinbox()
        self.light_slot_wall_gap.setRange(0.0, 20.0)
        self.light_slot_wall_gap.setValue(0.0)
        self.light_slot_wall_gap.setSingleStep(0.1)
        self.light_slot_wall_gap.setSuffix(" mm")
        self.light_slot_wall_gap.setEnabled(False)
        self.light_slot_wall_gap.setToolTip(
            self._parameter_tooltip(
                self.tr("Extra XY clearance between the light slot and nearby shell walls."),
                self.tr("0.00-20.00 mm. Use 0 for no extra clearance; larger values move slots farther from walls."),
            )
        )
        self.light_slot_wall_gap.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "gap", self.tr("Wall Gap:"), self.light_slot_wall_gap)

        layout.addLayout(form)

        self.light_slot_outer_enabled = QCheckBox(self.tr("Outer Slot"))
        self.light_slot_outer_enabled.setChecked(True)
        self.light_slot_outer_enabled.setEnabled(False)
        self.light_slot_outer_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.light_slot_outer_enabled)

        self.light_slot_hole_enabled = QCheckBox(self.tr("Hole Slot"))
        self.light_slot_hole_enabled.setChecked(True)
        self.light_slot_hole_enabled.setEnabled(False)
        self.light_slot_hole_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.light_slot_hole_enabled)

        self.light_slot_auto_skip_small_holes = QCheckBox(self.tr("Auto Skip Small Holes"))
        self.light_slot_auto_skip_small_holes.setChecked(True)
        self.light_slot_auto_skip_small_holes.setEnabled(False)
        self.light_slot_auto_skip_small_holes.stateChanged.connect(self._on_param_changed)
        self.light_slot_auto_skip_small_holes.stateChanged.connect(
            lambda: self._toggle_light_slot_controls(self.light_slot_enabled.isChecked())
        )
        layout.addWidget(self.light_slot_auto_skip_small_holes)

        min_hole_span_form = QFormLayout()
        min_hole_span_form.setSpacing(8)
        self.light_slot_min_hole_span = self._create_double_spinbox()
        self.light_slot_min_hole_span.setRange(1.0, 100.0)
        self.light_slot_min_hole_span.setValue(12.0)
        self.light_slot_min_hole_span.setSingleStep(0.5)
        self.light_slot_min_hole_span.setSuffix(" mm")
        self.light_slot_min_hole_span.setEnabled(False)
        self.light_slot_min_hole_span.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(min_hole_span_form, "dimension", self.tr("Min Hole Span:"), self.light_slot_min_hole_span)
        layout.addLayout(min_hole_span_form)

        self.light_slot_enabled.stateChanged.connect(
            lambda: self._toggle_light_slot_controls(self.light_slot_enabled.isChecked())
        )
        self.light_slot_enabled.stateChanged.connect(self._on_light_slot_toggled)
        self.light_slot_enabled.stateChanged.connect(self._sync_bottom_mode_from_controls)

        return group

    def _on_light_slot_toggled(self):
        """灯槽启用时自动关闭底板台阶（互斥）。"""
        if self.light_slot_enabled.isChecked() and hasattr(self, 'baseplate_step_enabled'):
            if self.baseplate_step_enabled.isChecked():
                self.baseplate_step_enabled.blockSignals(True)
                self.baseplate_step_enabled.setChecked(False)
                self._toggle_baseplate_step_controls(False)
                self.baseplate_step_enabled.blockSignals(False)
                self._on_param_changed()

    def _toggle_light_slot_controls(self, enabled: bool):
        """切换灯槽控件的启用状态。"""
        self.light_slot_width.setEnabled(enabled)
        self.light_slot_depth.setEnabled(enabled)
        self.light_slot_floor_layers.setEnabled(enabled)
        self.light_slot_wall_gap.setEnabled(enabled)
        self.light_slot_outer_enabled.setEnabled(enabled)
        self.light_slot_hole_enabled.setEnabled(enabled)
        self.light_slot_auto_skip_small_holes.setEnabled(enabled)
        self.light_slot_min_hole_span.setEnabled(
            enabled and self.light_slot_auto_skip_small_holes.isChecked()
        )

    def _create_top_face_group(self) -> QGroupBox:
        """创建顶面封闭参数组"""
        group = QGroupBox(self.tr("Top Face"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.top_face_enabled = QCheckBox(self.tr("Enable Top Face"))
        self.top_face_enabled.setObjectName("top_face_enabled")
        self.top_face_enabled.setVisible(False)
        self.top_face_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.top_face_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        # 顶面厚度
        self.top_face_thickness = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.top_face_thickness,
            0.1,
            10.0,
            2.4,
            enabled=False,
            meaning=self.tr("Printed solid top face thickness used to close the shell top."),
        )
        self.top_face_thickness.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "face-top", self.tr("Top Face Thickness:"), self.top_face_thickness)

        layout.addLayout(form)

        # 启用/禁用控件联动
        self.top_face_enabled.stateChanged.connect(
            lambda: self.top_face_thickness.setEnabled(self.top_face_enabled.isChecked())
        )
        # 与 Panel Step (Top) 互斥
        self.top_face_enabled.stateChanged.connect(self._on_top_face_toggled)
        self.top_face_enabled.stateChanged.connect(self._sync_top_mode_from_controls)

        return group

    def _on_top_face_toggled(self):
        """顶面封闭启用时，自动关闭面板台阶（互斥）"""
        if self.top_face_enabled.isChecked() and hasattr(self, 'panel_step_enabled'):
            if self.panel_step_enabled.isChecked():
                self.panel_step_enabled.blockSignals(True)
                self.panel_step_enabled.setChecked(False)
                self._toggle_panel_step_controls(False)
                self.panel_step_enabled.blockSignals(False)
                self._on_param_changed()

    def _on_panel_step_toggled(self):
        """面板台阶启用时，自动关闭顶面封闭（互斥）"""
        if self.panel_step_enabled.isChecked() and hasattr(self, 'top_face_enabled'):
            if self.top_face_enabled.isChecked():
                self.top_face_enabled.blockSignals(True)
                self.top_face_enabled.setChecked(False)
                self.top_face_thickness.setEnabled(False)
                self.top_face_enabled.blockSignals(False)
                self._on_param_changed()

    def _toggle_top_face_controls(self, enabled: bool):
        """切换顶面封闭控件的启用状态"""
        self.top_face_thickness.setEnabled(enabled)

    @staticmethod
    def _configure_wrapped_secondary_label(label: QLabel) -> None:
        label.setWordWrap(True)
        label.setMinimumWidth(0)
        label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        label.setStyleSheet("color: #8B949E; font-size: 12px;")

    @staticmethod
    def _create_script_preview_editor() -> QPlainTextEdit:
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        editor.setMinimumHeight(88)
        editor.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        editor.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {COLORS.bg_primary};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_default};
                border-bottom: 2px solid {COLORS.accent_primary};
                border-radius: 4px;
                padding: 6px;
                font-family: Consolas, "Courier New", monospace;
                font-size: 12px;
            }}
            """
        )
        return editor

    def _create_color_group(self) -> QGroupBox:
        """创建 Klipper 单喷头换色参数组"""
        group = QGroupBox(self.tr("Color Change"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.color_enabled = QCheckBox(self.tr("Enable Color Change"))
        self.color_enabled.stateChanged.connect(
            lambda: self._toggle_color_change_controls(self.color_enabled.isChecked())
        )
        self.color_enabled.stateChanged.connect(self._update_color_change_summary)
        self.color_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.color_enabled)

        self.color_change_hint = QLabel(
            self.tr("Initial color comes from Start G-code. Each change point runs the selected T macro.")
        )
        self._configure_wrapped_secondary_label(self.color_change_hint)
        layout.addWidget(self.color_change_hint)

        self.color_change_table = QTableWidget(0, 3)
        self.color_change_table.setHorizontalHeaderLabels(
            [
                self.tr("Change At Height"),
                self.tr("Macro Index"),
                self.tr("Preview"),
            ]
        )
        preview_header_item = self.color_change_table.horizontalHeaderItem(2)
        if preview_header_item is not None:
            preview_header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_change_table.verticalHeader().setVisible(False)
        self.color_change_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.color_change_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.color_change_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.color_change_table.setAlternatingRowColors(True)
        self.color_change_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.color_change_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.color_change_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.color_change_table.horizontalHeader().setStretchLastSection(True)
        self.color_change_table.itemSelectionChanged.connect(self._update_color_change_remove_button_state)
        layout.addWidget(self.color_change_table)

        self.color_change_actions_layout = QHBoxLayout()
        self.add_color_change_btn = QPushButton(self.tr("Add Change Point"))
        self.add_color_change_btn.clicked.connect(self._on_add_color_change_point)
        self.color_change_actions_layout.addWidget(self.add_color_change_btn)
        self.color_change_actions_layout.addStretch()

        self.remove_color_change_btn = QPushButton(self.tr("Remove Selected"))
        self.remove_color_change_btn.clicked.connect(self._on_remove_color_change_point)
        self.color_change_actions_layout.addWidget(self.remove_color_change_btn)
        layout.addLayout(self.color_change_actions_layout)

        self.color_change_summary = QLabel("")
        self._configure_wrapped_secondary_label(self.color_change_summary)
        layout.addWidget(self.color_change_summary)

        self._toggle_color_change_controls(False)
        self._update_color_change_summary()

        return group

    def _toggle_color_change_controls(self, enabled: bool):
        """切换换色控件启用状态。"""
        self.color_change_table.setEnabled(enabled)
        self.add_color_change_btn.setEnabled(enabled)
        self._update_color_change_remove_button_state()

    def _update_color_change_remove_button_state(self):
        enabled = self.color_enabled.isChecked() and bool(self.color_change_table.selectionModel().selectedRows())
        self.remove_color_change_btn.setEnabled(enabled)

    def _on_add_color_change_point(self):
        last_height = self._get_color_change_rows()[-1].height_mm if self._get_color_change_rows() else 0.0
        next_height = max(
            self._current_layer_height(),
            min(self.height_spin.value(), last_height + self._current_layer_height()),
        )
        self._insert_color_change_row(
            ColorChangePoint(height_mm=next_height, macro_index=1)
        )
        self._update_color_change_summary()
        self._on_param_changed()

    def _on_remove_color_change_point(self):
        selected_rows = self.color_change_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        for model_index in sorted(selected_rows, key=lambda item: item.row(), reverse=True):
            self.color_change_table.removeRow(model_index.row())
        self._update_color_change_summary()
        self._update_color_change_remove_button_state()
        self._on_param_changed()

    def _insert_color_change_row(self, change_point: ColorChangePoint):
        row = self.color_change_table.rowCount()
        self.color_change_table.insertRow(row)

        height_spin = self._create_double_spinbox()
        height_spin.setRange(self._current_layer_height(), 100.0)
        height_spin.setSingleStep(self._current_layer_height())
        height_spin.setSuffix(" mm")
        height_spin.setValue(change_point.height_mm)
        height_spin.setEnabled(self.color_enabled.isChecked())
        height_spin.setToolTip(self._color_change_height_tooltip())
        height_spin.valueChanged.connect(self._on_color_change_row_changed)
        self.color_change_table.setCellWidget(row, 0, height_spin)

        macro_spin = self._create_int_spinbox()
        macro_spin.setRange(0, 999)
        macro_spin.setValue(change_point.macro_index)
        macro_spin.setEnabled(self.color_enabled.isChecked())
        macro_spin.setToolTip(
            self._parameter_tooltip(
                self.tr("Macro index inserted into the configured color-change command template."),
                self.tr("0-999. With the default template T{index}, value 3 outputs T3."),
            )
        )
        macro_spin.valueChanged.connect(self._on_color_change_row_changed)
        self.color_change_table.setCellWidget(row, 1, macro_spin)

        preview_item = QTableWidgetItem(self._format_color_change_preview(change_point.macro_index))
        preview_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        preview_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_change_table.setItem(row, 2, preview_item)

    def _get_color_change_rows(self) -> list[ColorChangePoint]:
        rows: list[ColorChangePoint] = []
        for row in range(self.color_change_table.rowCount()):
            height_spin = self.color_change_table.cellWidget(row, 0)
            macro_spin = self.color_change_table.cellWidget(row, 1)
            if isinstance(height_spin, QDoubleSpinBox) and isinstance(macro_spin, QSpinBox):
                rows.append(
                    ColorChangePoint(
                        height_mm=height_spin.value(),
                        macro_index=macro_spin.value(),
                    )
                )
        return rows

    def _rebuild_color_change_rows(self, change_points: list[ColorChangePoint]):
        self._updating_profile_ui = True
        try:
            self.color_change_table.setRowCount(0)
            for change_point in change_points:
                self._insert_color_change_row(change_point)
        finally:
            self._updating_profile_ui = False
        self._update_color_change_summary()
        self._update_color_change_remove_button_state()

    def _on_color_change_row_changed(self):
        if self._updating_profile_ui:
            return
        for row in range(self.color_change_table.rowCount()):
            macro_spin = self.color_change_table.cellWidget(row, 1)
            preview_item = self.color_change_table.item(row, 2)
            if isinstance(macro_spin, QSpinBox) and preview_item is not None:
                preview_item.setText(self._format_color_change_preview(macro_spin.value()))
        self._update_color_change_summary()
        self._on_param_changed()

    def _format_color_change_preview(self, macro_index: int) -> str:
        if not hasattr(self, "profile_color_change_template"):
            return f"T{macro_index}"
        template = self.profile_color_change_template.text().strip() or "T{index}"
        if "{index}" not in template:
            return template
        try:
            return template.format(index=macro_index)
        except Exception:
            return template

    def _update_color_change_summary(self):
        if not hasattr(self, "color_change_summary"):
            return
        if not self.color_enabled.isChecked():
            self.color_change_summary.setText(self.tr("Color change disabled."))
            return

        change_points = self._get_color_change_rows()
        if not change_points:
            self.color_change_summary.setText(
                self.tr("Initial color comes from Start G-code. No automatic changes are configured.")
            )
            return

        lines = []
        for change_point in change_points:
            lines.append(
                self.tr("At {height:.2f}mm -> {command}").format(
                    height=change_point.height_mm,
                    command=self._format_color_change_preview(change_point.macro_index),
                )
            )
        self.color_change_summary.setText("\n".join(lines))

    def _create_prime_tower_group(self) -> QGroupBox:
        """Create prime tower settings."""
        group = QGroupBox(self.tr("Prime Tower"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.prime_tower_enabled = QCheckBox(self.tr("Enable Prime Tower"))
        self.prime_tower_enabled.stateChanged.connect(
            lambda: self._toggle_prime_tower_controls(self.prime_tower_enabled.isChecked())
        )
        self.prime_tower_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.prime_tower_enabled)

        self.prime_tower_hint = QLabel(
            self.tr("Prime tower geometry is defined by its center point in bed coordinates.")
        )
        self._configure_wrapped_secondary_label(self.prime_tower_hint)
        layout.addWidget(self.prime_tower_hint)

        form = QFormLayout()
        form.setSpacing(8)

        default_center_x, default_center_y = PrimeTowerGenerator.default_center(
            self._params.machine
        )

        self.prime_tower_center_x = self._create_double_spinbox()
        self.prime_tower_center_x.setDecimals(2)
        self.prime_tower_center_x.setRange(0.0, max(float(self._params.machine.bed_width), 1.0))
        self.prime_tower_center_x.setValue(default_center_x)
        self.prime_tower_center_x.setSuffix(" mm")
        self.prime_tower_center_x.setEnabled(False)
        self.prime_tower_center_x.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "center", self.tr("Center X:"), self.prime_tower_center_x)

        self.prime_tower_center_y = self._create_double_spinbox()
        self.prime_tower_center_y.setDecimals(2)
        self.prime_tower_center_y.setRange(0.0, max(float(self._params.machine.bed_depth), 1.0))
        self.prime_tower_center_y.setValue(default_center_y)
        self.prime_tower_center_y.setSuffix(" mm")
        self.prime_tower_center_y.setEnabled(False)
        self.prime_tower_center_y.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "center", self.tr("Center Y:"), self.prime_tower_center_y)

        self.prime_tower_width = self._create_double_spinbox()
        self.prime_tower_width.setDecimals(2)
        self.prime_tower_width.setRange(1.0, 5000.0)
        self.prime_tower_width.setValue(100.0)
        self.prime_tower_width.setSuffix(" mm")
        self.prime_tower_width.setEnabled(False)
        self.prime_tower_width.valueChanged.connect(self._update_prime_tower_coordinate_ranges)
        self.prime_tower_width.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "prime-tower", self.tr("Tower Width:"), self.prime_tower_width)

        self.prime_tower_depth = self._create_double_spinbox()
        self.prime_tower_depth.setDecimals(2)
        self.prime_tower_depth.setRange(1.0, 5000.0)
        self.prime_tower_depth.setValue(100.0)
        self.prime_tower_depth.setSuffix(" mm")
        self.prime_tower_depth.setEnabled(False)
        self.prime_tower_depth.valueChanged.connect(self._update_prime_tower_coordinate_ranges)
        self.prime_tower_depth.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "dimension", self.tr("Tower Depth:"), self.prime_tower_depth)

        self.prime_tower_infill_density = self._create_int_spinbox()
        self.prime_tower_infill_density.setRange(10, 80)
        self.prime_tower_infill_density.setSingleStep(5)
        self.prime_tower_infill_density.setValue(20)
        self.prime_tower_infill_density.setSuffix(" %")
        self.prime_tower_infill_density.setEnabled(False)
        self.prime_tower_infill_density.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "infill", self.tr("Infill Density:"), self.prime_tower_infill_density)

        layout.addLayout(form)
        return group

    def _toggle_prime_tower_controls(self, enabled: bool):
        """Toggle prime tower controls."""
        self.prime_tower_center_x.setEnabled(enabled)
        self.prime_tower_center_y.setEnabled(enabled)
        self.prime_tower_width.setEnabled(enabled)
        self.prime_tower_depth.setEnabled(enabled)
        self.prime_tower_infill_density.setEnabled(enabled)

    def _update_prime_tower_coordinate_ranges(self):
        """Clamp prime tower coordinates to the active printable area."""
        if not hasattr(self, "prime_tower_center_x"):
            return

        bed_width = (
            self.profile_bed_width.value()
            if hasattr(self, "profile_bed_width")
            else float(self._params.machine.bed_width)
        )
        bed_depth = (
            self.profile_bed_depth.value()
            if hasattr(self, "profile_bed_depth")
            else float(self._params.machine.bed_depth)
        )
        half_width = self.prime_tower_width.value() / 2.0
        half_depth = self.prime_tower_depth.value() / 2.0

        min_x = min(half_width, bed_width)
        max_x = max(min_x, bed_width - half_width)
        min_y = min(half_depth, bed_depth)
        max_y = max(min_y, bed_depth - half_depth)

        widgets = (self.prime_tower_center_x, self.prime_tower_center_y)
        for widget in widgets:
            widget.blockSignals(True)
        try:
            self.prime_tower_center_x.setRange(min_x, max_x)
            self.prime_tower_center_y.setRange(min_y, max_y)
            self.prime_tower_center_x.setValue(
                min(max(self.prime_tower_center_x.value(), min_x), max_x)
            )
            self.prime_tower_center_y.setValue(
                min(max(self.prime_tower_center_y.value(), min_y), max_y)
            )
        finally:
            for widget in widgets:
                widget.blockSignals(False)

    def _create_printer_profile_group(self) -> QGroupBox:
        """创建打印机档案参数组。"""
        group = QGroupBox(self.tr("Printer Profile"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        combo_row = QHBoxLayout()
        self.printer_profile_combo = GuardedComboBox()
        self.printer_profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        combo_row.addWidget(self.printer_profile_combo, 1)
        layout.addLayout(combo_row)

        action_row = QHBoxLayout()
        self.profile_new_btn = QPushButton(self.tr("New"))
        self.profile_new_btn.clicked.connect(self._on_new_profile)
        self.profile_new_btn.setVisible(False)
        action_row.addWidget(self.profile_new_btn)

        self.profile_duplicate_btn = QPushButton(self.tr("Duplicate"))
        self.profile_duplicate_btn.clicked.connect(self._on_duplicate_profile)
        self.profile_duplicate_btn.setVisible(False)
        action_row.addWidget(self.profile_duplicate_btn)

        self.profile_rename_btn = QPushButton(self.tr("Rename"))
        self.profile_rename_btn.clicked.connect(self._on_rename_profile)
        self.profile_rename_btn.setVisible(False)
        action_row.addWidget(self.profile_rename_btn)

        self.profile_delete_btn = QPushButton(self.tr("Delete"))
        self.profile_delete_btn.clicked.connect(self._on_delete_profile)
        self.profile_delete_btn.setVisible(False)
        action_row.addWidget(self.profile_delete_btn)

        self.profile_default_btn = QPushButton(self.tr("Set Default"))
        self.profile_default_btn.clicked.connect(self._on_set_default_profile)
        self.profile_default_btn.setVisible(False)
        action_row.addWidget(self.profile_default_btn)
        # Keep the button instances for now, but hide profile management actions from the UI.

        self.profile_source_label = QLabel("")
        self.profile_source_label.setWordWrap(True)
        self.profile_source_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        layout.addWidget(self.profile_source_label)

        form = QFormLayout()
        form.setSpacing(8)

        self.profile_bed_width = self._create_double_spinbox()
        self.profile_bed_width.setRange(1.0, 5000.0)
        self.profile_bed_width.setSuffix(" mm")
        self.profile_bed_width.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "bed", self.tr("Printable Area X:"), self.profile_bed_width)

        self.profile_bed_depth = self._create_double_spinbox()
        self.profile_bed_depth.setRange(1.0, 5000.0)
        self.profile_bed_depth.setSuffix(" mm")
        self.profile_bed_depth.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "bed", self.tr("Printable Area Y:"), self.profile_bed_depth)

        self.profile_bed_height = self._create_double_spinbox()
        self.profile_bed_height.setRange(1.0, 1000.0)
        self.profile_bed_height.setSuffix(" mm")
        self.profile_bed_height.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "height", self.tr("Printable Area Z:"), self.profile_bed_height)

        self.profile_bed_exclude_area = QPlainTextEdit()
        self.profile_bed_exclude_area.setFixedHeight(92)
        self.profile_bed_exclude_area.setPlaceholderText(
            self.tr("One polygon per line: 0x0,70x0,70x70,0x70")
        )
        self.profile_bed_exclude_area.setToolTip(
            self.tr("Orca-style bed exclude area. Use XxY points separated by commas; put each region on its own line.")
        )
        self.profile_bed_exclude_area.textChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "clearance", self.tr("Bed Exclude Area:"), self.profile_bed_exclude_area)

        self.profile_nozzle_diameter = self._create_double_spinbox(3)
        self.profile_nozzle_diameter.setRange(0.1, 5.0)
        self.profile_nozzle_diameter.setSingleStep(0.05)
        self.profile_nozzle_diameter.setSuffix(" mm")
        self.profile_nozzle_diameter.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "nozzle", self.tr("Nozzle Diameter:"), self.profile_nozzle_diameter)

        self.profile_filament_diameter = self._create_double_spinbox(3)
        self.profile_filament_diameter.setRange(0.5, 5.0)
        self.profile_filament_diameter.setSingleStep(0.05)
        self.profile_filament_diameter.setSuffix(" mm")
        self.profile_filament_diameter.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "filament", self.tr("Filament Diameter:"), self.profile_filament_diameter)

        self.profile_retract_length = self._create_double_spinbox()
        self.profile_retract_length.setRange(0.0, 20.0)
        self.profile_retract_length.setSingleStep(0.1)
        self.profile_retract_length.setSuffix(" mm")
        self.profile_retract_length.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "retract", self.tr("Retract Length:"), self.profile_retract_length)

        self.profile_retract_speed = self._create_double_spinbox()
        self.profile_retract_speed.setRange(1.0, 300.0)
        self.profile_retract_speed.setSuffix(" mm/s")
        self.profile_retract_speed.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "speed", self.tr("Retract Speed:"), self.profile_retract_speed)

        self.profile_z_hop_short = self._create_double_spinbox()
        self.profile_z_hop_short.setRange(0.0, 20.0)
        self.profile_z_hop_short.setSingleStep(0.1)
        self.profile_z_hop_short.setSuffix(" mm")
        self.profile_z_hop_short.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "z-hop", self.tr("Short Z-Hop:"), self.profile_z_hop_short)

        self.profile_z_hop_long = self._create_double_spinbox()
        self.profile_z_hop_long.setRange(0.0, 50.0)
        self.profile_z_hop_long.setSingleStep(0.1)
        self.profile_z_hop_long.setSuffix(" mm")
        self.profile_z_hop_long.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "z-hop", self.tr("Long Z-Hop:"), self.profile_z_hop_long)

        self.profile_long_travel_threshold = self._create_double_spinbox()
        self.profile_long_travel_threshold.setRange(1.0, 1000.0)
        self.profile_long_travel_threshold.setSuffix(" mm")
        self.profile_long_travel_threshold.valueChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "dimension", self.tr("Long Travel Threshold:"), self.profile_long_travel_threshold)

        self.profile_color_change_template = QLineEdit()
        self.profile_color_change_template.textChanged.connect(self._on_printer_profile_field_changed)
        self._add_icon_row(form, "color-change", self.tr("Color Change Template:"), self.profile_color_change_template)

        layout.addLayout(form)
        return group

    def _create_klipper_commands_group(self) -> QGroupBox:
        """创建 Klipper 脚本参数组。"""
        group = QGroupBox(self.tr("Machine G-code"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        start_row = QVBoxLayout()
        start_row.setSpacing(6)
        start_header_row = QHBoxLayout()
        self.start_gcode_title = QLabel(self.tr("Machine start G-code"))
        self.start_gcode_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        start_header_row.addWidget(self.start_gcode_title)
        start_header_row.addStretch()
        self.edit_start_gcode_btn = QPushButton(self.tr("Edit Start G-code"))
        self.edit_start_gcode_btn.clicked.connect(
            lambda: self._edit_script("start_gcode", self.tr("Start G-code"))
        )
        start_header_row.addWidget(self.edit_start_gcode_btn)
        start_row.addLayout(start_header_row)
        self.start_gcode_summary = self._create_script_preview_editor()
        start_row.addWidget(self.start_gcode_summary)
        layout.addLayout(start_row)

        end_row = QVBoxLayout()
        end_row.setSpacing(6)
        end_header_row = QHBoxLayout()
        self.end_gcode_title = QLabel(self.tr("Machine end G-code"))
        self.end_gcode_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        end_header_row.addWidget(self.end_gcode_title)
        end_header_row.addStretch()
        self.edit_end_gcode_btn = QPushButton(self.tr("Edit End G-code"))
        self.edit_end_gcode_btn.clicked.connect(
            lambda: self._edit_script("end_gcode", self.tr("End G-code"))
        )
        end_header_row.addWidget(self.edit_end_gcode_btn)
        end_row.addLayout(end_header_row)
        self.end_gcode_summary = self._create_script_preview_editor()
        end_row.addWidget(self.end_gcode_summary)
        layout.addLayout(end_row)

        return group

    def _load_initial_printer_profile(self):
        """初始化当前打印机档案。"""
        settings = get_settings_manager()
        saved_profile_id = settings.get_active_printer_profile_id() if settings else ""
        target_profile_id = saved_profile_id or self._profile_manager.get_default_profile_id()
        self._refresh_profile_selector(target_profile_id)
        profile = self._current_printer_profile()
        if profile is None:
            return
        self._apply_profile_to_form(profile)
        apply_printer_profile_to_params(self._params, profile)
        self._update_script_summaries()
        self._update_color_change_summary()

    def _refresh_profile_selector(self, selected_profile_id: str = ""):
        self._updating_profile_ui = True
        try:
            self.printer_profile_combo.blockSignals(True)
            self.printer_profile_combo.clear()
            if self._runtime_profile is not None:
                self.printer_profile_combo.addItem(
                    self.tr("{name} (Project Snapshot)").format(name=self._runtime_profile.name),
                    self._runtime_profile.id,
                )
            for profile in self._profile_manager.list_profiles():
                self.printer_profile_combo.addItem(profile.name, profile.id)

            target_profile_id = (
                selected_profile_id
                or self._active_profile_id
                or self._profile_manager.get_default_profile_id()
            )
            combo_index = self.printer_profile_combo.findData(target_profile_id)
            if combo_index < 0 and self.printer_profile_combo.count() > 0:
                combo_index = 0
            self.printer_profile_combo.setCurrentIndex(combo_index)
            self._active_profile_id = self.printer_profile_combo.currentData() or ""
        finally:
            self.printer_profile_combo.blockSignals(False)
            self._updating_profile_ui = False
        self._update_profile_action_buttons()

    def _selected_profile_is_runtime(self) -> bool:
        return self._runtime_profile is not None and self._active_profile_id == self._runtime_profile.id

    def _current_printer_profile(self) -> Optional[PrinterProfile]:
        if self._selected_profile_is_runtime():
            return clone_printer_profile(self._runtime_profile)
        profile = self._profile_manager.get_profile(self._active_profile_id)
        if profile is not None:
            return profile
        if self._runtime_profile is not None:
            return clone_printer_profile(self._runtime_profile)
        return None

    def _update_profile_action_buttons(self):
        if not hasattr(self, "profile_source_label"):
            return
        is_runtime = self._selected_profile_is_runtime()
        buttons_enabled = self._profile_management_buttons_enabled
        self.profile_new_btn.setEnabled(buttons_enabled)
        self.profile_duplicate_btn.setEnabled(buttons_enabled)
        self.profile_rename_btn.setEnabled(buttons_enabled and not is_runtime)
        self.profile_delete_btn.setEnabled(buttons_enabled and not is_runtime)
        self.profile_default_btn.setEnabled(buttons_enabled and not is_runtime)
        self.profile_source_label.setText(
            self.tr("Using embedded project profile snapshot.")
            if is_runtime
            else self.tr("Profile changes are saved immediately.")
        )

    def _apply_profile_to_form(self, profile: PrinterProfile):
        self._updating_profile_ui = True
        widgets = [
            self.profile_bed_width,
            self.profile_bed_depth,
            self.profile_bed_height,
            self.profile_bed_exclude_area,
            self.profile_nozzle_diameter,
            self.profile_filament_diameter,
            self.profile_retract_length,
            self.profile_retract_speed,
            self.profile_z_hop_short,
            self.profile_z_hop_long,
            self.profile_long_travel_threshold,
            self.profile_color_change_template,
            self.prime_tower_center_x,
            self.prime_tower_center_y,
        ]
        try:
            for widget in widgets:
                widget.blockSignals(True)

            self.profile_bed_width.setValue(profile.bed_width)
            self.profile_bed_depth.setValue(profile.bed_depth)
            self.profile_bed_height.setValue(profile.bed_height)
            self.profile_bed_exclude_area.setPlainText(
                format_bed_exclude_area_for_editor(profile.bed_exclude_area)
            )
            self.profile_nozzle_diameter.setValue(profile.nozzle_diameter)
            self.profile_filament_diameter.setValue(profile.filament_diameter)
            self.profile_retract_length.setValue(profile.retract_length)
            self.profile_retract_speed.setValue(profile.retract_speed)
            self.profile_z_hop_short.setValue(profile.z_hop_short)
            self.profile_z_hop_long.setValue(profile.z_hop_long)
            self.profile_long_travel_threshold.setValue(profile.long_travel_threshold)
            self.profile_color_change_template.setText(profile.color_change_command_template)
            self._params.gcode.start_gcode = profile.start_gcode
            self._params.gcode.end_gcode = profile.end_gcode
        finally:
            for widget in widgets:
                widget.blockSignals(False)
            self._updating_profile_ui = False

        apply_printer_profile_to_params(self._params, profile)
        self._update_prime_tower_coordinate_ranges()
        self._update_script_summaries()
        self._update_color_change_summary()
        self._sync_wall_tooltips()

    def _apply_shell_defaults_for_profile_nozzle_change(
        self,
        previous_nozzle_diameter: float,
        new_nozzle_diameter: float,
    ) -> None:
        if (
            not hasattr(self, "layer_height_spin")
            or not hasattr(self, "width_line_spin")
            or math.isclose(
                previous_nozzle_diameter,
                new_nozzle_diameter,
                abs_tol=1e-9,
            )
        ):
            return

        target_layer_height = round(
            new_nozzle_diameter / 2.0,
            self.layer_height_spin.decimals(),
        )
        target_layer_height = min(
            max(target_layer_height, self.layer_height_spin.minimum()),
            self.layer_height_spin.maximum(),
        )
        target_width_line = round(
            new_nozzle_diameter,
            self.width_line_spin.decimals(),
        )
        target_width_line = min(
            max(target_width_line, self.width_line_spin.minimum()),
            self.width_line_spin.maximum(),
        )

        self.layer_height_spin.blockSignals(True)
        self.width_line_spin.blockSignals(True)
        try:
            self.layer_height_spin.setValue(target_layer_height)
            self.width_line_spin.setValue(target_width_line)
        finally:
            self.layer_height_spin.blockSignals(False)
            self.width_line_spin.blockSignals(False)

        self._sync_layer_based_controls()

    def _profile_from_form(
        self,
        *,
        profile_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> PrinterProfile:
        base_profile = self._current_printer_profile() or PrinterProfile()
        profile = clone_printer_profile(base_profile)
        if profile_id is not None:
            profile.id = profile_id
        if name is not None:
            profile.name = name
        profile.bed_width = self.profile_bed_width.value()
        profile.bed_depth = self.profile_bed_depth.value()
        profile.bed_height = self.profile_bed_height.value()
        profile.bed_exclude_area = normalize_bed_exclude_area(
            self.profile_bed_exclude_area.toPlainText()
        )
        profile.nozzle_diameter = self.profile_nozzle_diameter.value()
        profile.filament_diameter = self.profile_filament_diameter.value()
        profile.retract_length = self.profile_retract_length.value()
        profile.retract_speed = self.profile_retract_speed.value()
        profile.z_hop_short = self.profile_z_hop_short.value()
        profile.z_hop_long = self.profile_z_hop_long.value()
        profile.long_travel_threshold = self.profile_long_travel_threshold.value()
        profile.start_gcode = self._params.gcode.start_gcode
        profile.end_gcode = self._params.gcode.end_gcode
        profile.color_change_command_template = self.profile_color_change_template.text().strip() or "T{index}"
        return profile

    def _persist_profile_form_edits(self):
        profile = self._profile_from_form()
        apply_printer_profile_to_params(self._params, profile)
        if self._selected_profile_is_runtime():
            self._runtime_profile = clone_printer_profile(profile)
        else:
            self._profile_manager.save_profile(profile)
        self._update_script_summaries()
        self._update_color_change_summary()

    def _on_profile_selected(self):
        if self._updating_profile_ui:
            return
        previous_profile = self._current_printer_profile()
        previous_nozzle_diameter = (
            previous_profile.nozzle_diameter
            if previous_profile is not None
            else self._params.machine.nozzle_diameter
        )
        self._active_profile_id = self.printer_profile_combo.currentData() or ""
        profile = self._current_printer_profile()
        if profile is None:
            return
        settings = get_settings_manager()
        if settings and not self._selected_profile_is_runtime():
            settings.set_active_printer_profile_id(self._active_profile_id)
        self._apply_profile_to_form(profile)
        self._apply_shell_defaults_for_profile_nozzle_change(
            previous_nozzle_diameter,
            profile.nozzle_diameter,
        )
        self._sync_wall_tooltips()
        self._update_profile_action_buttons()
        self._on_param_changed()

    def _refresh_default_bed_exclude_area_for_current_bed(self):
        if not hasattr(self, "profile_bed_exclude_area"):
            return

        current_text = self.profile_bed_exclude_area.toPlainText()
        current_area = normalize_bed_exclude_area(current_text)
        if current_area and not is_default_bed_exclude_area(current_area):
            return

        default_area = default_bed_exclude_area_for_bed(
            self.profile_bed_width.value(),
            self.profile_bed_depth.value(),
        )
        new_text = format_bed_exclude_area_for_editor(default_area)
        if current_text.strip() == new_text.strip():
            return

        self.profile_bed_exclude_area.blockSignals(True)
        try:
            self.profile_bed_exclude_area.setPlainText(new_text)
        finally:
            self.profile_bed_exclude_area.blockSignals(False)

    def _on_printer_profile_field_changed(self):
        if self._updating_profile_ui:
            return
        sender = self.sender()
        if sender is self.profile_bed_width or sender is self.profile_bed_depth:
            self._refresh_default_bed_exclude_area_for_current_bed()
        self._update_prime_tower_coordinate_ranges()
        self._persist_profile_form_edits()
        self._sync_wall_tooltips()
        self._on_param_changed()

    def _prompt_profile_name(self, title: str, text: str, value: str = "") -> Optional[str]:
        name, accepted = QInputDialog.getText(self, title, text, text=value)
        normalized = name.strip()
        if not accepted or not normalized:
            return None
        return normalized

    def _on_new_profile(self):
        if not self._profile_management_buttons_enabled:
            return
        name = self._prompt_profile_name(
            self.tr("New Printer Profile"),
            self.tr("Profile Name:"),
        )
        if name is None:
            return
        base_profile = self._profile_from_form()
        profile = self._profile_manager.create_profile(name, base_profile)
        self._runtime_profile = None
        self._active_profile_id = profile.id
        self._refresh_profile_selector(profile.id)
        self._apply_profile_to_form(profile)
        settings = get_settings_manager()
        if settings:
            settings.set_active_printer_profile_id(profile.id)
        self._on_param_changed()

    def _on_duplicate_profile(self):
        if not self._profile_management_buttons_enabled:
            return
        base_profile = self._profile_from_form()
        name = self._prompt_profile_name(
            self.tr("Duplicate Printer Profile"),
            self.tr("New Profile Name:"),
            self.tr("{name} Copy").format(name=base_profile.name),
        )
        if name is None:
            return
        profile = self._profile_manager.create_profile(name, base_profile)
        self._runtime_profile = None
        self._active_profile_id = profile.id
        self._refresh_profile_selector(profile.id)
        self._apply_profile_to_form(profile)
        settings = get_settings_manager()
        if settings:
            settings.set_active_printer_profile_id(profile.id)
        self._on_param_changed()

    def _on_rename_profile(self):
        if not self._profile_management_buttons_enabled:
            return
        if self._selected_profile_is_runtime():
            return
        profile = self._current_printer_profile()
        if profile is None:
            return
        name = self._prompt_profile_name(
            self.tr("Rename Printer Profile"),
            self.tr("Profile Name:"),
            profile.name,
        )
        if name is None:
            return
        profile.name = name
        self._profile_manager.save_profile(profile)
        self._refresh_profile_selector(profile.id)
        self._apply_profile_to_form(profile)

    def _on_delete_profile(self):
        if not self._profile_management_buttons_enabled:
            return
        if self._selected_profile_is_runtime():
            return
        profile = self._current_printer_profile()
        if profile is None:
            return
        answer = QMessageBox.question(
            self,
            self.tr("Delete Printer Profile"),
            self.tr("Delete printer profile '{name}'?").format(name=profile.name),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._profile_manager.delete_profile(profile.id)
        fallback_profile_id = self._profile_manager.get_default_profile_id()
        self._active_profile_id = fallback_profile_id
        self._refresh_profile_selector(fallback_profile_id)
        new_profile = self._current_printer_profile()
        if new_profile is not None:
            self._apply_profile_to_form(new_profile)
            settings = get_settings_manager()
            if settings:
                settings.set_active_printer_profile_id(new_profile.id)
            self._on_param_changed()

    def _on_set_default_profile(self):
        if not self._profile_management_buttons_enabled:
            return
        if self._selected_profile_is_runtime():
            return
        if self._profile_manager.set_default_profile_id(self._active_profile_id):
            self._refresh_profile_selector(self._active_profile_id)

    def _edit_script(self, attr_name: str, title: str):
        current_text = getattr(self._params.gcode, attr_name, "")
        text, accepted = QInputDialog.getMultiLineText(
            self,
            title,
            title,
            current_text,
        )
        if not accepted:
            return
        setattr(self._params.gcode, attr_name, text)
        self._persist_profile_form_edits()
        self._on_param_changed()

    def _summarize_script(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return self.tr("Empty")
        if len(lines) == 1:
            return lines[0]
        return self.tr("{first} (+{count} more lines)").format(
            first=lines[0],
            count=len(lines) - 1,
        )

    def _update_script_summaries(self):
        if hasattr(self, "start_gcode_summary"):
            self.start_gcode_summary.setPlainText(self._params.gcode.start_gcode)
        if hasattr(self, "end_gcode_summary"):
            self.end_gcode_summary.setPlainText(self._params.gcode.end_gcode)

    def get_active_printer_profile(self) -> PrinterProfile:
        current_profile = self._current_printer_profile()
        return self._profile_from_form(
            profile_id=self._active_profile_id or "",
            name=current_profile.name if current_profile is not None else self.tr("Klipper Profile"),
        )

    def get_active_printer_profile_id(self) -> str:
        return self._active_profile_id

    def load_project_printer_profile(
        self,
        profile_id: str,
        profile_snapshot: Optional[PrinterProfile],
    ) -> None:
        if profile_snapshot is None:
            self.clear_project_printer_profile()
            return
        self._runtime_profile = clone_printer_profile(profile_snapshot)
        self._runtime_profile.id = profile_id or self._runtime_profile.id
        self._active_profile_id = self._runtime_profile.id
        self._refresh_profile_selector(self._active_profile_id)
        self._apply_profile_to_form(self._runtime_profile)

    def clear_project_printer_profile(self) -> None:
        self._runtime_profile = None
        settings = get_settings_manager()
        target_profile_id = (
            settings.get_active_printer_profile_id()
            if settings and settings.get_active_printer_profile_id()
            else self._profile_manager.get_default_profile_id()
        )
        self._active_profile_id = target_profile_id
        self._refresh_profile_selector(target_profile_id)
        profile = self._current_printer_profile()
        if profile is not None:
            self._apply_profile_to_form(profile)

    def _create_step_group(self) -> QGroupBox:
        """创建台阶/V槽参数组"""
        self.panel_step_group = QGroupBox(self.tr("Panel Step/V-Groove"))
        group = self.panel_step_group
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # ===== 面板台阶（顶部）=====
        self.panel_step_enabled = QCheckBox(self.tr("Enable Panel Step (Top)"))
        self.panel_step_enabled.setObjectName("panel_step_enabled")
        self.panel_step_enabled.setVisible(False)
        self.panel_step_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.panel_step_enabled)

        form1 = QFormLayout()
        self.panel_step_height = self._create_double_spinbox()
        self.panel_step_height.setRange(15.0, 100.0)
        self.panel_step_height.setValue(47.0)
        self.panel_step_height.setSingleStep(0.1)
        self.panel_step_height.setSuffix(" mm")
        self.panel_step_height.setEnabled(False)
        self.panel_step_height.setToolTip(
            self._parameter_tooltip(
                self.tr("Z height where the top panel step or V-groove is generated."),
                self.tr(
                    "Current range is automatically constrained between half of Shell Height and Shell Height. "
                    "The value is rounded up to the current layer-height grid before preview, STL export, and G-code export."
                ),
            )
        )
        self.panel_step_height.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form1, "step", self.tr("Step Height:"), self.panel_step_height)

        self.panel_step_width = self._create_double_spinbox()
        self.panel_step_width.setRange(0.5, 20)
        self.panel_step_width.setValue(1.8)
        self.panel_step_width.setSuffix(" mm")
        self.panel_step_width.setEnabled(False)
        self.panel_step_width.setToolTip(
            self._parameter_tooltip(
                self.tr("XY width of the top panel step or V-groove."),
                self.tr("0.50-20.00 mm. Choose a value wide enough for panel seating but not wider than the local stroke."),
            )
        )
        self.panel_step_width.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form1, "dimension", self.tr("Step Width:"), self.panel_step_width)

        self.panel_step_v_groove = QCheckBox(self.tr("V-Groove"))
        self.panel_step_v_groove.setObjectName("panel_step_v_groove")
        self.panel_step_v_groove.setVisible(False)
        self.panel_step_v_groove.setEnabled(False)
        self.panel_step_v_groove.stateChanged.connect(self._on_param_changed)
        form1.addRow("", self.panel_step_v_groove)

        layout.addLayout(form1)

        self.panel_step_enabled.stateChanged.connect(
            lambda: self._toggle_panel_step_controls(self.panel_step_enabled.isChecked())
        )
        # 与 Top Face 互斥
        self.panel_step_enabled.stateChanged.connect(self._on_panel_step_toggled)
        self.panel_step_enabled.stateChanged.connect(self._sync_top_mode_from_controls)
        self.panel_step_v_groove.stateChanged.connect(self._sync_top_mode_from_controls)

        # 分隔线
        self.baseplate_step_group = QGroupBox(self.tr("Baseplate Step/V-Groove"))
        bottom_layout = QVBoxLayout(self.baseplate_step_group)
        bottom_layout.setSpacing(8)

        # ===== 底板台阶（底部）=====
        self.baseplate_step_enabled = QCheckBox(self.tr("Enable Baseplate Step (Bottom)"))
        self.baseplate_step_enabled.setObjectName("baseplate_step_enabled")
        self.baseplate_step_enabled.setVisible(False)
        self.baseplate_step_enabled.stateChanged.connect(self._on_param_changed)
        bottom_layout.addWidget(self.baseplate_step_enabled)

        form2 = QFormLayout()
        self.baseplate_step_height = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.baseplate_step_height,
            0.1,
            50.0,
            3.0,
            enabled=False,
            meaning=self.tr("Z height where the bottom baseplate step or V-groove is generated."),
        )
        self.baseplate_step_height.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form2, "step", self.tr("Step Height:"), self.baseplate_step_height)

        self.baseplate_step_width = self._create_double_spinbox()
        self.baseplate_step_width.setRange(0.5, 20)
        self.baseplate_step_width.setValue(1.8)
        self.baseplate_step_width.setSuffix(" mm")
        self.baseplate_step_width.setEnabled(False)
        self.baseplate_step_width.setToolTip(
            self._parameter_tooltip(
                self.tr("XY width of the bottom baseplate step or V-groove."),
                self.tr("0.50-20.00 mm. Choose a value wide enough for baseplate seating but not wider than the local stroke."),
            )
        )
        self.baseplate_step_width.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form2, "dimension", self.tr("Step Width:"), self.baseplate_step_width)

        self.baseplate_step_v_groove = QCheckBox(self.tr("V-Groove"))
        self.baseplate_step_v_groove.setObjectName("baseplate_step_v_groove")
        self.baseplate_step_v_groove.setVisible(False)
        self.baseplate_step_v_groove.setEnabled(False)
        self.baseplate_step_v_groove.stateChanged.connect(self._on_param_changed)
        form2.addRow("", self.baseplate_step_v_groove)

        bottom_layout.addLayout(form2)

        self.step_speed = self._create_double_spinbox(decimals=1)
        self.step_speed.setRange(5.0, 200.0)
        self.step_speed.setValue(30.0)
        self.step_speed.setSingleStep(1.0)
        self.step_speed.setSuffix(" mm/s")
        self.step_speed.setEnabled(False)
        self.step_speed.valueChanged.connect(self._on_param_changed)

        self.baseplate_step_enabled.stateChanged.connect(
            lambda: self._toggle_baseplate_step_controls(self.baseplate_step_enabled.isChecked())
        )
        # 与 Bottom Face 互斥
        self.baseplate_step_enabled.stateChanged.connect(self._on_baseplate_step_toggled)
        self.baseplate_step_enabled.stateChanged.connect(self._sync_bottom_mode_from_controls)
        self.baseplate_step_v_groove.stateChanged.connect(self._sync_bottom_mode_from_controls)

        # 兼容旧变量（避免其他代码报错）
        self.top_step_enabled = self.panel_step_enabled
        self.top_step_height = self.panel_step_height
        self.top_step_width = self.panel_step_width
        self.bottom_groove_enabled = self.baseplate_step_enabled
        self.bottom_groove_height = self.baseplate_step_height

        return group

    def _update_step_ranges(self):
        """根据字壳高度更新台阶高度范围

        顶部卡槽：[字壳高度/2, 字壳高度]
        底部卡槽：[0.3, 字壳高度/2]
        """
        # 检查控件是否已创建
        if not hasattr(self, 'panel_step_height') or not hasattr(self, 'baseplate_step_height'):
            return

        layer_height = self._current_layer_height()
        shell_layers = self._height_to_layers(self.height_spin.value())
        half_min = max(1, (shell_layers + 1) // 2)
        half_max = max(1, shell_layers // 2)
        shell_height_mm = shell_layers * layer_height

        # 顶部卡槽（mm）
        panel_min_mm = half_min * layer_height
        panel_max_mm = max(panel_min_mm, shell_height_mm)
        self.panel_step_height.setRange(panel_min_mm, panel_max_mm)
        self.panel_step_height.setSingleStep(layer_height)
        self.panel_step_height.setToolTip(
            self._parameter_tooltip(
                self.tr("Z height where the top panel step or V-groove is generated."),
                self.tr(
                    "Current range: {minimum:.2f}-{maximum:.2f} mm. "
                    "The value is rounded up to the current layer-height grid before preview, STL export, and G-code export."
                ).format(minimum=panel_min_mm, maximum=panel_max_mm),
            )
        )
        if self.panel_step_height.value() < panel_min_mm:
            self.panel_step_height.setValue(panel_min_mm)
        elif self.panel_step_height.value() > panel_max_mm:
            self.panel_step_height.setValue(panel_max_mm)

        # 底部卡槽（layers）
        baseplate_max_mm = max(layer_height, half_max * layer_height)
        self.baseplate_step_height.setRange(layer_height, baseplate_max_mm)
        self.baseplate_step_height.setSingleStep(layer_height)
        self.baseplate_step_height.setToolTip(
            self._parameter_tooltip(
                self.tr("Z height where the bottom baseplate step or V-groove is generated."),
                self.tr(
                    "Current range: {minimum:.2f}-{maximum:.2f} mm. "
                    "The value is rounded up to the current layer-height grid before preview, STL export, and G-code export."
                ).format(minimum=layer_height, maximum=baseplate_max_mm),
            )
        )
        if self.baseplate_step_height.value() < layer_height:
            self.baseplate_step_height.setValue(layer_height)
        elif self.baseplate_step_height.value() > baseplate_max_mm:
            self.baseplate_step_height.setValue(baseplate_max_mm)

    def _toggle_panel_step_controls(self, enabled: bool):
        """切换面板台阶控件的启用状态"""
        self.panel_step_height.setEnabled(enabled)
        self.panel_step_width.setEnabled(enabled)
        self.panel_step_v_groove.setEnabled(enabled)
        self._sync_step_speed_control_state()

    def _toggle_baseplate_step_controls(self, enabled: bool):
        """切换底板台阶控件的启用状态"""
        self.baseplate_step_height.setEnabled(enabled)
        self.baseplate_step_width.setEnabled(enabled)
        self.baseplate_step_v_groove.setEnabled(enabled)

        self._sync_step_speed_control_state()

    def _sync_step_speed_control_state(self) -> None:
        """Keep the shared step speed control enabled while any step mode is active."""
        if not hasattr(self, "step_speed"):
            return
        self.step_speed.setEnabled(
            self.panel_step_enabled.isChecked() or self.baseplate_step_enabled.isChecked()
        )

    def _create_skirt_group(self) -> QGroupBox:
        """创建防翘裙边参数组"""
        group = QGroupBox(self.tr("Anti-Warping Skirt"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.skirt_enabled = QCheckBox(self.tr("Enable Anti-Warping Skirt"))
        self.skirt_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.skirt_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        self.skirt_height = self._create_double_spinbox()
        self.skirt_height.setRange(0.2, 10)
        self.skirt_height.setValue(0.3)
        self.skirt_height.setSingleStep(0.1)
        self.skirt_height.setSuffix(" mm")
        self.skirt_height.setEnabled(False)
        self.skirt_height.setToolTip(
            self._z_height_tooltip(
                self.tr("Printed vertical height of the anti-warping skirt around the shell."),
                0.2,
                10.0,
            )
        )
        self.skirt_height.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "skirt", self.tr("Skirt Height:"), self.skirt_height)

        self.skirt_speed = self._create_double_spinbox(decimals=1)
        self.skirt_speed.setRange(5.0, 200.0)
        self.skirt_speed.setValue(20.0)
        self.skirt_speed.setSingleStep(1.0)
        self.skirt_speed.setSuffix(" mm/s")
        self.skirt_speed.setEnabled(False)
        self.skirt_speed.valueChanged.connect(self._on_param_changed)

        self.skirt_offset = self._create_double_spinbox()
        self.skirt_offset.setRange(0, 1.0)
        self.skirt_offset.setValue(0.12)
        self.skirt_offset.setSingleStep(0.1)
        self.skirt_offset.setSuffix(" mm")
        self.skirt_offset.setEnabled(False)
        self.skirt_offset.setToolTip(
            self._parameter_tooltip(
                self.tr("XY breakaway gap between the shell wall and the skirt."),
                self.tr("0.00-1.00 mm. Use 0 for a touching skirt; larger values make removal easier."),
            )
        )
        self.skirt_offset.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "gap", self.tr("Wall Gap:"), self.skirt_offset)

        direction_layout = QHBoxLayout()
        direction_layout.setContentsMargins(0, 0, 0, 0)
        self.skirt_outer_enabled = QCheckBox(self.tr("Outer"))
        self.skirt_outer_enabled.setChecked(True)
        self.skirt_outer_enabled.setEnabled(False)
        self.skirt_outer_enabled.stateChanged.connect(self._on_param_changed)
        direction_layout.addWidget(self.skirt_outer_enabled)
        self.skirt_inner_enabled = QCheckBox(self.tr("Inner"))
        self.skirt_inner_enabled.setEnabled(False)
        self.skirt_inner_enabled.stateChanged.connect(self._on_param_changed)
        direction_layout.addWidget(self.skirt_inner_enabled)
        direction_layout.addStretch()
        self._add_icon_row(form, "direction", self.tr("Skirt Sides:"), direction_layout)

        layout.addLayout(form)

        self.skirt_enabled.stateChanged.connect(
            lambda: self._toggle_skirt_controls(self.skirt_enabled.isChecked())
        )

        return group

    def _toggle_skirt_controls(self, enabled: bool):
        """切换裙边控件的启用状态"""
        self.skirt_height.setEnabled(enabled)
        self.skirt_speed.setEnabled(enabled)
        self.skirt_offset.setEnabled(enabled)
        self.skirt_outer_enabled.setEnabled(enabled)
        self.skirt_inner_enabled.setEnabled(enabled)

    def _create_connected_group(self) -> QGroupBox:
        """创建连襟字参数组"""
        group = QGroupBox(self.tr("Connected Letters"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.connected_enabled = QCheckBox(self.tr("Enable Connected Letters"))
        self.connected_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.connected_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        # 连襟类型
        self.connected_type = GuardedComboBox()
        self.connected_type.addItem(self.tr("Triangle"), "triangle")
        self.connected_type.addItem(self.tr("Diamond"), "diamond")
        self.connected_type.setEnabled(False)
        self.connected_type.currentIndexChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "connected", self.tr("Connection Type:"), self.connected_type)

        # 自动检测
        self.connected_auto_detect = QCheckBox(self.tr("Auto Detect Connection Points"))
        self.connected_auto_detect.setChecked(True)
        self.connected_auto_detect.setEnabled(False)
        self.connected_auto_detect.stateChanged.connect(self._on_param_changed)
        form.addRow("", self.connected_auto_detect)

        # 连襟宽度
        self.connected_width = self._create_double_spinbox()
        self.connected_width.setRange(1, 50)
        self.connected_width.setValue(5)
        self.connected_width.setSuffix(" mm")
        self.connected_width.setEnabled(False)
        self.connected_width.setToolTip(
            self._parameter_tooltip(
                self.tr("XY width of the bridge that connects neighboring letters."),
                self.tr("1.00-50.00 mm. Choose a value wide enough for strength without covering visible letter gaps."),
            )
        )
        self.connected_width.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "dimension", self.tr("Connection Width:"), self.connected_width)

        # 斜边高度
        self.connected_height = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.connected_height,
            0.1,
            20.0,
            4.5,
            enabled=False,
            meaning=self.tr("Vertical bevel height used on the connected-letter bridge."),
        )
        self.connected_height.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "bevel", self.tr("Bevel Height:"), self.connected_height)

        # 底座高度
        self.connected_base_height = self._create_double_spinbox()
        self._configure_z_height_spin(
            self.connected_base_height,
            0.1,
            20.0,
            4.5,
            enabled=False,
            meaning=self.tr("Vertical base height of the connected-letter bridge before beveling."),
        )
        self.connected_base_height.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "baseplate", self.tr("Base Height:"), self.connected_base_height)

        # 支撑偏移
        self.connected_support_offset = self._create_double_spinbox()
        self.connected_support_offset.setRange(0, 10)
        self.connected_support_offset.setValue(2.5)
        self.connected_support_offset.setSuffix(" mm")
        self.connected_support_offset.setEnabled(False)
        self.connected_support_offset.setToolTip(
            self._parameter_tooltip(
                self.tr("XY offset used to place extra bridge support away from the detected connection point."),
                self.tr("0.00-10.00 mm. Use smaller values for tight letter gaps and larger values for stronger support."),
            )
        )
        self.connected_support_offset.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(form, "clearance", self.tr("Support Offset:"), self.connected_support_offset)

        layout.addLayout(form)

        self.connected_enabled.stateChanged.connect(
            lambda: self._toggle_connected_controls(self.connected_enabled.isChecked())
        )

        return group

    def _toggle_connected_controls(self, enabled: bool):
        """切换连襟字控件的启用状态"""
        self.connected_type.setEnabled(enabled)
        self.connected_auto_detect.setEnabled(enabled)
        self.connected_width.setEnabled(enabled)
        self.connected_height.setEnabled(enabled)
        self.connected_base_height.setEnabled(enabled)
        self.connected_support_offset.setEnabled(enabled)

    def _toggle_wrap_controls(self, enabled: bool):
        """Toggle edge wrap controls."""
        self.wrap_width.setEnabled(enabled)
        self.wrap_height.setEnabled(enabled)
        self.wrap_dir_inner.setEnabled(enabled)
        self.wrap_dir_outer.setEnabled(enabled)

    def _toggle_outline_controls(self, enabled: bool):
        """Toggle outline controls."""
        self.outline_width.setEnabled(enabled)
        self.outline_height.setEnabled(enabled)
        self.outline_offset.setEnabled(enabled)
        self.outline_dir_inner.setEnabled(enabled)
        self.outline_dir_outer.setEnabled(enabled)

    def _create_edge_wrap_group(self) -> QGroupBox:
        """创建包边/勾边参数组"""
        group = QGroupBox(self.tr("Edge Wrap/Outline"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 包边设置
        self.wrap_enabled = QCheckBox(self.tr("Enable Edge Wrap"))
        self.wrap_enabled.setObjectName("wrap_enabled")
        self.wrap_enabled.setVisible(False)
        self.wrap_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.wrap_enabled)

        wrap_form = QFormLayout()
        wrap_form.setSpacing(8)

        # 包边方向单选按钮
        wrap_dir_layout = QHBoxLayout()
        self.wrap_dir_inner = QRadioButton(self.tr("Inner"))
        self.wrap_dir_outer = QRadioButton(self.tr("Outer"))
        self.wrap_dir_inner.setChecked(True)  # 默认内部
        self.wrap_dir_inner.setEnabled(False)
        self.wrap_dir_outer.setEnabled(False)
        self.wrap_dir_group = QButtonGroup(self)
        self.wrap_dir_group.addButton(self.wrap_dir_inner, 0)
        self.wrap_dir_group.addButton(self.wrap_dir_outer, 1)
        self.wrap_dir_group.buttonClicked.connect(self._on_param_changed)
        wrap_dir_layout.addWidget(self.wrap_dir_inner)
        wrap_dir_layout.addWidget(self.wrap_dir_outer)
        wrap_dir_layout.addStretch()
        self._add_icon_row(wrap_form, "direction", self.tr("Wrap Direction:"), wrap_dir_layout)

        self.wrap_width = self._create_double_spinbox()
        self.wrap_width.setRange(0.5, 10)
        self.wrap_width.setValue(3.0)
        self.wrap_width.setSingleStep(0.1)
        self.wrap_width.setSuffix(" mm")
        self.wrap_width.setEnabled(False)
        self._add_icon_row(wrap_form, "wrap", self.tr("Wrap Width:"), self.wrap_width)

        self.wrap_height = self._create_double_spinbox()
        self.wrap_height.setRange(0.5, 20)
        self.wrap_height.setValue(3.0)
        self.wrap_height.setSingleStep(0.5)
        self.wrap_height.setSuffix(" mm")
        self.wrap_height.setEnabled(False)
        self._add_icon_row(wrap_form, "height", self.tr("Wrap Height:"), self.wrap_height)

        layout.addLayout(wrap_form)

        self.wrap_enabled.stateChanged.connect(
            lambda: self._toggle_wrap_controls(self.wrap_enabled.isChecked())
        )

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {COLORS.border_default};")
        layout.addWidget(line)

        # 勾边设置
        self.outline_enabled = QCheckBox(self.tr("Enable Outline"))
        self.outline_enabled.setObjectName("outline_enabled")
        self.outline_enabled.setVisible(False)
        self.outline_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.outline_enabled)

        outline_form = QFormLayout()
        outline_form.setSpacing(8)

        # 勾边方向单选按钮
        outline_dir_layout = QHBoxLayout()
        self.outline_dir_inner = QRadioButton(self.tr("Inner"))
        self.outline_dir_outer = QRadioButton(self.tr("Outer"))
        self.outline_dir_inner.setChecked(True)  # 默认内部
        self.outline_dir_inner.setEnabled(False)
        self.outline_dir_outer.setEnabled(False)
        self.outline_dir_group = QButtonGroup(self)
        self.outline_dir_group.addButton(self.outline_dir_inner, 0)
        self.outline_dir_group.addButton(self.outline_dir_outer, 1)
        self.outline_dir_group.buttonClicked.connect(self._on_param_changed)
        outline_dir_layout.addWidget(self.outline_dir_inner)
        outline_dir_layout.addWidget(self.outline_dir_outer)
        outline_dir_layout.addStretch()
        self._add_icon_row(outline_form, "direction", self.tr("Outline Direction:"), outline_dir_layout)

        self.outline_width = self._create_double_spinbox()
        self.outline_width.setRange(0.3, 5)
        self.outline_width.setValue(3.0)
        self.outline_width.setSingleStep(0.1)
        self.outline_width.setSuffix(" mm")
        self.outline_width.setEnabled(False)
        self._add_icon_row(outline_form, "outline", self.tr("Outline Width:"), self.outline_width)

        self.outline_height = self._create_double_spinbox()
        self.outline_height.setRange(0.3, 10)
        self.outline_height.setValue(3.0)
        self.outline_height.setSingleStep(0.1)
        self.outline_height.setSuffix(" mm")
        self.outline_height.setEnabled(False)
        self._add_icon_row(outline_form, "height", self.tr("Outline Height:"), self.outline_height)

        self.outline_offset = self._create_double_spinbox()
        self.outline_offset.setRange(-5, 5)
        self.outline_offset.setValue(0.0)
        self.outline_offset.setSingleStep(0.1)
        self.outline_offset.setSuffix(" mm")
        self.outline_offset.setEnabled(False)
        self._add_icon_row(outline_form, "clearance", self.tr("Outline Offset:"), self.outline_offset)

        layout.addLayout(outline_form)

        self.outline_enabled.stateChanged.connect(
            lambda: self._toggle_outline_controls(self.outline_enabled.isChecked())
        )

        # 包边和勾边互斥
        self.wrap_enabled.stateChanged.connect(self._on_wrap_outline_mutual_exclusive)
        self.outline_enabled.stateChanged.connect(self._on_wrap_outline_mutual_exclusive)
        self.wrap_enabled.stateChanged.connect(self._sync_bottom_mode_from_controls)
        self.outline_enabled.stateChanged.connect(self._sync_bottom_mode_from_controls)

        return group

    def _create_speed_group(self) -> QGroupBox:
        """创建速度参数组"""
        group = QGroupBox(self.tr("Speed Settings"))
        layout = QFormLayout(group)
        layout.setSpacing(8)

        # 打印速度
        self.print_speed = self._create_int_spinbox()
        self.print_speed.setRange(10, 200)
        self.print_speed.setValue(50)
        self.print_speed.setSuffix(" mm/s")
        self.print_speed.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "speed", self.tr("Print Speed:"), self.print_speed)

        # 空走速度
        self.travel_speed = self._create_int_spinbox()
        self.travel_speed.setRange(50, 300)
        self.travel_speed.setValue(150)
        self.travel_speed.setSuffix(" mm/s")
        self.travel_speed.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "speed", self.tr("Travel Speed:"), self.travel_speed)

        # 首层速度
        self.first_layer_speed = self._create_int_spinbox()
        self.first_layer_speed.setRange(5, 50)
        self.first_layer_speed.setValue(20)
        self.first_layer_speed.setSuffix(" mm/s")
        self.first_layer_speed.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "layer", self.tr("First Layer Speed:"), self.first_layer_speed)

        self._add_icon_row(layout, "skirt", self.tr("Skirt Speed:"), self.skirt_speed)
        self._add_icon_row(layout, "step", self.tr("Step Speed:"), self.step_speed)

        return group

    def _create_temperature_group(self) -> QGroupBox:
        """创建温度参数组"""
        group = QGroupBox(self.tr("Temperature Settings"))
        layout = QFormLayout(group)
        layout.setSpacing(8)

        self.first_layer_nozzle_temp = self._create_int_spinbox()
        self.first_layer_nozzle_temp.setRange(0, 400)
        self.first_layer_nozzle_temp.setValue(220)
        self.first_layer_nozzle_temp.setSuffix(" °C")
        self.first_layer_nozzle_temp.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "temperature", self.tr("First Layer Nozzle Temperature:"), self.first_layer_nozzle_temp)

        self.other_layer_nozzle_temp = self._create_int_spinbox()
        self.other_layer_nozzle_temp.setRange(0, 400)
        self.other_layer_nozzle_temp.setValue(220)
        self.other_layer_nozzle_temp.setSuffix(" °C")
        self.other_layer_nozzle_temp.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "temperature", self.tr("Other Layers Nozzle Temperature:"), self.other_layer_nozzle_temp)

        self.first_layer_bed_temp = self._create_int_spinbox()
        self.first_layer_bed_temp.setRange(0, 200)
        self.first_layer_bed_temp.setValue(60)
        self.first_layer_bed_temp.setSuffix(" °C")
        self.first_layer_bed_temp.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "temperature", self.tr("First Layer Bed Temperature:"), self.first_layer_bed_temp)

        self.other_layer_bed_temp = self._create_int_spinbox()
        self.other_layer_bed_temp.setRange(0, 200)
        self.other_layer_bed_temp.setValue(60)
        self.other_layer_bed_temp.setSuffix(" °C")
        self.other_layer_bed_temp.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "temperature", self.tr("Other Layers Bed Temperature:"), self.other_layer_bed_temp)

        return group

    def _create_cooling_group(self) -> QGroupBox:
        """Create cooling parameters group."""
        group = QGroupBox(self.tr("Cooling Settings"))
        layout = QFormLayout(group)
        layout.setSpacing(8)

        self.first_layer_fan_percent = self._create_int_spinbox()
        self.first_layer_fan_percent.setRange(0, 100)
        self.first_layer_fan_percent.setValue(0)
        self.first_layer_fan_percent.setSuffix(" %")
        self.first_layer_fan_percent.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "fan", self.tr("First Layer Fan Speed:"), self.first_layer_fan_percent)

        self.other_layer_fan_percent = self._create_int_spinbox()
        self.other_layer_fan_percent.setRange(0, 100)
        self.other_layer_fan_percent.setValue(100)
        self.other_layer_fan_percent.setSuffix(" %")
        self.other_layer_fan_percent.valueChanged.connect(self._on_param_changed)
        self._add_icon_row(layout, "fan", self.tr("Other Layers Fan Speed:"), self.other_layer_fan_percent)

        return group

    def _on_wall_mode_selected(self, mode_id: int) -> None:
        edge_type = self._wall_mode_edge_types.get(mode_id)
        if edge_type is None:
            return
        edge_index = self.edge_type_combo.findData(edge_type)
        if edge_index >= 0 and edge_index != self.edge_type_combo.currentIndex():
            self.edge_type_combo.setCurrentIndex(edge_index)
        else:
            self._sync_wall_mode_from_controls()

    def _sync_wall_mode_from_controls(self) -> None:
        if not hasattr(self, "wall_mode_group"):
            return
        edge_type = self.edge_type_combo.currentData()
        for mode_id, candidate in self._wall_mode_edge_types.items():
            if candidate == edge_type:
                self._set_button_group_checked(self.wall_mode_group, mode_id)
                break
        self._sync_shape_mode_group_visibility()

    def _top_mode_from_controls(self) -> int:
        if self.top_face_enabled.isChecked():
            return self.TOP_MODE_FACE
        if self.panel_step_enabled.isChecked():
            if self.panel_step_v_groove.isChecked():
                return self.TOP_MODE_PANEL_V_GROOVE
            return self.TOP_MODE_PANEL_STEP
        return self.TOP_MODE_NONE

    def _top_mode_from_params(self, params: SliceParams) -> int:
        if params.top_face.enabled:
            return self.TOP_MODE_FACE
        if params.step.panel_step_enabled:
            if params.step.panel_step_is_v_groove:
                return self.TOP_MODE_PANEL_V_GROOVE
            return self.TOP_MODE_PANEL_STEP
        return self.TOP_MODE_NONE

    def _on_top_mode_selected(self, mode_id: int) -> None:
        self._apply_top_mode(mode_id, emit_changed=True)

    def _apply_top_mode(self, mode_id: int, *, emit_changed: bool) -> None:
        self._set_checked_silent(self.top_face_enabled, mode_id == self.TOP_MODE_FACE)
        self._set_checked_silent(
            self.panel_step_enabled,
            mode_id in (self.TOP_MODE_PANEL_STEP, self.TOP_MODE_PANEL_V_GROOVE),
        )
        self._set_checked_silent(
            self.panel_step_v_groove,
            mode_id == self.TOP_MODE_PANEL_V_GROOVE,
        )
        self._toggle_top_face_controls(self.top_face_enabled.isChecked())
        self._toggle_panel_step_controls(self.panel_step_enabled.isChecked())
        self._set_button_group_checked(self.top_mode_group, mode_id)
        self._sync_shape_mode_group_visibility()
        if emit_changed:
            self._on_param_changed()

    def _sync_top_mode_from_controls(self) -> None:
        if not hasattr(self, "top_mode_group"):
            return
        self._apply_top_mode(self._top_mode_from_controls(), emit_changed=False)

    def _bottom_mode_for_sender(self, sender: QWidget) -> Optional[int]:
        if sender is self.bottom_face_enabled:
            return self.BOTTOM_MODE_FACE
        if sender is self.baseplate_step_enabled:
            return (
                self.BOTTOM_MODE_BASEPLATE_V_GROOVE
                if self.baseplate_step_v_groove.isChecked()
                else self.BOTTOM_MODE_BASEPLATE_STEP
            )
        if sender is self.baseplate_step_v_groove and self.baseplate_step_enabled.isChecked():
            return (
                self.BOTTOM_MODE_BASEPLATE_V_GROOVE
                if self.baseplate_step_v_groove.isChecked()
                else self.BOTTOM_MODE_BASEPLATE_STEP
            )
        if sender is self.light_slot_enabled:
            return self.BOTTOM_MODE_LIGHT_SLOT
        if sender is self.wrap_enabled:
            return self.BOTTOM_MODE_EDGE_WRAP
        if sender is self.outline_enabled:
            return self.BOTTOM_MODE_OUTLINE
        return None

    def _bottom_mode_from_controls(self) -> int:
        if self.bottom_face_enabled.isChecked() and not self._is_u_shape_edge_selected():
            return self.BOTTOM_MODE_FACE
        if self.baseplate_step_enabled.isChecked():
            if self.baseplate_step_v_groove.isChecked():
                return self.BOTTOM_MODE_BASEPLATE_V_GROOVE
            return self.BOTTOM_MODE_BASEPLATE_STEP
        if self.light_slot_enabled.isChecked():
            return self.BOTTOM_MODE_LIGHT_SLOT
        if self.wrap_enabled.isChecked():
            return self.BOTTOM_MODE_EDGE_WRAP
        if self.outline_enabled.isChecked():
            return self.BOTTOM_MODE_OUTLINE
        return self.BOTTOM_MODE_NONE

    def _bottom_mode_from_params(self, params: SliceParams) -> int:
        if params.bottom_face.enabled and params.shell.edge_type != EdgeType.U_SHAPED:
            return self.BOTTOM_MODE_FACE
        if params.step.baseplate_step_enabled:
            if params.step.baseplate_step_is_v_groove:
                return self.BOTTOM_MODE_BASEPLATE_V_GROOVE
            return self.BOTTOM_MODE_BASEPLATE_STEP
        if params.light_slot.enabled:
            return self.BOTTOM_MODE_LIGHT_SLOT
        if params.edge_wrap.wrap_enabled:
            return self.BOTTOM_MODE_EDGE_WRAP
        if params.edge_wrap.outline_enabled:
            return self.BOTTOM_MODE_OUTLINE
        return self.BOTTOM_MODE_NONE

    def _on_bottom_mode_selected(self, mode_id: int) -> None:
        self._apply_bottom_mode(mode_id, emit_changed=True)

    def _apply_bottom_mode(self, mode_id: int, *, emit_changed: bool) -> None:
        if mode_id == self.BOTTOM_MODE_FACE and self._is_u_shape_edge_selected():
            mode_id = self.BOTTOM_MODE_NONE

        self._set_checked_silent(self.bottom_face_enabled, mode_id == self.BOTTOM_MODE_FACE)
        self._set_checked_silent(
            self.baseplate_step_enabled,
            mode_id in (
                self.BOTTOM_MODE_BASEPLATE_STEP,
                self.BOTTOM_MODE_BASEPLATE_V_GROOVE,
            ),
        )
        self._set_checked_silent(
            self.baseplate_step_v_groove,
            mode_id == self.BOTTOM_MODE_BASEPLATE_V_GROOVE,
        )
        self._set_checked_silent(self.light_slot_enabled, mode_id == self.BOTTOM_MODE_LIGHT_SLOT)
        self._set_checked_silent(self.wrap_enabled, mode_id == self.BOTTOM_MODE_EDGE_WRAP)
        self._set_checked_silent(self.outline_enabled, mode_id == self.BOTTOM_MODE_OUTLINE)

        self._toggle_bottom_face_controls(self.bottom_face_enabled.isChecked())
        self._toggle_baseplate_step_controls(self.baseplate_step_enabled.isChecked())
        self._toggle_light_slot_controls(self.light_slot_enabled.isChecked())
        self._toggle_wrap_controls(self.wrap_enabled.isChecked())
        self._toggle_outline_controls(self.outline_enabled.isChecked())
        self._set_button_group_checked(self.bottom_mode_group, mode_id)
        self._sync_shape_mode_group_visibility()
        if emit_changed:
            self._on_param_changed()

    def _sync_bottom_mode_from_controls(self) -> None:
        if not hasattr(self, "bottom_mode_group"):
            return
        sender = self.sender()
        sender_mode = None
        if isinstance(sender, QCheckBox):
            sender_mode = self._bottom_mode_for_sender(sender)
            if sender_mode is not None and (
                sender.isChecked()
                or sender is self.baseplate_step_v_groove
            ):
                self._apply_bottom_mode(sender_mode, emit_changed=True)
                return
        self._apply_bottom_mode(self._bottom_mode_from_controls(), emit_changed=False)

    def _sync_shape_mode_group_visibility(self) -> None:
        if hasattr(self, "top_face_group"):
            top_mode = self._top_mode_from_controls()
            self.top_face_group.setVisible(top_mode == self.TOP_MODE_FACE)
            self.panel_step_group.setVisible(
                top_mode in (self.TOP_MODE_PANEL_STEP, self.TOP_MODE_PANEL_V_GROOVE)
            )
        if hasattr(self, "bottom_face_group"):
            bottom_mode = self._bottom_mode_from_controls()
            self.bottom_face_group.setVisible(bottom_mode == self.BOTTOM_MODE_FACE)
            self.baseplate_step_group.setVisible(
                bottom_mode in (
                    self.BOTTOM_MODE_BASEPLATE_STEP,
                    self.BOTTOM_MODE_BASEPLATE_V_GROOVE,
                )
            )
            self.light_slot_group.setVisible(bottom_mode == self.BOTTOM_MODE_LIGHT_SLOT)
            self.edge_wrap_group.setVisible(
                bottom_mode in (self.BOTTOM_MODE_EDGE_WRAP, self.BOTTOM_MODE_OUTLINE)
            )

    def _on_edge_type_changed(self, index: int):
        """边缘类型变化"""
        edge_type = self.edge_type_combo.currentData()

        # 显示/隐藏对应的参数组
        self.bevel_params_widget.setVisible(edge_type == EdgeType.BEVELED)
        self.u_shape_params_widget.setVisible(edge_type == EdgeType.U_SHAPED)
        self.custom_edge_widget.setVisible(edge_type == EdgeType.CUSTOM)
        self._sync_wall_mode_from_controls()
        self._sync_bottom_face_availability()

        # 如果切换到异形边且没有选择预设，自动加载默认预设
        if edge_type == EdgeType.CUSTOM and self._current_profile is None:
            preset_name = self.preset_selector.get_selected_preset()
            if preset_name:
                self._on_preset_changed(preset_name)

        self._on_param_changed()

    def _on_param_changed(self):
        """参数变化处理"""
        if getattr(self, "_committing_numeric_edits", False):
            return
        self._update_params()
        self.params_changed.emit()

    def _spinbox_has_pending_edit(self, spinbox: QAbstractSpinBox) -> bool:
        """Return whether a standard spinbox still has uncommitted text."""
        line_edit = spinbox.lineEdit()
        if line_edit is None:
            return False
        committed = f"{spinbox.textFromValue(spinbox.value())}{spinbox.suffix()}".strip()
        return line_edit.text().strip() != committed

    def _commit_pending_numeric_edits(self) -> None:
        """Flush in-progress text edits from standard spinboxes before reading values."""
        numeric_widgets = [
            self.height_spin,
            self.layer_height_spin,
            self.width_line_spin,
            self.wall_thickness_spin,
            self.bevel_width_spin,
            self.baseplate_spin,
            self.panel_thickness_spin,
            self.u_arc_height_spin,
            self.u_bottom_layers_spin,
            self.dxf_outer_clearance_spin,
            self.dxf_hole_clearance_spin,
            self.dxf_laser_kerf_spin,
            self.skirt_height,
            self.skirt_speed,
            self.skirt_offset,
            self.connected_width,
            self.connected_height,
            self.connected_base_height,
            self.connected_support_offset,
            self.wrap_width,
            self.wrap_height,
            self.outline_width,
            self.outline_height,
            self.outline_offset,
            self.panel_step_height,
            self.panel_step_width,
            self.baseplate_step_height,
            self.baseplate_step_width,
            self.step_speed,
            self.bottom_face_thickness,
            self.light_slot_width,
            self.light_slot_depth,
            self.light_slot_floor_layers,
            self.light_slot_wall_gap,
            self.light_slot_min_hole_span,
            self.top_face_thickness,
            self.print_speed,
            self.travel_speed,
            self.first_layer_speed,
            self.first_layer_nozzle_temp,
            self.other_layer_nozzle_temp,
            self.first_layer_bed_temp,
            self.other_layer_bed_temp,
            self.first_layer_fan_percent,
            self.other_layer_fan_percent,
            self.prime_tower_center_x,
            self.prime_tower_center_y,
            self.prime_tower_width,
            self.prime_tower_depth,
            self.prime_tower_infill_density,
            self.profile_bed_width,
            self.profile_bed_depth,
            self.profile_bed_height,
            self.profile_nozzle_diameter,
            self.profile_filament_diameter,
            self.profile_retract_length,
            self.profile_retract_speed,
            self.profile_z_hop_short,
            self.profile_z_hop_long,
            self.profile_long_travel_threshold,
        ]

        for row in range(self.color_change_table.rowCount()):
            height_spin = self.color_change_table.cellWidget(row, 0)
            macro_spin = self.color_change_table.cellWidget(row, 1)
            if isinstance(height_spin, QAbstractSpinBox):
                numeric_widgets.append(height_spin)
            if isinstance(macro_spin, QAbstractSpinBox):
                numeric_widgets.append(macro_spin)

        self._committing_numeric_edits = True
        try:
            previous_layer_height = self.layer_height_spin.value()
            width_line_has_pending_edit = self._spinbox_has_pending_edit(self.width_line_spin)
            width_line_is_default = math.isclose(
                self.width_line_spin.value(),
                self._derived_width_line(previous_layer_height),
                abs_tol=1e-9,
            )

            for widget in numeric_widgets:
                widget.blockSignals(True)
                widget.interpretText()
                widget.blockSignals(False)

            if (
                not math.isclose(self.layer_height_spin.value(), previous_layer_height, abs_tol=1e-9)
                and width_line_is_default
                and not width_line_has_pending_edit
            ):
                self.width_line_spin.setValue(self._derived_width_line())
            self._sync_layer_based_controls()
        finally:
            self._committing_numeric_edits = False

    def _on_wrap_outline_mutual_exclusive(self):
        """包边和勾边互斥处理"""
        sender = self.sender()
        if sender == self.wrap_enabled and self.wrap_enabled.isChecked():
            self.outline_enabled.blockSignals(True)
            self.outline_enabled.setChecked(False)
            self.outline_enabled.blockSignals(False)
            self._toggle_outline_controls(False)
        elif sender == self.outline_enabled and self.outline_enabled.isChecked():
            self.wrap_enabled.blockSignals(True)
            self.wrap_enabled.setChecked(False)
            self.wrap_enabled.blockSignals(False)
            self._toggle_wrap_controls(False)

    def _update_params(self):
        """更新内部参数"""
        self._commit_pending_numeric_edits()
        self._snap_z_controls_to_layer_grid()

        # 字壳参数
        self._params.shell.height = self.height_spin.value()
        self._params.shell.layer_height = self.layer_height_spin.value()
        self._params.shell.line_width = self.width_line_spin.value()
        self._params.shell.wall_thickness = self.wall_thickness_spin.value()
        line_width = self._params.shell.line_width

        # 边缘参数
        self._params.shell.edge_type = self.edge_type_combo.currentData()
        self._params.shell.bevel_direction = self.bevel_direction_combo.currentData()
        self._params.shell.baseplate_thickness = self.baseplate_spin.value()
        self._params.shell.panel_thickness = self.panel_thickness_spin.value()
        self._params.shell.u_arc_height = self.u_arc_height_spin.value()
        self._params.shell.u_bottom_layers = self._height_to_layers(
            self.u_bottom_layers_spin.value(),
            minimum=0,
        )
        self._params.shell.dxf_outer_clearance = self.dxf_outer_clearance_spin.value()
        self._params.shell.dxf_hole_clearance = self.dxf_hole_clearance_spin.value()
        self._params.shell.dxf_laser_kerf = self.dxf_laser_kerf_spin.value()

        # 根据边缘类型设置轮廓
        if self._params.shell.edge_type == EdgeType.CUSTOM:
            # 异形边：使用模板中的原始宽度
            self._params.shell.edge_profile = self._current_profile
            if self._current_profile:
                self._params.shell.bevel_width = self._current_profile.original_width
        elif self._params.shell.edge_type == EdgeType.U_SHAPED:
            self._params.shell.bevel_width = self._params.shell.u_arc_height
            self._params.shell.edge_profile = None
        else:
            # 直边或斜边
            self._params.shell.bevel_width = self.bevel_width_spin.value()
            self._params.shell.edge_profile = None

        # 换色参数
        self._params.color.enabled = self.color_enabled.isChecked()
        self._params.color.change_points = self._get_color_change_rows()

        # Prime tower 参数
        self._params.prime_tower.enabled = self.prime_tower_enabled.isChecked()
        self._params.prime_tower.center_x = self.prime_tower_center_x.value()
        self._params.prime_tower.center_y = self.prime_tower_center_y.value()
        self._params.prime_tower.width = self.prime_tower_width.value()
        self._params.prime_tower.depth = self.prime_tower_depth.value()
        self._params.prime_tower.infill_density_percent = self.prime_tower_infill_density.value()

        # 台阶参数
        # 面板台阶（顶部）
        self._params.step.panel_step_enabled = self.panel_step_enabled.isChecked()
        self._params.step.panel_step_height = self.panel_step_height.value()
        self._params.step.panel_step_width = self.panel_step_width.value()
        self._params.step.panel_step_is_v_groove = self.panel_step_v_groove.isChecked()

        # 底板台阶（底部）
        self._params.step.baseplate_step_enabled = self.baseplate_step_enabled.isChecked()
        self._params.step.baseplate_step_height = self.baseplate_step_height.value()
        self._params.step.baseplate_step_width = self.baseplate_step_width.value()
        self._params.step.baseplate_step_is_v_groove = self.baseplate_step_v_groove.isChecked()

        # 兼容旧参数
        self._params.step.top_step_enabled = self.panel_step_enabled.isChecked()
        self._params.step.top_step_height = self.panel_step_height.value()
        self._params.step.top_step_width = self.panel_step_width.value()
        self._params.step.bottom_groove_enabled = self.baseplate_step_enabled.isChecked()
        self._params.step.bottom_groove_height = self.baseplate_step_height.value()
        self._params.step.bottom_groove_depth = self.baseplate_step_width.value()
        self._params.step.print_speed = self.step_speed.value()

        # 启用台阶总开关
        self._params.step.enabled = (
            self._params.step.panel_step_enabled or
            self._params.step.baseplate_step_enabled or
            len(self._params.step.steps) > 0
        )

        # 裙边参数
        self._params.skirt.enabled = self.skirt_enabled.isChecked()
        self._params.skirt.height = self.skirt_height.value()
        self._params.skirt.speed = self.skirt_speed.value()
        self._params.skirt.offset = self.skirt_offset.value()
        self._params.skirt.outer_enabled = self.skirt_outer_enabled.isChecked()
        self._params.skirt.inner_enabled = self.skirt_inner_enabled.isChecked()
        self._params.skirt.is_outer = self.skirt_outer_enabled.isChecked()

        # 连襟字参数
        self._params.connected.enabled = self.connected_enabled.isChecked()
        self._params.connected.type = self.connected_type.currentData()
        self._params.connected.auto_detect = self.connected_auto_detect.isChecked()
        self._params.connected.width = self.connected_width.value()
        self._params.connected.height = self.connected_height.value()
        self._params.connected.base_height = self.connected_base_height.value()
        self._params.connected.support_offset = self.connected_support_offset.value()

        # 包边勾边参数
        self._params.edge_wrap.wrap_enabled = self.wrap_enabled.isChecked()
        self._params.edge_wrap.wrap_width = self.wrap_width.value()
        self._params.edge_wrap.wrap_height = self.wrap_height.value()
        self._params.edge_wrap.wrap_direction = (
            EdgeDirection.INNER if self.wrap_dir_inner.isChecked()
            else EdgeDirection.OUTER
        )
        self._params.edge_wrap.outline_enabled = self.outline_enabled.isChecked()
        self._params.edge_wrap.outline_width = self.outline_width.value()
        self._params.edge_wrap.outline_height = self.outline_height.value()
        self._params.edge_wrap.outline_offset = self.outline_offset.value()
        self._params.edge_wrap.outline_direction = (
            EdgeDirection.INNER if self.outline_dir_inner.isChecked()
            else EdgeDirection.OUTER
        )

        # 速度参数
        self._params.speed.print_speed = self.print_speed.value()
        self._params.speed.travel_speed = self.travel_speed.value()
        self._params.speed.first_layer_speed = self.first_layer_speed.value()

        # 同步到G-code参数
        self._params.gcode.print_speed = self.print_speed.value()
        self._params.gcode.travel_speed = self.travel_speed.value()
        self._params.gcode.first_layer_speed = self.first_layer_speed.value()
        self._params.gcode.first_layer_nozzle_temp = self.first_layer_nozzle_temp.value()
        self._params.gcode.other_layer_nozzle_temp = self.other_layer_nozzle_temp.value()
        self._params.gcode.first_layer_bed_temp = self.first_layer_bed_temp.value()
        self._params.gcode.other_layer_bed_temp = self.other_layer_bed_temp.value()
        self._params.gcode.first_layer_fan_percent = self.first_layer_fan_percent.value()
        self._params.gcode.other_layer_fan_percent = self.other_layer_fan_percent.value()
        apply_printer_profile_to_params(self._params, self._profile_from_form())
        wall_plan = resolve_shell_wall_plan(
            self._params.shell.wall_thickness,
            line_width,
            self._params.shell.layer_height,
            self._params.machine.nozzle_diameter,
            strict=False,
        )
        self._params.shell.wall_count = wall_plan.wall_count
        self._params.shell.line_width = wall_plan.line_width
        self._params.shell.wall_thickness = wall_plan.wall_thickness
        if not math.isclose(
            self.wall_thickness_spin.value(),
            wall_plan.wall_thickness,
            abs_tol=1e-9,
        ):
            self._set_spin_value_silent(
                self.wall_thickness_spin,
                min(
                    max(wall_plan.wall_thickness, self.wall_thickness_spin.minimum()),
                    self.wall_thickness_spin.maximum(),
                ),
            )

        # 底面封闭参数
        self._params.bottom_face.enabled = (
            self.bottom_face_enabled.isChecked()
            and self._params.shell.edge_type != EdgeType.U_SHAPED
        )
        self._params.bottom_face.thickness = self.bottom_face_thickness.value()
        self._params.bottom_face.screw_hole_diameter = self.bottom_face_screw_hole_diameter.value()

        # 灯槽参数
        self._params.light_slot.enabled = self.light_slot_enabled.isChecked()
        self._params.light_slot.width = self.light_slot_width.value()
        self._params.light_slot.depth = self.light_slot_depth.value()
        self._params.light_slot.floor_layers = self._height_to_layers(
            self.light_slot_floor_layers.value(),
            minimum=1,
        )
        self._params.light_slot.wall_gap = self.light_slot_wall_gap.value()
        self._params.light_slot.outer_enabled = self.light_slot_outer_enabled.isChecked()
        self._params.light_slot.hole_enabled = self.light_slot_hole_enabled.isChecked()
        self._params.light_slot.auto_skip_small_holes = self.light_slot_auto_skip_small_holes.isChecked()
        self._params.light_slot.min_hole_span = self.light_slot_min_hole_span.value()

        # 顶面封闭参数
        self._params.top_face.enabled = self.top_face_enabled.isChecked()
        self._params.top_face.thickness = self.top_face_thickness.value()

    def get_params(self) -> SliceParams:
        """获取当前参数"""
        self._update_params()
        return self._params

    def set_params(self, params: SliceParams):
        """设置参数"""
        params = normalize_slice_params(params, strict_wall=False)
        prime_tower_enabled = params.prime_tower.enabled
        prime_tower_center_x = params.prime_tower.center_x
        prime_tower_center_y = params.prime_tower.center_y
        prime_tower_width = params.prime_tower.width
        prime_tower_depth = params.prime_tower.depth
        prime_tower_infill_density = params.prime_tower.infill_density_percent
        panel_step_enabled = params.step.panel_step_enabled
        panel_step_height = params.step.panel_step_height
        panel_step_width = params.step.panel_step_width
        panel_step_is_v_groove = params.step.panel_step_is_v_groove
        baseplate_step_enabled = params.step.baseplate_step_enabled
        baseplate_step_height = params.step.baseplate_step_height
        baseplate_step_width = params.step.baseplate_step_width
        baseplate_step_is_v_groove = params.step.baseplate_step_is_v_groove
        bottom_face_enabled = params.bottom_face.enabled
        bottom_face_thickness = params.bottom_face.thickness
        bottom_face_screw_hole_diameter = params.bottom_face.screw_hole_diameter
        light_slot_enabled = params.light_slot.enabled
        light_slot_width = params.light_slot.width
        light_slot_depth = params.light_slot.depth
        light_slot_floor_layers = params.light_slot.floor_layers
        light_slot_wall_gap = params.light_slot.wall_gap
        light_slot_outer_enabled = params.light_slot.outer_enabled
        light_slot_hole_enabled = params.light_slot.hole_enabled
        light_slot_auto_skip_small_holes = params.light_slot.auto_skip_small_holes
        light_slot_min_hole_span = params.light_slot.min_hole_span
        top_face_enabled = params.top_face.enabled
        top_face_thickness = params.top_face.thickness
        top_mode = self._top_mode_from_params(params)
        bottom_mode = self._bottom_mode_from_params(params)

        top_face_enabled = top_mode == self.TOP_MODE_FACE
        panel_step_enabled = top_mode in (
            self.TOP_MODE_PANEL_STEP,
            self.TOP_MODE_PANEL_V_GROOVE,
        )
        panel_step_is_v_groove = top_mode == self.TOP_MODE_PANEL_V_GROOVE

        bottom_face_enabled = bottom_mode == self.BOTTOM_MODE_FACE
        baseplate_step_enabled = bottom_mode in (
            self.BOTTOM_MODE_BASEPLATE_STEP,
            self.BOTTOM_MODE_BASEPLATE_V_GROOVE,
        )
        baseplate_step_is_v_groove = bottom_mode == self.BOTTOM_MODE_BASEPLATE_V_GROOVE
        light_slot_enabled = bottom_mode == self.BOTTOM_MODE_LIGHT_SLOT

        params.top_face.enabled = top_face_enabled
        params.step.panel_step_enabled = panel_step_enabled
        params.step.panel_step_is_v_groove = panel_step_is_v_groove
        params.step.top_step_enabled = panel_step_enabled
        params.step.top_step_height = panel_step_height
        params.step.top_step_width = panel_step_width
        params.bottom_face.enabled = bottom_face_enabled
        params.step.baseplate_step_enabled = baseplate_step_enabled
        params.step.baseplate_step_is_v_groove = baseplate_step_is_v_groove
        params.step.bottom_groove_enabled = baseplate_step_enabled
        params.step.bottom_groove_height = baseplate_step_height
        params.step.bottom_groove_depth = baseplate_step_width
        params.light_slot.enabled = light_slot_enabled
        params.edge_wrap.wrap_enabled = bottom_mode == self.BOTTOM_MODE_EDGE_WRAP
        params.edge_wrap.outline_enabled = bottom_mode == self.BOTTOM_MODE_OUTLINE
        self._params = params

        # 确保机器参数使用当前默认值（避免旧配置的平台尺寸被加载）
        # 如果机器参数是旧的默认值（400×400×500），更新为新默认值（800×1200×100）
        if (params.machine.bed_width == 400.0 and
            params.machine.bed_depth == 400.0 and
            params.machine.bed_height == 500.0):
            # 这是旧的默认值，更新为新默认值
            params.machine.bed_width = 800.0
            params.machine.bed_depth = 1200.0
            params.machine.bed_height = 100.0

        # 阻止各控件信号，防止设置值时触发 _on_param_changed
        widgets = [
            self.height_spin, self.layer_height_spin, self.width_line_spin,
            self.wall_thickness_spin, self.edge_type_combo, self.bevel_direction_combo,
            self.bevel_width_spin, self.baseplate_spin, self.panel_thickness_spin,
            self.u_arc_height_spin, self.u_bottom_layers_spin,
            self.dxf_outer_clearance_spin, self.dxf_hole_clearance_spin, self.dxf_laser_kerf_spin,
            self.print_speed, self.travel_speed, self.first_layer_speed,
            self.first_layer_nozzle_temp, self.other_layer_nozzle_temp,
            self.first_layer_bed_temp, self.other_layer_bed_temp,
            self.first_layer_fan_percent, self.other_layer_fan_percent,
            self.skirt_enabled, self.skirt_height, self.skirt_speed, self.skirt_offset,
            self.skirt_outer_enabled, self.skirt_inner_enabled,
            self.step_speed,
            self.connected_enabled, self.connected_type, self.connected_auto_detect,
            self.connected_width, self.connected_height, self.connected_base_height,
            self.connected_support_offset,
            self.wrap_enabled, self.wrap_width, self.wrap_height,
            self.wrap_dir_inner, self.wrap_dir_outer,
            self.outline_enabled, self.outline_width, self.outline_height,
            self.outline_offset, self.outline_dir_inner, self.outline_dir_outer,
            self.color_enabled,
            self.prime_tower_enabled, self.prime_tower_center_x, self.prime_tower_center_y,
            self.prime_tower_width, self.prime_tower_depth, self.prime_tower_infill_density,
            self.panel_step_enabled, self.panel_step_height, self.panel_step_width,
            self.panel_step_v_groove, self.baseplate_step_enabled,
            self.baseplate_step_height, self.baseplate_step_width, self.baseplate_step_v_groove,
            # 底面封闭控件
            self.bottom_face_enabled, self.bottom_face_thickness, self.bottom_face_screw_hole_diameter,
            # 灯槽控件
            self.light_slot_enabled, self.light_slot_width, self.light_slot_depth,
            self.light_slot_floor_layers,
            self.light_slot_wall_gap, self.light_slot_outer_enabled,
            self.light_slot_hole_enabled, self.light_slot_auto_skip_small_holes,
            self.light_slot_min_hole_span,
            # 顶面封闭控件
            self.top_face_enabled, self.top_face_thickness
        ]
        for w in widgets:
            w.blockSignals(True)

        # 更新UI
        self.layer_height_spin.setValue(params.shell.layer_height)
        self.width_line_spin.setValue(
            resolve_shell_line_width(
                params.shell.line_width,
                params.shell.layer_height,
                wall_thickness=params.shell.wall_thickness,
                wall_count=params.shell.wall_count,
            )
        )
        self.height_spin.setValue(params.shell.height)
        self.wall_thickness_spin.setValue(params.shell.wall_thickness)
        self._sync_wall_thickness_step()

        # 边缘参数
        edge_index = self.edge_type_combo.findData(params.shell.edge_type)
        if edge_index >= 0:
            self.edge_type_combo.setCurrentIndex(edge_index)
        bevel_dir_index = self.bevel_direction_combo.findData(params.shell.bevel_direction)
        if bevel_dir_index >= 0:
            self.bevel_direction_combo.setCurrentIndex(bevel_dir_index)
        self.bevel_width_spin.setValue(params.shell.bevel_width)
        self.baseplate_spin.setValue(params.shell.baseplate_thickness)
        self.panel_thickness_spin.setValue(params.shell.panel_thickness)
        self.u_arc_height_spin.setValue(params.shell.u_arc_height)
        self.u_bottom_layers_spin.setValue(
            params.shell.u_bottom_layers * self._current_layer_height()
        )
        self.dxf_outer_clearance_spin.setValue(params.shell.dxf_outer_clearance)
        self.dxf_hole_clearance_spin.setValue(params.shell.dxf_hole_clearance)
        self.dxf_laser_kerf_spin.setValue(params.shell.dxf_laser_kerf)

        # 速度参数
        self.print_speed.setValue(int(params.speed.print_speed))
        self.travel_speed.setValue(int(params.speed.travel_speed))
        self.first_layer_speed.setValue(int(params.speed.first_layer_speed))
        self.step_speed.setValue(params.step.print_speed)
        self.first_layer_nozzle_temp.setValue(int(params.gcode.first_layer_nozzle_temp))
        self.other_layer_nozzle_temp.setValue(int(params.gcode.other_layer_nozzle_temp))
        self.first_layer_bed_temp.setValue(int(params.gcode.first_layer_bed_temp))
        self.other_layer_bed_temp.setValue(int(params.gcode.other_layer_bed_temp))
        self.first_layer_fan_percent.setValue(int(params.gcode.first_layer_fan_percent))
        self.other_layer_fan_percent.setValue(int(params.gcode.other_layer_fan_percent))

        current_profile = self._current_printer_profile()
        profile_snapshot = printer_profile_from_params(
            params,
            profile_id=self._active_profile_id or "",
            name=(
                current_profile.name
                if current_profile is not None
                else (params.machine.name or self.tr("Klipper Profile"))
            ),
        )
        self._apply_profile_to_form(profile_snapshot)

        # 裙边参数
        self.skirt_height.setValue(params.skirt.height)
        self.skirt_speed.setValue(params.skirt.speed)
        self.skirt_offset.setValue(params.skirt.offset)
        self.skirt_outer_enabled.setChecked(params.skirt.outer_enabled)
        self.skirt_inner_enabled.setChecked(params.skirt.inner_enabled)
        self.skirt_enabled.setChecked(params.skirt.enabled)

        # 连襟字参数
        connected_type_index = self.connected_type.findData(params.connected.type)
        if connected_type_index >= 0:
            self.connected_type.setCurrentIndex(connected_type_index)
        self.connected_auto_detect.setChecked(params.connected.auto_detect)
        self.connected_width.setValue(params.connected.width)
        self.connected_height.setValue(params.connected.height)
        self.connected_base_height.setValue(params.connected.base_height)
        self.connected_support_offset.setValue(params.connected.support_offset)
        self.connected_enabled.setChecked(params.connected.enabled)

        # 包边勾边参数
        self.wrap_enabled.setChecked(params.edge_wrap.wrap_enabled)
        self.wrap_width.setValue(params.edge_wrap.wrap_width)
        self.wrap_height.setValue(params.edge_wrap.wrap_height)
        if params.edge_wrap.wrap_direction == EdgeDirection.INNER:
            self.wrap_dir_inner.setChecked(True)
        else:
            self.wrap_dir_outer.setChecked(True)
        self.outline_enabled.setChecked(params.edge_wrap.outline_enabled)
        self.outline_width.setValue(params.edge_wrap.outline_width)
        self.outline_height.setValue(params.edge_wrap.outline_height)
        self.outline_offset.setValue(params.edge_wrap.outline_offset)
        if params.edge_wrap.outline_direction == EdgeDirection.INNER:
            self.outline_dir_inner.setChecked(True)
        else:
            self.outline_dir_outer.setChecked(True)

        # 换色层参数
        self.color_enabled.setChecked(params.color.enabled)
        self._rebuild_color_change_rows(params.color.change_points)

        # Prime tower 参数
        self.prime_tower_enabled.setChecked(prime_tower_enabled)
        self.prime_tower_width.setValue(prime_tower_width)
        self.prime_tower_depth.setValue(prime_tower_depth)
        self._update_prime_tower_coordinate_ranges()
        self.prime_tower_center_x.setValue(prime_tower_center_x)
        self.prime_tower_center_y.setValue(prime_tower_center_y)
        self.prime_tower_infill_density.setValue(prime_tower_infill_density)

        # 台阶参数 - 面板台阶（顶部）
        self.panel_step_enabled.setChecked(panel_step_enabled)
        self.panel_step_height.setValue(panel_step_height)
        self.panel_step_width.setValue(panel_step_width)
        self.panel_step_v_groove.setChecked(panel_step_is_v_groove)

        # 台阶参数 - 底板台阶（底部）
        self.baseplate_step_enabled.setChecked(baseplate_step_enabled)
        self.baseplate_step_height.setValue(baseplate_step_height)
        self.baseplate_step_width.setValue(baseplate_step_width)
        self.baseplate_step_v_groove.setChecked(baseplate_step_is_v_groove)

        # 底面封闭参数
        self.bottom_face_enabled.setChecked(bottom_face_enabled)
        self.bottom_face_thickness.setValue(bottom_face_thickness)
        self.bottom_face_screw_hole_diameter.setValue(bottom_face_screw_hole_diameter)

        # 灯槽参数
        self.light_slot_enabled.setChecked(light_slot_enabled)
        self.light_slot_width.setValue(light_slot_width)
        self.light_slot_depth.setValue(light_slot_depth)
        self.light_slot_floor_layers.setValue(
            light_slot_floor_layers * self._current_layer_height()
        )
        self.light_slot_wall_gap.setValue(light_slot_wall_gap)
        self.light_slot_outer_enabled.setChecked(light_slot_outer_enabled)
        self.light_slot_hole_enabled.setChecked(light_slot_hole_enabled)
        self.light_slot_auto_skip_small_holes.setChecked(light_slot_auto_skip_small_holes)
        self.light_slot_min_hole_span.setValue(light_slot_min_hole_span)

        # 顶面封闭参数
        self.top_face_enabled.setChecked(top_face_enabled)
        self.top_face_thickness.setValue(top_face_thickness)

        # 恢复信号
        for w in widgets:
            w.blockSignals(False)

        # 手动更新控件的启用/可见状态
        # 边缘类型：展开对应的参数面板
        edge_type = params.shell.edge_type
        self.bevel_params_widget.setVisible(edge_type == EdgeType.BEVELED)
        self.u_shape_params_widget.setVisible(edge_type == EdgeType.U_SHAPED)
        self.custom_edge_widget.setVisible(edge_type == EdgeType.CUSTOM)
        self._sync_wall_mode_from_controls()

        # 异形边：恢复 profile 和预设选中状态
        if edge_type == EdgeType.CUSTOM and params.shell.edge_profile is not None:
            self._current_profile = params.shell.edge_profile
            # 恢复预设缩略图的选中高亮
            if params.shell.edge_profile.preset_name:
                self.preset_selector.select_preset(params.shell.edge_profile.preset_name)
            self._update_profile_info()

        self._toggle_skirt_controls(params.skirt.enabled)
        self._toggle_connected_controls(params.connected.enabled)
        self._apply_top_mode(top_mode, emit_changed=False)
        self._apply_bottom_mode(bottom_mode, emit_changed=False)
        self._toggle_color_change_controls(params.color.enabled)
        self._toggle_prime_tower_controls(prime_tower_enabled)
        self._sync_bottom_face_availability()
        self._sync_layer_based_controls()

    # ===== 异形边相关方法 =====

    def _on_preset_changed(self, preset_name: str):
        """预设选择变更"""
        if not preset_name:
            return

        # 加载预设（使用模板原始宽度）
        profile = self._preset_manager.get_preset_profile(preset_name)

        if profile:
            self._current_profile = profile
            self._update_profile_info()
            self._on_param_changed()

    def _on_import_dxf(self):
        """导入DXF文件"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        settings = get_settings_manager()
        initial_dir = settings.get_last_open_dir() if settings else ""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Import Custom Edge DXF"),
            initial_dir,
            self.tr("DXF Files (*.dxf);;All Files (*.*)")
        )

        if not file_path:
            return

        if settings:
            settings.set_last_open_dir(str(Path(file_path).expanduser().resolve(strict=False).parent))

        try:
            from src.core.edge_profile_loader import EdgeProfileDXFLoader
            loader = EdgeProfileDXFLoader()
            profile = loader.load_from_dxf(file_path)

            self._current_profile = profile
            self._update_profile_info()
            self._on_param_changed()

            QMessageBox.information(
                self, self.tr("Import Success"),
                self.tr("Imported custom edge profile: {name}\nSize: {width:.1f} x {height:.1f} mm\nControl points: {points}").format(
                    name=profile.name,
                    width=profile.original_width,
                    height=profile.original_height,
                    points=len(profile.control_points)
                )
            )

        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, self.tr("Import Failed"),
                self.tr("Failed to import DXF file:\n{error}").format(error=str(e))
            )

    def _update_profile_info(self):
        """更新轮廓信息显示"""
        if self._current_profile:
            # 翻译预设名称
            translated_name = QCoreApplication.translate(
                "EdgePresets", self._current_profile.name)
            info = f"{translated_name}"
            if self._current_profile.control_points:
                info += self.tr(" ({count} points)").format(count=len(self._current_profile.control_points))
            self.profile_info_label.setText(info)
            self.profile_info_label.setStyleSheet("color: #58A6FF;")
        else:
            self.profile_info_label.setText(self.tr("No profile selected"))
            self.profile_info_label.setStyleSheet("color: #888;")
