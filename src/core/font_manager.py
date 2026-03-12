"""
Font Manager - System font scanning and management
"""
from typing import Dict, List
import os
import sys
import freetype


class FontManager:
    """Manages system fonts for text generation"""

    def __init__(self):
        self._fonts: Dict[str, str] = {}
        self._scan_system_fonts()

    def _get_system_font_dirs(self) -> List[str]:
        """Get system font directories based on OS"""
        dirs = []

        if sys.platform == "win32":
            # Windows font directories
            dirs.append(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"))
            local_fonts = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")
            if os.path.exists(local_fonts):
                dirs.append(local_fonts)
        elif sys.platform == "darwin":
            # macOS font directories
            dirs.extend([
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ])
        else:
            # Linux font directories
            dirs.extend([
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts")
            ])

        return [d for d in dirs if os.path.exists(d)]

    def _scan_system_fonts(self):
        """Scan system fonts and cache font name -> path mapping"""
        font_dirs = self._get_system_font_dirs()

        for font_dir in font_dirs:
            for root, _, files in os.walk(font_dir):
                for file in files:
                    if file.lower().endswith(('.ttf', '.otf')):
                        font_path = os.path.join(root, file)
                        try:
                            face = freetype.Face(font_path)
                            # Get real font name (e.g., "Arial" not "arial")
                            font_name = face.family_name.decode('utf-8')

                            # Store first occurrence of each font name
                            if font_name not in self._fonts:
                                self._fonts[font_name] = font_path
                        except Exception:
                            # Skip fonts that can't be loaded
                            continue

    def get_font_names(self) -> List[str]:
        """Get list of all available font names"""
        return sorted(self._fonts.keys())

    def get_font_path(self, font_name: str) -> str:
        """Get font file path by font name"""
        return self._fonts.get(font_name, "")

    def has_font(self, font_name: str) -> bool:
        """Check if font exists"""
        return font_name in self._fonts
