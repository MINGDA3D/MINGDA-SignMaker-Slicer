"""
MINGDA SignMaker - 导航栏

导航栏设计：
- 最左侧：菜单按钮
- 左侧：文件操作（打开、保存、导出）+ 编辑操作（撤销、重做）
- 中间：导航按钮（首页、项目、预览）
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QMenu, QFrame, QToolButton
)
from PySide6.QtCore import Qt, Signal, QSize, QCoreApplication
from PySide6.QtGui import QIcon, QAction, QActionGroup

from .theme import COLORS, get_active_theme_mode


class TitleBar(QWidget):
    """导航栏"""

    # 信号
    nav_changed = Signal(str)  # 导航切换信号
    menu_action = Signal(str)  # 菜单动作信号
    open_recent_menu_requested = Signal(object)

    # 文件操作信号
    open_clicked = Signal()
    save_clicked = Signal()
    export_clicked = Signal()
    undo_clicked = Signal()
    redo_clicked = Signal()
    slice_clicked = Signal()
    export_gcode_clicked = Signal()
    export_stl_clicked = Signal()
    export_format_changed = Signal(str)

    EXPORT_GCODE = "gcode"
    EXPORT_STL = "stl"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_nav = "home"
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
        self.btn_menu.setIcon(QIcon(":/icons/icons/topbar_dropdown.svg"))
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
        self.btn_open.setIcon(QIcon(":/icons/icons/topbar_open.svg"))
        self.btn_open.setIconSize(icon_size)
        self.btn_open.setObjectName("iconButton")
        self.btn_open.setToolTip(self.tr("Open File (DXF/SVG/SMP)"))
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_clicked.emit)
        file_layout.addWidget(self.btn_open)

        self.btn_save = QPushButton()
        self.btn_save.setIcon(QIcon(":/icons/icons/topbar_save.svg"))
        self.btn_save.setIconSize(icon_size)
        self.btn_save.setObjectName("iconButton")
        self.btn_save.setToolTip(self.tr("Save Project"))
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        file_layout.addWidget(self.btn_save)

        self.btn_export = QPushButton()
        self.btn_export.setIcon(QIcon(":/icons/icons/topbar_publish.svg"))
        self.btn_export.setIconSize(icon_size)
        self.btn_export.setObjectName("iconButton")
        self.btn_export.setToolTip(self.tr("Export Project"))
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
        self.btn_undo.setIcon(QIcon(":/icons/icons/topbar_undo.svg"))
        self.btn_undo.setIconSize(icon_size)
        self.btn_undo.setObjectName("iconButton")
        self.btn_undo.setToolTip(self.tr("Undo"))
        self.btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo.clicked.connect(self.undo_clicked.emit)
        edit_layout.addWidget(self.btn_undo)

        self.btn_redo = QPushButton()
        self.btn_redo.setIcon(QIcon(":/icons/icons/topbar_redo.svg"))
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
        self.btn_home.setObjectName("navButtonActive")
        self.btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_home.clicked.connect(lambda: self._on_nav_click("home"))
        nav_layout.addWidget(self.btn_home)

        self.btn_project = QPushButton(self.tr("Project"))
        self.btn_project.setObjectName("navButton")
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

        self.btn_slice = QPushButton(self.tr("Process"))
        self.btn_slice.setObjectName("primaryButton")
        self.btn_slice.setToolTip(self.tr("Process the model and generate layers"))
        self.btn_slice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_slice.clicked.connect(self.slice_clicked.emit)
        action_layout.addWidget(self.btn_slice)

        self.export_button_group = QWidget()
        export_layout = QHBoxLayout(self.export_button_group)
        export_layout.setContentsMargins(0, 0, 0, 0)
        export_layout.setSpacing(0)
        export_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_export_options = QToolButton()
        self.btn_export_options.setObjectName("splitPrimaryMenuButton")
        self.btn_export_options.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_export_options.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_export_options.setText("▼")
        self.btn_export_options.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_export_stl = QPushButton()
        self.btn_export_stl.setObjectName("splitPrimaryMainButton")
        self.btn_export_stl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_stl.clicked.connect(self._on_primary_export_clicked)
        self._export_menu = QMenu(self.btn_export_options)
        self._apply_menu_style(self._export_menu)
        self._export_action_group = QActionGroup(self)
        self._export_action_group.setExclusive(True)
        self._export_gcode_action = QAction(
            self._translate_export_text(self.EXPORT_GCODE),
            self,
        )
        self._export_gcode_action.setCheckable(True)
        self._export_gcode_action.triggered.connect(self._on_export_gcode_selected)
        self._export_action_group.addAction(self._export_gcode_action)
        self._export_menu.addAction(self._export_gcode_action)
        self._export_stl_action = QAction(
            self._translate_export_text(self.EXPORT_STL),
            self,
        )
        self._export_stl_action.setCheckable(True)
        self._export_stl_action.triggered.connect(self._on_export_stl_selected)
        self._export_action_group.addAction(self._export_stl_action)
        self._export_menu.addAction(self._export_stl_action)
        self.btn_export_options.setMenu(self._export_menu)
        self._current_primary_export_format = self.EXPORT_GCODE
        self.set_primary_export_format(self.EXPORT_GCODE)
        export_layout.addWidget(self.btn_export_options)
        export_layout.addWidget(self.btn_export_stl)
        action_layout.addWidget(self.export_button_group)

        layout.addWidget(action_container)

        self.setFixedHeight(44)

    def _create_separator(self):
        """创建分隔符"""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("separator")
        sep.setFixedWidth(1)
        return sep

    def _apply_menu_style(self, menu: QMenu):
        """Apply the shared popup-menu styling."""
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS.bg_panel};
                border: 1px solid {COLORS.border_default};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {COLORS.text_secondary};
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
            QMenu::item:checked {{
                color: {COLORS.accent_primary};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {COLORS.border_default};
                margin: 4px 8px;
            }}
        """)

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet(f"""
            TitleBar {{
                background-color: {COLORS.editor_toolbar_bg};
                border-bottom: 1px solid {COLORS.editor_toolbar_border};
            }}

            /* 导航按钮 - 普通状态 */
            QPushButton#navButton {{
                background-color: transparent;
                color: {COLORS.text_muted};
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 5px 16px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#navButton:hover {{
                background-color: {COLORS.editor_canvas_toolbar_bg};
                border-color: {COLORS.editor_toolbar_border};
                color: {COLORS.text_secondary};
            }}

            /* 导航按钮 - 激活状态 */
            QPushButton#navButtonActive {{
                background-color: {COLORS.accent_primary};
                color: {COLORS.text_on_accent};
                border: 1px solid {COLORS.editor_canvas_toolbar_accent};
                border-radius: 4px;
                padding: 5px 16px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#navButtonActive:hover {{
                background-color: {COLORS.accent_primary_hover};
            }}

            /* 图标按钮 */
            QPushButton#iconButton {{
                background-color: transparent;
                color: {COLORS.text_muted};
                border: 1px solid transparent;
                border-radius: 4px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
                padding: 2px;
            }}
            QPushButton#iconButton:hover {{
                background-color: {COLORS.editor_canvas_toolbar_bg};
                border-color: {COLORS.editor_toolbar_border};
                color: {COLORS.text_secondary};
            }}

            /* 操作按钮 */
            QPushButton#actionButton {{
                background-color: {COLORS.editor_canvas_toolbar_bg};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.editor_toolbar_border};
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#actionButton:hover {{
                background-color: {COLORS.bg_hover};
                border-color: {COLORS.border_hover};
            }}
            QPushButton#actionButton:pressed {{
                background-color: {COLORS.bg_secondary};
            }}

            /* 主要按钮 */
            QPushButton#primaryButton,
            QToolButton#primaryButton {{
                background-color: {COLORS.accent_success};
                color: {COLORS.text_on_success};
                border: none;
                border-radius: 4px;
                min-height: 36px;
                max-height: 36px;
                padding: 0 18px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#primaryButton:hover,
            QToolButton#primaryButton:hover {{
                background-color: {COLORS.accent_success_hover};
            }}
            QPushButton#primaryButton:pressed,
            QToolButton#primaryButton:pressed {{
                background-color: {COLORS.accent_success_pressed};
            }}
            QToolButton#primaryButton {{
                padding-right: 28px;
            }}
            QToolButton#primaryButton::menu-button {{
                border: none;
                width: 18px;
            }}
            QToolButton#primaryButton::menu-indicator {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                right: 8px;
            }}

            /* Export split button */
            QPushButton#splitPrimaryMainButton,
            QToolButton#splitPrimaryMenuButton {{
                background-color: {COLORS.accent_success};
                color: {COLORS.text_on_success};
                border: none;
                min-height: 36px;
                max-height: 36px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#splitPrimaryMainButton {{
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
                padding: 0 18px;
            }}
            QToolButton#splitPrimaryMenuButton {{
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
                min-width: 38px;
                max-width: 38px;
                border-right: 1px solid {COLORS.accent_success_pressed};
                padding: 0;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton#splitPrimaryMainButton:hover,
            QToolButton#splitPrimaryMenuButton:hover {{
                background-color: {COLORS.accent_success_hover};
            }}
            QPushButton#splitPrimaryMainButton:pressed,
            QToolButton#splitPrimaryMenuButton:pressed {{
                background-color: {COLORS.accent_success_pressed};
            }}
            QPushButton#splitPrimaryMainButton:disabled,
            QToolButton#splitPrimaryMenuButton:disabled {{
                background-color: {COLORS.bg_hover};
                color: {COLORS.text_muted};
            }}
            QToolButton#splitPrimaryMenuButton:disabled {{
                border-right: 1px solid {COLORS.border_hover};
            }}
            QToolButton#splitPrimaryMenuButton::menu-indicator {{
                image: none;
                width: 0;
            }}
            QFrame#separator {{
                background-color: {COLORS.editor_toolbar_border};
                margin: 8px 8px;
            }}
        """)

    def apply_theme(self):
        """Refresh all title-bar styles after the global theme changes."""
        self._apply_styles()
        self._apply_menu_style(self._export_menu)
        self.update()

    def _translate_export_text(self, export_format: str) -> str:
        """Return the translated label for the primary export button."""
        source = "Export STL" if export_format == self.EXPORT_STL else "Export G-code"
        return QCoreApplication.translate("MainWindow", source)

    def get_primary_export_format(self) -> str:
        """Return the currently selected primary export format."""
        return self._current_primary_export_format

    def set_primary_export_format(self, export_format: str):
        """Update the primary export button label and checked menu item."""
        normalized = (
            export_format
            if export_format in {self.EXPORT_GCODE, self.EXPORT_STL}
            else self.EXPORT_GCODE
        )
        self._current_primary_export_format = normalized
        self.btn_export_stl.setText(self._translate_export_text(normalized))
        self.btn_export_stl.setToolTip(self.btn_export_stl.text())
        self.btn_export_options.setToolTip(self.btn_export_stl.text())
        self._export_gcode_action.setChecked(normalized == self.EXPORT_GCODE)
        self._export_stl_action.setChecked(normalized == self.EXPORT_STL)

    def set_primary_export_enabled(self, enabled: bool):
        """Enable or disable the export split button as a group."""
        self.btn_export_stl.setEnabled(enabled)
        self.btn_export_options.setEnabled(enabled)

    def _select_primary_export_format(self, export_format: str):
        """Update the selected primary export format without running an export."""
        previous_format = self._current_primary_export_format
        self.set_primary_export_format(export_format)
        if export_format != previous_format:
            self.export_format_changed.emit(export_format)

    def _emit_primary_export_clicked(self):
        """Run the currently selected export action."""
        export_format = self._current_primary_export_format
        if export_format == self.EXPORT_STL:
            self.export_stl_clicked.emit()
        else:
            self.export_gcode_clicked.emit()

    def _on_primary_export_clicked(self):
        """Run the currently selected export action."""
        self._emit_primary_export_clicked()

    def _on_export_gcode_selected(self):
        """Select G-code as the primary export action."""
        self._select_primary_export_format(self.EXPORT_GCODE)

    def _on_export_stl_selected(self):
        """Select STL as the primary export action."""
        self._select_primary_export_format(self.EXPORT_STL)

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
        self._apply_menu_style(menu)

        menu.addAction(self.tr("New Project"), lambda: self.menu_action.emit("new"))
        menu.addAction(self.tr("Open File..."), lambda: self.menu_action.emit("open"))
        menu.addAction(self.tr("Open Project..."), lambda: self.menu_action.emit("open_project"))
        self._add_open_recent_menu(menu)
        menu.addSeparator()
        menu.addAction(self.tr("Save Project"), lambda: self.menu_action.emit("save"))
        menu.addAction(self.tr("Save As..."), lambda: self.menu_action.emit("save_as"))
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

        theme_menu = menu.addMenu(self.tr("Theme"))
        theme_group = QActionGroup(menu)
        theme_group.setExclusive(True)
        current_theme = get_active_theme_mode()
        for mode, label in (
            ("system", self.tr("System")),
            ("dark", self.tr("Dark")),
            ("light", self.tr("Light")),
        ):
            action = QAction(label, menu)
            action.setCheckable(True)
            action.setChecked(current_theme == mode)
            action.triggered.connect(lambda checked=False, m=mode: self.menu_action.emit(f"theme_{m}"))
            theme_group.addAction(action)
            theme_menu.addAction(action)

        menu.addAction(self.tr("Show Configuration Folder"), lambda: self.menu_action.emit("open_user_config_dir"))
        menu.addAction(self.tr("Tutorial"), lambda: self.menu_action.emit("tutorial"))
        menu.addAction(self.tr("Check for Updates"), lambda: self.menu_action.emit("check_updates"))
        menu.addSeparator()

        menu.addAction(self.tr("About"), lambda: self.menu_action.emit("about"))
        menu.addSeparator()
        menu.addAction(self.tr("Exit"), lambda: self.menu_action.emit("quit"))

        menu.exec(self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomLeft()))

    def _add_open_recent_menu(self, menu: QMenu):
        recent_menu = menu.addMenu(self.tr("Open Recent"))
        self._apply_menu_style(recent_menu)
        recent_menu.setToolTipsVisible(True)
        recent_menu.aboutToShow.connect(
            lambda target_menu=recent_menu: self.open_recent_menu_requested.emit(target_menu)
        )

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
