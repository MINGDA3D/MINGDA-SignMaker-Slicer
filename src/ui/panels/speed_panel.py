"""
速度参数面板
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox
)
from PySide6.QtCore import Signal


class SpeedPanel(QWidget):
    """速度参数面板"""

    params_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 打印速度组
        print_group = QGroupBox("打印速度")
        print_layout = QFormLayout(print_group)

        self.print_speed_spin = QDoubleSpinBox()
        self.print_speed_spin.setRange(10, 150)
        self.print_speed_spin.setValue(40.0)
        self.print_speed_spin.setSuffix(" mm/s")
        print_layout.addRow("打印速度:", self.print_speed_spin)

        self.first_layer_spin = QDoubleSpinBox()
        self.first_layer_spin.setRange(10, 100)
        self.first_layer_spin.setValue(30.0)
        self.first_layer_spin.setSuffix(" mm/s")
        print_layout.addRow("首层速度:", self.first_layer_spin)

        self.infill_speed_spin = QDoubleSpinBox()
        self.infill_speed_spin.setRange(10, 150)
        self.infill_speed_spin.setValue(50.0)
        self.infill_speed_spin.setSuffix(" mm/s")
        print_layout.addRow("填充速度:", self.infill_speed_spin)

        layout.addWidget(print_group)

        # 移动速度组
        move_group = QGroupBox("移动速度")
        move_layout = QFormLayout(move_group)

        self.travel_speed_spin = QDoubleSpinBox()
        self.travel_speed_spin.setRange(100, 500)
        self.travel_speed_spin.setValue(300.0)
        self.travel_speed_spin.setSuffix(" mm/s")
        move_layout.addRow("空程速度:", self.travel_speed_spin)

        self.z_speed_spin = QDoubleSpinBox()
        self.z_speed_spin.setRange(1, 50)
        self.z_speed_spin.setValue(5.0)
        self.z_speed_spin.setSuffix(" mm/s")
        move_layout.addRow("Z轴速度:", self.z_speed_spin)

        layout.addWidget(move_group)

        # 回抽速度组
        retract_group = QGroupBox("回抽速度")
        retract_layout = QFormLayout(retract_group)

        self.retract_speed_spin = QDoubleSpinBox()
        self.retract_speed_spin.setRange(10, 100)
        self.retract_speed_spin.setValue(40.0)
        self.retract_speed_spin.setSuffix(" mm/s")
        retract_layout.addRow("回抽速度:", self.retract_speed_spin)

        self.color_change_speed_spin = QDoubleSpinBox()
        self.color_change_speed_spin.setRange(10, 100)
        self.color_change_speed_spin.setValue(50.0)
        self.color_change_speed_spin.setSuffix(" mm/s")
        retract_layout.addRow("换色速度:", self.color_change_speed_spin)

        layout.addWidget(retract_group)

        layout.addStretch()

    def _connect_signals(self):
        self.print_speed_spin.valueChanged.connect(self._emit_params)
        self.first_layer_spin.valueChanged.connect(self._emit_params)
        self.infill_speed_spin.valueChanged.connect(self._emit_params)
        self.travel_speed_spin.valueChanged.connect(self._emit_params)
        self.z_speed_spin.valueChanged.connect(self._emit_params)
        self.retract_speed_spin.valueChanged.connect(self._emit_params)
        self.color_change_speed_spin.valueChanged.connect(self._emit_params)

    def _emit_params(self):
        params = {
            'print_speed': self.print_speed_spin.value(),
            'first_layer_speed': self.first_layer_spin.value(),
            'infill_speed': self.infill_speed_spin.value(),
            'travel_speed': self.travel_speed_spin.value(),
            'z_speed': self.z_speed_spin.value(),
            'retract_speed': self.retract_speed_spin.value(),
            'color_change_speed': self.color_change_speed_spin.value(),
        }
        self.params_changed.emit(params)
