"""
SignMaker Slicer - 主窗口

应用程序的主窗口，包含：
- 菜单栏
- 工具栏
- 左侧项目面板
- 中央画布（2D/3D预览）
- 右侧参数面板
- 状态栏
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar, QLabel,
    QPushButton, QFrame, QScrollArea, QDockWidget, QFileDialog,
    QMessageBox, QSizePolicy, QDoubleSpinBox, QSpinBox, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QIcon, QKeySequence

from .theme import get_stylesheet, COLORS, LAYOUT
from .canvas_2d import Canvas2D
from .param_panel import ParamPanel
from .project_panel import ProjectPanel
from .preview_3d import Preview3D

from src.core import (
    DXFParser, SliceEngine, GCodeWriter,
    Contour, SliceParams, SliceResult
)
from src.core.stl_writer import STLWriter
from src.business.undo_manager import (
    UndoManager, Command, MoveCommand, RotateCommand, ScaleCommand,
    MirrorCommand, DeleteCommand, AddContoursCommand, ReplaceContoursCommand,
    TransformCommand
)


class MainWindow(QMainWindow):
    """SignMaker Slicer 主窗口"""

    # 信号
    project_loaded = Signal(str)  # 项目加载信号
    slice_completed = Signal(object)  # 切片完成信号

    def __init__(self):
        super().__init__()

        # 数据
        self.contours: List[Contour] = []
        self.slice_params = SliceParams()
        self.slice_result: Optional[SliceResult] = None
        self.current_file: Optional[str] = None

        # 核心组件
        self.dxf_parser = DXFParser()
        self.slice_engine = SliceEngine()

        # 撤销/重做管理器
        self.undo_manager = UndoManager(max_undo_levels=100)
        self._pending_transform: Optional[TransformCommand] = None

        # 初始化UI
        self._init_window()
        self._init_menubar()
        self._init_toolbar()
        self._init_transform_panel()  # 变换参数面板
        self._init_central_widget()
        self._init_statusbar()

        # 应用样式
        self.setStyleSheet(get_stylesheet())

    def _init_window(self):
        """初始化窗口属性"""
        self.setWindowTitle("SignMaker Slicer - 发光字切片软件")
        self.setMinimumSize(LAYOUT.window_min_width, LAYOUT.window_min_height)
        self.resize(1600, 900)

        # 设置窗口图标（如果存在）
        icon_path = Path(__file__).parent.parent.parent / "docs" / "images" / "MINGDA_logo.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _init_menubar(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # === 文件菜单 ===
        file_menu = menubar.addMenu("文件(&F)")

        # 新建项目
        new_action = QAction("新建项目", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)

        # 打开文件
        open_action = QAction("打开DXF/SVG...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # 保存项目
        save_action = QAction("保存项目", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)

        # 另存为
        save_as_action = QAction("另存为...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # 导出G-code
        export_gcode_action = QAction("导出G-code...", self)
        export_gcode_action.setShortcut(QKeySequence("Ctrl+E"))
        export_gcode_action.triggered.connect(self._on_export_gcode)
        file_menu.addAction(export_gcode_action)

        # 导出STL
        export_stl_action = QAction("导出STL...", self)
        export_stl_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_stl_action.triggered.connect(self._on_export_stl)
        file_menu.addAction(export_stl_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # === 编辑菜单 ===
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        select_all_action = QAction("全选", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        edit_menu.addAction(select_all_action)

        delete_action = QAction("删除", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        edit_menu.addAction(delete_action)

        # === 视图菜单 ===
        view_menu = menubar.addMenu("视图(&V)")

        view_2d_action = QAction("2D视图", self)
        view_2d_action.setShortcut(QKeySequence("1"))
        view_2d_action.triggered.connect(lambda: self._switch_view("2d"))
        view_menu.addAction(view_2d_action)

        view_3d_action = QAction("3D视图", self)
        view_3d_action.setShortcut(QKeySequence("2"))
        view_3d_action.triggered.connect(lambda: self._switch_view("3d"))
        view_menu.addAction(view_3d_action)

        view_menu.addSeparator()

        zoom_fit_action = QAction("适应画面", self)
        zoom_fit_action.setShortcut(QKeySequence("F"))
        zoom_fit_action.triggered.connect(self._on_zoom_fit)
        view_menu.addAction(zoom_fit_action)

        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        view_menu.addAction(zoom_out_action)

        # === 切片菜单 ===
        slice_menu = menubar.addMenu("切片(&S)")

        slice_action = QAction("开始切片", self)
        slice_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        slice_action.triggered.connect(self._on_slice)
        slice_menu.addAction(slice_action)

        preview_action = QAction("预览G-code", self)
        preview_action.setShortcut(QKeySequence("Ctrl+P"))
        slice_menu.addAction(preview_action)

        # === 帮助菜单 ===
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _init_toolbar(self):
        """初始化工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # 文件操作
        toolbar.addAction(self._create_action("新建", self._on_new_project, "Ctrl+N"))
        toolbar.addAction(self._create_action("打开", self._on_open_file, "Ctrl+O"))
        toolbar.addAction(self._create_action("保存", self._on_save_project, "Ctrl+S"))

        toolbar.addSeparator()

        # 编辑操作
        toolbar.addAction(self._create_action("撤销", self._on_undo, "Ctrl+Z"))
        toolbar.addAction(self._create_action("重做", self._on_redo, "Ctrl+Y"))

        toolbar.addSeparator()

        # 变换操作 - 点击切换工具并显示输入框
        self.move_action = self._create_action("移动", self._on_move_tool)
        self.rotate_action = self._create_action("旋转", self._on_rotate_tool)
        self.scale_action = self._create_action("缩放", self._on_scale_tool)
        self.move_action.setCheckable(True)
        self.rotate_action.setCheckable(True)
        self.scale_action.setCheckable(True)
        toolbar.addAction(self.move_action)
        toolbar.addAction(self.rotate_action)
        toolbar.addAction(self.scale_action)
        toolbar.addAction(self._create_action("镜像X", lambda: self._on_mirror("x")))
        toolbar.addAction(self._create_action("镜像Y", lambda: self._on_mirror("y")))

        toolbar.addSeparator()

        # 布尔操作
        toolbar.addAction(self._create_action("交集", self._on_intersection))
        toolbar.addAction(self._create_action("差集", self._on_difference))

        toolbar.addSeparator()

        # 组合操作
        toolbar.addAction(self._create_action("组合", self._on_group))
        toolbar.addAction(self._create_action("打散", self._on_ungroup))

        toolbar.addSeparator()

        # 视图
        self.view_2d_btn = self._create_action("2D", lambda: self._switch_view("2d"))
        self.view_3d_btn = self._create_action("3D", lambda: self._switch_view("3d"))
        toolbar.addAction(self.view_2d_btn)
        toolbar.addAction(self.view_3d_btn)

        # 弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # 切片按钮
        slice_btn = QPushButton("开始切片")
        slice_btn.setProperty("primary", True)
        slice_btn.clicked.connect(self._on_slice)
        toolbar.addWidget(slice_btn)

        # 导出G-code按钮
        export_btn = QPushButton("导出G-code")
        export_btn.setProperty("primary", True)
        export_btn.clicked.connect(self._on_export_gcode)
        toolbar.addWidget(export_btn)

    def _create_action(self, text: str, callback, shortcut: str = None) -> QAction:
        """创建Action"""
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        return action

    def _init_transform_panel(self):
        """初始化变换参数面板（显示在工具栏下方）"""
        # 创建浮动面板
        self.transform_panel = QFrame(self)
        self.transform_panel.setObjectName("transformPanel")
        self.transform_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.transform_panel.setStyleSheet("""
            #transformPanel {
                background-color: #1C2128;
                border: 1px solid #444C56;
                border-radius: 4px;
                padding: 8px;
            }
            QLabel {
                color: #8B949E;
                font-size: 12px;
            }
            QDoubleSpinBox {
                background-color: #0D1117;
                border: 1px solid #30363D;
                border-radius: 3px;
                color: #C9D1D9;
                padding: 4px 8px;
                min-width: 70px;
            }
            QDoubleSpinBox:focus {
                border-color: #58A6FF;
            }
        """)
        self.transform_panel.setVisible(False)

        # 面板布局
        panel_layout = QVBoxLayout(self.transform_panel)
        panel_layout.setContentsMargins(12, 8, 12, 8)
        panel_layout.setSpacing(8)

        # 标题行（可折叠）
        title_layout = QHBoxLayout()
        self.transform_title = QLabel("▼ World coordinates")
        self.transform_title.setStyleSheet("color: #58A6FF; font-weight: bold;")
        title_layout.addWidget(self.transform_title)

        # X Y Z 标签
        for label_text in ["X", "Y", "Z"]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #58A6FF; font-weight: bold; min-width: 70px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_layout.addWidget(lbl)

        title_layout.addWidget(QLabel(""))  # 占位
        panel_layout.addLayout(title_layout)

        # Position 行
        pos_layout = QHBoxLayout()
        self.transform_row_label = QLabel("Position")
        self.transform_row_label.setMinimumWidth(120)
        pos_layout.addWidget(self.transform_row_label)

        # X坐标
        self.transform_x = QDoubleSpinBox()
        self.transform_x.setRange(-10000, 10000)
        self.transform_x.setValue(0)
        self.transform_x.setDecimals(2)
        self.transform_x.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        pos_layout.addWidget(self.transform_x)

        # Y坐标
        self.transform_y = QDoubleSpinBox()
        self.transform_y.setRange(-10000, 10000)
        self.transform_y.setValue(0)
        self.transform_y.setDecimals(2)
        self.transform_y.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        pos_layout.addWidget(self.transform_y)

        # Z坐标
        self.transform_z = QDoubleSpinBox()
        self.transform_z.setRange(-10000, 10000)
        self.transform_z.setValue(0)
        self.transform_z.setDecimals(2)
        self.transform_z.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        pos_layout.addWidget(self.transform_z)

        # 单位标签
        unit_label = QLabel("mm")
        unit_label.setMinimumWidth(30)
        pos_layout.addWidget(unit_label)

        panel_layout.addLayout(pos_layout)

        # 当前变换模式
        self.current_transform_mode = None

        # 连接信号 - 当值改变时实时应用
        self.transform_x.valueChanged.connect(self._on_transform_value_changed)
        self.transform_y.valueChanged.connect(self._on_transform_value_changed)
        self.transform_z.valueChanged.connect(self._on_transform_value_changed)

    def _init_central_widget(self):
        """初始化中央区域"""
        # 主分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左侧项目面板 ===
        self.project_panel = ProjectPanel()
        self.project_panel.setMinimumWidth(180)
        self.project_panel.setMaximumWidth(300)
        main_splitter.addWidget(self.project_panel)

        # === 中央视图区域（2D/3D切换）===
        self.view_stack = QStackedWidget()

        # 2D画布
        self.canvas = Canvas2D()
        self.view_stack.addWidget(self.canvas)

        # 3D预览
        self.preview_3d = Preview3D()
        self.view_stack.addWidget(self.preview_3d)

        # 默认显示2D视图
        self.view_stack.setCurrentIndex(0)
        self.current_view = "2d"

        main_splitter.addWidget(self.view_stack)

        # === 右侧参数面板 ===
        self.param_panel = ParamPanel()
        self.param_panel.setMinimumWidth(280)
        self.param_panel.setMaximumWidth(400)
        main_splitter.addWidget(self.param_panel)

        # 设置分割比例
        main_splitter.setSizes([200, 900, 320])

        self.setCentralWidget(main_splitter)

        # 连接画布信号到撤销/重做系统
        self._connect_undo_signals()

    def _init_statusbar(self):
        """初始化状态栏"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)

        # 状态信息
        self.status_label = QLabel("就绪")
        statusbar.addWidget(self.status_label, 1)

        # 坐标显示
        self.coord_label = QLabel("X: 0.00  Y: 0.00")
        statusbar.addPermanentWidget(self.coord_label)

        # 缩放比例
        self.zoom_label = QLabel("100%")
        statusbar.addPermanentWidget(self.zoom_label)

    def _connect_undo_signals(self):
        """连接撤销/重做相关信号"""
        # 画布变换信号
        self.canvas.transform_started.connect(self._on_transform_started)
        self.canvas.transform_ended.connect(self._on_transform_ended)
        self.canvas.delete_requested.connect(self._on_delete_requested)

        # 撤销管理器信号
        self.undo_manager.can_undo_changed.connect(self._update_undo_actions)
        self.undo_manager.can_redo_changed.connect(self._update_undo_actions)
        self.undo_manager.command_executed.connect(
            lambda desc: self._update_status(f"执行: {desc}")
        )
        self.undo_manager.command_undone.connect(
            lambda desc: self._update_status(f"撤销: {desc}")
        )
        self.undo_manager.command_redone.connect(
            lambda desc: self._update_status(f"重做: {desc}")
        )

    def _update_undo_actions(self):
        """更新撤销/重做菜单项的状态"""
        # 这里可以更新菜单项的启用/禁用状态和文本
        pass

    def _on_transform_started(self, tool: str, indices: list):
        """变换开始时保存状态"""
        if indices:
            self._pending_transform = TransformCommand(
                self.contours, indices, f"{tool}"
            )

    def _on_transform_ended(self, tool: str, indices: list):
        """变换结束时创建命令"""
        if self._pending_transform and indices:
            # 获取变换增量
            delta = self.canvas.get_transform_delta()

            # 根据工具类型创建适当的命令
            if tool == "move" and (abs(delta['dx']) > 0.001 or abs(delta['dy']) > 0.001):
                # 撤销刚才的移动，然后创建一个可撤销的命令
                # 先反向移动回去
                for idx in indices:
                    if 0 <= idx < len(self.contours):
                        contour = self.contours[idx]
                        for p in contour.outer.points:
                            p.x -= delta['dx']
                            p.y -= delta['dy']
                        for hole in contour.holes:
                            for p in hole.points:
                                p.x -= delta['dx']
                                p.y -= delta['dy']

                # 创建命令并执行
                cmd = MoveCommand(self.contours, indices, delta['dx'], delta['dy'])
                self.undo_manager.push(cmd)
                self.canvas.update()

            elif tool == "rotate" and abs(delta['angle']) > 0.001:
                # 捕获变换后的状态
                self._pending_transform.description = f"旋转 {delta['angle']:.1f}°"
                self._pending_transform.capture_after()
                self.undo_manager.push(self._pending_transform, execute=False)

            elif tool == "scale" and abs(delta['scale'] - 1.0) > 0.001:
                # 捕获变换后的状态
                self._pending_transform.description = f"缩放 {delta['scale']*100:.0f}%"
                self._pending_transform.capture_after()
                self.undo_manager.push(self._pending_transform, execute=False)

        self._pending_transform = None

    def _on_delete_requested(self, indices: list):
        """处理删除请求"""
        if not indices:
            return

        # 创建删除命令
        cmd = DeleteCommand(self.contours, indices)
        self.undo_manager.push(cmd)

        # 清除选择
        self.canvas.selected_indices = []
        self.canvas.update()
        self.project_panel.update_contours(self.contours)

    # =========================================================================
    # 事件处理
    # =========================================================================

    def _on_new_project(self):
        """新建项目"""
        # 清空撤销历史
        self.undo_manager.clear()

        self.contours = []
        self.slice_result = None
        self.current_file = None
        self.canvas.set_contours([])
        self.setWindowTitle("SignMaker Slicer - 新项目")
        self._update_status("新建项目")

    def _on_open_file(self):
        """打开DXF/SVG文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开文件",
            "",
            "支持的文件 (*.dxf *.svg);;DXF文件 (*.dxf);;SVG文件 (*.svg);;所有文件 (*)"
        )

        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        """加载文件"""
        try:
            path = Path(file_path)
            if path.suffix.lower() == '.dxf':
                new_contours = self.dxf_parser.parse(file_path)
            else:
                QMessageBox.warning(self, "不支持的格式", f"暂不支持 {path.suffix} 格式")
                return

            # 创建替换轮廓命令（可撤销）
            cmd = ReplaceContoursCommand(
                self.contours, new_contours,
                f"加载 {path.name}"
            )
            self.undo_manager.push(cmd)

            self.current_file = file_path
            self.canvas.set_contours(self.contours)
            self.canvas.fit_view()
            self.project_panel.update_contours(self.contours)

            self.setWindowTitle(f"SignMaker Slicer - {path.name}")
            self._update_status(f"已加载: {path.name}, {len(self.contours)} 个轮廓")
            self.project_loaded.emit(file_path)

        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"无法加载文件:\n{e}")

    def _on_save_project(self):
        """保存项目"""
        if not self.current_file:
            self._on_save_as()
        else:
            self._save_project(self.current_file)

    def _on_save_as(self):
        """另存为"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存项目",
            "",
            "SignMaker项目 (*.smp);;所有文件 (*)"
        )
        if file_path:
            self._save_project(file_path)

    def _save_project(self, file_path: str):
        """保存项目到文件"""
        # TODO: 实现项目保存
        self._update_status(f"项目已保存: {Path(file_path).name}")

    def _on_export_gcode(self):
        """导出G-code"""
        if not self.slice_result:
            QMessageBox.information(self, "提示", "请先进行切片")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出G-code",
            "",
            "G-code文件 (*.gcode);;所有文件 (*)"
        )

        if file_path:
            try:
                params = self.param_panel.get_params()
                writer = GCodeWriter(params.gcode)
                writer.write(self.slice_result, file_path, params)
                self._update_status(f"G-code已导出: {Path(file_path).name}")
                QMessageBox.information(self, "导出成功", f"G-code已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"无法导出G-code:\n{e}")

    def _on_export_stl(self):
        """导出STL"""
        if not self.slice_result:
            QMessageBox.information(self, "提示", "请先进行切片")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出STL",
            "",
            "STL文件 (*.stl);;所有文件 (*)"
        )

        if file_path:
            try:
                # 获取当前参数
                params = self.param_panel.get_params()
                writer = STLWriter(wall_thickness=params.shell.wall_thickness)
                # 传递轮廓和参数用于生成包边
                writer.write(
                    self.slice_result, file_path,
                    contours=self.contours, params=params
                )
                self._update_status(f"STL已导出: {Path(file_path).name}")
                QMessageBox.information(self, "导出成功", f"STL已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"无法导出STL:\n{e}")

    def _on_undo(self):
        """撤销"""
        if self.undo_manager.can_undo:
            self.undo_manager.undo()
            self.canvas.update()
            self.project_panel.update_contours(self.contours)
        else:
            self._update_status("没有可撤销的操作")

    def _on_redo(self):
        """重做"""
        if self.undo_manager.can_redo:
            self.undo_manager.redo()
            self.canvas.update()
            self.project_panel.update_contours(self.contours)
        else:
            self._update_status("没有可重做的操作")

    def _on_slice(self):
        """执行切片"""
        if not self.contours:
            QMessageBox.information(self, "提示", "请先导入DXF文件")
            return

        try:
            self._update_status("正在切片...")
            QApplication.processEvents()

            # 获取参数
            params = self.param_panel.get_params()

            # 执行切片
            self.slice_result = self.slice_engine.slice(self.contours, params)

            # 更新3D预览
            if self.slice_result and self.slice_result.layers:
                self.preview_3d.set_layers(self.slice_result.layers)
                machine = params.machine
                self.preview_3d.set_bed_size(
                    machine.bed_width,
                    machine.bed_depth,
                    machine.bed_height
                )

            # 更新状态
            msg = (
                f"切片完成: {self.slice_result.total_layers} 层, "
                f"预计时间: {self.slice_result.estimated_time / 60:.1f} 分钟"
            )
            self._update_status(msg)

            self.slice_completed.emit(self.slice_result)

            # 弹窗提示切片成功，询问是否导出
            reply = QMessageBox.question(
                self,
                "切片完成",
                f"{msg}\n\n是否立即导出G-code?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._on_export_gcode()

        except Exception as e:
            QMessageBox.critical(self, "切片失败", f"切片过程中发生错误:\n{e}")
            self._update_status("切片失败")

    def _switch_view(self, view_type: str):
        """切换2D/3D视图"""
        if view_type == "2d":
            self.view_stack.setCurrentIndex(0)
            self.current_view = "2d"
        else:
            self.view_stack.setCurrentIndex(1)
            self.current_view = "3d"
            # 如果有切片结果，更新3D预览
            if self.slice_result and self.slice_result.layers:
                self.preview_3d.set_layers(self.slice_result.layers)
                # 更新打印平台尺寸
                machine = self.slice_params.machine
                self.preview_3d.set_bed_size(
                    machine.bed_width,
                    machine.bed_depth,
                    machine.bed_height
                )
        self._update_status(f"切换到{view_type.upper()}视图")

    def _on_zoom_fit(self):
        """适应画面"""
        self.canvas.fit_view()

    def _set_tool(self, tool: str):
        """设置当前工具"""
        self.canvas.set_tool(tool)
        self._update_status(f"工具: {tool}")

    def _on_move_tool(self):
        """激活移动工具"""
        self._activate_transform_tool("move")

    def _on_rotate_tool(self):
        """激活旋转工具"""
        self._activate_transform_tool("rotate")

    def _on_scale_tool(self):
        """激活缩放工具"""
        self._activate_transform_tool("scale")

    def _activate_transform_tool(self, mode: str):
        """激活变换工具并显示面板"""
        # 更新按钮状态
        self.move_action.setChecked(mode == "move")
        self.rotate_action.setChecked(mode == "rotate")
        self.scale_action.setChecked(mode == "scale")

        # 设置画布工具
        self.canvas.set_tool(mode)
        self.current_transform_mode = mode

        # 配置面板显示
        if mode == "move":
            self.transform_title.setText("▼ World coordinates")
            self.transform_row_label.setText("Position")
        elif mode == "rotate":
            self.transform_title.setText("▼ Rotation")
            self.transform_row_label.setText("Angle (°)")
        elif mode == "scale":
            self.transform_title.setText("▼ Scale")
            self.transform_row_label.setText("Scale (%)")

        # 更新面板中的值（显示选中轮廓的当前位置）
        self._update_transform_panel_values()

        # 显示面板并定位
        self._show_transform_panel()
        self._update_status(f"工具: {mode}")

    def _show_transform_panel(self):
        """显示变换面板并定位到工具栏下方"""
        # 获取移动按钮的位置
        toolbar = self.findChild(QToolBar, "主工具栏")
        if toolbar:
            # 定位到工具栏下方左侧
            toolbar_rect = toolbar.geometry()
            panel_x = toolbar_rect.left() + 10
            panel_y = toolbar_rect.bottom() + 5
        else:
            panel_x = 200
            panel_y = 80

        self.transform_panel.move(panel_x, panel_y)
        self.transform_panel.adjustSize()
        self.transform_panel.setVisible(True)
        self.transform_panel.raise_()

    def _update_transform_panel_values(self):
        """更新面板中显示的值"""
        if not self.canvas.selected_indices:
            self.transform_x.setValue(0)
            self.transform_y.setValue(0)
            self.transform_z.setValue(0)
            return

        # 获取选中轮廓的中心位置
        center = self.canvas._get_selection_center()

        # 阻止信号触发
        self.transform_x.blockSignals(True)
        self.transform_y.blockSignals(True)
        self.transform_z.blockSignals(True)

        if self.current_transform_mode == "move":
            self.transform_x.setValue(center.x())
            self.transform_y.setValue(center.y())
            self.transform_z.setValue(0)  # Z坐标暂时为0
        elif self.current_transform_mode == "rotate":
            self.transform_x.setValue(0)
            self.transform_y.setValue(0)
            self.transform_z.setValue(0)
        elif self.current_transform_mode == "scale":
            self.transform_x.setValue(100)
            self.transform_y.setValue(100)
            self.transform_z.setValue(100)

        self.transform_x.blockSignals(False)
        self.transform_y.blockSignals(False)
        self.transform_z.blockSignals(False)

    def _on_transform_value_changed(self):
        """当面板中的值改变时"""
        if not self.canvas.selected_indices:
            return

        mode = self.current_transform_mode
        if mode == "move":
            # 计算当前中心和目标位置的差值
            center = self.canvas._get_selection_center()
            target_x = self.transform_x.value()
            target_y = self.transform_y.value()
            dx = target_x - center.x()
            dy = target_y - center.y()
            if abs(dx) > 0.001 or abs(dy) > 0.001:
                self.canvas.move_selected(dx, dy)
                self._update_status(f"移动到: X={target_x:.2f}, Y={target_y:.2f}")

    def _close_transform_panel(self):
        """关闭变换面板"""
        self.transform_panel.setVisible(False)
        self.current_transform_mode = None
        self.move_action.setChecked(False)
        self.rotate_action.setChecked(False)
        self.scale_action.setChecked(False)
        self.canvas.set_tool("select")
        self._update_status("就绪")

    def _on_mirror(self, axis: str):
        """镜像"""
        if not self.canvas.selected_indices:
            QMessageBox.information(self, "提示", "请先选中轮廓")
            return

        # 获取选择中心
        center = self.canvas._get_selection_center()

        # 创建镜像命令
        cmd = MirrorCommand(
            self.contours,
            self.canvas.selected_indices,
            center.x(), center.y(),
            axis
        )
        self.undo_manager.push(cmd)

        self.canvas.update()
        self._update_status(f"镜像 {axis.upper()} 完成")

    def _on_intersection(self):
        """交集"""
        self.canvas.boolean_intersection()

    def _on_difference(self):
        """差集"""
        self.canvas.boolean_difference()

    def _on_group(self):
        """组合"""
        self.canvas.group_selected()

    def _on_ungroup(self):
        """打散"""
        self.canvas.ungroup_selected()

    def _on_about(self):
        """关于对话框"""
        QMessageBox.about(
            self,
            "关于 SignMaker Slicer",
            "<h3>SignMaker Slicer</h3>"
            "<p>专业发光字3D打印切片软件</p>"
            "<p>版本: 0.1.0 (开发版)</p>"
            "<p></p>"
            "<p>功能特性:</p>"
            "<ul>"
            "<li>DXF/SVG文件导入</li>"
            "<li>直边/斜边/异形边</li>"
            "<li>多色打印支持</li>"
            "<li>台阶/V槽</li>"
            "<li>防翘裙边</li>"
            "<li>连襟字</li>"
            "</ul>"
        )

    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_label.setText(message)


def main():
    """主程序入口"""
    app = QApplication(sys.argv)
    app.setApplicationName("SignMaker Slicer")
    app.setOrganizationName("MINGDA")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
