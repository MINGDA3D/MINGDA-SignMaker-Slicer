"""
可视化裙边 v2 算法 vs v1 对比

生成一张图，左边是 G-code 路径模式（使用 generate_skirt_clipped），
右边是裙边多边形的填充效果。

用于验证：
1. 拐角处裙边是否绕着走（而非被删除）
2. 裙边是否与模型相交
3. 多个轮廓之间裙边是否重叠
"""
import math
import sys
from PIL import Image, ImageDraw, ImageFont

from src.core.dxf_parser import DXFParser
from src.core.types import SkirtParams, Point, Path, Contour
from src.core.skirt_generator import SkirtGenerator
from src.core.path_offset import PathOffset


def create_test_contours():
    """创建测试用的带尖角轮廓"""
    # 一个五角星形状（大量尖角）
    def star_points(cx, cy, outer_r, inner_r, n=5):
        pts = []
        for i in range(2 * n):
            angle = math.pi / 2 + i * math.pi / n
            r = outer_r if i % 2 == 0 else inner_r
            pts.append(Point(cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return pts

    star1 = Contour(
        outer=Path(points=star_points(50, 50, 30, 12)),
        holes=[],
        name="Star1"
    )

    # 一个L形（直角拐角）
    l_shape = Contour(
        outer=Path(points=[
            Point(120, 20), Point(160, 20), Point(160, 50),
            Point(140, 50), Point(140, 80), Point(120, 80)
        ]),
        holes=[],
        name="L-shape"
    )

    # 两个相近的矩形（测试禁区裁剪）
    rect1 = Contour(
        outer=Path(points=[
            Point(200, 20), Point(240, 20), Point(240, 60), Point(200, 60)
        ]),
        holes=[],
        name="Rect1"
    )
    rect2 = Contour(
        outer=Path(points=[
            Point(250, 20), Point(290, 20), Point(290, 60), Point(250, 60)
        ]),
        holes=[],
        name="Rect2"
    )

    return [star1, l_shape, rect1, rect2]


def visualize(contours, output_path, title="Skirt V2"):
    """可视化裙边效果"""
    params = SkirtParams(
        enabled=True, width=5.0, height=5.0, offset=0.0,
        interval=10.0, is_outer=True, extrusion_width=0.4
    )
    wall_thickness = 1.2
    path_offset = PathOffset()
    generator = SkirtGenerator()

    # 收集所有点，计算边界
    all_x, all_y = [], []
    for c in contours:
        for p in c.outer.points:
            all_x.append(p.x)
            all_y.append(p.y)

    if not all_x:
        print("No contour points found!")
        return

    min_x, max_x = min(all_x) - 10, max(all_x) + 10
    min_y, max_y = min(all_y) - 10, max(all_y) + 10

    W, H = 1600, 900
    margin = 60
    scale = min((W - 2 * margin) / (max_x - min_x),
                (H - 2 * margin) / (max_y - min_y))

    def to_px(x, y):
        return (int((x - min_x) * scale + margin),
                int(H - (y - min_y) * scale - margin))

    img = Image.new("RGB", (W, H), (30, 30, 40))
    draw = ImageDraw.Draw(img)

    # 标题
    draw.text((W // 2 - 100, 10), title, fill=(255, 255, 255))

    # 画轮廓（填充半透明蓝色）
    for c in contours:
        pts = [to_px(p.x, p.y) for p in c.outer.points]
        draw.polygon(pts, fill=(20, 30, 60), outline=(80, 130, 220))
        # 画孔
        for hole in c.holes:
            hole_pts = [to_px(p.x, p.y) for p in hole.points]
            draw.polygon(hole_pts, fill=(30, 30, 40), outline=(80, 130, 220))

    # 画裙边（使用 generate_skirt_clipped 的 v2 算法）
    colors = [
        (255, 100, 100), (100, 255, 100), (255, 255, 100),
        (255, 100, 255), (100, 255, 255), (200, 200, 200)
    ]

    total_skirt_paths = 0
    for ci, contour in enumerate(contours):
        color = colors[ci % len(colors)]
        fill_color = (color[0] // 4, color[1] // 4, color[2] // 4)

        skirt_paths = generator.generate_skirt_clipped(
            contour=contour,
            all_contours=contours,
            params=params,
            wall_thickness=wall_thickness,
            path_offset=path_offset
        )

        total_skirt_paths += len(skirt_paths)

        for lp in skirt_paths:
            pts = [to_px(p.x, p.y) for p in lp.points]
            if len(pts) >= 3:
                draw.polygon(pts, fill=fill_color, outline=color)

        # 标注轮廓名称
        if contour.outer.points:
            cx = sum(p.x for p in contour.outer.points) / len(contour.outer.points)
            cy = sum(p.y for p in contour.outer.points) / len(contour.outer.points)
            px, py = to_px(cx, cy)
            name = contour.name or f"Contour {ci}"
            draw.text((px - 20, py - 8), name, fill=(255, 255, 255))

    # 统计信息
    info_text = f"Contours: {len(contours)} | Skirt paths: {total_skirt_paths}"
    draw.text((10, H - 30), info_text, fill=(180, 180, 180))

    img.save(output_path)
    print(f"Saved to {output_path}")
    print(f"  Contours: {len(contours)}, Skirt paths: {total_skirt_paths}")


def main():
    # Test 1: 合成测试图形
    print("=== Test 1: Synthetic shapes ===")
    test_contours = create_test_contours()
    visualize(test_contours, "e:/SignMaker Slicer/Debug/skirt_v2_synthetic.png",
              "Skirt V2 - Synthetic Shapes (Star, L, Rects)")

    # Test 2: 真实 DXF 文件
    dxf_files = [
        "e:/SignMaker Slicer/Debug/Coca-Cola.dxf",
        "e:/SignMaker Slicer/Debug/20-MD.dxf",
    ]

    for dxf_path in dxf_files:
        try:
            parser = DXFParser()
            contours = parser.parse(dxf_path)
            name = dxf_path.split("/")[-1].replace(".dxf", "")
            print(f"\n=== Test: {name} ({len(contours)} contours) ===")
            visualize(contours,
                      f"e:/SignMaker Slicer/Debug/skirt_v2_{name}.png",
                      f"Skirt V2 - {name}")
        except Exception as e:
            print(f"Error processing {dxf_path}: {e}")


if __name__ == "__main__":
    main()
