"""
SignMaker Slicer - 项目模式 2D视图 (更新版)
包含完整参数面板分组
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 配色
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
    "border_default": "#334155",
    "border_focus": "#3B82F6",
    "extruder_1": "#3B82F6",
    "extruder_2": "#EC4899",
    "extruder_3": "#F59E0B",
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) for k, v in COLORS.items()}

WIDTH = 1600
HEIGHT = 1000

img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_base"])
draw = ImageDraw.Draw(img)

try:
    font_h1 = ImageFont.truetype("msyh.ttc", 16)
    font_h2 = ImageFont.truetype("msyh.ttc", 13)
    font_body = ImageFont.truetype("msyh.ttc", 11)
    font_small = ImageFont.truetype("msyh.ttc", 9)
    font_mono = ImageFont.truetype("consola.ttf", 11)
    font_icon = ImageFont.truetype("seguisym.ttf", 14)
    font_large = ImageFont.truetype("msyh.ttc", 80)
except:
    font_h1 = font_h2 = font_body = font_small = font_mono = font_icon = font_large = ImageFont.load_default()

def draw_rounded_rect(x, y, w, h, r, fill=None, outline=None):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline)

def draw_text(x, y, text, font=None, fill=None):
    draw.text((x, y), text, font=font or font_body, fill=fill or C["text_secondary"])

def draw_gradient_rect(x, y, w, h):
    for i in range(w):
        ratio = i / w
        color = tuple(int(C["accent_primary"][j] + (C["accent_secondary"][j] - C["accent_primary"][j]) * ratio) for j in range(3))
        draw.line([(x + i, y), (x + i, y + h)], fill=color)

def draw_input(x, y, w, value, unit=""):
    draw_rounded_rect(x, y, w, 26, 5, fill=C["bg_primary"], outline=C["border_default"])
    draw_text(x + 8, y + 5, str(value), font_mono, C["text_primary"])
    if unit:
        draw_text(x + w + 6, y + 6, unit, font_small, C["text_muted"])

def draw_select(x, y, w, value):
    draw_rounded_rect(x, y, w, 26, 5, fill=C["bg_primary"], outline=C["border_default"])
    draw_text(x + 8, y + 5, value, font_body, C["text_primary"])
    draw_text(x + w - 18, y + 5, "▼", font_small, C["text_muted"])

# 布局
HEADER_H = 48
SIDEBAR_LEFT_W = 220
SIDEBAR_RIGHT_W = 360
FOOTER_H = 36

content_y = HEADER_H
content_h = HEIGHT - HEADER_H - FOOTER_H

# ============================================
# 顶部导航栏
# ============================================
draw_rounded_rect(0, 0, WIDTH, HEADER_H, 0, fill=C["bg_primary"])

# Logo
draw_gradient_rect(16, 12, 4, 24)
draw_text(28, 14, "SignMaker", font_h1, C["text_primary"])
draw_text(110, 16, "Slicer", font_h2, C["accent_secondary"])

# 标签页
tabs = [("项目", True), ("切片", False), ("预览", False)]
tabs_x = WIDTH // 2 - 150
for i, (name, active) in enumerate(tabs):
    tx = tabs_x + i * 100
    if active:
        draw_rounded_rect(tx, 8, 90, 32, 8, fill=C["bg_card"])
        draw_text(tx + 30, 14, name, font_h2, C["text_primary"])
    else:
        draw_text(tx + 30, 14, name, font_h2, C["text_muted"])

# 右侧按钮
right_tools = ["⚙", "?", "☰"]
tool_x = WIDTH - 140
for icon in right_tools:
    draw_rounded_rect(tool_x, 10, 32, 28, 6, fill=C["bg_card"])
    draw_text(tool_x + 10, 14, icon, font_icon, C["text_secondary"])
    tool_x += 40

# ============================================
# 左侧面板 - 图形管理
# ============================================
draw_rounded_rect(8, content_y + 8, SIDEBAR_LEFT_W - 16, content_h - 16, 12, fill=C["bg_secondary"])

# 文件操作工具栏
toolbar_y = content_y + 16
draw_rounded_rect(16, toolbar_y, SIDEBAR_LEFT_W - 32, 36, 8, fill=C["bg_card"])

file_icons = ["📂", "💾", "📥", "📤"]
ftx = 24
for icon in file_icons:
    draw_rounded_rect(ftx, toolbar_y + 4, 40, 28, 6, fill=C["bg_elevated"])
    draw_text(ftx + 12, toolbar_y + 10, icon, font_icon, C["text_secondary"])
    ftx += 46

# 图形列表标题
draw_text(20, toolbar_y + 50, "图形列表", font_h2, C["text_primary"])

# 图形项目
shapes = [
    ("发光字-发", True, C["extruder_1"]),
    ("发光字-光", False, C["extruder_2"]),
    ("发光字-字", False, C["extruder_1"]),
]
shape_y = toolbar_y + 80
for name, selected, color in shapes:
    if selected:
        draw_rounded_rect(16, shape_y, SIDEBAR_LEFT_W - 32, 44, 8, fill=C["bg_hover"], outline=C["border_focus"])
    else:
        draw_rounded_rect(16, shape_y, SIDEBAR_LEFT_W - 32, 44, 8, fill=C["bg_card"])
    draw_rounded_rect(24, shape_y + 12, 4, 20, 2, fill=color)
    draw_text(36, shape_y + 14, name, font_body, C["text_primary"] if selected else C["text_secondary"])
    draw_text(SIDEBAR_LEFT_W - 50, shape_y + 14, "👁", font_small, C["text_muted"])
    shape_y += 52

# 添加按钮
draw_rounded_rect(16, shape_y + 10, SIDEBAR_LEFT_W - 32, 36, 8, outline=C["border_default"])
draw_text(70, shape_y + 18, "+ 导入图形", font_body, C["text_muted"])

# ============================================
# 中央画布
# ============================================
canvas_x = SIDEBAR_LEFT_W
canvas_w = WIDTH - SIDEBAR_LEFT_W - SIDEBAR_RIGHT_W
canvas_y = content_y
canvas_h = content_h

draw_rounded_rect(canvas_x + 8, canvas_y + 8, canvas_w - 16, canvas_h - 16, 12, fill=C["bg_primary"])

# 顶部工具栏
canvas_toolbar_y = canvas_y + 16
draw_rounded_rect(canvas_x + 20, canvas_toolbar_y, canvas_w - 40, 40, 8, fill=C["bg_card"])

# 编辑工具
edit_tools = ["选择", "移动", "旋转", "镜像", "缩放"]
etx = canvas_x + 32
for tool in edit_tools:
    active = tool == "选择"
    if active:
        draw_rounded_rect(etx, canvas_toolbar_y + 6, 50, 28, 6, fill=C["accent_primary"])
        draw_text(etx + 10, canvas_toolbar_y + 12, tool, font_body, (255,255,255))
    else:
        draw_text(etx + 10, canvas_toolbar_y + 12, tool, font_body, C["text_secondary"])
    etx += 60

# 2D/3D切换
view_x = canvas_x + canvas_w - 180
draw_rounded_rect(view_x, canvas_toolbar_y + 6, 100, 28, 6, fill=C["bg_elevated"])
draw_rounded_rect(view_x + 5, canvas_toolbar_y + 8, 40, 24, 4, fill=C["accent_primary"])
draw_text(view_x + 15, canvas_toolbar_y + 12, "2D", font_body, (255,255,255))
draw.line([(view_x + 50, canvas_toolbar_y + 12), (view_x + 50, canvas_toolbar_y + 28)], fill=C["border_default"])
draw_text(view_x + 65, canvas_toolbar_y + 12, "3D", font_body, C["text_muted"])

# 画布区域
inner_canvas_y = canvas_toolbar_y + 56
inner_canvas_h = canvas_h - 120

draw_rounded_rect(canvas_x + 20, inner_canvas_y, canvas_w - 40, inner_canvas_h, 8, fill=C["bg_base"])

# 网格
grid_color = (20, 28, 38)
for gx in range(canvas_x + 20, canvas_x + canvas_w - 20, 30):
    draw.line([(gx, inner_canvas_y), (gx, inner_canvas_y + inner_canvas_h)], fill=grid_color)
for gy in range(inner_canvas_y, inner_canvas_y + inner_canvas_h, 30):
    draw.line([(canvas_x + 20, gy), (canvas_x + canvas_w - 20, gy)], fill=grid_color)

# 机器边界
margin = 40
draw_rounded_rect(canvas_x + 20 + margin, inner_canvas_y + margin,
                  canvas_w - 40 - margin*2, inner_canvas_h - margin*2, 4,
                  outline=C["border_default"])

# 字形
char_x = canvas_x + canvas_w // 2 - 60
char_y = inner_canvas_y + inner_canvas_h // 2 - 80
draw_text(char_x, char_y, "发", font_large, C["accent_primary"])

# 起点
draw.ellipse([char_x - 8, char_y - 8, char_x + 8, char_y + 8], fill=C["success"])

# 底部信息
info_y = inner_canvas_y + inner_canvas_h + 8
draw_rounded_rect(canvas_x + 20, info_y, canvas_w - 40, 36, 8, fill=C["bg_card"])
draw_text(canvas_x + 36, info_y + 10, "尺寸: 120 × 150 mm", font_small, C["text_muted"])
draw_text(canvas_x + 200, info_y + 10, "缩放: 100%", font_small, C["text_muted"])
draw_text(canvas_x + 340, info_y + 10, "鼠标: X 125.5  Y 89.2", font_mono, C["text_muted"])

# 缩放控制
zoom_x = canvas_x + canvas_w - 160
draw_rounded_rect(zoom_x, info_y + 6, 120, 24, 6, fill=C["bg_elevated"])
draw_text(zoom_x + 10, info_y + 10, "−", font_h2, C["text_muted"])
draw_rounded_rect(zoom_x + 35, info_y + 8, 50, 20, 4, fill=C["bg_card"])
draw_text(zoom_x + 95, info_y + 10, "+", font_h2, C["text_muted"])

# ============================================
# 右侧参数面板 - 完整版
# ============================================
right_x = WIDTH - SIDEBAR_RIGHT_W
draw_rounded_rect(right_x + 8, content_y + 8, SIDEBAR_RIGHT_W - 16, content_h - 16, 12, fill=C["bg_secondary"])

draw_text(right_x + 20, content_y + 20, "参数设置", font_h1, C["text_primary"])

# 快速参数
card_y = content_y + 50
draw_rounded_rect(right_x + 16, card_y, SIDEBAR_RIGHT_W - 32, 70, 10, fill=C["bg_card"])

quick_params = [("字壳高度", "30", "mm"), ("壁厚", "1.2", "mm"), ("层高", "0.3", "mm")]
qp_x = right_x + 26
for label, value, unit in quick_params:
    draw_text(qp_x, card_y + 10, label, font_small, C["text_muted"])
    draw_rounded_rect(qp_x, card_y + 28, 85, 28, 6, fill=C["bg_elevated"])
    draw_text(qp_x + 10, card_y + 34, value, font_mono, C["text_primary"])
    draw_text(qp_x + 60, card_y + 36, unit, font_small, C["text_muted"])
    qp_x += 105

# 参数分组 - 可折叠
sections = [
    ("字壳工艺", True, [
        ("字边类型", "直边", "select"),
        ("斜边宽度", "5", "mm"),
        ("底板厚度", "10", "mm"),
    ]),
    ("换色层设置", False, []),
    ("台阶/V槽", False, []),
    ("防翘裙边", False, []),
    ("连襟字", False, []),
    ("包边勾边", False, []),
    ("面板打印", False, []),
    ("生成底板", False, []),
    ("文件输出", False, []),
    ("机械参数", False, []),
]

section_y = card_y + 85
for section_name, expanded, params in sections:
    # 分组标题
    draw_rounded_rect(right_x + 16, section_y, SIDEBAR_RIGHT_W - 32, 36, 8, fill=C["bg_card"])
    indicator = "▼" if expanded else "▶"
    draw_text(right_x + 28, section_y + 10, indicator, font_small, C["accent_primary"] if expanded else C["text_muted"])
    draw_text(right_x + 46, section_y + 10, section_name, font_h2, C["text_primary"])
    section_y += 42

    if expanded and params:
        draw_rounded_rect(right_x + 16, section_y, SIDEBAR_RIGHT_W - 32, len(params) * 36 + 12, 8, fill=C["bg_elevated"])
        param_y = section_y + 8
        for label, value, unit in params:
            draw_text(right_x + 28, param_y + 4, label, font_body, C["text_secondary"])
            if unit == "select":
                draw_select(right_x + 160, param_y, 120, value)
            else:
                draw_input(right_x + 160, param_y, 80, value, unit)
            param_y += 34
        section_y += len(params) * 36 + 18

    section_y += 4

# ============================================
# 底部统计和按钮
# ============================================
footer_y = content_y + content_h - 110

# 统计
draw_rounded_rect(right_x + 16, footer_y, SIDEBAR_RIGHT_W - 32, 45, 8, fill=C["bg_card"])
draw_text(right_x + 28, footer_y + 6, "预计打印时间", font_small, C["text_muted"])
draw_text(right_x + 28, footer_y + 22, "2h 15min", font_h2, C["accent_secondary"])
draw_text(right_x + 180, footer_y + 6, "耗材用量", font_small, C["text_muted"])
draw_text(right_x + 180, footer_y + 22, "125.8m", font_h2, C["accent_secondary"])

# 主按钮
btn_y = footer_y + 55
draw_gradient_rect(right_x + 16, btn_y, SIDEBAR_RIGHT_W - 32, 40)
draw_rounded_rect(right_x + 16, btn_y, SIDEBAR_RIGHT_W - 32, 40, 10, outline=None)
draw_text(right_x + 110, btn_y + 10, "生成 G-Code", font_h2, (255,255,255))

# ============================================
# 底部状态栏
# ============================================
draw_rounded_rect(0, HEIGHT - FOOTER_H, WIDTH, FOOTER_H, 0, fill=C["bg_primary"])
draw_text(20, HEIGHT - FOOTER_H + 10, "● 就绪", font_body, C["success"])
draw_text(100, HEIGHT - FOOTER_H + 10, "图形: 3个", font_small, C["text_muted"])
draw_text(200, HEIGHT - FOOTER_H + 10, "机器: ZC-800 (800×800mm)", font_small, C["text_muted"])
draw_text(WIDTH - 150, HEIGHT - FOOTER_H + 10, "SignMaker Slicer v1.0", font_small, C["text_muted"])

# ============================================
# 保存
# ============================================
output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(output_dir, exist_ok=True)

# 覆盖原来的UI_Modern.png
output_path = os.path.join(output_dir, "UI_Modern.png")
img.save(output_path, "PNG", quality=95)
print(f"Saved: {output_path}")

root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Modern.png")
img.save(root_path, "PNG", quality=95)
print(f"Saved: {root_path}")
