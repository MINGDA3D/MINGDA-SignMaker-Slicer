import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from resources import rc_resources  # noqa: F401

from src.ui.theme import (
    COLORS,
    get_color_dict,
    get_effective_theme,
    get_palette,
    get_stylesheet,
    normalize_theme_mode,
    set_active_theme,
)
from src.ui.icon_utils import build_theme_icon


@pytest.fixture(autouse=True)
def reset_theme():
    set_active_theme("dark")
    yield
    set_active_theme("system")


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_disabled_radio_button_checked_state_uses_muted_style():
    stylesheet = get_stylesheet()

    assert "QRadioButton:disabled" in stylesheet
    assert "QRadioButton::indicator:checked:disabled" in stylesheet
    assert COLORS.text_muted in stylesheet


def test_project_editor_regions_use_distinct_surface_colors():
    stylesheet = get_stylesheet()

    assert "QWidget#canvas" in stylesheet
    assert "QWidget#paramPanel" in stylesheet
    assert "QWidget#projectPanel" in stylesheet
    assert COLORS.editor_canvas_bg in stylesheet
    assert COLORS.editor_sidebar_left_bg in stylesheet
    assert COLORS.editor_sidebar_right_bg in stylesheet
    assert COLORS.editor_canvas_frame in stylesheet
    assert COLORS.editor_sidebar_left_accent in stylesheet
    assert COLORS.editor_sidebar_right_accent in stylesheet


def test_project_editor_headers_use_distinct_colors():
    header_colors = {
        COLORS.editor_toolbar_bg,
        COLORS.editor_sidebar_left_header_bg,
        COLORS.editor_canvas_toolbar_bg,
        COLORS.editor_sidebar_right_header_bg,
    }
    accent_colors = {
        COLORS.editor_toolbar_border,
        COLORS.editor_sidebar_left_accent,
        COLORS.editor_canvas_toolbar_accent,
        COLORS.editor_sidebar_right_accent,
    }

    assert len(header_colors) == 4
    assert len(accent_colors) == 4


def test_light_stylesheet_uses_light_design_tokens():
    stylesheet = get_stylesheet("light")

    assert "#F6F8FB" in stylesheet
    assert "#1298CC" in stylesheet
    assert "#111827" in stylesheet


def test_light_option_indicators_use_visible_borders():
    stylesheet = get_stylesheet("light")

    assert "border: 2px solid #64748B;" in stylesheet
    assert "background-color: #EEF3F8;" in stylesheet
    assert "QCheckBox::indicator:checked:disabled" in stylesheet


def test_dark_option_indicators_use_visible_borders():
    stylesheet = get_stylesheet("dark")

    assert "border: 2px solid #8B949E;" in stylesheet
    assert "border-color: #58A6FF;" in stylesheet
    assert "border-color: #484F58;" in stylesheet


def test_set_active_theme_updates_shared_colors_in_place():
    original = COLORS

    effective = set_active_theme("light")

    assert effective == "light"
    assert COLORS is original
    assert COLORS.theme_name == "light"
    assert COLORS.bg_primary == "#F6F8FB"
    assert get_effective_theme() == "light"
    assert get_color_dict()["theme_name"] == "light"


def test_invalid_theme_mode_normalizes_to_system():
    assert normalize_theme_mode("invalid") == "system"


def test_light_and_dark_palettes_are_distinct():
    assert get_palette("dark").bg_primary != get_palette("light").bg_primary
    assert get_palette("dark").text_primary != get_palette("light").text_primary


def test_dark_selected_surface_matches_mode_button_design():
    dark = get_palette("dark")

    assert dark.bg_selected == "#1E344F"
    assert dark.accent_primary == "#58A6FF"


def test_light_theme_recolors_pale_resource_icons(qapp):
    set_active_theme("light")
    icons = [
        (
            build_theme_icon(
                ":/icons/icons/bottom_hole.png",
                QSize(36, 36),
                light_color=COLORS.accent_primary,
                on_light_color=COLORS.text_on_accent,
                disabled_light_color=COLORS.text_muted,
            ),
            QSize(36, 36),
        ),
        (
            build_theme_icon(
                ":/icons/icons/params/none.svg",
                QSize(32, 32),
                light_color=COLORS.accent_primary,
                disabled_light_color=COLORS.text_muted,
            ),
            QSize(32, 32),
        ),
    ]

    for icon, size in icons:
        image = icon.pixmap(size, QIcon.Mode.Normal, QIcon.State.Off).toImage()
        visible = 0
        white = 0
        accent = 0
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                if color.alpha() <= 20:
                    continue
                visible += 1
                if color.red() > 220 and color.green() > 220 and color.blue() > 220:
                    white += 1
                if (
                    abs(color.red() - 18) < 20
                    and abs(color.green() - 152) < 30
                    and abs(color.blue() - 204) < 30
                ):
                    accent += 1

        assert visible > 0
        assert white == 0
        assert accent > 0
