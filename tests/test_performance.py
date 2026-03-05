"""
MINGDA SignMaker - 性能测试

测试关键场景的性能，确保处理大型模型时的响应速度
"""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.types import Point, Path, Contour, SliceParams, ShellParams, EdgeType
from src.core.slice_engine import SliceEngine
from src.core.stl_writer import STLWriter


class TestPerformance:
    """性能测试"""

    @pytest.fixture
    def engine(self):
        return SliceEngine()

    @pytest.fixture
    def stl_writer(self):
        return STLWriter()

    @pytest.fixture
    def large_contour(self):
        """大型复杂轮廓（100个点）"""
        import math
        points = []
        for i in range(100):
            angle = 2 * math.pi * i / 100
            x = 500 + 400 * math.cos(angle)
            y = 500 + 400 * math.sin(angle)
            points.append(Point(x, y))
        return Contour(outer=Path(points=points))

    @pytest.fixture
    def multiple_contours(self):
        """多个轮廓（10个）"""
        contours = []
        for i in range(10):
            offset_x = (i % 5) * 150
            offset_y = (i // 5) * 150
            outer = Path(points=[
                Point(offset_x, offset_y),
                Point(offset_x + 100, offset_y),
                Point(offset_x + 100, offset_y + 100),
                Point(offset_x, offset_y + 100)
            ])
            contours.append(Contour(outer=outer))
        return contours

    def test_large_contour_slice_performance(self, engine, large_contour):
        """测试大型轮廓切片性能（应在1秒内完成）"""
        params = SliceParams()
        params.shell.height = 50.0
        params.shell.layer_height = 0.3

        start = time.time()
        result = engine.slice([large_contour], params)
        elapsed = time.time() - start

        assert result.total_layers > 0
        assert elapsed < 1.0, f"大型轮廓切片耗时{elapsed:.2f}秒，超过1秒阈值"

    def test_beveled_edge_performance(self, engine, large_contour):
        """测试斜边切片性能（应在2秒内完成）"""
        params = SliceParams()
        params.shell.height = 50.0
        params.shell.layer_height = 0.3
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_width = 5.0

        start = time.time()
        result = engine.slice([large_contour], params)
        elapsed = time.time() - start

        assert result.total_layers > 0
        assert elapsed < 2.0, f"斜边切片耗时{elapsed:.2f}秒，超过2秒阈值"

    def test_multiple_contours_performance(self, engine, multiple_contours):
        """测试多轮廓切片性能（应在2秒内完成）"""
        params = SliceParams()
        params.shell.height = 30.0
        params.shell.layer_height = 0.3

        start = time.time()
        result = engine.slice(multiple_contours, params)
        elapsed = time.time() - start

        assert result.total_layers > 0
        assert elapsed < 2.0, f"多轮廓切片耗时{elapsed:.2f}秒，超过2秒阈值"

    def test_stl_export_performance(self, engine, stl_writer, large_contour, tmp_path):
        """测试STL导出性能（应在3秒内完成）"""
        params = SliceParams()
        params.shell.height = 50.0
        params.shell.layer_height = 0.3
        params.shell.edge_type = EdgeType.BEVELED
        params.shell.bevel_width = 5.0
        params.step.baseplate_step_enabled = True
        params.step.baseplate_step_height = 10.0

        result = engine.slice([large_contour], params)
        stl_file = tmp_path / "perf_test.stl"

        start = time.time()
        stl_writer.write(result, str(stl_file), True, [large_contour], params)
        elapsed = time.time() - start

        assert stl_file.exists()
        assert elapsed < 3.0, f"STL导出耗时{elapsed:.2f}秒，超过3秒阈值"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
