"""
SignMaker Slicer - 完整参数面板 V2
包含所有144项功能参数
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 配色
COLORS = {
    "bg_base": "#0A0E14",
    "bg_secondary": "#131A24",
    "bg_card": "#1A2332",
    "bg_elevated": "#1F2A3C",
    "text_primary": "#E6EDF3",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",
    "accent_primary": "#3B82F6",
    "accent_secondary": "#06B6D4",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "border_default": "#334155",
    "extruder_1": "#3B82F6",
    "extruder_2": "#EC4899",
    "extruder_3": "#F59E0B",
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) for k, v in COLORS.items()}

WIDTH = 480
HEIGHT = 4200  # 更高以容纳所有参数

img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_secondary"])
draw = ImageDraw.Draw(img)

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

def draw_input(x, y, w, value, disabled=False):
    bg = C["bg_card"] if not disabled else C["bg_elevated"]
    text_color = C["text_primary"] if not disabled else C["text_muted"]
    draw_rounded_rect(x, y, w, 26, 5, fill=bg, outline=C["border_default"])
    draw_text(x + 8, y + 5, str(value), font_mono, text_color)

def draw_select(x, y, w, value, disabled=False):
    text_color = C["text_muted"] if disabled else C["text_primary"]
    draw_rounded_rect(x, y, w, 26, 5, fill=C["bg_card"], outline=C["border_default"])
    draw_text(x + 8, y + 5, value, font_body, text_color)
    draw_text(x + w - 18, y + 5, "▼", font_small, C["text_muted"])

def draw_checkbox(x, y, label, checked=False, disabled=False):
    if disabled:
        fill_color = C["bg_elevated"]
        text_color = C["text_muted"]
    elif checked:
        fill_color = C["accent_primary"]
        text_color = C["text_primary"]
    else:
        fill_color = C["bg_elevated"]
        text_color = C["text_secondary"]
    draw_rounded_rect(x, y, 14, 14, 3, fill=fill_color, outline=C["border_default"])
    if checked:
        draw_text(x + 2, y - 2, "✓", font_small, (255,255,255))
    draw_text(x + 20, y - 1, label, font_body, text_color)

def draw_section(y, title, expanded=True):
    draw_rounded_rect(12, y, WIDTH - 24, 36, 8, fill=C["bg_card"])
    indicator = "▼" if expanded else "▶"
    draw_text(24, y + 10, indicator, font_small, C["accent_primary"] if expanded else C["text_muted"])
    draw_text(44, y + 10, title, font_h2, C["text_primary"])
    return y + 44

def draw_subsection(y, title):
    draw_text(24, y, title, font_body, C["accent_secondary"])
    draw.line([(24, y + 16), (WIDTH - 36, y + 16)], fill=C["border_default"], width=1)
    return y + 24

def draw_param_row(y, label, value, unit="", w_input=80):
    draw_text(24, y + 3, label, font_body, C["text_secondary"])
    draw_input(200, y, w_input, value)
    if unit:
        draw_text(200 + w_input + 8, y + 5, unit, font_small, C["text_muted"])
    return y + 30

# ============================================
# 标题
# ============================================
draw_text(16, 16, "参数设置 - 完整版 (所有功能)", font_h1, C["text_primary"])

y = 50

# ============================================
# 1. 字壳工艺
# ============================================
y = draw_section(y, "1. 字壳工艺")
draw_rounded_rect(12, y, WIDTH - 24, 420, 8, fill=C["bg_elevated"])
py = y + 12

# 打印模式
draw_text(24, py, "打印模式", font_body, C["text_secondary"])
draw_rounded_rect(200, py - 2, 60, 26, 5, fill=C["accent_primary"])
draw_text(215, py + 3, "正常", font_body, (255,255,255))
draw_rounded_rect(270, py - 2, 60, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(285, py + 3, "镜像", font_body, C["text_muted"])
py += 35

# 字边类型
draw_text(24, py, "字边类型", font_body, C["text_secondary"])
draw_select(200, py - 2, 120, "斜边")
py += 35

# 异形边
py = draw_subsection(py, "异形边管理")
draw_rounded_rect(24, py, 80, 50, 4, fill=C["bg_card"], outline=C["border_default"])
draw_text(100, py + 5, "添加", font_small, C["accent_primary"])
draw_text(140, py + 5, "选中", font_small, C["text_muted"])
draw_text(180, py + 5, "删除", font_small, C["error"])
py += 60

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
    py = draw_param_row(py, label, value, unit)

y = y + 430

# ============================================
# 2. 壁厚设置
# ============================================
y = draw_section(y, "2. 壁厚设置")
draw_rounded_rect(12, y, WIDTH - 24, 240, 8, fill=C["bg_elevated"])
py = y + 12

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
    py = draw_param_row(py, label, value, unit)

y = y + 250

# ============================================
# 3. 换色层设置
# ============================================
y = draw_section(y, "3. 换色层设置")
draw_rounded_rect(12, y, WIDTH - 24, 380, 8, fill=C["bg_elevated"])
py = y + 12

draw_text(24, py, "换色层配置 (最多7层)", font_body, C["text_primary"])
py += 25

# 表头
draw_text(24, py, "层", font_small, C["text_muted"])
draw_text(60, py, "高度范围", font_small, C["text_muted"])
draw_text(180, py, "挤出机", font_small, C["text_muted"])
draw_text(300, py, "换色偏移", font_small, C["text_muted"])
draw_text(400, py, "操作", font_small, C["text_muted"])
py += 22

layers = [
    ("1", "0-10", C["extruder_1"], "1号", "0"),
    ("2", "10-15", C["extruder_2"], "2号", "0.5"),
    ("3", "15-20", C["extruder_3"], "3号", "0.5"),
    ("4", "20-30", C["extruder_1"], "1号", "0"),
]
for num, height, color, ext, offset in layers:
    draw_rounded_rect(24, py, 24, 24, 4, fill=color)
    draw_text(32, py + 4, num, font_small, (255,255,255))
    draw_input(60, py, 90, height)
    draw_select(180, py, 80, ext)
    draw_input(300, py, 60, offset)
    draw_rounded_rect(400, py, 24, 24, 4, fill=C["error"])
    draw_text(408, py + 3, "×", font_body, (255,255,255))
    py += 32

draw_rounded_rect(24, py, WIDTH - 60, 28, 5, outline=C["accent_primary"])
draw_text(180, py + 6, "+ 添加换色层", font_body, C["accent_primary"])
py += 40

py = draw_subsection(py, "双层打印 (启用喷头2)")
draw_checkbox(24, py, "启用喷头2", False)
py += 28
draw_text(24, py, "双层吐丝宽度", font_body, C["text_muted"])
draw_input(200, py - 2, 80, "1.2", disabled=True)
draw_text(290, py + 3, "mm", font_small, C["text_muted"])
py += 28
draw_text(24, py, "双层走线偏移", font_body, C["text_muted"])
draw_input(200, py - 2, 80, "0.8", disabled=True)
draw_text(290, py + 3, "mm", font_small, C["text_muted"])
py += 28
draw_text(24, py, "双层走线次数", font_body, C["text_muted"])
draw_input(200, py - 2, 80, "1", disabled=True)
py += 28
draw_text(24, py, "双层走线速度", font_body, C["text_muted"])
draw_input(200, py - 2, 80, "30", disabled=True)
draw_text(290, py + 3, "mm/s", font_small, C["text_muted"])

y = y + 390

# ============================================
# 4. 台阶V槽
# ============================================
y = draw_section(y, "4. 台阶V槽")
draw_rounded_rect(12, y, WIDTH - 24, 380, 8, fill=C["bg_elevated"])
py = y + 12

draw_text(24, py, "台阶配置 (最多7个)", font_body, C["text_primary"])
py += 25

# 表头
draw_text(24, py, "启用", font_small, C["text_muted"])
draw_text(75, py, "名称", font_small, C["text_muted"])
draw_text(170, py, "位置", font_small, C["text_muted"])
draw_text(260, py, "高度", font_small, C["text_muted"])
draw_text(350, py, "宽度", font_small, C["text_muted"])
py += 22

steps = [
    (True, "底板台阶", "5", "1.2", "1.2"),
    (True, "面板台阶", "27", "1.2", "1.2"),
    (False, "台阶3", "0", "0", "0"),
    (False, "台阶4", "0", "0", "0"),
    (False, "台阶5", "0", "0", "0"),
    (False, "台阶6", "0", "0", "0"),
    (False, "台阶7", "0", "0", "0"),
]
for enabled, name, pos, h, w in steps:
    draw_checkbox(24, py + 3, "", enabled)
    draw_text(50, py + 1, name, font_small, C["text_primary"] if enabled else C["text_muted"])
    draw_input(150, py - 2, 55, pos, disabled=not enabled)
    draw_input(230, py - 2, 55, h, disabled=not enabled)
    draw_input(310, py - 2, 55, w, disabled=not enabled)
    py += 30

py += 10
py = draw_subsection(py, "台阶打印参数")
step_params = [
    ("台阶速度", "30", "mm/s"),
    ("喷头水平偏移", "0", "mm"),
    ("喷头吐丝宽度", "1.2", "mm"),
    ("台阶厚度", "0.3", "mm"),
]
for label, value, unit in step_params:
    py = draw_param_row(py, label, value, unit)

y = y + 390

# ============================================
# 5. 防翘裙边
# ============================================
y = draw_section(y, "5. 防翘裙边")
draw_rounded_rect(12, y, WIDTH - 24, 300, 8, fill=C["bg_elevated"])
py = y + 12

draw_checkbox(24, py, "启用防翘裙边", True)
py += 32

draw_text(24, py, "裙边位置", font_body, C["text_secondary"])
draw_rounded_rect(200, py - 2, 60, 26, 5, fill=C["accent_primary"])
draw_text(212, py + 3, "外侧", font_body, (255,255,255))
draw_rounded_rect(270, py - 2, 60, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(282, py + 3, "内侧", font_body, C["text_muted"])
py += 38

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
    py = draw_param_row(py, label, value, unit)

y = y + 310

# ============================================
# 6. 连襟字
# ============================================
y = draw_section(y, "6. 连襟字")
draw_rounded_rect(12, y, WIDTH - 24, 280, 8, fill=C["bg_elevated"])
py = y + 12

draw_checkbox(24, py, "启用连襟字", True)
py += 32

draw_text(24, py, "连襟类型", font_body, C["text_secondary"])
draw_rounded_rect(200, py - 2, 80, 26, 5, fill=C["accent_primary"])
draw_text(215, py + 3, "三角形", font_body, (255,255,255))
draw_rounded_rect(290, py - 2, 80, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(312, py + 3, "菱形", font_body, C["text_muted"])
py += 38

lian_params = [
    ("连襟宽度", "15", "mm"),
    ("连襟高度", "5", "mm"),
    ("连襟底座高度", "5", "mm"),
    ("连襟支撑偏移", "2.5", "mm"),
    ("整板排序行距", "0", "mm"),
]
for label, value, unit in lian_params:
    py = draw_param_row(py, label, value, unit)

py += 5
draw_text(24, py, "提示: 连襟高度 + 底座高度 = 连襟总高度", font_small, C["warning"])

y = y + 290

# ============================================
# 7. 包边勾边字
# ============================================
y = draw_section(y, "7. 包边勾边字")
draw_rounded_rect(12, y, WIDTH - 24, 340, 8, fill=C["bg_elevated"])
py = y + 12

draw_checkbox(24, py, "包边有效", False)
draw_checkbox(180, py, "勾边有效", True)
py += 32

draw_text(24, py, "位置", font_body, C["text_secondary"])
draw_rounded_rect(200, py - 2, 60, 26, 5, fill=C["accent_primary"])
draw_text(215, py + 3, "内部", font_body, (255,255,255))
draw_rounded_rect(270, py - 2, 60, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(285, py + 3, "外部", font_body, C["text_muted"])
py += 38

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
    py = draw_param_row(py, label, value, unit)

y = y + 350

# ============================================
# 8. 面板打印
# ============================================
y = draw_section(y, "8. 面板打印")
draw_rounded_rect(12, y, WIDTH - 24, 580, 8, fill=C["bg_elevated"])
py = y + 12

draw_text(24, py, "填充类型", font_body, C["text_primary"])
py += 28
fill_types = [("面板", True), ("网格", False), ("底板", False)]
ftx = 24
for name, active in fill_types:
    if active:
        draw_rounded_rect(ftx, py, 100, 28, 5, fill=C["accent_primary"])
        draw_text(ftx + 30, py + 6, name, font_body, (255,255,255))
    else:
        draw_rounded_rect(ftx, py, 100, 28, 5, fill=C["bg_card"], outline=C["border_default"])
        draw_text(ftx + 30, py + 6, name, font_body, C["text_muted"])
    ftx += 115
py += 45

# 通用参数
py = draw_subsection(py, "通用填充参数")
common_params = [
    ("填充间距", "3", "mm"),
    ("填充间距2", "0.9", "mm"),
    ("边界距离", "1.4", "mm"),
    ("角度", "45", "°"),
]
for label, value, unit in common_params:
    py = draw_param_row(py, label, value, unit)

draw_checkbox(24, py, "连襟不参与", True)
draw_checkbox(200, py, "面板不参与", True)
py += 35

# 1类填充
py = draw_subsection(py, "1类填充 (正面)")
fill1_params = [
    ("填充高度", "0.6", "mm"),
    ("填充速度", "40", "mm/s"),
    ("吐丝宽度", "1.2", "mm"),
    ("压线宽度", "0.8", "mm"),
]
for label, value, unit in fill1_params:
    py = draw_param_row(py, label, value, unit)
draw_text(24, py, "填充模式", font_body, C["text_secondary"])
draw_select(200, py - 2, 120, "自动连接")
py += 30
draw_text(24, py, "指定挤出机", font_body, C["text_secondary"])
draw_select(200, py - 2, 120, "无")
py += 35

# 2类填充
py = draw_subsection(py, "2类填充 (背面)")
fill2_params = [
    ("填充高度", "1.5", "mm"),
    ("填充速度", "60", "mm/s"),
]
for label, value, unit in fill2_params:
    py = draw_param_row(py, label, value, unit)
draw_text(24, py, "指定挤出机", font_body, C["text_secondary"])
draw_select(200, py - 2, 120, "无")

y = y + 590

# ============================================
# 9. 面板花纹
# ============================================
y = draw_section(y, "9. 面板花纹")
draw_rounded_rect(12, y, WIDTH - 24, 260, 8, fill=C["bg_elevated"])
py = y + 12

draw_checkbox(24, py, "启用面板花纹", False)
py += 32

draw_text(24, py, "花纹类型", font_body, C["text_muted"])
draw_rounded_rect(200, py - 2, 80, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(220, py + 3, "直边", font_body, C["text_muted"])
draw_rounded_rect(290, py - 2, 80, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(310, py + 3, "斜边", font_body, C["text_muted"])
py += 38

pattern_params = [
    ("打印高度", "0.2", "mm"),
    ("斜边宽度", "1.2", "mm"),
    ("底座厚度", "0.6", "mm"),
    ("打印速度", "40", "mm/s"),
    ("吐丝宽度", "1.2", "mm"),
]
for label, value, unit in pattern_params:
    draw_text(24, py, label, font_body, C["text_muted"])
    draw_input(200, py - 2, 80, value, disabled=True)
    draw_text(290, py + 3, unit, font_small, C["text_muted"])
    py += 28
draw_text(24, py, "指定挤出机", font_body, C["text_muted"])
draw_select(200, py - 2, 120, "无", disabled=True)

y = y + 270

# ============================================
# 10. 底孔
# ============================================
y = draw_section(y, "10. 底孔")
draw_rounded_rect(12, y, WIDTH - 24, 100, 8, fill=C["bg_elevated"])
py = y + 12

draw_text(24, py, "底孔选择", font_body, C["text_secondary"])
draw_text(200, py, "在画布中点击内孔选择出线孔(显示绿色)", font_small, C["text_muted"])
py += 30
py = draw_param_row(py, "底孔高度", "0", "mm")

y = y + 110

# ============================================
# 11. 生成底板/面板
# ============================================
y = draw_section(y, "11. 生成底板/面板 DXF")
draw_rounded_rect(12, y, WIDTH - 24, 220, 8, fill=C["bg_elevated"])
py = y + 12

draw_checkbox(24, py, "生成底板 DXF", True)
py += 28
py = draw_param_row(py, "对齐补偿", "-0.4", "mm")
draw_text(24, py, "保存路径", font_body, C["text_secondary"])
draw_rounded_rect(200, py - 2, 200, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(210, py + 3, "桌面/底板.dxf", font_small, C["text_muted"])
draw_rounded_rect(410, py - 2, 40, 26, 5, fill=C["accent_primary"])
draw_text(422, py + 3, "...", font_body, (255,255,255))
py += 40

draw_checkbox(24, py, "生成面板 DXF", True)
py += 28
py = draw_param_row(py, "对齐补偿", "0", "mm")
draw_text(24, py, "保存路径", font_body, C["text_secondary"])
draw_rounded_rect(200, py - 2, 200, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(210, py + 3, "桌面/面板.dxf", font_small, C["text_muted"])
draw_rounded_rect(410, py - 2, 40, 26, 5, fill=C["accent_primary"])
draw_text(422, py + 3, "...", font_body, (255,255,255))

y = y + 230

# ============================================
# 12. 文件输出
# ============================================
y = draw_section(y, "12. 文件输出")
draw_rounded_rect(12, y, WIDTH - 24, 340, 8, fill=C["bg_elevated"])
py = y + 12

draw_text(24, py, "文件名", font_body, C["text_secondary"])
draw_rounded_rect(200, py - 2, 250, 26, 5, fill=C["bg_card"], outline=C["border_default"])
draw_text(210, py + 3, "发光字.gcode", font_mono, C["text_primary"])
py += 35

output_params = [
    ("打印速度", "50", "mm/s"),
    ("首层打印速度", "30", "mm/s"),
    ("空程速度", "300", "mm/s"),
    ("喷头1温度", "230", "°C"),
    ("喷头2温度", "230", "°C"),
    ("喷头3温度", "230", "°C"),
]
for label, value, unit in output_params:
    py = draw_param_row(py, label, value, unit)

py += 5
draw_text(24, py, "机台类型", font_body, C["text_secondary"])
draw_select(200, py - 2, 150, "ZC-80 (800x800)")
py += 35

draw_checkbox(24, py, "头尾交替打印", False)
py += 26
draw_checkbox(24, py, "结束完成不回抽", False)

y = y + 350

# ============================================
# 13. 机械参数
# ============================================
y = draw_section(y, "13. 机械参数")
draw_rounded_rect(12, y, WIDTH - 24, 580, 8, fill=C["bg_elevated"])
py = y + 12

py = draw_subsection(py, "基础参数")
base_params = [
    ("材料直径", "1.75", "mm"),
    ("抬头回抽", "2", "mm"),
    ("换料回抽", "5", "mm"),
    ("换料补偿", "3", "mm"),
    ("消除邻近点距离", "0.1", "mm"),
]
for label, value, unit in base_params:
    py = draw_param_row(py, label, value, unit)

py = draw_subsection(py, "空走参数")
travel_params = [
    ("空走抬头高度1", "2", "mm"),
    ("空走抬头高度2", "5", "mm"),
    ("空走最长距离", "50", "mm"),
]
for label, value, unit in travel_params:
    py = draw_param_row(py, label, value, unit)

py = draw_subsection(py, "喷头参数")
head_params = [
    ("结束喷头位置", "50", "mm"),
    ("清洗喷头", "30", "mm"),
    ("提前关胶距离", "0.5", "mm"),
]
for label, value, unit in head_params:
    py = draw_param_row(py, label, value, unit)

py = draw_subsection(py, "速度参数")
speed_params = [
    ("Z轴抬落速度", "300", "mm/s"),
    ("抬头挤出速度", "30", "mm/s"),
    ("抬头回抽速度", "30", "mm/s"),
    ("换色速度", "40", "mm/s"),
    ("换色回抽速度", "30", "mm/s"),
]
for label, value, unit in speed_params:
    py = draw_param_row(py, label, value, unit)

py = draw_subsection(py, "缺料补偿 (各挤出机独立)")
draw_text(24, py, "挤出机", font_small, C["text_muted"])
draw_text(120, py, "近距离补偿", font_small, C["text_muted"])
draw_text(240, py, "远距离补偿", font_small, C["text_muted"])
draw_text(360, py, "分界线", font_small, C["text_muted"])
py += 22

for i, color in enumerate([C["extruder_1"], C["extruder_2"], C["extruder_3"]]):
    draw_rounded_rect(24, py, 60, 24, 4, fill=color)
    draw_text(40, py + 4, f"{i+1}号", font_small, (255,255,255))
    draw_input(100, py - 2, 60, "0.4")
    draw_input(200, py - 2, 60, "0.4")
    draw_input(320, py - 2, 60, "100")
    draw_text(390, py + 3, "mm", font_small, C["text_muted"])
    py += 32

y = y + 590

# ============================================
# 底部操作
# ============================================
y += 20

# 统计
draw_rounded_rect(12, y, WIDTH - 24, 60, 8, fill=C["bg_card"])
draw_text(24, y + 10, "预计打印时间", font_small, C["text_muted"])
draw_text(24, y + 30, "2h 15min", font_h2, C["accent_secondary"])
draw_text(160, y + 10, "耗材用量", font_small, C["text_muted"])
draw_text(160, y + 30, "125.8m", font_h2, C["accent_secondary"])
draw_text(300, y + 10, "总层数", font_small, C["text_muted"])
draw_text(300, y + 30, "100层", font_h2, C["accent_secondary"])

y += 75

# 计算路径
draw_rounded_rect(12, y, WIDTH - 24, 44, 10, fill=C["warning"])
draw_text(180, y + 12, "计算路径", font_h2, (0,0,0))

y += 55

# 生成G-Code
for i in range(WIDTH - 24):
    ratio = i / (WIDTH - 24)
    color = tuple(int(C["accent_primary"][j] + (C["accent_secondary"][j] - C["accent_primary"][j]) * ratio) for j in range(3))
    draw.line([(12 + i, y), (12 + i, y + 44)], fill=color)
draw_rounded_rect(12, y, WIDTH - 24, 44, 10, outline=None)
draw_text(170, y + 12, "生成 G-Code", font_h2, (255,255,255))

# ============================================
# 保存
# ============================================
output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "UI_Params_Complete.png")
img.save(output_path, "PNG", quality=95)
print(f"Saved: {output_path}")

root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Params_Complete.png")
img.save(root_path, "PNG", quality=95)
print(f"Saved: {root_path}")
