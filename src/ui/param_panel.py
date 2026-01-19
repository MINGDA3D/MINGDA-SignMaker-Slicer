"""
SignMaker Slicer - 参数面板组件

用于设置切片参数的面板，包含：
- 字壳工艺参数
- 换色层设置
- 台阶/V槽设置
- 其他参数分组
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QGroupBox, QFrame,
    QPushButton, QTabWidget, QFormLayout
)
from PySide6.QtCore import Qt, Signal

from src.core.types import (
    SliceParams, ShellParams, EdgeType, ExtruderType
)
from .theme import COLORS, LAYOUT


class ParamPanel(QWidget):
    """参数面板"""

    params_changed = Signal()  # 参数变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 参数
        self._params = SliceParams()

        # 初始化UI
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel("参数设置")
        title.setProperty("heading", True)
        title.setStyleSheet(f"""
            padding: 12px;
            background-color: {COLORS.bg_secondary};
            border-bottom: 1px solid {COLORS.border_default};
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(title)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        layout.addWidget(scroll)

        # 滚动内容
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        # 添加参数分组
        content_layout.addWidget(self._create_shell_group())
        content_layout.addWidget(self._create_edge_group())
        content_layout.addWidget(self._create_color_group())
        content_layout.addWidget(self._create_step_group())
        content_layout.addWidget(self._create_skirt_group())
        content_layout.addWidget(self._create_edge_wrap_group())
        content_layout.addWidget(self._create_speed_group())

        content_layout.addStretch()

        scroll.setWidget(content)

    def _create_shell_group(self) -> QGroupBox:
        """创建字壳工艺参数组"""
        group = QGroupBox("字壳工艺")
        layout = QFormLayout(group)
        layout.setSpacing(8)

        # 字壳高度
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 500)
        self.height_spin.setValue(30)
        self.height_spin.setSuffix(" mm")
        self.height_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow("字壳高度:", self.height_spin)

        # 层高
        self.layer_height_spin = QDoubleSpinBox()
        self.layer_height_spin.setRange(0.1, 1.0)
        self.layer_height_spin.setValue(0.3)
        self.layer_height_spin.setSingleStep(0.05)
        self.layer_height_spin.setSuffix(" mm")
        self.layer_height_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow("层高:", self.layer_height_spin)

        # 壁厚
        self.wall_thickness_spin = QDoubleSpinBox()
        self.wall_thickness_spin.setRange(0.4, 3.0)
        self.wall_thickness_spin.setValue(1.2)
        self.wall_thickness_spin.setSingleStep(0.1)
        self.wall_thickness_spin.setSuffix(" mm")
        self.wall_thickness_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow("壁厚:", self.wall_thickness_spin)

        # 壁数量
        self.wall_count_spin = QSpinBox()
        self.wall_count_spin.setRange(1, 5)
        self.wall_count_spin.setValue(1)
        self.wall_count_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow("壁数量:", self.wall_count_spin)

        return group

    def _create_edge_group(self) -> QGroupBox:
        """创建边缘类型参数组"""
        group = QGroupBox("边缘类型")
        layout = QFormLayout(group)
        layout.setSpacing(8)

        # 边缘类型
        self.edge_type_combo = QComboBox()
        self.edge_type_combo.addItem("直边", EdgeType.STRAIGHT)
        self.edge_type_combo.addItem("斜边", EdgeType.BEVELED)
        self.edge_type_combo.addItem("异形边", EdgeType.CUSTOM)
        self.edge_type_combo.currentIndexChanged.connect(self._on_edge_type_changed)
        layout.addRow("边缘类型:", self.edge_type_combo)

        # 斜边宽度
        self.bevel_width_spin = QDoubleSpinBox()
        self.bevel_width_spin.setRange(0, 50)
        self.bevel_width_spin.setValue(5)
        self.bevel_width_spin.setSuffix(" mm")
        self.bevel_width_spin.setEnabled(False)
        self.bevel_width_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow("斜边宽度:", self.bevel_width_spin)

        # 斜边角度
        self.bevel_angle_spin = QDoubleSpinBox()
        self.bevel_angle_spin.setRange(30, 90)
        self.bevel_angle_spin.setValue(75)
        self.bevel_angle_spin.setSuffix("°")
        self.bevel_angle_spin.setEnabled(False)
        self.bevel_angle_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow("斜边角度:", self.bevel_angle_spin)

        # 底板厚度
        self.baseplate_spin = QDoubleSpinBox()
        self.baseplate_spin.setRange(0, 50)
        self.baseplate_spin.setValue(10)
        self.baseplate_spin.setSuffix(" mm")
        self.baseplate_spin.valueChanged.connect(self._on_param_changed)
        layout.addRow("底板厚度:", self.baseplate_spin)

        return group

    def _create_color_group(self) -> QGroupBox:
        """创建换色层参数组"""
        group = QGroupBox("换色层设置")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.color_enabled = QCheckBox("启用换色层")
        self.color_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.color_enabled)

        # 换色层配置（简化版）
        form = QFormLayout()
        form.setSpacing(8)

        self.color1_height = QDoubleSpinBox()
        self.color1_height.setRange(0, 100)
        self.color1_height.setValue(10)
        self.color1_height.setSuffix(" mm")
        self.color1_height.setEnabled(False)
        form.addRow("第1色高度:", self.color1_height)

        self.color2_height = QDoubleSpinBox()
        self.color2_height.setRange(0, 100)
        self.color2_height.setValue(20)
        self.color2_height.setSuffix(" mm")
        self.color2_height.setEnabled(False)
        form.addRow("第2色高度:", self.color2_height)

        layout.addLayout(form)

        self.color_enabled.stateChanged.connect(
            lambda: self.color1_height.setEnabled(self.color_enabled.isChecked())
        )
        self.color_enabled.stateChanged.connect(
            lambda: self.color2_height.setEnabled(self.color_enabled.isChecked())
        )

        return group

    def _create_step_group(self) -> QGroupBox:
        """创建台阶/V槽参数组"""
        group = QGroupBox("台阶/V槽")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 顶部台阶
        self.top_step_enabled = QCheckBox("启用顶部台阶")
        self.top_step_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.top_step_enabled)

        form1 = QFormLayout()
        self.top_step_height = QDoubleSpinBox()
        self.top_step_height.setRange(0, 20)
        self.top_step_height.setValue(2)
        self.top_step_height.setSuffix(" mm")
        self.top_step_height.setEnabled(False)
        form1.addRow("台阶高度:", self.top_step_height)

        self.top_step_width = QDoubleSpinBox()
        self.top_step_width.setRange(0, 20)
        self.top_step_width.setValue(3)
        self.top_step_width.setSuffix(" mm")
        self.top_step_width.setEnabled(False)
        form1.addRow("台阶宽度:", self.top_step_width)
        layout.addLayout(form1)

        self.top_step_enabled.stateChanged.connect(
            lambda: self.top_step_height.setEnabled(self.top_step_enabled.isChecked())
        )
        self.top_step_enabled.stateChanged.connect(
            lambda: self.top_step_width.setEnabled(self.top_step_enabled.isChecked())
        )

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {COLORS.border_default};")
        layout.addWidget(line)

        # 底部凹槽
        self.bottom_groove_enabled = QCheckBox("启用底部凹槽")
        self.bottom_groove_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.bottom_groove_enabled)

        form2 = QFormLayout()
        self.bottom_groove_height = QDoubleSpinBox()
        self.bottom_groove_height.setRange(0, 20)
        self.bottom_groove_height.setValue(2)
        self.bottom_groove_height.setSuffix(" mm")
        self.bottom_groove_height.setEnabled(False)
        form2.addRow("凹槽高度:", self.bottom_groove_height)
        layout.addLayout(form2)

        self.bottom_groove_enabled.stateChanged.connect(
            lambda: self.bottom_groove_height.setEnabled(self.bottom_groove_enabled.isChecked())
        )

        return group

    def _create_skirt_group(self) -> QGroupBox:
        """创建防翘裙边参数组"""
        group = QGroupBox("防翘裙边")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.skirt_enabled = QCheckBox("启用防翘裙边")
        self.skirt_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.skirt_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        self.skirt_width = QDoubleSpinBox()
        self.skirt_width.setRange(1, 20)
        self.skirt_width.setValue(5)
        self.skirt_width.setSuffix(" mm")
        self.skirt_width.setEnabled(False)
        form.addRow("裙边宽度:", self.skirt_width)

        self.skirt_offset = QDoubleSpinBox()
        self.skirt_offset.setRange(0, 20)
        self.skirt_offset.setValue(3)
        self.skirt_offset.setSuffix(" mm")
        self.skirt_offset.setEnabled(False)
        form.addRow("裙边距离:", self.skirt_offset)

        layout.addLayout(form)

        self.skirt_enabled.stateChanged.connect(
            lambda: self.skirt_width.setEnabled(self.skirt_enabled.isChecked())
        )
        self.skirt_enabled.stateChanged.connect(
            lambda: self.skirt_offset.setEnabled(self.skirt_enabled.isChecked())
        )

        return group

    def _create_edge_wrap_group(self) -> QGroupBox:
        """创建包边/勾边参数组"""
        group = QGroupBox("包边勾边")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 包边设置
        self.wrap_enabled = QCheckBox("启用包边")
        self.wrap_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.wrap_enabled)

        wrap_form = QFormLayout()
        wrap_form.setSpacing(8)

        self.wrap_width = QDoubleSpinBox()
        self.wrap_width.setRange(0.5, 10)
        self.wrap_width.setValue(2.0)
        self.wrap_width.setSingleStep(0.1)
        self.wrap_width.setSuffix(" mm")
        self.wrap_width.setEnabled(False)
        wrap_form.addRow("包边宽度:", self.wrap_width)

        self.wrap_height = QDoubleSpinBox()
        self.wrap_height.setRange(0.5, 20)
        self.wrap_height.setValue(3.0)
        self.wrap_height.setSingleStep(0.5)
        self.wrap_height.setSuffix(" mm")
        self.wrap_height.setEnabled(False)
        wrap_form.addRow("包边高度:", self.wrap_height)

        layout.addLayout(wrap_form)

        self.wrap_enabled.stateChanged.connect(
            lambda: self.wrap_width.setEnabled(self.wrap_enabled.isChecked())
        )
        self.wrap_enabled.stateChanged.connect(
            lambda: self.wrap_height.setEnabled(self.wrap_enabled.isChecked())
        )

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {COLORS.border_default};")
        layout.addWidget(line)

        # 勾边设置
        self.outline_enabled = QCheckBox("启用勾边")
        self.outline_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.outline_enabled)

        outline_form = QFormLayout()
        outline_form.setSpacing(8)

        self.outline_width = QDoubleSpinBox()
        self.outline_width.setRange(0.3, 5)
        self.outline_width.setValue(1.0)
        self.outline_width.setSingleStep(0.1)
        self.outline_width.setSuffix(" mm")
        self.outline_width.setEnabled(False)
        outline_form.addRow("勾边宽度:", self.outline_width)

        self.outline_offset = QDoubleSpinBox()
        self.outline_offset.setRange(-5, 5)
        self.outline_offset.setValue(0.0)
        self.outline_offset.setSingleStep(0.1)
        self.outline_offset.setSuffix(" mm")
        self.outline_offset.setEnabled(False)
        outline_form.addRow("勾边偏移:", self.outline_offset)

        layout.addLayout(outline_form)

        self.outline_enabled.stateChanged.connect(
            lambda: self.outline_width.setEnabled(self.outline_enabled.isChecked())
        )
        self.outline_enabled.stateChanged.connect(
            lambda: self.outline_offset.setEnabled(self.outline_enabled.isChecked())
        )

        return group

    def _create_speed_group(self) -> QGroupBox:
        """创建速度参数组"""
        group = QGroupBox("速度设置")
        layout = QFormLayout(group)
        layout.setSpacing(8)

        # 打印速度
        self.print_speed = QSpinBox()
        self.print_speed.setRange(10, 200)
        self.print_speed.setValue(50)
        self.print_speed.setSuffix(" mm/s")
        self.print_speed.valueChanged.connect(self._on_param_changed)
        layout.addRow("打印速度:", self.print_speed)

        # 空走速度
        self.travel_speed = QSpinBox()
        self.travel_speed.setRange(50, 300)
        self.travel_speed.setValue(150)
        self.travel_speed.setSuffix(" mm/s")
        self.travel_speed.valueChanged.connect(self._on_param_changed)
        layout.addRow("空走速度:", self.travel_speed)

        # 首层速度
        self.first_layer_speed = QSpinBox()
        self.first_layer_speed.setRange(5, 50)
        self.first_layer_speed.setValue(20)
        self.first_layer_speed.setSuffix(" mm/s")
        self.first_layer_speed.valueChanged.connect(self._on_param_changed)
        layout.addRow("首层速度:", self.first_layer_speed)

        return group

    def _on_edge_type_changed(self, index: int):
        """边缘类型变化"""
        edge_type = self.edge_type_combo.currentData()
        is_beveled = edge_type == EdgeType.BEVELED

        self.bevel_width_spin.setEnabled(is_beveled)
        self.bevel_angle_spin.setEnabled(is_beveled)

        self._on_param_changed()

    def _on_param_changed(self):
        """参数变化处理"""
        self._update_params()
        self.params_changed.emit()

    def _update_params(self):
        """更新内部参数"""
        # 字壳参数
        self._params.shell.height = self.height_spin.value()
        self._params.shell.layer_height = self.layer_height_spin.value()
        self._params.shell.wall_thickness = self.wall_thickness_spin.value()
        self._params.shell.wall_count = self.wall_count_spin.value()

        # 边缘参数
        self._params.shell.edge_type = self.edge_type_combo.currentData()
        self._params.shell.bevel_width = self.bevel_width_spin.value()
        self._params.shell.bevel_angle = self.bevel_angle_spin.value()
        self._params.shell.baseplate_thickness = self.baseplate_spin.value()

        # 换色层参数
        self._params.color.enabled = self.color_enabled.isChecked()

        # 台阶参数
        self._params.step.top_step_enabled = self.top_step_enabled.isChecked()
        self._params.step.top_step_height = self.top_step_height.value()
        self._params.step.top_step_width = self.top_step_width.value()
        self._params.step.bottom_groove_enabled = self.bottom_groove_enabled.isChecked()
        self._params.step.bottom_groove_height = self.bottom_groove_height.value()

        # 裙边参数
        self._params.skirt.enabled = self.skirt_enabled.isChecked()
        self._params.skirt.width = self.skirt_width.value()
        self._params.skirt.offset = self.skirt_offset.value()

        # 包边勾边参数
        self._params.edge_wrap.wrap_enabled = self.wrap_enabled.isChecked()
        self._params.edge_wrap.wrap_width = self.wrap_width.value()
        self._params.edge_wrap.wrap_height = self.wrap_height.value()
        self._params.edge_wrap.outline_enabled = self.outline_enabled.isChecked()
        self._params.edge_wrap.outline_width = self.outline_width.value()
        self._params.edge_wrap.outline_offset = self.outline_offset.value()

        # 速度参数
        self._params.speed.print_speed = self.print_speed.value()
        self._params.speed.travel_speed = self.travel_speed.value()
        self._params.speed.first_layer_speed = self.first_layer_speed.value()

        # 同步到G-code参数
        self._params.gcode.print_speed = self.print_speed.value()
        self._params.gcode.travel_speed = self.travel_speed.value()
        self._params.gcode.first_layer_speed = self.first_layer_speed.value()

    def get_params(self) -> SliceParams:
        """获取当前参数"""
        self._update_params()
        return self._params

    def set_params(self, params: SliceParams):
        """设置参数"""
        self._params = params

        # 更新UI
        self.height_spin.setValue(params.shell.height)
        self.layer_height_spin.setValue(params.shell.layer_height)
        self.wall_thickness_spin.setValue(params.shell.wall_thickness)
        self.wall_count_spin.setValue(params.shell.wall_count)

        # 边缘参数
        edge_index = self.edge_type_combo.findData(params.shell.edge_type)
        if edge_index >= 0:
            self.edge_type_combo.setCurrentIndex(edge_index)
        self.bevel_width_spin.setValue(params.shell.bevel_width)
        self.bevel_angle_spin.setValue(params.shell.bevel_angle)
        self.baseplate_spin.setValue(params.shell.baseplate_thickness)

        # 速度参数
        self.print_speed.setValue(int(params.speed.print_speed))
        self.travel_speed.setValue(int(params.speed.travel_speed))
        self.first_layer_speed.setValue(int(params.speed.first_layer_speed))

        # 包边勾边参数
        self.wrap_enabled.setChecked(params.edge_wrap.wrap_enabled)
        self.wrap_width.setValue(params.edge_wrap.wrap_width)
        self.wrap_height.setValue(params.edge_wrap.wrap_height)
        self.outline_enabled.setChecked(params.edge_wrap.outline_enabled)
        self.outline_width.setValue(params.edge_wrap.outline_width)
        self.outline_offset.setValue(params.edge_wrap.outline_offset)
