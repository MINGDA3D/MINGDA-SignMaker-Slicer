"""
SignMaker Slicer UI Mockup Generator V2
基于INC-S实际界面的完整效果图
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 颜色定义
COLORS = {
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_panel": "#21262D",
    "bg_hover": "#30363D",
    "bg_input": "#0D1117",
    "text_primary": "#F0F6FC",
    "text_secondary": "#C9D1D9",
    "text_muted": "#8B949E",
    "accent_primary": "#58A6FF",
    "accent_success": "#3FB950",
    "accent_warning": "#F59E0B",
    "accent_error": "#F85149",
    "border_default": "#30363D",
    "canvas_bg": "#1A1D21",
    "btn_primary": "#58A6FF",
    "btn_warning": "#F59E0B",
    "btn_danger": "#F85149",
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) for k, v in COLORS.items()}

# 画布尺寸 - 更大以容纳更多内容
WIDTH = 1600
HEIGHT = 1000

# 布局
MENUBAR_H = 28
TOOLBAR_H = 80  # 两行工具栏
STATUSBAR_H = 26
SIDEBAR_LEFT_W = 60  # 工具箱
SIDEBAR_RIGHT_W = 420  # 更宽的参数面板

img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_primary"])
draw = ImageDraw.Draw(img)

# 字体
try:
    font_title = ImageFont.truetype("msyh.ttc", 13)
    font_body = ImageFont.truetype("msyh.ttc", 11)
    font_small = ImageFont.truetype("msyh.ttc", 9)
    font_mono = ImageFont.truetype("consola.ttf", 10)
    font_large = ImageFont.truetype("msyh.ttc", 72)
except:
    font_title = font_body = font_small = font_mono = font_large = ImageFont.load_default()

def draw_rect(x, y, w, h, fill=None, outline=None):
    draw.rectangle([x, y, x+w, y+h], fill=fill, outline=outline)

def draw_rounded_rect(x, y, w, h, r, fill=None, outline=None):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline)

def draw_text(x, y, text, font=None, fill=None):
    draw.text((x, y), text, font=font or font_body, fill=fill or C["text_secondary"])

def draw_input(x, y, w, value, unit="", highlight=False):
    """绘制输入框"""
    bg = C["accent_warning"] if highlight else C["bg_input"]
    text_color = (0,0,0) if highlight else C["text_primary"]
    draw_rounded_rect(x, y, w, 22, 3, fill=bg, outline=C["border_default"])
    draw_text(x + 6, y + 4, str(value), font_mono, text_color)
    if unit:
        draw_text(x + w + 4, y + 4, unit, font_small, C["text_muted"])

def draw_checkbox(x, y, label, checked=False):
    """绘制复选框"""
    box_color = C["accent_primary"] if checked else C["border_default"]
    draw_rounded_rect(x, y, 14, 14, 2, fill=C["bg_input"] if not checked else C["accent_primary"], outline=box_color)
    if checked:
        draw_text(x + 2, y - 1, "✓", font_small, (255,255,255))
    draw_text(x + 20, y, label, font_body, C["text_secondary"])

def draw_button(x, y, w, h, text, style="default"):
    """绘制按钮"""
    colors = {
        "default": (C["bg_panel"], C["border_default"], C["text_secondary"]),
        "primary": (C["btn_primary"], C["btn_primary"], (255,255,255)),
        "warning": (C["btn_warning"], C["btn_warning"], (0,0,0)),
        "danger": (C["btn_danger"], C["btn_danger"], (255,255,255)),
    }
    bg, border, text_color = colors.get(style, colors["default"])
    draw_rounded_rect(x, y, w, h, 4, fill=bg, outline=border)
    # 文字居中
    draw_text(x + 8, y + (h-14)//2, text, font_body, text_color)

# ============================================
# 菜单栏
# ============================================
draw_rect(0, 0, WIDTH, MENUBAR_H, fill=C["bg_secondary"])
draw.line([(0, MENUBAR_H), (WIDTH, MENUBAR_H)], fill=C["border_default"])

draw_text(12, 6, "ZCCAD - SignMaker Slicer", font_title, C["text_primary"])
menus = ["文件", "编辑", "视图", "工具", "帮助"]
menu_x = 200
for m in menus:
    draw_text(menu_x, 6, m, font_body, C["text_secondary"])
    menu_x += 50

# ============================================
# 工具栏 (两行)
# ============================================
toolbar_y = MENUBAR_H
draw_rect(0, toolbar_y, WIDTH, TOOLBAR_H, fill=C["bg_secondary"])
draw.line([(0, toolbar_y + TOOLBAR_H), (WIDTH, toolbar_y + TOOLBAR_H)], fill=C["border_default"])

# 第一行工具
row1_tools = [
    ("打开", "default"), ("保存", "default"), ("|", ""),
    ("导入", "default"), ("导出", "default"), ("|", ""),
    ("结合", "default"), ("打散", "default"), ("|", ""),
    ("旋转", "default"), ("镜像", "default"), ("|", ""),
    ("机器版面", "default"), ("宽", "input"), ("800", "value"), ("高", "input"), ("800", "value"), ("|", ""),
    ("到页面", "default"), ("页面中心", "default"), ("|", ""),
    ("三维预览", "primary"), ("语言", "default"),
]

tool_x = 70
tool_y = toolbar_y + 6
for item, style in row1_tools:
    if item == "|":
        draw.line([(tool_x, tool_y + 4), (tool_x, tool_y + 26)], fill=C["border_default"])
        tool_x += 12
    elif style == "input":
        draw_text(tool_x, tool_y + 6, item, font_small, C["text_muted"])
        tool_x += 20
    elif style == "value":
        draw_input(tool_x, tool_y + 2, 50, item)
        tool_x += 60
    else:
        draw_button(tool_x, tool_y, 52, 28, item, style)
        tool_x += 58

# 第二行工具
row2_tools = [
    ("排版", "default"), ("填充", "primary"), ("底孔", "default"), ("|", ""),
    ("起始点编辑", "default"), ("连襟取消", "default"), ("打印顺序", "default"), ("|", ""),
    ("面板选择", "default"), ("2号", "default"), ("3号", "default"), ("|", ""),
    ("WiFi传输", "default"), ("输出打开", "warning"),
]

tool_x = 70
tool_y = toolbar_y + 42
for item, style in row2_tools:
    if item == "|":
        draw.line([(tool_x, tool_y + 4), (tool_x, tool_y + 26)], fill=C["border_default"])
        tool_x += 12
    else:
        w = len(item) * 11 + 16
        draw_button(tool_x, tool_y, w, 28, item, style)
        tool_x += w + 6

# ============================================
# 左侧工具箱
# ============================================
content_y = MENUBAR_H + TOOLBAR_H
content_h = HEIGHT - content_y - STATUSBAR_H

draw_rect(0, content_y, SIDEBAR_LEFT_W, content_h, fill=C["bg_secondary"])
draw.line([(SIDEBAR_LEFT_W, content_y), (SIDEBAR_LEFT_W, content_y + content_h)], fill=C["border_default"])

# 工具图标
tools_icons = ["✥", "☐", "▢", "◇", "✎", "⊕", "⊖", "↺", "⤢", "▲"]
icon_y = content_y + 10
for icon in tools_icons:
    draw_rounded_rect(10, icon_y, 40, 36, 4, fill=C["bg_panel"], outline=C["border_default"])
    draw_text(22, icon_y + 10, icon, font_title, C["text_secondary"])
    icon_y += 44

# ============================================
# 中央画布
# ============================================
canvas_x = SIDEBAR_LEFT_W + 1
canvas_w = WIDTH - SIDEBAR_LEFT_W - SIDEBAR_RIGHT_W - 2
canvas_y = content_y
canvas_h = content_h

draw_rect(canvas_x, canvas_y, canvas_w, canvas_h, fill=C["canvas_bg"])

# 网格
grid_color = (30, 35, 42)
for gx in range(canvas_x, canvas_x + canvas_w, 40):
    draw.line([(gx, canvas_y), (gx, canvas_y + canvas_h)], fill=grid_color)
for gy in range(canvas_y, canvas_y + canvas_h, 40):
    draw.line([(canvas_x, gy), (canvas_x + canvas_w, gy)], fill=grid_color)

# 机器版面边框
margin = 60
draw_rounded_rect(canvas_x + margin, canvas_y + margin,
                  canvas_w - margin*2, canvas_h - margin*2, 0,
                  outline=C["accent_error"])

# 字形
center_x = canvas_x + canvas_w // 2
center_y = canvas_y + canvas_h // 2
draw_text(center_x - 50, center_y - 60, "发", font_large, C["accent_primary"])

# 起点标记
draw.ellipse([center_x - 45, center_y - 55, center_x - 35, center_y - 45], fill=C["accent_success"])

# 坐标显示
draw_rounded_rect(canvas_x + 10, canvas_y + canvas_h - 40, 140, 28, 4, fill=C["bg_panel"])
draw_text(canvas_x + 20, canvas_y + canvas_h - 34, "X: 245.5  Y: 189.2", font_mono, C["text_muted"])

# ============================================
# 右侧参数面板 - 输出设置
# ============================================
right_x = WIDTH - SIDEBAR_RIGHT_W
draw_rect(right_x, content_y, SIDEBAR_RIGHT_W, content_h, fill=C["bg_secondary"])
draw.line([(right_x, content_y), (right_x, content_y + content_h)], fill=C["border_default"])

# 面板标题
draw_rect(right_x, content_y, SIDEBAR_RIGHT_W, 28, fill=C["bg_panel"])
draw_text(right_x + 12, content_y + 6, "输出", font_title, C["text_primary"])

# 标签页
tabs = ["字壳工艺", "换色层数", "台阶V槽", "防翘裙边", "连襟字", "包边勾边", "面板打印", "生成底板"]
tab_y = content_y + 32
tab_x = right_x
tab_w = SIDEBAR_RIGHT_W // 4
for i, tab in enumerate(tabs):
    row = i // 4
    col = i % 4
    tx = right_x + col * tab_w
    ty = tab_y + row * 26

    if i == 0:  # 选中的标签
        draw_rect(tx, ty, tab_w, 24, fill=C["bg_panel"])
        draw.line([(tx, ty + 23), (tx + tab_w, ty + 23)], fill=C["accent_primary"], width=2)
        draw_text(tx + 8, ty + 5, tab, font_small, C["text_primary"])
    else:
        draw_text(tx + 8, ty + 5, tab, font_small, C["text_muted"])

# 参数内容区
panel_y = tab_y + 56
panel_h = content_h - 120

draw_rect(right_x, panel_y, SIDEBAR_RIGHT_W, panel_h, fill=C["bg_panel"])

# ============================================
# 字壳工艺 参数
# ============================================
py = panel_y + 12
px_left = right_x + 12
px_right = right_x + SIDEBAR_RIGHT_W // 2 + 10

# 异形边选择
draw_text(px_left, py, "异形边选择", font_body, C["text_secondary"])
py += 22

# 预览图
draw_rounded_rect(px_left, py, 80, 60, 4, fill=C["bg_secondary"], outline=C["border_default"])
draw.line([(px_left + 40, py + 5), (px_left + 40, py + 55)], fill=C["accent_error"], width=2)

# 按钮
draw_button(px_left + 90, py, 50, 24, "添加", "primary")
draw_button(px_left + 145, py + 0, 50, 24, "选中", "default")
draw_button(px_left + 200, py + 0, 50, 24, "删除", "danger")

py += 70

# 字壳工艺标题
draw_text(px_left, py, "字壳工艺", font_title, C["text_primary"])
py += 24

# 镜像/正常打印
draw_text(px_left, py, "○ 镜像打印", font_body, C["text_secondary"])
draw_text(px_left + 90, py, "● 正常打印", font_body, C["accent_primary"])
py += 26

# 左列参数
params_left = [
    ("字边类型", "直边", True, False),
    ("字壳高度", "30", False, False),
    ("斜边宽度", "0", False, False),
    ("面板厚度", "2", False, False),
    ("底板厚度", "10", False, False),
    ("层高", "0.3", False, True),
    ("预打边线偏", "15", False, True),
    ("预打边线次", "2", False, False),
]

# 右列参数
params_right = [
    ("雕刻刀刃", "0.4", False, False),
    ("壁厚", "1.2", False, False),
    ("壁厚补偿", "0", False, True),
    ("走线次数", "1", False, False),
    ("走线高度", "0", False, True),
    ("走线偏移", "0.8", False, True),
    ("字芯高度", "0", False, True),
    ("字芯斜边宽度", "0", False, True),
]

param_y = py
for (label, value, is_dropdown, highlight) in params_left:
    draw_text(px_left, param_y + 4, label, font_body, C["text_secondary"])
    if is_dropdown:
        draw_rounded_rect(px_left + 75, param_y, 70, 22, 3, fill=C["bg_input"], outline=C["border_default"])
        draw_text(px_left + 82, param_y + 4, value, font_mono, C["text_primary"])
        draw_text(px_left + 130, param_y + 4, "▼", font_small, C["text_muted"])
    else:
        draw_input(px_left + 75, param_y, 50, value, "mm", highlight)
    param_y += 28

param_y = py
for (label, value, is_dropdown, highlight) in params_right:
    draw_text(px_right, param_y + 4, label, font_body, C["text_secondary"])
    draw_input(px_right + 75, param_y, 50, value, "mm", highlight)
    param_y += 28

# ============================================
# 底部按钮区
# ============================================
btn_y = content_y + content_h - 50
draw_rect(right_x, btn_y - 10, SIDEBAR_RIGHT_W, 60, fill=C["bg_secondary"])

# 计算路径按钮
draw_button(right_x + 12, btn_y, 80, 32, "计算路径", "primary")

# 进度条
draw_rounded_rect(right_x + 100, btn_y + 8, 100, 16, 3, fill=C["bg_panel"], outline=C["border_default"])

# 预览和输出按钮
draw_button(right_x + 215, btn_y, 90, 32, "预览字边类型", "warning")
draw_button(right_x + 315, btn_y, 90, 32, "文件输出", "danger")

# ============================================
# 状态栏
# ============================================
status_y = HEIGHT - STATUSBAR_H
draw_rect(0, status_y, WIDTH, STATUSBAR_H, fill=C["bg_secondary"])
draw.line([(0, status_y), (WIDTH, status_y)], fill=C["border_default"])

draw_text(12, status_y + 6, "就绪 | 图形: 1个", font_small, C["text_muted"])
draw_text(WIDTH - 300, status_y + 6, "打印时间: 1h 45m | 耗材: 89.5m | 版本 1.0.0", font_small, C["text_muted"])

# ============================================
# 保存
# ============================================
output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "UI_Mockup_V2.png")
img.save(output_path, "PNG", quality=95)
print(f"Saved: {output_path}")

root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Mockup_V2.png")
img.save(root_path, "PNG", quality=95)
print(f"Saved: {root_path}")
