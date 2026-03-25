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
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QLineEdit,
    QComboBox, QCheckBox, QGroupBox, QFrame,
    QPushButton, QTabWidget, QFormLayout, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QCoreApplication

from src.core.types import (
    SliceParams, ShellParams, EdgeType, ExtruderType, EdgeDirection, BevelDirection,
    ConnectedParams, EdgeProfile, TopFaceParams
)
from src.core.edge_presets import EdgePresetManager, ProfileCategory
from src.ui.widgets.edge_preset_selector import EdgePresetSelector
from src.ui.widgets.plus_minus_spinbox import PlusMinusSpinBox, PlusMinusIntSpinBox
from .theme import COLORS, LAYOUT


class ParamPanel(QWidget):
    """参数面板"""

    params_changed = Signal()  # 参数变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 参数
        self._params = SliceParams()

        # 异形边预设管理器
        self._preset_manager = EdgePresetManager()
        self._current_profile = None

        # 初始化UI
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel(self.tr("Parameters"))
        title.setProperty("heading", True)
        title.setStyleSheet(f"""
            padding: 12px;
            background-color: {COLORS.bg_secondary};
            border-bottom: 1px solid {COLORS.border_default};
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(title)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        layout.addWidget(scroll)

        # 滚动内容
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        # 添加参数分组
        content_layout.addWidget(self._create_shell_group())
        content_layout.addWidget(self._create_edge_group())
        content_layout.addWidget(self._create_dxf_export_group())
        content_layout.addWidget(self._create_bottom_face_group())  # 底面封闭
        content_layout.addWidget(self._create_light_slot_group())  # 灯槽
        content_layout.addWidget(self._create_top_face_group())  # 顶面封闭

        # 暂时隐藏换色层设置
        color_group = self._create_color_group()
        color_group.setVisible(False)
        content_layout.addWidget(color_group)

        content_layout.addWidget(self._create_step_group())
        content_layout.addWidget(self._create_skirt_group())
        content_layout.addWidget(self._create_connected_group())
        content_layout.addWidget(self._create_edge_wrap_group())

        # 暂时隐藏速度设置
        speed_group = self._create_speed_group()
        speed_group.setVisible(False)
        content_layout.addWidget(speed_group)

        content_layout.addStretch()

        scroll.setWidget(content)
        self._sync_layer_based_controls()

    def _create_layer_count_editor(self, spinbox: PlusMinusIntSpinBox, label_attr: str) -> QWidget:
        """Wrap a layer-count input with a live mm summary label."""
        summary = QLabel()
        summary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        summary.setMinimumWidth(78)
        summary.setStyleSheet("color: #8B949E; font-size: 12px;")
        setattr(self, label_attr, summary)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(spinbox)
        layout.addWidget(summary)
        return container

    def _configure_layer_count_spin(
        self,
        spinbox: PlusMinusIntSpinBox,
        minimum: int,
        maximum: int,
        value: int,
        enabled: bool = True,
    ) -> None:
        """Initialize a layer-count spinbox with a consistent suffix/tooltip."""
        spinbox.setRange(minimum, maximum)
        spinbox.setValue(value)
        spinbox.setSuffix(self.tr("layers"))
        spinbox.setEnabled(enabled)
        spinbox.setToolTip(
            self.tr("Height is derived from layer count * layer height.")
        )
        spinbox.valueChanged.connect(self._sync_layer_based_controls)

    def _current_layer_height(self) -> float:
        """Return the currently selected layer height."""
        if hasattr(self, "layer_height_spin"):
            return max(self.layer_height_spin.value(), 0.001)
        return 0.3

    def _layers_to_mm(self, layers: int) -> float:
        """Convert layer count to mm using the active layer height."""
        return max(0, layers) * self._current_layer_height()

    def _height_to_layers(self, height_mm: float, minimum: int = 1) -> int:
        """Convert a mm height to the nearest positive layer count."""
        layer_height = self._current_layer_height()
        if layer_height <= 0:
            return minimum
        return max(minimum, int(round(height_mm / layer_height)))

    def _set_layer_summary(self, label: QLabel, layers: int) -> None:
        """Update a mm summary label for a layer-count control."""
        label.setText(f"{self._layers_to_mm(layers):.2f} mm")

    def _sync_layer_based_controls(self):
        """Refresh limits and derived mm labels for layer-count parameters."""
        if not hasattr(self, "height_spin") or not hasattr(self, "layer_height_spin"):
            return

        layer_height = self._current_layer_height()

        shell_max_layers = max(1, math.ceil(500 / layer_height))
        self.height_spin.setMaximum(shell_max_layers)
        self._set_layer_summary(self.height_value_label, self.height_spin.value())

        if hasattr(self, "bottom_face_thickness"):
            self.bottom_face_thickness.setMaximum(max(1, math.ceil(10.0 / layer_height)))
            self._set_layer_summary(
                self.bottom_face_thickness_value_label,
                self.bottom_face_thickness.value(),
            )

        if hasattr(self, "light_slot_depth"):
            self.light_slot_depth.setMaximum(max(1, math.ceil(20.0 / layer_height)))
            self._set_layer_summary(
                self.light_slot_depth_value_label,
                self.light_slot_depth.value(),
            )

        if hasattr(self, "top_face_thickness"):
            self.top_face_thickness.setMaximum(max(1, math.ceil(10.0 / layer_height)))
            self._set_layer_summary(
                self.top_face_thickness_value_label,
                self.top_face_thickness.value(),
            )

        if hasattr(self, "panel_step_height") and hasattr(self, "baseplate_step_height"):
            self._update_step_ranges()
            self._set_layer_summary(
                self.panel_step_height_value_label,
                self.panel_step_height.value(),
            )
            self._set_layer_summary(
                self.baseplate_step_height_value_label,
                self.baseplate_step_height.value(),
            )

        if hasattr(self, "connected_height") and hasattr(self, "connected_base_height"):
            max_connected_layers = max(1, math.ceil(20.0 / layer_height))
            self.connected_height.setMaximum(max_connected_layers)
            self.connected_base_height.setMaximum(max_connected_layers)
            self._set_layer_summary(
                self.connected_height_value_label,
                self.connected_height.value(),
            )
            self._set_layer_summary(
                self.connected_base_height_value_label,
                self.connected_base_height.value(),
            )

    def _create_shell_group(self) -> QGroupBox:
        """创建字壳工艺参数组"""
        group = QGroupBox(self.tr("Shell Settings"))
        layout = QFormLayout(group)
        layout.setSpacing(8)

        # 字壳高度
        self.height_spin = PlusMinusIntSpinBox()
        self._configure_layer_count_spin(self.height_spin, 1, 5000, 100)
        self.height_spin.valueChanged.connect(self._on_param_changed)
        self.height_spin.valueChanged.connect(self._update_step_ranges)
        layout.addRow(
            self.tr("Shell Height:"),
            self._create_layer_count_editor(self.height_spin, "height_value_label"),
        )

        # 层高
        self.layer_height_spin = PlusMinusSpinBox()
        self.layer_height_spin.setRange(0.1, 1.0)
        self.layer_height_spin.setValue(0.3)
        self.layer_height_spin.setSingleStep(0.05)
        self.layer_height_spin.setSuffix("mm")
        self.layer_height_spin.valueChanged.connect(self._on_param_changed)
        self.layer_height_spin.valueChanged.connect(self._sync_layer_based_controls)
        layout.addRow(self.tr("Layer Height:"), self.layer_height_spin)

        # 壁厚
        self.wall_thickness_spin = PlusMinusSpinBox()
        self.wall_thickness_spin.setRange(0.4, 3.0)
        self.wall_thickness_spin.setValue(1.2)
        self.wall_thickness_spin.setSingleStep(0.1)
        self.wall_thickness_spin.setSuffix("mm")
        self.wall_thickness_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow(self.tr("Wall Thickness:"), self.wall_thickness_spin)

        # 壁数量
        self.wall_count_spin = PlusMinusIntSpinBox()
        self.wall_count_spin.setRange(1, 5)
        self.wall_count_spin.setValue(1)
        self.wall_count_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow(self.tr("Wall Count:"), self.wall_count_spin)

        return group

    def _create_edge_group(self) -> QGroupBox:
        """创建边缘类型参数组"""
        group = QGroupBox(self.tr("Edge Type"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 边缘类型选择
        type_form = QFormLayout()
        type_form.setSpacing(8)

        self.edge_type_combo = QComboBox()
        self.edge_type_combo.addItem(self.tr("Straight"), EdgeType.STRAIGHT)
        self.edge_type_combo.addItem(self.tr("Beveled"), EdgeType.BEVELED)
        self.edge_type_combo.addItem(self.tr("Custom"), EdgeType.CUSTOM)
        self.edge_type_combo.currentIndexChanged.connect(self._on_edge_type_changed)
        type_form.addRow(self.tr("Edge Type:"), self.edge_type_combo)

        layout.addLayout(type_form)

        # ===== 斜边参数容器 =====
        self.bevel_params_widget = QWidget()
        bevel_layout = QFormLayout(self.bevel_params_widget)
        bevel_layout.setContentsMargins(0, 8, 0, 0)
        bevel_layout.setSpacing(8)

        # 斜边方向
        self.bevel_direction_combo = QComboBox()
        self.bevel_direction_combo.addItem(self.tr("Top Small"), BevelDirection.TOP_SMALL)
        self.bevel_direction_combo.addItem(self.tr("Top Large"), BevelDirection.TOP_LARGE)
        self.bevel_direction_combo.currentIndexChanged.connect(self._on_param_changed)
        bevel_layout.addRow(self.tr("Bevel Direction:"), self.bevel_direction_combo)

        self.bevel_direction_hint = QLabel(
            self.tr("Original contour is always based on the bottom face (z=0).")
        )
        self.bevel_direction_hint.setWordWrap(True)
        self.bevel_direction_hint.setStyleSheet("color: #8B949E; font-size: 12px;")
        bevel_layout.addRow("", self.bevel_direction_hint)

        # 斜边宽度
        self.bevel_width_spin = PlusMinusSpinBox()
        self.bevel_width_spin.setRange(0, 50)
        self.bevel_width_spin.setValue(5)
        self.bevel_width_spin.setSuffix("mm")
        self.bevel_width_spin.valueChanged.connect(self._on_param_changed)
        bevel_layout.addRow(self.tr("Bevel Width:"), self.bevel_width_spin)

        # 底板厚度
        self.baseplate_spin = PlusMinusSpinBox()
        self.baseplate_spin.setRange(0, 50)
        self.baseplate_spin.setValue(10)
        self.baseplate_spin.setSuffix("mm")
        self.baseplate_spin.valueChanged.connect(self._on_param_changed)
        bevel_layout.addRow(self.tr("Baseplate Thickness:"), self.baseplate_spin)

        # 面板厚度
        self.panel_thickness_spin = PlusMinusSpinBox()
        self.panel_thickness_spin.setRange(0, 20)
        self.panel_thickness_spin.setValue(3)
        self.panel_thickness_spin.setSuffix("mm")
        self.panel_thickness_spin.valueChanged.connect(self._on_param_changed)
        bevel_layout.addRow(self.tr("Panel Thickness:"), self.panel_thickness_spin)

        layout.addWidget(self.bevel_params_widget)
        self.bevel_params_widget.setVisible(False)

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
        info_layout.addRow(self.tr("Current Profile:"), self.profile_info_label)
        custom_layout.addLayout(info_layout)

        layout.addWidget(self.custom_edge_widget)
        self.custom_edge_widget.setVisible(False)

        return group

    def _create_dxf_export_group(self) -> QGroupBox:
        """创建 DXF 导出补偿参数组"""
        group = QGroupBox(self.tr("DXF Export"))
        layout = QFormLayout(group)
        layout.setSpacing(8)

        self.dxf_outer_clearance_spin = PlusMinusSpinBox()
        self.dxf_outer_clearance_spin.setRange(0, 10)
        self.dxf_outer_clearance_spin.setValue(1.0)
        self.dxf_outer_clearance_spin.setSingleStep(0.1)
        self.dxf_outer_clearance_spin.setSuffix("mm")
        self.dxf_outer_clearance_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow(self.tr("Outer Clearance:"), self.dxf_outer_clearance_spin)

        self.dxf_hole_clearance_spin = PlusMinusSpinBox()
        self.dxf_hole_clearance_spin.setRange(0, 10)
        self.dxf_hole_clearance_spin.setValue(1.0)
        self.dxf_hole_clearance_spin.setSingleStep(0.1)
        self.dxf_hole_clearance_spin.setSuffix("mm")
        self.dxf_hole_clearance_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow(self.tr("Hole Clearance:"), self.dxf_hole_clearance_spin)

        self.dxf_laser_kerf_spin = PlusMinusSpinBox()
        self.dxf_laser_kerf_spin.setRange(0, 2)
        self.dxf_laser_kerf_spin.setValue(0.0)
        self.dxf_laser_kerf_spin.setSingleStep(0.01)
        self.dxf_laser_kerf_spin.setSuffix("mm")
        self.dxf_laser_kerf_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow(self.tr("Laser Kerf:"), self.dxf_laser_kerf_spin)

        return group

    def _create_bottom_face_group(self) -> QGroupBox:
        """创建底面封闭参数组"""
        group = QGroupBox(self.tr("Bottom Face"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.bottom_face_enabled = QCheckBox(self.tr("Enable Bottom Face"))
        self.bottom_face_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.bottom_face_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        # 底面厚度
        self.bottom_face_thickness = PlusMinusIntSpinBox()
        self._configure_layer_count_spin(self.bottom_face_thickness, 1, 100, 3, enabled=False)
        self.bottom_face_thickness.valueChanged.connect(self._on_param_changed)
        form.addRow(
            self.tr("Bottom Thickness:"),
            self._create_layer_count_editor(
                self.bottom_face_thickness,
                "bottom_face_thickness_value_label",
            ),
        )

        layout.addLayout(form)

        # 启用/禁用控件联动
        self.bottom_face_enabled.stateChanged.connect(
            lambda: self.bottom_face_thickness.setEnabled(self.bottom_face_enabled.isChecked())
        )
        # 与 Baseplate Step (Bottom) 互斥
        self.bottom_face_enabled.stateChanged.connect(self._on_bottom_face_toggled)

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
                self.bottom_face_thickness.setEnabled(False)
                self.bottom_face_enabled.blockSignals(False)
                self._on_param_changed()
        if self.baseplate_step_enabled.isChecked() and hasattr(self, 'light_slot_enabled'):
            if self.light_slot_enabled.isChecked():
                self.light_slot_enabled.blockSignals(True)
                self.light_slot_enabled.setChecked(False)
                self._toggle_light_slot_controls(False)
                self.light_slot_enabled.blockSignals(False)
                self._on_param_changed()

    def _toggle_bottom_face_controls(self, enabled: bool):
        """切换底面封闭控件的启用状态"""
        self.bottom_face_thickness.setEnabled(enabled)

    def _create_light_slot_group(self) -> QGroupBox:
        """创建灯槽参数组"""
        group = QGroupBox(self.tr("Light Slot"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.light_slot_enabled = QCheckBox(self.tr("Enable Light Slot"))
        self.light_slot_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.light_slot_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        self.light_slot_width = PlusMinusSpinBox()
        self.light_slot_width.setRange(0.5, 50.0)
        self.light_slot_width.setValue(8.0)
        self.light_slot_width.setSingleStep(0.5)
        self.light_slot_width.setSuffix("mm")
        self.light_slot_width.setEnabled(False)
        self.light_slot_width.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Slot Width:"), self.light_slot_width)

        self.light_slot_depth = PlusMinusIntSpinBox()
        self._configure_layer_count_spin(self.light_slot_depth, 1, 200, 10, enabled=False)
        self.light_slot_depth.valueChanged.connect(self._on_param_changed)
        form.addRow(
            self.tr("Slot Depth:"),
            self._create_layer_count_editor(
                self.light_slot_depth,
                "light_slot_depth_value_label",
            ),
        )

        self.light_slot_floor_layers = PlusMinusIntSpinBox()
        self.light_slot_floor_layers.setRange(1, 100)
        self.light_slot_floor_layers.setValue(2)
        self.light_slot_floor_layers.setSingleStep(1)
        self.light_slot_floor_layers.setEnabled(False)
        self.light_slot_floor_layers.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Floor Layers:"), self.light_slot_floor_layers)

        self.light_slot_wall_gap = PlusMinusSpinBox()
        self.light_slot_wall_gap.setRange(0.0, 20.0)
        self.light_slot_wall_gap.setValue(0.0)
        self.light_slot_wall_gap.setSingleStep(0.1)
        self.light_slot_wall_gap.setSuffix("mm")
        self.light_slot_wall_gap.setEnabled(False)
        self.light_slot_wall_gap.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Wall Gap:"), self.light_slot_wall_gap)

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
        self.light_slot_min_hole_span = PlusMinusSpinBox()
        self.light_slot_min_hole_span.setRange(1.0, 100.0)
        self.light_slot_min_hole_span.setValue(12.0)
        self.light_slot_min_hole_span.setSingleStep(0.5)
        self.light_slot_min_hole_span.setSuffix("mm")
        self.light_slot_min_hole_span.setEnabled(False)
        self.light_slot_min_hole_span.valueChanged.connect(self._on_param_changed)
        min_hole_span_form.addRow(self.tr("Min Hole Span:"), self.light_slot_min_hole_span)
        layout.addLayout(min_hole_span_form)

        self.light_slot_enabled.stateChanged.connect(
            lambda: self._toggle_light_slot_controls(self.light_slot_enabled.isChecked())
        )
        self.light_slot_enabled.stateChanged.connect(self._on_light_slot_toggled)

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
        self.top_face_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.top_face_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        # 顶面厚度
        self.top_face_thickness = PlusMinusIntSpinBox()
        self._configure_layer_count_spin(self.top_face_thickness, 1, 100, 3, enabled=False)
        self.top_face_thickness.valueChanged.connect(self._on_param_changed)
        form.addRow(
            self.tr("Top Thickness:"),
            self._create_layer_count_editor(
                self.top_face_thickness,
                "top_face_thickness_value_label",
            ),
        )

        layout.addLayout(form)

        # 启用/禁用控件联动
        self.top_face_enabled.stateChanged.connect(
            lambda: self.top_face_thickness.setEnabled(self.top_face_enabled.isChecked())
        )
        # 与 Panel Step (Top) 互斥
        self.top_face_enabled.stateChanged.connect(self._on_top_face_toggled)

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

    def _create_color_group(self) -> QGroupBox:
        """创建换色层参数组"""
        group = QGroupBox(self.tr("Color Layer Settings"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.color_enabled = QCheckBox(self.tr("Enable Color Layers"))
        self.color_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.color_enabled)

        # 换色层配置（简化版）
        form = QFormLayout()
        form.setSpacing(8)

        self.color1_height = PlusMinusSpinBox()
        self.color1_height.setRange(0, 100)
        self.color1_height.setValue(10)
        self.color1_height.setSuffix("mm")
        self.color1_height.setEnabled(False)
        form.addRow(self.tr("Color 1 Height:"), self.color1_height)

        self.color2_height = PlusMinusSpinBox()
        self.color2_height.setRange(0, 100)
        self.color2_height.setValue(20)
        self.color2_height.setSuffix("mm")
        self.color2_height.setEnabled(False)
        form.addRow(self.tr("Color 2 Height:"), self.color2_height)

        layout.addLayout(form)

        self.color_enabled.stateChanged.connect(
            lambda: self.color1_height.setEnabled(self.color_enabled.isChecked())
        )
        self.color_enabled.stateChanged.connect(
            lambda: self.color2_height.setEnabled(self.color_enabled.isChecked())
        )

        return group

    def _create_step_group(self) -> QGroupBox:
        """创建台阶/V槽参数组"""
        group = QGroupBox(self.tr("Step/V-Groove"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # ===== 面板台阶（顶部）=====
        self.panel_step_enabled = QCheckBox(self.tr("Enable Panel Step (Top)"))
        self.panel_step_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.panel_step_enabled)

        form1 = QFormLayout()
        self.panel_step_height = PlusMinusIntSpinBox()
        self._configure_layer_count_spin(self.panel_step_height, 50, 100, 93, enabled=False)
        self.panel_step_height.valueChanged.connect(self._on_param_changed)
        form1.addRow(
            self.tr("Step Height:"),
            self._create_layer_count_editor(
                self.panel_step_height,
                "panel_step_height_value_label",
            ),
        )

        self.panel_step_width = PlusMinusSpinBox()
        self.panel_step_width.setRange(0.5, 20)
        self.panel_step_width.setValue(3)
        self.panel_step_width.setSuffix("mm")
        self.panel_step_width.setEnabled(False)
        self.panel_step_width.valueChanged.connect(self._on_param_changed)
        form1.addRow(self.tr("Step Width:"), self.panel_step_width)

        self.panel_step_v_groove = QCheckBox(self.tr("V-Groove"))
        self.panel_step_v_groove.setEnabled(False)
        self.panel_step_v_groove.stateChanged.connect(self._on_param_changed)
        form1.addRow("", self.panel_step_v_groove)

        layout.addLayout(form1)

        self.panel_step_enabled.stateChanged.connect(
            lambda: self._toggle_panel_step_controls(self.panel_step_enabled.isChecked())
        )
        # 与 Top Face 互斥
        self.panel_step_enabled.stateChanged.connect(self._on_panel_step_toggled)

        # 分隔线
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet(f"background-color: {COLORS.border_default};")
        layout.addWidget(line1)

        # ===== 底板台阶（底部）=====
        self.baseplate_step_enabled = QCheckBox(self.tr("Enable Baseplate Step (Bottom)"))
        self.baseplate_step_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.baseplate_step_enabled)

        form2 = QFormLayout()
        self.baseplate_step_height = PlusMinusIntSpinBox()
        self._configure_layer_count_spin(self.baseplate_step_height, 1, 50, 10, enabled=False)
        self.baseplate_step_height.valueChanged.connect(self._on_param_changed)
        form2.addRow(
            self.tr("Step Height:"),
            self._create_layer_count_editor(
                self.baseplate_step_height,
                "baseplate_step_height_value_label",
            ),
        )

        self.baseplate_step_width = PlusMinusSpinBox()
        self.baseplate_step_width.setRange(0.5, 20)
        self.baseplate_step_width.setValue(3)
        self.baseplate_step_width.setSuffix("mm")
        self.baseplate_step_width.setEnabled(False)
        self.baseplate_step_width.valueChanged.connect(self._on_param_changed)
        form2.addRow(self.tr("Step Width:"), self.baseplate_step_width)

        self.baseplate_step_v_groove = QCheckBox(self.tr("V-Groove"))
        self.baseplate_step_v_groove.setEnabled(False)
        self.baseplate_step_v_groove.stateChanged.connect(self._on_param_changed)
        form2.addRow("", self.baseplate_step_v_groove)

        layout.addLayout(form2)

        self.baseplate_step_enabled.stateChanged.connect(
            lambda: self._toggle_baseplate_step_controls(self.baseplate_step_enabled.isChecked())
        )
        # 与 Bottom Face 互斥
        self.baseplate_step_enabled.stateChanged.connect(self._on_baseplate_step_toggled)

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

        shell_layers = self.height_spin.value()
        half_min = max(1, (shell_layers + 1) // 2)
        half_max = max(1, shell_layers // 2)

        # 顶部卡槽
        self.panel_step_height.setRange(half_min, max(half_min, shell_layers))
        if self.panel_step_height.value() < half_min:
            self.panel_step_height.setValue(half_min)

        # 底部卡槽
        self.baseplate_step_height.setRange(1, half_max)
        if self.baseplate_step_height.value() > half_max:
            self.baseplate_step_height.setValue(half_max)

    def _toggle_panel_step_controls(self, enabled: bool):
        """切换面板台阶控件的启用状态"""
        self.panel_step_height.setEnabled(enabled)
        self.panel_step_width.setEnabled(enabled)
        self.panel_step_v_groove.setEnabled(enabled)

    def _toggle_baseplate_step_controls(self, enabled: bool):
        """切换底板台阶控件的启用状态"""
        self.baseplate_step_height.setEnabled(enabled)
        self.baseplate_step_width.setEnabled(enabled)
        self.baseplate_step_v_groove.setEnabled(enabled)

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

        self.skirt_width = PlusMinusSpinBox()
        self.skirt_width.setRange(1, 20)
        self.skirt_width.setValue(5)
        self.skirt_width.setSuffix("mm")
        self.skirt_width.setEnabled(False)
        self.skirt_width.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Skirt Width:"), self.skirt_width)

        self.skirt_height = PlusMinusSpinBox()
        self.skirt_height.setRange(0.2, 10)
        self.skirt_height.setValue(0.3)
        self.skirt_height.setSingleStep(0.1)
        self.skirt_height.setSuffix("mm")
        self.skirt_height.setEnabled(False)
        self.skirt_height.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Skirt Height:"), self.skirt_height)

        self.skirt_interval = PlusMinusSpinBox()
        self.skirt_interval.setRange(5, 50)
        self.skirt_interval.setValue(10)
        self.skirt_interval.setSuffix("mm")
        self.skirt_interval.setEnabled(False)
        self.skirt_interval.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Trapezoid Interval:"), self.skirt_interval)

        self.skirt_offset = PlusMinusSpinBox()
        self.skirt_offset.setRange(0, 20)
        self.skirt_offset.setValue(0)
        self.skirt_offset.setSuffix("mm")
        self.skirt_offset.setEnabled(False)
        self.skirt_offset.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Skirt Offset:"), self.skirt_offset)

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
        form.addRow(self.tr("Skirt Sides:"), direction_layout)

        layout.addLayout(form)

        self.skirt_enabled.stateChanged.connect(
            lambda: self._toggle_skirt_controls(self.skirt_enabled.isChecked())
        )

        return group

    def _toggle_skirt_controls(self, enabled: bool):
        """切换裙边控件的启用状态"""
        self.skirt_width.setEnabled(enabled)
        self.skirt_height.setEnabled(enabled)
        self.skirt_interval.setEnabled(enabled)
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
        self.connected_type = QComboBox()
        self.connected_type.addItem(self.tr("Triangle"), "triangle")
        self.connected_type.addItem(self.tr("Diamond"), "diamond")
        self.connected_type.setEnabled(False)
        self.connected_type.currentIndexChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Connection Type:"), self.connected_type)

        # 自动检测
        self.connected_auto_detect = QCheckBox(self.tr("Auto Detect Connection Points"))
        self.connected_auto_detect.setChecked(True)
        self.connected_auto_detect.setEnabled(False)
        self.connected_auto_detect.stateChanged.connect(self._on_param_changed)
        form.addRow("", self.connected_auto_detect)

        # 连襟宽度
        self.connected_width = PlusMinusSpinBox()
        self.connected_width.setRange(1, 50)
        self.connected_width.setValue(5)
        self.connected_width.setSuffix("mm")
        self.connected_width.setEnabled(False)
        self.connected_width.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Connection Width:"), self.connected_width)

        # 斜边高度
        self.connected_height = PlusMinusIntSpinBox()
        self._configure_layer_count_spin(
            self.connected_height,
            1,
            100,
            self._height_to_layers(5.0),
            enabled=False,
        )
        self.connected_height.valueChanged.connect(self._on_param_changed)
        form.addRow(
            self.tr("Bevel Height:"),
            self._create_layer_count_editor(
                self.connected_height,
                "connected_height_value_label",
            ),
        )

        # 底座高度
        self.connected_base_height = PlusMinusIntSpinBox()
        self._configure_layer_count_spin(
            self.connected_base_height,
            1,
            100,
            self._height_to_layers(5.0),
            enabled=False,
        )
        self.connected_base_height.valueChanged.connect(self._on_param_changed)
        form.addRow(
            self.tr("Base Height:"),
            self._create_layer_count_editor(
                self.connected_base_height,
                "connected_base_height_value_label",
            ),
        )

        # 支撑偏移
        self.connected_support_offset = PlusMinusSpinBox()
        self.connected_support_offset.setRange(0, 10)
        self.connected_support_offset.setValue(2.5)
        self.connected_support_offset.setSuffix("mm")
        self.connected_support_offset.setEnabled(False)
        self.connected_support_offset.valueChanged.connect(self._on_param_changed)
        form.addRow(self.tr("Support Offset:"), self.connected_support_offset)

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
        wrap_form.addRow(self.tr("Wrap Direction:"), wrap_dir_layout)

        self.wrap_width = PlusMinusSpinBox()
        self.wrap_width.setRange(0.5, 10)
        self.wrap_width.setValue(2.0)
        self.wrap_width.setSingleStep(0.1)
        self.wrap_width.setSuffix("mm")
        self.wrap_width.setEnabled(False)
        wrap_form.addRow(self.tr("Wrap Width:"), self.wrap_width)

        self.wrap_height = PlusMinusSpinBox()
        self.wrap_height.setRange(0.5, 20)
        self.wrap_height.setValue(3.0)
        self.wrap_height.setSingleStep(0.5)
        self.wrap_height.setSuffix("mm")
        self.wrap_height.setEnabled(False)
        wrap_form.addRow(self.tr("Wrap Height:"), self.wrap_height)

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
        outline_form.addRow(self.tr("Outline Direction:"), outline_dir_layout)

        self.outline_width = PlusMinusSpinBox()
        self.outline_width.setRange(0.3, 5)
        self.outline_width.setValue(1.0)
        self.outline_width.setSingleStep(0.1)
        self.outline_width.setSuffix("mm")
        self.outline_width.setEnabled(False)
        outline_form.addRow(self.tr("Outline Width:"), self.outline_width)

        self.outline_height = PlusMinusSpinBox()
        self.outline_height.setRange(0.3, 10)
        self.outline_height.setValue(1.0)
        self.outline_height.setSingleStep(0.1)
        self.outline_height.setSuffix("mm")
        self.outline_height.setEnabled(False)
        outline_form.addRow(self.tr("Outline Height:"), self.outline_height)

        self.outline_offset = PlusMinusSpinBox()
        self.outline_offset.setRange(-5, 5)
        self.outline_offset.setValue(0.0)
        self.outline_offset.setSingleStep(0.1)
        self.outline_offset.setSuffix("mm")
        self.outline_offset.setEnabled(False)
        outline_form.addRow(self.tr("Outline Offset:"), self.outline_offset)

        layout.addLayout(outline_form)

        self.outline_enabled.stateChanged.connect(
            lambda: self._toggle_outline_controls(self.outline_enabled.isChecked())
        )

        # 包边和勾边互斥
        self.wrap_enabled.stateChanged.connect(self._on_wrap_outline_mutual_exclusive)
        self.outline_enabled.stateChanged.connect(self._on_wrap_outline_mutual_exclusive)

        return group

    def _create_speed_group(self) -> QGroupBox:
        """创建速度参数组"""
        group = QGroupBox(self.tr("Speed Settings"))
        layout = QFormLayout(group)
        layout.setSpacing(8)

        # 打印速度
        self.print_speed = PlusMinusIntSpinBox()
        self.print_speed.setRange(10, 200)
        self.print_speed.setValue(50)
        self.print_speed.setSuffix("mm/s")
        self.print_speed.valueChanged.connect(self._on_param_changed)
        layout.addRow(self.tr("Print Speed:"), self.print_speed)

        # 空走速度
        self.travel_speed = PlusMinusIntSpinBox()
        self.travel_speed.setRange(50, 300)
        self.travel_speed.setValue(150)
        self.travel_speed.setSuffix("mm/s")
        self.travel_speed.valueChanged.connect(self._on_param_changed)
        layout.addRow(self.tr("Travel Speed:"), self.travel_speed)

        # 首层速度
        self.first_layer_speed = PlusMinusIntSpinBox()
        self.first_layer_speed.setRange(5, 50)
        self.first_layer_speed.setValue(20)
        self.first_layer_speed.setSuffix("mm/s")
        self.first_layer_speed.valueChanged.connect(self._on_param_changed)
        layout.addRow(self.tr("First Layer Speed:"), self.first_layer_speed)

        return group

    def _on_edge_type_changed(self, index: int):
        """边缘类型变化"""
        edge_type = self.edge_type_combo.currentData()

        # 显示/隐藏对应的参数组
        self.bevel_params_widget.setVisible(edge_type == EdgeType.BEVELED)
        self.custom_edge_widget.setVisible(edge_type == EdgeType.CUSTOM)

        # 如果切换到异形边且没有选择预设，自动加载默认预设
        if edge_type == EdgeType.CUSTOM and self._current_profile is None:
            preset_name = self.preset_selector.get_selected_preset()
            if preset_name:
                self._on_preset_changed(preset_name)

        self._on_param_changed()

    def _on_param_changed(self):
        """参数变化处理"""
        self._update_params()
        self.params_changed.emit()

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
        # 字壳参数
        self._params.shell.height = self._layers_to_mm(self.height_spin.value())
        self._params.shell.layer_height = self.layer_height_spin.value()
        self._params.shell.wall_thickness = self.wall_thickness_spin.value()
        self._params.shell.wall_count = self.wall_count_spin.value()

        # 边缘参数
        self._params.shell.edge_type = self.edge_type_combo.currentData()
        self._params.shell.bevel_direction = self.bevel_direction_combo.currentData()
        self._params.shell.baseplate_thickness = self.baseplate_spin.value()
        self._params.shell.panel_thickness = self.panel_thickness_spin.value()
        self._params.shell.dxf_outer_clearance = self.dxf_outer_clearance_spin.value()
        self._params.shell.dxf_hole_clearance = self.dxf_hole_clearance_spin.value()
        self._params.shell.dxf_laser_kerf = self.dxf_laser_kerf_spin.value()

        # 根据边缘类型设置轮廓
        if self._params.shell.edge_type == EdgeType.CUSTOM:
            # 异形边：使用模板中的原始宽度
            self._params.shell.edge_profile = self._current_profile
            if self._current_profile:
                self._params.shell.bevel_width = self._current_profile.original_width
        else:
            # 直边或斜边
            self._params.shell.bevel_width = self.bevel_width_spin.value()
            self._params.shell.edge_profile = None

        # 换色层参数
        self._params.color.enabled = self.color_enabled.isChecked()

        # 台阶参数
        # 面板台阶（顶部）
        self._params.step.panel_step_enabled = self.panel_step_enabled.isChecked()
        self._params.step.panel_step_height = self._layers_to_mm(self.panel_step_height.value())
        self._params.step.panel_step_width = self.panel_step_width.value()
        self._params.step.panel_step_is_v_groove = self.panel_step_v_groove.isChecked()

        # 底板台阶（底部）
        self._params.step.baseplate_step_enabled = self.baseplate_step_enabled.isChecked()
        self._params.step.baseplate_step_height = self._layers_to_mm(self.baseplate_step_height.value())
        self._params.step.baseplate_step_width = self.baseplate_step_width.value()
        self._params.step.baseplate_step_is_v_groove = self.baseplate_step_v_groove.isChecked()

        # 兼容旧参数
        self._params.step.top_step_enabled = self.panel_step_enabled.isChecked()
        self._params.step.top_step_height = self._layers_to_mm(self.panel_step_height.value())
        self._params.step.top_step_width = self.panel_step_width.value()
        self._params.step.bottom_groove_enabled = self.baseplate_step_enabled.isChecked()
        self._params.step.bottom_groove_height = self._layers_to_mm(self.baseplate_step_height.value())
        self._params.step.bottom_groove_depth = self.baseplate_step_width.value()

        # 启用台阶总开关
        self._params.step.enabled = (
            self._params.step.panel_step_enabled or
            self._params.step.baseplate_step_enabled or
            len(self._params.step.steps) > 0
        )

        # 裙边参数
        self._params.skirt.enabled = self.skirt_enabled.isChecked()
        self._params.skirt.width = self.skirt_width.value()
        self._params.skirt.height = self.skirt_height.value()
        self._params.skirt.interval = self.skirt_interval.value()
        self._params.skirt.offset = self.skirt_offset.value()
        self._params.skirt.outer_enabled = self.skirt_outer_enabled.isChecked()
        self._params.skirt.inner_enabled = self.skirt_inner_enabled.isChecked()
        self._params.skirt.is_outer = self.skirt_outer_enabled.isChecked()

        # 连襟字参数
        self._params.connected.enabled = self.connected_enabled.isChecked()
        self._params.connected.type = self.connected_type.currentData()
        self._params.connected.auto_detect = self.connected_auto_detect.isChecked()
        self._params.connected.width = self.connected_width.value()
        self._params.connected.height = self._layers_to_mm(self.connected_height.value())
        self._params.connected.base_height = self._layers_to_mm(self.connected_base_height.value())
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

        # 底面封闭参数
        self._params.bottom_face.enabled = self.bottom_face_enabled.isChecked()
        self._params.bottom_face.thickness = self._layers_to_mm(self.bottom_face_thickness.value())

        # 灯槽参数
        self._params.light_slot.enabled = self.light_slot_enabled.isChecked()
        self._params.light_slot.width = self.light_slot_width.value()
        self._params.light_slot.depth = self._layers_to_mm(self.light_slot_depth.value())
        self._params.light_slot.floor_layers = self.light_slot_floor_layers.value()
        self._params.light_slot.wall_gap = self.light_slot_wall_gap.value()
        self._params.light_slot.outer_enabled = self.light_slot_outer_enabled.isChecked()
        self._params.light_slot.hole_enabled = self.light_slot_hole_enabled.isChecked()
        self._params.light_slot.auto_skip_small_holes = self.light_slot_auto_skip_small_holes.isChecked()
        self._params.light_slot.min_hole_span = self.light_slot_min_hole_span.value()

        # 顶面封闭参数
        self._params.top_face.enabled = self.top_face_enabled.isChecked()
        self._params.top_face.thickness = self._layers_to_mm(self.top_face_thickness.value())

    def get_params(self) -> SliceParams:
        """获取当前参数"""
        self._update_params()
        return self._params

    def set_params(self, params: SliceParams):
        """设置参数"""
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
            self.height_spin, self.layer_height_spin, self.wall_thickness_spin,
            self.wall_count_spin, self.edge_type_combo, self.bevel_direction_combo,
            self.bevel_width_spin, self.baseplate_spin, self.panel_thickness_spin,
            self.dxf_outer_clearance_spin, self.dxf_hole_clearance_spin, self.dxf_laser_kerf_spin,
            self.print_speed, self.travel_speed, self.first_layer_speed,
            self.skirt_enabled, self.skirt_width, self.skirt_height,
            self.skirt_interval, self.skirt_offset,
            self.skirt_outer_enabled, self.skirt_inner_enabled,
            self.connected_enabled, self.connected_type, self.connected_auto_detect,
            self.connected_width, self.connected_height, self.connected_base_height,
            self.connected_support_offset,
            self.wrap_enabled, self.wrap_width, self.wrap_height,
            self.wrap_dir_inner, self.wrap_dir_outer,
            self.outline_enabled, self.outline_width, self.outline_height,
            self.outline_offset, self.outline_dir_inner, self.outline_dir_outer,
            self.color_enabled, self.color1_height, self.color2_height,
            self.panel_step_enabled, self.panel_step_height, self.panel_step_width,
            self.panel_step_v_groove, self.baseplate_step_enabled,
            self.baseplate_step_height, self.baseplate_step_width, self.baseplate_step_v_groove,
            # 底面封闭控件
            self.bottom_face_enabled, self.bottom_face_thickness,
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
        self.height_spin.setValue(self._height_to_layers(params.shell.height))
        self.wall_thickness_spin.setValue(params.shell.wall_thickness)
        self.wall_count_spin.setValue(params.shell.wall_count)

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
        self.dxf_outer_clearance_spin.setValue(params.shell.dxf_outer_clearance)
        self.dxf_hole_clearance_spin.setValue(params.shell.dxf_hole_clearance)
        self.dxf_laser_kerf_spin.setValue(params.shell.dxf_laser_kerf)

        # 速度参数
        self.print_speed.setValue(int(params.speed.print_speed))
        self.travel_speed.setValue(int(params.speed.travel_speed))
        self.first_layer_speed.setValue(int(params.speed.first_layer_speed))

        # 裙边参数
        self.skirt_width.setValue(params.skirt.width)
        self.skirt_height.setValue(params.skirt.height)
        self.skirt_interval.setValue(params.skirt.interval)
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
        self.connected_height.setValue(self._height_to_layers(params.connected.height))
        self.connected_base_height.setValue(self._height_to_layers(params.connected.base_height))
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

        # 台阶参数 - 面板台阶（顶部）
        self.panel_step_enabled.setChecked(params.step.panel_step_enabled)
        self.panel_step_height.setValue(self._height_to_layers(params.step.panel_step_height))
        self.panel_step_width.setValue(params.step.panel_step_width)
        self.panel_step_v_groove.setChecked(params.step.panel_step_is_v_groove)

        # 台阶参数 - 底板台阶（底部）
        self.baseplate_step_enabled.setChecked(params.step.baseplate_step_enabled)
        self.baseplate_step_height.setValue(self._height_to_layers(params.step.baseplate_step_height))
        self.baseplate_step_width.setValue(params.step.baseplate_step_width)
        self.baseplate_step_v_groove.setChecked(params.step.baseplate_step_is_v_groove)

        # 底面封闭参数
        self.bottom_face_enabled.setChecked(params.bottom_face.enabled)
        self.bottom_face_thickness.setValue(self._height_to_layers(params.bottom_face.thickness))

        # 灯槽参数
        self.light_slot_enabled.setChecked(params.light_slot.enabled)
        self.light_slot_width.setValue(params.light_slot.width)
        self.light_slot_depth.setValue(self._height_to_layers(params.light_slot.depth))
        self.light_slot_floor_layers.setValue(params.light_slot.floor_layers)
        self.light_slot_wall_gap.setValue(params.light_slot.wall_gap)
        self.light_slot_outer_enabled.setChecked(params.light_slot.outer_enabled)
        self.light_slot_hole_enabled.setChecked(params.light_slot.hole_enabled)
        self.light_slot_auto_skip_small_holes.setChecked(params.light_slot.auto_skip_small_holes)
        self.light_slot_min_hole_span.setValue(params.light_slot.min_hole_span)

        # 顶面封闭参数
        self.top_face_enabled.setChecked(params.top_face.enabled)
        self.top_face_thickness.setValue(self._height_to_layers(params.top_face.thickness))

        # 恢复信号
        for w in widgets:
            w.blockSignals(False)

        # 手动更新控件的启用/可见状态
        # 边缘类型：展开对应的参数面板
        edge_type = params.shell.edge_type
        self.bevel_params_widget.setVisible(edge_type == EdgeType.BEVELED)
        self.custom_edge_widget.setVisible(edge_type == EdgeType.CUSTOM)

        # 异形边：恢复 profile 和预设选中状态
        if edge_type == EdgeType.CUSTOM and params.shell.edge_profile is not None:
            self._current_profile = params.shell.edge_profile
            # 恢复预设缩略图的选中高亮
            if params.shell.edge_profile.preset_name:
                self.preset_selector.select_preset(params.shell.edge_profile.preset_name)
            self._update_profile_info()

        self._toggle_skirt_controls(params.skirt.enabled)
        self._toggle_connected_controls(params.connected.enabled)
        self._toggle_wrap_controls(params.edge_wrap.wrap_enabled)
        self._toggle_outline_controls(params.edge_wrap.outline_enabled)
        self._toggle_panel_step_controls(params.step.panel_step_enabled)
        self._toggle_baseplate_step_controls(params.step.baseplate_step_enabled)
        self.color1_height.setEnabled(params.color.enabled)
        self.color2_height.setEnabled(params.color.enabled)
        self._toggle_bottom_face_controls(params.bottom_face.enabled)
        self._toggle_light_slot_controls(params.light_slot.enabled)
        self._toggle_top_face_controls(params.top_face.enabled)
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

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Import Custom Edge DXF"),
            "",
            self.tr("DXF Files (*.dxf);;All Files (*.*)")
        )

        if not file_path:
            return

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
