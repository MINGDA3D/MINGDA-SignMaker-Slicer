"""
SignMaker Slicer - Modern UI Design
现代化UI设计 - 独特风格
灵感来源: Figma, Blender, VS Code, Fusion 360
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
# 现代配色方案 - 深蓝科技风
# ============================================
COLORS = {
    # 背景层级 - 更有层次感
    "bg_base": "#0A0E14",        # 最深背景
    "bg_primary": "#0D1219",     # 主背景
    "bg_secondary": "#131A24",   # 次背景
    "bg_card": "#1A2332",        # 卡片背景
    "bg_elevated": "#1F2A3C",    # 悬浮背景
    "bg_hover": "#253345",       # 悬停背景

    # 文字
    "text_primary": "#E6EDF3",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",

    # 强调色 - 渐变蓝绿
    "accent_primary": "#3B82F6",   # 主蓝色
    "accent_secondary": "#06B6D4", # 青色
    "accent_gradient_start": "#3B82F6",
    "accent_gradient_end": "#06B6D4",

    # 语义色
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "info": "#6366F1",

    # 边框
    "border_subtle": "#1E293B",
    "border_default": "#334155",
    "border_focus": "#3B82F6",

    # 路径预览色
    "path_outer": "#3B82F6",
    "path_inner": "#06B6D4",
    "path_fill": "#10B981",
    "path_travel": "#475569",

    # 挤出机色
    "extruder_1": "#3B82F6",
    "extruder_2": "#EC4899",
    "extruder_3": "#F59E0B",
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) for k, v in COLORS.items()}

# 尺寸
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

def draw_gradient_rect(x, y, w, h, r=0):
    """绘制渐变矩形 (简化版)"""
    for i in range(w):
        ratio = i / w
        color = tuple(int(C["accent_gradient_start"][j] + (C["accent_gradient_end"][j] - C["accent_gradient_start"][j]) * ratio) for j in range(3))
        draw.line([(x + i, y), (x + i, y + h)], fill=color)

# ============================================
# 布局常量
# ============================================
HEADER_H = 48
SIDEBAR_LEFT_W = 240
SIDEBAR_RIGHT_W = 340
FOOTER_H = 36
TOOLBAR_H = 44

content_y = HEADER_H
content_h = HEIGHT - HEADER_H - FOOTER_H

# ============================================
# 顶部导航栏 - 现代简洁风格
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
        draw_gradient_rect(nx, 8, 64, 32, 14)
        draw_text(nx + 20, 14, name, font_h2, (255, 255, 255))
    else:
        draw_text(nx + 20, 14, name, font_h2, C["text_muted"])

# 右侧工具按钮
right_tools = ["⚙", "?", "☰"]
tool_x = WIDTH - 140
for icon in right_tools:
    draw_rounded_rect(tool_x, 10, 32, 28, 6, fill=C["bg_card"])
    draw_text(tool_x + 10, 14, icon, font_icon, C["text_secondary"])
    tool_x += 40

# ============================================
# 左侧面板 - 项目 + 图层管理
# ============================================
left_panel_x = 0
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

    # 颜色指示器
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
# 中央画布区域
# ============================================
canvas_x = SIDEBAR_LEFT_W
canvas_w = WIDTH - SIDEBAR_LEFT_W - SIDEBAR_RIGHT_W
canvas_y = content_y
canvas_h = content_h

# 画布背景
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

# 编辑工具组6 - 打印顺序编辑
icon_path = os.path.join(icons_dir, "顺序.png")
icon = load_icon(icon_path, icon_size)
if icon:
    img.paste(icon, (etx + 4, canvas_toolbar_y + 8), icon)
etx += 44

# 视图切换 (最右侧)
view_x = canvas_x + canvas_w - 110  # 工具栏右边距
draw_text(view_x + 12, canvas_toolbar_y + 16, "2D", font_body, C["accent_primary"])
draw.line([(view_x + 40, canvas_toolbar_y + 12), (view_x + 40, canvas_toolbar_y + 36)], fill=C["border_default"])
draw_text(view_x + 52, canvas_toolbar_y + 16, "3D", font_body, C["text_muted"])

# 画布内容区
inner_canvas_y = canvas_toolbar_y + 56
inner_canvas_h = canvas_h - 120

# 网格背景
draw_rounded_rect(canvas_x + 20, inner_canvas_y, canvas_w - 40, inner_canvas_h, 8, fill=C["bg_base"])

# 网格线
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

# 绘制字形
char_x = canvas_x + canvas_w // 2 - 60
char_y = inner_canvas_y + inner_canvas_h // 2 - 80
draw_text(char_x, char_y, "发", font_large, C["path_outer"])

# 路径高亮
draw.ellipse([char_x - 8, char_y - 8, char_x + 8, char_y + 8], fill=C["success"], outline=C["bg_base"])

# 底部信息栏
info_y = inner_canvas_y + inner_canvas_h + 8
draw_rounded_rect(canvas_x + 20, info_y, canvas_w - 40, 36, 8, fill=C["bg_card"])
draw_text(canvas_x + 36, info_y + 10, "尺寸: 120 × 150 mm", font_small, C["text_muted"])
draw_text(canvas_x + 200, info_y + 10, "缩放: 100%", font_small, C["text_muted"])
draw_text(canvas_x + 320, info_y + 10, "坐标: X 125.5  Y 89.2", font_small, C["text_muted"])

# 缩放控制 (右侧)
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

# 快速参数 - 紧凑布局
card_y = tag_row_y + 36
quick_params = [
    ("字壳高度", "30", "mm"),
    ("壁厚", "1.2", "mm"),
    ("层高", "0.3", "mm"),
]
qp_x = right_x + 24
for label, value, unit in quick_params:
    draw_text(qp_x, card_y + 6, label, font_small, C["text_muted"])
    draw_rounded_rect(qp_x, card_y + 22, 65, 28, 6, fill=C["bg_elevated"])
    draw_text(qp_x + 8, card_y + 28, value, font_mono, C["text_primary"])
    draw_text(qp_x + 42, card_y + 30, unit, font_small, C["text_muted"])
    qp_x += 100

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

# 切片按钮 - 渐变主按钮
slice_btn_w = 150
draw_gradient_rect(right_x + 16, btn_area_y, slice_btn_w, 44)
draw_rounded_rect(right_x + 16, btn_area_y, slice_btn_w, 44, 10, outline=None)
draw_text(right_x + 16 + (slice_btn_w - 26) // 2, btn_area_y + 12, "切片", font_h2, (255,255,255))

# 上传按钮
upload_btn_w = 150
upload_btn_x = right_x + 16 + slice_btn_w + 8
draw_rounded_rect(upload_btn_x, btn_area_y, upload_btn_w, 44, 10, fill=C["bg_card"], outline=C["border_default"])
draw_text(upload_btn_x + (upload_btn_w - 26) // 2, btn_area_y + 12, "上传", font_h2, C["text_secondary"])

# ============================================
# 底部状态栏
# ============================================
draw_rounded_rect(0, HEIGHT - FOOTER_H, WIDTH, FOOTER_H, 0, fill=C["bg_primary"])

# 状态信息
draw_text(20, HEIGHT - FOOTER_H + 10, "● 就绪", font_body, C["success"])
draw_text(100, HEIGHT - FOOTER_H + 10, "图形: 3个", font_small, C["text_muted"])
draw_text(200, HEIGHT - FOOTER_H + 10, "机器: AD-F4 (800×1200mm)", font_small, C["text_muted"])

# 版本
draw_text(WIDTH - 150, HEIGHT - FOOTER_H + 10, "SignMaker Slicer v1.0", font_small, C["text_muted"])

# ============================================
# 保存
# ============================================
output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "UI_Modern.png")
img.save(output_path, "PNG", quality=95)
print(f"Saved: {output_path}")

root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Modern.png")
img.save(root_path, "PNG", quality=95)
print(f"Saved: {root_path}")

print("\n设计理念:")
print("1. 深蓝科技风配色 - 区别于INC-S的灰白色调")
print("2. 卡片式布局 - 现代感更强")
print("3. 圆角设计 - 更友好的视觉体验")
print("4. 可折叠参数组 - 减少视觉负担")
print("5. 渐变主按钮 - 突出核心操作")
