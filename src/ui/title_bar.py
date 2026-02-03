"""
MINGDA SignMaker - 导航栏

导航栏设计：
- 最左侧：菜单按钮
- 左侧：文件操作（打开、保存、导出）+ 编辑操作（撤销、重做）
- 中间：导航按钮（首页、项目、预览）
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QMenu, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from pathlib import Path


class TitleBar(QWidget):
    """导航栏"""

    # 信号
    nav_changed = Signal(str)  # 导航切换信号
    menu_action = Signal(str)  # 菜单动作信号

    # 文件操作信号
    open_clicked = Signal()
    save_clicked = Signal()
    export_clicked = Signal()
    undo_clicked = Signal()
    redo_clicked = Signal()
    slice_clicked = Signal()
    export_gcode_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_nav = "project"
        self._icon_dir = Path(__file__).parent.parent.parent / "resources" / "icons"
        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 12, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_size = QSize(24, 24)

        # ========== 最左侧：菜单按钮 ==========
        self.btn_menu = QPushButton()
        self.btn_menu.setIcon(QIcon(str(self._icon_dir / "topbar_dropdown.svg")))
        self.btn_menu.setIconSize(icon_size)
        self.btn_menu.setObjectName("iconButton")
        self.btn_menu.setToolTip(self.tr("Menu"))
        self.btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_menu.clicked.connect(self._show_menu)
        layout.addWidget(self.btn_menu)

        # 分隔符
        layout.addWidget(self._create_separator())

        # ========== 左侧：文件操作 ==========
        file_container = QWidget()
        file_layout = QHBoxLayout(file_container)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)
        file_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_open = QPushButton()
        self.btn_open.setIcon(QIcon(str(self._icon_dir / "topbar_open.svg")))
        self.btn_open.setIconSize(icon_size)
        self.btn_open.setObjectName("iconButton")
        self.btn_open.setToolTip(self.tr("Open"))
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_clicked.emit)
        file_layout.addWidget(self.btn_open)

        self.btn_save = QPushButton()
        self.btn_save.setIcon(QIcon(str(self._icon_dir / "topbar_save.svg")))
        self.btn_save.setIconSize(icon_size)
        self.btn_save.setObjectName("iconButton")
        self.btn_save.setToolTip(self.tr("Save"))
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        file_layout.addWidget(self.btn_save)

        self.btn_export = QPushButton()
        self.btn_export.setIcon(QIcon(str(self._icon_dir / "topbar_publish.svg")))
        self.btn_export.setIconSize(icon_size)
        self.btn_export.setObjectName("iconButton")
        self.btn_export.setToolTip(self.tr("Export"))
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_clicked.emit)
        file_layout.addWidget(self.btn_export)

        layout.addWidget(file_container)

        # 分隔符
        layout.addWidget(self._create_separator())

        # ========== 撤销/重做 ==========
        edit_container = QWidget()
        edit_layout = QHBoxLayout(edit_container)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(8)
        edit_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_undo = QPushButton()
        self.btn_undo.setIcon(QIcon(str(self._icon_dir / "topbar_undo.svg")))
        self.btn_undo.setIconSize(icon_size)
        self.btn_undo.setObjectName("iconButton")
        self.btn_undo.setToolTip(self.tr("Undo"))
        self.btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo.clicked.connect(self.undo_clicked.emit)
        edit_layout.addWidget(self.btn_undo)

        self.btn_redo = QPushButton()
        self.btn_redo.setIcon(QIcon(str(self._icon_dir / "topbar_redo.svg")))
        self.btn_redo.setIconSize(icon_size)
        self.btn_redo.setObjectName("iconButton")
        self.btn_redo.setToolTip(self.tr("Redo"))
        self.btn_redo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_redo.clicked.connect(self.redo_clicked.emit)
        edit_layout.addWidget(self.btn_redo)

        layout.addWidget(edit_container)

        # ========== 中间：导航按钮 ==========
        layout.addStretch(1)

        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_home = QPushButton(self.tr("Home"))
        self.btn_home.setObjectName("navButton")
        self.btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_home.clicked.connect(lambda: self._on_nav_click("home"))
        nav_layout.addWidget(self.btn_home)

        self.btn_project = QPushButton(self.tr("Project"))
        self.btn_project.setObjectName("navButtonActive")
        self.btn_project.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_project.clicked.connect(lambda: self._on_nav_click("project"))
        nav_layout.addWidget(self.btn_project)

        self.btn_preview = QPushButton(self.tr("Preview"))
        self.btn_preview.setObjectName("navButton")
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.clicked.connect(lambda: self._on_nav_click("preview"))
        nav_layout.addWidget(self.btn_preview)

        layout.addWidget(nav_container)

        layout.addStretch(1)

        # ========== 右侧：切片和导出按钮 ==========
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_slice = QPushButton(self.tr("Slice"))
        self.btn_slice.setObjectName("actionButton")
        self.btn_slice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_slice.clicked.connect(self.slice_clicked.emit)
        action_layout.addWidget(self.btn_slice)

        self.btn_export_gcode = QPushButton(self.tr("Export Gcode"))
        self.btn_export_gcode.setObjectName("primaryButton")
        self.btn_export_gcode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_gcode.clicked.connect(self.export_gcode_clicked.emit)
        action_layout.addWidget(self.btn_export_gcode)

        layout.addWidget(action_container)

        self.setFixedHeight(44)

    def _create_separator(self):
        """创建分隔符"""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #30363D; margin: 8px 8px;")
        sep.setFixedWidth(1)
        return sep

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            TitleBar {
                background-color: #0D1117;
                border-bottom: 1px solid #21262D;
            }

            /* 导航按钮 - 普通状态 */
            QPushButton#navButton {
                background-color: transparent;
                color: #8B949E;
                border: none;
                border-radius: 4px;
                padding: 5px 16px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#navButton:hover {
                background-color: #21262D;
                color: #C9D1D9;
            }

            /* 导航按钮 - 激活状态 */
            QPushButton#navButtonActive {
                background-color: #1F6FEB;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 5px 16px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#navButtonActive:hover {
                background-color: #388BFD;
            }

            /* 图标按钮 */
            QPushButton#iconButton {
                background-color: transparent;
                color: #8B949E;
                border: none;
                border-radius: 4px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
                padding: 2px;
            }
            QPushButton#iconButton:hover {
                background-color: #21262D;
                color: #C9D1D9;
            }

            /* 操作按钮 */
            QPushButton#actionButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#actionButton:hover {
                background-color: #30363D;
                border-color: #8B949E;
            }
            QPushButton#actionButton:pressed {
                background-color: #161B22;
            }

            /* 主要按钮 */
            QPushButton#primaryButton {
                background-color: #238636;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#primaryButton:hover {
                background-color: #2EA043;
            }
            QPushButton#primaryButton:pressed {
                background-color: #196C2E;
            }
        """)

    def _on_nav_click(self, nav: str):
        """处理导航点击"""
        if nav == self.current_nav:
            return

        self.btn_home.setObjectName("navButtonActive" if nav == "home" else "navButton")
        self.btn_project.setObjectName("navButtonActive" if nav == "project" else "navButton")
        self.btn_preview.setObjectName("navButtonActive" if nav == "preview" else "navButton")

        self.btn_home.setStyle(self.btn_home.style())
        self.btn_project.setStyle(self.btn_project.style())
        self.btn_preview.setStyle(self.btn_preview.style())

        self.current_nav = nav
        self.nav_changed.emit(nav)

    def _show_menu(self):
        """显示菜单"""
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

        menu.addAction(self.tr("New Project"), lambda: self.menu_action.emit("new"))
        menu.addAction(self.tr("Open File..."), lambda: self.menu_action.emit("open"))
        menu.addAction(self.tr("Save Project"), lambda: self.menu_action.emit("save"))
        menu.addSeparator()
        menu.addAction(self.tr("Export G-code..."), lambda: self.menu_action.emit("export_gcode"))
        menu.addAction(self.tr("Export STL..."), lambda: self.menu_action.emit("export_stl"))
        menu.addSeparator()
        menu.addAction(self.tr("Export Baseplate DXF..."), lambda: self.menu_action.emit("export_baseplate"))
        menu.addAction(self.tr("Export Panel DXF..."), lambda: self.menu_action.emit("export_panel"))
        menu.addSeparator()

        # 语言子菜单
        lang_menu = menu.addMenu(self.tr("Language"))
        lang_menu.addAction("中文", lambda: self.menu_action.emit("lang_zh_CN"))
        lang_menu.addAction("English", lambda: self.menu_action.emit("lang_en_US"))
        lang_menu.addAction("Русский", lambda: self.menu_action.emit("lang_ru_RU"))
        lang_menu.addAction("Українська", lambda: self.menu_action.emit("lang_uk_UA"))
        lang_menu.addAction("Deutsch", lambda: self.menu_action.emit("lang_de_DE"))
        lang_menu.addAction("Français", lambda: self.menu_action.emit("lang_fr_FR"))
        lang_menu.addAction("Español", lambda: self.menu_action.emit("lang_es_ES"))
        lang_menu.addAction("Português", lambda: self.menu_action.emit("lang_pt_BR"))
        lang_menu.addAction("Italiano", lambda: self.menu_action.emit("lang_it_IT"))
        lang_menu.addAction("עברית", lambda: self.menu_action.emit("lang_he_IL"))
        lang_menu.addAction("العربية", lambda: self.menu_action.emit("lang_ar_SA"))
        lang_menu.addAction("日本語", lambda: self.menu_action.emit("lang_ja_JP"))
        lang_menu.addAction("한국어", lambda: self.menu_action.emit("lang_ko_KR"))
        lang_menu.addAction("Türkçe", lambda: self.menu_action.emit("lang_tr_TR"))
        menu.addSeparator()

        menu.addAction(self.tr("About"), lambda: self.menu_action.emit("about"))
        menu.addSeparator()
        menu.addAction(self.tr("Exit"), lambda: self.menu_action.emit("quit"))

        menu.exec(self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomLeft()))

    def set_nav(self, nav: str):
        """设置当前导航"""
        if nav not in ["home", "project", "preview"]:
            return
        self.current_nav = nav
        self.btn_home.setObjectName("navButtonActive" if nav == "home" else "navButton")
        self.btn_project.setObjectName("navButtonActive" if nav == "project" else "navButton")
        self.btn_preview.setObjectName("navButtonActive" if nav == "preview" else "navButton")
        self.btn_home.setStyle(self.btn_home.style())
        self.btn_project.setStyle(self.btn_project.style())
        self.btn_preview.setStyle(self.btn_preview.style())
