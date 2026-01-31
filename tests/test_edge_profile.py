"""
SignMaker Slicer - 异形边模块单元测试

测试内容：
1. EdgeProfile 数据类
2. EdgeProfileGenerator 插值算法
3. EdgeProfileDXFLoader DXF加载
4. EdgePresetManager 预设管理
5. SliceEngine 异形边切片集成
"""

import pytest
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.types import (
    EdgeProfile, EdgeProfileType, InterpolationType,
    EdgeType, Point, Path, Contour, SliceParams, ShellParams
)
from src.core.edge_profile_generator import EdgeProfileGenerator
from src.core.edge_profile_loader import EdgeProfileDXFLoader
from src.core.edge_presets import (
    EdgePresetManager, ProfileCategory, PRESET_DEFINITIONS,
    get_preset_profile, get_all_presets
)
from src.core.slice_engine import SliceEngine


# =============================================================================
# EdgeProfile 测试
# =============================================================================

class TestEdgeProfile:
    """EdgeProfile 数据类测试"""

    def test_create_from_preset(self):
        """测试从预设创建"""
        profile = EdgeProfile.from_preset("arc_single")
        assert profile.profile_type == EdgeProfileType.PRESET
        assert profile.preset_name == "arc_single"

    def test_create_from_control_points(self):
        """测试从控制点创建"""
        points = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]
        profile = EdgeProfile.from_control_points(
            points, InterpolationType.BEZIER, "Test"
        )
        assert profile.profile_type == EdgeProfileType.CUSTOM
        assert len(profile.control_points) == 3
        assert profile.interpolation == InterpolationType.BEZIER
        assert profile.name == "Test"

    def test_get_offset_at_height(self):
        """测试高度偏移计算"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (1.0, 1.0)],
            InterpolationType.LINEAR
        )
        # 底部偏移应为0
        offset = profile.get_offset_at_height(0.0, bevel_width=5.0)
        assert offset == pytest.approx(0.0, abs=0.01)

        # 中间偏移应为-2.5 (内缩)
        offset = profile.get_offset_at_height(0.5, bevel_width=5.0)
        assert offset == pytest.approx(-2.5, abs=0.01)

        # 顶部偏移应为-5.0
        offset = profile.get_offset_at_height(1.0, bevel_width=5.0)
        assert offset == pytest.approx(-5.0, abs=0.01)

    def test_serialization(self):
        """测试序列化/反序列化"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (0.5, 0.3), (1.0, 1.0)],
            InterpolationType.CUBIC,
            "SerializeTest"
        )
        profile.description = "Test description"

        # 序列化
        data = profile.to_dict()
        assert "control_points" in data
        assert data["interpolation"] == "cubic"

        # 反序列化
        restored = EdgeProfile.from_dict(data)
        assert restored.name == "SerializeTest"
        assert len(restored.control_points) == 3
        assert restored.interpolation == InterpolationType.CUBIC


# =============================================================================
# EdgeProfileGenerator 测试
# =============================================================================

class TestEdgeProfileGenerator:
    """EdgeProfileGenerator 插值算法测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.generator = EdgeProfileGenerator()

    def test_linear_interpolation(self):
        """测试线性插值"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (1.0, 1.0)],
            InterpolationType.LINEAR
        )
        profile.sample_points = 11

        curve = self.generator.generate_profile_curve(
            profile, bevel_width=10.0, shell_height=30.0
        )

        assert len(curve) == 11
        # 检查起点和终点
        assert curve[0][0] == pytest.approx(0.0, abs=0.1)
        assert curve[0][1] == pytest.approx(0.0, abs=0.1)
        assert curve[-1][0] == pytest.approx(10.0, abs=0.1)
        assert curve[-1][1] == pytest.approx(30.0, abs=0.1)

    def test_bezier_interpolation(self):
        """测试贝塞尔曲线插值"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (1.0, 0.3), (0.0, 0.7), (1.0, 1.0)],
            InterpolationType.BEZIER
        )
        profile.sample_points = 20

        curve = self.generator.generate_profile_curve(
            profile, bevel_width=5.0, shell_height=30.0
        )

        assert len(curve) == 20
        # 贝塞尔曲线应该产生平滑的S形

    def test_cubic_spline_interpolation(self):
        """测试三次样条插值"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (0.3, 0.3), (0.7, 0.7), (1.0, 1.0)],
            InterpolationType.CUBIC
        )
        profile.sample_points = 30

        curve = self.generator.generate_profile_curve(
            profile, bevel_width=4.0, shell_height=30.0
        )

        assert len(curve) == 30

    def test_bspline_interpolation(self):
        """测试B样条插值"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (0.2, 0.2), (0.5, 0.5), (0.8, 0.8), (1.0, 1.0)],
            InterpolationType.BSPLINE
        )
        profile.sample_points = 30

        curve = self.generator.generate_profile_curve(
            profile, bevel_width=4.0, shell_height=30.0
        )

        assert len(curve) == 30

    def test_layer_mapping(self):
        """测试层高映射"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (1.0, 1.0)],
            InterpolationType.LINEAR
        )
        profile.sample_points = 100

        curve = self.generator.generate_profile_curve(
            profile, bevel_width=5.0, shell_height=30.0
        )

        offsets = self.generator.map_profile_to_layers(
            curve, layer_height=0.3, shell_height=30.0
        )

        assert len(offsets) == 100
        # 底层偏移接近0
        assert offsets[0] == pytest.approx(0.0, abs=0.1)
        # 顶层偏移接近-5
        assert offsets[99] == pytest.approx(-5.0, abs=0.1)

    def test_empty_profile(self):
        """测试空轮廓处理"""
        profile = EdgeProfile()
        curve = self.generator.generate_profile_curve(
            profile, bevel_width=5.0, shell_height=30.0
        )
        # 应该返回默认直线
        assert len(curve) >= 2


# =============================================================================
# EdgeProfileDXFLoader 测试
# =============================================================================

class TestEdgeProfileDXFLoader:
    """DXF加载器测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.loader = EdgeProfileDXFLoader()
        self.test_dir = "docs/真材INC-26/special_shape"

    def test_load_zigzag_profile(self):
        """测试加���锯齿边DXF"""
        dxf_path = os.path.join(self.test_dir, "异型边1.dxf")
        if not os.path.exists(dxf_path):
            pytest.skip("Test DXF file not found")

        profile = self.loader.load_from_dxf(dxf_path)

        assert profile.profile_type == EdgeProfileType.DXF
        assert profile.interpolation == InterpolationType.BSPLINE
        assert len(profile.control_points) > 0
        assert profile.original_width == pytest.approx(1.1, rel=0.1)
        assert profile.original_height == pytest.approx(30.0, rel=0.1)

    def test_load_arc_profile(self):
        """测试加载圆弧边DXF"""
        dxf_path = os.path.join(self.test_dir, "异型边8.dxf")
        if not os.path.exists(dxf_path):
            pytest.skip("Test DXF file not found")

        profile = self.loader.load_from_dxf(dxf_path)

        assert profile.original_width == pytest.approx(1.6, rel=0.1)
        assert profile.original_height == pytest.approx(30.0, rel=0.1)

    def test_load_all_presets(self):
        """测试加载所有预设模板"""
        if not os.path.exists(self.test_dir):
            pytest.skip("Test directory not found")

        profiles = self.loader.load_all_from_directory(self.test_dir)

        assert len(profiles) >= 15  # 应该至少有15个模板
        for profile in profiles:
            assert profile.original_height == pytest.approx(30.0, rel=0.5) or \
                   profile.original_height == pytest.approx(40.0, rel=0.5) or \
                   profile.original_height == pytest.approx(50.0, rel=0.5)

    def test_get_profile_info(self):
        """测试获取轮廓信息"""
        dxf_path = os.path.join(self.test_dir, "异型边1.dxf")
        if not os.path.exists(dxf_path):
            pytest.skip("Test DXF file not found")

        info = self.loader.get_profile_info(dxf_path)

        assert "error" not in info
        assert info["type"] == "SPLINE"
        assert info["control_points"] > 0

    def test_file_not_found(self):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError):
            self.loader.load_from_dxf("nonexistent.dxf")


# =============================================================================
# EdgePresetManager 测试
# =============================================================================

class TestEdgePresetManager:
    """预设管理器测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.manager = EdgePresetManager()

    def test_get_preset_list(self):
        """测试获取预设列表"""
        presets = self.manager.get_preset_list()

        assert len(presets) >= 15
        for preset in presets:
            assert "name" in preset
            assert "display_name" in preset
            assert "category" in preset

    def test_get_presets_by_category(self):
        """测试按分类获取预设"""
        arcs = self.manager.get_presets_by_category(ProfileCategory.ARC)
        assert len(arcs) >= 3

        zigzags = self.manager.get_presets_by_category(ProfileCategory.ZIGZAG)
        assert len(zigzags) >= 3

    def test_get_preset_profile_simple(self):
        """测试获取简单斜边预设"""
        profile = self.manager.get_preset_profile("bevel_simple")

        assert profile is not None
        assert profile.preset_name == "bevel_simple"
        assert len(profile.control_points) == 2

    def test_get_preset_profile_from_dxf(self):
        """测试获取DXF预设"""
        if not os.path.exists("docs/真材INC-26/special_shape"):
            pytest.skip("DXF templates not found")

        profile = self.manager.get_preset_profile("arc_single")

        assert profile is not None
        assert profile.profile_type == EdgeProfileType.PRESET
        assert len(profile.control_points) > 0

    def test_get_preset_with_custom_width(self):
        """测试使用自定义宽度获取预设"""
        profile = self.manager.get_preset_profile("bevel_simple", bevel_width=10.0)

        assert profile is not None
        assert profile.original_width == 10.0

    def test_get_category_list(self):
        """测试获取分类列表"""
        categories = self.manager.get_category_list()

        assert len(categories) == len(ProfileCategory)

    def test_convenience_functions(self):
        """测试便捷函数"""
        presets = get_all_presets()
        assert len(presets) >= 15

        profile = get_preset_profile("bevel_simple")
        assert profile is not None


# =============================================================================
# SliceEngine 异形边集成测试
# =============================================================================

class TestSliceEngineCustomEdge:
    """SliceEngine 异形边切片测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.engine = SliceEngine()
        # 创建测试轮廓（简单矩形）
        outer = Path(points=[
            Point(0, 0), Point(100, 0), Point(100, 50), Point(0, 50)
        ])
        self.test_contour = Contour(outer=outer, name="TestRect")

    def test_apply_custom_edge_linear(self):
        """测试线性异形边应用"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (1.0, 1.0)],
            InterpolationType.LINEAR
        )
        params = ShellParams(
            height=30.0,
            bevel_width=5.0,
            edge_type=EdgeType.CUSTOM,
            edge_profile=profile
        )

        # 在z=15（中间）测试
        result = self.engine._apply_custom_edge(self.test_contour, z=15.0, params=params)

        assert result is not None
        # 原始边界: (0, 0, 100, 50)
        # 中间层应该内缩2.5mm
        bounds = result.outer.bounds
        assert bounds[0] == pytest.approx(2.5, abs=0.1)  # min_x
        assert bounds[1] == pytest.approx(2.5, abs=0.1)  # min_y

    def test_full_slice_with_custom_edge(self):
        """测试完整切片流程"""
        profile = EdgeProfile.from_control_points(
            [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)],
            InterpolationType.LINEAR
        )
        shell_params = ShellParams(
            height=30.0,
            layer_height=0.3,
            wall_thickness=1.2,
            edge_type=EdgeType.CUSTOM,
            bevel_width=5.0,
            edge_profile=profile
        )
        params = SliceParams(shell=shell_params)

        result = self.engine.slice([self.test_contour], params)

        assert result.total_layers == 100
        assert result.total_height == 30.0
        assert len(result.layers) > 0

    def test_custom_edge_with_preset(self):
        """测试使用预设的异形边切片"""
        if not os.path.exists("docs/真材INC-26/special_shape"):
            pytest.skip("DXF templates not found")

        manager = EdgePresetManager()
        profile = manager.get_preset_profile("arc_single")

        if profile is None:
            pytest.skip("Preset not available")

        shell_params = ShellParams(
            height=30.0,
            layer_height=0.3,
            edge_type=EdgeType.CUSTOM,
            bevel_width=3.0,
            edge_profile=profile
        )
        params = SliceParams(shell=shell_params)

        result = self.engine.slice([self.test_contour], params)

        assert result.total_layers == 100


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
