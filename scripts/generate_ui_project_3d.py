"""
SignMaker Slicer - 项目模式 3D视图 效果图
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

# 左上角Logo
logo_path = os.path.join(os.path.dirname(__file__), "..", "docs", "images", "MINGDA_logo.png")
logo = load_icon(logo_path, 32)
if logo:
    img.paste(logo, (16, 8), logo)
    draw_text(56, 14, "SignMaker", font_h1, C["text_primary"])
    draw_text(138, 16, "Slicer", font_h2, C["accent_secondary"])
else:
    # 没有logo时显示原样式
    draw_gradient_rect(16, 12, 4, 24)
    draw_text(28, 14, "SignMaker", font_h1, C["text_primary"])
    draw_text(110, 16, "Slicer", font_h2, C["accent_secondary"])

# 中央导航标签页 - 参考UI_Home样式
nav_items = [("首页", False), ("项目", True), ("预览", False)]
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

# 图标目录
icons_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "images")

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
    # 删除图标
    delete_icon_path = os.path.join(icons_dir, "delete.png")
    delete_icon = load_icon(delete_icon_path, 16)
    if delete_icon:
        img.paste(delete_icon, (SIDEBAR_LEFT_W - 44, shape_y + 14), delete_icon)
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

# 顶部画布工具栏
canvas_toolbar_y = canvas_y + 16
draw_rounded_rect(canvas_x + 20, canvas_toolbar_y, canvas_w - 40, 48, 8, fill=C["bg_card"])

# 图标目录
icons_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "images")

# 工具栏图标配置 (图标文件名, 是否激活)
toolbar_icons = [
    ("move.png", False),     # 移动
    ("rotate.png", False),   # 旋转
    ("scale.png", False),    # 缩放
]

etx = canvas_x + 28
icon_size = 32

# 编辑工具组1 - 变换操作 (移动/旋转/缩放)
for icon_file, active in toolbar_icons:
    icon_path = os.path.join(icons_dir, icon_file)
    icon = load_icon(icon_path, icon_size)
    
    if active:
        draw_rounded_rect(etx, canvas_toolbar_y + 8, 40, 32, 6, fill=C["accent_primary"])
    
    if icon:
        # 粘贴图标到画布
        icon_x = etx + 4
        icon_y = canvas_toolbar_y + 8
        img.paste(icon, (icon_x, icon_y), icon)
    
    etx += 48

# 分隔线
draw.line([(etx + 4, canvas_toolbar_y + 10), (etx + 4, canvas_toolbar_y + 38)], fill=C["border_default"])
etx += 20

# 编辑工具组2 - 镜像操作
mirror_icons = [("mirror_x.png", "水平"), ("mirror_y.png", "垂直")]
for icon_file, label in mirror_icons:
    icon_path = os.path.join(icons_dir, icon_file)
    icon = load_icon(icon_path, icon_size)
    if icon:
        img.paste(icon, (etx + 4, canvas_toolbar_y + 8), icon)
    etx += 44

# 分隔线
draw.line([(etx + 4, canvas_toolbar_y + 10), (etx + 4, canvas_toolbar_y + 38)], fill=C["border_default"])
etx += 20

# 编辑工具组3 - 组合操作
group_icons = [("组合.png", "组合"), ("split_objects_dark.png", "打散")]
for icon_file, label in group_icons:
    icon_path = os.path.join(icons_dir, icon_file)
    icon = load_icon(icon_path, icon_size)
    if icon:
        img.paste(icon, (etx + 4, canvas_toolbar_y + 8), icon)
    etx += 44

# 分隔线
draw.line([(etx + 4, canvas_toolbar_y + 10), (etx + 4, canvas_toolbar_y + 38)], fill=C["border_default"])
etx += 20

# 编辑工具组4 - 排版操作
layout_icons = [("画面中心.png", "页面中心"), ("arrange.png", "自动排版")]
for icon_file, label in layout_icons:
    icon_path = os.path.join(icons_dir, icon_file)
    icon = load_icon(icon_path, icon_size)
    if icon:
        img.paste(icon, (etx + 4, canvas_toolbar_y + 8), icon)
    etx += 44

# 分隔线
draw.line([(etx + 4, canvas_toolbar_y + 10), (etx + 4, canvas_toolbar_y + 38)], fill=C["border_default"])
etx += 20

# 编辑工具组5 - 起始点设置
icon_path = os.path.join(icons_dir, "起始点.png")
icon = load_icon(icon_path, icon_size)
if icon:
    img.paste(icon, (etx + 4, canvas_toolbar_y + 8), icon)
etx += 44

# 编辑工具组6 - 底孔
icon_path = os.path.join(icons_dir, "bottom_hole.png")
icon = load_icon(icon_path, icon_size)
if icon:
    img.paste(icon, (etx + 4, canvas_toolbar_y + 8), icon)
etx += 44

# 编辑工具组7 - 打印顺序编辑
icon_path = os.path.join(icons_dir, "顺序.png")
icon = load_icon(icon_path, icon_size)
if icon:
    img.paste(icon, (etx + 4, canvas_toolbar_y + 8), icon)
etx += 44

# 视图切换 (最右侧) - 3D激活状态
view_x = canvas_x + canvas_w - 110  # 工具栏右边距
draw_text(view_x + 12, canvas_toolbar_y + 16, "2D", font_body, C["text_muted"])
draw.line([(view_x + 40, canvas_toolbar_y + 12), (view_x + 40, canvas_toolbar_y + 36)], fill=C["border_default"])
# 3D激活
draw_text(view_x + 52, canvas_toolbar_y + 16, "3D", font_body, C["accent_primary"])

# 3D画布内容区
inner_canvas_y = canvas_toolbar_y + 56
inner_canvas_h = canvas_h - 120

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

# 3D网格地面 (透视效果) - 机器尺寸800×1200mm，每格40mm
grid_center_x = canvas_x + canvas_w // 2
grid_center_y = inner_canvas_y + inner_canvas_h - 80

# 绘制透视网格
grid_color = C["grid_3d"]
vanish_y = inner_canvas_y + 30  # 消失点

# 网格参数：800×1200mm，40mm一格
# X方向(宽度): 800/40 = 20格，21条线
# Y方向(深度): 1200/40 = 30格，用透视效果只显示部分
grid_base_width = 360  # 底部宽度（对应800mm）
grid_depth_lines = 16  # 深度方向显示的线数

# 横向网格线 (透视) - Y方向深度
grid_step_y = (grid_center_y - vanish_y - 60) / grid_depth_lines
for i in range(grid_depth_lines + 1):
    y_pos = int(grid_center_y - i * grid_step_y)
    # 随着距离变远，线条逐渐收窄（透视效果）
    shrink = 1 - (i / grid_depth_lines) * 0.6
    half_width = int(grid_base_width * shrink)
    if y_pos > vanish_y:
        alpha = max(0.3, 1 - i * 0.05)
        line_color = tuple(int(c * alpha) for c in grid_color)
        draw.line([(grid_center_x - half_width, y_pos),
                   (grid_center_x + half_width, y_pos)], fill=line_color, width=1)

# 纵向网格线 (透视 - 向消失点汇聚) - X方向20格
grid_lines_x = 21  # 800/40=20格，21条线
for i in range(grid_lines_x):
    # 底部位置：均匀分布
    ratio = (i / (grid_lines_x - 1)) - 0.5  # -0.5 到 0.5
    bottom_x = grid_center_x + int(ratio * 2 * grid_base_width)
    # 顶部位置：向消失点汇聚
    top_x = grid_center_x + int(ratio * 2 * grid_base_width * 0.4)
    top_y = int(grid_center_y - grid_depth_lines * grid_step_y)
    draw.line([(bottom_x, grid_center_y), (top_x, top_y)], fill=grid_color, width=1)

# ============================================
# 绘制3D字壳模型 - "发"字 (简单3D效果)
# ============================================
cx = grid_center_x
cy = inner_canvas_y + inner_canvas_h // 2 - 30

char_font = ImageFont.truetype("msyh.ttc", 120) if os.path.exists("C:\\Windows\\Fonts\\msyh.ttc") else font_large

# 简单3D效果 - 向右下的立体阴影
shadow_color = C["layer_base"]
for i in range(8, 0, -1):
    draw_text(cx - 60 + i, cy - 60 + i, "发", char_font, shadow_color)

# 顶层 - 青色描边
stroke_color = C["accent_primary"]
for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
    draw_text(cx - 60 + offset[0], cy - 60 + offset[1], "发", char_font, stroke_color)

# 顶层填充
draw_text(cx - 60, cy - 60, "发", char_font, C["layer_top"])

# 底部信息栏
info_y = inner_canvas_y + inner_canvas_h + 8
draw_rounded_rect(canvas_x + 20, info_y, canvas_w - 40, 36, 8, fill=C["bg_card"])
draw_text(canvas_x + 36, info_y + 10, "尺寸: 120 × 150 × 30 mm", font_small, C["text_muted"])
draw_text(canvas_x + 220, info_y + 10, "缩放: 100%", font_small, C["text_muted"])
draw_text(canvas_x + 340, info_y + 10, "坐标: X 125.5  Y 89.2  Z 15.0", font_small, C["text_muted"])

# 缩放控制
zoom_x = canvas_x + canvas_w - 160
draw_rounded_rect(zoom_x, info_y + 6, 120, 24, 6, fill=C["bg_elevated"])
draw_text(zoom_x + 10, info_y + 10, "−", font_h2, C["text_muted"])
draw_rounded_rect(zoom_x + 35, info_y + 8, 50, 20, 4, fill=C["bg_card"])
draw_text(zoom_x + 95, info_y + 10, "+", font_h2, C["text_muted"])

# ============================================
# 右侧属性面板 - 现代卡片式设计
# ============================================
right_x = WIDTH - SIDEBAR_RIGHT_W
# 面板高度减小，给底部按钮留出空间
draw_rounded_rect(right_x + 8, content_y + 8, SIDEBAR_RIGHT_W - 16, content_h - 80, 12, fill=C["bg_secondary"])

# 面板标题
draw_text(right_x + 24, content_y + 24, "参数设置", font_h1, C["text_primary"])

# ============================================
# 预设模板区域 - 简约下拉选择器
# ============================================
preset_y = content_y + 50

# 预设模板容器背景（包含标题和内容）
preset_content_h = 200  # 包含标题、下拉选择器、常用标签、快速参数
draw_rounded_rect(right_x + 16, preset_y, SIDEBAR_RIGHT_W - 32, preset_content_h, 8, fill=C["bg_card"])

# 预设模板标题栏 - 用polygon绘制向下三角形
tri_x = right_x + 28
tri_y = preset_y + 14
draw.polygon([(tri_x, tri_y), (tri_x + 10, tri_y), (tri_x + 5, tri_y + 6)], fill=C["accent_primary"])
draw_text(right_x + 48, preset_y + 10, "预设模板", font_h2, C["text_primary"])

# 简洁下拉选择器
preset_select_y = preset_y + 40
draw_rounded_rect(right_x + 24, preset_select_y, SIDEBAR_RIGHT_W - 48, 36, 8, fill=C["bg_elevated"], outline=C["border_default"])
draw_text(right_x + 36, preset_select_y + 10, "30cm勾边字", font_body, C["text_primary"])
# 下拉三角形
dropdown_tri_x = right_x + SIDEBAR_RIGHT_W - 56
dropdown_tri_y = preset_select_y + 14
draw.polygon([(dropdown_tri_x, dropdown_tri_y), (dropdown_tri_x + 10, dropdown_tri_y), (dropdown_tri_x + 5, dropdown_tri_y + 6)], fill=C["text_muted"])

# 常用模板快捷标签
tag_y = preset_select_y + 44
draw_text(right_x + 28, tag_y, "常用", font_small, C["text_muted"])

preset_tags = ["勾边字", "包边字", "连襟字", "围边字"]
tag_x = right_x + 24
tag_row_y = tag_y + 20
for i, tag in enumerate(preset_tags):
    tag_w = 68
    if i == 0:  # 选中状态
        draw_rounded_rect(tag_x, tag_row_y, tag_w, 28, 6, fill=C["accent_primary"])
        draw_text(tag_x + 12, tag_row_y + 6, tag, font_small, (255, 255, 255))
    else:
        draw_rounded_rect(tag_x, tag_row_y, tag_w, 28, 6, fill=C["bg_elevated"])
        draw_text(tag_x + 12, tag_row_y + 6, tag, font_small, C["text_secondary"])
    tag_x += tag_w + 6

# 快速参数 - 均分宽度布局
card_y = tag_row_y + 36
quick_params = [
    ("字壳高度", "30", "mm"),
    ("壁厚", "1.2", "mm"),
    ("层高", "0.3", "mm"),
]
# 计算均分宽度: 卡片内可用宽度 = SIDEBAR_RIGHT_W - 32(卡片边距) - 16(内边距)
available_width = SIDEBAR_RIGHT_W - 48
param_gap = 8  # 参数之间的间距
param_count = len(quick_params)
param_width = (available_width - param_gap * (param_count - 1)) // param_count
input_box_width = param_width - 4  # 输入框宽度略小于参数区域

qp_x = right_x + 24
for label, value, unit in quick_params:
    # 计算标签文字宽度，使其居中对齐输入框
    label_bbox = draw.textbbox((0, 0), label, font=font_small)
    label_width = label_bbox[2] - label_bbox[0]
    label_x = qp_x + (input_box_width - label_width) // 2
    draw_text(label_x, card_y + 6, label, font_small, C["text_muted"])
    draw_rounded_rect(qp_x, card_y + 22, input_box_width, 28, 6, fill=C["bg_elevated"])
    # 数值和单位也居中
    value_unit = value + " " + unit
    value_bbox = draw.textbbox((0, 0), value_unit, font=font_mono)
    value_width = value_bbox[2] - value_bbox[0]
    value_x = qp_x + (input_box_width - value_width) // 2
    draw_text(value_x, card_y + 28, value_unit, font_mono, C["text_primary"])
    qp_x += param_width + param_gap

# 可折叠参数组 - 全部折叠只显示标题
sections = [
    ("字壳工艺", False, []),
    ("换色层设置", False, []),
    ("台阶/V槽", False, []),
    ("防翘裙边", False, []),
    ("连襟字", False, []),
    ("包边勾边", False, []),
    ("面板设置", False, []),
    ("底板设置", False, []),
    ("速度设置", False, []),
    ("填充", False, []),
    ("机器设置", False, []),
]

section_y = preset_y + preset_content_h + 8
for section_name, expanded, params in sections:
    # 分组标题
    draw_rounded_rect(right_x + 16, section_y, SIDEBAR_RIGHT_W - 32, 36, 8, fill=C["bg_card"])

    # 展开/收起指示器 - 用polygon绘制三角形
    tri_x = right_x + 28
    tri_y = section_y + 14
    tri_color = C["accent_primary"] if expanded else C["text_muted"]
    if expanded:
        # 向下三角形
        draw.polygon([(tri_x, tri_y), (tri_x + 10, tri_y), (tri_x + 5, tri_y + 6)], fill=tri_color)
    else:
        # 向右三角形
        draw.polygon([(tri_x, tri_y), (tri_x + 6, tri_y + 5), (tri_x, tri_y + 10)], fill=tri_color)
    
    draw_text(right_x + 48, section_y + 10, section_name, font_h2, C["text_primary"])

    section_y += 42

# 右侧面板底部按钮区域（面板外）
btn_area_y = content_y + content_h - 60

# 切片按钮 - 蓝色圆角主按钮，右侧带下拉箭头
slice_btn_w = SIDEBAR_RIGHT_W - 32
slice_btn_h = 44
slice_btn_x = right_x + 16
slice_btn_y = btn_area_y

# 蓝色圆角背景
draw_rounded_rect(slice_btn_x, slice_btn_y, slice_btn_w, slice_btn_h, 10, fill=C["accent_primary"], outline=None)

# 文字居中（切片按钮用16号字体，留出箭头空间）
text = "切片"
try:
    font_btn_16 = ImageFont.truetype("msyh.ttc", 16)
except:
    font_btn_16 = font_h2  # 备用字体
bbox = draw.textbbox((0, 0), text, font=font_btn_16)
font_w = bbox[2] - bbox[0]
font_h = bbox[3] - bbox[1]
text_x = slice_btn_x + (slice_btn_w - font_w - 24) // 2  # 留出箭头空间
text_y = slice_btn_y + (slice_btn_h - font_h) // 2 - bbox[1]
draw_text(text_x, text_y, text, font_btn_16, (255,255,255))

# 右侧下拉箭头（三角形）
arrow_w, arrow_h = 16, 8
arrow_x = slice_btn_x + slice_btn_w - 24
arrow_y = slice_btn_y + (slice_btn_h - arrow_h) // 2
arrow_points = [
    (arrow_x, arrow_y),
    (arrow_x + arrow_w, arrow_y),
    (arrow_x + arrow_w // 2, arrow_y + arrow_h)
]
draw.polygon(arrow_points, fill=(255, 255, 255))

# ============================================
# 底部状态栏
# ============================================
draw_rounded_rect(0, HEIGHT - FOOTER_H, WIDTH, FOOTER_H, 0, fill=C["bg_primary"])
draw_text(20, HEIGHT - FOOTER_H + 10, "● 就绪", font_body, C["success"])
draw_text(100, HEIGHT - FOOTER_H + 10, "图形: 3个", font_small, C["text_muted"])
draw_text(200, HEIGHT - FOOTER_H + 10, "机器: AD-F4 (800×1200x100mm)", font_small, C["text_muted"])
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
