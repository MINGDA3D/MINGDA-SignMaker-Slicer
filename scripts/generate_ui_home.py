"""
MINGDA SignMaker - 首页设计 v3
极简大气风格 - 居中布局 + 光晕渐变 + 精致细节
一次生成两张图片：最近项目 和 精选案例
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
# 配色方案 - 与其他页面保持一致
# ============================================
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
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) if isinstance(v, str) else v for k, v in COLORS.items()}

WIDTH = 1600
HEIGHT = 1000

# 字体加载（全局）
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


def generate_home_image(tab_selected, output_filename):
    """
    生成首页图片
    tab_selected: 0 = 最近项目, 1 = 精选案例
    output_filename: 输出文件名（不含路径和扩展名）
    """
    # 创建带Alpha通道的图像
    img = Image.new('RGBA', (WIDTH, HEIGHT), C["bg_base"])
    draw = ImageDraw.Draw(img, 'RGBA')

    def draw_rounded_rect(x, y, w, h, r, fill=None, outline=None, width=1):
        draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline, width=width)

    def draw_text(x, y, text, font=None, fill=None):
        draw.text((x, y), text, font=font or font_body, fill=fill or C["text_secondary"])

    def draw_centered_text(y, text, font=None, fill=None):
        bbox = draw.textbbox((0, 0), text, font=font or font_body)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        draw.text((x, y), text, font=font, fill=fill or C["text_secondary"])

    def draw_gradient_text(x, y, text, font, color_start, color_end, vertical=False):
        """绘制渐变色文字"""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_w <= 0 or text_h <= 0:
            return

        gradient = Image.new('RGBA', (text_w, text_h), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)

        steps = text_h if vertical else text_w
        for i in range(steps):
            ratio = i / max(steps - 1, 1)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            if vertical:
                gradient_draw.line([(0, i), (text_w, i)], fill=(r, g, b, 255))
            else:
                gradient_draw.line([(i, 0), (i, text_h)], fill=(r, g, b, 255))

        mask = Image.new('L', (text_w, text_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((-bbox[0], -bbox[1]), text, font=font, fill=255)

        gradient.putalpha(mask)
        img.alpha_composite(gradient, (x, y))

    def draw_centered_gradient_text(y, text, font, color_start, color_end, vertical=False):
        """绘制居中的渐变色文字"""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2
        draw_gradient_text(x, y, text, font, color_start, color_end, vertical)

    def draw_gradient_rect(x, y, w, h, color_start, color_end, radius=0, vertical=False):
        """绘制渐变矩形"""
        if w <= 0 or h <= 0:
            return

        gradient = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)

        steps = h if vertical else w
        if steps <= 0:
            return

        for i in range(steps):
            ratio = i / max(steps - 1, 1)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            if vertical:
                gradient_draw.line([(0, i), (w - 1, i)], fill=(r, g, b, 255))
            else:
                gradient_draw.line([(i, 0), (i, h - 1)], fill=(r, g, b, 255))

        if radius > 0:
            mask = Image.new('L', (w, h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
            gradient.putalpha(mask)

        img.alpha_composite(gradient, (x, y))

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
        bbox = draw.textbbox((0, 0), icon_text, font=font_icon)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw_text(x + (size - tw) // 2, y + (size - th) // 2 - 2, icon_text, font_icon, text_color)

    # ============================================
    # 背景：深邃渐变 + 多层光晕
    # ============================================
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(C["bg_base"][0] * (1 - ratio * 0.3) + C["bg_base"][0] * (ratio * 0.3))
        g = int(C["bg_base"][1] * (1 - ratio * 0.3) + C["bg_base"][1] * (ratio * 0.3))
        b = int(C["bg_base"][2] * (1 - ratio * 0.3) + C["bg_base"][2] * (ratio * 0.3))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    draw_soft_glow(WIDTH // 2, 0, 600, C["accent_primary"], 0.06)
    draw_soft_glow(WIDTH // 2 - 300, 50, 400, C["info"], 0.04)
    draw_soft_glow(WIDTH // 2 + 300, 50, 400, C["accent_secondary"], 0.04)

    # ============================================
    # 顶部导航栏
    # ============================================
    HEADER_H = 60

    draw_rounded_rect(0, 0, WIDTH, HEADER_H, 0, fill=(12, 16, 23, 240))
    draw.line([(0, HEADER_H), (WIDTH, HEADER_H)], fill=(*C["border_default"], 80))

    logo_path = os.path.join(os.path.dirname(__file__), "..", "docs", "images", "MINGDA_logo.png")
    logo = load_icon(logo_path, 32)
    if logo:
        img.paste(logo, (16, 14), logo)
        draw_text(56, 18, "SignMaker", font_h2, C["text_primary"])
        draw_text(138, 20, "Slicer", font_h3, C["accent_secondary"])
    else:
        logo_x = 16
        draw_gradient_rect(logo_x, 20, 3, 20, C["accent_primary"], C["accent_secondary"], radius=1)
        draw_text(logo_x + 14, 18, "SignMaker", font_h2, C["text_primary"])
        draw_text(logo_x + 100, 20, "Slicer", font_h3, C["accent_secondary"])

    nav_items = [("首页", True), ("项目", False), ("预览", False)]
    nav_start_x = (WIDTH - 240) // 2

    for i, (name, active) in enumerate(nav_items):
        nx = nav_start_x + i * 80
        if active:
            draw_rounded_rect(nx, 16, 64, 28, 14, fill=C["accent_primary"])
            draw_text(nx + 20, 20, name, font_h3, (255, 255, 255))
        else:
            draw_text(nx + 20, 20, name, font_h3, C["text_muted"])

    tool_x = WIDTH - 100
    draw_rounded_rect(tool_x, 18, 28, 24, 6, fill=C["bg_elevated"])
    draw_text(tool_x + 8, 20, "?", font_h3, C["text_muted"])

    # ============================================
    # 英雄区域
    # ============================================
    hero_y = 140

    draw_centered_text(hero_y, "SignMakerSlicer", font_display, C["text_primary"])

    subtitle = "专业的广告发光字切片软件"
    draw_centered_gradient_text(hero_y + 75, subtitle, font_h2, C["accent_primary"], C["accent_secondary"])

    features_text = "一键生成 G-code  ·  支持多种边型  ·  高效精准"
    color_start = (6, 182, 212)
    color_end = (168, 85, 247)
    draw_centered_gradient_text(hero_y + 108, features_text, font_body, color_start, color_end)

    # ============================================
    # 核心操作按钮
    # ============================================
    btn_y = hero_y + 165
    btn_w = 160
    btn_h = 48
    btn_gap = 20

    btn1_x = (WIDTH - btn_w * 2 - btn_gap) // 2
    draw_rounded_rect(btn1_x, btn_y, btn_w, btn_h, 10, fill=C["accent_primary"])
    draw_text(btn1_x + 38, btn_y + 14, "+ 新建项目", font_h3, (255, 255, 255))

    btn2_x = btn1_x + btn_w + btn_gap
    draw_rounded_rect(btn2_x, btn_y, btn_w, btn_h, 10, fill=C["bg_card"], outline=C["border_default"])
    draw_text(btn2_x + 45, btn_y + 14, "打开文件", font_h3, C["text_secondary"])

    # ============================================
    # 最近项目 / 精选案例 切换标签
    # ============================================
    section_y = btn_y + 90

    tab1_text = "最近项目"
    tab2_text = "精选案例"

    tab1_bbox = draw.textbbox((0, 0), tab1_text, font=font_h1)
    tab2_bbox = draw.textbbox((0, 0), tab2_text, font=font_h1)
    tab1_w = tab1_bbox[2] - tab1_bbox[0]
    tab2_w = tab2_bbox[2] - tab2_bbox[0]

    tab_x = 80
    tab_gap = 32
    divider_x = tab_x + tab1_w + 16

    if tab_selected == 0:
        draw_text(tab_x, section_y, tab1_text, font_h1, C["text_primary"])
        draw_rounded_rect(tab_x, section_y + 32, tab1_w, 3, 1, fill=C["accent_primary"])
    else:
        draw_text(tab_x, section_y, tab1_text, font_h1, C["text_muted"])

    draw_text(divider_x, section_y, "|", font_h1, C["text_muted"])

    tab2_x = divider_x + 16
    if tab_selected == 1:
        draw_text(tab2_x, section_y, tab2_text, font_h1, C["text_primary"])
        draw_rounded_rect(tab2_x, section_y + 32, tab2_w, 3, 1, fill=C["accent_primary"])
    else:
        draw_text(tab2_x, section_y, tab2_text, font_h1, C["text_muted"])

    draw_text(WIDTH - 130, section_y + 6, "查看全部 ->", font_small, C["accent_secondary"])

    content_y = section_y + 50

    # ============================================
    # 最近项目 内容 (tab_selected == 0)
    # ============================================
    if tab_selected == 0:
        projects = [
            ("发光字-门头招牌.sms", "2025-12-25 14:30:04", C["accent_primary"]),
            ("连襟字-客户订单.sms", "2025-12-24 16:45:22", C["info"]),
            ("包边字-测试样品.sms", "2025-12-22 09:15:38", C["accent_secondary"]),
            ("勾边字-展示样板.sms", "2025-12-20 11:28:56", C["success"]),
            ("斜边字-商场招牌.sms", "2025-12-18 15:42:11", C["accent_primary"]),
            ("直边字-店铺门头.sms", "2025-12-15 08:33:45", C["info"]),
            ("双面字-广告牌.sms", "2025-12-12 17:20:33", C["accent_secondary"]),
            ("工厂字-车间标识.sms", "2025-12-10 14:55:19", C["success"]),
            ("背打光-酒店标识.sms", "2025-12-08 10:12:47", C["success"]),
            ("吸塑字-连锁店招.sms", "2025-12-05 16:38:02", C["accent_primary"]),
        ]

        preview_chars = ["洋", "明", "达", "发", "光", "字", "切", "片", "软", "件"]

        cols = 5
        rows = 2
        card_size = 260
        card_gap_x = 20
        card_gap_y = 15
        start_x = 80

        preview_size = 180
        preview_margin = (card_size - preview_size) // 2

        try:
            font_preview = ImageFont.truetype("msyh.ttc", 72)
        except:
            font_preview = font_display

        for i, (name, time, accent) in enumerate(projects):
            row = i // cols
            col = i % cols

            cx = start_x + col * (card_size + card_gap_x)
            cy = content_y + row * (card_size + card_gap_y)

            preview_x = cx + preview_margin
            preview_y = cy + 10
            draw_rounded_rect(preview_x, preview_y, preview_size, preview_size, 10, fill=(45, 50, 60))

            icon_cx = preview_x + preview_size // 2
            icon_cy = preview_y + preview_size // 2

            char = preview_chars[i] if i < len(preview_chars) else "字"

            wire_color = (120, 135, 160)
            bg_color = (45, 50, 60)
            draw.text((icon_cx, icon_cy), char, font=font_preview, fill=bg_color,
                      stroke_width=2, stroke_fill=wire_color, anchor="mm")

            text_y = preview_y + preview_size + 8
            display_name = name if len(name) <= 18 else name[:17] + "..."
            draw_text(preview_x, text_y, display_name, font_h3, C["text_primary"])

            time_y = text_y + 18
            draw_text(preview_x, time_y, time, font_small, C["text_muted"])

    # ============================================
    # 精选案例 内容 (tab_selected == 1)
    # ============================================
    else:
        cases = [
            ("TikTok", "斜边字", C["accent_secondary"]),
            ("ChatGPT", "包边字", C["success"]),
            ("奔驰", "连襟字", C["accent_primary"]),
            ("宝马", "勾边字", C["info"]),
            ("特斯拉", "工厂字", C["success"]),
            ("星巴克", "双面字", C["success"]),
            ("麦当劳", "吸塑字", C["accent_primary"]),
            ("耐克", "背打光", C["accent_secondary"]),
            ("苹果", "直边字", C["text_secondary"]),
            ("华为", "斜边字", C["error"]),
        ]

        cols = 5
        rows = 2
        case_card_w = 260
        case_card_h = 220
        case_gap_x = 20
        case_gap_y = 20

        for i, (brand, style, accent) in enumerate(cases):
            row = i // cols
            col = i % cols

            cx = 80 + col * (case_card_w + case_gap_x)
            cy = content_y + row * (case_card_h + case_gap_y)

            draw_rounded_rect(cx, cy, case_card_w, case_card_h, 12, fill=C["bg_card"])

            logo_size = 140
            logo_margin = (case_card_w - logo_size) // 2
            logo_x = cx + logo_margin
            logo_y = cy + 15

            draw_rounded_rect(logo_x, logo_y, logo_size, logo_size, 10, fill=(45, 50, 60))

            logo_cx = logo_x + logo_size // 2
            logo_cy = logo_y + logo_size // 2

            logo_map = {
                "TikTok": "tiktok.png",
                "ChatGPT": "ChatGPT_logo.png",
                "奔驰": "奔驰.png",
                "宝马": "宝马.png",
                "特斯拉": "特斯拉.png",
                "星巴克": "星巴克.png",
                "麦当劳": "麦当劳-01.png",
                "耐克": "耐克.png",
                "苹果": "apple.png",
                "华为": "huawei.png"
            }

            logo_file = logo_map.get(brand)
            loaded = False

            if logo_file:
                logo_path = os.path.join(os.path.dirname(__file__), "..", "docs", "images", logo_file)
                if os.path.exists(logo_path):
                    try:
                        logo_img = Image.open(logo_path).convert("RGBA")

                        max_size = 80
                        w, h = logo_img.size
                        ratio = min(max_size/w, max_size/h)
                        new_size = (int(w*ratio), int(h*ratio))
                        logo_img = logo_img.resize(new_size, Image.Resampling.LANCZOS)

                        paste_x = int(logo_cx - logo_img.width / 2)
                        paste_y = int(logo_cy - logo_img.height / 2)

                        img.alpha_composite(logo_img, (paste_x, paste_y))
                        loaded = True
                    except Exception as e:
                        print(f"Failed to load logo {logo_file}: {e}")

            if not loaded:
                draw_text(logo_cx - 15, logo_cy - 10, brand[0], font_h1, accent)

            text_y = logo_y + logo_size + 10
            brand_bbox = draw.textbbox((0, 0), brand, font=font_h3)
            brand_w = brand_bbox[2] - brand_bbox[0]
            brand_x = cx + (case_card_w - brand_w) // 2
            draw_text(brand_x, text_y, brand, font_h3, C["text_primary"])

            style_bbox = draw.textbbox((0, 0), style, font=font_small)
            style_w = style_bbox[2] - style_bbox[0]
            style_x = cx + (case_card_w - style_w) // 2
            draw_text(style_x, text_y + 20, style, font_small, C["text_muted"])

    # ============================================
    # 底部状态栏
    # ============================================
    FOOTER_H = 36
    footer_y = HEIGHT - FOOTER_H

    draw_rounded_rect(0, footer_y, WIDTH, FOOTER_H, 0, fill=(12, 16, 23, 250))
    draw.line([(0, footer_y), (WIDTH, footer_y)], fill=(*C["border_default"], 60))

    draw_text(28, footer_y + 10, "*", font_body, C["success"])
    draw_text(42, footer_y + 10, "就绪", font_small, C["text_muted"])
    draw_text(WIDTH - 160, footer_y + 10, "MINGDA SignMaker v1.0", font_small, C["text_muted"])

    # ============================================
    # 保存
    # ============================================
    img_rgb = Image.new('RGB', (WIDTH, HEIGHT), C["bg_base"])
    img_rgb.paste(img, (0, 0), img)

    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{output_filename}.png")
    img_rgb.save(output_path, "PNG", quality=95)
    print(f"Saved: {output_path}")

    root_path = os.path.join(os.path.dirname(__file__), "..", f"{output_filename}.png")
    img_rgb.save(root_path, "PNG", quality=95)
    print(f"Saved: {root_path}")


# ============================================
# 生成两张图片
# ============================================
if __name__ == "__main__":
    # 生成最近项目图片
    generate_home_image(tab_selected=0, output_filename="UI_Home_RecentProjects")

    # 生成精选案例图片
    generate_home_image(tab_selected=1, output_filename="UI_Home_FeaturedCases")

    print("\nHome UI v3 generated successfully!")
    print("  - UI_Home_RecentProjects.png (Recent Projects)")
    print("  - UI_Home_FeaturedCases.png (Featured Cases)")
