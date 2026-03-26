from src.ui.theme import COLORS, get_stylesheet


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
