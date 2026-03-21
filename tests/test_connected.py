"""
连襟字功能测试

测试自动检测轮廓连接和STL导出。
"""

import os
import sys
import tempfile
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.types import (
    Point, Path, Contour, SliceParams, ConnectedParams,
    ShellParams, Layer, LayerPath, PathRole, ExtruderType, SliceResult
)
from src.core.connected_generator import ConnectedGenerator, ConnectionBridge
from src.core.stl_writer import STLWriter
from src.core.slice_engine import SliceEngine


class TestConnectedGenerator:
    """连襟生成器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.generator = ConnectedGenerator()

    def test_find_connection_bridges_two_contours(self):
        """测试两个轮廓之间的连接检测"""
        # 创建两个相邻的方形轮廓
        contour1 = Contour(
            outer=Path(points=[
                Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)
            ])
        )
        contour2 = Contour(
            outer=Path(points=[
                Point(20, 0), Point(30, 0), Point(30, 10), Point(20, 10)
            ])
        )

        params = ConnectedParams(
            enabled=True,
            width=15.0
        )

        bridges = self.generator.find_connection_bridges([contour1, contour2], params)

        assert len(bridges) == 1
        assert bridges[0].distance == 10.0  # 两个轮廓间距10mm
        assert bridges[0].contour_a_index == 0
        assert bridges[0].contour_b_index == 1

    def test_find_connection_bridges_far_apart(self):
        """测试距离较远的轮廓也能连接"""
        contour1 = Contour(
            outer=Path(points=[
                Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)
            ])
        )
        contour2 = Contour(
            outer=Path(points=[
                Point(100, 0), Point(110, 0), Point(110, 10), Point(100, 10)
            ])
        )

        params = ConnectedParams(
            enabled=True
        )

        bridges = self.generator.find_connection_bridges([contour1, contour2], params)

        # 即使距离较远，也应该生成连接桥以确保所有轮廓连通
        assert len(bridges) == 1
        assert bridges[0].distance == 90.0  # 两个轮廓间距90mm

    def test_calculate_bridge_corners(self):
        """测试连接桥角点计算"""
        point_a = Point(10, 5)
        point_b = Point(20, 5)
        width = 10.0

        corners = self.generator._calculate_bridge_corners(point_a, point_b, width)

        assert len(corners) == 4
        # 验证宽度
        assert abs(corners[0].y - corners[1].y) == width
        assert abs(corners[2].y - corners[3].y) == width

    def test_calculate_width_at_z_triangle(self):
        """测试三角形连襟宽度计算"""
        params = ConnectedParams(
            enabled=True,
            type="triangle",
            width=15.0,
            height=5.0,
            base_height=5.0
        )

        # 底座区域保持原宽度
        assert self.generator._calculate_width_at_z(0, params) == 15.0
        assert self.generator._calculate_width_at_z(4, params) == 15.0
        assert self.generator._calculate_width_at_z(5, params) == 15.0

        # 斜边区域线性收窄
        assert abs(self.generator._calculate_width_at_z(7.5, params) - 7.5) < 0.01
        assert self.generator._calculate_width_at_z(10, params) == 0.0

    def test_calculate_width_at_z_diamond(self):
        """测试菱形连襟宽度计算"""
        params = ConnectedParams(
            enabled=True,
            type="diamond",
            width=20.0,
            height=5.0,
            base_height=5.0
        )

        # 菱形连襟：中间最窄
        total_height = 15.0  # base + height*2
        mid = total_height / 2

        # 底部为原宽度
        w0 = self.generator._calculate_width_at_z(0, params)
        assert w0 == 20.0

        # 中间最窄（50%）
        w_mid = self.generator._calculate_width_at_z(mid, params)
        assert w_mid == 10.0

    def test_generate_connected_disabled(self):
        """测试禁用时返回空列表"""
        params = ConnectedParams(enabled=False)
        contours = [Contour(), Contour()]

        paths = self.generator.generate_connected(contours, 0, params)

        assert paths == []

    def test_get_total_height(self):
        """测试总高度计算"""
        params_triangle = ConnectedParams(
            type="triangle",
            height=5.0,
            base_height=5.0
        )
        params_diamond = ConnectedParams(
            type="diamond",
            height=5.0,
            base_height=5.0
        )

        assert self.generator.get_total_height(params_triangle) == 10.0
        assert self.generator.get_total_height(params_diamond) == 15.0


class TestConnectedSTLExport:
    """连襟STL导出测试"""

    def test_slice_engine_includes_connected_preview_paths(self):
        """切片结果应包含 3D 预览可见的连襟路径。"""
        contour1 = Contour(
            outer=Path(points=[
                Point(0, 0), Point(20, 0), Point(20, 20), Point(0, 20)
            ])
        )
        contour2 = Contour(
            outer=Path(points=[
                Point(30, 0), Point(50, 0), Point(50, 20), Point(30, 20)
            ])
        )

        params = SliceParams(
            shell=ShellParams(height=10.0, layer_height=1.0, wall_thickness=1.2),
            connected=ConnectedParams(
                enabled=True,
                type="triangle",
                width=15.0,
                height=5.0,
                base_height=5.0
            )
        )

        result = SliceEngine().slice([contour1, contour2], params)

        assert any(
            path.role == PathRole.CONNECTED
            for layer in result.layers
            for path in layer.paths
        ), "切片结果中应该包含 CONNECTED 路径供 3D 预览显示"

    def test_stl_export_with_connected(self):
        """测试带连襟的STL导出"""
        # 创建两个轮廓
        contour1 = Contour(
            outer=Path(points=[
                Point(0, 0), Point(20, 0), Point(20, 20), Point(0, 20)
            ])
        )
        contour2 = Contour(
            outer=Path(points=[
                Point(30, 0), Point(50, 0), Point(50, 20), Point(30, 20)
            ])
        )

        # 创建参数
        params = SliceParams(
            shell=ShellParams(height=10.0, layer_height=0.3, wall_thickness=1.2),
            connected=ConnectedParams(
                enabled=True,
                type="triangle",
                width=15.0,
                height=5.0,
                base_height=5.0
            )
        )

        # 使用切片引擎生成切片结果
        engine = SliceEngine()
        result = engine.slice([contour1, contour2], params)

        assert result.total_layers > 0

        # 导出STL
        writer = STLWriter(wall_thickness=params.shell.wall_thickness)

        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
            output_path = f.name

        try:
            writer.write(result, output_path, contours=[contour1, contour2], params=params)

            # 验证文件已创建
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

            print(f"STL file created: {output_path}, size: {os.path.getsize(output_path)} bytes")

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_build_connected_mesh(self):
        """测试连襟网格构建"""
        contour1 = Contour(
            outer=Path(points=[
                Point(0, 0), Point(20, 0), Point(20, 20), Point(0, 20)
            ])
        )
        contour2 = Contour(
            outer=Path(points=[
                Point(30, 0), Point(50, 0), Point(50, 20), Point(30, 20)
            ])
        )

        params = SliceParams(
            shell=ShellParams(height=10.0),
            connected=ConnectedParams(
                enabled=True,
                type="triangle",
                width=15.0,
                height=5.0,
                base_height=5.0
            )
        )

        writer = STLWriter()
        mesh = writer._build_connected_mesh([contour1, contour2], params)

        assert mesh is not None
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0

        print(f"Connected mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")


class TestConnectedPanel:
    """连襟参数面板测试"""

    def test_connected_panel_params(self):
        """测试参数面板参数同步"""
        # 只导入，不创建实例（避免需要Qt环境）
        from src.ui.panels.connected_panel import ConnectedPanel

        # 验证类存在
        assert ConnectedPanel is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
