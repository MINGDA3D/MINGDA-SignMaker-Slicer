"""
面板填充参数面板
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QCheckBox, QComboBox, QTabWidget
)
from PySide6.QtCore import Signal

from src.core.types import PanelParams, GridParams, BaseplateParams, FillConfig


class PanelFillPanel(QWidget):
    """面板填充参数面板"""

    params_changed = Signal(object, object, object)  # PanelParams, GridParams, BaseplateParams

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panel_params = PanelParams()
        self._grid_params = GridParams()
        self._baseplate_params = BaseplateParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 选项卡
        self.tab_widget = QTabWidget()

        # 面板填充页
        panel_tab = QWidget()
        panel_layout = QVBoxLayout(panel_tab)

        self.panel_enabled_check = QCheckBox("启用面板填充")
        panel_layout.addWidget(self.panel_enabled_check)

        panel_group = QGroupBox("填充参数")
        pg_layout = QFormLayout(panel_group)

        self.panel_spacing_spin = QDoubleSpinBox()
        self.panel_spacing_spin.setRange(0.5, 10)
        self.panel_spacing_spin.setValue(2.0)
        self.panel_spacing_spin.setSuffix(" mm")
        pg_layout.addRow("填充间距:", self.panel_spacing_spin)

        self.panel_spacing2_spin = QDoubleSpinBox()
        self.panel_spacing2_spin.setRange(0.5, 5)
        self.panel_spacing2_spin.setValue(0.9)
        self.panel_spacing2_spin.setSuffix(" mm")
        pg_layout.addRow("背面间距:", self.panel_spacing2_spin)

        self.panel_boundary_spin = QDoubleSpinBox()
        self.panel_boundary_spin.setRange(0.5, 10)
        self.panel_boundary_spin.setValue(1.4)
        self.panel_boundary_spin.setSuffix(" mm")
        pg_layout.addRow("边界距离:", self.panel_boundary_spin)

        self.panel_angle_spin = QDoubleSpinBox()
        self.panel_angle_spin.setRange(0, 90)
        self.panel_angle_spin.setValue(45)
        self.panel_angle_spin.setSuffix(" °")
        pg_layout.addRow("填充角度:", self.panel_angle_spin)

        panel_layout.addWidget(panel_group)
        panel_layout.addStretch()

        self.tab_widget.addTab(panel_tab, "面板填充")

        # 网格填充页
        grid_tab = QWidget()
        grid_layout = QVBoxLayout(grid_tab)

        self.grid_enabled_check = QCheckBox("启用网格填充")
        grid_layout.addWidget(self.grid_enabled_check)

        grid_group = QGroupBox("填充参数")
        gg_layout = QFormLayout(grid_group)

        self.grid_spacing_spin = QDoubleSpinBox()
        self.grid_spacing_spin.setRange(1, 20)
        self.grid_spacing_spin.setValue(5.0)
        self.grid_spacing_spin.setSuffix(" mm")
        gg_layout.addRow("网格间距:", self.grid_spacing_spin)

        self.grid_boundary_spin = QDoubleSpinBox()
        self.grid_boundary_spin.setRange(0.5, 10)
        self.grid_boundary_spin.setValue(3.2)
        self.grid_boundary_spin.setSuffix(" mm")
        gg_layout.addRow("边界距离:", self.grid_boundary_spin)

        grid_layout.addWidget(grid_group)
        grid_layout.addStretch()

        self.tab_widget.addTab(grid_tab, "网格填充")

        # 底板填充页
        base_tab = QWidget()
        base_layout = QVBoxLayout(base_tab)

        self.base_enabled_check = QCheckBox("启用底板填充")
        base_layout.addWidget(self.base_enabled_check)

        base_group = QGroupBox("填充参数")
        bg_layout = QFormLayout(base_group)

        self.base_spacing_spin = QDoubleSpinBox()
        self.base_spacing_spin.setRange(0.5, 5)
        self.base_spacing_spin.setValue(0.95)
        self.base_spacing_spin.setSuffix(" mm")
        bg_layout.addRow("填充间距:", self.base_spacing_spin)

        self.base_boundary_spin = QDoubleSpinBox()
        self.base_boundary_spin.setRange(0.5, 10)
        self.base_boundary_spin.setValue(1.4)
        self.base_boundary_spin.setSuffix(" mm")
        bg_layout.addRow("边界距离:", self.base_boundary_spin)

        self.base_angle_spin = QDoubleSpinBox()
        self.base_angle_spin.setRange(0, 90)
        self.base_angle_spin.setValue(45)
        self.base_angle_spin.setSuffix(" °")
        bg_layout.addRow("填充角度:", self.base_angle_spin)

        base_layout.addWidget(base_group)
        base_layout.addStretch()

        self.tab_widget.addTab(base_tab, "底板填充")

        layout.addWidget(self.tab_widget)

    def _connect_signals(self):
        self.panel_enabled_check.toggled.connect(self._emit_params)
        self.panel_spacing_spin.valueChanged.connect(self._emit_params)
        self.panel_spacing2_spin.valueChanged.connect(self._emit_params)
        self.panel_boundary_spin.valueChanged.connect(self._emit_params)
        self.panel_angle_spin.valueChanged.connect(self._emit_params)

        self.grid_enabled_check.toggled.connect(self._emit_params)
        self.grid_spacing_spin.valueChanged.connect(self._emit_params)
        self.grid_boundary_spin.valueChanged.connect(self._emit_params)

        self.base_enabled_check.toggled.connect(self._emit_params)
        self.base_spacing_spin.valueChanged.connect(self._emit_params)
        self.base_boundary_spin.valueChanged.connect(self._emit_params)
        self.base_angle_spin.valueChanged.connect(self._emit_params)

    def _emit_params(self):
        # 面板参数
        self._panel_params.enabled = self.panel_enabled_check.isChecked()
        self._panel_params.fill_config.spacing = self.panel_spacing_spin.value()
        self._panel_params.fill_config.spacing2 = self.panel_spacing2_spin.value()
        self._panel_params.fill_config.boundary_distance = self.panel_boundary_spin.value()
        self._panel_params.fill_config.angle = self.panel_angle_spin.value()

        # 网格参数
        self._grid_params.enabled = self.grid_enabled_check.isChecked()
        self._grid_params.fill_config.spacing = self.grid_spacing_spin.value()
        self._grid_params.fill_config.boundary_distance = self.grid_boundary_spin.value()

        # 底板参数
        self._baseplate_params.enabled = self.base_enabled_check.isChecked()
        self._baseplate_params.fill_config.spacing = self.base_spacing_spin.value()
        self._baseplate_params.fill_config.boundary_distance = self.base_boundary_spin.value()
        self._baseplate_params.fill_config.angle = self.base_angle_spin.value()

        self.params_changed.emit(
            self._panel_params, self._grid_params, self._baseplate_params
        )
