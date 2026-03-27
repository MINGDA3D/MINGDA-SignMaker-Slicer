"""
MINGDA SignMaker - 主窗口

应用程序的主窗口，包含：
- 菜单栏
- 工具栏
- 左侧参数面板
- 中央画布（2D/3D预览）
- 右侧图形列表面板
- 状态栏
"""

from __future__ import annotations
from datetime import datetime
import sys
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar, QLabel,
    QPushButton, QFrame, QScrollArea, QDockWidget, QFileDialog,
    QMessageBox, QSizePolicy, QDoubleSpinBox, QSpinBox, QStackedWidget,
    QGraphicsDropShadowEffect, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QPixmap, QFont, QColor

from .theme import get_stylesheet, COLORS, LAYOUT
from .canvas_2d import Canvas2D
from .param_panel import ParamPanel

# 导入 Qt 资源文件
from resources import rc_resources  # noqa: F401
from .project_panel import ProjectPanel
from .preview_3d import Preview3D, Preview3DWidget
from .title_bar import TitleBar
from .canvas_toolbar import CanvasToolbar
from .home_page import HomePage
from .project_preview import (
    preview_pixmap_from_png_bytes,
    render_project_preview_pixmap,
    render_project_preview_png,
)
from .busy_dialog import run_async, WorkerThread

from src.core import (
    DXFParser, SVGParser, SliceEngine, GCodeWriter,
    Contour, SliceParams, SliceResult,
    DXFWriter, export_baseplate_dxf, export_panel_dxf
)
from src.core.types import resolve_shell_wall_thickness
from src.core.stl_writer import STLWriter
from src.business.undo_manager import (
    UndoManager, Command, MoveCommand, RotateCommand, ScaleCommand,
    MirrorCommand, DeleteCommand, AddContoursCommand, ReplaceContoursCommand,
    ReplaceSelectedContoursCommand,
    TransformCommand
)
from src.business.settings_manager import (
    SettingsManager, init_settings_manager, get_settings_manager
)
from src.business.project_manager import ProjectManager
from src.business.project_format import (
    get_project_info,
    load_project_contours,
    load_project_preview_png,
)
from src.i18n import (
    init_translation_manager, get_translation_manager,
    SUPPORTED_LANGUAGES, RTL_LANGUAGES
)

TUTORIAL_PLAYLIST_URL = (
    "https://youtube.com/playlist?list=PL1DS2s3xcuH3Nz3ZEUHmyzfmk7BfvvIt1"
    "&si=pYUuSv80w7LlNJGJ"
)


class MainWindow(QMainWindow):
    """MINGDA SignMaker 主窗口"""

    # 信号
    project_loaded = Signal(str)  # 项目加载信号
    slice_completed = Signal(object)  # 切片完成信号

    def __init__(self):
        super().__init__()

        # 初始化设置管理器
        self.settings_manager = init_settings_manager()

        # 初始化项目管理器
        self.project_manager = ProjectManager()

        # 数据
        self.contours: List[Contour] = []
        self.slice_params = SliceParams()
        self.slice_result: Optional[SliceResult] = None
        self._preview_mesh_worker: Optional[WorkerThread] = None
        self._preview_mesh_loading_key = None
        self.current_file: Optional[str] = None
        self._params_modified = False

        # 核心组件
        self.dxf_parser = DXFParser()
        self.svg_parser = SVGParser()
        self.slice_engine = SliceEngine()

        # 撤销/重做管理器
        self.undo_manager = UndoManager(max_undo_levels=100)
        self._pending_transform: Optional[TransformCommand] = None

        # 初始化UI
        self._init_window()
        self._init_title_bar()  # 自定义标题栏
        self._init_transform_panel()  # 变换参数面板
        self._init_central_widget()
        self._init_statusbar()

        # 隐藏默认菜单栏
        self.menuBar().setVisible(False)

        # 应用样式
        self.setStyleSheet(get_stylesheet())

        # 初始没有可直接导出的处理结果
        self._sync_export_stl_state()

        # 加载保存的参数
        self._load_saved_params()
        self._refresh_home_recent_projects()

    def _init_window(self):
        """初始化窗口属性"""
        self.setWindowTitle(self.tr("MINGDA SignMaker - LED Sign Letter Slicer"))
        self.setMinimumSize(LAYOUT.window_min_width, LAYOUT.window_min_height)
        self.resize(1600, 900)

        # 设置窗口图标
        self.setWindowIcon(QIcon(":/logos/logos/MINGDA_logo.png"))

    def _init_title_bar(self):
        """初始化自定义标题栏"""
        self.title_bar = TitleBar(self)

        # 创建标题栏工具栏（用于放置自定义标题栏）
        title_toolbar = QToolBar(self.tr("Title Bar"))
        title_toolbar.setObjectName("titleToolbar")
        title_toolbar.setMovable(False)
        title_toolbar.setFloatable(False)
        title_toolbar.setStyleSheet(f"""
            QToolBar#titleToolbar {{
                background-color: {COLORS.editor_toolbar_bg};
                border: none;
                border-bottom: 1px solid {COLORS.editor_toolbar_border};
                spacing: 0;
                padding: 0;
            }}
        """)
        title_toolbar.addWidget(self.title_bar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, title_toolbar)

        # 强制工具栏换行，让主工具栏显示在标题栏下方
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)

        # 连接标题栏信号
        self.title_bar.nav_changed.connect(self._on_nav_changed)
        self.title_bar.menu_action.connect(self._on_menu_action)
        self.title_bar.open_clicked.connect(self._on_open_file)
        self.title_bar.save_clicked.connect(self._on_save_project)
        self.title_bar.export_clicked.connect(self._on_show_export_menu)
        self.title_bar.undo_clicked.connect(self._on_undo)
        self.title_bar.redo_clicked.connect(self._on_redo)
        self.title_bar.slice_clicked.connect(self._on_slice)
        self.title_bar.export_stl_clicked.connect(self._on_export_stl)

    def _init_menubar(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # === 文件菜单 ===
        file_menu = menubar.addMenu(self.tr("File(&F)"))

        # 新建项目
        new_action = QAction(self.tr("New Project"), self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)

        # 打开文件
        open_action = QAction(self.tr("Open DXF/SVG..."), self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # 保存项目
        save_action = QAction(self.tr("Save Project"), self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)

        # 另存为
        save_as_action = QAction(self.tr("Save As..."), self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # 导出G-code (暂时屏蔽)
        # export_gcode_action = QAction(self.tr("Export G-code..."), self)
        # export_gcode_action.setShortcut(QKeySequence("Ctrl+E"))
        # export_gcode_action.triggered.connect(self._on_export_gcode)
        # file_menu.addAction(export_gcode_action)

        # 导出STL
        export_stl_action = QAction(self.tr("Export STL..."), self)
        export_stl_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_stl_action.triggered.connect(self._on_export_stl)
        file_menu.addAction(export_stl_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction(self.tr("Exit"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # === 编辑菜单 ===
        edit_menu = menubar.addMenu(self.tr("Edit(&E)"))

        undo_action = QAction(self.tr("Undo"), self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction(self.tr("Redo"), self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        select_all_action = QAction(self.tr("Select All"), self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        edit_menu.addAction(select_all_action)

        delete_action = QAction(self.tr("Delete"), self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        edit_menu.addAction(delete_action)

        # === 视图菜单 ===
        view_menu = menubar.addMenu(self.tr("View(&V)"))

        view_2d_action = QAction(self.tr("2D View"), self)
        view_2d_action.setShortcut(QKeySequence("1"))
        view_2d_action.triggered.connect(lambda: self._switch_view("2d"))
        view_menu.addAction(view_2d_action)

        view_3d_action = QAction(self.tr("3D View"), self)
        view_3d_action.setShortcut(QKeySequence("2"))
        view_3d_action.triggered.connect(lambda: self._switch_view("3d"))
        view_menu.addAction(view_3d_action)

        view_menu.addSeparator()

        zoom_fit_action = QAction(self.tr("Fit to Window"), self)
        zoom_fit_action.setShortcut(QKeySequence("F"))
        zoom_fit_action.triggered.connect(self._on_zoom_fit)
        view_menu.addAction(zoom_fit_action)

        zoom_in_action = QAction(self.tr("Zoom In"), self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction(self.tr("Zoom Out"), self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        view_menu.addAction(zoom_out_action)

        # === 处理菜单 ===
        slice_menu = menubar.addMenu(self.tr("Process(&P)"))

        slice_action = QAction(self.tr("Start Processing"), self)
        slice_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        slice_action.triggered.connect(self._on_slice)
        slice_menu.addAction(slice_action)

        preview_action = QAction(self.tr("Preview G-code"), self)
        preview_action.setShortcut(QKeySequence("Ctrl+P"))
        slice_menu.addAction(preview_action)

        # === 帮助菜单 ===
        help_menu = menubar.addMenu(self.tr("Help(&H)"))

        about_action = QAction(self.tr("About"), self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

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
                min-width: 80px;
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

        # 标题行
        title_layout = QHBoxLayout()
        self.transform_title = QLabel("▼ Position")
        self.transform_title.setStyleSheet("color: #58A6FF; font-weight: bold;")
        title_layout.addWidget(self.transform_title)
        title_layout.addStretch()
        panel_layout.addLayout(title_layout)

        # === Position 行（移动模式）===
        self.pos_widget = QWidget()
        pos_layout = QHBoxLayout(self.pos_widget)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        pos_layout.setSpacing(12)

        # X坐标
        x_layout = QHBoxLayout()
        x_layout.setSpacing(4)
        x_label = QLabel("X")
        x_label.setStyleSheet("color: #58A6FF; font-weight: bold;")
        x_layout.addWidget(x_label)
        self.transform_x = QDoubleSpinBox()
        self.transform_x.setRange(-10000, 10000)
        self.transform_x.setValue(0)
        self.transform_x.setDecimals(2)
        self.transform_x.setSuffix(" mm")
        self.transform_x.setKeyboardTracking(False)
        x_layout.addWidget(self.transform_x)
        pos_layout.addLayout(x_layout)

        # Y坐标
        y_layout = QHBoxLayout()
        y_layout.setSpacing(4)
        y_label = QLabel("Y")
        y_label.setStyleSheet("color: #58A6FF; font-weight: bold;")
        y_layout.addWidget(y_label)
        self.transform_y = QDoubleSpinBox()
        self.transform_y.setRange(-10000, 10000)
        self.transform_y.setValue(0)
        self.transform_y.setDecimals(2)
        self.transform_y.setSuffix(" mm")
        self.transform_y.setKeyboardTracking(False)
        y_layout.addWidget(self.transform_y)
        pos_layout.addLayout(y_layout)

        panel_layout.addWidget(self.pos_widget)

        # === Rotation 行（旋转模式）===
        self.rot_widget = QWidget()
        rot_layout = QHBoxLayout(self.rot_widget)
        rot_layout.setContentsMargins(0, 0, 0, 0)
        rot_layout.setSpacing(4)

        rot_label = QLabel(self.tr("Angle"))
        rot_label.setStyleSheet("color: #58A6FF; font-weight: bold;")
        rot_layout.addWidget(rot_label)
        self.transform_angle = QDoubleSpinBox()
        self.transform_angle.setRange(-360, 360)
        self.transform_angle.setValue(0)
        self.transform_angle.setDecimals(2)
        self.transform_angle.setSuffix(" °")
        self.transform_angle.setWrapping(True)
        self.transform_angle.setKeyboardTracking(False)
        rot_layout.addWidget(self.transform_angle)
        rot_layout.addStretch()

        self.rot_widget.setVisible(False)
        panel_layout.addWidget(self.rot_widget)

        # === Scale 区域（缩放模式）===
        self.scale_widget = QWidget()
        scale_main_layout = QVBoxLayout(self.scale_widget)
        scale_main_layout.setContentsMargins(0, 0, 0, 0)
        scale_main_layout.setSpacing(6)

        # Scale 行（百分比）
        scale_pct_layout = QHBoxLayout()
        scale_pct_layout.setSpacing(8)
        scale_label = QLabel(self.tr("Scale"))
        scale_label.setStyleSheet("color: #8B949E; min-width: 36px;")
        scale_pct_layout.addWidget(scale_label)

        # X%
        sx_layout = QHBoxLayout()
        sx_layout.setSpacing(4)
        sx_label = QLabel("X")
        sx_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")
        sx_layout.addWidget(sx_label)
        self.scale_x_pct = QDoubleSpinBox()
        self.scale_x_pct.setRange(1, 10000)
        self.scale_x_pct.setValue(100)
        self.scale_x_pct.setDecimals(2)
        self.scale_x_pct.setSuffix(" %")
        self.scale_x_pct.setKeyboardTracking(False)
        sx_layout.addWidget(self.scale_x_pct)
        scale_pct_layout.addLayout(sx_layout)

        # Y%
        sy_layout = QHBoxLayout()
        sy_layout.setSpacing(4)
        sy_label = QLabel("Y")
        sy_label.setStyleSheet("color: #69DB7C; font-weight: bold;")
        sy_layout.addWidget(sy_label)
        self.scale_y_pct = QDoubleSpinBox()
        self.scale_y_pct.setRange(1, 10000)
        self.scale_y_pct.setValue(100)
        self.scale_y_pct.setDecimals(2)
        self.scale_y_pct.setSuffix(" %")
        self.scale_y_pct.setKeyboardTracking(False)
        sy_layout.addWidget(self.scale_y_pct)
        scale_pct_layout.addLayout(sy_layout)

        scale_main_layout.addLayout(scale_pct_layout)

        # Size 行（绝对尺寸）
        size_layout = QHBoxLayout()
        size_layout.setSpacing(8)
        size_label = QLabel(self.tr("Size"))
        size_label.setStyleSheet("color: #8B949E; min-width: 36px;")
        size_layout.addWidget(size_label)

        # W (宽)
        sw_layout = QHBoxLayout()
        sw_layout.setSpacing(4)
        sw_label = QLabel("W")
        sw_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")
        sw_layout.addWidget(sw_label)
        self.scale_w = QDoubleSpinBox()
        self.scale_w.setRange(0.01, 100000)
        self.scale_w.setValue(100)
        self.scale_w.setDecimals(2)
        self.scale_w.setSuffix(" mm")
        self.scale_w.setKeyboardTracking(False)
        sw_layout.addWidget(self.scale_w)
        size_layout.addLayout(sw_layout)

        # H (高)
        sh_layout = QHBoxLayout()
        sh_layout.setSpacing(4)
        sh_label = QLabel("H")
        sh_label.setStyleSheet("color: #69DB7C; font-weight: bold;")
        sh_layout.addWidget(sh_label)
        self.scale_h = QDoubleSpinBox()
        self.scale_h.setRange(0.01, 100000)
        self.scale_h.setValue(100)
        self.scale_h.setDecimals(2)
        self.scale_h.setSuffix(" mm")
        self.scale_h.setKeyboardTracking(False)
        sh_layout.addWidget(self.scale_h)
        size_layout.addLayout(sh_layout)

        scale_main_layout.addLayout(size_layout)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #30363D;")
        scale_main_layout.addWidget(separator)

        # Uniform Scale 复选框
        self.uniform_scale_cb = QCheckBox(self.tr("Uniform Scale"))
        self.uniform_scale_cb.setChecked(True)
        self.uniform_scale_cb.setStyleSheet("""
            QCheckBox {
                color: #8B949E;
                font-size: 12px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #444C56;
                border-radius: 3px;
                background-color: #0D1117;
            }
            QCheckBox::indicator:checked {
                background-color: #58A6FF;
                border-color: #58A6FF;
            }
        """)
        scale_main_layout.addWidget(self.uniform_scale_cb)

        self.scale_widget.setVisible(False)
        panel_layout.addWidget(self.scale_widget)

        # 记录原始尺寸（用于百分比↔尺寸换算）
        self._scale_original_w = None
        self._scale_original_h = None
        self._scale_pct_x = 100.0  # 当前活跃轮廓的缩放百分比
        self._scale_pct_y = 100.0
        self._scale_updating = False  # 防止递归更新
        # 每个轮廓独立存储的变换状态（参考OrcaSlicer per-ModelInstance设计）
        # key: id(contour), value: {angle, scale_pct_x, scale_pct_y, original_w, original_h}
        self._contour_transforms: dict = {}
        self._current_selected_id: Optional[int] = None

        # 提示文本
        self.transform_hint = QLabel(self.tr("Arrow keys: 1mm, Shift+Arrow: 10mm"))
        self.transform_hint.setStyleSheet("color: #6E7681; font-size: 10px;")
        panel_layout.addWidget(self.transform_hint)

        # 当前变换模式
        self.current_transform_mode = None

        # 连接信号 - 当值改变时实时应用
        self.transform_x.editingFinished.connect(self._on_transform_value_changed)
        self.transform_y.editingFinished.connect(self._on_transform_value_changed)
        self.transform_angle.editingFinished.connect(self._on_transform_value_changed)
        self.scale_x_pct.editingFinished.connect(lambda: self._on_scale_pct_changed(self.scale_x_pct))
        self.scale_y_pct.editingFinished.connect(lambda: self._on_scale_pct_changed(self.scale_y_pct))
        self.scale_w.editingFinished.connect(lambda: self._on_scale_size_changed(self.scale_w))
        self.scale_h.editingFinished.connect(lambda: self._on_scale_size_changed(self.scale_h))

    def _init_central_widget(self):
        """初始化中央区域"""
        # === 主视图堆栈（首页 / 编辑器）===
        self.main_stack = QStackedWidget()

        # === 首页 ===
        self.home_page = HomePage()
        self.home_page.new_project_clicked.connect(self._on_new_project)
        self.home_page.open_file_clicked.connect(self._on_open_file)
        self.home_page.recent_project_clicked.connect(self._open_recent_project)

        self.home_scroll = QScrollArea()
        self.home_scroll.setObjectName("homeScrollArea")
        self.home_scroll.setWidgetResizable(True)
        self.home_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.home_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.home_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.home_scroll.setStyleSheet(f"""
            QScrollArea#homeScrollArea {{
                background-color: {COLORS.editor_canvas_bg};
                border: none;
            }}
            QScrollArea#homeScrollArea > QWidget > QWidget {{
                background-color: {COLORS.editor_canvas_bg};
            }}
        """)
        self.home_scroll.setWidget(self.home_page)
        self.main_stack.addWidget(self.home_scroll)  # index 0

        # === 编辑器视图（分割器）===
        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左侧参数面板 ===
        self.param_panel = ParamPanel()
        self.param_panel.setMinimumWidth(280)
        self.param_panel.setMaximumWidth(400)
        self.param_panel.params_changed.connect(self._on_params_changed)
        self.editor_splitter.addWidget(self.param_panel)

        # === 中央视图区域（工具栏 + 2D/3D视图）===
        center_container = QWidget()
        center_container.setObjectName("editorCenterContainer")
        center_container.setStyleSheet(f"""
            QWidget#editorCenterContainer {{
                background-color: {COLORS.editor_canvas_bg};
                border-left: 1px solid {COLORS.editor_canvas_frame};
                border-right: 1px solid {COLORS.editor_canvas_frame};
            }}
        """)
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # 嵌入式工具栏
        self.canvas_toolbar = CanvasToolbar()
        center_layout.addWidget(self.canvas_toolbar)

        # 视图堆栈（2D/3D切换）
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

        center_layout.addWidget(self.view_stack)
        self.editor_splitter.addWidget(center_container)

        # === 右侧图形列表面板 ===
        self.project_panel = ProjectPanel()
        self.project_panel.setMinimumWidth(180)
        self.project_panel.setMaximumWidth(300)
        self.project_panel.import_clicked.connect(self._on_open_file)
        self.project_panel.contour_deleted.connect(self._on_contour_deleted)
        self.project_panel.selection_changed.connect(
            self._on_project_panel_selection_changed
        )
        self.editor_splitter.addWidget(self.project_panel)

        # 设置分割比例
        self.editor_splitter.setSizes([320, 900, 200])

        self.main_stack.addWidget(self.editor_splitter)  # index 1

        # 默认显示首页
        self.main_stack.setCurrentIndex(0)
        self.current_main_view = "home"

        self.setCentralWidget(self.main_stack)
        self._sync_canvas_toolbar_visibility()

        # 连接画布工具栏信号
        self._connect_canvas_toolbar_signals()

        # 连接画布信号到撤销/重做系统
        self._connect_undo_signals()

    def _connect_canvas_toolbar_signals(self):
        """连接画布工具栏信号"""
        self.canvas_toolbar.move_clicked.connect(self._on_move_tool)
        self.canvas_toolbar.rotate_clicked.connect(self._on_rotate_tool)
        self.canvas_toolbar.scale_clicked.connect(self._on_scale_tool)
        self.canvas_toolbar.mirror_x_clicked.connect(lambda: self._on_mirror("x"))
        self.canvas_toolbar.mirror_y_clicked.connect(lambda: self._on_mirror("y"))
        self.canvas_toolbar.intersection_clicked.connect(self._on_intersection)
        self.canvas_toolbar.difference_clicked.connect(self._on_difference)
        self.canvas_toolbar.group_clicked.connect(self._on_group)
        self.canvas_toolbar.ungroup_clicked.connect(self._on_ungroup)
        self.canvas_toolbar.text_clicked.connect(self._on_text)

    def _init_statusbar(self):
        """初始化状态栏"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)

        # 状态信息
        self.status_label = QLabel(self.tr("Ready"))
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
        self.canvas.contour_selected.connect(self._on_contour_selected)
        self.canvas.selection_cleared.connect(self._on_selection_cleared)
        self.canvas.contours_modified.connect(self._on_contours_modified)

        # 右键菜单信号
        self.canvas.mirror_requested.connect(self._on_mirror)
        self.canvas.fit_view_requested.connect(self.canvas.fit_view)
        self.canvas.reset_view_requested.connect(self.canvas._init_view)
        self.canvas.reset_view_requested.connect(self.canvas.update)

        # 撤销管理器信号
        self.undo_manager.can_undo_changed.connect(self._update_undo_actions)
        self.undo_manager.can_redo_changed.connect(self._update_undo_actions)
        self.undo_manager.command_executed.connect(
            lambda desc: self._update_status(self.tr("Executed: ") + desc)
        )
        self.undo_manager.command_undone.connect(
            lambda desc: self._update_status(self.tr("Undone: ") + desc)
        )
        self.undo_manager.command_redone.connect(
            lambda desc: self._update_status(self.tr("Redone: ") + desc)
        )

    def _update_undo_actions(self):
        """更新撤销/重做菜单项的状态"""
        # 这里可以更新菜单项的启用/禁用状态和文本
        pass

    def _sync_export_stl_state(self):
        """根据当前处理结果同步导出 STL 按钮状态。"""
        if hasattr(self, "title_bar") and hasattr(self.title_bar, "btn_export_stl"):
            self.title_bar.btn_export_stl.setEnabled(True)

    def _invalidate_processed_result(self):
        """清除当前处理结果，要求重新点击 Process。"""
        had_processed_output = (
            self.slice_result is not None
            or self._preview_mesh_loading_key is not None
        )
        self.slice_result = None
        if had_processed_output:
            self._reset_preview_loading_state()
        self._sync_export_stl_state()

    def _on_params_changed(self):
        """参数变化后，当前处理结果失效。"""
        self.slice_params = self.param_panel.get_params()
        self._sync_canvas_platform_size(self.slice_params)
        self._invalidate_processed_result()
        if self.contours or self.current_file or self.project_manager.current_project is not None:
            self._params_modified = True
        self.canvas.update()

    def _has_unsaved_project_changes(self) -> bool:
        """Return whether the current project has unsaved changes."""
        return self.undo_manager.is_modified or self._params_modified

    def _set_project_save_point(self) -> None:
        """Mark the current project state as saved."""
        self.undo_manager.set_save_point()
        self._params_modified = False
        self.project_manager.is_modified = False

    def _confirm_close_with_unsaved_changes(self) -> QMessageBox.StandardButton:
        """Ask the user how to handle unsaved changes before closing."""
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle(self.tr("Exit"))
        message_box.setText(
            self.tr("The current project has unsaved changes. Do you want to save before exiting?")
        )
        save_button = message_box.addButton(
            self.tr("Save"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        discard_button = message_box.addButton(
            self.tr("Discard"),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel_button = message_box.addButton(
            self.tr("Cancel"),
            QMessageBox.ButtonRole.RejectRole,
        )
        message_box.setDefaultButton(save_button)
        message_box.setEscapeButton(cancel_button)
        message_box.exec()

        clicked_button = message_box.clickedButton()
        if clicked_button is save_button:
            return QMessageBox.StandardButton.Save
        if clicked_button is discard_button:
            return QMessageBox.StandardButton.Discard
        return QMessageBox.StandardButton.Cancel

    def _handle_unsaved_changes_before_close(self) -> bool:
        """Handle unsaved project changes before the window closes."""
        if not self._has_unsaved_project_changes():
            return True

        choice = self._confirm_close_with_unsaved_changes()
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Discard:
            return True

        if self.current_file and self.current_file.lower().endswith(".smp"):
            return self._save_project(self.current_file)

        self._on_save_as()
        return not self._has_unsaved_project_changes()

    def _sync_canvas_platform_size(self, params: Optional[SliceParams] = None) -> None:
        """å°†ç”»å¸ƒå¹³å°å°ºå¯¸åŒæ­¥åˆ°å½“å‰æœºå™¨å‚æ•°ã€‚"""
        target_params = params or self.slice_params
        machine = target_params.machine
        width = float(machine.bed_width)
        height = float(machine.bed_depth)

        if (
            abs(self.canvas.platform_width - width) > 1e-6
            or abs(self.canvas.platform_height - height) > 1e-6
        ):
            self.canvas.set_platform_size(width, height, self.canvas.grid_spacing)

    def _command_requires_reprocess(self, command: Optional[Command]) -> bool:
        """判断撤销/重做的命令是否会影响导出的 STL。"""
        if command is None:
            return False

        if isinstance(
            command,
            (
                MoveCommand,
                RotateCommand,
                ScaleCommand,
                MirrorCommand,
                DeleteCommand,
                AddContoursCommand,
                ReplaceContoursCommand,
                ReplaceSelectedContoursCommand,
            ),
        ):
            return True

        if isinstance(command, TransformCommand):
            return command.description not in {self.tr("Group"), self.tr("Ungroup")}

        return False

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
                # 更新所有被旋转轮廓的累计角度
                self._update_selected_rotation(delta['angle'])
                self.canvas._cumulative_angle += delta['angle']
                self._update_transform_panel_values()

            elif tool == "scale" and abs(delta['scale'] - 1.0) > 0.001:
                # 捕获变换后的状态
                self._pending_transform.description = f"缩放 {delta['scale']*100:.0f}%"
                self._pending_transform.capture_after()
                self.undo_manager.push(self._pending_transform, execute=False)
                # 更新所有被缩放轮廓的累计百分比
                self._update_selected_scale(delta['scale'], delta['scale'])
                self._scale_pct_x *= delta['scale']
                self._scale_pct_y *= delta['scale']

            if (
                abs(delta['dx']) > 0.001
                or abs(delta['dy']) > 0.001
                or abs(delta['angle']) > 0.001
                or abs(delta['scale'] - 1.0) > 0.001
            ):
                self._invalidate_processed_result()

        self._pending_transform = None

    def _on_delete_requested(self, indices: list):
        """处理删除请求"""
        if not indices:
            return

        # 清除被删除轮廓的变换状态
        for idx in indices:
            if 0 <= idx < len(self.contours):
                cid = id(self.contours[idx])
                self._contour_transforms.pop(cid, None)
                if self._current_selected_id == cid:
                    self._current_selected_id = None

        # 创建删除命令
        cmd = DeleteCommand(self.contours, indices)
        self.undo_manager.push(cmd)
        self._invalidate_processed_result()

        # 清除选择
        self.canvas.set_selected_indices([])
        self.project_panel.update_contours(self.contours)

    def _on_contour_deleted(self, index: int):
        """处理项目面板的删除请求"""
        self._on_delete_requested([index])

    def _get_selected_contour_id(self) -> Optional[int]:
        """获取当前选中轮廓的唯一ID（单选时使用 object id）"""
        if self.canvas.selected_indices and len(self.canvas.selected_indices) == 1:
            idx = self.canvas.selected_indices[0]
            if 0 <= idx < len(self.contours):
                return id(self.contours[idx])
        return None

    def _get_contour_state(self, contour_id: int) -> dict:
        """获取或创建指定轮廓的变换状态"""
        if contour_id not in self._contour_transforms:
            self._contour_transforms[contour_id] = {
                'angle': 0.0,
                'scale_pct_x': 100.0,
                'scale_pct_y': 100.0,
                'original_w': None,
                'original_h': None,
            }
        return self._contour_transforms[contour_id]

    def _update_selected_rotation(self, delta_angle: float):
        """更新所有选中轮廓的累计旋转角度（每个轮廓独立跟踪）"""
        for idx in self.canvas.selected_indices:
            if 0 <= idx < len(self.contours):
                state = self._get_contour_state(id(self.contours[idx]))
                state['angle'] += delta_angle

    def _update_selected_scale(self, sx: float, sy: float):
        """更新所有选中轮廓的累计缩放百分比（每个轮廓独立跟踪）"""
        for idx in self.canvas.selected_indices:
            if 0 <= idx < len(self.contours):
                state = self._get_contour_state(id(self.contours[idx]))
                state['scale_pct_x'] *= sx
                state['scale_pct_y'] *= sy

    def _restore_contour_transform(self, contour_id: Optional[int]):
        """从 per-contour 字典恢复指定轮廓的变换状态到显示变量"""
        if contour_id is not None and contour_id in self._contour_transforms:
            state = self._contour_transforms[contour_id]
            self.canvas._cumulative_angle = state['angle']
            self._scale_pct_x = state['scale_pct_x']
            self._scale_pct_y = state['scale_pct_y']
            self._scale_original_w = state['original_w']
            self._scale_original_h = state['original_h']
        else:
            self.canvas._cumulative_angle = 0.0
            self._scale_pct_x = 100.0
            self._scale_pct_y = 100.0
            self._scale_original_w = None
            self._scale_original_h = None
        self._current_selected_id = contour_id

    def _sync_active_transform_tool(self) -> None:
        """Keep the toolbar and canvas tool in sync with the active transform mode."""
        active_mode = (
            self.current_transform_mode
            if self.canvas.selected_indices
            and self.current_transform_mode in {"move", "rotate", "scale"}
            else None
        )

        if active_mode is None:
            self.canvas_toolbar.clear_tool()
            self.canvas.set_tool("select")
            return

        self.canvas_toolbar._set_tool_checked(active_mode)
        self.canvas.set_tool(active_mode)

    def _on_contour_selected(self, index: int):
        """当选中轮廓时显示位置面板"""
        if self.canvas.selected_indices:
            self.project_panel.set_selected_indices(self.canvas.selected_indices)
            # 恢复新选中轮廓的变换状态
            new_id = self._get_selected_contour_id()
            self._restore_contour_transform(new_id)
            if self.current_transform_mode in ("rotate", "scale"):
                if self.current_transform_mode == "scale" and self._scale_original_w is None:
                    self._capture_original_size()
                # 保持当前工具模式不变
                self._sync_active_transform_tool()
                self._update_transform_panel_values()
                self._show_transform_panel()
            else:
                # 默认显示位置面板
                self.transform_title.setText(self.tr("Position"))
                self.current_transform_mode = "move"
                self.pos_widget.setVisible(True)
                self.rot_widget.setVisible(False)
                self.scale_widget.setVisible(False)
                self.transform_hint.setText(self.tr("Arrow keys: 1mm, Shift+Arrow: 10mm"))
                self._sync_active_transform_tool()
                self._update_transform_panel_values()
                self._show_transform_panel()
        else:
            # 取消选择时隐藏面板
            self.project_panel.clear_selection()
            self._close_transform_panel()

    def _on_contours_modified(self):
        """当轮廓被修改时更新面板"""
        if self._pending_transform is None and not self.canvas.is_transforming:
            self._invalidate_processed_result()
        if self.canvas.selected_indices and self.transform_panel.isVisible():
            # 拖拽旋转过程中不更新面板，等拖拽结束后再更新
            if self.canvas.is_transforming and self.current_transform_mode == "rotate":
                return
            self._update_transform_panel_values()

    def _on_selection_cleared(self):
        """当选择被清除时隐藏面板"""
        self.project_panel.clear_selection()
        self._current_selected_id = None
        self._close_transform_panel()

    def _on_project_panel_selection_changed(self, indices: List[int]):
        """当右侧图形列表变化时同步到画布。"""
        self._apply_contour_selection(indices)

    def _apply_contour_selection(self, indices: List[int]):
        """同步画布和项目面板的选中状态。"""
        valid_indices = self.canvas.expand_indices_to_groups(indices)
        active_index = valid_indices[0] if valid_indices else None
        self.canvas.set_selected_indices(valid_indices, active_index=active_index)

    # =========================================================================
    # 事件处理
    # =========================================================================

    def _reset_preview_loading_state(self):
        """Clear any pending non-blocking preview load indicator/state."""
        self._preview_mesh_loading_key = None
        self._preview_mesh_worker = None
        if hasattr(self, "preview_3d"):
            self.preview_3d.set_loading(False)
            self.preview_3d.clear_scene()

    def _prepare_preview_3d(self):
        """Ensure the 3D preview scene is ready without blocking the UI."""
        if not self.slice_result or not self.slice_result.layers:
            return

        machine = self.slice_params.machine
        self.preview_3d.set_bed_size(
            machine.bed_width,
            machine.bed_depth,
            machine.bed_height,
        )

        target_result = self.slice_result
        target_contours = list(self.contours)
        target_params = self.slice_params
        loading_key = Preview3DWidget._get_mesh_cache_key(
            target_result,
            target_contours,
            target_params,
        )

        if self.preview_3d.has_cached_mesh_parts(target_result, target_contours, target_params):
            self.preview_3d.set_loading(False)
            return

        # Avoid synchronous layer processing on first open; show the page immediately.
        self.preview_3d.clear_scene()
        self.preview_3d.set_layer_count(len(target_result.layers), target_result.layers)

        if self._preview_mesh_loading_key == loading_key:
            self.preview_3d.set_loading(True, self.tr("Loading 3D preview..."))
            return

        def build_preview_mesh():
            return Preview3DWidget.build_mesh_parts_for_result(
                target_result,
                target_contours,
                target_params,
            )

        worker = WorkerThread(build_preview_mesh, self)
        self._preview_mesh_worker = worker
        self._preview_mesh_loading_key = loading_key
        self.preview_3d.set_loading(True, self.tr("Loading 3D preview..."))

        def on_success(mesh_parts):
            if self._preview_mesh_loading_key != loading_key:
                return
            self.preview_3d.set_prebuilt_mesh_parts(
                target_result,
                mesh_parts,
                target_contours,
                target_params,
            )
            self.preview_3d.set_loading(False)
            self._preview_mesh_loading_key = None
            self._preview_mesh_worker = None

        def on_error(err):
            if self._preview_mesh_loading_key != loading_key:
                return
            self.preview_3d.set_loading(False)
            self._preview_mesh_loading_key = None
            self._preview_mesh_worker = None
            self._update_status(self.tr("3D preview loading failed"))
            QMessageBox.warning(
                self,
                self.tr("3D Preview"),
                self.tr("Failed to prepare 3D preview:") + f"\n{err}",
            )

        worker.finished_result.connect(on_success)
        worker.error_occurred.connect(on_error)
        worker.start()

    def _sync_canvas_toolbar_visibility(self):
        """Show the canvas toolbar only in the 2D project editor."""
        if hasattr(self, "canvas_toolbar"):
            self.canvas_toolbar.setVisible(
                self.current_main_view == "editor" and self.current_view == "2d"
            )

    def _sync_transform_panel_visibility(self):
        """Show the transform panel only in the 2D project editor."""
        if not hasattr(self, "transform_panel"):
            return

        should_show = (
            self.current_main_view == "editor"
            and self.current_view == "2d"
            and bool(self.canvas.selected_indices)
            and self.current_transform_mode in {"move", "rotate", "scale"}
        )

        if not should_show:
            self.transform_panel.setVisible(False)
            return

        self._position_transform_panel()
        self.transform_panel.adjustSize()
        self.transform_panel.setVisible(True)
        self.transform_panel.raise_()

    def _position_transform_panel(self):
        """Position the transform panel beneath the canvas toolbar."""
        if hasattr(self, "canvas_toolbar"):
            pos = self.canvas_toolbar.mapTo(self, self.canvas_toolbar.rect().bottomLeft())
            panel_x = pos.x() + 10
            panel_y = pos.y() + 5
        else:
            panel_x = 200
            panel_y = 80

        self.transform_panel.move(panel_x, panel_y)

    def _show_preview_view(self):
        """Switch to the 3D preview view without preparing content yet."""
        self.main_stack.setCurrentIndex(1)
        self.current_main_view = "editor"
        self.view_stack.setCurrentIndex(1)
        self.current_view = "3d"
        self._sync_canvas_toolbar_visibility()
        self._sync_transform_panel_visibility()

    @staticmethod
    def _format_recent_project_date(date_value: Optional[str], file_path: str) -> str:
        """Format a recent project timestamp for home-page cards."""
        if date_value:
            try:
                return datetime.fromisoformat(date_value).strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass

        try:
            return datetime.fromtimestamp(Path(file_path).stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            return ""

    @staticmethod
    def _get_recent_project_preview_char(project_name: str) -> str:
        """Return the display character for a recent project card."""
        for char in project_name.strip():
            if not char.isspace():
                return char.upper()
        return "S"

    @staticmethod
    def _load_recent_project_preview_pixmap(file_path: str) -> Optional[QPixmap]:
        """Load the best available preview image for a recent project card."""
        preview_png = load_project_preview_png(file_path)
        if preview_png is not None:
            return preview_pixmap_from_png_bytes(preview_png)

        try:
            contours = load_project_contours(file_path)
        except Exception:
            return None

        return render_project_preview_pixmap(contours)

    def _refresh_home_recent_projects(self):
        """Refresh recent-project cards shown on the home page."""
        if not hasattr(self, "home_page"):
            return

        if not self.settings_manager:
            self.home_page.set_recent_projects([])
            return

        recent_projects = []
        invalid_paths = []

        for file_path in self.settings_manager.get_recent_files():
            path = Path(file_path)
            resolved_path = str(path.resolve())
            if path.suffix.lower() != ".smp" or not path.exists():
                invalid_paths.append(resolved_path)
                continue

            try:
                info = get_project_info(resolved_path)
            except Exception:
                invalid_paths.append(resolved_path)
                continue

            project_name = info.get("name") or path.stem
            preview_pixmap = None
            try:
                preview_pixmap = self._load_recent_project_preview_pixmap(resolved_path)
            except Exception:
                preview_pixmap = None

            recent_projects.append({
                "name": project_name,
                "date": self._format_recent_project_date(info.get("modified_at"), resolved_path),
                "char": self._get_recent_project_preview_char(project_name),
                "preview_pixmap": preview_pixmap,
                "path": resolved_path,
            })

        for invalid_path in invalid_paths:
            self.settings_manager.remove_recent_file(invalid_path)

        self.home_page.set_recent_projects(recent_projects)

    def _open_recent_project(self, file_path: str):
        """Open a project from the home-page recent-project list."""
        path = Path(file_path)
        resolved_path = str(path.resolve())
        if path.suffix.lower() != ".smp" or not path.exists():
            if self.settings_manager:
                self.settings_manager.remove_recent_file(resolved_path)
            self._refresh_home_recent_projects()
            QMessageBox.warning(
                self,
                self.tr("Open Project"),
                self.tr("The selected recent project is no longer available and has been removed from the list."),
            )
            return

        if not self._load_project(resolved_path) and self.settings_manager:
            self.settings_manager.remove_recent_file(resolved_path)
            self._refresh_home_recent_projects()

    def _on_nav_changed(self, nav: str):
        """处理标题栏导航切换"""
        if nav == "home":
            # 显示首页
            self.main_stack.setCurrentIndex(0)
            self.current_main_view = "home"
            self._refresh_home_recent_projects()
            self._update_status(self.tr("Home"))
        elif nav == "project":
            # 显示项目编辑视图（2D）
            self.main_stack.setCurrentIndex(1)
            self.current_main_view = "editor"
            self.view_stack.setCurrentIndex(0)
            self.current_view = "2d"
            self._update_status(self.tr("Project Edit"))
        elif nav == "preview":
            # 显示3D预览；如果还未处理但已有图形，则自动先处理
            self._show_preview_view()
            if self.slice_result is None and self.contours:
                self.preview_3d.set_loading(True, self.tr("Processing..."))
                self._update_status(self.tr("Processing..."))
                self._on_slice()
                return
            QTimer.singleShot(0, self._prepare_preview_3d)
            self._update_status(self.tr("3D Preview"))
        self._sync_canvas_toolbar_visibility()
        self._sync_transform_panel_visibility()

    def _on_menu_action(self, action: str):
        """处理标题栏菜单动作"""
        actions = {
            "new": self._on_new_project,
            "open": self._on_open_file,
            "open_project": self._on_open_project,
            "save": self._on_save_project,
            "save_as": self._on_save_as,
            # "export_gcode": self._on_export_gcode,  # 暂时屏蔽
            "export_stl": self._on_export_stl,
            "export_baseplate": self._on_export_baseplate,
            "export_panel": self._on_export_panel,
            "tutorial": self._open_tutorial,
            "about": self._on_about,
            "quit": self.close,
        }

        # 处理语言切换
        if action.startswith("lang_"):
            lang_code = action[5:]  # 去掉 "lang_" 前缀
            self._on_change_language(lang_code)
            return

        if action in actions:
            actions[action]()
        elif action == "settings":
            self._update_status(self.tr("Settings feature under development..."))
        elif action == "help":
            self._update_status(self.tr("Help feature under development..."))

    def _on_new_project(self):
        """新建项目"""
        # 清空撤销历史
        self.undo_manager.clear()

        self.contours = []
        self._invalidate_processed_result()
        self.current_file = None
        self._contour_transforms.clear()
        self._current_selected_id = None
        self.canvas.set_contours([])
        self.setWindowTitle(self.tr("MINGDA SignMaker - New Project"))
        self._update_status(self.tr("New Project"))
        self._set_project_save_point()

        # 切换到项目页面
        self.title_bar.set_nav("project")
        self._on_nav_changed("project")

    def _on_open_file(self):
        """打开DXF/SVG/SMP文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open File"),
            "",
            self.tr("Supported Files (*.dxf *.svg *.smp);;SignMaker Project (*.smp);;DXF Files (*.dxf);;SVG Files (*.svg);;All Files (*)")
        )

        if file_path:
            self._load_file(file_path)

    def _on_open_project(self):
        """专门打开项目文件（.smp）"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open Project"),
            "",
            self.tr("SignMaker Project (*.smp);;All Files (*)")
        )

        if file_path:
            self._load_project(file_path)

    def _load_file(self, file_path: str):
        """加载文件（异步）"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == '.smp':
            self._load_project(file_path)
            return

        if suffix == '.dxf':
            parse_func = lambda: self.dxf_parser.parse(file_path)
        elif suffix == '.svg':
            parse_func = lambda: self.svg_parser.parse(file_path)
        else:
            QMessageBox.warning(self, self.tr("Unsupported Format"), self.tr("Format not supported: ") + path.suffix)
            return

        run_async(
            self,
            self.tr("Loading file..."),
            parse_func,
            on_success=lambda contours: self._load_contours(contours, path),
            on_error=lambda err: QMessageBox.critical(
                self, self.tr("Load Failed"),
                self.tr("Failed to load file:") + f"\n{err}"
            ),
        )

    @staticmethod
    def _get_contours_bounds(
        contours: List[Contour],
    ) -> Optional[tuple[float, float, float, float]]:
        """获取一组轮廓的整体边界框。"""
        if not contours:
            return None

        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for contour in contours:
            bounds = contour.outer.bounds
            min_x = min(min_x, bounds[0])
            min_y = min(min_y, bounds[1])
            max_x = max(max_x, bounds[2])
            max_y = max(max_y, bounds[3])

        if min_x == float("inf"):
            return None

        return (min_x, min_y, max_x, max_y)

    @staticmethod
    def _translate_contours(contours: List[Contour], dx: float, dy: float) -> None:
        """平移一组轮廓。"""
        for contour in contours:
            for path in [contour.outer, *contour.holes]:
                for point in path.points:
                    point.x += dx
                    point.y += dy

    @staticmethod
    def _rectangles_overlap(
        candidate: tuple[float, float, float, float],
        existing: tuple[float, float, float, float],
        spacing: float,
    ) -> bool:
        """判断两个矩形在给定间距下是否冲突。"""
        return not (
            candidate[2] <= existing[0] - spacing
            or candidate[0] >= existing[2] + spacing
            or candidate[3] <= existing[1] - spacing
            or candidate[1] >= existing[3] + spacing
        )

    def _center_contours_on_platform(self, contours: List[Contour]) -> None:
        """将一组轮廓居中到平台中心。"""
        bounds = self._get_contours_bounds(contours)
        if bounds is None:
            return

        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        target_min_x = (self.canvas.platform_width - width) / 2
        target_min_y = (self.canvas.platform_height - height) / 2
        self._translate_contours(
            contours,
            target_min_x - bounds[0],
            target_min_y - bounds[1],
        )

    def _can_place_contours(
        self,
        candidate: tuple[float, float, float, float],
        occupied: List[tuple[float, float, float, float]],
        spacing: float,
        margin: float,
    ) -> bool:
        """判断给定区域是否可以放下新轮廓组。"""
        if candidate[0] < margin or candidate[1] < margin:
            return False
        if candidate[2] > self.canvas.platform_width - margin:
            return False
        if candidate[3] > self.canvas.platform_height - margin:
            return False

        return not any(
            self._rectangles_overlap(candidate, rect, spacing)
            for rect in occupied
        )

    def _auto_arrange_contours(self, new_contours: List[Contour]) -> None:
        """为新轮廓寻找一个不会覆盖现有内容的位置。"""
        new_bounds = self._get_contours_bounds(new_contours)
        if new_bounds is None:
            return

        if not self.contours:
            self._center_contours_on_platform(new_contours)
            return

        spacing = max(float(self.slice_params.layout.spacing), 0.0)
        margin = max(float(self.slice_params.layout.margin), 0.0)
        new_width = new_bounds[2] - new_bounds[0]
        new_height = new_bounds[3] - new_bounds[1]

        occupied = [contour.outer.bounds for contour in self.contours]
        overall_bounds = self._get_contours_bounds(self.contours)
        if overall_bounds is None:
            self._center_contours_on_platform(new_contours)
            return

        candidates: List[tuple[float, float]] = [
            (overall_bounds[2] + spacing, overall_bounds[1]),
            (max(margin, overall_bounds[0]), overall_bounds[3] + spacing),
        ]

        candidate_xs = {margin}
        candidate_ys = {margin}
        for rect in occupied:
            candidate_xs.add(max(margin, rect[2] + spacing))
            candidate_ys.add(max(margin, rect[3] + spacing))

        for y in sorted(candidate_ys):
            for x in sorted(candidate_xs):
                candidates.append((x, y))

        seen = set()
        for min_x, min_y in candidates:
            key = (round(min_x, 6), round(min_y, 6))
            if key in seen:
                continue
            seen.add(key)

            candidate = (min_x, min_y, min_x + new_width, min_y + new_height)
            if self._can_place_contours(candidate, occupied, spacing, margin):
                self._translate_contours(
                    new_contours,
                    min_x - new_bounds[0],
                    min_y - new_bounds[1],
                )
                return

        self._translate_contours(
            new_contours,
            overall_bounds[2] + spacing - new_bounds[0],
            overall_bounds[1] - new_bounds[1],
        )

    def _append_contours(
        self,
        new_contours: List[Contour],
        description: str,
        *,
        fit_view: bool = False,
    ) -> List[int]:
        """追加新轮廓并自动排列。"""
        if not new_contours:
            return []

        self._auto_arrange_contours(new_contours)
        insert_at = len(self.contours)

        cmd = AddContoursCommand(self.contours, new_contours, description)
        self.undo_manager.push(cmd)
        self._invalidate_processed_result()

        new_indices = list(range(insert_at, insert_at + len(new_contours)))
        self.canvas.set_contours(self.contours, center_on_platform=False)
        self.project_panel.update_contours(self.contours)
        self._apply_contour_selection(new_indices)

        if fit_view:
            self.canvas.fit_view()

        return new_indices

    def _load_contours(self, new_contours: List[Contour], path: Path):
        """加载轮廓数据（从 DXF/SVG 导入）"""
        # 创建替换轮廓命令（可撤销）
        self._append_contours(
            new_contours,
            self.tr("Load ") + path.name,
            fit_view=True,
        )

        if not self.current_file or not self.current_file.lower().endswith(".smp"):
            self.current_file = str(path)
            self.setWindowTitle(f"MINGDA SignMaker - {path.name}")

        # 切换到编辑器视图
        self.main_stack.setCurrentIndex(1)
        self.current_main_view = "editor"
        self.view_stack.setCurrentIndex(0)
        self.current_view = "2d"
        self._sync_canvas_toolbar_visibility()
        self._sync_transform_panel_visibility()
        # 更新标题栏导航状态
        if hasattr(self, 'title_bar'):
            self.title_bar.set_nav("project")

        self._update_status(
            self.tr("Loaded: {file}, {count} contours").format(
                file=path.name,
                count=len(new_contours),
            )
        )
        self.project_loaded.emit(str(path))

    def _load_project(self, file_path: str) -> bool:
        """加载项目文件（.smp）"""
        try:
            project = self.project_manager.open_project(file_path)

            # 清空撤销历史
            self.undo_manager.clear()

            # 更新数据（替换列表内容而非引用）
            self.contours.clear()
            self.contours.extend(project.contours)
            self.slice_params = project.params
            self._invalidate_processed_result()
            self.current_file = file_path
            self._contour_transforms.clear()
            self._current_selected_id = None

            # 更新UI
            self.canvas.set_contours(self.contours)
            self.canvas.fit_view()
            self.project_panel.update_contours(self.contours)
            self.param_panel.set_params(self.slice_params)
            self._sync_canvas_platform_size(self.slice_params)

            # 切换到编辑器视图
            self.main_stack.setCurrentIndex(1)
            self.current_main_view = "editor"
            self.view_stack.setCurrentIndex(0)
            self.current_view = "2d"
            self._sync_canvas_toolbar_visibility()
            self._sync_transform_panel_visibility()
            # 更新标题栏导航状态
            if hasattr(self, 'title_bar'):
                self.title_bar.set_nav("project")

            # 更新窗口标题
            self.setWindowTitle(f"MINGDA SignMaker - {project.meta.name}")
            self._update_status(self.tr("Project loaded: {name}, {count} contours").format(
                name=project.meta.name,
                count=len(self.contours)
            ))
            if self.settings_manager:
                self.settings_manager.add_recent_file(file_path)
            self._set_project_save_point()
            self._refresh_home_recent_projects()
            self.project_loaded.emit(file_path)
            return True

        except Exception as e:
            QMessageBox.critical(self, self.tr("Load Failed"), self.tr("Failed to load project:") + f"\n{e}")
            return False

    def _on_save_project(self):
        """保存项目"""
        if not self._ensure_project_has_contours_for_save():
            return

        if not self.current_file or not self.current_file.endswith('.smp'):
            self._on_save_as()
        else:
            self._save_project(self.current_file)

    def _on_save_as(self):
        """另存为"""
        if not self._ensure_project_has_contours_for_save():
            return

        # 生成默认文件名
        default_name = ""
        if self.current_file:
            default_name = Path(self.current_file).stem + ".smp"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Project"),
            default_name,
            self.tr("SignMaker Project (*.smp);;All Files (*)")
        )
        if file_path:
            # 确保扩展名
            if not file_path.lower().endswith('.smp'):
                file_path += '.smp'
            self._save_project(file_path)

    def _ensure_project_has_contours_for_save(self) -> bool:
        """确保保存前画布上存在图形"""
        if self.contours:
            return True

        QMessageBox.information(
            self,
            self.tr("Info"),
            self.tr("Please import or create graphics before saving"),
        )
        return False

    def _save_project(self, file_path: str) -> bool:
        """保存项目到文件"""
        if not self._ensure_project_has_contours_for_save():
            return False

        try:
            # 获取当前参数
            current_params = self.param_panel.get_params()

            # 获取项目名称
            project_name = Path(file_path).stem

            # 创建或更新项目
            if self.project_manager.current_project is None:
                self.project_manager.new_project()

            # 更新项目数据
            self.project_manager.current_project.meta.name = project_name
            self.project_manager.current_project.contours = self.contours
            self.project_manager.current_project.params = current_params

            # 保存
            preview_png = render_project_preview_png(self.contours)
            self.project_manager.save_project(file_path, preview_png=preview_png)

            # 更新状态
            self.current_file = file_path
            self.setWindowTitle(f"MINGDA SignMaker - {project_name}")
            self._update_status(self.tr("Project saved: ") + Path(file_path).name)

            # 添加到最近文件列表
            if self.settings_manager:
                self.settings_manager.add_recent_file(file_path)
            self._set_project_save_point()
            self._refresh_home_recent_projects()
            return True

        except Exception as e:
            QMessageBox.critical(self, self.tr("Save Failed"), self.tr("Failed to save project:") + f"\n{e}")
            return False

    def _on_show_export_menu(self):
        """显示导出菜单"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                color: #C9D1D9;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #21262D;
            }
            QMenu::separator {
                height: 1px;
                background-color: #30363D;
                margin: 4px 8px;
            }
        """)

        # menu.addAction(self.tr("Export G-code..."), self._on_export_gcode)  # 暂时屏蔽
        menu.addAction(self.tr("Export STL..."), self._on_export_stl)
        menu.addSeparator()
        menu.addAction(self.tr("Export Baseplate DXF..."), self._on_export_baseplate)
        menu.addAction(self.tr("Export Panel DXF..."), self._on_export_panel)

        menu.exec(QCursor.pos())

    # 暂时屏蔽导出G-code功能
    # def _on_export_gcode(self):
    #     """导出G-code"""
    #     if not self.slice_result:
    #         QMessageBox.information(self, self.tr("Info"), self.tr("Please process first"))
    #         return
    #
    #     file_path, _ = QFileDialog.getSaveFileName(
    #         self,
    #         self.tr("Export G-code"),
    #         "",
    #         self.tr("G-code Files (*.gcode);;All Files (*)")
    #     )
    #
    #     if file_path:
    #         try:
    #             params = self.param_panel.get_params()
    #             writer = GCodeWriter(params.gcode)
    #             writer.write(self.slice_result, file_path, params)
    #             self._update_status(self.tr("G-code exported: ") + Path(file_path).name)
    #             QMessageBox.information(self, self.tr("Export Success"), self.tr("G-code saved to:") + f"\n{file_path}")
    #         except Exception as e:
    #             QMessageBox.critical(self, self.tr("Export Failed"), self.tr("Failed to export G-code:") + f"\n{e}")

    def _on_export_stl(self):
        """导出STL（异步）"""
        if self.slice_result is None:
            QMessageBox.information(self, self.tr("Info"), self.tr("Please process first"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export STL"),
            "",
            self.tr("STL Files (*.stl);;All Files (*)")
        )

        if file_path:
            # 获取当前参数
            params = self.param_panel.get_params()
            slice_result = self.slice_result
            contours = self.contours

            def do_export():
                writer = STLWriter(
                    wall_thickness=resolve_shell_wall_thickness(
                        params.shell.line_width,
                        params.shell.wall_count,
                        params.shell.layer_height,
                        wall_thickness=params.shell.wall_thickness,
                    )
                )
                writer.write(
                    slice_result, file_path,
                    contours=contours, params=params
                )

            def on_success(_result):
                self._update_status(self.tr("STL exported: ") + Path(file_path).name)
                QMessageBox.information(self, self.tr("Export Success"), self.tr("STL saved to:") + f"\n{file_path}")

            def on_error(err):
                QMessageBox.critical(self, self.tr("Export Failed"), self.tr("Failed to export STL:") + f"\n{err}")

            run_async(
                self,
                self.tr("Exporting STL..."),
                do_export,
                on_success=on_success,
                on_error=on_error,
            )

    def _on_export_baseplate(self):
        """导出底板DXF"""
        if not self.contours:
            QMessageBox.information(self, self.tr("Info"), self.tr("Please import a DXF file first"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Baseplate DXF"),
            "",
            self.tr("DXF Files (*.dxf);;All Files (*)")
        )

        if file_path:
            try:
                # 获取当前参数
                params = self.param_panel.get_params()
                success = export_baseplate_dxf(
                    self.contours, file_path, params
                )
                if success:
                    self._update_status(self.tr("Baseplate DXF exported: ") + Path(file_path).name)
                    QMessageBox.information(
                        self, self.tr("Export Success"),
                        self.tr("Baseplate DXF saved to:") + f"\n{file_path}\n\n" +
                        self.tr("Outer clearance: ") + f"{params.shell.dxf_outer_clearance}mm\n" +
                        self.tr("Hole clearance: ") + f"{params.shell.dxf_hole_clearance}mm\n" +
                        self.tr("Laser kerf: ") + f"{params.shell.dxf_laser_kerf}mm"
                    )
                else:
                    QMessageBox.warning(self, self.tr("Export Failed"), self.tr("Failed to generate baseplate contour"))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Export Failed"), self.tr("Failed to export baseplate DXF:") + f"\n{e}")

    def _on_export_panel(self):
        """导出面板DXF"""
        if not self.contours:
            QMessageBox.information(self, self.tr("Info"), self.tr("Please import a DXF file first"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Panel DXF"),
            "",
            self.tr("DXF Files (*.dxf);;All Files (*)")
        )

        if file_path:
            try:
                # 获取当前参数
                params = self.param_panel.get_params()
                success = export_panel_dxf(
                    self.contours, file_path, params
                )
                if success:
                    self._update_status(self.tr("Panel DXF exported: ") + Path(file_path).name)
                    QMessageBox.information(
                        self, self.tr("Export Success"),
                        self.tr("Panel DXF saved to:") + f"\n{file_path}\n\n" +
                        self.tr("Outer clearance: ") + f"{params.shell.dxf_outer_clearance}mm\n" +
                        self.tr("Hole clearance: ") + f"{params.shell.dxf_hole_clearance}mm\n" +
                        self.tr("Laser kerf: ") + f"{params.shell.dxf_laser_kerf}mm"
                    )
                else:
                    QMessageBox.warning(self, self.tr("Export Failed"), self.tr("Failed to generate panel contour"))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Export Failed"), self.tr("Failed to export panel DXF:") + f"\n{e}")

    def _on_undo(self):
        """撤销"""
        if self.undo_manager.can_undo:
            command = self.undo_manager._undo_stack[-1] if self.undo_manager._undo_stack else None
            requires_reprocess = self._command_requires_reprocess(command)
            if self.undo_manager.undo():
                self.canvas.update()
                self.project_panel.update_contours(self.contours)
                if requires_reprocess:
                    self._invalidate_processed_result()
        else:
            self._update_status(self.tr("Nothing to undo"))

    def _on_redo(self):
        """重做"""
        if self.undo_manager.can_redo:
            command = self.undo_manager._redo_stack[-1] if self.undo_manager._redo_stack else None
            requires_reprocess = self._command_requires_reprocess(command)
            if self.undo_manager.redo():
                self.canvas.update()
                self.project_panel.update_contours(self.contours)
                if requires_reprocess:
                    self._invalidate_processed_result()
        else:
            self._update_status(self.tr("Nothing to redo"))

    def _on_slice(self):
        """执行处理（异步）"""
        if not self.contours:
            QMessageBox.information(self, self.tr("Info"), self.tr("Please import a DXF file first"))
            return

        # 获取参数
        params = self.param_panel.get_params()
        self._sync_canvas_platform_size(params)

        out_of_bounds_indices = self.canvas.get_out_of_bounds_indices()
        if out_of_bounds_indices:
            QMessageBox.warning(
                self,
                self.tr("Processing Blocked"),
                self.tr(
                    "Some contours exceed the platform size. Please move or scale them back inside the platform before processing."
                ),
            )
            self._update_status(
                self.tr("Processing blocked: contours exceed platform size")
            )
            return

        def do_slice():
            return self.slice_engine.slice(self.contours, params)

        def on_success(result):
            self.slice_result = result
            self.slice_params = params
            self._reset_preview_loading_state()
            self._sync_export_stl_state()
            if self.current_view == "3d":
                QTimer.singleShot(0, self._prepare_preview_3d)

            # 更新状态
            msg = self.tr("Processing complete: {layers} layers, estimated time: {time:.1f} minutes").format(
                layers=self.slice_result.total_layers,
                time=self.slice_result.estimated_time / 60
            )
            self._update_status(msg)
            self.slice_completed.emit(self.slice_result)

        def on_error(err):
            QMessageBox.critical(self, self.tr("Processing Failed"), self.tr("Error during processing:") + f"\n{err}")
            self._update_status(self.tr("Processing failed"))

        run_async(
            self,
            self.tr("Processing..."),
            do_slice,
            on_success=on_success,
            on_error=on_error,
        )

    def _switch_view(self, view_type: str):
        """切换2D/3D视图"""
        if view_type == "2d":
            self.view_stack.setCurrentIndex(0)
            self.current_view = "2d"
        else:
            self.view_stack.setCurrentIndex(1)
            self.current_view = "3d"
            QTimer.singleShot(0, self._prepare_preview_3d)
        self._sync_canvas_toolbar_visibility()
        self._sync_transform_panel_visibility()
        self._update_status(self.tr("Switched to {view} view").format(view=view_type.upper()))

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
        # 更新工具栏按钮状态
        self.canvas_toolbar._set_tool_checked(mode)

        # 设置画布工具
        self.canvas.set_tool(mode)
        self.current_transform_mode = mode

        # 配置面板显示：根据模式切换内容
        if mode == "move":
            self.transform_title.setText(self.tr("Position"))
            self.pos_widget.setVisible(True)
            self.rot_widget.setVisible(False)
            self.scale_widget.setVisible(False)
            self.transform_hint.setText(self.tr("Arrow keys: 1mm, Shift+Arrow: 10mm"))
        elif mode == "rotate":
            self.transform_title.setText(self.tr("Rotation"))
            self.pos_widget.setVisible(False)
            self.rot_widget.setVisible(True)
            self.scale_widget.setVisible(False)
            self.transform_hint.setText(self.tr("Drag grabber on ring to rotate"))
        elif mode == "scale":
            self.transform_title.setText(self.tr("Scale"))
            self.pos_widget.setVisible(False)
            self.rot_widget.setVisible(False)
            self.scale_widget.setVisible(True)
            self.transform_hint.setText(self.tr("Drag to scale, input exact values above"))
            if not hasattr(self, '_scale_original_w') or self._scale_original_w is None:
                self._capture_original_size()

        # 更新面板中的值
        self._update_transform_panel_values()

        # 显示面板并定位
        self._show_transform_panel()
        self._update_status(self.tr("Tool: ") + mode)

    def _show_transform_panel(self):
        """显示变换面板并定位到工具栏下方"""
        self._sync_transform_panel_visibility()

    def _update_transform_panel_values(self):
        """更新面板中显示的值"""
        if not self.canvas.selected_indices:
            self.transform_x.setValue(0)
            self.transform_y.setValue(0)
            self.transform_angle.setValue(0)
            return

        mode = self.current_transform_mode

        if mode == "rotate":
            # 旋转模式：显示累计旋转角度
            self.transform_angle.blockSignals(True)
            angle_deg = getattr(self.canvas, '_cumulative_angle', 0.0)
            self.transform_angle.setValue(angle_deg)
            self.transform_angle.blockSignals(False)
        elif mode == "scale":
            # 缩放模式：更新当前尺寸和百分比
            self._update_scale_panel_values()
        else:
            # 位置模式：显示选中轮廓的中心位置
            center = self.canvas._get_selection_center()
            self.transform_x.blockSignals(True)
            self.transform_y.blockSignals(True)
            self.transform_x.setValue(center.x())
            self.transform_y.setValue(center.y())
            self.transform_x.blockSignals(False)
            self.transform_y.blockSignals(False)

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
                self._update_status(self.tr("Move to: X={x:.2f}, Y={y:.2f}").format(x=target_x, y=target_y))
        elif mode == "rotate":
            # 计算需要旋转的增量角度
            target_angle = self.transform_angle.value()
            current_angle = getattr(self.canvas, '_cumulative_angle', 0.0)
            delta = target_angle - current_angle
            if abs(delta) > 0.001:
                self.canvas._cumulative_angle = target_angle
                self.canvas.rotate_selected(delta)
                self._update_selected_rotation(delta)
                self._update_status(self.tr("Rotation: {angle:.2f}°").format(angle=target_angle))

    def _capture_original_size(self):
        """记录当前选中轮廓的尺寸作为缩放基准"""
        bounds = self.canvas.get_selection_bounds()
        if bounds:
            self._scale_original_w = max(bounds[2] - bounds[0], 0.01)
            self._scale_original_h = max(bounds[3] - bounds[1], 0.01)
            # 如果轮廓已有累计缩放状态（如之前全选缩放过），保留它
            cid = self._get_selected_contour_id()
            if cid is not None and cid in self._contour_transforms:
                state = self._contour_transforms[cid]
                self._scale_pct_x = state['scale_pct_x']
                self._scale_pct_y = state['scale_pct_y']
                state['original_w'] = self._scale_original_w
                state['original_h'] = self._scale_original_h
            else:
                self._scale_pct_x = 100.0
                self._scale_pct_y = 100.0

    def _update_scale_panel_values(self):
        """更新缩放面板中的尺寸和百分比"""
        if self._scale_updating:
            return
        self._scale_updating = True

        bounds = self.canvas.get_selection_bounds()
        if bounds:
            cur_w = bounds[2] - bounds[0]
            cur_h = bounds[3] - bounds[1]

            for spin in (self.scale_x_pct, self.scale_y_pct,
                         self.scale_w, self.scale_h):
                spin.blockSignals(True)

            # 百分比使用独立存储的值（不受旋转影响）
            self.scale_x_pct.setValue(self._scale_pct_x)
            self.scale_y_pct.setValue(self._scale_pct_y)
            # 尺寸使用实际包围盒
            self.scale_w.setValue(cur_w)
            self.scale_h.setValue(cur_h)

            for spin in (self.scale_x_pct, self.scale_y_pct,
                         self.scale_w, self.scale_h):
                spin.blockSignals(False)

        self._scale_updating = False

    def _on_scale_pct_changed(self, sender):
        """Scale百分比输入改变"""
        if self._scale_updating or not self.canvas.selected_indices:
            return

        target_pct_x = self.scale_x_pct.value()
        target_pct_y = self.scale_y_pct.value()

        if self.uniform_scale_cb.isChecked():
            # 等比例：用改变的那个轴的百分比同步另一个
            if sender is self.scale_x_pct:
                target_pct_y = target_pct_x
            else:
                target_pct_x = target_pct_y

        # 通过百分比比值计算缩放因子（不依赖包围盒，旋转后仍正确）
        old_pct_x = self._scale_pct_x if self._scale_pct_x > 0.001 else 100.0
        old_pct_y = self._scale_pct_y if self._scale_pct_y > 0.001 else 100.0
        sx = target_pct_x / old_pct_x
        sy = target_pct_y / old_pct_y

        if abs(sx - 1.0) > 0.0001 or abs(sy - 1.0) > 0.0001:
            self.canvas.scale_selected_xy(sx, sy)
            self._scale_pct_x = target_pct_x
            self._scale_pct_y = target_pct_y
            self._update_selected_scale(sx, sy)
            self._update_scale_panel_values()
            self._update_status(
                self.tr("Scale: {px:.1f}% x {py:.1f}%").format(
                    px=target_pct_x, py=target_pct_y
                )
            )

    def _on_scale_size_changed(self, sender):
        """Size尺寸输入改变"""
        if self._scale_updating or not self.canvas.selected_indices:
            return

        target_w = self.scale_w.value()
        target_h = self.scale_h.value()

        bounds = self.canvas.get_selection_bounds()
        if not bounds:
            return
        cur_w = max(bounds[2] - bounds[0], 0.01)
        cur_h = max(bounds[3] - bounds[1], 0.01)

        if self.uniform_scale_cb.isChecked():
            # 等比例：用改变的那个轴的比例同步另一个
            if sender is self.scale_w:
                sx = target_w / cur_w
                sy = sx
            else:
                sy = target_h / cur_h
                sx = sy
        else:
            sx = target_w / cur_w
            sy = target_h / cur_h

        if abs(sx - 1.0) > 0.0001 or abs(sy - 1.0) > 0.0001:
            self.canvas.scale_selected_xy(sx, sy)
            self._scale_pct_x *= sx
            self._scale_pct_y *= sy
            self._update_selected_scale(sx, sy)
            self._update_scale_panel_values()
            self._update_status(
                self.tr("Scale: {px:.1f}% x {py:.1f}%").format(
                    px=self._scale_pct_x, py=self._scale_pct_y
                )
            )

    def _apply_scale_to_size(self, target_w: float, target_h: float):
        """根据目标尺寸计算缩放因子并应用"""
        bounds = self.canvas.get_selection_bounds()
        if not bounds:
            return

        cur_w = max(bounds[2] - bounds[0], 0.01)
        cur_h = max(bounds[3] - bounds[1], 0.01)
        sx = target_w / cur_w
        sy = target_h / cur_h

        if abs(sx - 1.0) > 0.0001 or abs(sy - 1.0) > 0.0001:
            self.canvas.scale_selected_xy(sx, sy)
            self._scale_pct_x *= sx
            self._scale_pct_y *= sy
            self._update_selected_scale(sx, sy)
            self._update_scale_panel_values()
            self._update_status(
                self.tr("Scale: {px:.1f}% x {py:.1f}%").format(
                    px=self._scale_pct_x, py=self._scale_pct_y
                )
            )

    def _close_transform_panel(self):
        """关闭变换面板"""
        self.transform_panel.setVisible(False)
        self.current_transform_mode = None
        self.canvas_toolbar.clear_tool()
        self.canvas.set_tool("select")
        self._update_status(self.tr("Ready"))

    def _toggle_param_panel(self):
        """切换参数面板显示/隐藏"""
        if self.param_panel.isVisible():
            self.param_panel.hide()
        else:
            self.param_panel.show()

    def _on_mirror(self, axis: str):
        """镜像"""
        if not self.canvas.selected_indices:
            QMessageBox.information(self, self.tr("Info"), self.tr("Please select a contour first"))
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
        self._invalidate_processed_result()

        self.canvas.update()
        self._update_status(self.tr("Mirror {axis} complete").format(axis=axis.upper()))

    def _on_intersection(self):
        """交集"""
        if len(self.canvas.selected_indices) < 2:
            QMessageBox.information(
                self,
                self.tr("Info"),
                self.tr("Please select at least two contours"),
            )
            return

        result = self.canvas.build_boolean_intersection_result()
        if result is None:
            return

        selected, result_contours = result
        insert_at = min(selected)
        new_selection = list(range(insert_at, insert_at + len(result_contours)))
        cmd = ReplaceSelectedContoursCommand(
            self.contours,
            selected,
            result_contours,
            description=self.tr("Intersection"),
            selection_callback=self._apply_contour_selection,
            old_selection=selected,
            new_selection=new_selection,
        )
        self.undo_manager.push(cmd)
        self._invalidate_processed_result()
        self.project_panel.update_contours(self.contours)

    def _on_difference(self):
        """差集"""
        if len(self.canvas.selected_indices) < 2:
            QMessageBox.information(
                self,
                self.tr("Info"),
                self.tr("Please select at least two contours"),
            )
            return

        result = self.canvas.build_boolean_difference_result()
        if result is None:
            return

        selected, result_contours = result
        insert_at = min(selected)
        new_selection = list(range(insert_at, insert_at + len(result_contours)))
        cmd = ReplaceSelectedContoursCommand(
            self.contours,
            selected,
            result_contours,
            description=self.tr("Difference"),
            selection_callback=self._apply_contour_selection,
            old_selection=selected,
            new_selection=new_selection,
        )
        self.undo_manager.push(cmd)
        self._invalidate_processed_result()
        self.project_panel.update_contours(self.contours)

    def _on_group(self):
        """组合"""
        selected = self.canvas.get_group_target_indices()
        if len(selected) < 2:
            QMessageBox.information(
                self,
                self.tr("Info"),
                self.tr("Please select at least two contours"),
            )
            return

        existing_group_ids = {
            self.contours[idx].group_id
            for idx in selected
            if self.contours[idx].group_id
        }
        if len(existing_group_ids) == 1 and len(selected) == len(self.canvas._get_group_member_indices(next(iter(existing_group_ids)))):
            self._update_status(self.tr("Already grouped"))
            return

        cmd = TransformCommand(self.contours, selected, self.tr("Group"))
        group_id = self.canvas._generate_group_id()
        for idx in selected:
            self.contours[idx].group_id = group_id
        cmd.capture_after()
        self.undo_manager.push(cmd, execute=False)
        self._apply_contour_selection(selected)
        self.project_panel.update_contours(self.contours)

    def _on_ungroup(self):
        """打散"""
        selected = self.canvas.get_ungroup_target_indices()
        if not selected:
            QMessageBox.information(
                self,
                self.tr("Info"),
                self.tr("Please select a grouped contour first"),
            )
            return

        cmd = TransformCommand(self.contours, selected, self.tr("Ungroup"))
        for idx in selected:
            self.contours[idx].group_id = ""
        cmd.capture_after()
        self.undo_manager.push(cmd, execute=False)
        self._apply_contour_selection(selected)
        self.project_panel.update_contours(self.contours)

    def _on_text(self):
        """文字生成"""
        try:
            from .text_dialog import TextDialog
            dialog = TextDialog(self)
            if dialog.exec():
                contours = dialog.get_contours()
                if contours:
                    # 使用撤销系统添加轮廓
                    self._append_contours(contours, self.tr("Add Contours"))

                    # 更新UI
                    self._update_status(self.tr("Text added"))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to open text dialog')}: {str(e)}")

    def _on_about(self):
        """关于对话框"""
        QMessageBox.about(
            self,
            self.tr("About MINGDA SignMaker"),
            "<h3>MINGDA SignMaker</h3>"
            "<p>" + self.tr("Professional LED Sign Letter 3D Printing Slicer") + "</p>"
            "<p>" + self.tr("Version: 0.1.8 (Development)") + "</p>"
            "<p></p>"
            "<p>" + self.tr("Features:") + "</p>"
            "<ul>"
            "<li>" + self.tr("DXF/SVG file import") + "</li>"
            "<li>" + self.tr("Straight/Bevel/Custom edges") + "</li>"
            "<li>" + self.tr("Multi-color printing support") + "</li>"
            "<li>" + self.tr("Step/V-groove") + "</li>"
            "<li>" + self.tr("Anti-warping skirt") + "</li>"
            "<li>" + self.tr("Connected letters") + "</li>"
            "</ul>"
        )

    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_label.setText(message)

    def _open_tutorial(self):
        """Open the tutorial playlist in the default browser."""
        if not QDesktopServices.openUrl(QUrl(TUTORIAL_PLAYLIST_URL)):
            QMessageBox.warning(
                self,
                self.tr("Open Tutorial Failed"),
                self.tr("Failed to open the tutorial playlist in the default browser."),
            )

    def _on_change_language(self, lang_code: str):
        """切换语言"""
        translation_manager = get_translation_manager()
        if translation_manager:
            if translation_manager.set_language_preference(lang_code):
                # 提示用户需要重启应用
                QMessageBox.information(
                    self,
                    self.tr("Language Changed"),
                    self.tr("Language has been changed to {lang}. Please restart the application for full effect.").format(
                        lang=SUPPORTED_LANGUAGES.get(lang_code, lang_code)
                    )
                )
            else:
                QMessageBox.warning(
                    self,
                    self.tr("Language Change Failed"),
                    self.tr("Translation file for {lang} is not available yet.").format(
                        lang=SUPPORTED_LANGUAGES.get(lang_code, lang_code)
                    )
                )

    # =========================================================================
    # 设置保存/加载
    # =========================================================================

    def _load_saved_params(self):
        """加载保存的参数"""
        if self.settings_manager:
            saved_params = self.settings_manager.get_last_params()
            if saved_params:
                self.slice_params = saved_params
                # 更新参数面板
                if hasattr(self, 'param_panel') and self.param_panel:
                    self.param_panel.set_params(saved_params)
                self._sync_canvas_platform_size(saved_params)
                self._update_status(self.tr("Loaded saved parameters"))

    def _save_current_params(self):
        """保存当前参数"""
        if self.settings_manager and hasattr(self, 'param_panel') and self.param_panel:
            try:
                current_params = self.param_panel.get_params()
                return self.settings_manager.set_last_params(current_params)
            except Exception:
                return False
        return False

    def _save_window_state(self):
        """保存窗口状态（使用 QSettings）"""
        if self.settings_manager:
            self.settings_manager.save_window_state(self)

    def _restore_window_state(self):
        """恢复窗口状态（使用 QSettings）"""
        if self.settings_manager:
            return self.settings_manager.restore_window_state(self)
        return False

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 保存当前参数
        if not self._handle_unsaved_changes_before_close():
            event.ignore()
            return
        self._save_current_params()
        # 保存窗口状态（使用 QSettings）
        self._save_window_state()
        # 接受关闭事件
        event.accept()


def main():
    """主程序入口"""
    app = QApplication(sys.argv)
    app.setApplicationName("MINGDA SignMaker")
    app.setOrganizationName("MINGDA")

    # 初始化翻译管理器
    translation_manager = init_translation_manager(app)
    # 加载保存的语言偏好（默认中文）
    translation_manager.load_language(translation_manager.get_current_language())

    window = MainWindow()

    # 恢复窗口状态（使用 QSettings）
    window._restore_window_state()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
