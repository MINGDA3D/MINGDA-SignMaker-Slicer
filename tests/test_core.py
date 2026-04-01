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
from pathlib import Path as FilePath

from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.types import (
    Point, Point3D, Path, Contour, Layer, LayerPath,
    PathType, PathRole, EdgeType, ExtruderType, BevelDirection,
    SliceParams, ShellParams, StepParams, StepConfig
)
from src.core.path_offset import PathOffset, JoinType
from src.core.slice_engine import SliceEngine
from src.core.gcode_writer import GCodeWriter, GCodeParams
from src.core.step_generator import StepGenerator
from src.core.svg_parser import SVGParser
from src.core.stl import ShellMeshBuilder
from src.core.stl.step_mesh import StepMeshBuilder
from src.utils.geometry import normalize_path


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

    def test_top_large_bevel_keeps_bottom_profile_as_reference(self, engine, simple_contour):
        """上大下小模式下，原始轮廓始终对应底面，顶部向外扩展。"""
        params = SliceParams()
        params.shell.height = 30
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_direction = BevelDirection.TOP_LARGE
        params.shell.bevel_width = 5
        params.shell.baseplate_thickness = 10
        params.shell.panel_thickness = 3

        bottom_contour = engine._apply_edge_profile(simple_contour, 0, params.shell)
        top_contour = engine._apply_edge_profile(simple_contour, params.shell.height, params.shell)

        assert bottom_contour is not None
        assert top_contour is not None
        assert bottom_contour.outer.bounds == (0, 0, 100, 100)
        assert top_contour.outer.bounds == (-5, -5, 105, 105)

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
        assert any(
            "START_PRINT EXTRUDER=220 BED=60 TOOL=0" in line for line in lines
        )
        assert any("G1" in line for line in lines)   # Move command

    def test_gcode_contains_header(self, writer, simple_result):
        """测试G-code包含头部"""
        lines = writer.generate(simple_result)

        assert any("MINGDA SignMaker" in line for line in lines)
        assert any("Start sequence" in line for line in lines)

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

    def test_slice_engine_uses_shell_line_width_for_wall_paths(self):
        """测试 WALL 路径线宽跟随 shell.line_width，而不是 wall_thickness。"""
        outer = Path(points=[
            Point(0, 0), Point(20, 0), Point(20, 20), Point(0, 20)
        ], is_closed=True)
        contour = Contour(outer=outer)

        params = SliceParams()
        params.shell.height = 1.0
        params.shell.layer_height = 0.5
        params.shell.wall_thickness = 1.2
        params.shell.line_width = 0.8

        engine = SliceEngine()
        result = engine.slice([contour], params)

        wall_paths = [path for path in result.layers[0].paths if path.role == PathRole.WALL]

        assert wall_paths
        assert wall_paths[0].line_width == pytest.approx(0.8)

    def test_slice_engine_derives_multi_wall_offsets_from_line_width(self):
        """测试多道壁偏移按 line_width 推导，而不是直接读取旧 wall_thickness。"""
        outer = Path(points=[
            Point(0, 0), Point(20, 0), Point(20, 20), Point(0, 20)
        ], is_closed=True)
        contour = Contour(outer=outer)

        params = SliceParams()
        params.shell.height = 1.0
        params.shell.layer_height = 0.5
        params.shell.line_width = 0.8
        params.shell.wall_count = 2
        params.shell.wall_thickness = 9.9

        engine = SliceEngine()
        result = engine.slice([contour], params)

        wall_paths = [path for path in result.layers[0].paths if path.role == PathRole.WALL]
        min_x_values = sorted(min(point.x for point in path.points) for path in wall_paths)

        assert len(wall_paths) == 2
        assert min_x_values[0] == pytest.approx(0.4)
        assert min_x_values[1] == pytest.approx(1.2)

    def test_shell_mesh_builder_prefers_wall_path_line_width(self):
        """测试壳体 STL 优先按 WALL 路径自身的 line_width 生成几何厚度。"""
        builder = ShellMeshBuilder(PathOffset(), wall_thickness=1.2)
        layer = Layer(
            z_height=0.0,
            layer_height=0.3,
            extruder=ExtruderType.EXTRUDER_1,
            paths=[
                LayerPath(
                    points=[
                        Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)
                    ],
                    role=PathRole.WALL,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=0.6,
                    is_closed=True,
                )
            ],
        )

        mesh = builder.build([layer])

        assert mesh is not None
        assert mesh.bounds[0][0] == pytest.approx(-0.3)
        assert mesh.bounds[1][0] == pytest.approx(10.3)

    def test_shell_mesh_builder_multi_wall_does_not_expand_from_total_thickness(self):
        """测试多道 WALL 中心线建模时，不会再按总壁厚重复扩粗。"""
        builder = ShellMeshBuilder(PathOffset(), wall_thickness=1.6)
        layer = Layer(
            z_height=0.0,
            layer_height=0.5,
            extruder=ExtruderType.EXTRUDER_1,
            paths=[
                LayerPath(
                    points=[
                        Point(0.4, 0.4), Point(19.6, 0.4), Point(19.6, 19.6), Point(0.4, 19.6)
                    ],
                    role=PathRole.WALL,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=0.8,
                    is_closed=True,
                ),
                LayerPath(
                    points=[
                        Point(1.2, 1.2), Point(18.8, 1.2), Point(18.8, 18.8), Point(1.2, 18.8)
                    ],
                    role=PathRole.WALL,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=0.8,
                    is_closed=True,
                ),
            ],
        )

        mesh = builder.build([layer])

        assert mesh is not None
        assert mesh.bounds[0][0] == pytest.approx(0.0)
        assert mesh.bounds[1][0] == pytest.approx(20.0)
        assert mesh.volume == pytest.approx(58.88)


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

    def test_panel_v_groove_grows_toward_configured_height(self, step_generator, simple_contour):
        step_params = StepParams(
            enabled=True,
            panel_step_enabled=True,
            panel_step_height=6.0,
            panel_step_width=3.0,
            panel_step_is_v_groove=True,
            extrusion_width=1.2,
        )

        lower_paths = step_generator.generate_panel_step_for_layer(
            simple_contour,
            z_height=0.0,
            layer_height=1.0,
            total_height=10.0,
            params=step_params,
            wall_thickness=1.2,
        )
        upper_paths = step_generator.generate_panel_step_for_layer(
            simple_contour,
            z_height=5.0,
            layer_height=1.0,
            total_height=10.0,
            params=step_params,
            wall_thickness=1.2,
        )

        assert lower_paths
        assert upper_paths
        assert lower_paths[0].role == PathRole.V_GROOVE
        assert lower_paths[0].line_width < upper_paths[0].line_width

    def test_baseplate_v_groove_grows_toward_upper_boundary(self, step_generator, simple_contour):
        step_params = StepParams(
            enabled=True,
            baseplate_step_enabled=True,
            baseplate_step_height=4.0,
            baseplate_step_width=3.0,
            baseplate_step_is_v_groove=True,
            extrusion_width=1.2,
        )

        lower_paths = step_generator.generate_baseplate_step_for_layer(
            simple_contour,
            z_height=0.0,
            layer_height=1.0,
            total_height=10.0,
            params=step_params,
            wall_thickness=1.2,
        )
        upper_paths = step_generator.generate_baseplate_step_for_layer(
            simple_contour,
            z_height=3.0,
            layer_height=1.0,
            total_height=10.0,
            params=step_params,
            wall_thickness=1.2,
        )

        assert lower_paths
        assert upper_paths
        assert lower_paths[0].role == PathRole.V_GROOVE
        assert lower_paths[0].line_width < upper_paths[0].line_width

    def test_v_groove_reaches_full_width_after_ten_layers(self, step_generator, simple_contour):
        step_params = StepParams(
            enabled=True,
            baseplate_step_enabled=True,
            baseplate_step_height=15.0,
            baseplate_step_width=3.0,
            baseplate_step_is_v_groove=True,
            extrusion_width=1.2,
        )

        before_ramp_paths = step_generator.generate_baseplate_step_for_layer(
            simple_contour,
            z_height=0.0,
            layer_height=1.0,
            total_height=30.0,
            params=step_params,
            wall_thickness=1.2,
        )
        ramp_paths = step_generator.generate_baseplate_step_for_layer(
            simple_contour,
            z_height=9.0,
            layer_height=1.0,
            total_height=30.0,
            params=step_params,
            wall_thickness=1.2,
        )
        final_paths = step_generator.generate_baseplate_step_for_layer(
            simple_contour,
            z_height=14.0,
            layer_height=1.0,
            total_height=30.0,
            params=step_params,
            wall_thickness=1.2,
        )

        assert before_ramp_paths == []
        assert ramp_paths
        assert final_paths
        assert ramp_paths[0].line_width < step_params.baseplate_step_width
        assert final_paths[0].line_width == pytest.approx(step_params.baseplate_step_width)

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

    @pytest.fixture
    def contour_with_hole(self):
        outer = normalize_path(Path(points=[
            Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)
        ], is_closed=True, path_type=PathType.OUTER))
        hole = normalize_path(Path(points=[
            Point(30, 30), Point(70, 30), Point(70, 70), Point(30, 70)
        ], is_closed=True, path_type=PathType.INNER))
        return Contour(outer=outer, holes=[hole])

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
            if layer.z_height >= 25.0:
                for path in layer.paths:
                    if path.role in (PathRole.STEP, PathRole.V_GROOVE):
                        panel_step_found = True
                        break
            if panel_step_found:
                break

        assert panel_step_found, "应该在顶部找到面板台阶路径"

    def test_slice_with_panel_v_groove_ends_at_configured_height(self, engine, simple_contour):
        params = SliceParams()
        params.shell.height = 10.0
        params.shell.layer_height = 1.0
        params.shell.wall_thickness = 1.2
        params.step.enabled = True
        params.step.panel_step_enabled = True
        params.step.panel_step_height = 6.0
        params.step.panel_step_width = 3.0
        params.step.panel_step_is_v_groove = True

        result = engine.slice([simple_contour], params)

        v_layers = [
            layer.z_height
            for layer in result.layers
            if any(path.role == PathRole.V_GROOVE for path in layer.paths)
        ]

        assert v_layers
        assert min(v_layers) == pytest.approx(0.0)
        assert max(v_layers) == pytest.approx(5.0)

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

    def test_hole_wall_offsets_toward_solid_and_overlaps_step(self, engine, contour_with_hole):
        """回归测试：内孔 WALL 应向实体侧偏移，并与 STEP 保持搭接"""
        params = SliceParams()
        params.shell.height = 1.0
        params.shell.layer_height = 0.3
        params.shell.wall_thickness = 1.2
        params.shell.wall_count = 1
        params.step.enabled = True
        params.step.steps = [
            StepConfig(enabled=True, position=0.0, width=3.0, height=0.0, is_v_groove=False),
        ]

        result = engine.slice([contour_with_hole], params)

        layer = result.layers[0]
        wall_paths = [path for path in layer.paths if path.role == PathRole.WALL]
        step_paths = [path for path in layer.paths if path.role == PathRole.STEP]

        assert len(wall_paths) == 2
        assert len(step_paths) == 2

        hole_wall = min(
            wall_paths,
            key=lambda path: (max(p.x for p in path.points) - min(p.x for p in path.points))
        )
        hole_step = min(
            step_paths,
            key=lambda path: (max(p.x for p in path.points) - min(p.x for p in path.points))
        )

        hole_wall_min_x = min(point.x for point in hole_wall.points)
        hole_step_min_x = min(point.x for point in hole_step.points)

        # hole wall centerline must move into the solid, not into the empty hole.
        assert hole_wall_min_x == pytest.approx(29.4)

        hole_step_outer_edge = hole_step_min_x + hole_step.line_width / 2
        hole_wall_inner_edge = hole_wall_min_x - hole_wall.line_width / 2
        assert hole_step_outer_edge >= hole_wall_inner_edge - 1e-6

    def test_beveled_edge_with_steps_regression(self, engine, simple_contour):
        """回归测试：斜边字+台阶组合，防止台阶悬空问题"""
        params = SliceParams()
        params.shell.height = 50.0
        params.shell.layer_height = 0.3
        params.shell.wall_thickness = 1.2
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_width = 5.0
        params.shell.bevel_direction = BevelDirection.TOP_LARGE

        # 启用底板和面板台阶
        params.step.enabled = True
        params.step.baseplate_step_enabled = True
        params.step.baseplate_step_height = 10.0
        params.step.baseplate_step_width = 3.0
        params.step.panel_step_enabled = True
        params.step.panel_step_height = 40.0
        params.step.panel_step_width = 3.0

        result = engine.slice([simple_contour], params)

        assert result.total_layers > 0

        # 验证底板台阶层存在WALL路径（用于台阶生成）
        baseplate_layer_found = False
        panel_layer_found = False

        for layer in result.layers:
            if abs(layer.z_height - 10.0) < 0.2:
                wall_paths = [p for p in layer.paths if p.role == PathRole.WALL]
                if wall_paths:
                    baseplate_layer_found = True

            if abs(layer.z_height - 40.0) < 0.2:
                wall_paths = [p for p in layer.paths if p.role == PathRole.WALL]
                if wall_paths:
                    panel_layer_found = True

        assert baseplate_layer_found, "底板台阶层应该有WALL路径"
        assert panel_layer_found, "面板台阶层应该有WALL路径"


class TestStepMeshBuilder:
    """StepMeshBuilder类测试"""

    @pytest.fixture
    def step_mesh_builder(self):
        return StepMeshBuilder(PathOffset())

    def test_split_inset_step_ring_preserves_all_holes(self, step_mesh_builder):
        """回归测试：狭窄连接处台阶内缩分裂时，不应错误闭合区域"""
        svg_path = FilePath(__file__).resolve().parent.parent / "Debug" / "LOGO-08.svg"
        contours = SVGParser().parse(str(svg_path))

        for contour in contours:
            for point in contour.outer.points:
                point.x *= 4
                point.y *= 4
            for hole in contour.holes:
                for point in hole.points:
                    point.x *= 4
                    point.y *= 4

        target_coords = None
        inset_results = None

        for contour in contours:
            inner_wall_results = step_mesh_builder.path_offset.offset(contour.outer, -1.2)
            if not inner_wall_results:
                continue

            candidate_insets = step_mesh_builder.path_offset.offset(inner_wall_results[0], -3.0)
            if len(candidate_insets) > 1:
                target_coords = [(p.x, p.y) for p in inner_wall_results[0].points]
                if target_coords[0] != target_coords[-1]:
                    target_coords.append(target_coords[0])
                inset_results = candidate_insets
                break

        assert target_coords is not None, "应该找到会被3mm台阶切分的狭窄轮廓"
        assert inset_results is not None and len(inset_results) > 1

        ring_geometry = step_mesh_builder._build_step_ring_geometry(
            target_coords,
            step_width=3.0,
            is_hole=False
        )

        assert ring_geometry is not None
        assert ring_geometry.geom_type == "Polygon"
        assert len(ring_geometry.interiors) == len(inset_results)

        legacy_hole = [(p.x, p.y) for p in inset_results[0].points]
        if legacy_hole[0] != legacy_hole[-1]:
            legacy_hole.append(legacy_hole[0])
        legacy_geometry = ShapelyPolygon(target_coords, [legacy_hole])

        assert ring_geometry.area < legacy_geometry.area

        mesh = step_mesh_builder._create_thin_step_ring(
            target_coords,
            step_width=3.0,
            step_thickness=0.4,
            z_position=10.0,
            is_hole=False
        )

        assert mesh is not None
        assert abs(mesh.volume) == pytest.approx(ring_geometry.area * 0.4, rel=1e-3)

    def test_hole_step_ring_uses_expanded_region(self, step_mesh_builder):
        """内孔台阶应使用外扩区域减去原孔，不依赖无效多边形修复"""
        hole_coords = [
            (0.0, 0.0),
            (20.0, 0.0),
            (20.0, 20.0),
            (0.0, 20.0),
            (0.0, 0.0),
        ]

        ring_geometry = step_mesh_builder._build_step_ring_geometry(
            hole_coords,
            step_width=3.0,
            is_hole=True
        )

        assert ring_geometry is not None
        assert ring_geometry.is_valid

        hole_path = Path(points=[
            Point(0.0, 0.0),
            Point(20.0, 0.0),
            Point(20.0, 20.0),
            Point(0.0, 20.0),
        ], is_closed=True)
        expanded_paths = step_mesh_builder.path_offset.offset(hole_path, 3.0)
        expected_region = unary_union([
            ShapelyPolygon([(p.x, p.y) for p in path.points])
            for path in expanded_paths
        ]).difference(ShapelyPolygon(hole_coords))

        assert ring_geometry.area == pytest.approx(expected_region.area, rel=1e-6)

    def test_build_uses_sliced_v_groove_layers_for_sloped_mesh(self, step_mesh_builder):
        contour = Contour(
            outer=Path(points=[
                Point(0.0, 0.0),
                Point(40.0, 0.0),
                Point(40.0, 40.0),
                Point(0.0, 40.0),
            ], is_closed=True)
        )
        params = SliceParams()
        params.shell.height = 10.0
        params.shell.layer_height = 1.0
        params.shell.wall_thickness = 1.2
        params.step.panel_step_enabled = True
        params.step.panel_step_height = 6.0
        params.step.panel_step_width = 3.0
        params.step.panel_step_is_v_groove = True

        result = SliceEngine().slice([contour], params)
        mesh = step_mesh_builder.build([contour], result, params)

        assert mesh is not None
        assert mesh.bounds[0][2] == pytest.approx(0.0)
        assert mesh.bounds[1][2] == pytest.approx(6.0)
        assert abs(mesh.volume) > 0.0
        assert abs(mesh.volume) < 5000.0

    def test_build_keeps_flat_panel_step_as_single_thin_ring(self, step_mesh_builder):
        contour = Contour(
            outer=Path(points=[
                Point(0.0, 0.0),
                Point(40.0, 0.0),
                Point(40.0, 40.0),
                Point(0.0, 40.0),
            ], is_closed=True)
        )
        params = SliceParams()
        params.shell.height = 30.0
        params.shell.layer_height = 1.0
        params.shell.wall_thickness = 1.2
        params.step.panel_step_enabled = True
        params.step.panel_step_height = 20.0
        params.step.panel_step_width = 3.0

        result = SliceEngine().slice([contour], params)
        mesh = step_mesh_builder.build([contour], result, params)

        assert mesh is not None
        assert mesh.bounds[0][2] == pytest.approx(20.0)
        assert mesh.bounds[1][2] == pytest.approx(21.1)


class TestSTLExport:
    """STL导出验证测试"""

    @pytest.fixture
    def engine(self):
        from src.core.slice_engine import SliceEngine
        return SliceEngine()

    @pytest.fixture
    def simple_contour(self):
        outer = Path(points=[
            Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)
        ])
        return Contour(outer=outer)

    @pytest.fixture
    def stl_writer(self):
        from src.core.stl_writer import STLWriter
        return STLWriter()

    def test_beveled_edge_with_steps_stl_export(self, engine, simple_contour, stl_writer, tmp_path):
        """验证斜边字+台阶的STL导出包含台阶网格"""
        params = SliceParams()
        params.shell.height = 50.0
        params.shell.layer_height = 0.3
        params.shell.wall_thickness = 1.2
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_width = 5.0

        params.step.baseplate_step_enabled = True
        params.step.baseplate_step_height = 10.0
        params.step.baseplate_step_width = 3.0

        result = engine.slice([simple_contour], params)

        stl_file = tmp_path / "test_beveled_steps.stl"
        stl_writer.write(result, str(stl_file), True, [simple_contour], params)

        assert stl_file.exists(), "STL文件应该被创建"
        assert stl_file.stat().st_size > 1000, "STL文件应该包含网格数据"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
