"""Project preview rendering helpers for recent-project cards."""

from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap

from src.core.types import Contour, Path

PREVIEW_BACKGROUND = QColor("#2D323C")
PREVIEW_WIRE_COLOR = QColor("#7887A0")
PREVIEW_SIZE = QSize(180, 180)
PREVIEW_PADDING = 18
PREVIEW_STROKE_WIDTH = 2.0


def _iter_preview_paths(contours: Iterable[Contour]) -> Iterable[Path]:
    """Yield the paths that should appear in the project preview."""
    for contour in contours:
        yield contour.outer
        for hole in contour.holes:
            yield hole


def _get_preview_bounds(contours: list[Contour]) -> Optional[tuple[float, float, float, float]]:
    """Return the combined bounds for all previewable contour paths."""
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")
    has_points = False

    for path in _iter_preview_paths(contours):
        if not path.points:
            continue
        bounds = path.bounds
        min_x = min(min_x, bounds[0])
        min_y = min(min_y, bounds[1])
        max_x = max(max_x, bounds[2])
        max_y = max(max_y, bounds[3])
        has_points = True

    if not has_points:
        return None

    return (min_x, min_y, max_x, max_y)


def render_project_preview_image(
    contours: list[Contour],
    size: QSize = PREVIEW_SIZE,
    padding: int = PREVIEW_PADDING,
) -> Optional[QImage]:
    """Render project contours into a fixed-size preview image."""
    bounds = _get_preview_bounds(contours)
    if bounds is None:
        return None

    image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(PREVIEW_BACKGROUND)

    min_x, min_y, max_x, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y
    available_width = max(size.width() - padding * 2, 1)
    available_height = max(size.height() - padding * 2, 1)

    normalized_width = width if width > 0 else 1.0
    normalized_height = height if height > 0 else 1.0
    scale = min(available_width / normalized_width, available_height / normalized_height)

    draw_width = width * scale if width > 0 else 0.0
    draw_height = height * scale if height > 0 else 0.0
    offset_x = (size.width() - draw_width) / 2
    offset_y = (size.height() - draw_height) / 2
    center_x = size.width() / 2
    center_y = size.height() / 2

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    pen = QPen(PREVIEW_WIRE_COLOR, PREVIEW_STROKE_WIDTH)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    for path in _iter_preview_paths(contours):
        if not path.points:
            continue

        qpath = QPainterPath()
        first_point = path.points[0]
        first_x = center_x if width == 0 else offset_x + (first_point.x - min_x) * scale
        first_y = center_y if height == 0 else offset_y + (max_y - first_point.y) * scale
        qpath.moveTo(QPointF(first_x, first_y))

        for point in path.points[1:]:
            mapped_x = center_x if width == 0 else offset_x + (point.x - min_x) * scale
            mapped_y = center_y if height == 0 else offset_y + (max_y - point.y) * scale
            qpath.lineTo(QPointF(mapped_x, mapped_y))

        if path.is_closed and len(path.points) > 2:
            qpath.closeSubpath()

        painter.drawPath(qpath)

    painter.end()
    return image


def render_project_preview_png(
    contours: list[Contour],
    size: QSize = PREVIEW_SIZE,
    padding: int = PREVIEW_PADDING,
) -> Optional[bytes]:
    """Render project contours to PNG bytes for project persistence."""
    image = render_project_preview_image(contours, size=size, padding=padding)
    if image is None:
        return None

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        return None

    try:
        if not image.save(buffer, "PNG"):
            return None
    finally:
        buffer.close()

    return bytes(byte_array)


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
