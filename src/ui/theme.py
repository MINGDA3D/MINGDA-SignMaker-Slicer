"""
MINGDA SignMaker UI Theme
主题配色和样式定义
"""

from dataclasses import dataclass, fields
from typing import Dict, Literal, Optional


ThemeMode = Literal["system", "dark", "light"]
EffectiveTheme = Literal["dark", "light"]
VALID_THEME_MODES = {"system", "dark", "light"}


@dataclass
class Colors:
    """颜色定义"""
    theme_name: str = "dark"

    # 背景
    bg_primary: str = "#0D1117"       # 主背景
    bg_secondary: str = "#161B22"     # 次背景（侧边栏）
    bg_panel: str = "#21262D"         # 面板背景
    bg_hover: str = "#30363D"         # 悬浮背景
    bg_selected: str = "#1E344F"      # 选中背景
    editor_toolbar_bg: str = "#15202E"
    editor_toolbar_border: str = "#425A76"
    editor_sidebar_left_bg: str = "#121923"
    editor_sidebar_left_header_bg: str = "#22354C"
    editor_sidebar_left_accent: str = "#5D82B8"
    editor_sidebar_right_bg: str = "#101720"
    editor_sidebar_right_header_bg: str = "#23372F"
    editor_sidebar_right_accent: str = "#5F907C"
    editor_list_item_bg: str = "#18222E"
    editor_canvas_bg: str = "#0B1118"
    editor_canvas_toolbar_bg: str = "#182A42"
    editor_canvas_toolbar_accent: str = "#5E8FD0"
    editor_canvas_frame: str = "#3E5879"
    editor_canvas_platform_bg: str = "#111A23"
    editor_grid: str = "#242F3B"
    editor_grid_major: str = "#32404F"
    editor_platform_border: str = "#5C738A"
    editor_ruler_bg: str = "#101821"
    editor_ruler_text: str = "#788CA0"
    editor_ruler_tick: str = "#5C738A"

    # 文字
    text_primary: str = "#F0F6FC"     # 主文字
    text_secondary: str = "#C9D1D9"   # 次文字
    text_muted: str = "#8B949E"       # 禁用/提示文字
    text_on_accent: str = "#FFFFFF"
    text_on_success: str = "#FFFFFF"
    text_on_error: str = "#FFFFFF"

    # 强调色
    accent_primary: str = "#58A6FF"   # 主强调（蓝色）
    accent_primary_hover: str = "#79B8FF"
    accent_primary_pressed: str = "#388BFD"
    accent_success: str = "#3FB950"   # 成功（绿色）
    accent_success_hover: str = "#2EA043"
    accent_success_pressed: str = "#196C2E"
    accent_warning: str = "#F59E0B"   # 警告（橙色）
    accent_error: str = "#F85149"     # 错误（红色）
    accent_error_hover: str = "#FF6B6B"

    # 边框
    border_default: str = "#30363D"   # 默认边框
    border_hover: str = "#484F58"     # 悬浮边框
    border_focus: str = "#58A6FF"     # 焦点边框

    # 挤出机颜色（预览用）
    extruder_1: str = "#00BFFF"       # 挤出机1（天蓝色-遮光）
    extruder_2: str = "#FF1493"       # 挤出机2（玫红色-透光）
    extruder_3: str = "#FFA500"       # 挤出机3（橙黄色-透光）

    # 路径颜色
    path_shell: str = "#58A6FF"       # 字壳路径
    path_fill: str = "#3FB950"        # 填充路径
    path_travel: str = "#8B949E"      # 空走路径
    path_skirt: str = "#F59E0B"       # 裙边路径

    # 首页自绘色
    home_bg_base: str = "#0A0E14"
    home_bg_primary: str = "#0D1219"
    home_bg_card: str = "#1A2332"
    home_bg_hover: str = "#253345"
    home_text_primary: str = "#E6EDF3"
    home_text_secondary: str = "#9CA3AF"
    home_text_muted: str = "#6B7280"
    home_accent_primary: str = "#3B82F6"
    home_accent_secondary: str = "#06B6D4"
    home_info: str = "#6366F1"
    home_border_subtle: str = "#1E293B"
    home_border_default: str = "#334155"
    home_preview_bg: str = "#2D323C"
    home_wire_color: str = "#7887A0"
    home_glow_alpha: float = 0.06


@dataclass
class Fonts:
    """字体定义"""
    family_primary: str = "Microsoft YaHei UI"
    family_mono: str = "Consolas"
    family_fallback: str = "Segoe UI, Arial"

    # 字号
    size_h1: int = 18
    size_h2: int = 14
    size_h3: int = 12
    size_body: int = 11
    size_small: int = 10
    size_mono: int = 11

    # 字重
    weight_bold: int = 600
    weight_normal: int = 400
    weight_light: int = 300


@dataclass
class Layout:
    """布局尺寸"""
    # 窗口
    window_min_width: int = 1280
    window_min_height: int = 720

    # 面板
    sidebar_left_width: int = 200
    sidebar_right_width: int = 320
    toolbar_height: int = 40
    statusbar_height: int = 24
    menubar_height: int = 28

    # 间距
    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 12
    spacing_lg: int = 16
    spacing_xl: int = 24

    # 圆角
    radius_sm: int = 4
    radius_md: int = 6
    radius_lg: int = 8

    # 边框
    border_width: int = 1


# 主题色板
DARK_COLORS = Colors()
LIGHT_COLORS = Colors(
    theme_name="light",
    bg_primary="#F6F8FB",
    bg_secondary="#F0F4F8",
    bg_panel="#FFFFFF",
    bg_hover="#E9EEF5",
    bg_selected="#D9F4FC",
    editor_toolbar_bg="#FFFFFF",
    editor_toolbar_border="#D8E1EA",
    editor_sidebar_left_bg="#F8FAFC",
    editor_sidebar_left_header_bg="#EAF6FB",
    editor_sidebar_left_accent="#1298CC",
    editor_sidebar_right_bg="#F8FAFC",
    editor_sidebar_right_header_bg="#EEF8F2",
    editor_sidebar_right_accent="#16A34A",
    editor_list_item_bg="#FFFFFF",
    editor_canvas_bg="#EEF3F8",
    editor_canvas_toolbar_bg="#FFFFFF",
    editor_canvas_toolbar_accent="#1298CC",
    editor_canvas_frame="#C8D5E1",
    editor_canvas_platform_bg="#FFFFFF",
    editor_grid="#DDE6EF",
    editor_grid_major="#CBD5E1",
    editor_platform_border="#B8C7D6",
    editor_ruler_bg="#E9EEF5",
    editor_ruler_text="#64748B",
    editor_ruler_tick="#B8C7D6",
    text_primary="#111827",
    text_secondary="#526172",
    text_muted="#7A8796",
    accent_primary="#1298CC",
    accent_primary_hover="#1DADE5",
    accent_primary_pressed="#0F7FA8",
    accent_success="#16A34A",
    accent_success_hover="#22C55E",
    accent_success_pressed="#15803D",
    accent_warning="#D97706",
    accent_error="#DC2626",
    accent_error_hover="#EF4444",
    border_default="#D8E1EA",
    border_hover="#B8C7D6",
    border_focus="#1298CC",
    extruder_1="#1298CC",
    extruder_2="#DB2777",
    extruder_3="#D97706",
    path_shell="#1298CC",
    path_fill="#16A34A",
    path_travel="#64748B",
    path_skirt="#D97706",
    home_bg_base="#F6F8FB",
    home_bg_primary="#F0F4F8",
    home_bg_card="#FFFFFF",
    home_bg_hover="#E9EEF5",
    home_text_primary="#111827",
    home_text_secondary="#526172",
    home_text_muted="#7A8796",
    home_accent_primary="#1298CC",
    home_accent_secondary="#1DADE5",
    home_info="#4F46E5",
    home_border_subtle="#D8E1EA",
    home_border_default="#B8C7D6",
    home_preview_bg="#E9EEF5",
    home_wire_color="#64748B",
    home_glow_alpha=0.035,
)


def _copy_colors(source: Colors, target: Colors):
    for field in fields(Colors):
        setattr(target, field.name, getattr(source, field.name))


def _palette_for_effective_theme(theme: EffectiveTheme) -> Colors:
    return LIGHT_COLORS if theme == "light" else DARK_COLORS


def normalize_theme_mode(mode: Optional[str]) -> ThemeMode:
    """Normalize a persisted or requested theme mode."""
    return mode if mode in VALID_THEME_MODES else "system"  # type: ignore[return-value]


def resolve_effective_theme(mode: Optional[str] = None) -> EffectiveTheme:
    """Resolve system/dark/light into the effective theme currently rendered."""
    requested = normalize_theme_mode(mode or _REQUESTED_THEME_MODE)
    if requested in {"dark", "light"}:
        return requested  # type: ignore[return-value]

    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return "dark"

        color_scheme = app.styleHints().colorScheme()
        if color_scheme == Qt.ColorScheme.Light:
            return "light"
        if color_scheme == Qt.ColorScheme.Dark:
            return "dark"
    except Exception:
        return "dark"

    return "dark"


def get_palette(mode: Optional[str] = None) -> Colors:
    """Return the palette for a requested theme mode without mutating global state."""
    return _palette_for_effective_theme(resolve_effective_theme(mode))


_REQUESTED_THEME_MODE: ThemeMode = "system"
_EFFECTIVE_THEME: EffectiveTheme = resolve_effective_theme(_REQUESTED_THEME_MODE)


# 全局实例。注意：不要替换对象，其他模块会持有这个引用。
COLORS = Colors()
_copy_colors(_palette_for_effective_theme(_EFFECTIVE_THEME), COLORS)
FONTS = Fonts()
LAYOUT = Layout()


def set_active_theme(mode: Optional[str] = None) -> EffectiveTheme:
    """Set the active theme and update the shared COLORS object in place."""
    global _REQUESTED_THEME_MODE, _EFFECTIVE_THEME
    _REQUESTED_THEME_MODE = normalize_theme_mode(mode)
    _EFFECTIVE_THEME = resolve_effective_theme(_REQUESTED_THEME_MODE)
    _copy_colors(_palette_for_effective_theme(_EFFECTIVE_THEME), COLORS)
    return _EFFECTIVE_THEME


def get_active_theme_mode() -> ThemeMode:
    """Return the requested theme mode."""
    return _REQUESTED_THEME_MODE


def get_effective_theme() -> EffectiveTheme:
    """Return the effective rendered theme."""
    return _EFFECTIVE_THEME


def get_stylesheet(mode: Optional[str] = None) -> str:
    """获取完整的 Qt 样式表"""
    c = get_palette(mode) if mode is not None else COLORS
    f = FONTS
    l = LAYOUT

    return f"""
/* ============================================ */
/* MINGDA SignMaker - Theme Stylesheet         */
/* ============================================ */

/* 全局样式 */
QWidget {{
    background-color: {c.bg_primary};
    color: {c.text_primary};
    font-family: "{f.family_primary}", "{f.family_fallback}";
    font-size: {f.size_body}px;
}}

/* 主窗口 */
QMainWindow {{
    background-color: {c.bg_primary};
}}

/* ============================================ */
/* 菜单栏                                        */
/* ============================================ */

QMenuBar {{
    background-color: {c.bg_secondary};
    border-bottom: 1px solid {c.border_default};
    padding: 4px;
}}

QMenuBar::item {{
    padding: 4px 12px;
    border-radius: {l.radius_sm}px;
    color: {c.text_secondary};
}}

QMenuBar::item:selected {{
    background-color: {c.bg_hover};
    color: {c.text_primary};
}}

QMenu {{
    background-color: {c.bg_panel};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_md}px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: {l.radius_sm}px;
    color: {c.text_secondary};
}}

QMenu::item:selected {{
    background-color: {c.bg_hover};
    color: {c.text_primary};
}}

QMenu::separator {{
    height: 1px;
    background-color: {c.border_default};
    margin: 4px 8px;
}}

/* ============================================ */
/* 工具栏                                        */
/* ============================================ */

QToolBar {{
    background-color: {c.bg_secondary};
    border-bottom: 1px solid {c.border_default};
    padding: 4px;
    spacing: 4px;
}}

QToolBar::separator {{
    width: 1px;
    background-color: {c.border_default};
    margin: 4px 8px;
}}

QToolButton {{
    background-color: transparent;
    border: none;
    border-radius: {l.radius_sm}px;
    padding: 6px;
    color: {c.text_secondary};
}}

QToolButton:hover {{
    background-color: {c.bg_hover};
    color: {c.text_primary};
}}

QToolButton:pressed {{
    background-color: {c.bg_panel};
}}

QToolButton:checked {{
    background-color: {c.bg_selected};
    color: {c.accent_primary};
}}

/* ============================================ */
/* 按钮                                          */
/* ============================================ */

QPushButton {{
    background-color: {c.bg_panel};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_md}px;
    padding: 8px 16px;
    color: {c.text_secondary};
    font-weight: {f.weight_normal};
}}

QPushButton:hover {{
    background-color: {c.bg_hover};
    border-color: {c.border_hover};
    color: {c.text_primary};
}}

QPushButton:pressed {{
    background-color: {c.bg_secondary};
}}

QPushButton:disabled {{
    background-color: {c.bg_secondary};
    color: {c.text_muted};
    border-color: {c.bg_panel};
}}

/* 主要按钮 */
QPushButton[primary="true"] {{
    background-color: {c.accent_primary};
    border: none;
    color: {c.text_on_accent};
    font-weight: {f.weight_bold};
}}

QPushButton[primary="true"]:hover {{
    background-color: {c.accent_primary_hover};
}}

QPushButton[primary="true"]:pressed {{
    background-color: {c.accent_primary_pressed};
}}

/* 危险按钮 */
QPushButton[danger="true"] {{
    background-color: {c.accent_error};
    border: none;
    color: {c.text_on_error};
}}

QPushButton[danger="true"]:hover {{
    background-color: {c.accent_error_hover};
}}

/* ============================================ */
/* 输入框                                        */
/* ============================================ */

QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {c.bg_primary};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_md}px;
    padding: 6px 10px;
    color: {c.text_primary};
    selection-background-color: {c.accent_primary};
    font-family: "{f.family_mono}";
}}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {c.border_hover};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {c.accent_primary};
}}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {c.bg_secondary};
    color: {c.text_muted};
    border-color: {c.bg_panel};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border: none;
    border-left: 1px solid {c.border_default};
    border-top-right-radius: {l.radius_md}px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border: none;
    border-left: 1px solid {c.border_default};
    border-bottom-right-radius: {l.radius_md}px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {c.bg_hover};
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {c.text_secondary};
    width: 0px;
    height: 0px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c.text_secondary};
    width: 0px;
    height: 0px;
}}

QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover,
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{
    border-bottom-color: {c.text_primary};
    border-top-color: {c.text_primary};
}}

QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
    border-bottom-color: {c.text_muted};
    border-top-color: {c.text_muted};
}}

/* ============================================ */
/* 下拉框                                        */
/* ============================================ */

QComboBox {{
    background-color: {c.bg_panel};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_md}px;
    padding: 6px 10px;
    color: {c.text_primary};
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {c.border_hover};
}}

QComboBox:focus {{
    border-color: {c.accent_primary};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
    padding-right: 4px;
}}

QComboBox QAbstractItemView {{
    background-color: {c.bg_panel};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_md}px;
    padding: 4px;
    selection-background-color: {c.bg_hover};
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    border-radius: {l.radius_sm}px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {c.bg_hover};
}}

/* ============================================ */
/* 标签页                                        */
/* ============================================ */

QTabWidget::pane {{
    background-color: {c.bg_panel};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_md}px;
    border-top-left-radius: 0;
    padding: {l.spacing_md}px;
}}

QTabBar::tab {{
    background-color: transparent;
    border: none;
    padding: 8px 16px;
    color: {c.text_muted};
    font-weight: {f.weight_normal};
}}

QTabBar::tab:selected {{
    background-color: {c.bg_panel};
    color: {c.text_primary};
    border-bottom: 2px solid {c.accent_primary};
    font-weight: {f.weight_bold};
}}

QTabBar::tab:hover:!selected {{
    background-color: {c.bg_hover};
    color: {c.text_secondary};
}}

/* ============================================ */
/* 分组框                                        */
/* ============================================ */

QGroupBox {{
    background-color: {c.bg_secondary};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_md}px;
    margin-top: 16px;
    padding: {l.spacing_md}px;
    padding-top: 24px;
    font-weight: {f.weight_bold};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 4px;
    padding: 0 6px;
    color: {c.text_secondary};
    font-size: {f.size_h3}px;
}}

/* ============================================ */
/* 滚动条                                        */
/* ============================================ */

QScrollBar:vertical {{
    background-color: {c.bg_primary};
    width: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {c.border_default};
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c.border_hover};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {c.bg_primary};
    height: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {c.border_default};
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {c.border_hover};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ============================================ */
/* 状态栏                                        */
/* ============================================ */

QStatusBar {{
    background-color: {c.bg_secondary};
    border-top: 1px solid {c.border_default};
    color: {c.text_muted};
    font-size: {f.size_small}px;
}}

QStatusBar::item {{
    border: none;
}}

/* ============================================ */
/* 复选框                                        */
/* ============================================ */

QCheckBox {{
    spacing: 8px;
    color: {c.text_secondary};
}}

QCheckBox:hover {{
    color: {c.text_primary};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c.border_default};
    border-radius: {l.radius_sm}px;
    background-color: transparent;
}}

QCheckBox::indicator:hover {{
    border-color: {c.border_hover};
}}

QCheckBox::indicator:checked {{
    background-color: {c.accent_primary};
    border-color: {c.accent_primary};
    image: url(:/icons/icons/check.svg);
}}

QCheckBox::indicator:disabled {{
    border-color: {c.bg_panel};
    background-color: {c.bg_secondary};
}}

/* ============================================ */
/* 单选按钮                                      */
/* ============================================ */

QRadioButton {{
    spacing: 8px;
    color: {c.text_secondary};
}}

QRadioButton:disabled {{
    color: {c.text_muted};
}}

QRadioButton:hover {{
    color: {c.text_primary};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c.border_default};
    border-radius: 8px;
    background-color: transparent;
}}

QRadioButton::indicator:hover {{
    border-color: {c.border_hover};
}}

QRadioButton::indicator:checked {{
    background-color: {c.accent_primary};
    border-color: {c.accent_primary};
}}

QRadioButton::indicator:disabled {{
    border-color: {c.border_default};
    background-color: {c.bg_secondary};
}}

QRadioButton::indicator:checked:disabled {{
    background-color: {c.text_muted};
    border-color: {c.text_muted};
}}

/* ============================================ */
/* 滑块                                          */
/* ============================================ */

QSlider::groove:horizontal {{
    height: 4px;
    background-color: {c.border_default};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background-color: {c.text_primary};
    border: 2px solid {c.accent_primary};
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {c.bg_panel};
}}

QSlider::sub-page:horizontal {{
    background-color: {c.accent_primary};
    border-radius: 2px;
}}

/* ============================================ */
/* 进度条                                        */
/* ============================================ */

QProgressBar {{
    background-color: {c.border_default};
    border: none;
    border-radius: {l.radius_sm}px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {c.accent_primary};
    border-radius: {l.radius_sm}px;
}}

/* ============================================ */
/* 分割器                                        */
/* ============================================ */

QSplitter::handle {{
    background-color: {c.border_default};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

QSplitter::handle:hover {{
    background-color: {c.accent_primary};
}}

/* ============================================ */
/* 列表和树                                      */
/* ============================================ */

QListView, QTreeView, QTableView {{
    background-color: {c.bg_primary};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_md}px;
    outline: none;
}}

QListView::item, QTreeView::item {{
    padding: 6px 8px;
    border-radius: {l.radius_sm}px;
}}

QListView::item:hover, QTreeView::item:hover {{
    background-color: {c.bg_hover};
}}

QListView::item:selected, QTreeView::item:selected {{
    background-color: {c.bg_selected};
    color: {c.text_primary};
}}

QHeaderView::section {{
    background-color: {c.bg_secondary};
    border: none;
    border-right: 1px solid {c.border_default};
    border-bottom: 1px solid {c.border_default};
    padding: 6px 8px;
    color: {c.text_secondary};
    font-weight: {f.weight_bold};
}}

/* ============================================ */
/* 工具提示                                      */
/* ============================================ */

QToolTip {{
    background-color: {c.bg_panel};
    border: 1px solid {c.border_default};
    border-radius: {l.radius_sm}px;
    padding: 6px 10px;
    color: {c.text_primary};
    font-size: {f.size_small}px;
}}

/* ============================================ */
/* 对话框                                        */
/* ============================================ */

QDialog {{
    background-color: {c.bg_secondary};
}}

QMessageBox {{
    background-color: {c.bg_secondary};
}}

/* ============================================ */
/* 标签                                          */
/* ============================================ */

QLabel {{
    color: {c.text_secondary};
    background-color: transparent;
}}

QLabel[heading="true"] {{
    color: {c.text_primary};
    font-size: {f.size_h2}px;
    font-weight: {f.weight_bold};
}}

QLabel[muted="true"] {{
    color: {c.text_muted};
    font-size: {f.size_small}px;
}}

/* ============================================ */
/* 停靠窗口                                      */
/* ============================================ */

QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}

QDockWidget::title {{
    background-color: {c.bg_secondary};
    border: 1px solid {c.border_default};
    padding: 8px;
    text-align: left;
    font-weight: {f.weight_bold};
}}

QDockWidget::close-button, QDockWidget::float-button {{
    background-color: transparent;
    border: none;
    padding: 2px;
}}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background-color: {c.bg_hover};
}}

/* ============================================ */
/* 自定义类样式                                   */
/* ============================================ */

/* 画布背景 */
QWidget#canvas {{
    background-color: {c.editor_canvas_bg};
    border: 1px solid {c.editor_canvas_frame};
}}

/* 参数面板 */
QWidget#paramPanel {{
    background-color: {c.editor_sidebar_left_bg};
    border-right: 1px solid {c.editor_sidebar_left_accent};
}}

/* 项目面板 */
QWidget#projectPanel {{
    background-color: {c.editor_sidebar_right_bg};
    border-left: 1px solid {c.editor_sidebar_right_accent};
}}
"""


# 导出颜色为 QColor 对象的辅助函数
def hex_to_rgb(hex_color: str) -> tuple:
    """将十六进制颜色转换为 RGB 元组"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_color_dict() -> Dict[str, str]:
    """获取颜色字典"""
    return {
        "theme_name": COLORS.theme_name,
        "bg_primary": COLORS.bg_primary,
        "bg_secondary": COLORS.bg_secondary,
        "bg_panel": COLORS.bg_panel,
        "bg_hover": COLORS.bg_hover,
        "bg_selected": COLORS.bg_selected,
        "text_primary": COLORS.text_primary,
        "text_secondary": COLORS.text_secondary,
        "text_muted": COLORS.text_muted,
        "text_on_accent": COLORS.text_on_accent,
        "editor_toolbar_bg": COLORS.editor_toolbar_bg,
        "editor_toolbar_border": COLORS.editor_toolbar_border,
        "editor_sidebar_left_bg": COLORS.editor_sidebar_left_bg,
        "editor_sidebar_left_header_bg": COLORS.editor_sidebar_left_header_bg,
        "editor_sidebar_left_accent": COLORS.editor_sidebar_left_accent,
        "editor_sidebar_right_bg": COLORS.editor_sidebar_right_bg,
        "editor_sidebar_right_header_bg": COLORS.editor_sidebar_right_header_bg,
        "editor_sidebar_right_accent": COLORS.editor_sidebar_right_accent,
        "editor_canvas_bg": COLORS.editor_canvas_bg,
        "editor_canvas_toolbar_bg": COLORS.editor_canvas_toolbar_bg,
        "editor_canvas_toolbar_accent": COLORS.editor_canvas_toolbar_accent,
        "editor_canvas_frame": COLORS.editor_canvas_frame,
        "editor_canvas_platform_bg": COLORS.editor_canvas_platform_bg,
        "accent_primary": COLORS.accent_primary,
        "accent_success": COLORS.accent_success,
        "accent_warning": COLORS.accent_warning,
        "accent_error": COLORS.accent_error,
        "border_default": COLORS.border_default,
        "border_hover": COLORS.border_hover,
        "border_focus": COLORS.border_focus,
        "extruder_1": COLORS.extruder_1,
        "extruder_2": COLORS.extruder_2,
        "extruder_3": COLORS.extruder_3,
        "path_shell": COLORS.path_shell,
        "path_fill": COLORS.path_fill,
        "path_travel": COLORS.path_travel,
        "path_skirt": COLORS.path_skirt,
    }
