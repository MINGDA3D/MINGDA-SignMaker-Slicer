"""
SignMaker Slicer - 切片模式 & 预览模式 效果图
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# 配色方案
COLORS = {
    "bg_base": "#0A0E14",
    "bg_primary": "#0D1219",
    "bg_secondary": "#131A24",
    "bg_card": "#1A2332",
    "bg_elevated": "#1F2A3C",
    "bg_hover": "#253345",
    "text_primary": "#E6EDF3",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",
    "accent_primary": "#3B82F6",
    "accent_secondary": "#06B6D4",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "info": "#6366F1",
    "border_subtle": "#1E293B",
    "border_default": "#334155",
    "border_focus": "#3B82F6",
    "path_outer": "#3B82F6",
    "path_inner": "#06B6D4",
    "path_fill": "#10B981",
    "path_travel": "#475569",
    "extruder_1": "#3B82F6",
    "extruder_2": "#EC4899",
    "extruder_3": "#F59E0B",
    "layer_base": "#1E3A5F",
    "layer_mid": "#3B82F6",
    "layer_top": "#06B6D4",
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) for k, v in COLORS.items()}

WIDTH = 1600
HEIGHT = 1000

# 字体
try:
    font_h1 = ImageFont.truetype("msyh.ttc", 16)
    font_h2 = ImageFont.truetype("msyh.ttc", 13)
    font_body = ImageFont.truetype("msyh.ttc", 11)
    font_small = ImageFont.truetype("msyh.ttc", 9)
    font_mono = ImageFont.truetype("consola.ttf", 11)
    font_icon = ImageFont.truetype("seguisym.ttf", 14)
    font_large = ImageFont.truetype("msyh.ttc", 48)
except:
    font_h1 = font_h2 = font_body = font_small = font_mono = font_icon = font_large = ImageFont.load_default()


def create_base_layout(draw, active_tab="project"):
    """创建基础布局"""
    HEADER_H = 48
    FOOTER_H = 36

    # 顶部导航栏
    draw.rounded_rectangle([0, 0, WIDTH, HEADER_H], radius=0, fill=C["bg_primary"])

    # Logo
    draw.rectangle([16, 12, 20, 36], fill=C["accent_primary"])
    draw.text((28, 14), "SignMaker", font=font_h1, fill=C["text_primary"])
    draw.text((110, 16), "Slicer", font=font_h2, fill=C["accent_secondary"])

    # 中央导航标签页 - 参考UI_Home样式
    nav_items = [("首页", None), ("项目", "project"), ("预览", "preview")]
    nav_start_x = (WIDTH - 240) // 2
    for i, (name, key) in enumerate(nav_items):
        nx = nav_start_x + i * 80
        if key == active_tab:
            # 渐变填充按钮
            for px in range(64):
                ratio = px / 64
                r = int(C["accent_primary"][0] + (C["accent_secondary"][0] - C["accent_primary"][0]) * ratio)
                g = int(C["accent_primary"][1] + (C["accent_secondary"][1] - C["accent_primary"][1]) * ratio)
                b = int(C["accent_primary"][2] + (C["accent_secondary"][2] - C["accent_primary"][2]) * ratio)
                draw.line([(nx + px, 8), (nx + px, 40)], fill=(r, g, b))
            draw.text((nx + 20, 14), name, font=font_h2, fill=(255, 255, 255))
        else:
            draw.text((nx + 20, 14), name, font=font_h2, fill=C["text_muted"])

    # 右侧按钮
    right_tools = ["⚙", "?", "☰"]
    tool_x = WIDTH - 140
    for icon in right_tools:
        draw.rounded_rectangle([tool_x, 10, tool_x + 32, 38], radius=6, fill=C["bg_card"])
        draw.text((tool_x + 10, 14), icon, font=font_icon, fill=C["text_secondary"])
        tool_x += 40

    # 底部状态栏
    draw.rounded_rectangle([0, HEIGHT - FOOTER_H, WIDTH, HEIGHT], radius=0, fill=C["bg_primary"])
    draw.text((20, HEIGHT - FOOTER_H + 10), "● 就绪", font=font_body, fill=C["success"])
    draw.text((WIDTH - 150, HEIGHT - FOOTER_H + 10), "SignMaker Slicer v1.0", font=font_small, fill=C["text_muted"])

    return HEADER_H, FOOTER_H


def generate_slice_mode():
    """生成切片模式界面"""
    img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_base"])
    draw = ImageDraw.Draw(img)

    HEADER_H, FOOTER_H = create_base_layout(draw, "slice")

    content_y = HEADER_H
    content_h = HEIGHT - HEADER_H - FOOTER_H

    # ============================================
    # 左侧 - 切片参数面板
    # ============================================
    LEFT_W = 320
    draw.rounded_rectangle([8, content_y + 8, LEFT_W - 8, content_y + content_h - 8], radius=12, fill=C["bg_secondary"])

    # 标题
    draw.text((24, content_y + 24), "切片参数", font=font_h1, fill=C["text_primary"])

    # 字壳工艺卡片
    card_y = content_y + 60
    draw.rounded_rectangle([16, card_y, LEFT_W - 16, card_y + 200], radius=10, fill=C["bg_card"])
    draw.text((28, card_y + 12), "字壳工艺", font=font_h2, fill=C["text_primary"])

    # 参数
    params = [
        ("字边类型", "直边"),
        ("字壳高度", "30 mm"),
        ("斜边宽度", "5 mm"),
        ("底板厚度", "10 mm"),
        ("层高", "0.3 mm"),
        ("壁厚", "1.2 mm"),
    ]
    py = card_y + 40
    for label, value in params:
        draw.text((28, py), label, font=font_body, fill=C["text_secondary"])
        draw.text((180, py), value, font=font_mono, fill=C["text_primary"])
        py += 26

    # 换色层卡片
    card_y = content_y + 280
    draw.rounded_rectangle([16, card_y, LEFT_W - 16, card_y + 180], radius=10, fill=C["bg_card"])
    draw.text((28, card_y + 12), "换色层设置", font=font_h2, fill=C["text_primary"])

    # 换色层可视化
    layer_y = card_y + 45
    layers = [
        ("第1层", "0-10mm", C["extruder_1"]),
        ("第2层", "10-15mm", C["extruder_2"]),
        ("第3层", "15-20mm", C["extruder_3"]),
        ("第4层", "20-30mm", C["extruder_1"]),
    ]
    for name, range_text, color in layers:
        draw.rounded_rectangle([28, layer_y, 48, layer_y + 24], radius=4, fill=color)
        draw.text((58, layer_y + 4), name, font=font_body, fill=C["text_primary"])
        draw.text((130, layer_y + 4), range_text, font=font_small, fill=C["text_muted"])
        layer_y += 32

    # 台阶设置卡片
    card_y = content_y + 480
    draw.rounded_rectangle([16, card_y, LEFT_W - 16, card_y + 120], radius=10, fill=C["bg_card"])
    draw.text((28, card_y + 12), "台阶V槽", font=font_h2, fill=C["text_primary"])

    steps = [("底板台阶", "5mm", True), ("面板台阶", "27mm", True)]
    step_y = card_y + 45
    for name, pos, enabled in steps:
        # 复选框
        box_color = C["accent_primary"] if enabled else C["border_default"]
        draw.rounded_rectangle([28, step_y, 44, step_y + 16], radius=3,
                               fill=C["accent_primary"] if enabled else C["bg_elevated"], outline=box_color)
        if enabled:
            draw.text((31, step_y - 1), "✓", font=font_small, fill=(255,255,255))
        draw.text((54, step_y), name, font=font_body, fill=C["text_secondary"])
        draw.text((180, step_y), pos, font=font_mono, fill=C["text_primary"])
        step_y += 30

    # 计算按钮
    btn_y = content_y + content_h - 70
    # 渐变按钮
    for i in range(LEFT_W - 32):
        ratio = i / (LEFT_W - 32)
        color = tuple(int(C["accent_primary"][j] + (C["accent_secondary"][j] - C["accent_primary"][j]) * ratio) for j in range(3))
        draw.line([(16 + i, btn_y), (16 + i, btn_y + 44)], fill=color)
    draw.rounded_rectangle([16, btn_y, LEFT_W - 16, btn_y + 44], radius=10, outline=None)
    draw.text((100, btn_y + 12), "开始切片", font=font_h2, fill=(255,255,255))

    # ============================================
    # 中央 - 层预览 + 路径可视化
    # ============================================
    center_x = LEFT_W
    center_w = WIDTH - LEFT_W - 320
    center_h = content_h

    draw.rounded_rectangle([center_x + 8, content_y + 8, center_x + center_w - 8, content_y + center_h - 8],
                           radius=12, fill=C["bg_primary"])

    # 工具栏
    toolbar_y = content_y + 20
    draw.rounded_rectangle([center_x + 20, toolbar_y, center_x + center_w - 20, toolbar_y + 40], radius=8, fill=C["bg_card"])

    # 路径类型切换
    path_types = [("外壁", True), ("内壁", True), ("填充", False), ("空走", False)]
    ptx = center_x + 32
    for name, active in path_types:
        if active:
            draw.rounded_rectangle([ptx, toolbar_y + 6, ptx + 50, toolbar_y + 34], radius=6, fill=C["accent_primary"])
            draw.text((ptx + 10, toolbar_y + 12), name, font=font_body, fill=(255,255,255))
        else:
            draw.rounded_rectangle([ptx, toolbar_y + 6, ptx + 50, toolbar_y + 34], radius=6, fill=C["bg_elevated"])
            draw.text((ptx + 10, toolbar_y + 12), name, font=font_body, fill=C["text_muted"])
        ptx += 60

    # 层信息
    draw.text((center_x + center_w - 200, toolbar_y + 12), "当前层: 50 / 100", font=font_body, fill=C["text_secondary"])

    # 画布区域
    canvas_y = toolbar_y + 56
    canvas_h = center_h - 150
    draw.rounded_rectangle([center_x + 20, canvas_y, center_x + center_w - 20, canvas_y + canvas_h],
                           radius=8, fill=C["bg_base"])

    # 网格
    grid_color = (20, 28, 38)
    for gx in range(center_x + 20, center_x + center_w - 20, 25):
        draw.line([(gx, canvas_y), (gx, canvas_y + canvas_h)], fill=grid_color)
    for gy in range(canvas_y, canvas_y + canvas_h, 25):
        draw.line([(center_x + 20, gy), (center_x + center_w - 20, gy)], fill=grid_color)

    # 绘制路径预览 (简化的字形轮廓)
    path_center_x = center_x + center_w // 2
    path_center_y = canvas_y + canvas_h // 2

    # 外轮廓
    draw.rounded_rectangle([path_center_x - 80, path_center_y - 100, path_center_x + 80, path_center_y + 100],
                           radius=8, outline=C["path_outer"], width=3)
    # 内轮廓
    draw.rounded_rectangle([path_center_x - 65, path_center_y - 85, path_center_x + 65, path_center_y + 85],
                           radius=6, outline=C["path_inner"], width=2)

    # 填充线 (简化表示)
    for i in range(-60, 61, 15):
        draw.line([(path_center_x - 55 + i, path_center_y - 75),
                   (path_center_x + 55 + i, path_center_y + 75)], fill=C["path_fill"], width=1)

    # 起点标记
    draw.ellipse([path_center_x - 75, path_center_y - 95, path_center_x - 60, path_center_y - 80],
                 fill=C["success"])

    # 底部层滑块
    slider_y = canvas_y + canvas_h + 16
    draw.rounded_rectangle([center_x + 20, slider_y, center_x + center_w - 20, slider_y + 50], radius=8, fill=C["bg_card"])

    # 层高时间轴
    draw.text((center_x + 32, slider_y + 8), "层高", font=font_small, fill=C["text_muted"])

    # 滑块轨道
    track_x = center_x + 80
    track_w = center_w - 180
    draw.rounded_rectangle([track_x, slider_y + 20, track_x + track_w, slider_y + 28], radius=4, fill=C["bg_elevated"])

    # 进度 (50%)
    progress_w = int(track_w * 0.5)
    draw.rounded_rectangle([track_x, slider_y + 20, track_x + progress_w, slider_y + 28], radius=4, fill=C["accent_primary"])

    # 滑块手柄
    handle_x = track_x + progress_w - 8
    draw.ellipse([handle_x, slider_y + 14, handle_x + 20, slider_y + 34], fill=C["text_primary"], outline=C["accent_primary"])

    # 层数显示
    draw.text((center_x + center_w - 80, slider_y + 16), "15.0 mm", font=font_mono, fill=C["accent_secondary"])

    # ============================================
    # 右侧 - 切片统计
    # ============================================
    RIGHT_W = 320
    right_x = WIDTH - RIGHT_W
    draw.rounded_rectangle([right_x + 8, content_y + 8, WIDTH - 8, content_y + content_h - 8],
                           radius=12, fill=C["bg_secondary"])

    draw.text((right_x + 24, content_y + 24), "切片统计", font=font_h1, fill=C["text_primary"])

    # 统计卡片
    stats = [
        ("总层数", "100 层", C["accent_primary"]),
        ("打印时间", "2h 15min", C["accent_secondary"]),
        ("耗材用量", "125.8 m", C["success"]),
        ("外壁长度", "45.2 m", C["path_outer"]),
        ("填充长度", "68.5 m", C["path_fill"]),
    ]
    stat_y = content_y + 70
    for label, value, color in stats:
        draw.rounded_rectangle([right_x + 16, stat_y, WIDTH - 24, stat_y + 60], radius=8, fill=C["bg_card"])
        draw.text((right_x + 28, stat_y + 10), label, font=font_small, fill=C["text_muted"])
        draw.text((right_x + 28, stat_y + 30), value, font=font_h2, fill=color)
        stat_y += 72

    # 挤出机用量
    draw.text((right_x + 24, stat_y + 20), "挤出机用量", font=font_h2, fill=C["text_primary"])
    stat_y += 50

    extruders = [
        ("挤出机 1 (遮光)", "85.2 m", C["extruder_1"], 0.7),
        ("挤出机 2 (透光)", "25.6 m", C["extruder_2"], 0.2),
        ("挤出机 3 (透光)", "15.0 m", C["extruder_3"], 0.1),
    ]
    for name, usage, color, ratio in extruders:
        draw.rounded_rectangle([right_x + 16, stat_y, WIDTH - 24, stat_y + 50], radius=8, fill=C["bg_card"])
        draw.text((right_x + 28, stat_y + 8), name, font=font_small, fill=C["text_muted"])
        draw.text((right_x + 200, stat_y + 8), usage, font=font_mono, fill=color)

        # 进度条
        bar_w = RIGHT_W - 56
        draw.rounded_rectangle([right_x + 28, stat_y + 32, right_x + 28 + bar_w, stat_y + 40], radius=3, fill=C["bg_elevated"])
        draw.rounded_rectangle([right_x + 28, stat_y + 32, right_x + 28 + int(bar_w * ratio), stat_y + 40], radius=3, fill=color)
        stat_y += 58

    # 导出按钮
    btn_y = content_y + content_h - 70
    draw.rounded_rectangle([right_x + 16, btn_y, WIDTH - 24, btn_y + 44], radius=10, fill=C["bg_card"], outline=C["border_default"])
    draw.text((right_x + 100, btn_y + 12), "导出 G-Code", font=font_h2, fill=C["text_secondary"])

    return img


def generate_preview_mode():
    """生成预览模式界面"""
    img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_base"])
    draw = ImageDraw.Draw(img)

    HEADER_H, FOOTER_H = create_base_layout(draw, "preview")

    content_y = HEADER_H
    content_h = HEIGHT - HEADER_H - FOOTER_H

    # ============================================
    # 左侧 - 视图控制
    # ============================================
    LEFT_W = 280
    draw.rounded_rectangle([8, content_y + 8, LEFT_W - 8, content_y + content_h - 8], radius=12, fill=C["bg_secondary"])

    draw.text((24, content_y + 24), "视图控制", font=font_h1, fill=C["text_primary"])

    # 视图预设
    card_y = content_y + 60
    draw.rounded_rectangle([16, card_y, LEFT_W - 16, card_y + 100], radius=10, fill=C["bg_card"])
    draw.text((28, card_y + 12), "视图预设", font=font_h2, fill=C["text_primary"])

    views = [("正视", False), ("俯视", False), ("侧视", False), ("3D", True)]
    vx = 28
    vy = card_y + 45
    for name, active in views:
        if active:
            draw.rounded_rectangle([vx, vy, vx + 50, vy + 36], radius=6, fill=C["accent_primary"])
            draw.text((vx + 12, vy + 10), name, font=font_body, fill=(255,255,255))
        else:
            draw.rounded_rectangle([vx, vy, vx + 50, vy + 36], radius=6, fill=C["bg_elevated"])
            draw.text((vx + 12, vy + 10), name, font=font_body, fill=C["text_secondary"])
        vx += 58

    # 显示选项
    card_y = content_y + 180
    draw.rounded_rectangle([16, card_y, LEFT_W - 16, card_y + 200], radius=10, fill=C["bg_card"])
    draw.text((28, card_y + 12), "显示选项", font=font_h2, fill=C["text_primary"])

    options = [
        ("显示外壁", True, C["path_outer"]),
        ("显示内壁", True, C["path_inner"]),
        ("显示填充", False, C["path_fill"]),
        ("显示空走", False, C["path_travel"]),
        ("显示台阶", True, C["warning"]),
        ("显示裙边", True, C["success"]),
    ]
    oy = card_y + 45
    for name, enabled, color in options:
        # 复选框
        draw.rounded_rectangle([28, oy, 44, oy + 16], radius=3,
                               fill=color if enabled else C["bg_elevated"],
                               outline=color if enabled else C["border_default"])
        if enabled:
            draw.text((31, oy - 1), "✓", font=font_small, fill=(255,255,255) if enabled else C["text_muted"])
        draw.text((54, oy), name, font=font_body, fill=C["text_primary"] if enabled else C["text_muted"])
        oy += 26

    # 颜色方案
    card_y = content_y + 400
    draw.rounded_rectangle([16, card_y, LEFT_W - 16, card_y + 120], radius=10, fill=C["bg_card"])
    draw.text((28, card_y + 12), "颜色方案", font=font_h2, fill=C["text_primary"])

    schemes = [("挤出机", True), ("路径类型", False), ("层高", False)]
    sy = card_y + 45
    for name, active in schemes:
        draw.ellipse([28, sy + 2, 42, sy + 16], fill=C["accent_primary"] if active else C["bg_elevated"],
                     outline=C["accent_primary"] if active else C["border_default"])
        if active:
            draw.ellipse([32, sy + 6, 38, sy + 12], fill=(255,255,255))
        draw.text((50, sy), name, font=font_body, fill=C["text_primary"] if active else C["text_secondary"])
        sy += 26

    # ============================================
    # 中央 - 3D预览
    # ============================================
    center_x = LEFT_W
    center_w = WIDTH - LEFT_W - 320
    center_h = content_h

    draw.rounded_rectangle([center_x + 8, content_y + 8, center_x + center_w - 8, content_y + center_h - 8],
                           radius=12, fill=C["bg_primary"])

    # 3D视口
    viewport_margin = 20
    viewport_y = content_y + viewport_margin
    viewport_h = center_h - 100

    draw.rounded_rectangle([center_x + viewport_margin, viewport_y,
                            center_x + center_w - viewport_margin, viewport_y + viewport_h],
                           radius=8, fill=C["bg_base"])

    # 绘制简化的3D字壳效果
    cx = center_x + center_w // 2
    cy = viewport_y + viewport_h // 2 - 30

    # 底部 (深色)
    draw.polygon([(cx - 100, cy + 80), (cx + 100, cy + 80), (cx + 120, cy + 60), (cx - 80, cy + 60)],
                 fill=C["layer_base"])

    # 中部层 (多层效果)
    for i in range(5):
        offset = i * 20
        alpha_color = tuple(int(C["layer_mid"][j] * (0.6 + i * 0.08)) for j in range(3))
        draw.polygon([
            (cx - 95 + i*3, cy + 60 - offset),
            (cx + 95 - i*3, cy + 60 - offset),
            (cx + 115 - i*3, cy + 40 - offset),
            (cx - 75 + i*3, cy + 40 - offset)
        ], fill=alpha_color, outline=C["path_outer"])

    # 顶部 (亮色)
    draw.polygon([(cx - 80, cy - 40), (cx + 80, cy - 40), (cx + 100, cy - 60), (cx - 60, cy - 60)],
                 fill=C["layer_top"], outline=C["accent_secondary"])

    # 斜边效果
    draw.polygon([(cx - 100, cy + 80), (cx - 80, cy - 40), (cx - 60, cy - 60), (cx - 80, cy + 60)],
                 fill=C["layer_mid"], outline=C["path_outer"])
    draw.polygon([(cx + 100, cy + 80), (cx + 80, cy - 40), (cx + 100, cy - 60), (cx + 120, cy + 60)],
                 fill=C["layer_mid"], outline=C["path_outer"])

    # 台阶标记
    draw.line([(cx - 110, cy + 70), (cx - 130, cy + 70)], fill=C["warning"], width=2)
    draw.text((cx - 180, cy + 63), "底板台阶", font=font_small, fill=C["warning"])

    draw.line([(cx - 90, cy - 50), (cx - 130, cy - 50)], fill=C["warning"], width=2)
    draw.text((cx - 180, cy - 57), "面板台阶", font=font_small, fill=C["warning"])

    # 尺寸标注
    draw.line([(cx + 140, cy + 80), (cx + 140, cy - 60)], fill=C["text_muted"], width=1)
    draw.line([(cx + 135, cy + 80), (cx + 145, cy + 80)], fill=C["text_muted"], width=1)
    draw.line([(cx + 135, cy - 60), (cx + 145, cy - 60)], fill=C["text_muted"], width=1)
    draw.text((cx + 150, cy + 5), "30mm", font=font_small, fill=C["text_muted"])

    # 旋转控制提示
    draw.rounded_rectangle([center_x + center_w - 180, viewport_y + 10,
                            center_x + center_w - 30, viewport_y + 35], radius=6, fill=C["bg_card"])
    draw.text((center_x + center_w - 170, viewport_y + 15), "拖拽旋转 | 滚轮缩放", font=font_small, fill=C["text_muted"])

    # 底部播放控制
    ctrl_y = viewport_y + viewport_h + 16
    draw.rounded_rectangle([center_x + 20, ctrl_y, center_x + center_w - 20, ctrl_y + 50], radius=8, fill=C["bg_card"])

    # 播放按钮
    draw.rounded_rectangle([center_x + 40, ctrl_y + 10, center_x + 80, ctrl_y + 40], radius=6, fill=C["accent_primary"])
    draw.text((center_x + 52, ctrl_y + 16), "▶", font=font_icon, fill=(255,255,255))

    # 进度条
    track_x = center_x + 100
    track_w = center_w - 280
    draw.rounded_rectangle([track_x, ctrl_y + 20, track_x + track_w, ctrl_y + 28], radius=4, fill=C["bg_elevated"])
    draw.rounded_rectangle([track_x, ctrl_y + 20, track_x + int(track_w * 0.7), ctrl_y + 28], radius=4, fill=C["accent_secondary"])

    # 时间显示
    draw.text((center_x + center_w - 150, ctrl_y + 16), "1:34:25 / 2:15:00", font=font_mono, fill=C["text_secondary"])

    # ============================================
    # 右侧 - 打印信息
    # ============================================
    RIGHT_W = 320
    right_x = WIDTH - RIGHT_W
    draw.rounded_rectangle([right_x + 8, content_y + 8, WIDTH - 8, content_y + content_h - 8],
                           radius=12, fill=C["bg_secondary"])

    draw.text((right_x + 24, content_y + 24), "打印信息", font=font_h1, fill=C["text_primary"])

    # 基本信息卡片
    card_y = content_y + 60
    draw.rounded_rectangle([right_x + 16, card_y, WIDTH - 24, card_y + 160], radius=10, fill=C["bg_card"])

    info_items = [
        ("文件名", "发光字-发.gcode"),
        ("总层数", "100 层"),
        ("打印时间", "2h 15min"),
        ("耗材用量", "125.8 m"),
        ("字壳高度", "30 mm"),
    ]
    iy = card_y + 16
    for label, value in info_items:
        draw.text((right_x + 28, iy), label, font=font_body, fill=C["text_muted"])
        draw.text((right_x + 150, iy), value, font=font_mono, fill=C["text_primary"])
        iy += 28

    # 当前层信息
    card_y = content_y + 240
    draw.rounded_rectangle([right_x + 16, card_y, WIDTH - 24, card_y + 120], radius=10, fill=C["bg_card"])
    draw.text((right_x + 28, card_y + 12), "当前层信息", font=font_h2, fill=C["text_primary"])

    layer_info = [
        ("层号", "70 / 100"),
        ("层高位置", "21.0 mm"),
        ("挤出机", "1号 (遮光)"),
    ]
    ly = card_y + 45
    for label, value in layer_info:
        draw.text((right_x + 28, ly), label, font=font_body, fill=C["text_muted"])
        draw.text((right_x + 150, ly), value, font=font_mono, fill=C["accent_secondary"])
        ly += 26

    # 图例
    card_y = content_y + 380
    draw.rounded_rectangle([right_x + 16, card_y, WIDTH - 24, card_y + 150], radius=10, fill=C["bg_card"])
    draw.text((right_x + 28, card_y + 12), "图例", font=font_h2, fill=C["text_primary"])

    legends = [
        ("挤出机 1", C["extruder_1"]),
        ("挤出机 2", C["extruder_2"]),
        ("挤出机 3", C["extruder_3"]),
        ("台阶位置", C["warning"]),
    ]
    lx = right_x + 28
    ly = card_y + 45
    for name, color in legends:
        draw.rounded_rectangle([lx, ly, lx + 20, ly + 16], radius=3, fill=color)
        draw.text((lx + 28, ly), name, font=font_body, fill=C["text_secondary"])
        ly += 26

    # 导出按钮组
    btn_y = content_y + content_h - 120
    draw.rounded_rectangle([right_x + 16, btn_y, WIDTH - 24, btn_y + 44], radius=10,
                           fill=C["bg_card"], outline=C["border_default"])
    draw.text((right_x + 80, btn_y + 12), "保存截图", font=font_h2, fill=C["text_secondary"])

    btn_y += 54
    # 渐变按钮
    for i in range(RIGHT_W - 40):
        ratio = i / (RIGHT_W - 40)
        color = tuple(int(C["accent_primary"][j] + (C["accent_secondary"][j] - C["accent_primary"][j]) * ratio) for j in range(3))
        draw.line([(right_x + 16 + i, btn_y), (right_x + 16 + i, btn_y + 44)], fill=color)
    draw.rounded_rectangle([right_x + 16, btn_y, WIDTH - 24, btn_y + 44], radius=10, outline=None)
    draw.text((right_x + 70, btn_y + 12), "发送到打印机", font=font_h2, fill=(255,255,255))

    return img


# 生成两张效果图
if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(output_dir, exist_ok=True)

    # 预览模式
    preview_img = generate_preview_mode()
    preview_path = os.path.join(output_dir, "UI_Preview_Mode.png")
    preview_img.save(preview_path, "PNG", quality=95)
    print(f"Saved: {preview_path}")

    print("Done!")
