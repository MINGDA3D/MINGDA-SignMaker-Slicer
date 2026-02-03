"""
MINGDA SignMaker - 异形边预设模板库

提供基于INC-S的20个预设异形边模板，分为以下类别：
- 锯齿类 (Zigzag): 装饰性锯齿边缘
- 波浪类 (Wave): 平滑的S形波浪
- 圆弧类 (Arc): 圆弧凸起
- 台阶类 (Step): 台阶过渡
- 组合类 (Mixed): 多种元素组合
- 斜边类 (Bevel): 简单斜边

每个预设包含：
- 名称和描述
- DXF源文件路径
- 默认宽度
- 插值方式
- 预加载的控制点（如果可用）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import os

from .types import EdgeProfile, EdgeProfileType, InterpolationType


class ProfileCategory(Enum):
    """预设分类"""
    ZIGZAG = "zigzag"       # 锯齿类
    WAVE = "wave"           # 波浪类
    ARC = "arc"             # 圆弧类
    STEP = "step"           # 台阶类
    MIXED = "mixed"         # 组合类
    BEVEL = "bevel"         # 斜边类


@dataclass
class PresetInfo:
    """预设信息"""
    name: str               # 内部名称（英文）
    display_name: str       # 显示名称（中文）
    description: str        # 描述
    category: ProfileCategory  # 分类
    source_file: str        # DXF源文件（相对路径）
    default_width: float    # 默认宽度 (mm)
    preview_image: str = "" # 预览图路径（相对路径）
    interpolation: InterpolationType = InterpolationType.BSPLINE
    # 预加载的控制点（归一化）
    control_points: List[Tuple[float, float]] = field(default_factory=list)


# INC-S预设模板定义
PRESET_DEFINITIONS: Dict[str, PresetInfo] = {
    # === 锯齿类 ===
    "zigzag_4": PresetInfo(
        name="zigzag_4",
        display_name="四锯齿边",
        description="4个锐角锯齿，装饰性强",
        category=ProfileCategory.ZIGZAG,
        source_file="resources/profiles/profile_1.dxf",
        default_width=1.1,
        preview_image="resources/profiles/profile_1.jpg",
    ),
    "zigzag_3": PresetInfo(
        name="zigzag_3",
        display_name="三锯齿边",
        description="3个锯齿，中等装饰",
        category=ProfileCategory.ZIGZAG,
        source_file="resources/profiles/profile_3.dxf",
        default_width=1.5,
        preview_image="resources/profiles/profile_3.jpg",
    ),
    "zigzag_2": PresetInfo(
        name="zigzag_2",
        display_name="双锯齿边",
        description="2个锯齿，简洁大方",
        category=ProfileCategory.ZIGZAG,
        source_file="resources/profiles/profile_4.dxf",
        default_width=1.1,
        preview_image="resources/profiles/profile_4.jpg",
    ),
    "zigzag_5": PresetInfo(
        name="zigzag_5",
        display_name="五锯齿边",
        description="5个锯齿，复杂装饰",
        category=ProfileCategory.ZIGZAG,
        source_file="resources/profiles/profile_5.dxf",
        default_width=1.1,
        preview_image="resources/profiles/profile_5.jpg",
    ),

    # === 波浪类 ===
    "wave_3": PresetInfo(
        name="wave_3",
        display_name="三波浪边",
        description="3个平滑S形波浪",
        category=ProfileCategory.WAVE,
        source_file="resources/profiles/profile_2.dxf",
        default_width=2.1,
        preview_image="resources/profiles/profile_2.jpg",
    ),
    "wave_3b": PresetInfo(
        name="wave_3b",
        display_name="三波浪边B",
        description="3个平滑波浪（变体）",
        category=ProfileCategory.WAVE,
        source_file="resources/profiles/profile_6.dxf",
        default_width=2.1,
        preview_image="resources/profiles/profile_6.jpg",
    ),
    "wave_2": PresetInfo(
        name="wave_2",
        display_name="双波浪边",
        description="2个平滑波浪",
        category=ProfileCategory.WAVE,
        source_file="resources/profiles/profile_7.dxf",
        default_width=1.6,
        preview_image="resources/profiles/profile_7.jpg",
    ),

    # === 圆弧类 ===
    "arc_single": PresetInfo(
        name="arc_single",
        display_name="单凸起",
        description="中部单个圆弧凸起",
        category=ProfileCategory.ARC,
        source_file="resources/profiles/profile_8.dxf",
        default_width=1.6,
        preview_image="resources/profiles/profile_8.jpg",
    ),
    "arc_large": PresetInfo(
        name="arc_large",
        display_name="大圆弧",
        description="大弧度圆弧过渡",
        category=ProfileCategory.ARC,
        source_file="resources/profiles/profile_9.dxf",
        default_width=3.0,
        preview_image="resources/profiles/profile_9.jpg",
    ),
    "arc_platform": PresetInfo(
        name="arc_platform",
        display_name="圆弧带平台",
        description="圆弧过渡带上下平台",
        category=ProfileCategory.ARC,
        source_file="resources/profiles/profile_10.dxf",
        default_width=4.0,
        preview_image="resources/profiles/profile_10.jpg",
    ),
    "arc_platform_b": PresetInfo(
        name="arc_platform_b",
        display_name="圆弧带平台B",
        description="圆弧过渡带平台（变体）",
        category=ProfileCategory.ARC,
        source_file="resources/profiles/profile_11.dxf",
        default_width=4.3,
        preview_image="resources/profiles/profile_11.jpg",
    ),

    # === 台阶类 ===
    "step_small": PresetInfo(
        name="step_small",
        display_name="小台阶",
        description="单级小台阶",
        category=ProfileCategory.STEP,
        source_file="resources/profiles/profile_12.dxf",
        default_width=0.6,
        preview_image="resources/profiles/profile_12.jpg",
    ),
    "step_double": PresetInfo(
        name="step_double",
        display_name="双台阶",
        description="双级台阶",
        category=ProfileCategory.STEP,
        source_file="resources/profiles/profile_13.dxf",
        default_width=0.5,
        preview_image="resources/profiles/profile_13.jpg",
    ),

    # === 组合类 ===
    "mixed_step_arc": PresetInfo(
        name="mixed_step_arc",
        display_name="台阶+圆弧",
        description="台阶与圆弧组合",
        category=ProfileCategory.MIXED,
        source_file="resources/profiles/profile_14.dxf",
        default_width=2.2,
        preview_image="resources/profiles/profile_14.jpg",
    ),
    "mixed_complex": PresetInfo(
        name="mixed_complex",
        display_name="复杂组合",
        description="双圆弧+台阶复杂组合",
        category=ProfileCategory.MIXED,
        source_file="resources/profiles/profile_15.dxf",
        default_width=2.4,
        preview_image="resources/profiles/profile_15.jpg",
    ),

    # === 斜边类 ===
    "bevel_simple": PresetInfo(
        name="bevel_simple",
        display_name="简单斜边",
        description="线性斜边过渡",
        category=ProfileCategory.BEVEL,
        source_file="",  # 无需DXF，直接生成
        default_width=5.0,
        preview_image="",  # 无预览图，使用动态生成
        interpolation=InterpolationType.LINEAR,
        control_points=[(0.0, 0.0), (1.0, 1.0)],
    ),
    "bevel_large": PresetInfo(
        name="bevel_large",
        display_name="大斜边",
        description="大角度斜边过渡",
        category=ProfileCategory.BEVEL,
        source_file="resources/profiles/bevel_large.dxf",
        default_width=6.0,
        preview_image="resources/profiles/bevel_large.jpg",
    ),
    "bevel_steep": PresetInfo(
        name="bevel_steep",
        display_name="陡斜边",
        description="陡峭斜边（大宽度）",
        category=ProfileCategory.BEVEL,
        source_file="resources/profiles/bevel_steep.dxf",
        default_width=19.0,
        preview_image="resources/profiles/bevel_steep.jpg",
    ),
}


class EdgePresetManager:
    """异形边预设管理器

    提供预设模板的加载、查询和管理功能。

    使用示例:
        manager = EdgePresetManager()

        # 获取所有预设列表
        presets = manager.get_preset_list()

        # 获取指定预设的EdgeProfile
        profile = manager.get_preset_profile("arc_single", bevel_width=5.0)

        # 按分类获取
        arcs = manager.get_presets_by_category(ProfileCategory.ARC)
    """

    def __init__(self, base_path: str = ""):
        """
        初始化预设管理器

        Args:
            base_path: 项目根目录路径，用于定位DXF文件
        """
        self.base_path = base_path or self._detect_base_path()
        self._cache: Dict[str, EdgeProfile] = {}
        self._loader = None

    def _detect_base_path(self) -> str:
        """自动检测项目根目录"""
        # 尝试从当前文件位置推断
        current_file = os.path.abspath(__file__)
        # src/core/edge_presets.py -> 项目根目录
        return os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

    def _get_loader(self):
        """延迟加载DXF加载器"""
        if self._loader is None:
            from .edge_profile_loader import EdgeProfileDXFLoader
            self._loader = EdgeProfileDXFLoader()
        return self._loader

    def get_preset_list(self) -> List[Dict]:
        """
        获取所有预设列表（用于UI下拉框）

        Returns:
            预设信息列表，每个元素包含 name, display_name, category, description
        """
        result = []
        for name, info in PRESET_DEFINITIONS.items():
            # 构建预览图完整路径
            preview_path = ""
            if info.preview_image:
                preview_path = os.path.join(self.base_path, info.preview_image)

            result.append({
                "name": name,
                "display_name": info.display_name,
                "category": info.category.value,
                "category_name": self._get_category_name(info.category),
                "description": info.description,
                "default_width": info.default_width,
                "preview_image": preview_path,
            })
        return result

    def get_presets_by_category(
        self,
        category: ProfileCategory
    ) -> List[Dict]:
        """获取指定分类的预设"""
        return [
            p for p in self.get_preset_list()
            if p["category"] == category.value
        ]

    def get_category_list(self) -> List[Dict]:
        """获取分类列表"""
        return [
            {"value": cat.value, "name": self._get_category_name(cat)}
            for cat in ProfileCategory
        ]

    def _get_category_name(self, category: ProfileCategory) -> str:
        """获取分类显示名称"""
        names = {
            ProfileCategory.ZIGZAG: "锯齿类",
            ProfileCategory.WAVE: "波浪类",
            ProfileCategory.ARC: "圆弧类",
            ProfileCategory.STEP: "台阶类",
            ProfileCategory.MIXED: "组合类",
            ProfileCategory.BEVEL: "斜边类",
        }
        return names.get(category, category.value)

    def get_preset_profile(
        self,
        preset_name: str,
        bevel_width: Optional[float] = None
    ) -> Optional[EdgeProfile]:
        """
        获取预设的EdgeProfile对象

        Args:
            preset_name: 预设名称
            bevel_width: 覆盖默认宽度（可选）

        Returns:
            EdgeProfile对象，如果预设不存在则返回None
        """
        if preset_name not in PRESET_DEFINITIONS:
            return None

        # 检查缓存
        if preset_name in self._cache:
            profile = self._cache[preset_name]
            # 如果需要覆盖宽度，创建副本
            if bevel_width is not None:
                return self._copy_profile_with_width(profile, bevel_width)
            return profile

        info = PRESET_DEFINITIONS[preset_name]

        # 如果有预定义的控制点，直接使用
        if info.control_points:
            profile = EdgeProfile(
                profile_type=EdgeProfileType.PRESET,
                preset_name=preset_name,
                control_points=info.control_points,
                interpolation=info.interpolation,
                sample_points=100,
                original_width=info.default_width,
                original_height=30.0,  # 默认高度
                name=info.display_name,
                description=info.description
            )
        else:
            # 从DXF文件加载
            dxf_path = os.path.join(self.base_path, info.source_file)
            if not os.path.exists(dxf_path):
                # 尝试直接使用路径
                dxf_path = info.source_file

            try:
                loader = self._get_loader()
                profile = loader.load_from_dxf(dxf_path)
                # 更新为预设类型
                profile.profile_type = EdgeProfileType.PRESET
                profile.preset_name = preset_name
                profile.name = info.display_name
                profile.description = info.description
            except Exception as e:
                print(f"Warning: Failed to load preset {preset_name}: {e}")
                # 回退到简单斜边
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

        # 缓存
        self._cache[preset_name] = profile

        if bevel_width is not None:
            return self._copy_profile_with_width(profile, bevel_width)

        return profile

    def _copy_profile_with_width(
        self,
        profile: EdgeProfile,
        bevel_width: float
    ) -> EdgeProfile:
        """创建带有新宽度的轮廓副本"""
        return EdgeProfile(
            profile_type=profile.profile_type,
            preset_name=profile.preset_name,
            control_points=profile.control_points.copy(),
            interpolation=profile.interpolation,
            sample_points=profile.sample_points,
            original_width=bevel_width,
            original_height=profile.original_height,
            source_file=profile.source_file,
            name=profile.name,
            description=profile.description
        )

    def get_preset_info(self, preset_name: str) -> Optional[PresetInfo]:
        """获取预设信息"""
        return PRESET_DEFINITIONS.get(preset_name)

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()


# 便捷函数
def get_preset_profile(preset_name: str) -> Optional[EdgeProfile]:
    """获取预设的EdgeProfile（便捷函数）"""
    manager = EdgePresetManager()
    return manager.get_preset_profile(preset_name)


def get_all_presets() -> List[Dict]:
    """获取所有预设列表（便捷函数）"""
    manager = EdgePresetManager()
    return manager.get_preset_list()
