"""
包边勾边参数面板
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QCheckBox, QRadioButton
)
from PySide6.QtCore import Signal

from src.core.types import EdgeWrapParams


class EdgeWrapPanel(QWidget):
    """包边勾边参数面板"""

    params_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = EdgeWrapParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 功能选项
        enable_group = QGroupBox("功能选项")
        enable_layout = QVBoxLayout(enable_group)

        self.wrap_check = QCheckBox("包边有效")
        self.outline_check = QCheckBox("勾边有效")
        enable_layout.addWidget(self.wrap_check)
        enable_layout.addWidget(self.outline_check)

        self.inner_radio = QRadioButton("内部")
        self.outer_radio = QRadioButton("外部")
        self.inner_radio.setChecked(True)
        enable_layout.addWidget(self.inner_radio)
        enable_layout.addWidget(self.outer_radio)

        layout.addWidget(enable_group)

        # 参数组
        param_group = QGroupBox("参数")
        param_layout = QFormLayout(param_group)

        self.wrap_height_spin = QDoubleSpinBox()
        self.wrap_height_spin.setRange(0.3, 5.0)
        self.wrap_height_spin.setValue(1.2)
        self.wrap_height_spin.setSuffix(" mm")
        param_layout.addRow("包边高度:", self.wrap_height_spin)

        self.outline_height_spin = QDoubleSpinBox()
        self.outline_height_spin.setRange(0.3, 5.0)
        self.outline_height_spin.setValue(1.2)
        self.outline_height_spin.setSuffix(" mm")
        param_layout.addRow("勾边高度:", self.outline_height_spin)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 10)
        self.width_spin.setValue(3.0)
        self.width_spin.setSuffix(" mm")
        param_layout.addRow("勾包边宽度:", self.width_spin)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(10, 100)
        self.speed_spin.setValue(40.0)
        self.speed_spin.setSuffix(" mm/s")
        param_layout.addRow("打印速度:", self.speed_spin)

        self.wrap_offset_spin = QDoubleSpinBox()
        self.wrap_offset_spin.setRange(-2, 2)
        self.wrap_offset_spin.setValue(0.0)
        self.wrap_offset_spin.setSuffix(" mm")
        param_layout.addRow("包边偏移:", self.wrap_offset_spin)

        self.outline_offset_spin = QDoubleSpinBox()
        self.outline_offset_spin.setRange(-2, 2)
        self.outline_offset_spin.setValue(0.0)
        self.outline_offset_spin.setSuffix(" mm")
        param_layout.addRow("勾边偏移:", self.outline_offset_spin)

        self.extrusion_spin = QDoubleSpinBox()
        self.extrusion_spin.setRange(0.5, 3.0)
        self.extrusion_spin.setValue(1.2)
        self.extrusion_spin.setSuffix(" mm")
        param_layout.addRow("吐丝宽度:", self.extrusion_spin)

        layout.addWidget(param_group)
        layout.addStretch()

    def _connect_signals(self):
        self.wrap_check.toggled.connect(self._emit_params)
        self.outline_check.toggled.connect(self._emit_params)
        self.inner_radio.toggled.connect(self._emit_params)
        self.wrap_height_spin.valueChanged.connect(self._emit_params)
        self.outline_height_spin.valueChanged.connect(self._emit_params)
        self.width_spin.valueChanged.connect(self._emit_params)
        self.speed_spin.valueChanged.connect(self._emit_params)
        self.wrap_offset_spin.valueChanged.connect(self._emit_params)
        self.outline_offset_spin.valueChanged.connect(self._emit_params)
        self.extrusion_spin.valueChanged.connect(self._emit_params)

    def _emit_params(self):
        self._params.wrap_enabled = self.wrap_check.isChecked()
        self._params.outline_enabled = self.outline_check.isChecked()
        self._params.is_inner = self.inner_radio.isChecked()
        self._params.wrap_height = self.wrap_height_spin.value()
        self._params.outline_height = self.outline_height_spin.value()
        self._params.width = self.width_spin.value()
        self._params.speed = self.speed_spin.value()
        self._params.wrap_offset = self.wrap_offset_spin.value()
        self._params.outline_offset = self.outline_offset_spin.value()
        self._params.extrusion_width = self.extrusion_spin.value()
        self.params_changed.emit(self._params)

    def get_params(self) -> EdgeWrapParams:
        return self._params

    def set_params(self, params: EdgeWrapParams):
        self._params = params
        self._update_ui()

    def _update_ui(self):
        self.wrap_check.setChecked(self._params.wrap_enabled)
        self.outline_check.setChecked(self._params.outline_enabled)
        self.inner_radio.setChecked(self._params.is_inner)
        self.outer_radio.setChecked(not self._params.is_inner)
        self.wrap_height_spin.setValue(self._params.wrap_height)
        self.outline_height_spin.setValue(self._params.outline_height)
        self.width_spin.setValue(self._params.width)
        self.speed_spin.setValue(self._params.speed)
        self.wrap_offset_spin.setValue(self._params.wrap_offset)
        self.outline_offset_spin.setValue(self._params.outline_offset)
        self.extrusion_spin.setValue(self._params.extrusion_width)
