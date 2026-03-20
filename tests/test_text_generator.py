from src.core.font_manager import FontManager
from src.core.text_generator import TextGenerator
from src.core.types import PathType
from src.utils.geometry import is_clockwise


def _find_test_font() -> str:
    manager = FontManager()
    for name in (
        "Arial",
        "Calibri",
        "Times New Roman",
        "Microsoft YaHei UI",
        "Microsoft YaHei",
    ):
        path = manager.get_font_path(name)
        if path:
            return path
    return ""


def test_o_glyph_contour_is_normalized():
    font_path = _find_test_font()
    assert font_path, "No suitable system font found for text generator test"

    contours = TextGenerator().generate_text_contours("O", font_path, 30.0, 0.0)

    assert len(contours) == 1
    contour = contours[0]

    assert contour.outer.path_type == PathType.OUTER
    assert not is_clockwise(contour.outer)
    assert len(contour.holes) == 1

    hole = contour.holes[0]
    assert hole.path_type == PathType.INNER
    assert is_clockwise(hole)
