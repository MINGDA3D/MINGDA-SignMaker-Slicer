"""
SignMaker Slicer - 参数面板完整版
包含所有参数分组的完整设置
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

# 更高的画布
WIDTH = 450
HEIGHT = 2800

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

def draw_input(x, y, w, value, highlight=False, disabled=False):
    if disabled:
        bg = C["bg_card"]
        text_color = C["text_muted"]
        border = C["border_default"]
    elif highlight:
        bg = C["accent_primary"]
        text_color = (255,255,255)
        border = C["accent_primary"]
    else:
        bg = C["bg_card"]
        text_color = C["text_primary"]
        border = C["border_default"]
    draw_rounded_rect(x, y, w, 28, 6, fill=bg, outline=border)
    draw_text(x + 10, y + 6, str(value), font_mono, text_color)

def draw_select(x, y, w, value, disabled=False):
    text_color = C["text_muted"] if disabled else C["text_primary"]
    draw_rounded_rect(x, y, w, 28, 6, fill=C["bg_card"], outline=C["border_default"])
    draw_text(x + 10, y + 6, value, font_body, text_color)
    draw_text(x + w - 20, y + 6, "▼", font_small, C["text_muted"])

def draw_checkbox(x, y, label, checked=False, disabled=False):
    if disabled:
        box_color = C["border_default"]
        fill_color = C["bg_elevated"]
        text_color = C["text_muted"]
    elif checked:
        box_color = C["accent_primary"]
        fill_color = C["accent_primary"]
        text_color = C["text_primary"]
    else:
        box_color = C["border_default"]
        fill_color = C["bg_elevated"]
        text_color = C["text_secondary"]

    draw_rounded_rect(x, y, 16, 16, 3, fill=fill_color, outline=box_color)
    if checked:
        draw_text(x + 3, y - 1, "✓", font_small, (255,255,255))
    draw_text(x + 24, y, label, font_body, text_color)

def draw_section_header(y, title, expanded=True):
    draw_rounded_rect(16, y, WIDTH - 32, 40, 8, fill=C["bg_card"])
    indicator = "▼" if expanded else "▶"
    draw_text(28, y + 12, indicator, font_small, C["accent_primary"] if expanded else C["text_muted"])
    draw_text(48, y + 12, title, font_h2, C["text_primary"])
    return y + 48

def draw_subsection(y, title):
    draw_text(28, y, title, font_body, C["accent_secondary"])
    draw.line([(28, y + 18), (WIDTH - 44, y + 18)], fill=C["border_default"], width=1)
    return y + 28

# ============================================
# 面板标题
# ============================================
draw_text(20, 20, "参数设置 - 完整版", font_h1, C["text_primary"])

# 快速设置
card_y = 55
draw_rounded_rect(16, card_y, WIDTH - 32, 80, 10, fill=C["bg_card"])
quick_params = [("字壳高度", "30", "mm"), ("壁厚", "1.2", "mm"), ("层高", "0.3", "mm")]
qp_x = 28
for label, value, unit in quick_params:
    draw_text(qp_x, card_y + 12, label, font_small, C["text_muted"])
    draw_rounded_rect(qp_x, card_y + 30, 110, 32, 6, fill=C["bg_elevated"])
    draw_text(qp_x + 10, card_y + 38, value, font_mono, C["text_primary"])
    draw_text(qp_x + 75, card_y + 40, unit, font_small, C["text_muted"])
    qp_x += 135

y = card_y + 100

# ============================================
# 1. 字壳工艺
# ============================================
y = draw_section_header(y, "字壳工艺", True)
draw_rounded_rect(16, y, WIDTH - 32, 400, 8, fill=C["bg_elevated"])
py = y + 16

# 打印模式
draw_text(28, py, "打印模式", font_body, C["text_secondary"])
draw_rounded_rect(150, py - 2, 70, 28, 6, fill=C["accent_primary"])
draw_text(168, py + 4, "正常", font_body, (255,255,255))
draw_rounded_rect(230, py - 2, 70, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(248, py + 4, "镜像", font_body, C["text_muted"])
py += 40

# 字边类型
draw_text(28, py, "字边类型", font_body, C["text_secondary"])
draw_select(150, py - 2, 150, "斜边")
py += 40

params = [
    ("字壳高度", "30", "mm"),
    ("斜边宽度", "5", "mm"),
    ("面板厚度", "3", "mm"),
    ("底板厚度", "10", "mm"),
    ("层高", "0.3", "mm"),
    ("预打边线偏移", "20", "mm"),
    ("预打边线次数", "2", "次"),
    ("雕刻刀刃宽", "0.4", "mm"),
]
for label, value, unit in params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(180, py - 2, 90, value)
    draw_text(280, py + 4, unit, font_small, C["text_muted"])
    py += 34

y = y + 410

# ============================================
# 2. 壁厚设置
# ============================================
y = draw_section_header(y, "壁厚设置", True)
draw_rounded_rect(16, y, WIDTH - 32, 250, 8, fill=C["bg_elevated"])
py = y + 16

wall_params = [
    ("壁厚", "1.2", "mm"),
    ("壁厚补偿", "0", "mm"),
    ("走线次数", "1", "次"),
    ("走线高度", "0", "mm"),
    ("走线偏移", "0.8", "mm"),
    ("字芯高度", "0", "mm"),
    ("字芯斜边宽度", "0", "mm"),
]
for label, value, unit in wall_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(180, py - 2, 90, value)
    draw_text(280, py + 4, unit, font_small, C["text_muted"])
    py += 32

y = y + 260

# ============================================
# 3. 换色层设置
# ============================================
y = draw_section_header(y, "换色层设置", True)
draw_rounded_rect(16, y, WIDTH - 32, 340, 8, fill=C["bg_elevated"])
py = y + 16

draw_text(28, py, "换色层配置", font_body, C["text_primary"])
py += 28

# 表头
draw_text(28, py, "层", font_small, C["text_muted"])
draw_text(80, py, "高度范围", font_small, C["text_muted"])
draw_text(200, py, "挤出机", font_small, C["text_muted"])
draw_text(320, py, "操作", font_small, C["text_muted"])
py += 24

layers_data = [
    ("1", "0-10", C["extruder_1"], "1号"),
    ("2", "10-15", C["extruder_2"], "2号"),
    ("3", "15-20", C["extruder_3"], "3号"),
    ("4", "20-30", C["extruder_1"], "1号"),
]

for num, height_range, color, extruder in layers_data:
    draw_rounded_rect(28, py, 30, 28, 4, fill=color)
    draw_text(38, py + 6, num, font_body, (255,255,255))
    draw_input(70, py, 100, height_range)
    draw_text(175, py + 6, "mm", font_small, C["text_muted"])
    draw_select(210, py, 90, extruder)
    # 删除按钮
    draw_rounded_rect(320, py, 28, 28, 4, fill=C["error"])
    draw_text(330, py + 5, "×", font_body, (255,255,255))
    py += 38

# 添加按钮
py += 10
draw_rounded_rect(28, py, WIDTH - 72, 32, 6, outline=C["accent_primary"])
draw_text(170, py + 8, "+ 添加换色层", font_body, C["accent_primary"])
py += 45

# 启用喷头2
draw_checkbox(28, py, "启用喷头2 (双层打印)", False)

y = y + 350

# ============================================
# 4. 台阶V槽
# ============================================
y = draw_section_header(y, "台阶V槽", True)
draw_rounded_rect(16, y, WIDTH - 32, 320, 8, fill=C["bg_elevated"])
py = y + 16

draw_text(28, py, "台阶配置 (最多7个)", font_body, C["text_primary"])
py += 28

# 表头
draw_text(28, py, "启用", font_small, C["text_muted"])
draw_text(80, py, "名称", font_small, C["text_muted"])
draw_text(180, py, "位置", font_small, C["text_muted"])
draw_text(270, py, "高度", font_small, C["text_muted"])
draw_text(360, py, "宽度", font_small, C["text_muted"])
py += 24

steps = [
    (True, "底板台阶", "5", "1.2", "1.2"),
    (True, "面板台阶", "27", "1.2", "1.2"),
    (False, "台阶3", "0", "0", "0"),
    (False, "台阶4", "0", "0", "0"),
]

for enabled, name, pos, height, width in steps:
    draw_checkbox(28, py + 4, "", enabled)
    draw_text(55, py + 2, name, font_small, C["text_primary"] if enabled else C["text_muted"])
    draw_input(155, py - 2, 55, pos, disabled=not enabled)
    draw_input(230, py - 2, 55, height, disabled=not enabled)
    draw_input(305, py - 2, 55, width, disabled=not enabled)
    py += 38

py += 10
py = draw_subsection(py, "台阶打印参数")
step_params = [
    ("台阶速度", "30", "mm/s"),
    ("喷头吐丝宽度", "1.2", "mm"),
    ("台阶厚度", "0.3", "mm"),
]
for label, value, unit in step_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(180, py - 2, 80, value)
    draw_text(270, py + 4, unit, font_small, C["text_muted"])
    py += 32

y = y + 330

# ============================================
# 5. 防翘裙边
# ============================================
y = draw_section_header(y, "防翘裙边", True)
draw_rounded_rect(16, y, WIDTH - 32, 280, 8, fill=C["bg_elevated"])
py = y + 16

draw_checkbox(28, py, "启用防翘裙边", True)
py += 36

draw_text(28, py, "裙边位置", font_body, C["text_secondary"])
draw_rounded_rect(150, py - 2, 70, 28, 6, fill=C["accent_primary"])
draw_text(165, py + 4, "外侧", font_body, (255,255,255))
draw_rounded_rect(230, py - 2, 70, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(245, py + 4, "内侧", font_body, C["text_muted"])
py += 42

skirt_params = [
    ("压线宽度", "0.5", "mm"),
    ("吐丝宽度", "1.2", "mm"),
    ("防翘速度", "30", "mm/s"),
    ("防翘高度", "0.6", "mm"),
    ("防翘长度", "10", "mm"),
    ("防翘宽度", "5", "mm"),
    ("V型开口宽度", "3", "mm"),
]
for label, value, unit in skirt_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(180, py - 2, 80, value)
    draw_text(270, py + 4, unit, font_small, C["text_muted"])
    py += 28

y = y + 290

# ============================================
# 6. 连襟字 (完整版)
# ============================================
y = draw_section_header(y, "连襟字", True)
draw_rounded_rect(16, y, WIDTH - 32, 320, 8, fill=C["bg_elevated"])
py = y + 16

draw_checkbox(28, py, "启用连襟字", True)
py += 36

# 连襟类型
draw_text(28, py, "连襟类型", font_body, C["text_secondary"])
draw_rounded_rect(150, py - 2, 90, 28, 6, fill=C["accent_primary"])
draw_text(165, py + 4, "三角形", font_body, (255,255,255))
draw_rounded_rect(250, py - 2, 90, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(275, py + 4, "菱形", font_body, C["text_muted"])
py += 42

lian_params = [
    ("连襟宽度", "15", "mm"),
    ("连襟高度", "5", "mm"),
    ("连襟底座高度", "5", "mm"),
    ("连襟支撑偏移", "2.5", "mm"),
    ("整板排序行距", "0", "mm"),
]
for label, value, unit in lian_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(180, py - 2, 80, value)
    draw_text(270, py + 4, unit, font_small, C["text_muted"])
    py += 32

py += 10
draw_text(28, py, "提示: 连襟高度+底座高度=连襟总高度", font_small, C["warning"])

y = y + 330

# ============================================
# 7. 包边勾边字
# ============================================
y = draw_section_header(y, "包边勾边字", True)
draw_rounded_rect(16, y, WIDTH - 32, 300, 8, fill=C["bg_elevated"])
py = y + 16

draw_checkbox(28, py, "包边有效", False)
draw_checkbox(180, py, "勾边有效", True)
py += 32

draw_text(28, py, "位置", font_body, C["text_secondary"])
draw_rounded_rect(150, py - 2, 70, 28, 6, fill=C["accent_primary"])
draw_text(168, py + 4, "内部", font_body, (255,255,255))
draw_rounded_rect(230, py - 2, 70, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(248, py + 4, "外部", font_body, C["text_muted"])
py += 42

edge_params = [
    ("包边高度", "1.2", "mm"),
    ("勾边高度", "1.2", "mm"),
    ("勾包边宽度", "3", "mm"),
    ("勾包边速度", "30", "mm/s"),
    ("包边压线偏移", "0", "mm"),
    ("勾边压线偏移", "0", "mm"),
    ("吐丝宽度", "1.2", "mm"),
]
for label, value, unit in edge_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(180, py - 2, 80, value)
    draw_text(270, py + 4, unit, font_small, C["text_muted"])
    py += 28

y = y + 310

# ============================================
# 8. 面板打印 (完整版)
# ============================================
y = draw_section_header(y, "面板打印", True)
draw_rounded_rect(16, y, WIDTH - 32, 520, 8, fill=C["bg_elevated"])
py = y + 16

# 填充类型选择
draw_text(28, py, "填充类型", font_body, C["text_primary"])
py += 28

fill_types = [("面板", True), ("网格", False), ("底板", False)]
ftx = 28
for name, active in fill_types:
    if active:
        draw_rounded_rect(ftx, py, 100, 32, 6, fill=C["accent_primary"])
        draw_text(ftx + 30, py + 8, name, font_body, (255,255,255))
    else:
        draw_rounded_rect(ftx, py, 100, 32, 6, fill=C["bg_card"], outline=C["border_default"])
        draw_text(ftx + 30, py + 8, name, font_body, C["text_muted"])
    ftx += 115
py += 50

# 填充设置
py = draw_subsection(py, "填充参数设置")
fill_params = [
    ("填充间距", "3", "mm"),
    ("填充间距2", "0.9", "mm"),
    ("边界距离", "1.4", "mm"),
    ("角度", "45", "°"),
]
for label, value, unit in fill_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    draw_input(180, py - 2, 80, value)
    draw_text(270, py + 4, unit, font_small, C["text_muted"])
    py += 30

draw_checkbox(28, py, "连襟不参与", True)
draw_checkbox(180, py, "面板不参与", True)
py += 40

# 1类填充
py = draw_subsection(py, "1类填充 (正面)")
fill1_params = [
    ("填充高度", "0.6", "mm"),
    ("填充模式", "自动连接", ""),
    ("吐丝宽度", "1.2", "mm"),
    ("填充速度", "40", "mm/s"),
    ("指定挤出机", "无", ""),
    ("压线宽度", "0.8", "mm"),
]
for label, value, unit in fill1_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    if unit == "":
        draw_select(180, py - 2, 100, value)
    else:
        draw_input(180, py - 2, 80, value)
        draw_text(270, py + 4, unit, font_small, C["text_muted"])
    py += 28

# 2类填充
py = draw_subsection(py, "2类填充 (背面)")
fill2_params = [
    ("填充高度", "1.5", "mm"),
    ("填充速度", "60", "mm/s"),
    ("指定挤出机", "无", ""),
]
for label, value, unit in fill2_params:
    draw_text(28, py, label, font_body, C["text_secondary"])
    if unit == "":
        draw_select(180, py - 2, 100, value)
    else:
        draw_input(180, py - 2, 80, value)
        draw_text(270, py + 4, unit, font_small, C["text_muted"])
    py += 28

y = y + 530

# ============================================
# 9. 面板花纹
# ============================================
y = draw_section_header(y, "面板花纹", True)
draw_rounded_rect(16, y, WIDTH - 32, 220, 8, fill=C["bg_elevated"])
py = y + 16

draw_checkbox(28, py, "启用面板花纹", False)
py += 36

draw_text(28, py, "花纹类型", font_body, C["text_muted"])
draw_rounded_rect(150, py - 2, 70, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(168, py + 4, "直边", font_body, C["text_muted"])
draw_rounded_rect(230, py - 2, 70, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(248, py + 4, "斜边", font_body, C["text_muted"])
py += 42

pattern_params = [
    ("打印高度", "0.2", "mm"),
    ("斜边宽度", "1.2", "mm"),
    ("底座厚度", "0.6", "mm"),
    ("打印速度", "40", "mm/s"),
]
for label, value, unit in pattern_params:
    draw_text(28, py, label, font_body, C["text_muted"])
    draw_input(180, py - 2, 80, value, disabled=True)
    draw_text(270, py + 4, unit, font_small, C["text_muted"])
    py += 28

y = y + 230

# ============================================
# 10. 生成底板/面板
# ============================================
y = draw_section_header(y, "生成底板/面板", True)
draw_rounded_rect(16, y, WIDTH - 32, 220, 8, fill=C["bg_elevated"])
py = y + 16

# 生成底板
draw_checkbox(28, py, "生成底板 DXF", True)
py += 32

draw_text(28, py, "对齐补偿", font_body, C["text_secondary"])
draw_input(180, py - 2, 80, "-0.4")
draw_text(270, py + 4, "mm", font_small, C["text_muted"])
py += 32

draw_text(28, py, "保存路径", font_body, C["text_secondary"])
draw_rounded_rect(150, py - 2, 200, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(160, py + 4, "桌面/底板.dxf", font_small, C["text_muted"])
draw_rounded_rect(360, py - 2, 50, 28, 6, fill=C["accent_primary"])
draw_text(372, py + 4, "...", font_body, (255,255,255))
py += 45

# 生成面板
draw_checkbox(28, py, "生成面板 DXF", True)
py += 32

draw_text(28, py, "对齐补偿", font_body, C["text_secondary"])
draw_input(180, py - 2, 80, "0")
draw_text(270, py + 4, "mm", font_small, C["text_muted"])
py += 32

draw_text(28, py, "保存路径", font_body, C["text_secondary"])
draw_rounded_rect(150, py - 2, 200, 28, 6, fill=C["bg_card"], outline=C["border_default"])
draw_text(160, py + 4, "桌面/面板.dxf", font_small, C["text_muted"])
draw_rounded_rect(360, py - 2, 50, 28, 6, fill=C["accent_primary"])
draw_text(372, py + 4, "...", font_body, (255,255,255))

y = y + 230

# ============================================
# 底部操作
# ============================================
y += 20

# 统计信息
draw_rounded_rect(16, y, WIDTH - 32, 60, 8, fill=C["bg_card"])
draw_text(28, y + 10, "预计打印时间", font_small, C["text_muted"])
draw_text(28, y + 30, "2h 15min", font_h2, C["accent_secondary"])
draw_text(160, y + 10, "耗材用量", font_small, C["text_muted"])
draw_text(160, y + 30, "125.8m", font_h2, C["accent_secondary"])
draw_text(280, y + 10, "总层数", font_small, C["text_muted"])
draw_text(280, y + 30, "100层", font_h2, C["accent_secondary"])

y += 75

# 计算路径按钮
draw_rounded_rect(16, y, WIDTH - 32, 44, 10, fill=C["warning"])
draw_text(160, y + 12, "计算路径", font_h2, (0,0,0))

y += 55

# 主按钮
for i in range(WIDTH - 32):
    ratio = i / (WIDTH - 32)
    color = tuple(int(C["accent_primary"][j] + (C["accent_secondary"][j] - C["accent_primary"][j]) * ratio) for j in range(3))
    draw.line([(16 + i, y), (16 + i, y + 44)], fill=color)
draw_rounded_rect(16, y, WIDTH - 32, 44, 10, outline=None)
draw_text(155, y + 12, "生成 G-Code", font_h2, (255,255,255))

# ============================================
# 保存
# ============================================
output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "UI_Params_Full.png")
img.save(output_path, "PNG", quality=95)
print(f"Saved: {output_path}")

root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Params_Full.png")
img.save(root_path, "PNG", quality=95)
print(f"Saved: {root_path}")
