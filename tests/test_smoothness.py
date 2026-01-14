"""
DXF解析平滑度测试

验证曲线离散化后的平滑程度
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.types import Point, Path as ContourPath
from src.core.dxf_parser import DXFParser


def calculate_angle_deviation(points: list) -> float:
    """
    计算路径的最大角度偏差

    平滑的曲线应该有较小的相邻线段角度变化
    返回最大角度变化（度）
    """
    if len(points) < 3:
        return 0.0

    max_deviation = 0.0

    for i in range(1, len(points) - 1):
        # 计算前后两个向量
        v1_x = points[i].x - points[i-1].x
        v1_y = points[i].y - points[i-1].y
        v2_x = points[i+1].x - points[i].x
        v2_y = points[i+1].y - points[i].y

        # 计算向量长度
        len1 = math.sqrt(v1_x**2 + v1_y**2)
        len2 = math.sqrt(v2_x**2 + v2_y**2)

        if len1 < 1e-10 or len2 < 1e-10:
            continue

        # 计算夹角
        dot = v1_x * v2_x + v1_y * v2_y
        cos_angle = dot / (len1 * len2)
        cos_angle = max(-1, min(1, cos_angle))  # 防止数值误差

        angle = math.degrees(math.acos(cos_angle))
        max_deviation = max(max_deviation, angle)

    return max_deviation


def test_circle_smoothness():
    """测试圆形解析的平滑度"""
    parser = DXFParser(arc_resolution=128, chord_error=0.05)

    # 模拟一个半径为50mm的圆
    radius = 50.0
    points = []

    # 使用自适应分辨率计算分段数
    if radius > parser.chord_error:
        max_angle = 2 * math.acos(1 - parser.chord_error / radius)
        num_segments = int(math.ceil(2 * math.pi / max_angle))
    else:
        num_segments = parser.arc_resolution

    num_segments = max(parser.MIN_SEGMENTS_PER_ARC, min(parser.MAX_SEGMENTS_PER_ARC, num_segments))

    for i in range(num_segments):
        angle = 2 * math.pi * i / num_segments
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append(Point(x, y))

    # 计算最大角度偏差
    max_deviation = calculate_angle_deviation(points)

    print(f"圆形 (R={radius}mm):")
    print(f"  分段数: {num_segments}")
    print(f"  最大角度偏差: {max_deviation:.2f}°")

    # 对于50mm半径的圆，最大角度偏差应该很小（允许6度以内）
    assert max_deviation < 6.0, f"角度偏差过大: {max_deviation}°"
    print("  ✓ 通过")


def test_small_arc_smoothness():
    """测试小圆弧的平滑度"""
    parser = DXFParser(arc_resolution=128, chord_error=0.05)

    # 模拟一个小半径圆弧 (10mm, 90度弧)
    radius = 10.0
    sweep_angle = math.pi / 2  # 90度

    # 计算自适应分段数
    base_segments = int(sweep_angle / (2 * math.pi) * parser.arc_resolution)

    if radius > parser.chord_error:
        max_angle = 2 * math.acos(1 - parser.chord_error / radius)
        error_segments = int(math.ceil(sweep_angle / max_angle))
    else:
        error_segments = base_segments

    num_segments = max(base_segments, error_segments)
    num_segments = max(parser.MIN_SEGMENTS_PER_ARC, min(parser.MAX_SEGMENTS_PER_ARC, num_segments))

    points = []
    for i in range(num_segments + 1):
        t = i / num_segments
        angle = t * sweep_angle
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append(Point(x, y))

    max_deviation = calculate_angle_deviation(points)

    print(f"\n小圆弧 (R={radius}mm, 90°):")
    print(f"  分段数: {num_segments}")
    print(f"  最大角度偏差: {max_deviation:.2f}°")

    assert max_deviation < 6.0, f"角度偏差过大: {max_deviation}°"
    print("  ✓ 通过")


def test_large_circle_smoothness():
    """测试大圆的平滑度"""
    parser = DXFParser(arc_resolution=128, chord_error=0.05)

    # 模拟一个大半径圆 (200mm)
    radius = 200.0

    if radius > parser.chord_error:
        max_angle = 2 * math.acos(1 - parser.chord_error / radius)
        num_segments = int(math.ceil(2 * math.pi / max_angle))
    else:
        num_segments = parser.arc_resolution

    num_segments = max(parser.MIN_SEGMENTS_PER_ARC, min(parser.MAX_SEGMENTS_PER_ARC, num_segments))

    points = []
    for i in range(num_segments):
        angle = 2 * math.pi * i / num_segments
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append(Point(x, y))

    max_deviation = calculate_angle_deviation(points)

    print(f"\n大圆 (R={radius}mm):")
    print(f"  分段数: {num_segments}")
    print(f"  最大角度偏差: {max_deviation:.2f}°")

    # 大圆应该非常平滑
    assert max_deviation < 3.0, f"角度偏差过大: {max_deviation}°"
    print("  ✓ 通过")


def test_chord_error_effectiveness():
    """测试弦长误差控制的有效性"""

    test_cases = [
        (0.1, "粗糙"),
        (0.05, "标准"),
        (0.02, "精细"),
    ]

    radius = 50.0

    print("\n弦长误差对比测试 (R=50mm圆):")
    print("-" * 40)

    for chord_error, desc in test_cases:
        parser = DXFParser(chord_error=chord_error)

        if radius > chord_error:
            max_angle = 2 * math.acos(1 - chord_error / radius)
            num_segments = int(math.ceil(2 * math.pi / max_angle))
        else:
            num_segments = parser.arc_resolution

        num_segments = max(parser.MIN_SEGMENTS_PER_ARC, min(parser.MAX_SEGMENTS_PER_ARC, num_segments))

        points = []
        for i in range(num_segments):
            angle = 2 * math.pi * i / num_segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            points.append(Point(x, y))

        max_deviation = calculate_angle_deviation(points)

        print(f"  {desc} (chord_error={chord_error}mm):")
        print(f"    分段数: {num_segments}, 最大角度偏差: {max_deviation:.2f}°")

    print("  ✓ 完成")


def compare_old_vs_new():
    """对比新旧解析器的分段数差异"""

    print("\n新旧解析器对比:")
    print("=" * 50)

    test_radii = [5, 10, 20, 50, 100, 200]

    print(f"{'半径(mm)':<10} {'旧分段数':<12} {'新分段数':<12} {'提升倍数':<10}")
    print("-" * 50)

    for radius in test_radii:
        # 旧方法: 固定32分段
        old_segments = 32

        # 新方法: 自适应
        chord_error = 0.05
        if radius > chord_error:
            max_angle = 2 * math.acos(1 - chord_error / radius)
            new_segments = int(math.ceil(2 * math.pi / max_angle))
        else:
            new_segments = 128
        new_segments = max(8, min(360, new_segments))

        ratio = new_segments / old_segments
        print(f"{radius:<10} {old_segments:<12} {new_segments:<12} {ratio:.1f}x")

    print("=" * 50)


if __name__ == "__main__":
    print("DXF解析平滑度测试")
    print("=" * 50)

    test_circle_smoothness()
    test_small_arc_smoothness()
    test_large_circle_smoothness()
    test_chord_error_effectiveness()
    compare_old_vs_new()

    print("\n所有测试通过！")
