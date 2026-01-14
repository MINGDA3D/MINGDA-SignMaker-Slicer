"""
机器参数面板
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Signal


class MachinePanel(QWidget):
    """机器参数面板"""

    params_changed = Signal(dict)

    # 预设机器类型
    MACHINE_PRESETS = {
        "ZC-60": {"width": 600, "height": 600},
        "ZC-80": {"width": 800, "height": 800},
        "ZC-120": {"width": 1200, "height": 1200},
        "自定义": {"width": 600, "height": 600},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 机器类型
        type_group = QGroupBox("机器类型")
        type_layout = QFormLayout(type_group)

        self.machine_combo = QComboBox()
        self.machine_combo.addItems(list(self.MACHINE_PRESETS.keys()))
        type_layout.addRow("机器:", self.machine_combo)

        layout.addWidget(type_group)

        # 版面尺寸
        size_group = QGroupBox("版面尺寸")
        size_layout = QFormLayout(size_group)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(100, 3000)
        self.width_spin.setValue(600)
        self.width_spin.setSuffix(" mm")
        size_layout.addRow("宽度:", self.width_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(100, 3000)
        self.height_spin.setValue(600)
        self.height_spin.setSuffix(" mm")
        size_layout.addRow("高度:", self.height_spin)

        layout.addWidget(size_group)

        # 材料参数
        material_group = QGroupBox("材料参数")
        material_layout = QFormLayout(material_group)

        self.filament_spin = QDoubleSpinBox()
        self.filament_spin.setRange(1.0, 3.0)
        self.filament_spin.setValue(1.75)
        self.filament_spin.setSuffix(" mm")
        material_layout.addRow("材料直径:", self.filament_spin)

        layout.addWidget(material_group)

        # 回抽参数
        retract_group = QGroupBox("回抽参数")
        retract_layout = QFormLayout(retract_group)

        self.retract_length_spin = QDoubleSpinBox()
        self.retract_length_spin.setRange(0, 10)
        self.retract_length_spin.setValue(2.0)
        self.retract_length_spin.setSuffix(" mm")
        retract_layout.addRow("回抽长度:", self.retract_length_spin)

        self.color_retract_spin = QDoubleSpinBox()
        self.color_retract_spin.setRange(0, 100)
        self.color_retract_spin.setValue(50.0)
        self.color_retract_spin.setSuffix(" mm")
        retract_layout.addRow("换色回抽:", self.color_retract_spin)

        self.color_prime_spin = QDoubleSpinBox()
        self.color_prime_spin.setRange(0, 100)
        self.color_prime_spin.setValue(52.0)
        self.color_prime_spin.setSuffix(" mm")
        retract_layout.addRow("换色补偿:", self.color_prime_spin)

        layout.addWidget(retract_group)

        # 空走参数
        hop_group = QGroupBox("空走参数")
        hop_layout = QFormLayout(hop_group)

        self.z_hop1_spin = QDoubleSpinBox()
        self.z_hop1_spin.setRange(0, 10)
        self.z_hop1_spin.setValue(1.0)
        self.z_hop1_spin.setSuffix(" mm")
        hop_layout.addRow("抬头高度1:", self.z_hop1_spin)

        self.z_hop2_spin = QDoubleSpinBox()
        self.z_hop2_spin.setRange(0, 10)
        self.z_hop2_spin.setValue(2.0)
        self.z_hop2_spin.setSuffix(" mm")
        hop_layout.addRow("抬头高度2:", self.z_hop2_spin)

        self.max_travel_spin = QDoubleSpinBox()
        self.max_travel_spin.setRange(10, 500)
        self.max_travel_spin.setValue(100.0)
        self.max_travel_spin.setSuffix(" mm")
        hop_layout.addRow("最长空走:", self.max_travel_spin)

        layout.addWidget(hop_group)

        layout.addStretch()

    def _connect_signals(self):
        self.machine_combo.currentTextChanged.connect(self._on_machine_changed)
        self.width_spin.valueChanged.connect(self._emit_params)
        self.height_spin.valueChanged.connect(self._emit_params)
        self.filament_spin.valueChanged.connect(self._emit_params)
        self.retract_length_spin.valueChanged.connect(self._emit_params)
        self.color_retract_spin.valueChanged.connect(self._emit_params)
        self.color_prime_spin.valueChanged.connect(self._emit_params)
        self.z_hop1_spin.valueChanged.connect(self._emit_params)
        self.z_hop2_spin.valueChanged.connect(self._emit_params)
        self.max_travel_spin.valueChanged.connect(self._emit_params)

    def _on_machine_changed(self, name):
        if name in self.MACHINE_PRESETS and name != "自定义":
            preset = self.MACHINE_PRESETS[name]
            self.width_spin.setValue(preset['width'])
            self.height_spin.setValue(preset['height'])
        self._emit_params()

    def _emit_params(self):
        params = {
            'machine_type': self.machine_combo.currentText(),
            'bed_width': self.width_spin.value(),
            'bed_height': self.height_spin.value(),
            'filament_diameter': self.filament_spin.value(),
            'retract_length': self.retract_length_spin.value(),
            'color_change_retract': self.color_retract_spin.value(),
            'color_change_prime': self.color_prime_spin.value(),
            'z_hop_height1': self.z_hop1_spin.value(),
            'z_hop_height2': self.z_hop2_spin.value(),
            'max_travel_distance': self.max_travel_spin.value(),
        }
        self.params_changed.emit(params)
