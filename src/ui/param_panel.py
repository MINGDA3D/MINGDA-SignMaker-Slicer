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
    QPushButton, QTabWidget, QFormLayout, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal

from src.core.types import (
    SliceParams, ShellParams, EdgeType, ExtruderType, EdgeDirection, BevelDirection,
    ConnectedParams, EdgeProfile, TopFaceParams
)
from src.core.edge_presets import EdgePresetManager, ProfileCategory
from src.ui.widgets.edge_preset_selector import EdgePresetSelector
from .theme import COLORS, LAYOUT


class ParamPanel(QWidget):
    """参数面板"""

    params_changed = Signal()  # 参数变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 参数
        self._params = SliceParams()

        # 异形边预设管理器
        self._preset_manager = EdgePresetManager()
        self._current_profile = None

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
        content_layout.addWidget(self._create_bottom_face_group())  # 底面封闭
        content_layout.addWidget(self._create_top_face_group())  # 顶面封闭
        content_layout.addWidget(self._create_color_group())
        content_layout.addWidget(self._create_step_group())
        content_layout.addWidget(self._create_skirt_group())
        content_layout.addWidget(self._create_connected_group())
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
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 边缘类型选择
        type_form = QFormLayout()
        type_form.setSpacing(8)

        self.edge_type_combo = QComboBox()
        self.edge_type_combo.addItem("直边", EdgeType.STRAIGHT)
        self.edge_type_combo.addItem("斜边", EdgeType.BEVELED)
        self.edge_type_combo.addItem("异形边", EdgeType.CUSTOM)
        self.edge_type_combo.currentIndexChanged.connect(self._on_edge_type_changed)
        type_form.addRow("边缘类型:", self.edge_type_combo)

        layout.addLayout(type_form)

        # ===== 斜边参数容器 =====
        self.bevel_params_widget = QWidget()
        bevel_layout = QFormLayout(self.bevel_params_widget)
        bevel_layout.setContentsMargins(0, 8, 0, 0)
        bevel_layout.setSpacing(8)

        # 斜边方向
        self.bevel_direction_combo = QComboBox()
        self.bevel_direction_combo.addItem("上小下大", BevelDirection.TOP_SMALL)
        self.bevel_direction_combo.addItem("上大下小", BevelDirection.TOP_LARGE)
        self.bevel_direction_combo.currentIndexChanged.connect(self._on_param_changed)
        bevel_layout.addRow("斜边方向:", self.bevel_direction_combo)

        # 斜边宽度
        self.bevel_width_spin = QDoubleSpinBox()
        self.bevel_width_spin.setRange(0, 50)
        self.bevel_width_spin.setValue(5)
        self.bevel_width_spin.setSuffix(" mm")
        self.bevel_width_spin.valueChanged.connect(self._on_param_changed)
        bevel_layout.addRow("斜边宽度:", self.bevel_width_spin)

        # 底板厚度
        self.baseplate_spin = QDoubleSpinBox()
        self.baseplate_spin.setRange(0, 50)
        self.baseplate_spin.setValue(10)
        self.baseplate_spin.setSuffix(" mm")
        self.baseplate_spin.valueChanged.connect(self._on_param_changed)
        bevel_layout.addRow("底板厚度:", self.baseplate_spin)

        # 面板厚度
        self.panel_thickness_spin = QDoubleSpinBox()
        self.panel_thickness_spin.setRange(0, 20)
        self.panel_thickness_spin.setValue(3)
        self.panel_thickness_spin.setSuffix(" mm")
        self.panel_thickness_spin.valueChanged.connect(self._on_param_changed)
        bevel_layout.addRow("面板厚度:", self.panel_thickness_spin)

        layout.addWidget(self.bevel_params_widget)
        self.bevel_params_widget.setVisible(False)

        # ===== 异形边参数容器 =====
        self.custom_edge_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_edge_widget)
        custom_layout.setContentsMargins(0, 8, 0, 0)
        custom_layout.setSpacing(8)

        # 预设模板标签
        preset_label = QLabel("预设模板:")
        preset_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        custom_layout.addWidget(preset_label)

        # 预设图片选择器
        self.preset_selector = EdgePresetSelector()
        self.preset_selector.setMinimumHeight(200)
        self.preset_selector.preset_selected.connect(self._on_preset_changed)
        custom_layout.addWidget(self.preset_selector)

        # 导入DXF按钮
        btn_layout = QHBoxLayout()
        self.import_dxf_btn = QPushButton("导入DXF...")
        self.import_dxf_btn.setToolTip("从DXF文件导入自定义异形边轮廓")
        self.import_dxf_btn.clicked.connect(self._on_import_dxf)
        btn_layout.addWidget(self.import_dxf_btn)
        btn_layout.addStretch()
        custom_layout.addLayout(btn_layout)

        # 当前轮廓信息
        info_layout = QFormLayout()
        self.profile_info_label = QLabel("未选择轮廓")
        self.profile_info_label.setStyleSheet("color: #888;")
        info_layout.addRow("当前轮廓:", self.profile_info_label)
        custom_layout.addLayout(info_layout)

        layout.addWidget(self.custom_edge_widget)
        self.custom_edge_widget.setVisible(False)

        return group

    def _create_bottom_face_group(self) -> QGroupBox:
        """创建底面封闭参数组"""
        group = QGroupBox("底面封闭")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.bottom_face_enabled = QCheckBox("启用底面封闭")
        self.bottom_face_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.bottom_face_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        # 底面厚度
        self.bottom_face_thickness = QDoubleSpinBox()
        self.bottom_face_thickness.setRange(0.3, 10.0)
        self.bottom_face_thickness.setValue(1.0)
        self.bottom_face_thickness.setSingleStep(0.1)
        self.bottom_face_thickness.setSuffix(" mm")
        self.bottom_face_thickness.setEnabled(False)
        self.bottom_face_thickness.valueChanged.connect(self._on_param_changed)
        form.addRow("底面厚度:", self.bottom_face_thickness)

        layout.addLayout(form)

        # 启用/禁用控件联动
        self.bottom_face_enabled.stateChanged.connect(
            lambda: self.bottom_face_thickness.setEnabled(self.bottom_face_enabled.isChecked())
        )

        return group

    def _toggle_bottom_face_controls(self, enabled: bool):
        """切换底面封闭控件的启用状态"""
        self.bottom_face_thickness.setEnabled(enabled)

    def _create_top_face_group(self) -> QGroupBox:
        """创建顶面封闭参数组"""
        group = QGroupBox("顶面封闭")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.top_face_enabled = QCheckBox("启用顶面封闭")
        self.top_face_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.top_face_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        # 顶面厚度
        self.top_face_thickness = QDoubleSpinBox()
        self.top_face_thickness.setRange(0.3, 10.0)
        self.top_face_thickness.setValue(1.0)
        self.top_face_thickness.setSingleStep(0.1)
        self.top_face_thickness.setSuffix(" mm")
        self.top_face_thickness.setEnabled(False)
        self.top_face_thickness.valueChanged.connect(self._on_param_changed)
        form.addRow("顶面厚度:", self.top_face_thickness)

        layout.addLayout(form)

        # 启用/禁用控件联动
        self.top_face_enabled.stateChanged.connect(
            lambda: self.top_face_thickness.setEnabled(self.top_face_enabled.isChecked())
        )

        return group

    def _toggle_top_face_controls(self, enabled: bool):
        """切换顶面封闭控件的启用状态"""
        self.top_face_thickness.setEnabled(enabled)

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

        # ===== 面板台阶（顶部）=====
        self.panel_step_enabled = QCheckBox("启用面板台阶（顶部）")
        self.panel_step_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.panel_step_enabled)

        form1 = QFormLayout()
        self.panel_step_height = QDoubleSpinBox()
        self.panel_step_height.setRange(0.3, 30)
        self.panel_step_height.setValue(3)
        self.panel_step_height.setSuffix(" mm")
        self.panel_step_height.setEnabled(False)
        self.panel_step_height.valueChanged.connect(self._on_param_changed)
        form1.addRow("台阶高度:", self.panel_step_height)

        self.panel_step_width = QDoubleSpinBox()
        self.panel_step_width.setRange(0.5, 20)
        self.panel_step_width.setValue(3)
        self.panel_step_width.setSuffix(" mm")
        self.panel_step_width.setEnabled(False)
        self.panel_step_width.valueChanged.connect(self._on_param_changed)
        form1.addRow("台阶宽度:", self.panel_step_width)

        self.panel_step_v_groove = QCheckBox("V型槽")
        self.panel_step_v_groove.setEnabled(False)
        self.panel_step_v_groove.stateChanged.connect(self._on_param_changed)
        form1.addRow("", self.panel_step_v_groove)

        layout.addLayout(form1)

        self.panel_step_enabled.stateChanged.connect(
            lambda: self._toggle_panel_step_controls(self.panel_step_enabled.isChecked())
        )

        # 分隔线
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet(f"background-color: {COLORS.border_default};")
        layout.addWidget(line1)

        # ===== 底板台阶（底部）=====
        self.baseplate_step_enabled = QCheckBox("启用底板台阶（底部）")
        self.baseplate_step_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.baseplate_step_enabled)

        form2 = QFormLayout()
        self.baseplate_step_height = QDoubleSpinBox()
        self.baseplate_step_height.setRange(0.3, 30)
        self.baseplate_step_height.setValue(3)
        self.baseplate_step_height.setSuffix(" mm")
        self.baseplate_step_height.setEnabled(False)
        self.baseplate_step_height.valueChanged.connect(self._on_param_changed)
        form2.addRow("台阶高度:", self.baseplate_step_height)

        self.baseplate_step_width = QDoubleSpinBox()
        self.baseplate_step_width.setRange(0.5, 20)
        self.baseplate_step_width.setValue(3)
        self.baseplate_step_width.setSuffix(" mm")
        self.baseplate_step_width.setEnabled(False)
        self.baseplate_step_width.valueChanged.connect(self._on_param_changed)
        form2.addRow("台阶宽度:", self.baseplate_step_width)

        self.baseplate_step_v_groove = QCheckBox("V型槽")
        self.baseplate_step_v_groove.setEnabled(False)
        self.baseplate_step_v_groove.stateChanged.connect(self._on_param_changed)
        form2.addRow("", self.baseplate_step_v_groove)

        layout.addLayout(form2)

        self.baseplate_step_enabled.stateChanged.connect(
            lambda: self._toggle_baseplate_step_controls(self.baseplate_step_enabled.isChecked())
        )

        # 兼容旧变量（避免其他代码报错）
        self.top_step_enabled = self.panel_step_enabled
        self.top_step_height = self.panel_step_height
        self.top_step_width = self.panel_step_width
        self.bottom_groove_enabled = self.baseplate_step_enabled
        self.bottom_groove_height = self.baseplate_step_height

        return group

    def _toggle_panel_step_controls(self, enabled: bool):
        """切换面板台阶控件的启用状态"""
        self.panel_step_height.setEnabled(enabled)
        self.panel_step_width.setEnabled(enabled)
        self.panel_step_v_groove.setEnabled(enabled)

    def _toggle_baseplate_step_controls(self, enabled: bool):
        """切换底板台阶控件的启用状态"""
        self.baseplate_step_height.setEnabled(enabled)
        self.baseplate_step_width.setEnabled(enabled)
        self.baseplate_step_v_groove.setEnabled(enabled)

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
        self.skirt_width.valueChanged.connect(self._on_param_changed)
        form.addRow("裙边宽度:", self.skirt_width)

        self.skirt_height = QDoubleSpinBox()
        self.skirt_height.setRange(0.2, 10)
        self.skirt_height.setValue(0.3)
        self.skirt_height.setSingleStep(0.1)
        self.skirt_height.setSuffix(" mm")
        self.skirt_height.setEnabled(False)
        self.skirt_height.valueChanged.connect(self._on_param_changed)
        form.addRow("裙边高度:", self.skirt_height)

        self.skirt_interval = QDoubleSpinBox()
        self.skirt_interval.setRange(5, 50)
        self.skirt_interval.setValue(10)
        self.skirt_interval.setSuffix(" mm")
        self.skirt_interval.setEnabled(False)
        self.skirt_interval.valueChanged.connect(self._on_param_changed)
        form.addRow("梯形间距:", self.skirt_interval)

        self.skirt_offset = QDoubleSpinBox()
        self.skirt_offset.setRange(0, 20)
        self.skirt_offset.setValue(0)
        self.skirt_offset.setSuffix(" mm")
        self.skirt_offset.setEnabled(False)
        self.skirt_offset.valueChanged.connect(self._on_param_changed)
        form.addRow("裙边距离:", self.skirt_offset)

        layout.addLayout(form)

        self.skirt_enabled.stateChanged.connect(
            lambda: self._toggle_skirt_controls(self.skirt_enabled.isChecked())
        )

        return group

    def _toggle_skirt_controls(self, enabled: bool):
        """切换裙边控件的启用状态"""
        self.skirt_width.setEnabled(enabled)
        self.skirt_height.setEnabled(enabled)
        self.skirt_interval.setEnabled(enabled)
        self.skirt_offset.setEnabled(enabled)

    def _create_connected_group(self) -> QGroupBox:
        """创建连襟字参数组"""
        group = QGroupBox("连襟字")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 启用开关
        self.connected_enabled = QCheckBox("启用连襟字")
        self.connected_enabled.stateChanged.connect(self._on_param_changed)
        layout.addWidget(self.connected_enabled)

        form = QFormLayout()
        form.setSpacing(8)

        # 连襟类型
        self.connected_type = QComboBox()
        self.connected_type.addItem("三角形连襟", "triangle")
        self.connected_type.addItem("菱形连襟", "diamond")
        self.connected_type.setEnabled(False)
        self.connected_type.currentIndexChanged.connect(self._on_param_changed)
        form.addRow("连襟类型:", self.connected_type)

        # 自动检测
        self.connected_auto_detect = QCheckBox("自动检测连接点")
        self.connected_auto_detect.setChecked(True)
        self.connected_auto_detect.setEnabled(False)
        self.connected_auto_detect.stateChanged.connect(self._on_param_changed)
        form.addRow("", self.connected_auto_detect)

        # 连襟宽度
        self.connected_width = QDoubleSpinBox()
        self.connected_width.setRange(1, 50)
        self.connected_width.setValue(15)
        self.connected_width.setSuffix(" mm")
        self.connected_width.setEnabled(False)
        self.connected_width.valueChanged.connect(self._on_param_changed)
        form.addRow("连襟宽度:", self.connected_width)

        # 斜边高度
        self.connected_height = QDoubleSpinBox()
        self.connected_height.setRange(1, 20)
        self.connected_height.setValue(5)
        self.connected_height.setSuffix(" mm")
        self.connected_height.setEnabled(False)
        self.connected_height.valueChanged.connect(self._on_param_changed)
        form.addRow("斜边高度:", self.connected_height)

        # 底座高度
        self.connected_base_height = QDoubleSpinBox()
        self.connected_base_height.setRange(1, 20)
        self.connected_base_height.setValue(5)
        self.connected_base_height.setSuffix(" mm")
        self.connected_base_height.setEnabled(False)
        self.connected_base_height.valueChanged.connect(self._on_param_changed)
        form.addRow("底座高度:", self.connected_base_height)

        # 支撑偏移
        self.connected_support_offset = QDoubleSpinBox()
        self.connected_support_offset.setRange(0, 10)
        self.connected_support_offset.setValue(2.5)
        self.connected_support_offset.setSuffix(" mm")
        self.connected_support_offset.setEnabled(False)
        self.connected_support_offset.valueChanged.connect(self._on_param_changed)
        form.addRow("支撑偏移:", self.connected_support_offset)

        layout.addLayout(form)

        self.connected_enabled.stateChanged.connect(
            lambda: self._toggle_connected_controls(self.connected_enabled.isChecked())
        )

        return group

    def _toggle_connected_controls(self, enabled: bool):
        """切换连襟字控件的启用状态"""
        self.connected_type.setEnabled(enabled)
        self.connected_auto_detect.setEnabled(enabled)
        self.connected_width.setEnabled(enabled)
        self.connected_height.setEnabled(enabled)
        self.connected_base_height.setEnabled(enabled)
        self.connected_support_offset.setEnabled(enabled)

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

        # 包边方向单选按钮
        wrap_dir_layout = QHBoxLayout()
        self.wrap_dir_inner = QRadioButton("内部")
        self.wrap_dir_outer = QRadioButton("外部")
        self.wrap_dir_inner.setChecked(True)  # 默认内部
        self.wrap_dir_inner.setEnabled(False)
        self.wrap_dir_outer.setEnabled(False)
        self.wrap_dir_group = QButtonGroup(self)
        self.wrap_dir_group.addButton(self.wrap_dir_inner, 0)
        self.wrap_dir_group.addButton(self.wrap_dir_outer, 1)
        self.wrap_dir_group.buttonClicked.connect(self._on_param_changed)
        wrap_dir_layout.addWidget(self.wrap_dir_inner)
        wrap_dir_layout.addWidget(self.wrap_dir_outer)
        wrap_dir_layout.addStretch()
        wrap_form.addRow("包边方向:", wrap_dir_layout)

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
        self.wrap_enabled.stateChanged.connect(
            lambda: self.wrap_dir_inner.setEnabled(self.wrap_enabled.isChecked())
        )
        self.wrap_enabled.stateChanged.connect(
            lambda: self.wrap_dir_outer.setEnabled(self.wrap_enabled.isChecked())
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

        # 勾边方向单选按钮
        outline_dir_layout = QHBoxLayout()
        self.outline_dir_inner = QRadioButton("内部")
        self.outline_dir_outer = QRadioButton("外部")
        self.outline_dir_inner.setChecked(True)  # 默认内部
        self.outline_dir_inner.setEnabled(False)
        self.outline_dir_outer.setEnabled(False)
        self.outline_dir_group = QButtonGroup(self)
        self.outline_dir_group.addButton(self.outline_dir_inner, 0)
        self.outline_dir_group.addButton(self.outline_dir_outer, 1)
        self.outline_dir_group.buttonClicked.connect(self._on_param_changed)
        outline_dir_layout.addWidget(self.outline_dir_inner)
        outline_dir_layout.addWidget(self.outline_dir_outer)
        outline_dir_layout.addStretch()
        outline_form.addRow("勾边方向:", outline_dir_layout)

        self.outline_width = QDoubleSpinBox()
        self.outline_width.setRange(0.3, 5)
        self.outline_width.setValue(1.0)
        self.outline_width.setSingleStep(0.1)
        self.outline_width.setSuffix(" mm")
        self.outline_width.setEnabled(False)
        outline_form.addRow("勾边宽度:", self.outline_width)

        self.outline_height = QDoubleSpinBox()
        self.outline_height.setRange(0.3, 10)
        self.outline_height.setValue(1.0)
        self.outline_height.setSingleStep(0.1)
        self.outline_height.setSuffix(" mm")
        self.outline_height.setEnabled(False)
        outline_form.addRow("勾边高度:", self.outline_height)

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
            lambda: self.outline_height.setEnabled(self.outline_enabled.isChecked())
        )
        self.outline_enabled.stateChanged.connect(
            lambda: self.outline_offset.setEnabled(self.outline_enabled.isChecked())
        )
        self.outline_enabled.stateChanged.connect(
            lambda: self.outline_dir_inner.setEnabled(self.outline_enabled.isChecked())
        )
        self.outline_enabled.stateChanged.connect(
            lambda: self.outline_dir_outer.setEnabled(self.outline_enabled.isChecked())
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

        # 显示/隐藏对应的参数组
        self.bevel_params_widget.setVisible(edge_type == EdgeType.BEVELED)
        self.custom_edge_widget.setVisible(edge_type == EdgeType.CUSTOM)

        # 如果切换到异形边且没有选择预设，自动加载默认预设
        if edge_type == EdgeType.CUSTOM and self._current_profile is None:
            preset_name = self.preset_selector.get_selected_preset()
            if preset_name:
                self._on_preset_changed(preset_name)

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
        self._params.shell.bevel_direction = self.bevel_direction_combo.currentData()
        self._params.shell.baseplate_thickness = self.baseplate_spin.value()
        self._params.shell.panel_thickness = self.panel_thickness_spin.value()

        # 根据边缘类型设置轮廓
        if self._params.shell.edge_type == EdgeType.CUSTOM:
            # 异形边：使用模板中的原始宽度
            self._params.shell.edge_profile = self._current_profile
            if self._current_profile:
                self._params.shell.bevel_width = self._current_profile.original_width
        else:
            # 直边或斜边
            self._params.shell.bevel_width = self.bevel_width_spin.value()
            self._params.shell.edge_profile = None

        # 换色层参数
        self._params.color.enabled = self.color_enabled.isChecked()

        # 台阶参数
        # 面板台阶（顶部）
        self._params.step.panel_step_enabled = self.panel_step_enabled.isChecked()
        self._params.step.panel_step_height = self.panel_step_height.value()
        self._params.step.panel_step_width = self.panel_step_width.value()
        self._params.step.panel_step_is_v_groove = self.panel_step_v_groove.isChecked()

        # 底板台阶（底部）
        self._params.step.baseplate_step_enabled = self.baseplate_step_enabled.isChecked()
        self._params.step.baseplate_step_height = self.baseplate_step_height.value()
        self._params.step.baseplate_step_width = self.baseplate_step_width.value()
        self._params.step.baseplate_step_is_v_groove = self.baseplate_step_v_groove.isChecked()

        # 兼容旧参数
        self._params.step.top_step_enabled = self.panel_step_enabled.isChecked()
        self._params.step.top_step_height = self.panel_step_height.value()
        self._params.step.top_step_width = self.panel_step_width.value()
        self._params.step.bottom_groove_enabled = self.baseplate_step_enabled.isChecked()
        self._params.step.bottom_groove_height = self.baseplate_step_height.value()
        self._params.step.bottom_groove_depth = self.baseplate_step_width.value()

        # 启用台阶总开关
        self._params.step.enabled = (
            self._params.step.panel_step_enabled or
            self._params.step.baseplate_step_enabled or
            len(self._params.step.steps) > 0
        )

        # 裙边参数
        self._params.skirt.enabled = self.skirt_enabled.isChecked()
        self._params.skirt.width = self.skirt_width.value()
        self._params.skirt.height = self.skirt_height.value()
        self._params.skirt.interval = self.skirt_interval.value()
        self._params.skirt.offset = self.skirt_offset.value()

        # 连襟字参数
        self._params.connected.enabled = self.connected_enabled.isChecked()
        self._params.connected.type = self.connected_type.currentData()
        self._params.connected.auto_detect = self.connected_auto_detect.isChecked()
        self._params.connected.width = self.connected_width.value()
        self._params.connected.height = self.connected_height.value()
        self._params.connected.base_height = self.connected_base_height.value()
        self._params.connected.support_offset = self.connected_support_offset.value()

        # 包边勾边参数
        self._params.edge_wrap.wrap_enabled = self.wrap_enabled.isChecked()
        self._params.edge_wrap.wrap_width = self.wrap_width.value()
        self._params.edge_wrap.wrap_height = self.wrap_height.value()
        self._params.edge_wrap.wrap_direction = (
            EdgeDirection.INNER if self.wrap_dir_inner.isChecked()
            else EdgeDirection.OUTER
        )
        self._params.edge_wrap.outline_enabled = self.outline_enabled.isChecked()
        self._params.edge_wrap.outline_width = self.outline_width.value()
        self._params.edge_wrap.outline_height = self.outline_height.value()
        self._params.edge_wrap.outline_offset = self.outline_offset.value()
        self._params.edge_wrap.outline_direction = (
            EdgeDirection.INNER if self.outline_dir_inner.isChecked()
            else EdgeDirection.OUTER
        )

        # 速度参数
        self._params.speed.print_speed = self.print_speed.value()
        self._params.speed.travel_speed = self.travel_speed.value()
        self._params.speed.first_layer_speed = self.first_layer_speed.value()

        # 同步到G-code参数
        self._params.gcode.print_speed = self.print_speed.value()
        self._params.gcode.travel_speed = self.travel_speed.value()
        self._params.gcode.first_layer_speed = self.first_layer_speed.value()

        # 底面封闭参数
        self._params.bottom_face.enabled = self.bottom_face_enabled.isChecked()
        self._params.bottom_face.thickness = self.bottom_face_thickness.value()

        # 顶面封闭参数
        self._params.top_face.enabled = self.top_face_enabled.isChecked()
        self._params.top_face.thickness = self.top_face_thickness.value()

    def get_params(self) -> SliceParams:
        """获取当前参数"""
        self._update_params()
        return self._params

    def set_params(self, params: SliceParams):
        """设置参数"""
        self._params = params

        # 阻止各控件信号，防止设置值时触发 _on_param_changed
        widgets = [
            self.height_spin, self.layer_height_spin, self.wall_thickness_spin,
            self.wall_count_spin, self.edge_type_combo, self.bevel_direction_combo,
            self.bevel_width_spin, self.baseplate_spin, self.panel_thickness_spin,
            self.print_speed, self.travel_speed, self.first_layer_speed,
            self.skirt_enabled, self.skirt_width, self.skirt_height,
            self.skirt_interval, self.skirt_offset,
            self.connected_enabled, self.connected_type, self.connected_auto_detect,
            self.connected_width, self.connected_height, self.connected_base_height,
            self.connected_support_offset,
            self.wrap_enabled, self.wrap_width, self.wrap_height,
            self.wrap_dir_inner, self.wrap_dir_outer,
            self.outline_enabled, self.outline_width, self.outline_height,
            self.outline_offset, self.outline_dir_inner, self.outline_dir_outer,
            self.color_enabled, self.color1_height, self.color2_height,
            self.panel_step_enabled, self.panel_step_height, self.panel_step_width,
            self.panel_step_v_groove, self.baseplate_step_enabled,
            self.baseplate_step_height, self.baseplate_step_width, self.baseplate_step_v_groove,
            # 底面封闭控件
            self.bottom_face_enabled, self.bottom_face_thickness,
            # 顶面封闭控件
            self.top_face_enabled, self.top_face_thickness
        ]
        for w in widgets:
            w.blockSignals(True)

        # 更新UI
        self.height_spin.setValue(params.shell.height)
        self.layer_height_spin.setValue(params.shell.layer_height)
        self.wall_thickness_spin.setValue(params.shell.wall_thickness)
        self.wall_count_spin.setValue(params.shell.wall_count)

        # 边缘参数
        edge_index = self.edge_type_combo.findData(params.shell.edge_type)
        if edge_index >= 0:
            self.edge_type_combo.setCurrentIndex(edge_index)
        bevel_dir_index = self.bevel_direction_combo.findData(params.shell.bevel_direction)
        if bevel_dir_index >= 0:
            self.bevel_direction_combo.setCurrentIndex(bevel_dir_index)
        self.bevel_width_spin.setValue(params.shell.bevel_width)
        self.baseplate_spin.setValue(params.shell.baseplate_thickness)
        self.panel_thickness_spin.setValue(params.shell.panel_thickness)

        # 速度参数
        self.print_speed.setValue(int(params.speed.print_speed))
        self.travel_speed.setValue(int(params.speed.travel_speed))
        self.first_layer_speed.setValue(int(params.speed.first_layer_speed))

        # 裙边参数
        self.skirt_width.setValue(params.skirt.width)
        self.skirt_height.setValue(params.skirt.height)
        self.skirt_interval.setValue(params.skirt.interval)
        self.skirt_offset.setValue(params.skirt.offset)
        self.skirt_enabled.setChecked(params.skirt.enabled)

        # 连襟字参数
        connected_type_index = self.connected_type.findData(params.connected.type)
        if connected_type_index >= 0:
            self.connected_type.setCurrentIndex(connected_type_index)
        self.connected_auto_detect.setChecked(params.connected.auto_detect)
        self.connected_width.setValue(params.connected.width)
        self.connected_height.setValue(params.connected.height)
        self.connected_base_height.setValue(params.connected.base_height)
        self.connected_support_offset.setValue(params.connected.support_offset)
        self.connected_enabled.setChecked(params.connected.enabled)

        # 包边勾边参数
        self.wrap_enabled.setChecked(params.edge_wrap.wrap_enabled)
        self.wrap_width.setValue(params.edge_wrap.wrap_width)
        self.wrap_height.setValue(params.edge_wrap.wrap_height)
        if params.edge_wrap.wrap_direction == EdgeDirection.INNER:
            self.wrap_dir_inner.setChecked(True)
        else:
            self.wrap_dir_outer.setChecked(True)
        self.outline_enabled.setChecked(params.edge_wrap.outline_enabled)
        self.outline_width.setValue(params.edge_wrap.outline_width)
        self.outline_height.setValue(params.edge_wrap.outline_height)
        self.outline_offset.setValue(params.edge_wrap.outline_offset)
        if params.edge_wrap.outline_direction == EdgeDirection.INNER:
            self.outline_dir_inner.setChecked(True)
        else:
            self.outline_dir_outer.setChecked(True)

        # 底面封闭参数
        self.bottom_face_enabled.setChecked(params.bottom_face.enabled)
        self.bottom_face_thickness.setValue(params.bottom_face.thickness)

        # 顶面封闭参数
        self.top_face_enabled.setChecked(params.top_face.enabled)
        self.top_face_thickness.setValue(params.top_face.thickness)

        # 恢复信号
        for w in widgets:
            w.blockSignals(False)

        # 手动更新控件的启用状态
        self._toggle_skirt_controls(params.skirt.enabled)
        self._toggle_connected_controls(params.connected.enabled)
        self._toggle_bottom_face_controls(params.bottom_face.enabled)
        self._toggle_top_face_controls(params.top_face.enabled)

    # ===== 异形边相关方法 =====

    def _on_preset_changed(self, preset_name: str):
        """预设选择变更"""
        if not preset_name:
            return

        # 加载预设（使用模板原始宽度）
        profile = self._preset_manager.get_preset_profile(preset_name)

        if profile:
            self._current_profile = profile
            self._update_profile_info()
            self._on_param_changed()

    def _on_import_dxf(self):
        """导入DXF文件"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入异形边DXF",
            "",
            "DXF文件 (*.dxf);;所有文件 (*.*)"
        )

        if not file_path:
            return

        try:
            from src.core.edge_profile_loader import EdgeProfileDXFLoader
            loader = EdgeProfileDXFLoader()
            profile = loader.load_from_dxf(file_path)

            self._current_profile = profile
            self._update_profile_info()
            self._on_param_changed()

            QMessageBox.information(
                self, "导入成功",
                f"已导入异形边轮廓: {profile.name}\n"
                f"尺寸: {profile.original_width:.1f} x {profile.original_height:.1f} mm\n"
                f"控制点: {len(profile.control_points)} 个"
            )

        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "导入失败",
                f"无法导入DXF文件:\n{str(e)}"
            )

    def _update_profile_info(self):
        """更新轮廓信息显示"""
        if self._current_profile:
            info = f"{self._current_profile.name}"
            if self._current_profile.control_points:
                info += f" ({len(self._current_profile.control_points)}点)"
            self.profile_info_label.setText(info)
            self.profile_info_label.setStyleSheet("color: #58A6FF;")
        else:
            self.profile_info_label.setText("未选择轮廓")
            self.profile_info_label.setStyleSheet("color: #888;")
