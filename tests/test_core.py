"""
SignMaker Slicer - 单元测试

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
    PathType, PathRole, EdgeType, ExtruderType,
    SliceParams, ShellParams
)
from src.core.path_offset import PathOffset, JoinType
from src.core.slice_engine import SliceEngine
from src.core.gcode_writer import GCodeWriter, GCodeParams


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

        assert any("SignMaker Slicer" in line for line in lines)
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
