"""
台阶V槽参数面板

设置台阶位置、高度和宽度。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QSpinBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Signal

from src.core.types import StepParams, StepConfig


class StepPanel(QWidget):
    """台阶V槽参数面板"""

    params_changed = Signal(object)  # StepParams

    MAX_STEPS = 7

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = StepParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 台阶表格
        self.step_table = QTableWidget()
        self.step_table.setColumnCount(4)
        self.step_table.setHorizontalHeaderLabels(["启用", "位置(mm)", "高度(mm)", "宽度(mm)"])
        self.step_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.step_table.setRowCount(self.MAX_STEPS)

        # 初始化表格行
        for row in range(self.MAX_STEPS):
            # 启用复选框
            enabled_check = QCheckBox()
            enabled_check.toggled.connect(self._emit_params)
            self.step_table.setCellWidget(row, 0, enabled_check)

            # 位置
            pos_item = QTableWidgetItem("0.0")
            self.step_table.setItem(row, 1, pos_item)

            # 高度 (1.2=V型, 0=平台阶)
            height_item = QTableWidgetItem("1.2")
            self.step_table.setItem(row, 2, height_item)

            # 宽度
            width_item = QTableWidgetItem("1.2")
            self.step_table.setItem(row, 3, width_item)

        layout.addWidget(self.step_table)

        # 打印参数组
        print_group = QGroupBox("台阶打印参数")
        print_layout = QFormLayout(print_group)

        self.step_speed_spin = QDoubleSpinBox()
        self.step_speed_spin.setRange(10, 100)
        self.step_speed_spin.setValue(30.0)
        self.step_speed_spin.setSuffix(" mm/s")
        print_layout.addRow("卡槽/V槽速度:", self.step_speed_spin)

        self.nozzle_offset_spin = QDoubleSpinBox()
        self.nozzle_offset_spin.setRange(-5, 5)
        self.nozzle_offset_spin.setValue(0.0)
        self.nozzle_offset_spin.setSuffix(" mm")
        print_layout.addRow("喷头偏移:", self.nozzle_offset_spin)

        self.extrusion_width_spin = QDoubleSpinBox()
        self.extrusion_width_spin.setRange(0.5, 3.0)
        self.extrusion_width_spin.setValue(1.2)
        self.extrusion_width_spin.setSuffix(" mm")
        print_layout.addRow("吐丝宽度:", self.extrusion_width_spin)

        self.step_thickness_spin = QDoubleSpinBox()
        self.step_thickness_spin.setRange(0.1, 1.0)
        self.step_thickness_spin.setValue(0.3)
        self.step_thickness_spin.setSuffix(" mm")
        print_layout.addRow("台阶厚度:", self.step_thickness_spin)

        layout.addWidget(print_group)

        layout.addStretch()

    def _connect_signals(self):
        self.step_table.cellChanged.connect(self._emit_params)
        self.step_speed_spin.valueChanged.connect(self._emit_params)
        self.nozzle_offset_spin.valueChanged.connect(self._emit_params)
        self.extrusion_width_spin.valueChanged.connect(self._emit_params)
        self.step_thickness_spin.valueChanged.connect(self._emit_params)

    def _emit_params(self):
        self._params.step_speed = self.step_speed_spin.value()
        self._params.nozzle_offset = self.nozzle_offset_spin.value()
        self._params.extrusion_width = self.extrusion_width_spin.value()
        self._params.step_thickness = self.step_thickness_spin.value()

        # 读取表格数据
        self._params.steps = []
        for row in range(self.MAX_STEPS):
            enabled_check = self.step_table.cellWidget(row, 0)
            pos_item = self.step_table.item(row, 1)
            height_item = self.step_table.item(row, 2)
            width_item = self.step_table.item(row, 3)

            if enabled_check and pos_item and height_item and width_item:
                try:
                    self._params.steps.append(StepConfig(
                        enabled=enabled_check.isChecked(),
                        position=float(pos_item.text()),
                        height=float(height_item.text()),
                        width=float(width_item.text())
                    ))
                except ValueError:
                    pass

        self.params_changed.emit(self._params)

    def get_params(self) -> StepParams:
        return self._params

    def set_params(self, params: StepParams):
        self._params = params
        self._update_ui()

    def _update_ui(self):
        self.step_speed_spin.setValue(self._params.step_speed)
        self.nozzle_offset_spin.setValue(self._params.nozzle_offset)
        self.extrusion_width_spin.setValue(self._params.extrusion_width)
        self.step_thickness_spin.setValue(self._params.step_thickness)

        for row, step in enumerate(self._params.steps[:self.MAX_STEPS]):
            enabled_check = self.step_table.cellWidget(row, 0)
            if enabled_check:
                enabled_check.setChecked(step.enabled)
            if self.step_table.item(row, 1):
                self.step_table.item(row, 1).setText(str(step.position))
            if self.step_table.item(row, 2):
                self.step_table.item(row, 2).setText(str(step.height))
            if self.step_table.item(row, 3):
                self.step_table.item(row, 3).setText(str(step.width))
