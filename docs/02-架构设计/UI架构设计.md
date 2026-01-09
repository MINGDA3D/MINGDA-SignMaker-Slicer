# SignMaker Slicer UI架构设计

---

## 1. 概述

本文档详细描述 SignMaker Slicer 的用户界面架构设计，包括窗口布局、组件层次、交互设计和样式系统。

---

## 2. 界面布局

### 2.1 主窗口结构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                标题栏                                        │
│  SignMaker Slicer - 未命名项目                                    [_][□][X] │
├─────────────────────────────────────────────────────────────────────────────┤
│  文件(F)  编辑(E)  视图(V)  工具(T)  帮助(H)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  [打开][保存][导入][导出] | [撤销][重做] | [排版][填充][计算路径][输出]     │
├────────┬───────────────────────────────────────────────────────┬────────────┤
│        │ ┌────────┬────────┬────────┐                        │            │
│  左    │ │  首页  │  项目  │  预览  │                        │   右侧栏   │
│  侧    │ └────────┴────────┴────────┘                        │            │
│  栏    │                                                      │ ┌────────┐ │
│        │                                                      │ │选项卡1 │ │
│ ┌────┐ │                                                      │ │字壳工艺│ │
│ │文件│ │                                                      │ └────────┘ │
│ │列表│ │                                                      │ ┌────────┐ │
│ │    │ │              中央画布区域                            │ │选项卡2 │ │
│ │    │ │                                                      │ │换色层数│ │
│ │    │ │         (2D画布 / 3D预览 / 首页)                     │ └────────┘ │
│ └────┘ │                                                      │ ┌────────┐ │
│        │                                                      │ │选项卡3 │ │
│ ┌────┐ │                                                      │ │台阶V槽│ │
│ │工具│ │                                                      │ └────────┘ │
│ │面板│ │                                                      │   ...     │
│ │    │ │                                                      │ ┌────────┐ │
│ └────┘ │                                                      │ │选项卡8 │ │
│        │                                                      │ │生成底板│ │
│        │                                                      │ └────────┘ │
├────────┴───────────────────────────────────────────────────────┴────────────┤
│ 状态栏: 就绪 | 轮廓: 5个 | 当前层: 50/100 | 坐标: X:125.3 Y:89.2 | 缩放: 100%│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 尺寸规范

```python
LAYOUT_SPECS = {
    "window": {
        "min_width": 1280,
        "min_height": 720,
        "default_width": 1600,
        "default_height": 900,
    },
    "sidebar_left": {
        "width": 200,
        "min_width": 150,
        "max_width": 300,
        "collapsible": True,
    },
    "sidebar_right": {
        "width": 320,
        "min_width": 280,
        "max_width": 450,
        "collapsible": True,
    },
    "toolbar": {
        "height": 40,
        "icon_size": 24,
    },
    "statusbar": {
        "height": 24,
    },
    "tab_bar": {
        "height": 36,
    },
}
```

---

## 3. 组件层次结构

### 3.1 组件树

```
MainWindow
├── MenuBar
│   ├── FileMenu
│   ├── EditMenu
│   ├── ViewMenu
│   ├── ToolsMenu
│   └── HelpMenu
│
├── ToolBar
│   ├── FileToolGroup (打开/保存/导入/导出)
│   ├── EditToolGroup (撤销/重做)
│   ├── ArrangeToolGroup (排版/填充)
│   └── SliceToolGroup (计算路径/输出)
│
├── CentralWidget
│   ├── LeftSidebar
│   │   ├── FileTreePanel
│   │   │   └── ContourListWidget
│   │   └── ToolPanel
│   │       ├── SelectToolBtn
│   │       ├── StartPointToolBtn
│   │       ├── PrintOrderToolBtn
│   │       └── ...
│   │
│   ├── ContentArea
│   │   ├── TabBar
│   │   │   ├── HomeTab
│   │   │   ├── ProjectTab
│   │   │   └── PreviewTab
│   │   │
│   │   └── StackedWidget
│   │       ├── HomePage
│   │       │   ├── WelcomeSection
│   │       │   ├── RecentFilesSection
│   │       │   └── QuickActionsSection
│   │       │
│   │       ├── ProjectPage
│   │       │   └── Canvas2D
│   │       │
│   │       └── PreviewPage
│   │           ├── Preview3D
│   │           └── LayerSlider
│   │
│   └── RightSidebar
│       └── ParamTabWidget
│           ├── ShellPanel (选项卡1: 字壳工艺)
│           ├── ColorPanel (选项卡2: 换色层数)
│           ├── StepPanel (选项卡3: 台阶V槽)
│           ├── SkirtPanel (选项卡4: 防翘裙边)
│           ├── ConnectedPanel (选项卡5: 连襟字)
│           ├── EdgeWrapPanel (选项卡6: 包边勾边)
│           ├── FillPanel (选项卡7: 面板打印)
│           └── ExportPanel (选项卡8: 生成底板)
│
└── StatusBar
    ├── StatusLabel
    ├── ContourCountLabel
    ├── LayerInfoLabel
    ├── CoordinateLabel
    └── ZoomLabel
```

### 3.2 组件类定义

```python
# src/ui/main_window.py

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QStackedWidget, QToolBar,
    QMenuBar, QStatusBar, QDockWidget
)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        # 管理器
        self.project_manager = ProjectManager()
        self.slice_manager = SliceManager()
        self.preset_manager = PresetManager()
        self.command_manager = CommandManager()

        # 初始化UI
        self._setup_ui()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_connections()
        self._apply_theme()

    def _setup_ui(self):
        """设置UI布局"""
        # 中央widget
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局：水平分割
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 主分割器
        self.main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.main_splitter)

        # 左侧栏
        self.left_sidebar = LeftSidebar()
        self.main_splitter.addWidget(self.left_sidebar)

        # 内容区域
        self.content_area = ContentArea()
        self.main_splitter.addWidget(self.content_area)

        # 右侧栏（参数面板）
        self.right_sidebar = RightSidebar()
        self.main_splitter.addWidget(self.right_sidebar)

        # 设置分割比例
        self.main_splitter.setSizes([200, 800, 320])
        self.main_splitter.setStretchFactor(1, 1)  # 中间区域可伸缩

    def _setup_menubar(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("新建(&N)", self._on_new, "Ctrl+N")
        file_menu.addAction("打开(&O)...", self._on_open, "Ctrl+O")
        file_menu.addAction("保存(&S)", self._on_save, "Ctrl+S")
        file_menu.addAction("另存为(&A)...", self._on_save_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        file_menu.addAction("导入DXF(&I)...", self._on_import, "Ctrl+I")
        file_menu.addAction("导出DXF(&E)...", self._on_export_dxf)
        file_menu.addSeparator()
        file_menu.addAction("退出(&X)", self.close, "Alt+F4")

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        self.undo_action = edit_menu.addAction("撤销(&U)", self._on_undo, "Ctrl+Z")
        self.redo_action = edit_menu.addAction("重做(&R)", self._on_redo, "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("全选(&A)", self._on_select_all, "Ctrl+A")
        edit_menu.addAction("结合(&G)", self._on_combine, "Ctrl+G")
        edit_menu.addAction("打散(&U)", self._on_separate, "Ctrl+Shift+G")

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        view_menu.addAction("适应窗口(&F)", self._on_fit_view, "Ctrl+0")
        view_menu.addAction("放大(&I)", self._on_zoom_in, "Ctrl++")
        view_menu.addAction("缩小(&O)", self._on_zoom_out, "Ctrl+-")
        view_menu.addSeparator()
        view_menu.addAction("显示左侧栏", self._toggle_left_sidebar)
        view_menu.addAction("显示右侧栏", self._toggle_right_sidebar)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        tools_menu.addAction("起始点编辑", self._on_start_point_edit)
        tools_menu.addAction("打印顺序编辑", self._on_print_order_edit)
        tools_menu.addAction("排版...", self._on_layout)
        tools_menu.addSeparator()
        tools_menu.addAction("计算路径", self._on_calculate, "F5")
        tools_menu.addAction("文件输出...", self._on_output, "Ctrl+E")

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("帮助文档(&H)", self._on_help, "F1")
        help_menu.addAction("关于(&A)...", self._on_about)

    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 文件操作
        toolbar.addAction(QIcon("icons/open.svg"), "打开", self._on_open)
        toolbar.addAction(QIcon("icons/save.svg"), "保存", self._on_save)
        toolbar.addAction(QIcon("icons/import.svg"), "导入", self._on_import)
        toolbar.addAction(QIcon("icons/export.svg"), "导出", self._on_export)
        toolbar.addSeparator()

        # 编辑操作
        toolbar.addAction(QIcon("icons/undo.svg"), "撤销", self._on_undo)
        toolbar.addAction(QIcon("icons/redo.svg"), "重做", self._on_redo)
        toolbar.addSeparator()

        # 排版工具
        toolbar.addAction(QIcon("icons/layout.svg"), "排版", self._on_layout)
        toolbar.addAction(QIcon("icons/fill.svg"), "填充", self._on_fill_settings)
        toolbar.addSeparator()

        # 切片操作
        toolbar.addAction(QIcon("icons/slice.svg"), "计算路径", self._on_calculate)
        toolbar.addAction(QIcon("icons/output.svg"), "文件输出", self._on_output)

    def _setup_statusbar(self):
        """设置状态栏"""
        statusbar = self.statusBar()

        # 状态标签
        self.status_label = QLabel("就绪")
        statusbar.addWidget(self.status_label)

        # 分隔符
        statusbar.addWidget(QLabel(" | "))

        # 轮廓数量
        self.contour_label = QLabel("轮廓: 0个")
        statusbar.addWidget(self.contour_label)

        # 层信息
        self.layer_label = QLabel("")
        statusbar.addPermanentWidget(self.layer_label)

        # 坐标
        self.coord_label = QLabel("X: 0.0  Y: 0.0")
        statusbar.addPermanentWidget(self.coord_label)

        # 缩放
        self.zoom_label = QLabel("100%")
        statusbar.addPermanentWidget(self.zoom_label)

    def _setup_connections(self):
        """设置信号槽连接"""
        # 项目管理器信号
        self.project_manager.contours_updated.connect(
            self.content_area.canvas.set_contours
        )
        self.project_manager.project_modified.connect(
            self._update_title
        )

        # 切片管理器信号
        self.slice_manager.slice_progress.connect(
            self._on_slice_progress
        )
        self.slice_manager.slice_completed.connect(
            self._on_slice_completed
        )

        # 画布信号
        self.content_area.canvas.mouse_position.connect(
            self._update_coordinates
        )
        self.content_area.canvas.zoom_changed.connect(
            self._update_zoom
        )

        # 参数面板信号
        for panel in self.right_sidebar.param_panels:
            panel.params_changed.connect(
                self.slice_manager.update_params
            )
```

---

## 4. 核心组件设计

### 4.1 左侧栏 (LeftSidebar)

```python
class LeftSidebar(QWidget):
    """左侧栏"""

    def __init__(self):
        super().__init__()
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 文件/轮廓列表
        self.file_panel = FileTreePanel()
        layout.addWidget(self.file_panel, stretch=1)

        # 工具面板
        self.tool_panel = ToolPanel()
        layout.addWidget(self.tool_panel)


class FileTreePanel(QWidget):
    """文件/轮廓列表面板"""

    contour_selected = Signal(int)
    contour_double_clicked = Signal(int)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title = QLabel("轮廓列表")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)

    def set_contours(self, contours: List[Contour]):
        """设置轮廓列表"""
        self.list_widget.clear()
        for i, contour in enumerate(contours):
            name = contour.name or f"轮廓 {i + 1}"
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, i)
            self.list_widget.addItem(item)


class ToolPanel(QWidget):
    """工具面板"""

    tool_changed = Signal(str)

    TOOLS = [
        ("select", "选择", "icons/select.svg"),
        ("start_point", "起始点编辑", "icons/start_point.svg"),
        ("print_order", "打印顺序", "icons/print_order.svg"),
        ("mirror", "镜像", "icons/mirror.svg"),
        ("rotate", "旋转", "icons/rotate.svg"),
    ]

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title = QLabel("工具")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # 工具按钮组
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        tool_layout = QGridLayout()
        tool_layout.setSpacing(4)

        for i, (tool_id, tooltip, icon) in enumerate(self.TOOLS):
            btn = QToolButton()
            btn.setIcon(QIcon(icon))
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setProperty("tool_id", tool_id)
            self.button_group.addButton(btn)
            tool_layout.addWidget(btn, i // 3, i % 3)

        layout.addLayout(tool_layout)
        layout.addStretch()

        # 默认选择"选择"工具
        self.button_group.buttons()[0].setChecked(True)
        self.button_group.buttonClicked.connect(self._on_tool_clicked)

    def _on_tool_clicked(self, button):
        tool_id = button.property("tool_id")
        self.tool_changed.emit(tool_id)
```

### 4.2 内容区域 (ContentArea)

```python
class ContentArea(QWidget):
    """内容区域"""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 选项卡栏
        self.tab_bar = QTabBar()
        self.tab_bar.addTab("首页")
        self.tab_bar.addTab("项目")
        self.tab_bar.addTab("预览")
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_bar)

        # 堆叠widget
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # 首页
        self.home_page = HomePage()
        self.stack.addWidget(self.home_page)

        # 项目页（2D画布）
        self.project_page = ProjectPage()
        self.canvas = self.project_page.canvas
        self.stack.addWidget(self.project_page)

        # 预览页（3D预览）
        self.preview_page = PreviewPage()
        self.preview_3d = self.preview_page.preview
        self.stack.addWidget(self.preview_page)

    def _on_tab_changed(self, index):
        self.stack.setCurrentIndex(index)


class HomePage(QWidget):
    """首页"""

    file_open_requested = Signal(str)
    new_project_requested = Signal()

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Logo
        logo = QLabel()
        logo.setPixmap(QPixmap("icons/logo.png").scaled(200, 200, Qt.KeepAspectRatio))
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        # 欢迎标题
        title = QLabel("SignMaker Slicer")
        title.setObjectName("welcome-title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 副标题
        subtitle = QLabel("专业发光字3D打印切片软件")
        subtitle.setObjectName("welcome-subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(40)

        # 快速操作
        actions_layout = QHBoxLayout()
        actions_layout.setAlignment(Qt.AlignCenter)

        new_btn = QPushButton("新建项目")
        new_btn.setObjectName("primary-button")
        new_btn.clicked.connect(lambda: self.new_project_requested.emit())
        actions_layout.addWidget(new_btn)

        open_btn = QPushButton("打开项目")
        open_btn.clicked.connect(self._on_open_clicked)
        actions_layout.addWidget(open_btn)

        import_btn = QPushButton("导入DXF")
        import_btn.clicked.connect(self._on_import_clicked)
        actions_layout.addWidget(import_btn)

        layout.addLayout(actions_layout)

        layout.addSpacing(40)

        # 最近文件
        recent_label = QLabel("最近打开")
        recent_label.setObjectName("section-title")
        layout.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(150)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_clicked)
        layout.addWidget(self.recent_list)

        layout.addStretch()

    def set_recent_files(self, files: List[str]):
        """设置最近文件列表"""
        self.recent_list.clear()
        for file_path in files:
            item = QListWidgetItem(Path(file_path).name)
            item.setData(Qt.UserRole, file_path)
            item.setToolTip(file_path)
            self.recent_list.addItem(item)


class ProjectPage(QWidget):
    """项目页"""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 2D画布
        self.canvas = Canvas2D()
        layout.addWidget(self.canvas)


class PreviewPage(QWidget):
    """预览页"""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 3D预览
        self.preview = Preview3D()
        layout.addWidget(self.preview, stretch=1)

        # 层滑块
        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(8, 4, 8, 4)

        slider_layout.addWidget(QLabel("层:"))
        self.layer_slider = QSlider(Qt.Horizontal)
        self.layer_slider.valueChanged.connect(self.preview.set_current_layer)
        slider_layout.addWidget(self.layer_slider, stretch=1)

        self.layer_label = QLabel("0 / 0")
        slider_layout.addWidget(self.layer_label)

        layout.addLayout(slider_layout)

    def set_layers(self, layers: List[Layer]):
        """设置层数据"""
        self.preview.set_layers(layers)
        self.layer_slider.setMaximum(len(layers) - 1 if layers else 0)
        self._update_layer_label()

    def _update_layer_label(self):
        current = self.layer_slider.value()
        total = self.layer_slider.maximum() + 1
        self.layer_label.setText(f"{current + 1} / {total}")
```

### 4.3 右侧栏 - 参数面板 (RightSidebar)

```python
class RightSidebar(QWidget):
    """右侧参数面板"""

    def __init__(self):
        super().__init__()
        self.setFixedWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.West)  # 垂直选项卡
        layout.addWidget(self.tab_widget)

        # 8个参数面板
        self.shell_panel = ShellPanel()
        self.tab_widget.addTab(self.shell_panel, "字壳工艺")

        self.color_panel = ColorPanel()
        self.tab_widget.addTab(self.color_panel, "换色层数")

        self.step_panel = StepPanel()
        self.tab_widget.addTab(self.step_panel, "台阶V槽")

        self.skirt_panel = SkirtPanel()
        self.tab_widget.addTab(self.skirt_panel, "防翘裙边")

        self.connected_panel = ConnectedPanel()
        self.tab_widget.addTab(self.connected_panel, "连襟字")

        self.edge_wrap_panel = EdgeWrapPanel()
        self.tab_widget.addTab(self.edge_wrap_panel, "包边勾边")

        self.fill_panel = FillPanel()
        self.tab_widget.addTab(self.fill_panel, "面板打印")

        self.export_panel = ExportPanel()
        self.tab_widget.addTab(self.export_panel, "生成底板")

        # 收集所有面板
        self.param_panels = [
            self.shell_panel, self.color_panel, self.step_panel,
            self.skirt_panel, self.connected_panel, self.edge_wrap_panel,
            self.fill_panel, self.export_panel
        ]

    def load_params(self, params: SliceParams):
        """加载参数到所有面板"""
        self.shell_panel.set_params(params.shell)
        self.color_panel.set_params(params.color)
        self.step_panel.set_params(params.step)
        self.skirt_panel.set_params(params.skirt)
        self.connected_panel.set_params(params.connected)
        self.edge_wrap_panel.set_params(params.edge_wrap)
        self.fill_panel.set_params(params.panel, params.grid, params.baseplate)
        # export_panel 使用 GCodeParams

    def get_params(self) -> SliceParams:
        """获取所有面板的参数"""
        return SliceParams(
            shell=self.shell_panel.get_params(),
            color=self.color_panel.get_params(),
            step=self.step_panel.get_params(),
            skirt=self.skirt_panel.get_params(),
            connected=self.connected_panel.get_params(),
            edge_wrap=self.edge_wrap_panel.get_params(),
            panel=self.fill_panel.get_panel_params(),
            grid=self.fill_panel.get_grid_params(),
            baseplate=self.fill_panel.get_baseplate_params(),
        )
```

### 4.4 参数面板示例 (ShellPanel)

```python
class ShellPanel(QScrollArea):
    """字壳工艺参数面板"""

    params_changed = Signal(ShellParams)

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)

        # 内容widget
        content = QWidget()
        self.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setSpacing(8)

        # === 打印模式 ===
        mode_group = QGroupBox("打印模式")
        mode_layout = QHBoxLayout(mode_group)

        self.normal_radio = QRadioButton("正常打印")
        self.mirror_radio = QRadioButton("镜像打印")
        self.normal_radio.setChecked(True)

        mode_layout.addWidget(self.normal_radio)
        mode_layout.addWidget(self.mirror_radio)
        layout.addWidget(mode_group)

        # === 字边类型 ===
        edge_group = QGroupBox("字边类型")
        edge_layout = QVBoxLayout(edge_group)

        self.edge_type_combo = QComboBox()
        self.edge_type_combo.addItems(["直边", "斜边", "异形边"])
        self.edge_type_combo.currentIndexChanged.connect(self._on_edge_type_changed)
        edge_layout.addWidget(self.edge_type_combo)

        # 异形边选择（仅异形边时显示）
        self.profile_widget = QWidget()
        profile_layout = QHBoxLayout(self.profile_widget)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["波浪边", "锯齿边", "圆弧边"])
        profile_layout.addWidget(self.profile_combo)
        btn_add = QPushButton("添加")
        btn_del = QPushButton("删除")
        profile_layout.addWidget(btn_add)
        profile_layout.addWidget(btn_del)
        self.profile_widget.hide()
        edge_layout.addWidget(self.profile_widget)

        layout.addWidget(edge_group)

        # === 尺寸参数 ===
        size_group = QGroupBox("尺寸参数")
        size_layout = QFormLayout(size_group)

        self.height_spin = self._create_spin(0, 500, 30, "mm")
        size_layout.addRow("字壳高度:", self.height_spin)

        self.bevel_width_spin = self._create_spin(0, 50, 5, "mm")
        size_layout.addRow("斜边宽度:", self.bevel_width_spin)

        self.panel_thickness_spin = self._create_spin(0, 20, 3, "mm")
        size_layout.addRow("面板厚度:", self.panel_thickness_spin)

        self.baseplate_thickness_spin = self._create_spin(0, 50, 10, "mm")
        size_layout.addRow("底板厚度:", self.baseplate_thickness_spin)

        layout.addWidget(size_group)

        # === 壁厚参数 ===
        wall_group = QGroupBox("壁厚参数")
        wall_layout = QFormLayout(wall_group)

        self.wall_thickness_spin = self._create_spin(0.5, 5, 1.2, "mm", 0.1)
        wall_layout.addRow("壁厚:", self.wall_thickness_spin)

        self.wall_compensation_spin = self._create_spin(-1, 1, 0, "mm", 0.01)
        wall_layout.addRow("壁厚补偿:", self.wall_compensation_spin)

        self.wall_count_spin = self._create_spin(1, 5, 1)
        wall_layout.addRow("走线次数:", self.wall_count_spin)

        self.wall_offset_spin = self._create_spin(0, 2, 0.8, "mm", 0.1)
        wall_layout.addRow("走线偏移:", self.wall_offset_spin)

        layout.addWidget(wall_group)

        # === 层参数 ===
        layer_group = QGroupBox("层参数")
        layer_layout = QFormLayout(layer_group)

        self.layer_height_spin = self._create_spin(0.1, 1.0, 0.3, "mm", 0.05)
        layer_layout.addRow("层高:", self.layer_height_spin)

        layout.addWidget(layer_group)

        # === 预打边线 ===
        safety_group = QGroupBox("预打边线")
        safety_layout = QFormLayout(safety_group)

        self.safety_offset_spin = self._create_spin(5, 50, 20, "mm")
        safety_layout.addRow("偏移距离:", self.safety_offset_spin)

        self.safety_count_spin = self._create_spin(0, 10, 1)
        safety_layout.addRow("次数:", self.safety_count_spin)

        layout.addWidget(safety_group)

        # === 字芯参数 ===
        core_group = QGroupBox("字芯参数")
        core_layout = QFormLayout(core_group)

        self.core_height_spin = self._create_spin(0, 100, 0, "mm")
        core_layout.addRow("字芯高度:", self.core_height_spin)

        self.core_bevel_spin = self._create_spin(0, 20, 0, "mm")
        core_layout.addRow("字芯斜边:", self.core_bevel_spin)

        layout.addWidget(core_group)

        # === 操作按钮 ===
        btn_layout = QHBoxLayout()

        self.calc_btn = QPushButton("计算路径")
        self.calc_btn.setObjectName("primary-button")
        btn_layout.addWidget(self.calc_btn)

        self.preview_btn = QPushButton("预览字边")
        btn_layout.addWidget(self.preview_btn)

        layout.addLayout(btn_layout)

        layout.addStretch()

        # 连接信号
        self._connect_signals()

    def _create_spin(self, min_val, max_val, default, suffix="", step=1):
        """创建SpinBox"""
        if isinstance(default, float):
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setSingleStep(step if step else 0.1)
        else:
            spin = QSpinBox()
            if step:
                spin.setSingleStep(int(step))

        spin.setRange(min_val, max_val)
        spin.setValue(default)
        if suffix:
            spin.setSuffix(f" {suffix}")

        return spin

    def _connect_signals(self):
        """连接内部信号"""
        # 所有输入变化时触发参数更新
        for widget in self.findChildren((QSpinBox, QDoubleSpinBox)):
            widget.valueChanged.connect(self._emit_params)

        for widget in self.findChildren(QComboBox):
            widget.currentIndexChanged.connect(self._emit_params)

        for widget in self.findChildren(QRadioButton):
            widget.toggled.connect(self._emit_params)

    def _on_edge_type_changed(self, index):
        """边类型变化"""
        # 显示/隐藏异形边选择
        self.profile_widget.setVisible(index == 2)

        # 显示/隐藏斜边相关参数
        is_beveled = (index == 1)
        self.bevel_width_spin.setEnabled(is_beveled)
        self.panel_thickness_spin.setEnabled(is_beveled)
        self.baseplate_thickness_spin.setEnabled(is_beveled)

    def _emit_params(self):
        """发送参数变更信号"""
        params = self.get_params()
        self.params_changed.emit(params)

    def set_params(self, params: ShellParams):
        """设置参数"""
        # 阻止信号
        self.blockSignals(True)

        self.mirror_radio.setChecked(params.is_mirrored)
        self.normal_radio.setChecked(not params.is_mirrored)

        edge_index = {EdgeType.STRAIGHT: 0, EdgeType.BEVELED: 1, EdgeType.CUSTOM: 2}
        self.edge_type_combo.setCurrentIndex(edge_index.get(params.edge_type, 0))

        self.height_spin.setValue(params.height)
        self.bevel_width_spin.setValue(params.bevel_width)
        self.panel_thickness_spin.setValue(params.panel_thickness)
        self.baseplate_thickness_spin.setValue(params.baseplate_thickness)

        self.wall_thickness_spin.setValue(params.wall_thickness)
        self.wall_count_spin.setValue(params.wall_count)
        self.wall_offset_spin.setValue(params.wall_offset)

        self.layer_height_spin.setValue(params.layer_height)

        self.safety_offset_spin.setValue(params.safety_line_offset)
        self.safety_count_spin.setValue(params.safety_line_count)

        self.core_height_spin.setValue(params.core_height)
        self.core_bevel_spin.setValue(params.core_bevel_width)

        # 恢复信号
        self.blockSignals(False)

    def get_params(self) -> ShellParams:
        """获取参数"""
        edge_types = [EdgeType.STRAIGHT, EdgeType.BEVELED, EdgeType.CUSTOM]

        return ShellParams(
            is_mirrored=self.mirror_radio.isChecked(),
            edge_type=edge_types[self.edge_type_combo.currentIndex()],
            height=self.height_spin.value(),
            bevel_width=self.bevel_width_spin.value(),
            panel_thickness=self.panel_thickness_spin.value(),
            baseplate_thickness=self.baseplate_thickness_spin.value(),
            wall_thickness=self.wall_thickness_spin.value(),
            wall_count=self.wall_count_spin.value(),
            wall_offset=self.wall_offset_spin.value(),
            layer_height=self.layer_height_spin.value(),
            safety_line_offset=self.safety_offset_spin.value(),
            safety_line_count=self.safety_count_spin.value(),
            core_height=self.core_height_spin.value(),
            core_bevel_width=self.core_bevel_spin.value(),
        )
```

---

## 5. 2D画布设计

### 5.1 Canvas2D 类

```python
class Canvas2D(QWidget):
    """2D画布组件"""

    # 信号
    selection_changed = Signal(list)
    start_point_changed = Signal(int, int)
    print_order_changed = Signal(list)
    mouse_position = Signal(float, float)
    zoom_changed = Signal(float)
    context_menu_requested = Signal(QPoint)

    def __init__(self):
        super().__init__()

        # 数据
        self.contours: List[Contour] = []
        self.selected_indices: List[int] = []
        self.print_order: List[int] = []

        # 视图状态
        self.view_offset = QPointF(0, 0)
        self.view_scale = 1.0
        self.min_scale = 0.01
        self.max_scale = 100

        # 交互状态
        self.edit_mode = EditMode.SELECT
        self.is_panning = False
        self.last_mouse_pos = QPointF()
        self.drag_start = None

        # 渲染设置
        self.show_start_points = True
        self.show_print_order = False
        self.show_grid = True
        self.grid_spacing = 10  # mm

        # 颜色
        self.colors = {
            'background': QColor('#0D1117'),
            'grid': QColor('#21262D'),
            'contour': QColor('#58A6FF'),
            'contour_selected': QColor('#F78166'),
            'hole': QColor('#7EE787'),
            'start_point': QColor('#F78166'),
            'connected': QColor('#00FFFF'),
            'pattern': QColor('#0000FF'),
        }

        # 设置widget属性
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_contours(self, contours: List[Contour]):
        """设置轮廓数据"""
        self.contours = contours
        self.selected_indices = []
        self.print_order = list(range(len(contours)))
        self.fit_view()
        self.update()

    def set_edit_mode(self, mode: EditMode):
        """设置编辑模式"""
        self.edit_mode = mode
        self.setCursor(self._get_cursor_for_mode(mode))
        self.update()

    def fit_view(self):
        """适应视图"""
        if not self.contours:
            return

        # 计算所有轮廓的边界
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        for contour in self.contours:
            for point in contour.outer.points:
                min_x = min(min_x, point.x)
                min_y = min(min_y, point.y)
                max_x = max(max_x, point.x)
                max_y = max(max_y, point.y)

        if min_x == float('inf'):
            return

        # 计算合适的缩放和偏移
        content_width = max_x - min_x
        content_height = max_y - min_y
        margin = 50

        scale_x = (self.width() - margin * 2) / content_width if content_width > 0 else 1
        scale_y = (self.height() - margin * 2) / content_height if content_height > 0 else 1
        self.view_scale = min(scale_x, scale_y)

        # 居中
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.view_offset = QPointF(
            self.width() / 2 - center_x * self.view_scale,
            self.height() / 2 + center_y * self.view_scale  # Y轴翻转
        )

        self.zoom_changed.emit(self.view_scale * 100)
        self.update()

    def paintEvent(self, event: QPaintEvent):
        """绑制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), self.colors['background'])

        # 网格
        if self.show_grid:
            self._draw_grid(painter)

        # 保存变换状态
        painter.save()

        # 应用视图变换
        painter.translate(self.view_offset)
        painter.scale(self.view_scale, -self.view_scale)  # Y轴翻转

        # 绘制轮廓
        for i, contour in enumerate(self.contours):
            is_selected = i in self.selected_indices
            self._draw_contour(painter, contour, is_selected)

            # 绘制起始点
            if self.show_start_points:
                self._draw_start_point(painter, contour)

        # 绘制打印顺序
        if self.show_print_order and self.edit_mode == EditMode.PRINT_ORDER:
            self._draw_print_order(painter)

        painter.restore()

    def _draw_grid(self, painter: QPainter):
        """绘制网格"""
        painter.setPen(QPen(self.colors['grid'], 1))

        # 计算可见区域的世界坐标
        inv_scale = 1 / self.view_scale
        left = -self.view_offset.x() * inv_scale
        right = (self.width() - self.view_offset.x()) * inv_scale
        top = -(-self.view_offset.y()) * inv_scale
        bottom = (self.height() - self.view_offset.y()) * inv_scale

        # 网格间距（根据缩放调整）
        spacing = self.grid_spacing
        while spacing * self.view_scale < 20:
            spacing *= 5
        while spacing * self.view_scale > 100:
            spacing /= 5

        # 绘制垂直线
        x = int(left / spacing) * spacing
        while x < right:
            screen_x = x * self.view_scale + self.view_offset.x()
            painter.drawLine(int(screen_x), 0, int(screen_x), self.height())
            x += spacing

        # 绘制水平线
        y = int(bottom / spacing) * spacing
        while y < top:
            screen_y = -y * self.view_scale + self.view_offset.y()
            painter.drawLine(0, int(screen_y), self.width(), int(screen_y))
            y += spacing

    def _draw_contour(self, painter: QPainter, contour: Contour, is_selected: bool):
        """绘制轮廓"""
        # 外轮廓
        color = self.colors['contour_selected'] if is_selected else self.colors['contour']
        pen = QPen(color, 2 / self.view_scale)
        painter.setPen(pen)

        path = self._path_to_qpath(contour.outer)
        painter.drawPath(path)

        # 内孔
        painter.setPen(QPen(self.colors['hole'], 1.5 / self.view_scale))
        for hole in contour.holes:
            path = self._path_to_qpath(hole)
            painter.drawPath(path)

        # 连襟框
        painter.setPen(QPen(self.colors['connected'], 1.5 / self.view_scale))
        for frame in contour.connected_frames:
            path = self._path_to_qpath(frame)
            painter.drawPath(path)

        # 花纹
        painter.setPen(QPen(self.colors['pattern'], 1.5 / self.view_scale))
        for pattern in contour.patterns:
            path = self._path_to_qpath(pattern)
            painter.drawPath(path)

    def _draw_start_point(self, painter: QPainter, contour: Contour):
        """绘制起始点"""
        if contour.outer.points:
            start = contour.outer.points[contour.outer.start_index]
            radius = 5 / self.view_scale

            painter.setPen(Qt.NoPen)
            painter.setBrush(self.colors['start_point'])
            painter.drawEllipse(
                QPointF(start.x, start.y),
                radius, radius
            )

    def _draw_print_order(self, painter: QPainter):
        """绘制打印顺序"""
        font = painter.font()
        font.setPointSizeF(12 / self.view_scale)
        painter.setFont(font)

        for i, contour_idx in enumerate(self.print_order):
            contour = self.contours[contour_idx]
            center = self._get_contour_center(contour)

            # 背景圆
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#F78166'))
            radius = 15 / self.view_scale
            painter.drawEllipse(QPointF(center.x, center.y), radius, radius)

            # 数字
            painter.setPen(Qt.white)
            painter.drawText(
                QRectF(center.x - radius, center.y - radius, radius * 2, radius * 2),
                Qt.AlignCenter,
                str(i + 1)
            )

    def _path_to_qpath(self, path: Path) -> QPainterPath:
        """将Path转换为QPainterPath"""
        qpath = QPainterPath()
        if path.points:
            qpath.moveTo(path.points[0].x, path.points[0].y)
            for point in path.points[1:]:
                qpath.lineTo(point.x, point.y)
            qpath.closeSubpath()
        return qpath

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        if event.button() == Qt.MiddleButton:
            # 中键平移
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)

        elif event.button() == Qt.LeftButton:
            world_pos = self._screen_to_world(event.position())

            if self.edit_mode == EditMode.SELECT:
                # 选择模式
                clicked_idx = self._hit_test(world_pos)
                if clicked_idx >= 0:
                    if event.modifiers() & Qt.ControlModifier:
                        # Ctrl+点击 切换选择
                        if clicked_idx in self.selected_indices:
                            self.selected_indices.remove(clicked_idx)
                        else:
                            self.selected_indices.append(clicked_idx)
                    else:
                        # 单击选择
                        self.selected_indices = [clicked_idx]
                else:
                    self.selected_indices = []

                self.selection_changed.emit(self.selected_indices)
                self.update()

            elif self.edit_mode == EditMode.START_POINT:
                # 起始点编辑
                self._set_start_point(world_pos)

            elif self.edit_mode == EditMode.PRINT_ORDER:
                # 打印顺序编辑
                self._toggle_print_order(world_pos, event.button() == Qt.LeftButton)

        elif event.button() == Qt.RightButton:
            if self.edit_mode == EditMode.PRINT_ORDER:
                world_pos = self._screen_to_world(event.position())
                self._toggle_print_order(world_pos, False)
            else:
                self.context_menu_requested.emit(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        if self.is_panning:
            delta = event.position() - self.last_mouse_pos
            self.view_offset += delta
            self.last_mouse_pos = event.position()
            self.update()

        # 更新坐标显示
        world_pos = self._screen_to_world(event.position())
        self.mouse_position.emit(world_pos.x(), world_pos.y())

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.setCursor(self._get_cursor_for_mode(self.edit_mode))

    def wheelEvent(self, event: QWheelEvent):
        """滚轮缩放"""
        # 获取鼠标位置的世界坐标
        mouse_pos = event.position()
        world_before = self._screen_to_world(mouse_pos)

        # 计算缩放因子
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15

        new_scale = self.view_scale * factor
        new_scale = max(self.min_scale, min(self.max_scale, new_scale))

        # 应用缩放
        self.view_scale = new_scale

        # 调整偏移使鼠标位置的世界坐标保持不变
        world_after = self._screen_to_world(mouse_pos)
        self.view_offset += QPointF(
            (world_after.x() - world_before.x()) * self.view_scale,
            -(world_after.y() - world_before.y()) * self.view_scale
        )

        self.zoom_changed.emit(self.view_scale * 100)
        self.update()

    def _screen_to_world(self, screen_pos: QPointF) -> QPointF:
        """屏幕坐标转世界坐标"""
        x = (screen_pos.x() - self.view_offset.x()) / self.view_scale
        y = -(screen_pos.y() - self.view_offset.y()) / self.view_scale
        return QPointF(x, y)

    def _world_to_screen(self, world_pos: QPointF) -> QPointF:
        """世界坐标转屏幕坐标"""
        x = world_pos.x() * self.view_scale + self.view_offset.x()
        y = -world_pos.y() * self.view_scale + self.view_offset.y()
        return QPointF(x, y)

    def _hit_test(self, world_pos: QPointF) -> int:
        """点击测试，返回被点击的轮廓索引，-1表示未点击"""
        hit_distance = 5 / self.view_scale  # 5像素容差

        for i, contour in enumerate(self.contours):
            # 检查是否在轮廓边界附近
            for j, point in enumerate(contour.outer.points):
                next_point = contour.outer.points[(j + 1) % len(contour.outer.points)]

                dist = self._point_to_segment_distance(
                    world_pos, QPointF(point.x, point.y),
                    QPointF(next_point.x, next_point.y)
                )
                if dist < hit_distance:
                    return i

        return -1

    def _point_to_segment_distance(self, point: QPointF,
                                     seg_start: QPointF, seg_end: QPointF) -> float:
        """计算点到线段的距离"""
        dx = seg_end.x() - seg_start.x()
        dy = seg_end.y() - seg_start.y()

        if dx == 0 and dy == 0:
            return ((point.x() - seg_start.x()) ** 2 +
                    (point.y() - seg_start.y()) ** 2) ** 0.5

        t = max(0, min(1, (
            (point.x() - seg_start.x()) * dx +
            (point.y() - seg_start.y()) * dy
        ) / (dx * dx + dy * dy)))

        proj_x = seg_start.x() + t * dx
        proj_y = seg_start.y() + t * dy

        return ((point.x() - proj_x) ** 2 + (point.y() - proj_y) ** 2) ** 0.5

    def _get_cursor_for_mode(self, mode: EditMode) -> Qt.CursorShape:
        """获取模式对应的光标"""
        cursors = {
            EditMode.SELECT: Qt.ArrowCursor,
            EditMode.START_POINT: Qt.CrossCursor,
            EditMode.PRINT_ORDER: Qt.PointingHandCursor,
        }
        return cursors.get(mode, Qt.ArrowCursor)
```

---

## 6. 3D预览设计

### 6.1 Preview3D 类

```python
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
import numpy as np

class Preview3D(QOpenGLWidget):
    """3D预览组件"""

    current_layer_changed = Signal(int)

    def __init__(self):
        super().__init__()

        # 数据
        self.layers: List[Layer] = []
        self.current_layer = 0
        self.show_all_layers = True

        # 相机
        self.rotation = [30, 0, 45]  # 俯仰、偏航、滚转
        self.zoom = 1.0
        self.pan = [0, 0, 0]

        # 交互状态
        self.last_mouse_pos = QPointF()
        self.is_rotating = False
        self.is_panning = False

        # 渲染设置
        self.show_travel = False
        self.extruder_colors = {
            ExtruderType.EXTRUDER_1: (0.345, 0.651, 1.0, 1.0),  # 蓝色
            ExtruderType.EXTRUDER_2: (0.925, 0.282, 0.600, 1.0),  # 粉色
            ExtruderType.EXTRUDER_3: (0.961, 0.620, 0.043, 1.0),  # 橙色
        }

        # VBO数据
        self.vbo = None
        self.vao = None
        self.vertex_count = 0

        self.setMouseTracking(True)

    def set_layers(self, layers: List[Layer]):
        """设置层数据"""
        self.layers = layers
        self.current_layer = len(layers) - 1 if layers else 0
        self._rebuild_geometry()
        self.update()

    def set_current_layer(self, layer_index: int):
        """设置当前层"""
        self.current_layer = max(0, min(layer_index, len(self.layers) - 1))
        self.current_layer_changed.emit(self.current_layer)
        self.update()

    def initializeGL(self):
        """初始化OpenGL"""
        glClearColor(0.05, 0.07, 0.09, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glLineWidth(1.5)

        # 创建VBO
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)

    def paintGL(self):
        """渲染"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if not self.layers:
            return

        # 设置投影矩阵
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.width() / self.height() if self.height() > 0 else 1
        gluPerspective(45, aspect, 0.1, 10000)

        # 设置模型视图矩阵
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # 相机变换
        glTranslatef(self.pan[0], self.pan[1], -500 / self.zoom)
        glRotatef(self.rotation[0], 1, 0, 0)
        glRotatef(self.rotation[1], 0, 1, 0)
        glRotatef(self.rotation[2], 0, 0, 1)

        # 绘制层
        for i, layer in enumerate(self.layers):
            if self.show_all_layers or i <= self.current_layer:
                alpha = 1.0 if i == self.current_layer else 0.5
                self._draw_layer(layer, alpha)

        # 绘制地面网格
        self._draw_ground_grid()

    def _draw_layer(self, layer: Layer, alpha: float = 1.0):
        """绘制单层"""
        z = layer.z_height

        for path in layer.paths:
            # 获取挤出机颜色
            color = list(self.extruder_colors.get(
                path.extruder, (1, 1, 1, 1)
            ))
            color[3] = alpha

            glColor4f(*color)

            # 绘制路径
            if path.is_closed:
                glBegin(GL_LINE_LOOP)
            else:
                glBegin(GL_LINE_STRIP)

            for point in path.points:
                glVertex3f(point.x, point.y, z)

            glEnd()

    def _draw_ground_grid(self):
        """绘制地面网格"""
        glColor4f(0.2, 0.2, 0.2, 0.5)
        glBegin(GL_LINES)

        grid_size = 500
        spacing = 50

        for i in range(-grid_size, grid_size + 1, spacing):
            glVertex3f(i, -grid_size, 0)
            glVertex3f(i, grid_size, 0)
            glVertex3f(-grid_size, i, 0)
            glVertex3f(grid_size, i, 0)

        glEnd()

    def _rebuild_geometry(self):
        """重建几何数据"""
        # TODO: 使用VBO优化大数据量渲染
        pass

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        self.last_mouse_pos = event.position()

        if event.button() == Qt.LeftButton:
            self.is_rotating = True
        elif event.button() == Qt.MiddleButton:
            self.is_panning = True

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        delta = event.position() - self.last_mouse_pos
        self.last_mouse_pos = event.position()

        if self.is_rotating:
            self.rotation[0] += delta.y() * 0.5
            self.rotation[2] += delta.x() * 0.5
            self.update()

        elif self.is_panning:
            self.pan[0] += delta.x() * 0.5
            self.pan[1] -= delta.y() * 0.5
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        self.is_rotating = False
        self.is_panning = False

    def wheelEvent(self, event: QWheelEvent):
        """滚轮缩放"""
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 1 / 1.1
        self.zoom *= factor
        self.zoom = max(0.1, min(10, self.zoom))
        self.update()

    def reset_view(self):
        """重置视图"""
        self.rotation = [30, 0, 45]
        self.zoom = 1.0
        self.pan = [0, 0, 0]
        self.update()
```

---

## 7. 样式系统

### 7.1 主题定义

```python
# 在 src/ui/theme.py 中已有完整定义
# 这里是使用示例

def apply_theme(app: QApplication):
    """应用主题"""
    from src.ui.theme import get_stylesheet

    app.setStyleSheet(get_stylesheet())

    # 设置调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor('#0D1117'))
    palette.setColor(QPalette.WindowText, QColor('#E6EDF3'))
    palette.setColor(QPalette.Base, QColor('#161B22'))
    palette.setColor(QPalette.Text, QColor('#E6EDF3'))
    palette.setColor(QPalette.Button, QColor('#21262D'))
    palette.setColor(QPalette.ButtonText, QColor('#E6EDF3'))
    palette.setColor(QPalette.Highlight, QColor('#1F6FEB'))
    palette.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))

    app.setPalette(palette)
```

### 7.2 组件样式类

```python
class StyledWidgets:
    """样式化组件工厂"""

    @staticmethod
    def create_primary_button(text: str) -> QPushButton:
        """创建主要按钮"""
        btn = QPushButton(text)
        btn.setObjectName("primary-button")
        return btn

    @staticmethod
    def create_group_box(title: str) -> QGroupBox:
        """创建分组框"""
        group = QGroupBox(title)
        group.setObjectName("param-group")
        return group

    @staticmethod
    def create_spin_box(min_val: float, max_val: float,
                         default: float, suffix: str = "") -> QDoubleSpinBox:
        """创建数值输入框"""
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSuffix(f" {suffix}" if suffix else "")
        spin.setDecimals(2)
        return spin
```

---

## 8. 对话框设计

### 8.1 输出设置对话框

```python
class OutputDialog(QDialog):
    """输出设置对话框"""

    def __init__(self, gcode_params: GCodeParams, parent=None):
        super().__init__(parent)
        self.params = gcode_params
        self.result_path = ""

        self.setWindowTitle("文件输出")
        self.setMinimumWidth(500)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 文件名
        file_group = QGroupBox("输出文件")
        file_layout = QHBoxLayout(file_group)

        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("选择保存位置...")
        file_layout.addWidget(self.file_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)

        layout.addWidget(file_group)

        # 加工参数
        param_group = QGroupBox("加工参数")
        param_layout = QFormLayout(param_group)

        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(10, 200)
        self.speed_spin.setValue(int(self.params.print_speed))
        self.speed_spin.setSuffix(" mm/s")
        param_layout.addRow("打印速度:", self.speed_spin)

        self.first_speed_spin = QSpinBox()
        self.first_speed_spin.setRange(10, 100)
        self.first_speed_spin.setValue(int(self.params.first_layer_speed))
        self.first_speed_spin.setSuffix(" mm/s")
        param_layout.addRow("首层速度:", self.first_speed_spin)

        self.travel_speed_spin = QSpinBox()
        self.travel_speed_spin.setRange(100, 500)
        self.travel_speed_spin.setValue(int(self.params.travel_speed))
        self.travel_speed_spin.setSuffix(" mm/s")
        param_layout.addRow("空程速度:", self.travel_speed_spin)

        self.temp1_spin = QSpinBox()
        self.temp1_spin.setRange(180, 280)
        self.temp1_spin.setValue(self.params.extruder1_temp)
        self.temp1_spin.setSuffix(" °C")
        param_layout.addRow("喷头1温度:", self.temp1_spin)

        self.temp2_spin = QSpinBox()
        self.temp2_spin.setRange(180, 280)
        self.temp2_spin.setValue(self.params.extruder2_temp)
        self.temp2_spin.setSuffix(" °C")
        param_layout.addRow("喷头2温度:", self.temp2_spin)

        layout.addWidget(param_group)

        # 机台类型
        machine_group = QGroupBox("机台类型")
        machine_layout = QHBoxLayout(machine_group)

        self.machine_combo = QComboBox()
        self.machine_combo.addItems(["ZC-60", "ZC-80", "ZC-120"])
        self.machine_combo.setCurrentText(self.params.machine_type)
        machine_layout.addWidget(self.machine_combo)

        layout.addWidget(machine_group)

        # 其他选项
        options_group = QGroupBox("其他选项")
        options_layout = QVBoxLayout(options_group)

        self.alternate_check = QCheckBox("头尾交替打印")
        self.alternate_check.setChecked(self.params.alternate_direction)
        options_layout.addWidget(self.alternate_check)

        self.no_retract_check = QCheckBox("结束完成不回抽")
        self.no_retract_check.setChecked(self.params.no_retract_on_finish)
        options_layout.addWidget(self.no_retract_check)

        layout.addWidget(options_group)

        # 按钮
        btn_layout = QHBoxLayout()

        save_preset_btn = QPushButton("保存模板")
        save_preset_btn.clicked.connect(self._save_preset)
        btn_layout.addWidget(save_preset_btn)

        load_preset_btn = QPushButton("读取模板")
        load_preset_btn.clicked.connect(self._load_preset)
        btn_layout.addWidget(load_preset_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("primary-button")
        ok_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _browse_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存G-code文件",
            "", "G-code文件 (*.gcode);;所有文件 (*.*)"
        )
        if path:
            self.file_edit.setText(path)

    def _on_accept(self):
        if not self.file_edit.text():
            QMessageBox.warning(self, "警告", "请选择保存位置")
            return

        self.result_path = self.file_edit.text()
        self.accept()

    def get_params(self) -> GCodeParams:
        """获取参数"""
        return GCodeParams(
            print_speed=self.speed_spin.value(),
            first_layer_speed=self.first_speed_spin.value(),
            travel_speed=self.travel_speed_spin.value(),
            extruder1_temp=self.temp1_spin.value(),
            extruder2_temp=self.temp2_spin.value(),
            machine_type=self.machine_combo.currentText(),
            alternate_direction=self.alternate_check.isChecked(),
            no_retract_on_finish=self.no_retract_check.isChecked(),
        )
```

---

## 9. 快捷键定义

```python
SHORTCUTS = {
    # 文件
    "Ctrl+N": "新建项目",
    "Ctrl+O": "打开项目",
    "Ctrl+S": "保存项目",
    "Ctrl+Shift+S": "另存为",
    "Ctrl+I": "导入DXF",
    "Ctrl+E": "文件输出",
    "Alt+F4": "退出",

    # 编辑
    "Ctrl+Z": "撤销",
    "Ctrl+Y": "重做",
    "Ctrl+A": "全选",
    "Ctrl+G": "结合",
    "Ctrl+Shift+G": "打散",
    "Delete": "删除选中",

    # 视图
    "Ctrl+0": "适应窗口",
    "Ctrl++": "放大",
    "Ctrl+-": "缩小",
    "F11": "全屏",

    # 工具
    "F5": "计算路径",
    "Escape": "退出当前编辑模式",

    # 导航
    "Tab": "切换选项卡",
    "1": "切换到首页",
    "2": "切换到项目",
    "3": "切换到预览",
}
```

---

*文档版本：1.0*
*创建日期：2026-01-08*
