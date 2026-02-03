"""
MINGDA SignMaker - 单元测试

测试核心模块功能：
- types: 数据类型
- path_offset: 路径偏移
- slice_engine: 切片引擎
- gcode_writer: G-code生成
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.types import (
    Point, Point3D, Path, Contour,
    PathType, PathRole, EdgeType, ExtruderType, BevelDirection,
    SliceParams, ShellParams, StepParams, StepConfig
)
from src.core.path_offset import PathOffset, JoinType
from src.core.slice_engine import SliceEngine
from src.core.gcode_writer import GCodeWriter, GCodeParams
from src.core.step_generator import StepGenerator


class TestPoint:
    """Point类测试"""

    def test_point_creation(self):
        """测试点创建"""
        p = Point(1.0, 2.0)
        assert p.x == 1.0
        assert p.y == 2.0

    def test_point_addition(self):
        """测试点加法"""
        p1 = Point(1.0, 2.0)
        p2 = Point(3.0, 4.0)
        result = p1 + p2
        assert result.x == 4.0
        assert result.y == 6.0

    def test_point_subtraction(self):
        """测试点减法"""
        p1 = Point(5.0, 6.0)
        p2 = Point(2.0, 3.0)
        result = p1 - p2
        assert result.x == 3.0
        assert result.y == 3.0

    def test_point_multiplication(self):
        """测试点乘法"""
        p = Point(2.0, 3.0)
        result = p * 2
        assert result.x == 4.0
        assert result.y == 6.0

    def test_point_equality(self):
        """测试点相等性"""
        p1 = Point(1.0, 2.0)
        p2 = Point(1.0, 2.0)
        p3 = Point(1.0, 3.0)
        assert p1 == p2
        assert p1 != p3

    def test_point_to_tuple(self):
        """测试点转元组"""
        p = Point(1.5, 2.5)
        assert p.to_tuple() == (1.5, 2.5)


class TestPath:
    """Path类测试"""

    def test_path_creation(self):
        """测试路径创建"""
        points = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        path = Path(points=points)
        assert len(path.points) == 4
        assert path.is_closed == True

    def test_path_bounds(self):
        """测试路径边界框"""
        points = [Point(1, 2), Point(5, 2), Point(5, 8), Point(1, 8)]
        path = Path(points=points)
        bounds = path.bounds
        assert bounds == (1, 2, 5, 8)

    def test_path_area_square(self):
        """测试正方形面积"""
        points = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        path = Path(points=points)
        assert path.area == 100.0

    def test_path_area_triangle(self):
        """测试三角形面积"""
        points = [Point(0, 0), Point(10, 0), Point(5, 10)]
        path = Path(points=points)
        assert path.area == 50.0

    def test_path_length_square(self):
        """测试正方形周长"""
        points = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        path = Path(points=points, is_closed=True)
        assert abs(path.length - 40.0) < 0.001


class TestContour:
    """Contour类测试"""

    def test_contour_creation(self):
        """测试轮廓创建"""
        outer = Path(points=[Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)])
        hole = Path(points=[Point(30, 30), Point(70, 30), Point(70, 70), Point(30, 70)])

        contour = Contour(outer=outer, holes=[hole])
        assert len(contour.holes) == 1


class TestPathOffset:
    """PathOffset类测试"""

    @pytest.fixture
    def offset_tool(self):
        return PathOffset()

    @pytest.fixture
    def square_path(self):
        return Path(points=[
            Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)
        ], is_closed=True)

    def test_offset_outward(self, offset_tool, square_path):
        """测试外扩偏移"""
        result = offset_tool.offset(square_path, 1)
        assert len(result) >= 1
        # 外扩后面积应该增大
        if result:
            assert result[0].area > square_path.area

    def test_offset_inward(self, offset_tool, square_path):
        """测试内缩偏移"""
        result = offset_tool.offset(square_path, -1)
        assert len(result) >= 1
        # 内缩后面积应该减小
        if result:
            assert result[0].area < square_path.area

    def test_offset_inward_too_much(self, offset_tool, square_path):
        """测试过度内缩（应该消失）"""
        result = offset_tool.offset(square_path, -10)
        # 内缩超过一半宽度应该消失
        assert len(result) == 0

    def test_offset_contour(self, offset_tool):
        """测试轮廓偏移"""
        outer = Path(points=[
            Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)
        ], is_closed=True)
        hole = Path(points=[
            Point(30, 30), Point(70, 30), Point(70, 70), Point(30, 70)
        ], is_closed=True)

        contour = Contour(outer=outer, holes=[hole])
        result = offset_tool.offset_contour(contour, -5)

        assert result is not None
        assert result.outer is not None
        # 外轮廓内缩，内孔外扩

    def test_boolean_union(self, offset_tool):
        """测试布尔并集"""
        path1 = Path(points=[Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)])
        path2 = Path(points=[Point(5, 0), Point(15, 0), Point(15, 10), Point(5, 10)])

        result = offset_tool.boolean_union([path1, path2])
        assert len(result) >= 1

    def test_boolean_difference(self, offset_tool):
        """测试布尔差集"""
        subject = Path(points=[Point(0, 0), Point(20, 0), Point(20, 20), Point(0, 20)])
        clip = Path(points=[Point(5, 5), Point(15, 5), Point(15, 15), Point(5, 15)])

        result = offset_tool.boolean_difference(subject, clip)
        assert len(result) >= 1

    def test_boolean_intersection(self, offset_tool):
        """测试布尔交集"""
        path1 = Path(points=[Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)])
        path2 = Path(points=[Point(5, 5), Point(15, 5), Point(15, 15), Point(5, 15)])

        result = offset_tool.boolean_intersection(path1, path2)
        assert len(result) >= 1


class TestSliceEngine:
    """SliceEngine类测试"""

    @pytest.fixture
    def engine(self):
        return SliceEngine()

    @pytest.fixture
    def simple_contour(self):
        outer = Path(points=[
            Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)
        ], is_closed=True)
        return Contour(outer=outer)

    def test_slice_simple_contour(self, engine, simple_contour):
        """测试简单轮廓切片"""
        params = SliceParams()
        params.shell.height = 30
        params.shell.layer_height = 0.3

        result = engine.slice([simple_contour], params)

        assert result.total_layers == 100  # 30 / 0.3
        assert len(result.layers) == 100

    def test_slice_with_beveled_edge(self, engine, simple_contour):
        """测试斜边切片"""
        params = SliceParams()
        params.shell.height = 30
        params.shell.layer_height = 0.3
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_width = 5
        params.shell.baseplate_thickness = 10

        result = engine.slice([simple_contour], params)

        assert result.total_layers > 0

    def test_slice_with_inverse_beveled_edge(self, engine, simple_contour):
        """测试反向斜边切片（上大下小）"""
        params = SliceParams()
        params.shell.height = 30
        params.shell.layer_height = 0.3
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_direction = BevelDirection.TOP_LARGE
        params.shell.bevel_width = 5
        params.shell.baseplate_thickness = 10
        params.shell.panel_thickness = 3

        result = engine.slice([simple_contour], params)

        assert result.total_layers > 0
        # 验证反向斜边生成了正确的层数
        assert result.total_layers == 100  # 30 / 0.3

    def test_slice_with_safety_lines(self, engine, simple_contour):
        """测试带安全线切片"""
        params = SliceParams()
        params.shell.height = 10
        params.shell.layer_height = 0.5
        params.shell.safety_line_count = 2
        params.shell.safety_line_offset = 5

        result = engine.slice([simple_contour], params)

        # 安全线层 + 正常层
        assert result.total_layers >= 20 + 2

    def test_slice_empty_contours(self, engine):
        """测试空轮廓列表"""
        params = SliceParams()
        result = engine.slice([], params)

        assert result.total_layers == 0
        assert len(result.layers) == 0


class TestGCodeWriter:
    """GCodeWriter类测试"""

    @pytest.fixture
    def writer(self):
        params = GCodeParams()
        return GCodeWriter(params)

    @pytest.fixture
    def simple_result(self):
        from src.core.types import Layer, LayerPath, SliceResult

        path = LayerPath(
            points=[Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)],
            role=PathRole.WALL,
            extruder=ExtruderType.EXTRUDER_1,
            line_width=1.2,
            is_closed=True
        )

        layer = Layer(
            z_height=0,
            layer_height=0.3,
            extruder=ExtruderType.EXTRUDER_1,
            paths=[path]
        )

        return SliceResult(
            layers=[layer],
            total_layers=1,
            total_height=0.3,
            estimated_time=60,
            estimated_filament=0.1
        )

    def test_generate_gcode(self, writer, simple_result):
        """测试生成G-code"""
        lines = writer.generate(simple_result)

        assert len(lines) > 0
        assert any("G28" in line for line in lines)  # Home command
        assert any("G1" in line for line in lines)   # Move command

    def test_gcode_contains_header(self, writer, simple_result):
        """测试G-code包含头部"""
        lines = writer.generate(simple_result)

        assert any("MINGDA SignMaker" in line for line in lines)
        assert any("Home" in line for line in lines)

    def test_gcode_contains_footer(self, writer, simple_result):
        """测试G-code包含尾部"""
        lines = writer.generate(simple_result)

        assert any("end" in line.lower() for line in lines)
        assert any("M84" in line for line in lines)  # Disable motors

    def test_gcode_has_extrusion(self, writer, simple_result):
        """测试G-code包含挤出"""
        lines = writer.generate(simple_result)

        # 应该有 E 参数的 G1 命令
        assert any("G1" in line and "E" in line for line in lines)


class TestIntegration:
    """集成测试"""

    def test_full_pipeline(self):
        """测试完整流程：轮廓 -> 切片 -> G-code"""
        # 创建轮廓
        outer = Path(points=[
            Point(0, 0), Point(50, 0), Point(50, 50), Point(0, 50)
        ], is_closed=True)
        contour = Contour(outer=outer)

        # 切片参数
        params = SliceParams()
        params.shell.height = 10
        params.shell.layer_height = 0.5
        params.shell.wall_thickness = 1.2

        # 切片
        engine = SliceEngine()
        result = engine.slice([contour], params)

        assert result.total_layers == 20  # 10 / 0.5
        assert len(result.layers) == 20

        # 生成G-code
        writer = GCodeWriter(params.gcode)
        lines = writer.generate(result)

        assert len(lines) > 100  # 应该有大量G-code
        assert any("Layer" in line for line in lines)


class TestStepGenerator:
    """StepGenerator类测试"""

    @pytest.fixture
    def step_generator(self):
        return StepGenerator()

    @pytest.fixture
    def simple_contour(self):
        outer = Path(points=[
            Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)
        ], is_closed=True)
        return Contour(outer=outer)

    @pytest.fixture
    def contour_with_hole(self):
        outer = Path(points=[
            Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)
        ], is_closed=True)
        hole = Path(points=[
            Point(30, 30), Point(70, 30), Point(70, 70), Point(30, 70)
        ], is_closed=True)
        return Contour(outer=outer, holes=[hole])

    def test_generate_flat_step(self, step_generator, simple_contour):
        """测试生成平台阶"""
        step_config = StepConfig(
            enabled=True,
            position=5.0,
            width=3.0,
            height=0.0,
            is_v_groove=False
        )
        step_params = StepParams(enabled=True)

        paths = step_generator.generate_steps(
            simple_contour, step_config, step_params,
            wall_thickness=1.2
        )

        assert len(paths) > 0
        assert paths[0].role == PathRole.STEP
        assert paths[0].line_width == step_config.width

    def test_generate_v_groove(self, step_generator, simple_contour):
        """测试生成V槽"""
        step_config = StepConfig(
            enabled=True,
            position=5.0,
            width=3.0,
            height=2.0,
            is_v_groove=True
        )
        step_params = StepParams(
            enabled=True,
            step_thickness=0.3
        )

        paths = step_generator.generate_steps(
            simple_contour, step_config, step_params,
            wall_thickness=1.2
        )

        assert len(paths) > 0
        assert paths[0].role == PathRole.V_GROOVE

    def test_step_with_hole(self, step_generator, contour_with_hole):
        """测试带内孔的台阶生成"""
        step_config = StepConfig(
            enabled=True,
            position=5.0,
            width=3.0,
            height=0.0,
            is_v_groove=False
        )
        step_params = StepParams(enabled=True)

        paths = step_generator.generate_steps(
            contour_with_hole, step_config, step_params,
            wall_thickness=1.2
        )

        # 外轮廓��内孔都应该有台阶
        assert len(paths) >= 2

    def test_get_step_layers(self, step_generator):
        """测试获取台阶层映射"""
        step_params = StepParams(
            enabled=True,
            steps=[
                StepConfig(enabled=True, position=3.0, width=3.0, height=0.6),
                StepConfig(enabled=True, position=9.0, width=3.0, height=0.6),
            ]
        )

        step_layers = step_generator.get_step_layers(
            step_params,
            total_height=15.0,
            layer_height=0.3
        )

        # 应该找到台阶层
        assert len(step_layers) > 0

    def test_generate_step_for_layer(self, step_generator, simple_contour):
        """测试逐层台阶生成"""
        step_config = StepConfig(
            enabled=True,
            position=3.0,
            width=3.0,
            height=1.2,
            is_v_groove=True
        )
        step_params = StepParams(
            enabled=True,
            step_thickness=0.3,
            extrusion_width=1.2
        )

        # 在台阶区域内的层
        paths = step_generator.generate_step_for_layer(
            simple_contour,
            z_height=3.3,  # 在台阶区域内
            layer_height=0.3,
            step_config=step_config,
            params=step_params,
            wall_thickness=1.2
        )

        assert len(paths) > 0

    def test_step_outside_range(self, step_generator, simple_contour):
        """测试台阶区域外的层"""
        step_config = StepConfig(
            enabled=True,
            position=10.0,
            width=3.0,
            height=1.2,
            is_v_groove=True
        )
        step_params = StepParams(enabled=True)

        # 在台阶区域外的层
        paths = step_generator.generate_step_for_layer(
            simple_contour,
            z_height=0.0,  # 在台阶区域外
            layer_height=0.3,
            step_config=step_config,
            params=step_params,
            wall_thickness=1.2
        )

        assert len(paths) == 0

    def test_disabled_step(self, step_generator, simple_contour):
        """测试禁用的台阶"""
        step_config = StepConfig(
            enabled=False,
            position=5.0,
            width=3.0,
            height=0.0
        )
        step_params = StepParams(enabled=True)

        paths = step_generator.generate_steps(
            simple_contour, step_config, step_params
        )

        assert len(paths) == 0

    def test_is_step_layer(self, step_generator):
        """测试判断是否为台阶层"""
        step_params = StepParams(
            enabled=True,
            steps=[
                StepConfig(enabled=True, position=3.0, width=3.0, height=0.6),
            ]
        )

        # 在台阶范围内
        is_step, config = step_generator.is_step_layer(3.0, 0.3, step_params)
        assert is_step is True
        assert config is not None

        # 在台阶范围外
        is_step, config = step_generator.is_step_layer(10.0, 0.3, step_params)
        assert is_step is False
        assert config is None

    def test_bottom_groove(self, step_generator, simple_contour):
        """测试底部凹槽生成"""
        step_params = StepParams(
            enabled=True,
            bottom_groove_enabled=True,
            bottom_groove_height=3.0,
            bottom_groove_depth=2.0,
            extrusion_width=1.2
        )

        # 在凹槽范围内
        paths = step_generator.generate_bottom_groove(
            simple_contour,
            z_height=1.0,
            layer_height=0.3,
            params=step_params,
            wall_thickness=1.2
        )

        assert len(paths) > 0

        # 在凹槽范围外
        paths = step_generator.generate_bottom_groove(
            simple_contour,
            z_height=5.0,  # 超过凹槽高度
            layer_height=0.3,
            params=step_params,
            wall_thickness=1.2
        )

        assert len(paths) == 0


class TestSliceEngineWithSteps:
    """切片引擎台阶集成测试"""

    @pytest.fixture
    def engine(self):
        return SliceEngine()

    @pytest.fixture
    def simple_contour(self):
        outer = Path(points=[
            Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)
        ], is_closed=True)
        return Contour(outer=outer)

    def test_slice_with_steps(self, engine, simple_contour):
        """测试带台阶的切片"""
        params = SliceParams()
        params.shell.height = 15
        params.shell.layer_height = 0.3
        params.shell.wall_thickness = 1.2

        # 添加两个台阶
        params.step.enabled = True
        params.step.steps = [
            StepConfig(enabled=True, position=3.0, width=3.0, height=0.6),
            StepConfig(enabled=True, position=12.0, width=3.0, height=0.6),
        ]

        result = engine.slice([simple_contour], params)

        assert result.total_layers > 0

        # 检查是否有台阶路径
        step_paths_found = False
        for layer in result.layers:
            for path in layer.paths:
                if path.role in (PathRole.STEP, PathRole.V_GROOVE):
                    step_paths_found = True
                    break
            if step_paths_found:
                break

        assert step_paths_found, "应该找到台阶路径"

    def test_slice_with_bottom_groove(self, engine, simple_contour):
        """测试带底部凹槽的切片（使用底板台阶代替）"""
        params = SliceParams()
        params.shell.height = 15
        params.shell.layer_height = 0.3
        params.shell.wall_thickness = 1.2

        # 使用底板台阶代替旧的底部凹槽
        params.step.enabled = True
        params.step.baseplate_step_enabled = True
        params.step.baseplate_step_height = 3.0
        params.step.baseplate_step_width = 2.0

        result = engine.slice([simple_contour], params)

        assert result.total_layers > 0

        # 检查底部层是否有台阶路径
        bottom_step_found = False
        for layer in result.layers[:10]:  # 检查前10层
            for path in layer.paths:
                if path.role in (PathRole.STEP, PathRole.V_GROOVE):
                    bottom_step_found = True
                    break

        assert bottom_step_found, "应该找到底部台阶路径"

    def test_slice_with_panel_step(self, engine, simple_contour):
        """测试带面板台阶的切片"""
        params = SliceParams()
        params.shell.height = 30
        params.shell.layer_height = 0.3
        params.shell.wall_thickness = 1.2

        # 启用面板台阶（顶部）
        params.step.enabled = True
        params.step.panel_step_enabled = True
        params.step.panel_step_height = 5.0
        params.step.panel_step_width = 3.0
        params.step.panel_step_is_v_groove = False

        result = engine.slice([simple_contour], params)

        assert result.total_layers > 0

        # 检查顶部层是否有台阶路径
        panel_step_found = False
        # 台阶应该在 (30 - 5) = 25mm 到 30mm 之间
        for layer in result.layers:
            if layer.z_height >= 25.0:  # 顶部区域
                for path in layer.paths:
                    if path.role in (PathRole.STEP, PathRole.V_GROOVE):
                        panel_step_found = True
                        break
            if panel_step_found:
                break

        assert panel_step_found, "应该在顶部找到面板台阶路径"

    def test_slice_with_baseplate_step(self, engine, simple_contour):
        """测试带底板台阶的切片"""
        params = SliceParams()
        params.shell.height = 30
        params.shell.layer_height = 0.3
        params.shell.wall_thickness = 1.2

        # 启用底板台阶（底部）
        params.step.enabled = True
        params.step.baseplate_step_enabled = True
        params.step.baseplate_step_height = 5.0
        params.step.baseplate_step_width = 3.0
        params.step.baseplate_step_is_v_groove = False

        result = engine.slice([simple_contour], params)

        assert result.total_layers > 0

        # 检查底部层是否有台阶路径
        baseplate_step_found = False
        # 台阶应该在 0mm 到 5mm 之间
        for layer in result.layers:
            if layer.z_height < 5.0:  # 底部区域
                for path in layer.paths:
                    if path.role in (PathRole.STEP, PathRole.V_GROOVE):
                        baseplate_step_found = True
                        break
            if baseplate_step_found:
                break

        assert baseplate_step_found, "应该在底部找到底板台阶路径"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
