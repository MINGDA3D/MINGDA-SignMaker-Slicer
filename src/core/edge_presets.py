"""
MINGDA SignMaker - Edge Profile Preset Library

Provides 20 preset edge profile templates based on INC-S, categorized as:
- Zigzag: Decorative zigzag edges
- Wave: Smooth S-shaped waves
- Arc: Arc bulges
- Step: Step transitions
- Mixed: Combined elements
- Bevel: Simple bevels

Each preset contains:
- Name and description
- DXF source file path
- Default width
- Interpolation type
- Preloaded control points (if available)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import os

from .types import EdgeProfile, EdgeProfileType, InterpolationType


class ProfileCategory(Enum):
    """Profile categories"""
    ZIGZAG = "zigzag"       # Zigzag
    WAVE = "wave"           # Wave
    ARC = "arc"             # Arc
    STEP = "step"           # Step
    MIXED = "mixed"         # Mixed
    BEVEL = "bevel"         # Bevel


@dataclass
class PresetInfo:
    """Preset information"""
    name: str               # Internal name (English)
    display_name: str       # Display name (for UI, translatable)
    description: str        # Description (for UI, translatable)
    category: ProfileCategory  # Category
    source_file: str        # DXF source file (relative path)
    default_width: float    # Default width (mm)
    preview_image: str = "" # Preview image path (relative path)
    interpolation: InterpolationType = InterpolationType.BSPLINE
    # Preloaded control points (normalized)
    control_points: List[Tuple[float, float]] = field(default_factory=list)


# INC-S preset template definitions
PRESET_DEFINITIONS: Dict[str, PresetInfo] = {
    # === Zigzag ===
    "zigzag_4": PresetInfo(
        name="zigzag_4",
        display_name="U-Shaped Letter",
        description="U-shaped letter outline template",
        category=ProfileCategory.MIXED,
        source_file="resources/profiles/u_letter_outline.dxf",
        default_width=6.0,
        preview_image="",
    ),
    "zigzag_3": PresetInfo(
        name="zigzag_3",
        display_name="3-Tooth Zigzag",
        description="3 zigzag teeth, medium decoration",
        category=ProfileCategory.ZIGZAG,
        source_file="resources/profiles/profile_3.dxf",
        default_width=1.5,
        preview_image="resources/profiles/profile_3.jpg",
    ),
    "zigzag_2": PresetInfo(
        name="zigzag_2",
        display_name="2-Tooth Zigzag",
        description="2 zigzag teeth, simple and clean",
        category=ProfileCategory.ZIGZAG,
        source_file="resources/profiles/profile_4.dxf",
        default_width=1.1,
        preview_image="resources/profiles/profile_4.jpg",
    ),
    "zigzag_5": PresetInfo(
        name="zigzag_5",
        display_name="5-Tooth Zigzag",
        description="5 zigzag teeth, complex decoration",
        category=ProfileCategory.ZIGZAG,
        source_file="resources/profiles/profile_5.dxf",
        default_width=1.1,
        preview_image="resources/profiles/profile_5.jpg",
    ),

    # === Wave ===
    "wave_3": PresetInfo(
        name="wave_3",
        display_name="3-Wave",
        description="3 smooth S-shaped waves",
        category=ProfileCategory.WAVE,
        source_file="resources/profiles/profile_2.dxf",
        default_width=2.1,
        preview_image="resources/profiles/profile_2.jpg",
    ),
    "wave_3b": PresetInfo(
        name="wave_3b",
        display_name="3-Wave B",
        description="3 smooth waves (variant)",
        category=ProfileCategory.WAVE,
        source_file="resources/profiles/profile_6.dxf",
        default_width=2.1,
        preview_image="resources/profiles/profile_6.jpg",
    ),
    "wave_2": PresetInfo(
        name="wave_2",
        display_name="2-Wave",
        description="2 smooth waves",
        category=ProfileCategory.WAVE,
        source_file="resources/profiles/profile_7.dxf",
        default_width=1.6,
        preview_image="resources/profiles/profile_7.jpg",
    ),

    # === Arc ===
    "arc_single": PresetInfo(
        name="arc_single",
        display_name="Single Bump",
        description="Single arc bump in the middle",
        category=ProfileCategory.ARC,
        source_file="resources/profiles/profile_8.dxf",
        default_width=1.6,
        preview_image="resources/profiles/profile_8.jpg",
    ),
    "arc_large": PresetInfo(
        name="arc_large",
        display_name="Large Arc",
        description="Large radius arc transition",
        category=ProfileCategory.ARC,
        source_file="resources/profiles/profile_9.dxf",
        default_width=3.0,
        preview_image="resources/profiles/profile_9.jpg",
    ),
    "arc_platform": PresetInfo(
        name="arc_platform",
        display_name="Arc with Platform",
        description="Arc transition with top/bottom platforms",
        category=ProfileCategory.ARC,
        source_file="resources/profiles/profile_10.dxf",
        default_width=4.0,
        preview_image="resources/profiles/profile_10.jpg",
    ),
    "arc_platform_b": PresetInfo(
        name="arc_platform_b",
        display_name="Arc with Platform B",
        description="Arc with platform (variant)",
        category=ProfileCategory.ARC,
        source_file="resources/profiles/profile_11.dxf",
        default_width=4.3,
        preview_image="resources/profiles/profile_11.jpg",
    ),

    # === Step ===
    "step_small": PresetInfo(
        name="step_small",
        display_name="Center V Peak",
        description="Centered V-shaped peak",
        category=ProfileCategory.STEP,
        source_file="resources/profiles/profile_12.dxf",
        default_width=5.3,
        preview_image="resources/profiles/profile_12.jpg",
    ),
    "step_double": PresetInfo(
        name="step_double",
        display_name="Double Step",
        description="Two-level step",
        category=ProfileCategory.STEP,
        source_file="resources/profiles/profile_13.dxf",
        default_width=0.5,
        preview_image="resources/profiles/profile_13.jpg",
    ),

    # === Mixed ===
    "mixed_step_arc": PresetInfo(
        name="mixed_step_arc",
        display_name="Step + Arc",
        description="Combination of step and arc",
        category=ProfileCategory.MIXED,
        source_file="resources/profiles/profile_14.dxf",
        default_width=2.2,
        preview_image="resources/profiles/profile_14.jpg",
    ),
    "mixed_complex": PresetInfo(
        name="mixed_complex",
        display_name="Complex Mixed",
        description="Double arc + step complex combination",
        category=ProfileCategory.MIXED,
        source_file="resources/profiles/profile_15.dxf",
        default_width=2.4,
        preview_image="resources/profiles/profile_15.jpg",
    ),

    # === Bevel ===
    "bevel_simple": PresetInfo(
        name="bevel_simple",
        display_name="Simple Bevel",
        description="Linear bevel transition",
        category=ProfileCategory.BEVEL,
        source_file="",  # No DXF needed, generated directly
        default_width=5.0,
        preview_image="",  # No preview, dynamically generated
        interpolation=InterpolationType.LINEAR,
        control_points=[(0.0, 0.0), (1.0, 1.0)],
    ),
    "bevel_large": PresetInfo(
        name="bevel_large",
        display_name="Large Bevel",
        description="Large angle bevel transition",
        category=ProfileCategory.BEVEL,
        source_file="resources/profiles/bevel_large.dxf",
        default_width=6.0,
        preview_image="resources/profiles/bevel_large.jpg",
    ),
    "bevel_steep": PresetInfo(
        name="bevel_steep",
        display_name="Steep Bevel",
        description="Steep bevel (large width)",
        category=ProfileCategory.BEVEL,
        source_file="resources/profiles/bevel_steep.dxf",
        default_width=19.0,
        preview_image="resources/profiles/bevel_steep.jpg",
    ),
}


class EdgePresetManager:
    """Edge profile preset manager

    Provides loading, querying and management of preset templates.

    Usage:
        manager = EdgePresetManager()

        # Get all presets
        presets = manager.get_preset_list()

        # Get EdgeProfile for a preset
        profile = manager.get_preset_profile("arc_single", bevel_width=5.0)

        # Get by category
        arcs = manager.get_presets_by_category(ProfileCategory.ARC)
    """

    def __init__(self, base_path: str = ""):
        """
        Initialize preset manager

        Args:
            base_path: Base path for resource files (default: auto-detect)
        """
        if base_path:
            self.base_path = base_path
        else:
            # Auto-detect base path (支持打包后的exe)
            self.base_path = self._get_resource_base_path()
        self._cache: Dict[str, EdgeProfile] = {}
        self._loader = None

    def _get_resource_base_path(self) -> str:
        """
        获取资源文件基础路径

        支持开发环境和PyInstaller打包后的环境
        """
        import sys

        # PyInstaller打包后，资源文件在_MEIPASS目录下
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS

        # 开发环境：返回项目根目录
        # 假设edge_presets.py在src/core/目录下
        current_file = os.path.abspath(__file__)
        src_core_dir = os.path.dirname(current_file)
        src_dir = os.path.dirname(src_core_dir)
        project_root = os.path.dirname(src_dir)
        return project_root

    def _get_loader(self):
        """Get DXF loader (lazy loading)"""
        if self._loader is None:
            from .edge_profile_loader import EdgeProfileDXFLoader
            self._loader = EdgeProfileDXFLoader()
        return self._loader

    def get_preset_list(self) -> List[Dict]:
        """Get list of all presets

        Returns:
            List of preset info dictionaries
        """
        return [
            {
                "name": name,
                "display_name": info.display_name,
                "description": info.description,
                "category": info.category.value,
                "default_width": info.default_width,
                "preview_image": info.preview_image,
            }
            for name, info in PRESET_DEFINITIONS.items()
        ]

    def get_presets_by_category(self, category: ProfileCategory) -> List[Dict]:
        """Get presets by category"""
        return [
            {
                "name": name,
                "display_name": info.display_name,
                "description": info.description,
                "default_width": info.default_width,
                "preview_image": info.preview_image,
            }
            for name, info in PRESET_DEFINITIONS.items()
            if info.category == category
        ]

    def get_category_list(self) -> List[Dict]:
        """Get list of categories"""
        return [
            {"value": cat.value, "name": self._get_category_name(cat)}
            for cat in ProfileCategory
        ]

    def _get_category_name(self, category: ProfileCategory) -> str:
        """Get category display name"""
        names = {
            ProfileCategory.ZIGZAG: "Zigzag",
            ProfileCategory.WAVE: "Wave",
            ProfileCategory.ARC: "Arc",
            ProfileCategory.STEP: "Step",
            ProfileCategory.MIXED: "Mixed",
            ProfileCategory.BEVEL: "Bevel",
        }
        return names.get(category, category.value)

    def get_preset_profile(
        self,
        preset_name: str,
        bevel_width: Optional[float] = None
    ) -> Optional[EdgeProfile]:
        """
        Get EdgeProfile object for a preset

        Args:
            preset_name: Preset name
            bevel_width: Override default width (optional)

        Returns:
            EdgeProfile object, or None if preset doesn't exist
        """
        if preset_name not in PRESET_DEFINITIONS:
            return None

        # Check cache
        if preset_name in self._cache:
            profile = self._cache[preset_name]
            # If width override needed, create a copy
            if bevel_width is not None:
                return self._copy_profile_with_width(profile, bevel_width)
            return profile

        info = PRESET_DEFINITIONS[preset_name]

        # If predefined control points exist, use them directly
        if info.control_points:
            profile = EdgeProfile(
                profile_type=EdgeProfileType.PRESET,
                preset_name=preset_name,
                control_points=info.control_points,
                interpolation=info.interpolation,
                sample_points=100,
                original_width=info.default_width,
                original_height=30.0,  # Default height
                name=info.display_name,
                description=info.description
            )
        else:
            # Load from DXF file
            dxf_path = os.path.join(self.base_path, info.source_file)

            if not os.path.exists(dxf_path):
                # Try using path directly
                dxf_path = info.source_file

            try:
                loader = self._get_loader()
                profile = loader.load_from_dxf(dxf_path)
                # Update to preset type
                profile.profile_type = EdgeProfileType.PRESET
                profile.preset_name = preset_name
                profile.name = info.display_name
                profile.description = info.description
            except Exception as e:
                print(f"[EdgePresetManager] Warning: Failed to load preset {preset_name}: {e}")
                # Fallback to simple bevel
                profile = EdgeProfile(
                    profile_type=EdgeProfileType.PRESET,
                    preset_name=preset_name,
                    control_points=[(0.0, 0.0), (1.0, 1.0)],
                    interpolation=InterpolationType.LINEAR,
                    original_width=info.default_width,
                    original_height=30.0,
                    name=info.display_name,
                    description=f"Fallback: {info.description}"
                )

        # Cache
        self._cache[preset_name] = profile

        if bevel_width is not None:
            return self._copy_profile_with_width(profile, bevel_width)

        return profile

    def _copy_profile_with_width(
        self,
        profile: EdgeProfile,
        new_width: float
    ) -> EdgeProfile:
        """Create a copy with new width"""
        return EdgeProfile(
            profile_type=profile.profile_type,
            preset_name=profile.preset_name,
            control_points=profile.control_points.copy(),
            interpolation=profile.interpolation,
            sample_points=profile.sample_points,
            original_width=new_width,
            original_height=profile.original_height,
            source_file=profile.source_file,
            name=profile.name,
            description=profile.description
        )

    def get_preset_info(self, preset_name: str) -> Optional[PresetInfo]:
        """Get preset info"""
        return PRESET_DEFINITIONS.get(preset_name)

    def clear_cache(self):
        """Clear preset cache"""
        self._cache.clear()


# Module-level convenience functions
_default_manager = None


def get_preset_profile(preset_name: str, bevel_width: Optional[float] = None) -> Optional[EdgeProfile]:
    """Get EdgeProfile for a preset (convenience function)"""
    global _default_manager
    if _default_manager is None:
        _default_manager = EdgePresetManager()
    return _default_manager.get_preset_profile(preset_name, bevel_width)


def get_all_presets() -> List[Dict]:
    """Get all presets (convenience function)"""
    global _default_manager
    if _default_manager is None:
        _default_manager = EdgePresetManager()
    return _default_manager.get_preset_list()
