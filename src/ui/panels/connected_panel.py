"""
连襟字参数面板
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QCheckBox, QComboBox
)
from PySide6.QtCore import Signal

from src.core.types import ConnectedParams


class ConnectedPanel(QWidget):
    """连襟字参数面板"""

    params_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = ConnectedParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.enabled_check = QCheckBox("启用连襟字")
        layout.addWidget(self.enabled_check)

        # 类型选择
        type_group = QGroupBox("连襟类型")
        type_layout = QFormLayout(type_group)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["三角形连襟", "菱形连襟"])
        type_layout.addRow("类型:", self.type_combo)

        self.auto_detect_check = QCheckBox("自动检测连接点")
        self.auto_detect_check.setChecked(True)
        type_layout.addRow(self.auto_detect_check)

        layout.addWidget(type_group)

        # 参数组
        param_group = QGroupBox("参数")
        param_layout = QFormLayout(param_group)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 50)
        self.width_spin.setValue(15.0)
        self.width_spin.setSuffix(" mm")
        param_layout.addRow("连襟宽度:", self.width_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 20)
        self.height_spin.setValue(5.0)
        self.height_spin.setSuffix(" mm")
        param_layout.addRow("斜边高度:", self.height_spin)

        self.base_height_spin = QDoubleSpinBox()
        self.base_height_spin.setRange(1, 20)
        self.base_height_spin.setValue(5.0)
        self.base_height_spin.setSuffix(" mm")
        param_layout.addRow("底座高度:", self.base_height_spin)

        self.support_offset_spin = QDoubleSpinBox()
        self.support_offset_spin.setRange(0, 10)
        self.support_offset_spin.setValue(2.5)
        self.support_offset_spin.setSuffix(" mm")
        param_layout.addRow("支撑偏移:", self.support_offset_spin)

        layout.addWidget(param_group)
        layout.addStretch()

    def _connect_signals(self):
        self.enabled_check.toggled.connect(self._emit_params)
        self.type_combo.currentIndexChanged.connect(self._emit_params)
        self.auto_detect_check.toggled.connect(self._emit_params)
        self.width_spin.valueChanged.connect(self._emit_params)
        self.height_spin.valueChanged.connect(self._emit_params)
        self.base_height_spin.valueChanged.connect(self._emit_params)
        self.support_offset_spin.valueChanged.connect(self._emit_params)

    def _emit_params(self):
        self._params.enabled = self.enabled_check.isChecked()
        self._params.type = "triangle" if self.type_combo.currentIndex() == 0 else "diamond"
        self._params.auto_detect = self.auto_detect_check.isChecked()
        self._params.width = self.width_spin.value()
        self._params.height = self.height_spin.value()
        self._params.base_height = self.base_height_spin.value()
        self._params.support_offset = self.support_offset_spin.value()
        self.params_changed.emit(self._params)

    def get_params(self) -> ConnectedParams:
        return self._params

    def set_params(self, params: ConnectedParams):
        self._params = params
        self._update_ui()

    def _update_ui(self):
        self.enabled_check.setChecked(self._params.enabled)
        self.type_combo.setCurrentIndex(0 if self._params.type == "triangle" else 1)
        self.auto_detect_check.setChecked(self._params.auto_detect)
        self.width_spin.setValue(self._params.width)
        self.height_spin.setValue(self._params.height)
        self.base_height_spin.setValue(self._params.base_height)
        self.support_offset_spin.setValue(self._params.support_offset)
