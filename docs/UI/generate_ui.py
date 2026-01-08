#!/usr/bin/env python3
"""
SignMaker Slicer UI Generator - Add Preset Template to Existing UI
在现有UI基础上添加预设模板功能
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Color palette matching original UI
COLORS = {
    'bg_dark': '#1a1d21',
    'bg_panel': '#1e2228',
    'bg_section': '#2a2f38',
    'accent': '#00a8e8',
    'text_primary': '#ffffff',
    'text_secondary': '#a0a0a0',
    'text_dim': '#606060',
    'border': '#3a4048',
    'input_bg': '#1a1d21',
    'button_bg': '#3a4048',
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# Font paths
FONT_DIR = r"E:\SignMaker Slicer\.claude\skills\canvas-design\canvas-fonts"
FONT_REGULAR = os.path.join(FONT_DIR, "NotoSansSC-Regular.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "NotoSansSC-Bold.ttf")
FONT_MONO = os.path.join(FONT_DIR, "JetBrainsMono-Regular.ttf")

def load_fonts():
    """Load fonts with fallback"""
    fonts = {}
    try:
        # 尝试加载思源黑体
        if os.path.exists(FONT_REGULAR):
            fonts['regular'] = ImageFont.truetype(FONT_REGULAR, 12)
            fonts['small'] = ImageFont.truetype(FONT_REGULAR, 11)
        else:
            # 使用系统中文字体
            fonts['regular'] = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 12)
            fonts['small'] = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 11)

        if os.path.exists(FONT_BOLD):
            fonts['bold'] = ImageFont.truetype(FONT_BOLD, 12)
        else:
            fonts['bold'] = ImageFont.truetype("C:\\Windows\\Fonts\\msyhbd.ttc", 12)

    except Exception as e:
        print(f"Font loading error: {e}, using default")
        default = ImageFont.load_default()
        fonts['regular'] = default
        fonts['small'] = default
        fonts['bold'] = default
    return fonts

def draw_rounded_rect(draw, coords, radius, fill=None, outline=None, width=1):
    """Draw a rounded rectangle"""
    x1, y1, x2, y2 = coords

    if radius <= 0:
        if fill:
            draw.rectangle([x1, y1, x2, y2], fill=fill)
        if outline:
            draw.rectangle([x1, y1, x2, y2], outline=outline, width=width)
        return

    if fill:
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill)
        draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill)
        draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill)
        draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill)

    if outline:
        draw.arc([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=outline, width=width)
        draw.arc([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=outline, width=width)
        draw.arc([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=outline, width=width)
        draw.arc([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=outline, width=width)
        draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
        draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
        draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
        draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)

def add_preset_template_section(img, fonts):
    """在现有图像上添加预设模板部分 - 作为独立的可折叠区域"""
    draw = ImageDraw.Draw(img)

    # 从原图中直接采样颜色，确保完全匹配
    panel_bg = img.getpixel((1200, 400))  # 面板背景色
    section_header_bg = img.getpixel((1200, 175))  # section标题栏背景 (字壳工艺位置)
    input_bg = img.getpixel((1250, 213))  # 输入框背景色
    input_border = img.getpixel((1310, 213))  # 输入框边框色

    # 右侧面板的位置
    panel_x = 1090
    panel_width = 295

    # 预设模板区域位置 - 放在"字壳工艺"section位置
    section_start_y = 155
    section_total_height = 160  # 增加高度，完全覆盖原有内容

    # 首先用面板背景色覆盖该区域
    draw.rectangle([panel_x + 1, section_start_y, panel_x + panel_width, section_start_y + section_total_height],
                   fill=panel_bg)

    # 1. 绘制"预设模板"可折叠标题栏 - 匹配原有section样式
    header_y = section_start_y
    header_height = 32

    # 标题栏背景 - 使用采样的section背景色
    draw.rectangle([panel_x + 1, header_y, panel_x + panel_width, header_y + header_height],
                   fill=section_header_bg)

    # 折叠箭头 (▼ 展开状态) - 青色
    arrow_color = (0, 168, 232)  # #00a8e8
    arrow_x = panel_x + 12
    arrow_y = header_y + 13
    draw.polygon([(arrow_x, arrow_y), (arrow_x + 8, arrow_y), (arrow_x + 4, arrow_y + 5)],
                 fill=arrow_color)

    # 复选框
    checkbox_x = panel_x + 28
    checkbox_y = header_y + 9
    checkbox_size = 14
    checkbox_border = (74, 80, 96)  # 采样的复选框边框色
    draw_rounded_rect(draw, [checkbox_x, checkbox_y, checkbox_x + checkbox_size, checkbox_y + checkbox_size],
                     2, outline=checkbox_border)

    # 标题文字 "预设模板"
    draw.text((panel_x + 50, header_y + 9), "预设模板",
              fill=(255, 255, 255), font=fonts['regular'])

    # 2. 内容区域
    content_y = header_y + header_height + 10
    content_x = panel_x + 15
    content_width = panel_width - 30

    # 下拉选择框 - 使用采样的输入框颜色
    dropdown_height = 30

    draw_rounded_rect(draw, [content_x, content_y, content_x + content_width, content_y + dropdown_height],
                     4, fill=input_bg, outline=input_border)

    # 下拉框文字
    draw.text((content_x + 12, content_y + 8), "30cm 斜边模板",
              fill=(255, 255, 255), font=fonts['regular'])

    # 下拉箭头
    arr_x = content_x + content_width - 22
    arr_y = content_y + 13
    draw.polygon([(arr_x, arr_y), (arr_x + 10, arr_y), (arr_x + 5, arr_y + 6)],
                 fill=(96, 104, 112))

    # 3. 三个操作按钮：保存、另存为、删除
    button_y = content_y + dropdown_height + 10
    button_height = 28
    button_gap = 8
    button_width = (content_width - button_gap * 2) // 3

    button_texts = ["保存", "另存为", "删除"]

    for i, text in enumerate(button_texts):
        btn_x = content_x + i * (button_width + button_gap)
        draw_rounded_rect(draw, [btn_x, button_y, btn_x + button_width, button_y + button_height],
                         4, fill=section_header_bg, outline=input_border)

        # 按钮文字居中
        bbox = draw.textbbox((0, 0), text, font=fonts['regular'])
        text_width = bbox[2] - bbox[0]
        text_x = btn_x + (button_width - text_width) // 2
        draw.text((text_x, button_y + 7), text,
                  fill=(180, 180, 180), font=fonts['regular'])

    return img

def generate_ui():
    """Main function to add preset template to existing UI"""
    # 加载现有的UI图像
    original_path = r"E:\SignMaker Slicer\docs\UI\UI_Modern.png"

    if not os.path.exists(original_path):
        print(f"Error: Original UI file not found: {original_path}")
        return None

    img = Image.open(original_path)
    print(f"Loaded original UI: {img.size}")

    # Load fonts
    fonts = load_fonts()

    # 在现有图像上添加预设模板部分
    img = add_preset_template_section(img, fonts)

    # Save image
    output_path = r"E:\SignMaker Slicer\docs\UI\UI_Modern_WithPresets.png"
    img.save(output_path, 'PNG')
    print(f"UI with presets generated: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_ui()
