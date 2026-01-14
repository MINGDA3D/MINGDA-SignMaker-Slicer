"""
换色层参数面板

设置多挤出机换色层配置。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QDoubleSpinBox, QSpinBox,
    QComboBox, QCheckBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Signal

from src.core.types import ColorParams, ColorLayerConfig, ExtruderType


class ColorPanel(QWidget):
    """换色层参数面板"""

    params_changed = Signal(object)  # ColorParams

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = ColorParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 启用开关
        self.enabled_check = QCheckBox("启用换色层")
        layout.addWidget(self.enabled_check)

        # 换色层表格
        self.layer_table = QTableWidget()
        self.layer_table.setColumnCount(2)
        self.layer_table.setHorizontalHeaderLabels(["层高 (mm)", "挤出机"])
        self.layer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.layer_table)

        # 按钮行
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加层")
        self.remove_btn = QPushButton("删除层")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        layout.addLayout(btn_layout)

        # 换色偏移
        offset_group = QGroupBox("换色设置")
        offset_layout = QFormLayout(offset_group)

        self.color_offset_spin = QDoubleSpinBox()
        self.color_offset_spin.setRange(0, 50)
        self.color_offset_spin.setValue(5.0)
        self.color_offset_spin.setSuffix(" mm")
        offset_layout.addRow("换色偏移:", self.color_offset_spin)

        layout.addWidget(offset_group)

        # 双层打印组
        dual_group = QGroupBox("双层打印（外黑内白）")
        dual_layout = QFormLayout(dual_group)

        self.dual_enabled_check = QCheckBox("启用喷头2")
        dual_layout.addRow(self.dual_enabled_check)

        self.dual_width_spin = QDoubleSpinBox()
        self.dual_width_spin.setRange(0.5, 5.0)
        self.dual_width_spin.setValue(1.2)
        self.dual_width_spin.setSuffix(" mm")
        dual_layout.addRow("吐丝宽度:", self.dual_width_spin)

        self.dual_offset_spin = QDoubleSpinBox()
        self.dual_offset_spin.setRange(0, 5.0)
        self.dual_offset_spin.setValue(0.8)
        self.dual_offset_spin.setSuffix(" mm")
        dual_layout.addRow("走线偏移:", self.dual_offset_spin)

        layout.addWidget(dual_group)

        layout.addStretch()

    def _connect_signals(self):
        self.enabled_check.toggled.connect(self._emit_params)
        self.add_btn.clicked.connect(self._add_layer)
        self.remove_btn.clicked.connect(self._remove_layer)
        self.color_offset_spin.valueChanged.connect(self._emit_params)
        self.dual_enabled_check.toggled.connect(self._emit_params)
        self.dual_width_spin.valueChanged.connect(self._emit_params)
        self.dual_offset_spin.valueChanged.connect(self._emit_params)
        self.layer_table.cellChanged.connect(self._emit_params)

    def _add_layer(self):
        row = self.layer_table.rowCount()
        self.layer_table.insertRow(row)

        # 层高
        height_item = QTableWidgetItem("5.0")
        self.layer_table.setItem(row, 0, height_item)

        # 挤出机选择
        extruder_combo = QComboBox()
        extruder_combo.addItems(["挤出机1", "挤出机2", "挤出机3"])
        extruder_combo.currentIndexChanged.connect(self._emit_params)
        self.layer_table.setCellWidget(row, 1, extruder_combo)

        self._emit_params()

    def _remove_layer(self):
        row = self.layer_table.currentRow()
        if row >= 0:
            self.layer_table.removeRow(row)
            self._emit_params()

    def _emit_params(self):
        self._params.enabled = self.enabled_check.isChecked()
        self._params.color_offset = self.color_offset_spin.value()
        self._params.dual_wall_enabled = self.dual_enabled_check.isChecked()
        self._params.dual_wall_width = self.dual_width_spin.value()
        self._params.dual_wall_offset = self.dual_offset_spin.value()

        # 读取表格数据
        self._params.layers = []
        for row in range(self.layer_table.rowCount()):
            height_item = self.layer_table.item(row, 0)
            extruder_combo = self.layer_table.cellWidget(row, 1)

            if height_item and extruder_combo:
                try:
                    height = float(height_item.text())
                    extruder_index = extruder_combo.currentIndex()
                    extruder = [ExtruderType.EXTRUDER_1,
                                ExtruderType.EXTRUDER_2,
                                ExtruderType.EXTRUDER_3][extruder_index]

                    self._params.layers.append(ColorLayerConfig(
                        height=height,
                        extruder=extruder
                    ))
                except ValueError:
                    pass

        self.params_changed.emit(self._params)

    def get_params(self) -> ColorParams:
        return self._params

    def set_params(self, params: ColorParams):
        self._params = params
        self._update_ui()

    def _update_ui(self):
        self.enabled_check.setChecked(self._params.enabled)
        self.color_offset_spin.setValue(self._params.color_offset)
        self.dual_enabled_check.setChecked(self._params.dual_wall_enabled)
        self.dual_width_spin.setValue(self._params.dual_wall_width)
        self.dual_offset_spin.setValue(self._params.dual_wall_offset)

        # 更新表格
        self.layer_table.setRowCount(0)
        for layer in self._params.layers:
            self._add_layer()
            row = self.layer_table.rowCount() - 1
            self.layer_table.item(row, 0).setText(str(layer.height))
            combo = self.layer_table.cellWidget(row, 1)
            if combo and layer.extruder:
                combo.setCurrentIndex(layer.extruder.value - 1)
