"""Project preview rendering helpers for recent-project cards."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPixmap

from src.core.contour_preview import (
    PREVIEW_BACKGROUND as CORE_PREVIEW_BACKGROUND,
    PREVIEW_PADDING,
    PREVIEW_SIZE,
    render_contour_preview_image,
    render_contour_preview_png,
)
from src.core.types import Contour

PREVIEW_BACKGROUND = CORE_PREVIEW_BACKGROUND


def render_project_preview_image(
    contours: list[Contour],
    size: QSize = PREVIEW_SIZE,
    padding: int = PREVIEW_PADDING,
) -> Optional[QImage]:
    """Render project contours into a fixed-size preview image."""
    return render_contour_preview_image(contours, size=size, padding=padding)


def render_project_preview_png(
    contours: list[Contour],
    size: QSize = PREVIEW_SIZE,
    padding: int = PREVIEW_PADDING,
) -> Optional[bytes]:
    """Render project contours to PNG bytes for project persistence."""
    return render_contour_preview_png(contours, size=size, padding=padding)


def render_project_preview_pixmap(
    contours: list[Contour],
    size: QSize = PREVIEW_SIZE,
    padding: int = PREVIEW_PADDING,
) -> Optional[QPixmap]:
    """Render project contours directly to a pixmap."""
    image = render_project_preview_image(contours, size=size, padding=padding)
    if image is None:
        return None
    return QPixmap.fromImage(image)


def preview_pixmap_from_png_bytes(preview_png: bytes) -> Optional[QPixmap]:
    """Decode preview PNG bytes into a pixmap."""
    if not preview_png:
        return None

    pixmap = QPixmap()
    if not pixmap.loadFromData(preview_png, "PNG"):
        return None
    return pixmap
