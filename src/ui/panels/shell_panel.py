"""
字壳工艺参数面板

设置字壳高度、壁厚、边缘类型等核心参数。
支持直边、斜边和异形边三种边缘类型。
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QDoubleSpinBox, QSpinBox,
    QComboBox, QCheckBox, QPushButton, QFileDialog,
    QMessageBox
)
from PySide6.QtCore import Signal, QCoreApplication

from src.business.settings_manager import get_settings_manager
from src.core.types import ShellParams, EdgeType, BevelDirection, EdgeProfile
from src.core.edge_presets import EdgePresetManager, ProfileCategory
from src.ui.widgets.edge_preset_selector import EdgePresetSelector


class ShellPanel(QWidget):
    """字壳工艺参数面板"""

    params_changed = Signal(object)  # ShellParams

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = ShellParams()
        self._preset_manager = EdgePresetManager()
        self._current_profile = None
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

        # 斜边方向选择
        self.bevel_direction_combo = QComboBox()
        self.bevel_direction_combo.addItems(["上小下大", "上大下小"])
        bevel_layout.addRow("斜边方向:", self.bevel_direction_combo)

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

        # 异形边参数组
        self.custom_edge_group = QGroupBox("异形边设置")
        custom_layout = QVBoxLayout(self.custom_edge_group)
        custom_layout.setSpacing(8)

        # 预设图片选择器
        preset_label = QLabel("预设模板:")
        preset_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        custom_layout.addWidget(preset_label)

        self.preset_selector = EdgePresetSelector()
        self.preset_selector.setMinimumHeight(200)
        custom_layout.addWidget(self.preset_selector)

        # 按钮行
        btn_layout = QHBoxLayout()

        self.import_dxf_btn = QPushButton("导入DXF")
        self.import_dxf_btn.setToolTip("从DXF文件导入自定义异形边轮廓")
        btn_layout.addWidget(self.import_dxf_btn)
        btn_layout.addStretch()

        custom_layout.addLayout(btn_layout)

        # 当前轮廓信息
        info_layout = QFormLayout()
        self.profile_info_label = QLabel("未选择轮廓")
        self.profile_info_label.setStyleSheet("color: #888;")
        info_layout.addRow("当前轮廓:", self.profile_info_label)
        custom_layout.addLayout(info_layout)

        layout.addWidget(self.custom_edge_group)
        self.custom_edge_group.setVisible(False)

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
        self.bevel_direction_combo.currentIndexChanged.connect(self._emit_params)
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

        # 异形边信号
        self.preset_selector.preset_selected.connect(self._on_preset_changed)
        self.import_dxf_btn.clicked.connect(self._on_import_dxf)

    def _on_edge_type_changed(self, index):
        # 斜边(index=1)时显示斜边参数
        self.bevel_group.setVisible(index == 1)
        # 异形边(index=2)时显示异形边参数
        self.custom_edge_group.setVisible(index == 2)

        # 如果切换到异形边且没有选择预设，自动加载默认预设
        if index == 2 and self._current_profile is None:
            preset_name = self.preset_selector.get_selected_preset()
            if preset_name:
                self._on_preset_changed(preset_name)

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

        # 边缘类型
        edge_types = [EdgeType.STRAIGHT, EdgeType.BEVELED, EdgeType.CUSTOM]
        self._params.edge_type = edge_types[self.edge_type_combo.currentIndex()]

        # 斜边方向
        bevel_directions = [BevelDirection.TOP_SMALL, BevelDirection.TOP_LARGE]
        self._params.bevel_direction = bevel_directions[self.bevel_direction_combo.currentIndex()]

        # 异形边轮廓
        if self._params.edge_type == EdgeType.CUSTOM:
            self._params.edge_profile = self._current_profile
            # 使用模板中的原始宽度
            if self._current_profile:
                self._params.bevel_width = self._current_profile.original_width
        else:
            self._params.edge_profile = None

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

        # 边缘类型
        if self._params.edge_type == EdgeType.STRAIGHT:
            self.edge_type_combo.setCurrentIndex(0)
        elif self._params.edge_type == EdgeType.BEVELED:
            self.edge_type_combo.setCurrentIndex(1)
        else:
            self.edge_type_combo.setCurrentIndex(2)

        # 斜边方向
        if self._params.bevel_direction == BevelDirection.TOP_SMALL:
            self.bevel_direction_combo.setCurrentIndex(0)
        else:
            self.bevel_direction_combo.setCurrentIndex(1)

    def _on_preset_changed(self, preset_name: str):
        """预设选择变更"""
        if not preset_name:
            return

        # 加载预设（使用模板原始宽度）
        profile = self._preset_manager.get_preset_profile(preset_name)

        if profile:
            self._current_profile = profile
            self._update_profile_info()
            self._emit_params()

    def _on_import_dxf(self):
        """导入DXF文件"""
        settings = get_settings_manager()
        initial_dir = settings.get_last_open_dir() if settings else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入异形边DXF",
            initial_dir,
            "DXF文件 (*.dxf);;所有文件 (*.*)"
        )

        if not file_path:
            return

        if settings:
            settings.set_last_open_dir(str(Path(file_path).expanduser().resolve(strict=False).parent))

        try:
            from src.core.edge_profile_loader import EdgeProfileDXFLoader
            loader = EdgeProfileDXFLoader()
            profile = loader.load_from_dxf(file_path)

            self._current_profile = profile
            self._update_profile_info()
            self._emit_params()

            QMessageBox.information(
                self, "导入成功",
                f"已导入异形边轮廓: {profile.name}\n"
                f"尺寸: {profile.original_width:.1f} x {profile.original_height:.1f} mm\n"
                f"控制点: {len(profile.control_points)} 个"
            )

        except Exception as e:
            QMessageBox.warning(
                self, "导入失败",
                f"无法导入DXF文件:\n{str(e)}"
            )

    def _update_profile_info(self):
        """更新轮廓信息显示"""
        if self._current_profile:
            # Translate profile name if it's a preset
            name = self._current_profile.name
            translated_name = QCoreApplication.translate("EdgePresets", name)
            info = f"{translated_name}"
            if self._current_profile.control_points:
                info += f" ({len(self._current_profile.control_points)}{self.tr('points')})"
            self.profile_info_label.setText(info)
            self.profile_info_label.setStyleSheet("color: #58A6FF;")
        else:
            self.profile_info_label.setText(self.tr("No profile selected"))
            self.profile_info_label.setStyleSheet("color: #888;")
