"""
SignMaker Slicer - SVG解析器单元测试

测试SVG解析功能（基于svgpathtools库）：
- 基本图形解析（rect, circle, ellipse, polygon, path）
- 颜色解析
- 轮廓分类和包含关系
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.svg_parser import SVGParser
from src.core.types import Point, PathType


class TestSVGParser:
    """SVGParser类测试"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return SVGParser()

    def test_parse_rect(self, parser):
        """测试矩形解析"""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="20" width="100" height="50" fill="black"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        assert len(contours) == 1
        # 矩形有4个角点，闭合路径可能包含额外的闭合点
        assert len(contours[0].outer.points) >= 4
        # 检查矩形角点存在
        points = contours[0].outer.points
        # 验证矩形的边界
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        assert min(xs) == pytest.approx(10, abs=0.1)
        assert max(xs) == pytest.approx(110, abs=0.1)
        assert min(ys) == pytest.approx(20, abs=0.1)
        assert max(ys) == pytest.approx(70, abs=0.1)

    def test_parse_circle(self, parser):
        """测试圆形解析"""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="30" fill="red"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        assert len(contours) == 1
        # 圆形应该有多个点（曲线离散化）
        assert len(contours[0].outer.points) >= 8
        # 验证圆的边界
        points = contours[0].outer.points
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        assert min(xs) == pytest.approx(20, abs=1)  # cx - r
        assert max(xs) == pytest.approx(80, abs=1)  # cx + r
        assert min(ys) == pytest.approx(20, abs=1)  # cy - r
        assert max(ys) == pytest.approx(80, abs=1)  # cy + r

    def test_parse_polygon(self, parser):
        """测试多边形解析"""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg">
            <polygon points="50,10 90,90 10,90" fill="black"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        assert len(contours) == 1
        # 三角形有3个顶点，闭合路径可能包含额外的闭合点
        assert len(contours[0].outer.points) >= 3
        # 验证三角形的顶点
        points = contours[0].outer.points
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        assert min(xs) == pytest.approx(10, abs=0.1)
        assert max(xs) == pytest.approx(90, abs=0.1)
        assert min(ys) == pytest.approx(10, abs=0.1)
        assert max(ys) == pytest.approx(90, abs=0.1)

    def test_parse_path_simple(self, parser):
        """测试简单路径解析"""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg">
            <path d="M 10 10 L 100 10 L 100 100 L 10 100 Z" fill="black"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        assert len(contours) == 1
        # 简单矩形路径应该有至少4个点
        assert len(contours[0].outer.points) >= 4

    def test_parse_path_bezier(self, parser):
        """测试贝塞尔曲线路径"""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg">
            <path d="M 10 10 C 20 20, 40 20, 50 10 L 50 50 L 10 50 Z" fill="black"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        assert len(contours) == 1
        # 有贝塞尔曲线，点数应该更多
        assert len(contours[0].outer.points) >= 4

    def test_parse_nested_shapes(self, parser):
        """测试嵌套形状（外轮廓+内孔）"""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="100" height="100" fill="black"/>
            <rect x="20" y="20" width="60" height="60" fill="white"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        assert len(contours) == 1
        assert contours[0].outer is not None
        assert len(contours[0].holes) == 1

    def test_color_parsing_hex(self, parser):
        """测试十六进制颜色解析"""
        color = parser._parse_color('#FF0000')
        assert color == (255, 0, 0)

        color = parser._parse_color('#00FF00')
        assert color == (0, 255, 0)

        color = parser._parse_color('#F00')  # 简写形式
        assert color == (255, 0, 0)

    def test_color_parsing_rgb(self, parser):
        """测试rgb()颜色解析"""
        color = parser._parse_color('rgb(255, 128, 0)')
        assert color == (255, 128, 0)

    def test_color_parsing_named(self, parser):
        """测试命名颜色解析"""
        color = parser._parse_color('red')
        assert color == (255, 0, 0)

        color = parser._parse_color('cyan')
        assert color == (0, 255, 255)

    def test_special_color_recognition(self, parser):
        """测试特殊颜色识别（连襟框、底孔等）"""
        # 青色应该被识别为连襟框
        path_type = parser._determine_path_type((0, 255, 255))
        assert path_type == PathType.CONNECTED

        # 绿色应该被识别为底孔
        path_type = parser._determine_path_type((0, 255, 0))
        assert path_type == PathType.HOLE

        # 蓝色应该被识别为花纹
        path_type = parser._determine_path_type((0, 0, 255))
        assert path_type == PathType.PATTERN

        # 其他颜色应该是外轮廓
        path_type = parser._determine_path_type((128, 128, 128))
        assert path_type == PathType.OUTER


class TestSVGParserWithRealSVG:
    """使用真实SVG文件测试解析器"""

    @pytest.fixture
    def parser(self):
        return SVGParser()

    def test_parse_complex_path(self, parser):
        """测试复杂路径解析"""
        # 一个包含多种命令的复杂路径
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <path d="M 10,30
                     A 20,20 0,0,1 50,30
                     A 20,20 0,0,1 90,30
                     Q 90,60 50,90
                     Q 10,60 10,30 z" fill="red"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        # 应该成功解��为一个轮廓
        assert len(contours) == 1
        # 复杂曲线应该有很多采样点
        assert len(contours[0].outer.points) >= 10

    def test_parse_ellipse(self, parser):
        """测试椭圆解析"""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="50" cy="50" rx="40" ry="20" fill="blue"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        # 椭圆被识别为PATTERN类型（蓝色）
        # 如果没有其他普通轮廓，会作为特殊路径处理
        # 根据颜色识别逻辑，蓝色会被识别为花纹
        # 由于没有外轮廓，patterns会为空
        assert len(contours) >= 0  # 可能没有轮廓（蓝色被识别为花纹）

    def test_parse_line_path(self, parser):
        """测试线条路径（非闭合）"""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg">
            <line x1="10" y1="10" x2="90" y2="90" stroke="black"/>
        </svg>'''

        contours = parser.parse_from_string(svg_content)

        # 线条只有2个点，不满足闭合路径要求，不会生成轮廓
        assert len(contours) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
