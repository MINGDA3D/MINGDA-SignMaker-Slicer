"""
字壳工艺参数面板

设置字壳高度、壁厚、边缘类型等核心参数。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QDoubleSpinBox, QSpinBox,
    QComboBox, QCheckBox
)
from PySide6.QtCore import Signal

from src.core.types import ShellParams, EdgeType


class ShellPanel(QWidget):
    """字壳工艺参数面板"""

    params_changed = Signal(object)  # ShellParams

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = ShellParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 打印模式组
        mode_group = QGroupBox("打印模式")
        mode_layout = QFormLayout(mode_group)

        self.mirror_check = QCheckBox("镜像打印")
        mode_layout.addRow(self.mirror_check)

        layout.addWidget(mode_group)

        # 字边类型组
        edge_group = QGroupBox("字边类型")
        edge_layout = QFormLayout(edge_group)

        self.edge_type_combo = QComboBox()
        self.edge_type_combo.addItems(["直边", "斜边", "异形边"])
        edge_layout.addRow("边缘类型:", self.edge_type_combo)

        layout.addWidget(edge_group)

        # 基本参数组
        basic_group = QGroupBox("基本参数")
        basic_layout = QFormLayout(basic_group)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 200)
        self.height_spin.setValue(30.0)
        self.height_spin.setSuffix(" mm")
        basic_layout.addRow("字壳高度:", self.height_spin)

        self.layer_height_spin = QDoubleSpinBox()
        self.layer_height_spin.setRange(0.1, 1.0)
        self.layer_height_spin.setValue(0.3)
        self.layer_height_spin.setSingleStep(0.1)
        self.layer_height_spin.setSuffix(" mm")
        basic_layout.addRow("层高:", self.layer_height_spin)

        self.wall_thickness_spin = QDoubleSpinBox()
        self.wall_thickness_spin.setRange(0.5, 5.0)
        self.wall_thickness_spin.setValue(1.2)
        self.wall_thickness_spin.setSingleStep(0.1)
        self.wall_thickness_spin.setSuffix(" mm")
        basic_layout.addRow("壁厚:", self.wall_thickness_spin)

        layout.addWidget(basic_group)

        # 斜边参数组
        self.bevel_group = QGroupBox("斜边参数")
        bevel_layout = QFormLayout(self.bevel_group)

        self.bevel_width_spin = QDoubleSpinBox()
        self.bevel_width_spin.setRange(1, 50)
        self.bevel_width_spin.setValue(5.0)
        self.bevel_width_spin.setSuffix(" mm")
        bevel_layout.addRow("斜边宽度:", self.bevel_width_spin)

        self.baseplate_spin = QDoubleSpinBox()
        self.baseplate_spin.setRange(0, 50)
        self.baseplate_spin.setValue(10.0)
        self.baseplate_spin.setSuffix(" mm")
        bevel_layout.addRow("底板厚度:", self.baseplate_spin)

        self.panel_spin = QDoubleSpinBox()
        self.panel_spin.setRange(0, 20)
        self.panel_spin.setValue(3.0)
        self.panel_spin.setSuffix(" mm")
        bevel_layout.addRow("面板厚度:", self.panel_spin)

        layout.addWidget(self.bevel_group)
        self.bevel_group.setVisible(False)

        # 多层壁厚组
        wall_group = QGroupBox("多层壁厚")
        wall_layout = QFormLayout(wall_group)

        self.wall_count_spin = QSpinBox()
        self.wall_count_spin.setRange(1, 5)
        self.wall_count_spin.setValue(1)
        wall_layout.addRow("走线次数:", self.wall_count_spin)

        self.wall_offset_spin = QDoubleSpinBox()
        self.wall_offset_spin.setRange(0, 5)
        self.wall_offset_spin.setValue(0.8)
        self.wall_offset_spin.setSuffix(" mm")
        wall_layout.addRow("走线偏移:", self.wall_offset_spin)

        layout.addWidget(wall_group)

        # 预打边线组
        safety_group = QGroupBox("预打边线")
        safety_layout = QFormLayout(safety_group)

        self.safety_offset_spin = QDoubleSpinBox()
        self.safety_offset_spin.setRange(0, 100)
        self.safety_offset_spin.setValue(20.0)
        self.safety_offset_spin.setSuffix(" mm")
        safety_layout.addRow("边线偏移:", self.safety_offset_spin)

        self.safety_count_spin = QSpinBox()
        self.safety_count_spin.setRange(0, 5)
        self.safety_count_spin.setValue(1)
        safety_layout.addRow("边线次数:", self.safety_count_spin)

        layout.addWidget(safety_group)

        layout.addStretch()

    def _connect_signals(self):
        self.edge_type_combo.currentIndexChanged.connect(self._on_edge_type_changed)
        self.height_spin.valueChanged.connect(self._emit_params)
        self.layer_height_spin.valueChanged.connect(self._emit_params)
        self.wall_thickness_spin.valueChanged.connect(self._emit_params)
        self.bevel_width_spin.valueChanged.connect(self._emit_params)
        self.baseplate_spin.valueChanged.connect(self._emit_params)
        self.panel_spin.valueChanged.connect(self._emit_params)
        self.wall_count_spin.valueChanged.connect(self._emit_params)
        self.wall_offset_spin.valueChanged.connect(self._emit_params)
        self.safety_offset_spin.valueChanged.connect(self._emit_params)
        self.safety_count_spin.valueChanged.connect(self._emit_params)
        self.mirror_check.toggled.connect(self._emit_params)

    def _on_edge_type_changed(self, index):
        self.bevel_group.setVisible(index == 1)  # 斜边
        self._emit_params()

    def _emit_params(self):
        self._params.height = self.height_spin.value()
        self._params.layer_height = self.layer_height_spin.value()
        self._params.wall_thickness = self.wall_thickness_spin.value()
        self._params.wall_count = self.wall_count_spin.value()
        self._params.wall_offset = self.wall_offset_spin.value()
        self._params.bevel_width = self.bevel_width_spin.value()
        self._params.baseplate_thickness = self.baseplate_spin.value()
        self._params.panel_thickness = self.panel_spin.value()
        self._params.safety_line_offset = self.safety_offset_spin.value()
        self._params.safety_line_count = self.safety_count_spin.value()
        self._params.is_mirrored = self.mirror_check.isChecked()

        edge_types = [EdgeType.STRAIGHT, EdgeType.BEVELED, EdgeType.CUSTOM]
        self._params.edge_type = edge_types[self.edge_type_combo.currentIndex()]

        self.params_changed.emit(self._params)

    def get_params(self) -> ShellParams:
        return self._params

    def set_params(self, params: ShellParams):
        self._params = params
        self._update_ui()

    def _update_ui(self):
        self.height_spin.setValue(self._params.height)
        self.layer_height_spin.setValue(self._params.layer_height)
        self.wall_thickness_spin.setValue(self._params.wall_thickness)
        self.wall_count_spin.setValue(self._params.wall_count)
        self.wall_offset_spin.setValue(self._params.wall_offset)
        self.bevel_width_spin.setValue(self._params.bevel_width)
        self.baseplate_spin.setValue(self._params.baseplate_thickness)
        self.panel_spin.setValue(self._params.panel_thickness)
        self.safety_offset_spin.setValue(self._params.safety_line_offset)
        self.safety_count_spin.setValue(self._params.safety_line_count)
        self.mirror_check.setChecked(self._params.is_mirrored)

        if self._params.edge_type == EdgeType.STRAIGHT:
            self.edge_type_combo.setCurrentIndex(0)
        elif self._params.edge_type == EdgeType.BEVELED:
            self.edge_type_combo.setCurrentIndex(1)
        else:
            self.edge_type_combo.setCurrentIndex(2)
