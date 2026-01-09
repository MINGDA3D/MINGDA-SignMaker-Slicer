"""
SignMaker Slicer - 切片预览界面效果图
风格与项目其他页面保持一致，内容参考 OrcaSlicer 的信息架构
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

def load_icon(icon_path, size=24):
    """加载 PNG 图标"""
    if not os.path.exists(icon_path):
        return None
    try:
        icon = Image.open(icon_path).convert('RGBA')
        icon = icon.resize((size, size), Image.Resampling.LANCZOS)
        return icon
    except Exception as e:
        print(f"图标加载失败: {e}")
        return None

# ============================================
# 配色方案 - 与项目其他页面保持一致
# ============================================
COLORS = {
    # 背景层级
    "bg_base": "#0A0E14",
    "bg_primary": "#0D1219",
    "bg_secondary": "#131A24",
    "bg_card": "#1A2332",
    "bg_elevated": "#1F2A3C",
    "bg_hover": "#253345",

    # 文字
    "text_primary": "#E6EDF3",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",

    # 强调色
    "accent_primary": "#3B82F6",
    "accent_secondary": "#06B6D4",

    # 语义色
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "info": "#6366F1",

    # 边框
    "border_subtle": "#1E293B",
    "border_default": "#334155",
    "border_focus": "#3B82F6",

    # 路径颜色
    "path_outer": "#3B82F6",
    "path_inner": "#06B6D4",
    "path_fill": "#10B981",
    "path_travel": "#475569",

    # 挤出机颜色
    "extruder_1": "#3B82F6",
    "extruder_2": "#EC4899",
    "extruder_3": "#F59E0B",

    # 3D相关
    "layer_base": "#1E3A5F",
    "layer_mid": "#2563EB",
    "layer_top": "#06B6D4",
    "grid_3d": "#1a2535",
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
    font_mono_small = ImageFont.truetype("consola.ttf", 9)
    font_icon = ImageFont.truetype("seguisym.ttf", 14)
    font_large = ImageFont.truetype("msyh.ttc", 120)
except:
    font_h1 = font_h2 = font_body = font_small = font_mono = font_mono_small = font_icon = font_large = ImageFont.load_default()


def generate_preview_mode():
    """生成切片预览界面"""
    img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_base"])
    draw = ImageDraw.Draw(img)

    def draw_rounded_rect(x, y, w, h, r, fill=None, outline=None, width=1):
        draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline, width=width)

    def draw_text(x, y, text, font=None, fill=None):
        draw.text((x, y), text, font=font or font_body, fill=fill or C["text_secondary"])

    def draw_gradient_rect(x, y, w, h):
        for i in range(w):
            ratio = i / w
            color = tuple(int(C["accent_primary"][j] + (C["accent_secondary"][j] - C["accent_primary"][j]) * ratio) for j in range(3))
            draw.line([(x + i, y), (x + i, y + h)], fill=color)

    # ============================================
    # 布局常量
    # ============================================
    HEADER_H = 48
    SIDEBAR_RIGHT_W = 340
    FOOTER_H = 36
    LAYER_SLIDER_W = 50  # 层高滑块宽度

    content_y = HEADER_H
    content_h = HEIGHT - HEADER_H - FOOTER_H

    # ============================================
    # 顶部导航栏
    # ============================================
    draw_rounded_rect(0, 0, WIDTH, HEADER_H, 0, fill=C["bg_primary"])

    # Logo
    logo_path = os.path.join(os.path.dirname(__file__), "..", "docs", "images", "MINGDA_logo.png")
    logo = load_icon(logo_path, 32)
    if logo:
        img.paste(logo, (16, 8), logo)
        draw_text(56, 14, "SignMaker", font_h1, C["text_primary"])
        draw_text(138, 16, "Slicer", font_h2, C["accent_secondary"])
    else:
        draw_gradient_rect(16, 12, 4, 24)
        draw_text(28, 14, "SignMaker", font_h1, C["text_primary"])
        draw_text(110, 16, "Slicer", font_h2, C["accent_secondary"])

    # 中央导航标签页 - 预览激活
    nav_items = [("首页", False), ("项目", False), ("预览", True)]
    nav_start_x = (WIDTH - 240) // 2
    for i, (name, active) in enumerate(nav_items):
        nx = nav_start_x + i * 80
        if active:
            draw_gradient_rect(nx, 8, 64, 32)
            draw_text(nx + 20, 14, name, font_h2, (255, 255, 255))
        else:
            draw_text(nx + 20, 14, name, font_h2, C["text_muted"])

    # 右侧按钮
    right_tools = ["⚙", "?", "☰"]
    tool_x = WIDTH - 140
    for icon in right_tools:
        draw_rounded_rect(tool_x, 10, 32, 28, 6, fill=C["bg_card"])
        draw_text(tool_x + 10, 14, icon, font_icon, C["text_secondary"])
        tool_x += 40

    # ============================================
    # 中央预览区域 - 3D视图
    # ============================================
    canvas_x = 0
    canvas_w = WIDTH - SIDEBAR_RIGHT_W - LAYER_SLIDER_W
    canvas_y = content_y
    canvas_h = content_h

    # 画布背景
    draw_rounded_rect(canvas_x + 8, canvas_y + 8, canvas_w - 16, canvas_h - 16, 12, fill=C["bg_primary"])

    # 顶部工具栏
    toolbar_y = canvas_y + 16
    draw_rounded_rect(canvas_x + 20, toolbar_y, canvas_w - 40, 44, 8, fill=C["bg_card"])

    # 显示选项（路径类型过滤）
    display_options = [("外壁", True, C["path_outer"]), ("内壁", True, C["path_inner"]),
                       ("填充", False, C["path_fill"]), ("空走", False, C["path_travel"])]
    ox = canvas_x + 32
    for name, enabled, color in display_options:
        # 复选框
        box_x = ox
        box_y = toolbar_y + 14
        if enabled:
            draw.rounded_rectangle([box_x, box_y, box_x + 14, box_y + 14], radius=3, fill=color)
            draw_text(box_x + 3, box_y - 1, "✓", font_small, (255, 255, 255))
        else:
            draw.rounded_rectangle([box_x, box_y, box_x + 14, box_y + 14], radius=3,
                                   fill=C["bg_elevated"], outline=C["border_default"])
        draw_text(box_x + 18, box_y, name, font_body, C["text_primary"] if enabled else C["text_muted"])
        ox += 65

    # 3D画布内容区
    inner_canvas_y = toolbar_y + 52
    inner_canvas_h = canvas_h - 150  # 给底部进度条留空间
    draw_rounded_rect(canvas_x + 20, inner_canvas_y, canvas_w - 40, inner_canvas_h, 8, fill=C["bg_base"])

    # ---- 左上角坐标系 ----
    axis_box_x = canvas_x + 28
    axis_box_y = inner_canvas_y + 8
    draw_rounded_rect(axis_box_x, axis_box_y, 60, 60, 6, fill=C["bg_card"])

    # 坐标轴原点（在盒子左侧中间位置）
    axis_origin_x = axis_box_x + 18
    axis_origin_y = axis_box_y + 40
    axis_len = 25

    # Z轴 (蓝色, 向上 - 垂直)
    draw.line([(axis_origin_x, axis_origin_y), (axis_origin_x, axis_origin_y - 30)], fill=(0, 100, 255), width=2)
    draw_text(axis_origin_x - 4, axis_origin_y - 42, "Z", font_small, (0, 100, 255))

    # Y轴 (绿色, 向右上)
    draw.line([(axis_origin_x, axis_origin_y), (axis_origin_x + 22, axis_origin_y - 14)], fill=(0, 180, 0), width=2)
    draw_text(axis_origin_x + 26, axis_origin_y - 22, "Y", font_small, (0, 180, 0))

    # X轴 (红色, 向右下)
    draw.line([(axis_origin_x, axis_origin_y), (axis_origin_x + 25, axis_origin_y + 12)], fill=(220, 0, 0), width=2)
    draw_text(axis_origin_x + 28, axis_origin_y + 8, "X", font_small, (220, 0, 0))

    # ---- 左下角观察方位按钮 ----
    view_btn_y = inner_canvas_y + inner_canvas_h - 48
    view_btn_x = canvas_x + 28
    view_buttons = [("正", False), ("俯", False), ("侧", False), ("透", True)]
    for name, active in view_buttons:
        btn_w = 32
        if active:
            draw_rounded_rect(view_btn_x, view_btn_y, btn_w, 32, 6, fill=C["accent_primary"])
            draw_text(view_btn_x + 10, view_btn_y + 8, name, font_body, (255, 255, 255))
        else:
            draw_rounded_rect(view_btn_x, view_btn_y, btn_w, 32, 6, fill=C["bg_card"])
            draw_text(view_btn_x + 10, view_btn_y + 8, name, font_body, C["text_secondary"])
        view_btn_x += btn_w + 6

    # ---- 右上角操作提示 ----
    hint_text = "拖拽旋转 | 滚轮缩放"
    hint_x = canvas_x + canvas_w - 180
    hint_y = inner_canvas_y + 16
    draw_rounded_rect(hint_x, hint_y, 150, 24, 6, fill=C["bg_card"])
    draw_text(hint_x + 12, hint_y + 5, hint_text, font_small, C["text_muted"])

    # 3D网格地面 (透视效果)
    grid_center_x = canvas_x + canvas_w // 2
    grid_center_y = inner_canvas_y + inner_canvas_h - 80
    grid_color = C["grid_3d"]
    vanish_y = inner_canvas_y + 30
    grid_base_width = 320
    grid_depth_lines = 14

    # 横向网格线 (透视)
    grid_step_y = (grid_center_y - vanish_y - 60) / grid_depth_lines
    for i in range(grid_depth_lines + 1):
        y_pos = int(grid_center_y - i * grid_step_y)
        shrink = 1 - (i / grid_depth_lines) * 0.6
        half_width = int(grid_base_width * shrink)
        if y_pos > vanish_y:
            alpha = max(0.3, 1 - i * 0.05)
            line_color = tuple(int(c * alpha) for c in grid_color)
            draw.line([(grid_center_x - half_width, y_pos),
                       (grid_center_x + half_width, y_pos)], fill=line_color, width=1)

    # 纵向网格线 (透视)
    grid_lines_x = 17
    for i in range(grid_lines_x):
        ratio = (i / (grid_lines_x - 1)) - 0.5
        bottom_x = grid_center_x + int(ratio * 2 * grid_base_width)
        top_x = grid_center_x + int(ratio * 2 * grid_base_width * 0.4)
        top_y = int(grid_center_y - grid_depth_lines * grid_step_y)
        draw.line([(bottom_x, grid_center_y), (top_x, top_y)], fill=grid_color, width=1)

    # 绘制3D字壳模型 - "发"字
    cx = grid_center_x
    cy = inner_canvas_y + inner_canvas_h // 2 - 20

    # 3D立体效果
    shadow_color = C["layer_base"]
    for i in range(10, 0, -1):
        draw_text(cx - 60 + i, cy - 60 + i, "发", font_large, shadow_color)

    # 描边
    stroke_color = C["accent_primary"]
    for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw_text(cx - 60 + offset[0], cy - 60 + offset[1], "发", font_large, stroke_color)

    # 顶层
    draw_text(cx - 60, cy - 60, "发", font_large, C["layer_top"])

    # ============================================
    # 底部进度条 - 简洁设计
    # ============================================
    ctrl_y = inner_canvas_y + inner_canvas_h + 8

    # 坐标信息栏
    info_w = 360
    info_x = canvas_x + (canvas_w - info_w) // 2
    draw_rounded_rect(info_x, ctrl_y, info_w, 28, 6, fill=C["bg_card"])
    draw_text(info_x + 16, ctrl_y + 7, "X:", font_small, C["text_muted"])
    draw_text(info_x + 30, ctrl_y + 7, "342.652", font_mono_small, C["text_primary"])
    draw_text(info_x + 100, ctrl_y + 7, "Y:", font_small, C["text_muted"])
    draw_text(info_x + 114, ctrl_y + 7, "523.336", font_mono_small, C["text_primary"])
    draw_text(info_x + 184, ctrl_y + 7, "Z:", font_small, C["text_muted"])
    draw_text(info_x + 198, ctrl_y + 7, "26.700", font_mono_small, C["text_primary"])
    draw_text(info_x + 260, ctrl_y + 7, "Speed:", font_small, C["text_muted"])
    draw_text(info_x + 305, ctrl_y + 7, "98", font_mono_small, C["text_primary"])

    # 进度条轨道
    track_y = ctrl_y + 36
    track_x = canvas_x + 32
    track_w = canvas_w - 64
    track_h = 10

    # 轨道背景 (灰色)
    draw.rounded_rectangle([track_x, track_y, track_x + track_w, track_y + track_h],
                           radius=5, fill=C["bg_elevated"])

    # 进度 (绿色)
    progress_ratio = 0.35
    progress_w = int(track_w * progress_ratio)
    draw.rounded_rectangle([track_x, track_y, track_x + progress_w, track_y + track_h],
                           radius=5, fill=C["success"])

    # 滑块手柄
    handle_x = track_x + progress_w
    handle_r = 7
    draw.ellipse([handle_x - handle_r, track_y + track_h // 2 - handle_r,
                  handle_x + handle_r, track_y + track_h // 2 + handle_r],
                 fill=C["accent_secondary"], outline=C["text_primary"], width=2)

    # 当前行号显示
    draw_rounded_rect(handle_x - 20, track_y + track_h + 4, 40, 18, 4, fill=C["accent_secondary"])
    draw_text(handle_x - 12, track_y + track_h + 6, "298", font_mono_small, (255, 255, 255))

    # ============================================
    # 右侧层高滑块 - 简洁设计
    # ============================================
    slider_x = canvas_x + canvas_w
    slider_y = content_y + 60
    slider_h = content_h - 120

    # 滑块背景
    draw.rectangle([slider_x, content_y, slider_x + LAYER_SLIDER_W, content_y + content_h], fill=C["bg_primary"])

    # 层高刻度条
    track_x = slider_x + 18
    track_w = 12
    draw.rounded_rectangle([track_x, slider_y, track_x + track_w, slider_y + slider_h],
                           radius=6, fill=C["bg_elevated"])

    # 彩色进度条 (青色渐变)
    current_layer_ratio = 0.70
    progress_h = int(slider_h * current_layer_ratio)
    progress_y = slider_y + slider_h - progress_h
    draw.rounded_rectangle([track_x + 1, progress_y, track_x + track_w - 1, slider_y + slider_h],
                           radius=5, fill=C["accent_secondary"])

    # 当前层指示器 (三角形手柄 - 在右侧朝向进度条)
    handle_y = progress_y
    tri_x = track_x + track_w + 4
    draw.polygon([(tri_x + 8, handle_y - 5),
                  (tri_x, handle_y),
                  (tri_x + 8, handle_y + 5)],
                 fill=C["text_primary"])

    # 顶部层数显示
    draw_text(slider_x + 12, slider_y - 30, "89", font_mono, C["text_primary"])
    draw_text(slider_x + 5, slider_y - 16, "26.70", font_mono_small, C["accent_secondary"])

    # 底部层数显示
    draw_text(slider_x + 18, slider_y + slider_h + 8, "1", font_mono, C["text_primary"])
    draw_text(slider_x + 8, slider_y + slider_h + 22, "0.30", font_mono_small, C["text_muted"])

    # 右下角挤出机编号
    ext_y = slider_y + slider_h + 50
    draw_text(slider_x + 8, ext_y, "01", ImageFont.truetype("msyh.ttc", 28) if os.path.exists("C:\\Windows\\Fonts\\msyh.ttc") else font_h1, C["warning"])

    # ============================================
    # 右侧信息面板
    # ============================================
    right_x = WIDTH - SIDEBAR_RIGHT_W
    draw_rounded_rect(right_x + 8, content_y + 8, SIDEBAR_RIGHT_W - 16, content_h - 80, 12, fill=C["bg_secondary"])

    # 面板标题
    draw_text(right_x + 24, content_y + 24, "切片统计", font_h1, C["text_primary"])

    # ============================================
    # 路径类型统计卡片
    # ============================================
    card_y = content_y + 56
    draw_rounded_rect(right_x + 16, card_y, SIDEBAR_RIGHT_W - 32, 180, 8, fill=C["bg_card"])

    # 卡片标题
    tri_x = right_x + 28
    tri_y = card_y + 14
    draw.polygon([(tri_x, tri_y), (tri_x + 10, tri_y), (tri_x + 5, tri_y + 6)], fill=C["accent_primary"])
    draw_text(right_x + 48, card_y + 10, "路径类型", font_h2, C["text_primary"])

    # 表头
    header_y = card_y + 38
    draw_text(right_x + 28, header_y, "类型", font_small, C["text_muted"])
    draw_text(right_x + 130, header_y, "时间", font_small, C["text_muted"])
    draw_text(right_x + 190, header_y, "长度", font_small, C["text_muted"])
    draw_text(right_x + 250, header_y, "占比", font_small, C["text_muted"])

    # 路径类型数据
    path_types = [
        ("外壁", C["path_outer"], "1h36m", "31.45m", "68.3%"),
        ("内壁", C["path_inner"], "15m32s", "5.22m", "11.1%"),
        ("填充", C["path_fill"], "6m38s", "1.94m", "4.7%"),
        ("顶面", C["warning"], "8m29s", "1.12m", "6.1%"),
        ("空走", C["path_travel"], "13m38s", "-", "9.7%"),
    ]

    row_y = header_y + 18
    for name, color, time, length, pct in path_types:
        # 颜色指示器
        draw.ellipse([right_x + 28, row_y + 3, right_x + 38, row_y + 13], fill=color)
        draw_text(right_x + 44, row_y, name, font_body, C["text_primary"])
        draw_text(right_x + 125, row_y, time, font_mono_small, C["text_secondary"])
        draw_text(right_x + 190, row_y, length, font_mono_small, C["text_secondary"])
        draw_text(right_x + 250, row_y, pct, font_mono_small, C["text_secondary"])
        row_y += 22

    # ============================================
    # 总估算卡片
    # ============================================
    est_card_y = card_y + 190
    draw_rounded_rect(right_x + 16, est_card_y, SIDEBAR_RIGHT_W - 32, 160, 8, fill=C["bg_card"])

    tri_x = right_x + 28
    tri_y = est_card_y + 14
    draw.polygon([(tri_x, tri_y), (tri_x + 10, tri_y), (tri_x + 5, tri_y + 6)], fill=C["accent_primary"])
    draw_text(right_x + 48, est_card_y + 10, "打印估算", font_h2, C["text_primary"])

    estimations = [
        ("总层数", "100 层", C["accent_primary"]),
        ("打印时间", "2h 20min", C["accent_secondary"]),
        ("总耗材", "39.74 m / 118.51 g", C["success"]),
        ("预估成本", "¥ 2.37", C["warning"]),
    ]

    est_y = est_card_y + 40
    for label, value, color in estimations:
        draw_text(right_x + 28, est_y, label, font_body, C["text_muted"])
        draw_text(right_x + 140, est_y, value, font_mono, color)
        est_y += 28

    # ============================================
    # 挤出机用量卡片
    # ============================================
    ext_card_y = est_card_y + 170
    draw_rounded_rect(right_x + 16, ext_card_y, SIDEBAR_RIGHT_W - 32, 140, 8, fill=C["bg_card"])

    tri_x = right_x + 28
    tri_y = ext_card_y + 14
    draw.polygon([(tri_x, tri_y), (tri_x + 10, tri_y), (tri_x + 5, tri_y + 6)], fill=C["accent_primary"])
    draw_text(right_x + 48, ext_card_y + 10, "挤出机用量", font_h2, C["text_primary"])

    extruders = [
        ("挤出机 1 (遮光)", "85.2 m", C["extruder_1"], 0.7),
        ("挤出机 2 (透光)", "25.6 m", C["extruder_2"], 0.2),
        ("挤出机 3 (透光)", "15.0 m", C["extruder_3"], 0.1),
    ]

    ext_y = ext_card_y + 40
    bar_w = SIDEBAR_RIGHT_W - 64
    for name, usage, color, ratio in extruders:
        draw_text(right_x + 28, ext_y, name, font_small, C["text_muted"])
        draw_text(right_x + 200, ext_y, usage, font_mono_small, color)

        # 进度条
        bar_y = ext_y + 18
        draw.rounded_rectangle([right_x + 28, bar_y, right_x + 28 + bar_w, bar_y + 6],
                               radius=3, fill=C["bg_elevated"])
        draw.rounded_rectangle([right_x + 28, bar_y, right_x + 28 + int(bar_w * ratio), bar_y + 6],
                               radius=3, fill=color)
        ext_y += 32

    # ============================================
    # 底部按钮区域
    # ============================================
    btn_area_y = content_y + content_h - 60

    # 发送到打印机按钮
    btn_w = SIDEBAR_RIGHT_W - 32
    draw_gradient_rect(right_x + 16, btn_area_y, btn_w, 44)
    draw.rounded_rectangle([right_x + 16, btn_area_y, right_x + 16 + btn_w, btn_area_y + 44],
                           radius=10, outline=None)

    btn_text = "发送到打印机"
    bbox = draw.textbbox((0, 0), btn_text, font=font_h2)
    text_w = bbox[2] - bbox[0]
    draw_text(right_x + 16 + (btn_w - text_w) // 2, btn_area_y + 14, btn_text, font_h2, (255, 255, 255))

    # ============================================
    # 底部状态栏
    # ============================================
    draw_rounded_rect(0, HEIGHT - FOOTER_H, WIDTH, FOOTER_H, 0, fill=C["bg_primary"])
    draw_text(20, HEIGHT - FOOTER_H + 10, "● 切片完成", font_body, C["success"])
    draw_text(140, HEIGHT - FOOTER_H + 10, "文件: 发光字-发.gcode", font_small, C["text_muted"])
    draw_text(340, HEIGHT - FOOTER_H + 10, "机器: AD-F4 (800×1200mm)", font_small, C["text_muted"])
    draw_text(WIDTH - 150, HEIGHT - FOOTER_H + 10, "SignMaker Slicer v1.0", font_small, C["text_muted"])

    return img


# 生成效果图
if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(output_dir, exist_ok=True)

    # 预览模式
    preview_img = generate_preview_mode()
    preview_path = os.path.join(output_dir, "UI_Slice_Preview.png")
    preview_img.save(preview_path, "PNG", quality=95)
    print(f"Saved: {preview_path}")

    # 也保存到根目录
    root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Slice_Preview.png")
    preview_img.save(root_path, "PNG", quality=95)
    print(f"Saved: {root_path}")

    print("Done!")
