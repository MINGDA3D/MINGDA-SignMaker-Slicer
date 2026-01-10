"""
SignMaker Slicer - 首页设计 v3
极简大气风格 - 居中布局 + 光晕渐变 + 精致细节
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
# 配色方案 - 深邃优雅风
# ============================================
COLORS = {
    # 背景层次
    "bg_deep": "#06080D",
    "bg_base": "#0C1017",
    "bg_surface": "#12161F",
    "bg_card": "#1A1F2E",
    "bg_elevated": "#232938",

    # 文字
    "text_hero": "#FFFFFF",
    "text_primary": "#F3F4F6",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",
    "text_hint": "#4B5563",

    # 强调色 - 蓝紫渐变系
    "accent_indigo": "#818CF8",
    "accent_violet": "#A78BFA",
    "accent_cyan": "#22D3EE",
    "accent_teal": "#2DD4BF",

    # 功能色
    "success": "#34D399",
    "border": "#374151",
    "border_light": "#4B5563",
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) if isinstance(v, str) else v for k, v in COLORS.items()}

WIDTH = 1600
HEIGHT = 1000

# 创建带Alpha通道的图像
img = Image.new('RGBA', (WIDTH, HEIGHT), C["bg_deep"])
draw = ImageDraw.Draw(img, 'RGBA')

# 字体加载
try:
    font_display = ImageFont.truetype("msyh.ttc", 56)
    font_h1 = ImageFont.truetype("msyh.ttc", 24)
    font_h2 = ImageFont.truetype("msyh.ttc", 16)
    font_h3 = ImageFont.truetype("msyh.ttc", 13)
    font_body = ImageFont.truetype("msyh.ttc", 11)
    font_small = ImageFont.truetype("msyh.ttc", 10)
    font_icon = ImageFont.truetype("msyh.ttc", 20)
except:
    font_display = font_h1 = font_h2 = font_h3 = font_body = font_small = font_icon = ImageFont.load_default()

def draw_rounded_rect(x, y, w, h, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline, width=width)

def draw_text(x, y, text, font=None, fill=None):
    draw.text((x, y), text, font=font or font_body, fill=fill or C["text_secondary"])

def draw_centered_text(y, text, font=None, fill=None):
    bbox = draw.textbbox((0, 0), text, font=font or font_body)
    text_width = bbox[2] - bbox[0]
    x = (WIDTH - text_width) // 2
    draw.text((x, y), text, font=font, fill=fill or C["text_secondary"])

def draw_gradient_rect(x, y, w, h, color_start, color_end, radius=0, vertical=False):
    """绘制渐变矩形"""
    gradient = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)

    steps = h if vertical else w
    for i in range(steps):
        ratio = i / steps
        r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
        if vertical:
            gradient_draw.line([(0, i), (w, i)], fill=(r, g, b, 255))
        else:
            gradient_draw.line([(i, 0), (i, h)], fill=(r, g, b, 255))

    if radius > 0:
        mask = Image.new('L', (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
        gradient.putalpha(mask)

    img.paste(gradient, (x, y), gradient)

def draw_soft_glow(cx, cy, radius, color, intensity=0.15):
    """绘制柔和光晕"""
    for r in range(radius, 0, -8):
        alpha = int(255 * intensity * (r / radius) ** 3)
        if alpha > 0:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))

def draw_icon_box(x, y, size, icon_text, bg_color, text_color):
    """绘制图标盒子"""
    draw_rounded_rect(x, y, size, size, size // 4, fill=(*bg_color, 30))
    draw_rounded_rect(x + 2, y + 2, size - 4, size - 4, size // 4 - 1, outline=(*bg_color, 60))
    # 居中文字
    bbox = draw.textbbox((0, 0), icon_text, font=font_icon)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw_text(x + (size - tw) // 2, y + (size - th) // 2 - 2, icon_text, font_icon, text_color)

# ============================================
# 背景：深邃渐变 + 多层光晕
# ============================================
# 垂直渐变背景
for y in range(HEIGHT):
    ratio = y / HEIGHT
    # 从深到稍浅的渐变
    r = int(C["bg_deep"][0] * (1 - ratio * 0.3) + C["bg_base"][0] * (ratio * 0.3))
    g = int(C["bg_deep"][1] * (1 - ratio * 0.3) + C["bg_base"][1] * (ratio * 0.3))
    b = int(C["bg_deep"][2] * (1 - ratio * 0.3) + C["bg_base"][2] * (ratio * 0.3))
    draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

# 顶部光晕组合 - 营造氛围
draw_soft_glow(WIDTH // 2, 0, 600, C["accent_indigo"], 0.06)
draw_soft_glow(WIDTH // 2 - 300, 50, 400, C["accent_violet"], 0.04)
draw_soft_glow(WIDTH // 2 + 300, 50, 400, C["accent_cyan"], 0.04)

# ============================================
# 顶部导航栏
# ============================================
HEADER_H = 60

# 导航背景 - 微透明
draw_rounded_rect(0, 0, WIDTH, HEADER_H, 0, fill=(12, 16, 23, 240))
# 底部分隔线
draw.line([(0, HEADER_H), (WIDTH, HEADER_H)], fill=(*C["border"], 80))

# Logo - 与其他页面保持一致
logo_path = os.path.join(os.path.dirname(__file__), "..", "docs", "images", "MINGDA_logo.png")
logo = load_icon(logo_path, 32)
if logo:
    img.paste(logo, (16, 14), logo)
    draw_text(56, 18, "SignMaker", font_h2, C["text_primary"])
    draw_text(138, 20, "Slicer", font_h3, C["accent_cyan"])
else:
    # 没有logo时显示原样式
    logo_x = 16
    draw_gradient_rect(logo_x, 20, 3, 20, C["accent_indigo"], C["accent_cyan"], radius=1)
    draw_text(logo_x + 14, 18, "SignMaker", font_h2, C["text_primary"])
    draw_text(logo_x + 100, 20, "Slicer", font_h3, C["accent_cyan"])

# 中央导航
nav_items = [("首页", True), ("项目", False), ("预览", False)]
nav_start_x = (WIDTH - 240) // 2

for i, (name, active) in enumerate(nav_items):
    nx = nav_start_x + i * 80
    if active:
        draw_gradient_rect(nx, 16, 64, 28, C["accent_indigo"], C["accent_violet"], radius=14)
        draw_text(nx + 20, 20, name, font_h3, (255, 255, 255))
    else:
        draw_text(nx + 20, 20, name, font_h3, C["text_muted"])

# 右侧工具按钮
tool_x = WIDTH - 100
draw_rounded_rect(tool_x, 18, 28, 24, 6, fill=C["bg_elevated"])
draw_text(tool_x + 8, 20, "?", font_h3, C["text_muted"])

# ============================================
# 英雄区域
# ============================================
hero_y = 140

# 主标题
draw_centered_text(hero_y, "SignMaker Slicer", font_display, C["text_hero"])

# 副标题 - 带渐变色效果(模拟)
subtitle = "专业的广告发光字切片软件"
draw_centered_text(hero_y + 75, subtitle, font_h2, C["accent_violet"])

# 特性说明
features_text = "一键生成 G-code  ·  支持多种边型  ·  高效精准"
draw_centered_text(hero_y + 108, features_text, font_body, C["text_muted"])

# ============================================
# 核心操作按钮
# ============================================
btn_y = hero_y + 165
btn_w = 160
btn_h = 48
btn_gap = 20

# 新建项目按钮 - 渐变填充
btn1_x = (WIDTH - btn_w * 2 - btn_gap) // 2
draw_gradient_rect(btn1_x, btn_y, btn_w, btn_h, C["accent_indigo"], C["accent_violet"], radius=10)
draw_text(btn1_x + 38, btn_y + 14, "+ 新建项目", font_h3, (255, 255, 255))

# 打开文件按钮 - 边框样式
btn2_x = btn1_x + btn_w + btn_gap
draw_rounded_rect(btn2_x, btn_y, btn_w, btn_h, 10, fill=C["bg_card"], outline=C["border"])
draw_text(btn2_x + 45, btn_y + 14, "打开文件", font_h3, C["text_secondary"])

# ============================================
# 最近项目 / 精选案例 切换标签
# ============================================
section_y = btn_y + 90

# 标签切换栏
tab_selected = 0  # 0: 最近项目, 1: 精选案例

# 计算标签位置
tab1_text = "最近项目"
tab2_text = "精选案例"

tab1_bbox = draw.textbbox((0, 0), tab1_text, font=font_h1)
tab2_bbox = draw.textbbox((0, 0), tab2_text, font=font_h1)
tab1_w = tab1_bbox[2] - tab1_bbox[0]
tab2_w = tab2_bbox[2] - tab2_bbox[0]

tab_x = 80
tab_gap = 32  # 标签之间的间距（包括分隔符）
divider_x = tab_x + tab1_w + 16  # 分隔符位置

# 绘制第一个标签（最近项目）- 选中状态
if tab_selected == 0:
    draw_text(tab_x, section_y, tab1_text, font_h1, C["text_primary"])
    # 选中下划线
    draw_gradient_rect(tab_x, section_y + 32, tab1_w, 3, C["accent_indigo"], C["accent_violet"], radius=1)
else:
    draw_text(tab_x, section_y, tab1_text, font_h1, C["text_muted"])

# 分隔符
draw_text(divider_x, section_y, "|", font_h1, C["text_hint"])

# 绘制第二个标签（精选案例）- 未选中状态
tab2_x = divider_x + 16
if tab_selected == 1:
    draw_text(tab2_x, section_y, tab2_text, font_h1, C["text_primary"])
    # 选中下划线
    draw_gradient_rect(tab2_x, section_y + 32, tab2_w, 3, C["accent_indigo"], C["accent_violet"], radius=1)
else:
    draw_text(tab2_x, section_y, tab2_text, font_h1, C["text_muted"])

# 查看全部链接
draw_text(WIDTH - 130, section_y + 6, "查看全部 ->", font_small, C["accent_cyan"])

# 内容区域起始位置
content_y = section_y + 50

# ============================================
# 最近项目 内容 (tab_selected == 0)
# ============================================
if tab_selected == 0:
    # 10个项目 (2行 x 5列)
    projects = [
        ("发光字-门头招牌.dxf", "2025-12-25 14:30:04", C["accent_indigo"]),
        ("连襟字-客户订单.dxf", "2025-12-24 16:45:22", C["accent_violet"]),
        ("包边字-测试样品.dxf", "2025-12-22 09:15:38", C["accent_cyan"]),
        ("勾边字-展示样板.dxf", "2025-12-20 11:28:56", C["accent_teal"]),
        ("斜边字-商场招牌.dxf", "2025-12-18 15:42:11", C["accent_indigo"]),
        ("直边字-店铺门头.dxf", "2025-12-15 08:33:45", C["accent_violet"]),
        ("双面字-广告牌.dxf", "2025-12-12 17:20:33", C["accent_cyan"]),
        ("工厂字-车间标识.dxf", "2025-12-10 14:55:19", C["accent_teal"]),
        ("背打光-酒店标识.dxf", "2025-12-08 10:12:47", C["success"]),
        ("吸塑字-连锁店招.dxf", "2025-12-05 16:38:02", C["accent_indigo"]),
    ]

    # 预览图显示的字符 - "洋明达发光字切片软件"
    preview_chars = ["洋", "明", "达", "发", "光", "字", "切", "片", "软", "件"]

    # 2行5列布局 - 正方形卡片
    cols = 5
    rows = 2
    card_size = 260  # 正方形
    card_gap_x = 20
    card_gap_y = 15
    start_x = 80

    # 预览图区域参数（正方形预览图）
    preview_size = 180
    preview_margin = (card_size - preview_size) // 2

    # 加载大号字体用于预览图中的字符
    try:
        font_preview = ImageFont.truetype("msyh.ttc", 72)
    except:
        font_preview = font_display

    for i, (name, time, accent) in enumerate(projects):
        row = i // cols
        col = i % cols

        cx = start_x + col * (card_size + card_gap_x)
        cy = content_y + row * (card_size + card_gap_y)

        # 预览图区域 - 深色背景，正方形
        preview_x = cx + preview_margin
        preview_y = cy + 10
        draw_rounded_rect(preview_x, preview_y, preview_size, preview_size, 10, fill=(45, 50, 60))

        # 预览图中心
        icon_cx = preview_x + preview_size // 2
        icon_cy = preview_y + preview_size // 2

        # 获取当前预览字符
        char = preview_chars[i] if i < len(preview_chars) else "字"

        # 线框颜色
        wire_color = (120, 135, 160)

        # 绘制字符轮廓（只有描边，没有填充）- 使用 anchor 居中
        bg_color = (45, 50, 60)
        draw.text((icon_cx, icon_cy), char, font=font_preview, fill=bg_color,
                  stroke_width=2, stroke_fill=wire_color, anchor="mm")

        # 文件名 - 在预览图下方，与预览图左对齐
        text_y = preview_y + preview_size + 8
        # 截断过长的文件名
        display_name = name if len(name) <= 18 else name[:17] + "..."
        draw_text(preview_x, text_y, display_name, font_h3, C["text_primary"])

        # 时间戳 - 最下方，与预览图左对齐
        time_y = text_y + 18
        draw_text(preview_x, time_y, time, font_small, C["text_muted"])

# ============================================
# 精选案例 内容 (tab_selected == 1)
# ============================================
else:
    # 品牌案例 - 简化信息，强调图形
    cases = [
        ("TikTok", "斜边字", C["accent_cyan"]),
        ("ChatGPT", "包边字", C["accent_teal"]),
        ("奔驰", "连襟字", C["accent_indigo"]),
        ("宝马", "勾边字", C["accent_violet"]),
        ("特斯拉", "工厂字", C["success"]),
        ("星巴克", "双面字", C["success"]),
        ("麦当劳", "吸塑字", C["accent_indigo"]),
        ("耐克", "背打光", C["accent_cyan"]),
    ]

    # 调整布局参数
    case_card_w = 330
    case_card_h = 100
    case_gap_x = 40
    case_gap_y = 30

    for i, (brand, style, accent) in enumerate(cases):
        # 计算行列
        row = i // 4
        col = i % 4

        cx = 80 + col * (case_card_w + case_gap_x)
        cy = content_y + row * (case_card_h + case_gap_y)

        # 卡片背景
        draw_rounded_rect(cx, cy, case_card_w, case_card_h, 16, fill=C["bg_card"], outline=(*accent, 40))

        # Logo区域 - 扩大展示区
        logo_size = 64
        logo_cx = cx + 50  # 左侧留出更多空间放Logo
        logo_cy = cy + case_card_h // 2

        # Logo背景
        draw_rounded_rect(logo_cx - 32, logo_cy - 32, 64, 64, 16, fill=(*accent, 15))

        # 加载真实Logo图片
        logo_map = {
            "TikTok": "tiktok.png",
            "ChatGPT": "ChatGPT_logo.png",
            "奔驰": "奔驰.png",
            "宝马": "宝马.png",
            "特斯拉": "特斯拉.png",
            "星巴克": "星巴克.png",
            "麦当劳": "麦当劳-01.png",
            "耐克": "耐克.png"
        }

        logo_file = logo_map.get(brand)
        loaded = False

        if logo_file:
            logo_path = os.path.join(os.path.dirname(__file__), "..", "docs", "images", logo_file)
            if os.path.exists(logo_path):
                try:
                    logo_img = Image.open(logo_path).convert("RGBA")

                    # 调整大小，保持比例，限制在 40x40 以内 (留出边距)
                    max_size = 40
                    w, h = logo_img.size
                    ratio = min(max_size/w, max_size/h)
                    new_size = (int(w*ratio), int(h*ratio))
                    logo_img = logo_img.resize(new_size, Image.Resampling.LANCZOS)

                    # 居中粘贴
                    paste_x = int(logo_cx - logo_img.width / 2)
                    paste_y = int(logo_cy - logo_img.height / 2)

                    # 使用 alpha_composite 进行透明混合
                    img.alpha_composite(logo_img, (paste_x, paste_y))
                    loaded = True
                except Exception as e:
                    print(f"Failed to load logo {logo_file}: {e}")

        # 如果加载失败，回退到简易绘制 (仅作为兜底)
        if not loaded:
            lx, ly = logo_cx, logo_cy
            if brand == "TikTok":
                # 模拟音符
                draw.ellipse([lx-10, ly-5, lx+5, ly+10], fill=accent)
                draw.rectangle([lx+2, ly-15, lx+5, ly+5], fill=accent)
            elif brand == "ChatGPT":
                 draw.polygon([(lx, ly-15), (lx+13, ly-7), (lx+13, ly+7), (lx, ly+15), (lx-13, ly+7), (lx-13, ly-7)], outline=accent)
            else:
                 draw_text(lx - 10, ly - 10, brand[0], font_h2, accent)

        # 品牌信息 - 极简展示
        text_x = cx + 105
        draw_text(text_x, cy + 24, brand, font_h2, C["text_primary"]) # 品牌名加大

        # 样式标签 - 弱化显示
        draw_rounded_rect(text_x, cy + 54, 70, 20, 4, fill=(*C["bg_deep"], 100), outline=(*C["text_muted"], 50))
        draw_text(text_x + 8, cy + 56, style, font_small, C["text_muted"])

        # 打印按钮图标 - 仅显示图标
        btn_size = 32
        btn_x = cx + case_card_w - btn_size - 20
        btn_y = cy + (case_card_h - btn_size) // 2

        draw_rounded_rect(btn_x, btn_y, btn_size, btn_size, 16, fill=(*accent, 20), outline=(*accent, 60))
        # 简单的箭头图标
        draw.line([btn_x+10, btn_y+16, btn_x+22, btn_y+16], fill=accent, width=2)
        draw.line([btn_x+16, btn_y+10, btn_x+22, btn_y+16], fill=accent, width=2)
        draw.line([btn_x+16, btn_y+22, btn_x+22, btn_y+16], fill=accent, width=2)

# ============================================
# 底部状态栏
# ============================================
FOOTER_H = 36
footer_y = HEIGHT - FOOTER_H

draw_rounded_rect(0, footer_y, WIDTH, FOOTER_H, 0, fill=(12, 16, 23, 250))
draw.line([(0, footer_y), (WIDTH, footer_y)], fill=(*C["border"], 60))

draw_text(28, footer_y + 10, "*", font_body, C["success"])
draw_text(42, footer_y + 10, "就绪", font_small, C["text_muted"])
draw_text(WIDTH - 160, footer_y + 10, "SignMaker Slicer v1.0", font_small, C["text_hint"])

# ============================================
# 保存
# ============================================
img_rgb = Image.new('RGB', (WIDTH, HEIGHT), C["bg_deep"])
img_rgb.paste(img, (0, 0), img)

output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "UI_Home.png")
img_rgb.save(output_path, "PNG", quality=95)
print(f"Saved: {output_path}")

root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Home.png")
img_rgb.save(root_path, "PNG", quality=95)
print(f"Saved: {root_path}")

print("Home UI v3 generated successfully!")
