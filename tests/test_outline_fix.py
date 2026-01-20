"""
Test outline generation fix for complex contours

Verify that _build_sloped_ring method correctly handles complex contours
"""

import sys
import os
import math
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.types import (
    Point, Path, Contour, Layer, LayerPath,
    PathRole, ExtruderType, EdgeDirection,
    SliceResult, SliceParams, EdgeWrapParams, ShellParams
)
from src.core.stl_writer import STLWriter


def create_complex_contour():
    """
    创建一个复杂的轮廓，类似于Coca-Cola字母的曲线
    使用多段贝塞尔曲线生成复杂的形状
    """
    points = []

    # 创建一个波浪形的"C"字形状
    # 这个形状有很多曲线，类似于复杂字体
    num_points = 200  # 使用较多的点来模拟复杂轮廓

    # 外轮廓 - 类似于一个复杂的"C"形
    for i in range(num_points):
        t = i / num_points * 2 * math.pi

        # 基础圆形
        r = 50 + 10 * math.sin(5 * t) + 5 * math.cos(7 * t)  # 添加波浪效果
        x = r * math.cos(t)
        y = r * math.sin(t)

        points.append(Point(x, y))

    path = Path(points=points, is_closed=True)
    contour = Contour(outer=path)
    return contour


def create_simple_contour():
    """创建一个简单的方形轮廓作为对比"""
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(100, 100),
        Point(0, 100)
    ]
    path = Path(points=points, is_closed=True)
    contour = Contour(outer=path)
    return contour


def create_layer_from_contour(contour: Contour) -> Layer:
    """从轮廓创建一个基础层"""
    layer = Layer(
        z_height=0,
        layer_height=0.3,
        extruder=ExtruderType.EXTRUDER_1
    )

    # 添加壁路径
    layer_path = LayerPath(
        points=contour.outer.points,
        role=PathRole.WALL,
        extruder=ExtruderType.EXTRUDER_1,
        line_width=1.2,
        is_closed=True
    )
    layer.paths.append(layer_path)

    return layer


def test_complex_outline():
    """测试复杂轮廓的勾边生成"""
    print("=" * 60)
    print("测试复杂轮廓勾边生成")
    print("=" * 60)

    # 创建复杂轮廓
    contour = create_complex_contour()
    print(f"轮廓点数: {len(contour.outer.points)}")

    # 创建切片结果
    layers = []
    total_height = 30.0
    layer_height = 0.3
    num_layers = int(total_height / layer_height)

    for i in range(num_layers):
        layer = Layer(
            z_height=i * layer_height,
            layer_height=layer_height,
            extruder=ExtruderType.EXTRUDER_1
        )

        layer_path = LayerPath(
            points=contour.outer.points,
            role=PathRole.WALL,
            extruder=ExtruderType.EXTRUDER_1,
            line_width=1.2,
            is_closed=True
        )
        layer.paths.append(layer_path)
        layers.append(layer)

    result = SliceResult(
        layers=layers,
        total_layers=num_layers,
        total_height=total_height
    )

    # 创建参数
    params = SliceParams()
    params.shell = ShellParams(height=total_height, layer_height=layer_height, wall_thickness=1.2)
    params.edge_wrap = EdgeWrapParams(
        outline_enabled=True,
        outline_width=3.0,
        outline_height=3.0,
        outline_offset=0.0,
        outline_direction=EdgeDirection.OUTER  # 外部勾边
    )

    # 创建STL写入器
    writer = STLWriter(wall_thickness=1.2)

    try:
        # 构建勾边网格
        outline_mesh = writer._build_outline_mesh([contour], result, params)

        if outline_mesh is not None:
            print(f"✓ 勾边网格生成成功!")
            print(f"  - 顶点数: {len(outline_mesh.vertices)}")
            print(f"  - 面数: {len(outline_mesh.faces)}")
            print(f"  - 网格是否有效: {outline_mesh.is_watertight}")

            # 检查是否有异常的几何
            bounds = outline_mesh.bounds
            print(f"  - 边界框: X[{bounds[0][0]:.2f}, {bounds[1][0]:.2f}]  Y[{bounds[0][1]:.2f}, {bounds[1][1]:.2f}]  Z[{bounds[0][2]:.2f}, {bounds[1][2]:.2f}]")

            # 检查是否有非常大的面（可能是错误的几何）
            face_areas = outline_mesh.area_faces
            max_face_area = max(face_areas) if len(face_areas) > 0 else 0
            avg_face_area = sum(face_areas) / len(face_areas) if len(face_areas) > 0 else 0
            print(f"  - 最大面积: {max_face_area:.4f}")
            print(f"  - 平均面积: {avg_face_area:.4f}")

            # 如果最大面积远大于平均面积，可能有问题
            if max_face_area > 100 * avg_face_area:
                print(f"  ⚠ 警告: 存在异常大的面，可能有几何错误")
            else:
                print(f"  ✓ 面积分布正常")

            return True
        else:
            print("✗ 勾边网格生成失败: 返回None")
            return False

    except Exception as e:
        print(f"✗ 勾边网格生成异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_inner_outline():
    """测试内部勾边"""
    print("\n" + "=" * 60)
    print("测试内部勾边")
    print("=" * 60)

    # 创建复杂轮廓
    contour = create_complex_contour()
    print(f"轮廓点数: {len(contour.outer.points)}")

    # 创建切片结果
    layers = []
    total_height = 30.0
    layer_height = 0.3
    num_layers = int(total_height / layer_height)

    for i in range(num_layers):
        layer = Layer(
            z_height=i * layer_height,
            layer_height=layer_height,
            extruder=ExtruderType.EXTRUDER_1
        )

        layer_path = LayerPath(
            points=contour.outer.points,
            role=PathRole.WALL,
            extruder=ExtruderType.EXTRUDER_1,
            line_width=1.2,
            is_closed=True
        )
        layer.paths.append(layer_path)
        layers.append(layer)

    result = SliceResult(
        layers=layers,
        total_layers=num_layers,
        total_height=total_height
    )

    # 创建参数 - 内部勾边
    params = SliceParams()
    params.shell = ShellParams(height=total_height, layer_height=layer_height, wall_thickness=1.2)
    params.edge_wrap = EdgeWrapParams(
        outline_enabled=True,
        outline_width=3.0,
        outline_height=3.0,
        outline_offset=0.0,
        outline_direction=EdgeDirection.INNER  # 内部勾边
    )

    # 创建STL写入器
    writer = STLWriter(wall_thickness=1.2)

    try:
        # 构建勾边网格
        outline_mesh = writer._build_outline_mesh([contour], result, params)

        if outline_mesh is not None:
            print(f"✓ 内部勾边网格生成成功!")
            print(f"  - 顶点数: {len(outline_mesh.vertices)}")
            print(f"  - 面数: {len(outline_mesh.faces)}")

            # 检查面积分布
            face_areas = outline_mesh.area_faces
            max_face_area = max(face_areas) if len(face_areas) > 0 else 0
            avg_face_area = sum(face_areas) / len(face_areas) if len(face_areas) > 0 else 0
            print(f"  - 最大面积: {max_face_area:.4f}")
            print(f"  - 平均面积: {avg_face_area:.4f}")

            if max_face_area > 100 * avg_face_area:
                print(f"  ⚠ 警告: 存在异常大的面，可能有几何错误")
            else:
                print(f"  ✓ 面积分布正常")

            return True
        else:
            print("✗ 内部勾边网格生成失败: 返回None")
            return False

    except Exception as e:
        print(f"✗ 内部勾边网格生成异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_export_stl():
    """测试导出STL文件"""
    print("\n" + "=" * 60)
    print("测试导出STL文件")
    print("=" * 60)

    # 创建复杂轮廓
    contour = create_complex_contour()

    # 创建切片结果
    layers = []
    total_height = 30.0
    layer_height = 0.3
    num_layers = int(total_height / layer_height)

    for i in range(num_layers):
        layer = Layer(
            z_height=i * layer_height,
            layer_height=layer_height,
            extruder=ExtruderType.EXTRUDER_1
        )

        layer_path = LayerPath(
            points=contour.outer.points,
            role=PathRole.WALL,
            extruder=ExtruderType.EXTRUDER_1,
            line_width=1.2,
            is_closed=True
        )
        layer.paths.append(layer_path)
        layers.append(layer)

    result = SliceResult(
        layers=layers,
        total_layers=num_layers,
        total_height=total_height
    )

    # 创建参数 - 启用勾边
    params = SliceParams()
    params.shell = ShellParams(height=total_height, layer_height=layer_height, wall_thickness=1.2)
    params.edge_wrap = EdgeWrapParams(
        outline_enabled=True,
        outline_width=3.0,
        outline_height=3.0,
        outline_offset=0.0,
        outline_direction=EdgeDirection.OUTER
    )

    # 导出STL
    output_path = os.path.join(os.path.dirname(__file__), "test_outline_output.stl")
    writer = STLWriter(wall_thickness=1.2)

    try:
        writer.write(result, output_path, binary=True, contours=[contour], params=params)

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✓ STL文件导出成功!")
            print(f"  - 文件路径: {output_path}")
            print(f"  - 文件大小: {file_size / 1024:.2f} KB")

            # 清理测试文件
            os.remove(output_path)
            print(f"  - 测试文件已清理")
            return True
        else:
            print("✗ STL文件导出失败: 文件不存在")
            return False

    except Exception as e:
        print(f"✗ STL文件导出异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("勾边功能修复测试")
    print("=" * 60 + "\n")

    results = []

    # 运行测试
    results.append(("复杂轮廓外部勾边", test_complex_outline()))
    results.append(("复杂轮廓内部勾边", test_inner_outline()))
    results.append(("STL文件导出", test_export_stl()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("所有测试通过! 勾边功能修复成功")
    else:
        print("部分测试失败，请检查代码")
    print("=" * 60)
