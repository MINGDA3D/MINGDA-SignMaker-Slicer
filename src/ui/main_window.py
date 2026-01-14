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
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QIcon, QKeySequence

from .theme import get_stylesheet, COLORS, LAYOUT
from .canvas_2d import Canvas2D
from .param_panel import ParamPanel
from .project_panel import ProjectPanel

from src.core import (
    DXFParser, SliceEngine, GCodeWriter,
    Contour, SliceParams, SliceResult
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

        # 初始化UI
        self._init_window()
        self._init_menubar()
        self._init_toolbar()
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

        # 变换操作
        toolbar.addAction(self._create_action("移动", lambda: self._set_tool("move")))
        toolbar.addAction(self._create_action("旋转", lambda: self._set_tool("rotate")))
        toolbar.addAction(self._create_action("缩放", lambda: self._set_tool("scale")))
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

    def _create_action(self, text: str, callback, shortcut: str = None) -> QAction:
        """创建Action"""
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        return action

    def _init_central_widget(self):
        """初始化中央区域"""
        # 主分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左侧项目面板 ===
        self.project_panel = ProjectPanel()
        self.project_panel.setMinimumWidth(180)
        self.project_panel.setMaximumWidth(300)
        main_splitter.addWidget(self.project_panel)

        # === 中央画布 ===
        self.canvas = Canvas2D()
        main_splitter.addWidget(self.canvas)

        # === 右侧参数面板 ===
        self.param_panel = ParamPanel()
        self.param_panel.setMinimumWidth(280)
        self.param_panel.setMaximumWidth(400)
        main_splitter.addWidget(self.param_panel)

        # 设置分割比例
        main_splitter.setSizes([200, 900, 320])

        self.setCentralWidget(main_splitter)

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

    # =========================================================================
    # 事件处理
    # =========================================================================

    def _on_new_project(self):
        """新建项目"""
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
                self.contours = self.dxf_parser.parse(file_path)
            else:
                QMessageBox.warning(self, "不支持的格式", f"暂不支持 {path.suffix} 格式")
                return

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

    def _on_undo(self):
        """撤销"""
        self._update_status("撤销")

    def _on_redo(self):
        """重做"""
        self._update_status("重做")

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

            # 更新状态
            self._update_status(
                f"切片完成: {self.slice_result.total_layers} 层, "
                f"预计时间: {self.slice_result.estimated_time / 60:.1f} 分钟"
            )

            self.slice_completed.emit(self.slice_result)

            # 可以切换到3D预览
            # self._switch_view("3d")

        except Exception as e:
            QMessageBox.critical(self, "切片失败", f"切片过程中发生错误:\n{e}")
            self._update_status("切片失败")

    def _switch_view(self, view_type: str):
        """切换2D/3D视图"""
        if view_type == "2d":
            self.canvas.set_view_mode("2d")
        else:
            self.canvas.set_view_mode("3d")
        self._update_status(f"切换到{view_type.upper()}视图")

    def _on_zoom_fit(self):
        """适应画面"""
        self.canvas.fit_view()

    def _set_tool(self, tool: str):
        """设置当前工具"""
        self.canvas.set_tool(tool)
        self._update_status(f"工具: {tool}")

    def _on_mirror(self, axis: str):
        """镜像"""
        self.canvas.mirror_selected(axis)

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
