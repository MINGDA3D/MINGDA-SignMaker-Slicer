"""
Theme-aware icon helpers for Qt resource icons.

Some existing PNG/SVG resources were authored for dark UI surfaces and use
white or very pale strokes. On light surfaces those strokes disappear, so the
helpers below recolor only low-contrast light pixels while preserving saturated
accent details such as print-order numbers.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap

from .theme import COLORS


def _tint_pixmap(
    pixmap: QPixmap,
    color: QColor,
    *,
    low_contrast_only: bool,
    alpha_multiplier: float = 1.0,
) -> QPixmap:
    """Return a copy of pixmap with visible pixels recolored."""
    if pixmap.isNull():
        return pixmap

    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            pixel = image.pixelColor(x, y)
            alpha = pixel.alpha()
            if alpha == 0:
                continue

            if low_contrast_only:
                luminance = (
                    pixel.red() * 0.299
                    + pixel.green() * 0.587
                    + pixel.blue() * 0.114
                )
                saturation = max(pixel.red(), pixel.green(), pixel.blue()) - min(
                    pixel.red(), pixel.green(), pixel.blue()
                )
                if luminance < 185 or saturation > 72:
                    continue

            pixel.setRgb(
                color.red(),
                color.green(),
                color.blue(),
                max(0, min(255, int(alpha * alpha_multiplier))),
            )
            image.setPixelColor(x, y, pixel)
    return QPixmap.fromImage(image)


def build_theme_icon(
    resource_path: str,
    size: QSize,
    *,
    light_color: str | None = None,
    on_light_color: str | None = None,
    disabled_light_color: str | None = None,
) -> QIcon:
    """
    Build an icon that remains legible in the active theme.

    In dark mode the source icon is kept as-is except for an explicit disabled
    variant. In light mode pale source pixels are recolored for normal state.
    If ``on_light_color`` is provided, the checked/on state is fully tinted for
    use on filled accent backgrounds.
    """
    source = QIcon(resource_path)
    normal = source.pixmap(size, QIcon.Mode.Normal, QIcon.State.Off)
    if normal.isNull():
        return source

    icon = QIcon()
    if COLORS.theme_name == "light":
        normal_color = QColor(light_color or COLORS.accent_primary)
        normal = _tint_pixmap(
            normal,
            normal_color,
            low_contrast_only=True,
        )
        on = normal
        if on_light_color:
            on = _tint_pixmap(
                source.pixmap(size, QIcon.Mode.Normal, QIcon.State.Off),
                QColor(on_light_color),
                low_contrast_only=False,
            )
        disabled = _tint_pixmap(
            source.pixmap(size, QIcon.Mode.Normal, QIcon.State.Off),
            QColor(disabled_light_color or COLORS.text_muted),
            low_contrast_only=False,
            alpha_multiplier=0.72,
        )
    else:
        on = normal
        disabled = _tint_pixmap(
            normal,
            QColor(COLORS.text_muted),
            low_contrast_only=False,
            alpha_multiplier=0.55,
        )

    icon.addPixmap(normal, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(on, QIcon.Mode.Normal, QIcon.State.On)
    icon.addPixmap(disabled, QIcon.Mode.Disabled, QIcon.State.Off)
    icon.addPixmap(disabled, QIcon.Mode.Disabled, QIcon.State.On)
    return icon
