from src.ui.theme import COLORS, get_stylesheet


def test_disabled_radio_button_checked_state_uses_muted_style():
    stylesheet = get_stylesheet()

    assert "QRadioButton:disabled" in stylesheet
    assert "QRadioButton::indicator:checked:disabled" in stylesheet
    assert COLORS.text_muted in stylesheet
