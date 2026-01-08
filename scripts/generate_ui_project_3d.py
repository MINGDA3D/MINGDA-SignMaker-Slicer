"""
SignMaker Slicer - 项目模式 3D视图 效果图
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
    "extruder_1": "#3B82F6",
    "extruder_2": "#EC4899",
    "extruder_3": "#F59E0B",
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

img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_base"])
draw = ImageDraw.Draw(img)

# 字体
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

def draw_rounded_rect(x, y, w, h, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline, width=width)

def draw_text(x, y, text, font=None, fill=None):
    draw.text((x, y), text, font=font or font_body, fill=fill or C["text_secondary"])

def draw_gradient_rect(x, y, w, h):
    for i in range(w):
        ratio = i / w
        color = tuple(int(C["accent_primary"][j] + (C["accent_secondary"][j] - C["accent_primary"][j]) * ratio) for j in range(3))
        draw.line([(x + i, y), (x + i, y + h)], fill=color)

# 布局常量
HEADER_H = 48
SIDEBAR_LEFT_W = 240
SIDEBAR_RIGHT_W = 340
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

file_tools = [("📂", "打开"), ("💾", "保存"), ("📥", "导入"), ("📤", "导出")]
ftx = 24
for icon, tip in file_tools:
    draw_rounded_rect(ftx, toolbar_y + 4, 44, 28, 6, fill=C["bg_elevated"])
    draw_text(ftx + 14, toolbar_y + 10, icon, font_icon, C["text_secondary"])
    ftx += 52

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
draw_text(90, shape_y + 18, "+ 导入图形", font_body, C["text_muted"])

# ============================================
# 中央画布 - 3D视图
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

# 2D/3D切换 - 3D激活状态
view_x = canvas_x + canvas_w - 180
draw_rounded_rect(view_x, canvas_toolbar_y + 6, 100, 28, 6, fill=C["bg_elevated"])
draw_text(view_x + 15, canvas_toolbar_y + 12, "2D", font_body, C["text_muted"])
draw.line([(view_x + 50, canvas_toolbar_y + 12), (view_x + 50, canvas_toolbar_y + 28)], fill=C["border_default"])
# 3D激活
draw_rounded_rect(view_x + 55, canvas_toolbar_y + 8, 40, 24, 4, fill=C["accent_primary"])
draw_text(view_x + 65, canvas_toolbar_y + 12, "3D", font_body, (255,255,255))

# 3D画布内容区
inner_canvas_y = canvas_toolbar_y + 56
inner_canvas_h = canvas_h - 120

draw_rounded_rect(canvas_x + 20, inner_canvas_y, canvas_w - 40, inner_canvas_h, 8, fill=C["bg_base"])

# 3D网格地面 (透视效果)
grid_center_x = canvas_x + canvas_w // 2
grid_center_y = inner_canvas_y + inner_canvas_h - 100

# 绘制透视网格
grid_color = C["grid_3d"]
vanish_y = inner_canvas_y + 50  # 消失点

# 横向网格线 (透视)
for i in range(12):
    y_pos = grid_center_y - i * 18
    # 随着距离变远，线条逐渐收窄
    shrink = 1 - (i * 0.05)
    half_width = int(350 * shrink)
    if y_pos > vanish_y:
        alpha = max(0.2, 1 - i * 0.08)
        line_color = tuple(int(c * alpha) for c in grid_color)
        draw.line([(grid_center_x - half_width, y_pos),
                   (grid_center_x + half_width, y_pos)], fill=line_color, width=1)

# 纵向网格线 (透视 - 向消失点汇聚)
for i in range(-7, 8):
    bottom_x = grid_center_x + i * 50
    # 计算顶部位置 (向消失点汇聚)
    top_x = grid_center_x + int(i * 15)
    draw.line([(bottom_x, grid_center_y), (top_x, vanish_y + 100)], fill=grid_color, width=1)

# ============================================
# 绘制3D字壳模型 - "发"字
# ============================================
cx = grid_center_x
cy = inner_canvas_y + inner_canvas_h // 2 - 20

# 字壳3D效果 - 多层堆叠
shell_width = 140
shell_height = 180
shell_depth = 80  # 3D深度

# 从底层到顶层绘制
layers = 8
for layer in range(layers):
    # 计算每层的偏移和颜色
    layer_offset = layer * (shell_depth // layers)
    layer_ratio = layer / (layers - 1)

    # 颜色渐变: 底部深蓝 -> 顶部青色
    r = int(C["layer_base"][0] + (C["layer_top"][0] - C["layer_base"][0]) * layer_ratio)
    g = int(C["layer_base"][1] + (C["layer_top"][1] - C["layer_base"][1]) * layer_ratio)
    b = int(C["layer_base"][2] + (C["layer_top"][2] - C["layer_base"][2]) * layer_ratio)
    layer_color = (r, g, b)

    # 外边框颜色
    border_color = C["accent_primary"] if layer == layers - 1 else tuple(int(c * 0.7) for c in layer_color)

    # 3D透视偏移
    x_offset = -layer_offset // 3
    y_offset = -layer_offset

    # 绘制层
    left = cx - shell_width // 2 + x_offset
    top = cy - shell_height // 2 + y_offset
    right = cx + shell_width // 2 + x_offset
    bottom = cy + shell_height // 2 + y_offset

    # 绘制圆角矩形层
    draw_rounded_rect(left, top, shell_width, shell_height, 8, fill=layer_color, outline=border_color)

# 绘制斜边效果 (左侧面)
left_face = [
    (cx - shell_width // 2, cy + shell_height // 2),  # 底部左前
    (cx - shell_width // 2 - shell_depth // 3, cy + shell_height // 2 - shell_depth),  # 底部左后
    (cx - shell_width // 2 - shell_depth // 3, cy - shell_height // 2 - shell_depth),  # 顶部左后
    (cx - shell_width // 2, cy - shell_height // 2),  # 顶部左前
]
draw.polygon(left_face, fill=C["layer_mid"], outline=C["accent_primary"])

# 绘制斜边效果 (底部面)
bottom_face = [
    (cx - shell_width // 2, cy + shell_height // 2),  # 底部左前
    (cx + shell_width // 2, cy + shell_height // 2),  # 底部右前
    (cx + shell_width // 2 - shell_depth // 3, cy + shell_height // 2 - shell_depth),  # 底部右后
    (cx - shell_width // 2 - shell_depth // 3, cy + shell_height // 2 - shell_depth),  # 底部左后
]
draw.polygon(bottom_face, fill=C["layer_base"], outline=C["accent_primary"])

# 顶面高亮
top_face_color = C["layer_top"]
draw_rounded_rect(cx - shell_width // 2 - shell_depth // 3,
                  cy - shell_height // 2 - shell_depth,
                  shell_width, shell_height, 8,
                  fill=top_face_color, outline=C["accent_secondary"])

# 在顶面绘制"发"字轮廓
draw_text(cx - 35 - shell_depth // 3, cy - 45 - shell_depth, "发",
          ImageFont.truetype("msyh.ttc", 60) if os.path.exists("C:\\Windows\\Fonts\\msyh.ttc") else font_large,
          C["bg_base"])

# 台阶标注
# 底部台阶
step_y1 = cy + shell_height // 2 - 15
draw.line([(cx + shell_width // 2 + 20, step_y1), (cx + shell_width // 2 + 80, step_y1)],
          fill=C["warning"], width=2)
draw.line([(cx + shell_width // 2 + 20, step_y1 - 5), (cx + shell_width // 2 + 20, step_y1 + 5)],
          fill=C["warning"], width=2)
draw_text(cx + shell_width // 2 + 90, step_y1 - 8, "底板台阶 5mm", font_small, C["warning"])

# 顶部台阶
step_y2 = cy - shell_height // 2 - shell_depth + 15
draw.line([(cx + shell_width // 2 - shell_depth // 3 + 20, step_y2),
           (cx + shell_width // 2 - shell_depth // 3 + 80, step_y2)],
          fill=C["warning"], width=2)
draw.line([(cx + shell_width // 2 - shell_depth // 3 + 20, step_y2 - 5),
           (cx + shell_width // 2 - shell_depth // 3 + 20, step_y2 + 5)],
          fill=C["warning"], width=2)
draw_text(cx + shell_width // 2 - shell_depth // 3 + 90, step_y2 - 8, "面板台阶 27mm", font_small, C["warning"])

# 尺寸标注 - 高度
dim_x = cx - shell_width // 2 - shell_depth // 3 - 50
draw.line([(dim_x, cy + shell_height // 2), (dim_x, cy - shell_height // 2 - shell_depth)],
          fill=C["text_muted"], width=1)
draw.line([(dim_x - 5, cy + shell_height // 2), (dim_x + 5, cy + shell_height // 2)],
          fill=C["text_muted"], width=1)
draw.line([(dim_x - 5, cy - shell_height // 2 - shell_depth), (dim_x + 5, cy - shell_height // 2 - shell_depth)],
          fill=C["text_muted"], width=1)
draw_text(dim_x - 45, cy - 10, "30mm", font_small, C["text_muted"])

# 3D视图控制提示
draw_rounded_rect(canvas_x + canvas_w - 200, inner_canvas_y + 10,
                  170, 30, 6, fill=C["bg_card"])
draw_text(canvas_x + canvas_w - 190, inner_canvas_y + 16, "🖱 拖拽旋转 | 滚轮缩放", font_small, C["text_muted"])

# 视图快捷按钮
view_btns = ["正", "俯", "侧", "透"]
vbx = canvas_x + 30
vby = inner_canvas_y + inner_canvas_h - 50
for i, btn in enumerate(view_btns):
    active = btn == "透"
    if active:
        draw_rounded_rect(vbx, vby, 36, 36, 6, fill=C["accent_primary"])
        draw_text(vbx + 12, vby + 10, btn, font_body, (255,255,255))
    else:
        draw_rounded_rect(vbx, vby, 36, 36, 6, fill=C["bg_card"])
        draw_text(vbx + 12, vby + 10, btn, font_body, C["text_secondary"])
    vbx += 44

# 坐标轴指示器
axis_x = canvas_x + 40
axis_y = inner_canvas_y + 60
# X轴 (红)
draw.line([(axis_x, axis_y), (axis_x + 30, axis_y)], fill=(239, 68, 68), width=2)
draw_text(axis_x + 32, axis_y - 6, "X", font_small, (239, 68, 68))
# Y轴 (绿)
draw.line([(axis_x, axis_y), (axis_x, axis_y - 30)], fill=(34, 197, 94), width=2)
draw_text(axis_x - 4, axis_y - 45, "Y", font_small, (34, 197, 94))
# Z轴 (蓝)
draw.line([(axis_x, axis_y), (axis_x - 20, axis_y + 15)], fill=(59, 130, 246), width=2)
draw_text(axis_x - 35, axis_y + 12, "Z", font_small, (59, 130, 246))

# 底部信息栏
info_y = inner_canvas_y + inner_canvas_h + 8
draw_rounded_rect(canvas_x + 20, info_y, canvas_w - 40, 36, 8, fill=C["bg_card"])
draw_text(canvas_x + 36, info_y + 10, "尺寸: 120 × 150 × 30 mm", font_small, C["text_muted"])
draw_text(canvas_x + 220, info_y + 10, "缩放: 100%", font_small, C["text_muted"])
draw_text(canvas_x + 340, info_y + 10, "视角: 透视", font_mono, C["accent_secondary"])

# 缩放控制
zoom_x = canvas_x + canvas_w - 160
draw_rounded_rect(zoom_x, info_y + 6, 120, 24, 6, fill=C["bg_elevated"])
draw_text(zoom_x + 10, info_y + 10, "−", font_h2, C["text_muted"])
draw_rounded_rect(zoom_x + 35, info_y + 8, 50, 20, 4, fill=C["bg_card"])
draw_text(zoom_x + 95, info_y + 10, "+", font_h2, C["text_muted"])

# ============================================
# 右侧参数面板
# ============================================
right_x = WIDTH - SIDEBAR_RIGHT_W
draw_rounded_rect(right_x + 8, content_y + 8, SIDEBAR_RIGHT_W - 16, content_h - 16, 12, fill=C["bg_secondary"])

draw_text(right_x + 24, content_y + 24, "参数设置", font_h1, C["text_primary"])

# 快速设置卡片
card_y = content_y + 60
draw_rounded_rect(right_x + 16, card_y, SIDEBAR_RIGHT_W - 32, 80, 10, fill=C["bg_card"])

quick_params = [
    ("字壳高度", "30", "mm"),
    ("壁厚", "1.2", "mm"),
    ("层高", "0.3", "mm"),
]
qp_x = right_x + 28
for label, value, unit in quick_params:
    draw_text(qp_x, card_y + 12, label, font_small, C["text_muted"])
    draw_rounded_rect(qp_x, card_y + 30, 70, 32, 6, fill=C["bg_elevated"])
    draw_text(qp_x + 10, card_y + 38, value, font_mono, C["text_primary"])
    draw_text(qp_x + 50, card_y + 40, unit, font_small, C["text_muted"])
    qp_x += 100

# 参数分组
sections = [
    ("字壳工艺", True, [
        ("字边类型", "斜边", "select"),
        ("斜边宽度", "5", "mm"),
        ("底板厚度", "10", "mm"),
    ]),
    ("换色层设置", False, []),
    ("台阶/V槽", False, []),
    ("防翘裙边", False, []),
    ("连襟字", False, []),
    ("面板打印", False, []),
]

section_y = card_y + 100
for section_name, expanded, params in sections:
    draw_rounded_rect(right_x + 16, section_y, SIDEBAR_RIGHT_W - 32, 40, 8, fill=C["bg_card"])

    indicator = "▼" if expanded else "▶"
    draw_text(right_x + 28, section_y + 12, indicator, font_small, C["accent_primary"] if expanded else C["text_muted"])
    draw_text(right_x + 48, section_y + 12, section_name, font_h2, C["text_primary"])

    section_y += 48

    if expanded and params:
        draw_rounded_rect(right_x + 16, section_y, SIDEBAR_RIGHT_W - 32, len(params) * 44 + 16, 8, fill=C["bg_elevated"])

        param_y = section_y + 12
        for label, value, unit in params:
            draw_text(right_x + 28, param_y + 6, label, font_body, C["text_secondary"])

            if unit == "select":
                draw_rounded_rect(right_x + 150, param_y, 130, 28, 6, fill=C["bg_card"], outline=C["border_default"])
                draw_text(right_x + 162, param_y + 6, value, font_body, C["text_primary"])
                draw_text(right_x + 260, param_y + 6, "▼", font_small, C["text_muted"])
            else:
                draw_rounded_rect(right_x + 150, param_y, 90, 28, 6, fill=C["bg_card"], outline=C["border_default"])
                draw_text(right_x + 162, param_y + 6, value, font_mono, C["text_primary"])
                draw_text(right_x + 250, param_y + 8, unit, font_small, C["text_muted"])

            param_y += 40

        section_y += len(params) * 44 + 24

    section_y += 8

# 输出统计
footer_y = HEIGHT - FOOTER_H - 60
draw_rounded_rect(right_x + 16, footer_y, SIDEBAR_RIGHT_W - 32, 50, 8, fill=C["bg_card"])
draw_text(right_x + 28, footer_y + 8, "预计打印时间", font_small, C["text_muted"])
draw_text(right_x + 28, footer_y + 26, "2h 15min", font_h2, C["accent_secondary"])
draw_text(right_x + 150, footer_y + 8, "耗材用量", font_small, C["text_muted"])
draw_text(right_x + 150, footer_y + 26, "125.8m", font_h2, C["accent_secondary"])

# 主按钮
btn_y = footer_y + 60
draw_gradient_rect(right_x + 16, btn_y, SIDEBAR_RIGHT_W - 32, 44)
draw_rounded_rect(right_x + 16, btn_y, SIDEBAR_RIGHT_W - 32, 44, 10, outline=None)
draw_text(right_x + 100, btn_y + 12, "生成 G-Code", font_h2, (255,255,255))

# 次要按钮
btn2_y = btn_y + 54
draw_rounded_rect(right_x + 16, btn2_y, 150, 38, 8, fill=C["bg_card"], outline=C["border_default"])
draw_text(right_x + 50, btn2_y + 10, "预览切片", font_body, C["text_secondary"])

draw_rounded_rect(right_x + 176, btn2_y, 150, 38, 8, fill=C["bg_card"], outline=C["border_default"])
draw_text(right_x + 215, btn2_y + 10, "导出文件", font_body, C["text_secondary"])

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

output_path = os.path.join(output_dir, "UI_Modern_3D.png")
img.save(output_path, "PNG", quality=95)
print(f"Saved: {output_path}")

root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Modern_3D.png")
img.save(root_path, "PNG", quality=95)
print(f"Saved: {root_path}")
