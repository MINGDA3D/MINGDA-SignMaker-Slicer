"""
导出参数面板
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QCheckBox, QLineEdit, QPushButton,
    QFileDialog, QHBoxLayout
)
from PySide6.QtCore import Signal

from src.business.settings_manager import get_settings_manager
from src.core.types import GCodeParams


class ExportPanel(QWidget):
    """导出参数面板"""

    params_changed = Signal(object)  # GCodeParams
    export_requested = Signal(str, object)  # (file_path, GCodeParams)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = GCodeParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 输出文件
        file_group = QGroupBox("输出文件")
        file_layout = QVBoxLayout(file_group)

        path_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择输出路径...")
        self.browse_btn = QPushButton("浏览")
        path_layout.addWidget(self.file_path_edit)
        path_layout.addWidget(self.browse_btn)
        file_layout.addLayout(path_layout)

        layout.addWidget(file_group)

        # 速度参数
        speed_group = QGroupBox("速度参数")
        speed_layout = QFormLayout(speed_group)

        self.print_speed_spin = QDoubleSpinBox()
        self.print_speed_spin.setRange(10, 150)
        self.print_speed_spin.setValue(40.0)
        self.print_speed_spin.setSuffix(" mm/s")
        speed_layout.addRow("打印速度:", self.print_speed_spin)

        self.first_layer_speed_spin = QDoubleSpinBox()
        self.first_layer_speed_spin.setRange(10, 100)
        self.first_layer_speed_spin.setValue(30.0)
        self.first_layer_speed_spin.setSuffix(" mm/s")
        speed_layout.addRow("首层速度:", self.first_layer_speed_spin)

        self.travel_speed_spin = QDoubleSpinBox()
        self.travel_speed_spin.setRange(100, 500)
        self.travel_speed_spin.setValue(300.0)
        self.travel_speed_spin.setSuffix(" mm/s")
        speed_layout.addRow("空程速度:", self.travel_speed_spin)

        layout.addWidget(speed_group)

        # 温度参数
        temp_group = QGroupBox("温度参数")
        temp_layout = QFormLayout(temp_group)

        self.extruder1_temp_spin = QDoubleSpinBox()
        self.extruder1_temp_spin.setRange(180, 300)
        self.extruder1_temp_spin.setValue(220)
        self.extruder1_temp_spin.setSuffix(" °C")
        temp_layout.addRow("喷头1温度:", self.extruder1_temp_spin)

        self.extruder2_temp_spin = QDoubleSpinBox()
        self.extruder2_temp_spin.setRange(0, 300)
        self.extruder2_temp_spin.setValue(220)
        self.extruder2_temp_spin.setSuffix(" °C")
        temp_layout.addRow("喷头2温度:", self.extruder2_temp_spin)

        self.extruder3_temp_spin = QDoubleSpinBox()
        self.extruder3_temp_spin.setRange(0, 300)
        self.extruder3_temp_spin.setValue(220)
        self.extruder3_temp_spin.setSuffix(" °C")
        temp_layout.addRow("喷头3温度:", self.extruder3_temp_spin)

        layout.addWidget(temp_group)

        # 其他选项
        other_group = QGroupBox("其他选项")
        other_layout = QVBoxLayout(other_group)

        self.alternate_check = QCheckBox("头尾交替打印")
        self.no_retract_check = QCheckBox("结束不回抽")
        other_layout.addWidget(self.alternate_check)
        other_layout.addWidget(self.no_retract_check)

        layout.addWidget(other_group)

        # 导出按钮
        self.export_btn = QPushButton("生成 G-code")
        self.export_btn.setMinimumHeight(40)
        layout.addWidget(self.export_btn)

        layout.addStretch()

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._browse_file)
        self.export_btn.clicked.connect(self._on_export)
        self.print_speed_spin.valueChanged.connect(self._emit_params)
        self.first_layer_speed_spin.valueChanged.connect(self._emit_params)
        self.travel_speed_spin.valueChanged.connect(self._emit_params)
        self.extruder1_temp_spin.valueChanged.connect(self._emit_params)
        self.extruder2_temp_spin.valueChanged.connect(self._emit_params)
        self.extruder3_temp_spin.valueChanged.connect(self._emit_params)
        self.alternate_check.toggled.connect(self._emit_params)
        self.no_retract_check.toggled.connect(self._emit_params)

    def _browse_file(self):
        settings = get_settings_manager()
        initial_dir = settings.get_last_save_dir() if settings else ""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存G-code文件", initial_dir, "G-code文件 (*.gcode)"
        )
        if file_path:
            if settings:
                settings.set_last_save_dir(str(Path(file_path).expanduser().resolve(strict=False).parent))
            self.file_path_edit.setText(file_path)

    def _on_export(self):
        file_path = self.file_path_edit.text()
        if file_path:
            self.export_requested.emit(file_path, self._params)

    def _emit_params(self):
        self._params.print_speed = self.print_speed_spin.value()
        self._params.first_layer_speed = self.first_layer_speed_spin.value()
        self._params.travel_speed = self.travel_speed_spin.value()
        self._params.extruder1_temp = int(self.extruder1_temp_spin.value())
        self._params.extruder2_temp = int(self.extruder2_temp_spin.value())
        self._params.extruder3_temp = int(self.extruder3_temp_spin.value())
        self._params.alternate_direction = self.alternate_check.isChecked()
        self._params.no_retract_on_finish = self.no_retract_check.isChecked()
        self.params_changed.emit(self._params)

    def get_params(self) -> GCodeParams:
        return self._params

    def set_params(self, params: GCodeParams):
        self._params = params
        self._update_ui()

    def _update_ui(self):
        self.print_speed_spin.setValue(self._params.print_speed)
        self.first_layer_speed_spin.setValue(self._params.first_layer_speed)
        self.travel_speed_spin.setValue(self._params.travel_speed)
        self.extruder1_temp_spin.setValue(self._params.extruder1_temp)
        self.extruder2_temp_spin.setValue(self._params.extruder2_temp)
        self.extruder3_temp_spin.setValue(self._params.extruder3_temp)
        self.alternate_check.setChecked(self._params.alternate_direction)
        self.no_retract_check.setChecked(self._params.no_retract_on_finish)
