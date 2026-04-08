"""
防翘裙边参数面板
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QCheckBox
)
from PySide6.QtCore import Signal

from src.core.types import SkirtParams


class SkirtPanel(QWidget):
    """防翘裙边参数面板"""

    params_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = SkirtParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.enabled_check = QCheckBox("启用防翘裙边")
        layout.addWidget(self.enabled_check)

        # 位置选择
        pos_group = QGroupBox("位置")
        pos_layout = QVBoxLayout(pos_group)
        self.outer_check = QCheckBox("外裙边")
        self.inner_check = QCheckBox("内裙边")
        self.outer_check.setChecked(True)
        pos_layout.addWidget(self.outer_check)
        pos_layout.addWidget(self.inner_check)
        layout.addWidget(pos_group)

        # 参数组
        param_group = QGroupBox("参数")
        param_layout = QFormLayout(param_group)

        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.1, 5.0)
        self.line_width_spin.setValue(0.5)
        self.line_width_spin.setSuffix(" mm")
        param_layout.addRow("压线宽度:", self.line_width_spin)

        self.extrusion_spin = QDoubleSpinBox()
        self.extrusion_spin.setRange(0.5, 3.0)
        self.extrusion_spin.setValue(1.2)
        self.extrusion_spin.setSuffix(" mm")
        param_layout.addRow("吐丝宽度:", self.extrusion_spin)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(10, 100)
        self.speed_spin.setValue(20.0)
        self.speed_spin.setSuffix(" mm/s")
        param_layout.addRow("防翘速度:", self.speed_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.1, 2.0)
        self.height_spin.setValue(0.3)
        self.height_spin.setSuffix(" mm")
        param_layout.addRow("防翘高度:", self.height_spin)

        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(1, 50)
        self.length_spin.setValue(10.0)
        self.length_spin.setSuffix(" mm")
        param_layout.addRow("防翘长度:", self.length_spin)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 20)
        self.width_spin.setValue(5.0)
        self.width_spin.setSuffix(" mm")
        param_layout.addRow("防翘宽度:", self.width_spin)

        self.v_opening_spin = QDoubleSpinBox()
        self.v_opening_spin.setRange(0.5, 10)
        self.v_opening_spin.setValue(3.0)
        self.v_opening_spin.setSuffix(" mm")
        param_layout.addRow("V型开口:", self.v_opening_spin)

        layout.addWidget(param_group)
        layout.addStretch()

    def _connect_signals(self):
        self.enabled_check.toggled.connect(self._emit_params)
        self.outer_check.toggled.connect(self._emit_params)
        self.inner_check.toggled.connect(self._emit_params)
        self.line_width_spin.valueChanged.connect(self._emit_params)
        self.extrusion_spin.valueChanged.connect(self._emit_params)
        self.speed_spin.valueChanged.connect(self._emit_params)
        self.height_spin.valueChanged.connect(self._emit_params)
        self.length_spin.valueChanged.connect(self._emit_params)
        self.width_spin.valueChanged.connect(self._emit_params)
        self.v_opening_spin.valueChanged.connect(self._emit_params)

    def _emit_params(self):
        self._params.enabled = self.enabled_check.isChecked()
        self._params.outer_enabled = self.outer_check.isChecked()
        self._params.inner_enabled = self.inner_check.isChecked()
        self._params.is_outer = self.outer_check.isChecked()
        self._params.line_width = self.line_width_spin.value()
        self._params.extrusion_width = self.extrusion_spin.value()
        self._params.speed = self.speed_spin.value()
        self._params.height = self.height_spin.value()
        self._params.length = self.length_spin.value()
        self._params.width = self.width_spin.value()
        self._params.v_opening = self.v_opening_spin.value()
        self.params_changed.emit(self._params)

    def get_params(self) -> SkirtParams:
        return self._params

    def set_params(self, params: SkirtParams):
        self._params = params
        self._update_ui()

    def _update_ui(self):
        self.enabled_check.setChecked(self._params.enabled)
        self.outer_check.setChecked(self._params.outer_enabled)
        self.inner_check.setChecked(self._params.inner_enabled)
        self.line_width_spin.setValue(self._params.line_width)
        self.extrusion_spin.setValue(self._params.extrusion_width)
        self.speed_spin.setValue(self._params.speed)
        self.height_spin.setValue(self._params.height)
        self.length_spin.setValue(self._params.length)
        self.width_spin.setValue(self._params.width)
        self.v_opening_spin.setValue(self._params.v_opening)
