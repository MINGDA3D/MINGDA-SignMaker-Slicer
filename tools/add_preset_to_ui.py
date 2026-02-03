"""
在现有 UI_Modern.png 基础上添加预设模板功能
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 颜色定义
COLORS = {
    'bg_panel': '#252526',
    'bg_input': '#3c3c3c',
    'bg_button': '#0078d4',
    'border': '#555555',
    'text_primary': '#cccccc',
    'text_white': '#ffffff',
    'text_secondary': '#888888',
    'accent_blue': '#4fc3f7',
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def load_font(size):
    """尝试加载系统字体"""
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/segoeui.ttf",  # Segoe UI
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

def add_preset_template_section(img):
    """在右侧面板添加预设模板区域"""
    draw = ImageDraw.Draw(img)

    # 加载字体
    font_title = load_font(14)
    font_normal = load_font(12)
    font_small = load_font(11)

    # 右侧面板的位置 (根据原图分析)
    # 原图中右侧面板大约从 x=1600 开始，宽度约320
    panel_x = 1600
    panel_width = 320

    # 预设模板区域起始位置（在"工艺类型"区域下方）
    # 原图中工艺类型区域大约在 y=76 到 y=200
    # 我们需要在工艺类型和基础参数之间插入预设模板

    # 首先，清除一部分区域来放置预设模板
    # 在 y=195 到 y=330 之间添加预设模板区域
    preset_y = 195

    # 绘制预设模板区域背景
    draw.rectangle([panel_x, preset_y, panel_x + panel_width, preset_y + 145],
                   fill=hex_to_rgb(COLORS['bg_panel']))

    # 分隔线
    draw.rectangle([panel_x + 15, preset_y, panel_x + panel_width - 15, preset_y + 1],
                   fill=hex_to_rgb('#4a4a4a'))

    py = preset_y + 15

    # 预设模板标题
    draw.text((panel_x + 15, py), "⭐ 预设模板",
              fill=hex_to_rgb(COLORS['accent_blue']), font=font_title)
    py += 25

    # 下拉选择框
    draw.rounded_rectangle([panel_x + 15, py, panel_x + panel_width - 15, py + 28],
                           radius=4,
                           fill=hex_to_rgb(COLORS['bg_input']),
                           outline=hex_to_rgb(COLORS['border']))
    draw.text((panel_x + 25, py + 6), "30cm斜边字（常用）",
              fill=hex_to_rgb(COLORS['text_white']), font=font_normal)
    draw.text((panel_x + panel_width - 35, py + 6), "▼",
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_normal)
    py += 35

    # 预设列表提示
    presets = ['✓ 30cm斜边字（常用）', '  50cm直边字']
    for preset in presets:
        draw.text((panel_x + 25, py), preset,
                  fill=hex_to_rgb(COLORS['text_secondary']), font=font_small)
        py += 18
    py += 5

    # 智能推荐按钮
    btn_width = panel_width - 30
    draw.rounded_rectangle([panel_x + 15, py, panel_x + 15 + btn_width, py + 32],
                           radius=4,
                           fill=hex_to_rgb(COLORS['bg_button']))
    draw.text((panel_x + 15 + btn_width//2 - 38, py + 8), "⚡ 智能推荐",
              fill=hex_to_rgb(COLORS['text_white']), font=font_title)
    py += 40

    # 底部分隔线
    draw.rectangle([panel_x + 15, py, panel_x + panel_width - 15, py + 1],
                   fill=hex_to_rgb('#4a4a4a'))

    return img

def main():
    # 加载原始图片
    input_path = r"E:\MINGDA SignMaker\docs\UI\UI_Modern.png"
    output_path = r"E:\MINGDA SignMaker\docs\UI\UI_Modern_WithPresets.png"

    print(f"Loading original UI: {input_path}")
    img = Image.open(input_path)

    # 添加预设模板区域
    print("Adding preset template section...")
    img = add_preset_template_section(img)

    # 保存结果
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG', quality=95)
    print(f"UI with presets saved to: {output_path}")
    print("Done!")

if __name__ == "__main__":
    main()
