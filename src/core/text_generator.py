"""
Text Generator - Convert text to contours using FreeType
"""
from typing import List, Tuple
import freetype
from .types import Point, Path, Contour, PathType
import math


class TextGenerator:
    """Generate text contours from font files"""

    def __init__(self):
        self._face = None

    def generate_text_contours(
        self,
        text: str,
        font_path: str,
        font_size: float,  # mm
        spacing: float = 0.0  # mm
    ) -> List[Contour]:
        """
        Generate contours from text

        Args:
            text: Text to generate
            font_path: Path to font file
            font_size: Font size in mm
            spacing: Character spacing in mm

        Returns:
            List of Contour objects
        """
        if not text or not font_path:
            return []

        # Load font
        face = freetype.Face(font_path)
        # Set font size: convert mm to points (1 inch = 25.4mm = 72 points)
        points = font_size * 72 / 25.4
        face.set_char_size(int(points * 64))  # 26.6 fractional points

        contours = []
        x_offset = 0.0

        for char in text:
            # Load character
            face.load_char(char, freetype.FT_LOAD_NO_BITMAP)

            # Get glyph outline
            outline = face.glyph.outline
            if not outline:
                # Space or non-printable character
                x_offset += face.glyph.advance.x / 64.0 * 25.4 / 72 + spacing
                continue

            # Convert outline to paths
            paths = self._outline_to_paths(outline, x_offset)

            if paths:
                # Separate outer and holes
                outer_path = None
                holes = []

                for path in paths:
                    if path.area > 0:  # Counter-clockwise = outer
                        if outer_path is None or path.area > outer_path.area:
                            if outer_path:
                                holes.append(outer_path)
                            outer_path = path
                        else:
                            holes.append(path)
                    else:  # Clockwise = hole
                        holes.append(path)

                if outer_path:
                    contour = Contour(
                        outer=outer_path,
                        holes=holes,
                        name=char
                    )
                    contours.append(contour)

            # Advance to next character (convert 26.6 format to mm)
            x_offset += face.glyph.advance.x / 64.0 * 25.4 / 72 + spacing

        return contours

    def _outline_to_paths(
        self,
        outline,
        x_offset: float
    ) -> List[Path]:
        """Convert FreeType outline to Path objects with Bezier curve interpolation"""
        paths = []

        start = 0
        for i in range(outline.n_contours):
            end = outline.contours[i] + 1
            points = []

            # Convert all points to mm
            contour_points = []
            for j in range(start, end):
                x = outline.points[j][0] / 64.0 * 25.4 / 72 + x_offset
                y = outline.points[j][1] / 64.0 * 25.4 / 72
                tag = outline.tags[j] & 1  # 1 = on-curve, 0 = off-curve
                contour_points.append((x, y, tag))

            # Process contour
            n = len(contour_points)
            if n == 0:
                continue

            j = 0
            while j < n:
                x0, y0, tag0 = contour_points[j]

                # Add on-curve point
                if tag0:
                    points.append(Point(x0, y0))
                    j += 1
                else:
                    # Off-curve point - find the curve segment
                    j_next = (j + 1) % n
                    x1, y1, tag1 = contour_points[j_next]

                    if tag1:
                        # Next is on-curve: simple quadratic Bezier
                        # Need previous on-curve point
                        if points:
                            px, py = points[-1].x, points[-1].y
                        else:
                            # Find last on-curve point
                            for k in range(n-1, -1, -1):
                                if contour_points[k][2]:
                                    px, py = contour_points[k][0], contour_points[k][1]
                                    break

                        # Interpolate
                        for t in range(1, 21):
                            t = t / 20.0
                            x = (1-t)**2 * px + 2*(1-t)*t * x0 + t**2 * x1
                            y = (1-t)**2 * py + 2*(1-t)*t * y0 + t**2 * y1
                            points.append(Point(x, y))
                        j += 2
                    else:
                        # Next is also off-curve: implicit on-curve at midpoint
                        mid_x = (x0 + x1) / 2
                        mid_y = (y0 + y1) / 2

                        if points:
                            px, py = points[-1].x, points[-1].y
                        else:
                            for k in range(n-1, -1, -1):
                                if contour_points[k][2]:
                                    px, py = contour_points[k][0], contour_points[k][1]
                                    break

                        # Interpolate to midpoint
                        for t in range(1, 21):
                            t = t / 20.0
                            x = (1-t)**2 * px + 2*(1-t)*t * x0 + t**2 * mid_x
                            y = (1-t)**2 * py + 2*(1-t)*t * y0 + t**2 * mid_y
                            points.append(Point(x, y))
                        j += 1

            if points:
                path = Path(
                    points=points,
                    path_type=PathType.OUTER,
                    is_closed=True
                )
                paths.append(path)

            start = end

        return paths
