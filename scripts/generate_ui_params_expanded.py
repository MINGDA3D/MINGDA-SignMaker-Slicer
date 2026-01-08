"""
SignMaker Slicer - 参数面板展开详细视图
展示所有参数分组展开后的完整效果
"""

from PIL import Image, ImageDraw, ImageFont
import os

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

# 创建一个更高的画布来展示完整参数面板
WIDTH = 420
HEIGHT = 1800

img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_secondary"])
draw = ImageDraw.Draw(img)

# 字体
try:
    font_h1 = ImageFont.truetype("msyh.ttc", 16)
    font_h2 = ImageFont.truetype("msyh.ttc", 13)
    font_body = ImageFont.truetype("msyh.ttc", 11)
    font_small = ImageFont.truetype("msyh.ttc", 9)
    font_mono = ImageFont.truetype("consola.ttf", 11)
except:
    font_h1 = font_h2 = font_body = font_small = font_mono = ImageFont.load_default()

def draw_rounded_rect(x, y, w, h, r, fill=None, outline=None):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline)

def draw_text(x, y, text, font=None, fill=None):
    draw.text((x, y), text, font=font or font_body, fill=fill or C["text_secondary"])

def draw_input(x, y, w, value, highlight=False):
    bg = C["accent_primary"] if highlight else C["bg_card"]
    text_color = (255,255,255) if highlight else C["text_primary"]
    draw_rounded_rect(x, y, w, 28, 6, fill=bg, outline=C["border_default"])
    draw_text(x + 10, y + 6, str(value), font_mono, text_color)

def draw_select(x, y, w, value):
    draw_rounded_rect(x, y, w, 28, 6, fill=C["bg_card"], outline=C["border_default"])
    draw_text(x + 10, y + 6, value, font_body, C["text_primary"])
    draw_text(x + w - 20, y + 6, "▼", font_small, C["text_muted"])

def draw_checkbox(x, y, label, checked=False):
    box_color = C["accent_primary"] if checked else C["border_default"]
    draw_rounded_rect(x, y, 16, 16, 3,
                      fill=C["accent_primary"] if checked else C["bg_elevated"],
                      outline=box_color)
    if checked:
        draw_text(x + 3, y - 1, "✓", font_small, (255,255,255))
    draw_text(x + 24, y, label, font_body, C["text_primary"] if checked else C["text_secondary"])

def draw_section_header(y, title, expanded=True):
    draw_rounded_rect(16, y, WIDTH - 32, 40, 8, fill=C["bg_card"])
    indicator = "▼" if expanded else "▶"
    draw_text(28, y + 12, indicator, font_small, C["accent_primary"] if expanded else C["text_muted"])
    draw_text(48, y + 12, title, font_h2, C["text_primary"])
    return y + 48

# ============================================
# 面板标题
# ============================================
draw_text(20, 20, "参数设置", font_h1, C["text_primary"])

# 快速设置卡片
card_y = 55
draw_rounded_rect(16, card_y, WIDTH - 32, 80, 10, fill=C["bg_card"])

quick_params = [("字壳高度", "30", "mm"), ("壁厚", "1.2", "mm"), ("层高", "0.3", "mm")]
qp_x = 28
for label, value, unit in quick_params:
    draw_text(qp_x, card_y + 12, label, font_small, C["text_muted"])
    draw_rounded_rect(qp_x, card_y + 30, 100, 32, 6, fill=C["bg_elevated"])
    draw_text(qp_x + 10, card_y + 38, value, font_mono, C["text_primary"])
    draw_text(qp_x + 70, card_y + 40, unit, font_small, C["text_muted"])
    qp_x += 125

y = card_y + 100

# ============================================
# 1. 字壳工艺
# ============================================
y = draw_section_header(y, "字壳工艺", True)

draw_rounded_rect(16, y, WIDTH - 32, 320, 8, fill=C["bg_elevated"])
py = y + 16

# 打印模式
draw_text(28, py, "打印模式", font_body, C["text_secondary"])
draw_rounded_rect(150, py - 2, 70, 28, 6, fill=C["bg_card"], outline=C["border_focus"])
draw_text(162, py + 4, "正常", font_body, C["text_primary"])
draw_rounded_rect(230, py - 2, 70, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(242, py + 4, "镜像", font_body, C["text_muted"])
py += 40

# 字边类型
draw_text(28, py, "字边类型", font_body, C["text_secondary"])
draw_select(150, py - 2, 150, "斜边")
py += 40

# 基础参数
params = [
    ("字壳高度", "30", "mm"),
    ("斜边宽度", "5", "mm"),
    ("面板厚度", "3", "mm"),
    ("底板厚度", "10", "mm"),
    ("层高", "0.3", "mm"),
]
for label, value, unit in params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(150, py - 2, 100, value)
    draw_text(260, py + 4, unit, font_small, C["text_muted"])
    py += 36

y = y + 330

# ============================================
# 2. 壁厚设置
# ============================================
y = draw_section_header(y, "壁厚设置", True)

draw_rounded_rect(16, y, WIDTH - 32, 180, 8, fill=C["bg_elevated"])
py = y + 16

wall_params = [
    ("壁厚", "1.2", "mm"),
    ("壁厚补偿", "0", "mm"),
    ("走线次数", "1", "次"),
    ("走线偏移", "0.8", "mm"),
]
for label, value, unit in wall_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(150, py - 2, 100, value)
    draw_text(260, py + 4, unit, font_small, C["text_muted"])
    py += 36

y = y + 190

# ============================================
# 3. 换色层设置
# ============================================
y = draw_section_header(y, "换色层设置", True)

draw_rounded_rect(16, y, WIDTH - 32, 280, 8, fill=C["bg_elevated"])
py = y + 16

# 换色层可视化
layers_data = [
    ("第1层", "0-10", C["extruder_1"], "1号"),
    ("第2层", "10-15", C["extruder_2"], "2号"),
    ("第3层", "15-20", C["extruder_3"], "3号"),
    ("第4层", "20-30", C["extruder_1"], "1号"),
]

draw_text(28, py, "换色层配置", font_body, C["text_primary"])
py += 28

for name, height_range, color, extruder in layers_data:
    # 颜色指示器
    draw_rounded_rect(28, py, 24, 24, 4, fill=color)
    draw_text(60, py + 4, name, font_body, C["text_primary"])

    # 高度范围
    draw_input(130, py - 2, 80, height_range)
    draw_text(215, py + 4, "mm", font_small, C["text_muted"])

    # 挤出机选择
    draw_select(260, py - 2, 100, extruder)
    py += 36

# 添加层按钮
py += 10
draw_rounded_rect(28, py, WIDTH - 72, 32, 6, outline=C["border_default"])
draw_text(160, py + 8, "+ 添加换色层", font_body, C["text_muted"])

y = y + 290

# ============================================
# 4. 台阶V槽
# ============================================
y = draw_section_header(y, "台阶V槽", True)

draw_rounded_rect(16, y, WIDTH - 32, 200, 8, fill=C["bg_elevated"])
py = y + 16

steps = [
    ("底板台阶", "5", True),
    ("面板台阶", "27", True),
    ("台阶3", "0", False),
]

for name, pos, enabled in steps:
    draw_checkbox(28, py + 4, "", enabled)
    draw_text(52, py + 2, name, font_body, C["text_primary"] if enabled else C["text_muted"])

    # 位置输入
    draw_text(160, py + 2, "位置", font_small, C["text_muted"])
    draw_input(200, py - 2, 60, pos, highlight=enabled)
    draw_text(268, py + 4, "mm", font_small, C["text_muted"])

    # 类型选择
    draw_select(310, py - 2, 70, "V型" if enabled else "平")
    py += 40

# 台阶参数
py += 10
draw_text(28, py, "台阶宽度", font_body, C["text_secondary"])
draw_input(150, py - 2, 80, "1.2")
draw_text(240, py + 4, "mm", font_small, C["text_muted"])

y = y + 210

# ============================================
# 5. 防翘裙边
# ============================================
y = draw_section_header(y, "防翘裙边", True)

draw_rounded_rect(16, y, WIDTH - 32, 200, 8, fill=C["bg_elevated"])
py = y + 16

# 启用开关
draw_checkbox(28, py, "启用防翘裙边", True)
py += 32

# 位置选择
draw_text(28, py, "裙边位置", font_body, C["text_secondary"])
draw_rounded_rect(150, py - 2, 70, 28, 6, fill=C["accent_primary"])
draw_text(168, py + 4, "外侧", font_body, (255,255,255))
draw_rounded_rect(230, py - 2, 70, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(248, py + 4, "内侧", font_body, C["text_muted"])
py += 40

skirt_params = [
    ("裙边高度", "0.6", "mm"),
    ("裙边宽度", "5", "mm"),
    ("裙边间距", "10", "mm"),
]
for label, value, unit in skirt_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(150, py - 2, 80, value)
    draw_text(240, py + 4, unit, font_small, C["text_muted"])
    py += 32

y = y + 210

# ============================================
# 6. 连襟字
# ============================================
y = draw_section_header(y, "连襟字", True)

draw_rounded_rect(16, y, WIDTH - 32, 180, 8, fill=C["bg_elevated"])
py = y + 16

draw_checkbox(28, py, "启用连襟字", False)
py += 32

# 连襟类型
draw_text(28, py, "连襟类型", font_body, C["text_muted"])
draw_rounded_rect(150, py - 2, 90, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(168, py + 4, "三角形", font_body, C["text_muted"])
draw_rounded_rect(250, py - 2, 90, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(275, py + 4, "菱形", font_body, C["text_muted"])
py += 40

lian_params = [
    ("连襟宽度", "15", "mm"),
    ("连襟高度", "20", "mm"),
]
for label, value, unit in lian_params:
    draw_text(28, py, label, font_body, C["text_muted"])
    draw_rounded_rect(150, py - 2, 80, 28, 6, fill=C["bg_card"], outline=C["border_default"])
    draw_text(160, py + 4, value, font_mono, C["text_muted"])
    draw_text(240, py + 4, unit, font_small, C["text_muted"])
    py += 32

y = y + 190

# ============================================
# 7. 面板打印
# ============================================
y = draw_section_header(y, "面板打印", True)

draw_rounded_rect(16, y, WIDTH - 32, 220, 8, fill=C["bg_elevated"])
py = y + 16

# 填充类型选择
draw_text(28, py, "填充类型", font_body, C["text_secondary"])
py += 28

fill_types = [("面板", True), ("网格", False), ("底板", False)]
ftx = 28
for name, active in fill_types:
    if active:
        draw_rounded_rect(ftx, py, 80, 28, 6, fill=C["accent_primary"])
        draw_text(ftx + 22, py + 6, name, font_body, (255,255,255))
    else:
        draw_rounded_rect(ftx, py, 80, 28, 6, fill=C["bg_card"], outline=C["border_default"])
        draw_text(ftx + 22, py + 6, name, font_body, C["text_muted"])
    ftx += 90
py += 40

panel_params = [
    ("填充间距", "3", "mm"),
    ("边界距离", "1.4", "mm"),
    ("填充角度", "45", "°"),
    ("填充速度", "40", "mm/s"),
]
for label, value, unit in panel_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(150, py - 2, 80, value)
    draw_text(240, py + 4, unit, font_small, C["text_muted"])
    py += 32

y = y + 230

# ============================================
# 底部操作按钮
# ============================================
y += 20

# 统计信息
draw_rounded_rect(16, y, WIDTH - 32, 50, 8, fill=C["bg_card"])
draw_text(28, y + 8, "预计打印时间", font_small, C["text_muted"])
draw_text(28, y + 26, "2h 15min", font_h2, C["accent_secondary"])
draw_text(200, y + 8, "耗材用量", font_small, C["text_muted"])
draw_text(200, y + 26, "125.8m", font_h2, C["accent_secondary"])

y += 60

# 主按钮 - 渐变
for i in range(WIDTH - 32):
    ratio = i / (WIDTH - 32)
    color = tuple(int(C["accent_primary"][j] + (C["accent_secondary"][j] - C["accent_primary"][j]) * ratio) for j in range(3))
    draw.line([(16 + i, y), (16 + i, y + 44)], fill=color)
draw_rounded_rect(16, y, WIDTH - 32, 44, 10, outline=None)
draw_text(140, y + 12, "生成 G-Code", font_h2, (255,255,255))

# ============================================
# 保存
# ============================================
output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "UI_Params_Expanded.png")
img.save(output_path, "PNG", quality=95)
print(f"Saved: {output_path}")

root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Params_Expanded.png")
img.save(root_path, "PNG", quality=95)
print(f"Saved: {root_path}")
