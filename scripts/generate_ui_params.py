"""
SignMaker Slicer - 参数设置界面
根据实际UI界面和INC-S文档生成
分为两张图片：Part1 (预设+1-6) 和 Part2 (7-11+机器设置)
"""

from PIL import Image, ImageDraw, ImageFont
import os

# ============================================
# 配色方案 - 与预览界面保持一致
# ============================================
COLORS = {
    "bg_base": "#0A0E14",
    "bg_primary": "#0D1219",
    "bg_secondary": "#131A24",
    "bg_card": "#1A2332",
    "bg_elevated": "#1F2A3C",
    "bg_hover": "#253345",
    "bg_input": "#0D1219",
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
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) for k, v in COLORS.items()}

WIDTH = 480

# 字体加载
try:
    font_title = ImageFont.truetype("msyh.ttc", 14)
    font_section = ImageFont.truetype("msyh.ttc", 12)
    font_label = ImageFont.truetype("msyh.ttc", 11)
    font_small = ImageFont.truetype("msyh.ttc", 9)
    font_value = ImageFont.truetype("consola.ttf", 10)
except:
    font_title = font_section = font_label = font_small = font_value = ImageFont.load_default()


class ParamsRenderer:
    def __init__(self, width, height):
        self.width = width
        self.img = Image.new('RGB', (width, height), C["bg_base"])
        self.draw = ImageDraw.Draw(self.img)
        self.margin = 12
        self.content_w = width - self.margin * 2
        self.y = 12

    def draw_rounded_rect(self, x, y, w, h, r, fill=None, outline=None, width=1):
        self.draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline, width=width)

    def draw_text(self, x, y, text, font=None, fill=None):
        self.draw.text((x, y), text, font=font or font_label, fill=fill or C["text_secondary"])

    def draw_checkbox(self, x, y, checked=False, size=14):
        if checked:
            self.draw_rounded_rect(x, y, size, size, 3, fill=C["accent_primary"])
            self.draw.line([(x+3, y+7), (x+5, y+10)], fill=(255, 255, 255), width=2)
            self.draw.line([(x+5, y+10), (x+11, y+4)], fill=(255, 255, 255), width=2)
        else:
            self.draw_rounded_rect(x, y, size, size, 3, fill=C["bg_input"], outline=C["border_default"])

    def draw_input(self, x, y, w, h, value="", unit=""):
        self.draw_rounded_rect(x, y, w, h, 4, fill=C["bg_input"], outline=C["border_default"])
        self.draw_text(x + 6, y + (h - 10) // 2, str(value), font_value, C["text_primary"])
        if unit:
            self.draw_text(x + w + 4, y + (h - 9) // 2, unit, font_small, C["text_muted"])

    def draw_dropdown(self, x, y, w, h, value=""):
        self.draw_rounded_rect(x, y, w, h, 4, fill=C["bg_input"], outline=C["border_default"])
        self.draw_text(x + 6, y + (h - 11) // 2, value, font_label, C["text_primary"])
        arrow_x = x + w - 14
        arrow_y = y + h // 2
        self.draw.polygon([(arrow_x, arrow_y - 2), (arrow_x + 8, arrow_y - 2), (arrow_x + 4, arrow_y + 3)],
                     fill=C["text_muted"])

    def draw_button(self, x, y, w, h, text, primary=False, color=None):
        if color:
            fill_color = color
        elif primary:
            fill_color = C["accent_primary"]
        else:
            fill_color = C["bg_elevated"]

        self.draw_rounded_rect(x, y, w, h, 4, fill=fill_color)
        bbox = self.draw.textbbox((0, 0), text, font=font_small)
        text_w = bbox[2] - bbox[0]
        text_x = x + (w - text_w) // 2
        text_y = y + (h - 10) // 2
        self.draw_text(text_x, text_y, text, font_small, (255, 255, 255) if primary or color else C["text_secondary"])

    def draw_radio_group(self, x, y, options, selected=0, btn_w=None, btn_h=22, total_w=None):
        gap = 4
        # 如果没有指定按钮宽度，则根据总宽度等分
        if btn_w is None and total_w is not None:
            btn_w = (total_w - gap * (len(options) - 1)) // len(options)
        elif btn_w is None:
            btn_w = 55  # 默认宽度

        for i, opt in enumerate(options):
            bx = x + i * (btn_w + gap)
            if i == selected:
                self.draw_rounded_rect(bx, y, btn_w, btn_h, 4, fill=C["accent_primary"])
                # 文字居中
                bbox = self.draw.textbbox((0, 0), opt, font=font_small)
                text_w = bbox[2] - bbox[0]
                text_x = bx + (btn_w - text_w) // 2
                self.draw_text(text_x, y + 4, opt, font_small, (255, 255, 255))
            else:
                self.draw_rounded_rect(bx, y, btn_w, btn_h, 4, fill=C["bg_elevated"])
                bbox = self.draw.textbbox((0, 0), opt, font=font_small)
                text_w = bbox[2] - bbox[0]
                text_x = bx + (btn_w - text_w) // 2
                self.draw_text(text_x, y + 4, opt, font_small, C["text_muted"])

    def draw_radio_row(self, label, options, selected=0):
        """绘制带标签的单选按钮行"""
        x = self.margin + 8
        label_w = 90
        self.draw_text(x, self.y + 4, label, font_label, C["text_secondary"])
        radio_x = self.margin + label_w + 16
        radio_w = self.content_w - label_w - 24
        self.draw_radio_group(radio_x, self.y, options, selected, total_w=radio_w)
        self.y += 28

    def draw_dropdown_row(self, label, value):
        """绘制带标签的下拉框行"""
        x = self.margin + 8
        label_w = 90
        self.draw_text(x, self.y + 4, label, font_label, C["text_secondary"])
        dropdown_x = self.margin + label_w + 16
        dropdown_w = self.content_w - label_w - 24
        self.draw_dropdown(dropdown_x, self.y, dropdown_w, 22, value)
        self.y += 28

    def draw_section_header(self, title, expanded=True, has_checkbox=False, checked=False):
        x = self.margin
        w = self.content_w
        self.draw_rounded_rect(x, self.y, w, 28, 6, fill=C["bg_card"])

        tri_x = x + 10
        tri_y = self.y + 10
        if expanded:
            self.draw.polygon([(tri_x, tri_y), (tri_x + 8, tri_y), (tri_x + 4, tri_y + 5)],
                         fill=C["accent_primary"])
        else:
            self.draw.polygon([(tri_x, tri_y), (tri_x + 5, tri_y + 4), (tri_x, tri_y + 8)],
                         fill=C["text_muted"])

        text_x = tri_x + 14
        if has_checkbox:
            self.draw_checkbox(text_x, self.y + 7, checked, 14)
            text_x += 20

        self.draw_text(text_x, self.y + 7, title, font_section, C["text_primary"])
        self.y += 32

    def draw_param_row(self, label, value, unit="", input_w=None):
        x = self.margin + 8
        label_w = 90  # 标签区域宽度
        self.draw_text(x, self.y + 4, label, font_label, C["text_secondary"])
        input_x = self.margin + label_w + 16
        # 输入框延伸到右边界，留出单位空间
        if input_w is None:
            unit_space = 30 if unit else 8
            input_w = self.content_w - label_w - 24 - unit_space
        self.draw_input(input_x, self.y, input_w, 22, value, unit)
        self.y += 26

    def add_space(self, h=8):
        self.y += h

    def crop_to_content(self):
        return self.img.crop((0, 0, self.width, self.y + 12))


def generate_part1():
    """生成参数设置 Part 1 (预设模板 + 分组 1-6)"""
    renderer = ParamsRenderer(WIDTH, 2800)
    m = renderer.margin

    # 页面标题
    renderer.draw_text(m, renderer.y, "参数设置", font_title, C["text_primary"])
    renderer.y += 28

    # ============================================
    # 预设模板区域
    # ============================================
    renderer.draw_section_header("预设模板", expanded=True)

    # 下拉选择器
    renderer.draw_dropdown(m + 8, renderer.y, renderer.content_w - 16, 28, "30cm勾边字")
    renderer.y += 36

    # 常用标签 - 等分宽度
    renderer.draw_text(m + 8, renderer.y, "常用", font_small, C["text_muted"])
    renderer.y += 18

    tags = ["勾边字", "包边字", "连襟字", "围边字"]
    # 计算等分宽度
    available_width = renderer.content_w - 16  # 两边各留8px边距
    tag_gap = 6  # 标签之间的间距
    tag_count = len(tags)
    tag_w = (available_width - tag_gap * (tag_count - 1)) // tag_count

    tag_x = m + 8
    for i, tag in enumerate(tags):
        if i == 0:
            renderer.draw_rounded_rect(tag_x, renderer.y, tag_w, 24, 4, fill=C["accent_primary"])
            # 文字居中
            bbox = renderer.draw.textbbox((0, 0), tag, font=font_small)
            text_w = bbox[2] - bbox[0]
            text_x = tag_x + (tag_w - text_w) // 2
            renderer.draw_text(text_x, renderer.y + 5, tag, font_small, (255, 255, 255))
        else:
            renderer.draw_rounded_rect(tag_x, renderer.y, tag_w, 24, 4, fill=C["bg_elevated"])
            bbox = renderer.draw.textbbox((0, 0), tag, font=font_small)
            text_w = bbox[2] - bbox[0]
            text_x = tag_x + (tag_w - text_w) // 2
            renderer.draw_text(text_x, renderer.y + 5, tag, font_small, C["text_secondary"])
        tag_x += tag_w + tag_gap
    renderer.y += 32

    # 快速参数 - 等分宽度
    quick_params = [("字壳高度", "30", "mm"), ("壁厚", "1.2", "mm"), ("层高", "0.3", "mm")]
    param_count = len(quick_params)
    param_gap = 8
    param_w = (available_width - param_gap * (param_count - 1)) // param_count
    input_w = param_w - 4  # 输入框宽度略小

    qp_x = m + 8
    for label, value, unit in quick_params:
        # 标签居中
        bbox = renderer.draw.textbbox((0, 0), label, font=font_small)
        label_w = bbox[2] - bbox[0]
        label_x = qp_x + (input_w - label_w) // 2
        renderer.draw_text(label_x, renderer.y, label, font_small, C["text_muted"])

        # 输入框
        renderer.draw_rounded_rect(qp_x, renderer.y + 14, input_w, 24, 4, fill=C["bg_elevated"])

        # 数值和单位居中
        value_unit = value + " " + unit
        bbox = renderer.draw.textbbox((0, 0), value_unit, font=font_value)
        value_w = bbox[2] - bbox[0]
        value_x = qp_x + (input_w - value_w) // 2
        renderer.draw_text(value_x, renderer.y + 20, value_unit, font_value, C["text_primary"])

        qp_x += param_w + param_gap

    renderer.y += 50
    renderer.add_space()

    # ============================================
    # 1. 字壳工艺
    # ============================================
    renderer.draw_section_header("字壳工艺", expanded=True)

    # 打印模式
    renderer.draw_radio_row("打印模式", ["镜像打印", "正常打印"], selected=1)

    # 字边类型
    renderer.draw_radio_row("字边类型", ["直边", "斜边", "异形边"], selected=1)

    params_1 = [
        ("字壳高度", "30", "mm"),
        ("斜边宽度", "5", "mm"),
        ("面板厚度", "3", "mm"),
        ("底板厚度", "10", "mm"),
        ("层高", "0.3", "mm"),
        ("壁厚", "1.2", "mm"),
        ("壁厚补偿", "0", "mm"),
        ("走线次数", "1", "次"),
        ("走线偏移", "0.8", "mm"),
        ("预打边线偏移", "20", "mm"),
        ("预打边线次数", "1", "次"),
    ]
    for label, value, unit in params_1:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 2. 换色层设置
    # ============================================
    renderer.draw_section_header("换色层设置", expanded=True, has_checkbox=True, checked=True)

    renderer.draw_text(m + 8, renderer.y + 2, "换色层数 (最多7层)", font_small, C["text_muted"])
    renderer.y += 18

    color_layers = [
        ("1", "10", "1", True, C["extruder_1"]),
        ("2", "5", "2", True, C["extruder_2"]),
        ("3", "5", "3", True, C["extruder_3"]),
        ("4", "10", "1", True, C["extruder_1"]),
        ("5", "0", "1", False, C["extruder_1"]),
    ]

    for layer_num, height, ext, enabled, color in color_layers:
        x = m + 8
        if enabled:
            renderer.draw_rounded_rect(x, renderer.y + 2, 4, 18, 2, fill=color)
        renderer.draw_text(x + 10, renderer.y + 4, f"层{layer_num}", font_small, C["text_primary"] if enabled else C["text_muted"])
        renderer.draw_input(x + 50, renderer.y, 45, 20, height, "mm")
        renderer.draw_text(x + 130, renderer.y + 4, "挤出机", font_small, C["text_muted"])
        renderer.draw_dropdown(x + 175, renderer.y, 45, 20, ext)
        renderer.draw_checkbox(x + 235, renderer.y + 3, enabled, 14)
        renderer.y += 24

    renderer.draw_button(m + 8, renderer.y, 100, 24, "+ 添加换色层")
    renderer.y += 32

    # 启用喷头2
    renderer.draw_text(m + 8, renderer.y + 2, "启用喷头2 (双层壁厚)", font_label, C["text_secondary"])
    renderer.draw_checkbox(m + 160, renderer.y, False, 14)
    renderer.y += 24

    params_ext = [
        ("双层吐丝宽度", "1.2", "mm"),
        ("双层走线偏移", "0.8", "mm"),
    ]
    for label, value, unit in params_ext:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 3. 台阶/V槽
    # ============================================
    renderer.draw_section_header("台阶/V槽", expanded=True, has_checkbox=True, checked=True)

    renderer.draw_text(m + 8, renderer.y + 2, "台阶数量 (最多7个)", font_small, C["text_muted"])
    renderer.y += 18

    # 表头
    renderer.draw_text(m + 8, renderer.y, "序号", font_small, C["text_muted"])
    renderer.draw_text(m + 50, renderer.y, "位置", font_small, C["text_muted"])
    renderer.draw_text(m + 125, renderer.y, "高度", font_small, C["text_muted"])
    renderer.draw_text(m + 200, renderer.y, "宽度", font_small, C["text_muted"])
    renderer.draw_text(m + 275, renderer.y, "启用", font_small, C["text_muted"])
    renderer.y += 16

    steps = [
        ("1", "4", "1.2", "1.2", True),
        ("2", "27", "1.2", "1.2", True),
        ("3", "0", "0", "0", False),
    ]

    for step_num, pos, height, width, enabled in steps:
        renderer.draw_text(m + 12, renderer.y + 4, step_num, font_small, C["text_primary"] if enabled else C["text_muted"])
        renderer.draw_input(m + 40, renderer.y, 50, 20, pos)
        renderer.draw_input(m + 115, renderer.y, 50, 20, height)
        renderer.draw_input(m + 190, renderer.y, 50, 20, width)
        renderer.draw_checkbox(m + 280, renderer.y + 3, enabled, 14)
        renderer.y += 24

    renderer.y += 4
    params_step = [
        ("台阶速度", "30", "mm/s"),
        ("台阶厚度", "0.3", "mm"),
    ]
    for label, value, unit in params_step:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 4. 防翘裙边
    # ============================================
    renderer.draw_section_header("防翘裙边", expanded=True, has_checkbox=True, checked=True)

    renderer.draw_radio_row("防翘位置", ["外防翘", "内防翘"], selected=0)

    params_5 = [
        ("压线宽度", "0.5", "mm"),
        ("吐丝宽度", "1.2", "mm"),
        ("防翘速度", "30", "mm/s"),
        ("防翘高度", "0.3", "mm"),
        ("防翘长度", "10", "mm"),
        ("V型开口宽度", "3", "mm"),
    ]
    for label, value, unit in params_5:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 5. 连襟字
    # ============================================
    renderer.draw_section_header("连襟字", expanded=True, has_checkbox=True, checked=False)

    renderer.draw_radio_row("连襟类型", ["三角形", "菱形"], selected=0)

    params_6 = [
        ("连襟宽度", "15", "mm"),
        ("连襟高度", "5", "mm"),
        ("连襟底座高度", "5", "mm"),
        ("连襟支撑偏移", "2.5", "mm"),
    ]
    for label, value, unit in params_6:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 6. 包边勾边
    # ============================================
    renderer.draw_section_header("包边勾边", expanded=True)

    # 勾边/包边有效 - 使用全宽布局
    check_row_w = renderer.content_w - 16
    half_w = check_row_w // 2
    renderer.draw_text(m + 8, renderer.y + 2, "勾边有效", font_label, C["text_secondary"])
    renderer.draw_checkbox(m + 80, renderer.y, True, 14)
    renderer.draw_text(m + 8 + half_w, renderer.y + 2, "包边有效", font_label, C["text_secondary"])
    renderer.draw_checkbox(m + 80 + half_w, renderer.y, False, 14)
    renderer.y += 24

    renderer.draw_radio_row("位置", ["内部", "外部"], selected=0)

    params_7 = [
        ("勾边高度", "1.2", "mm"),
        ("包边高度", "1.2", "mm"),
        ("勾包边宽度", "3", "mm"),
        ("勾包边速度", "30", "mm/s"),
        ("吐丝宽度", "1.2", "mm"),
    ]
    for label, value, unit in params_7:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space(16)

    img = renderer.crop_to_content()
    return img


def generate_part2():
    """生成参数设置 Part 2 (分组 7-11)"""
    renderer = ParamsRenderer(WIDTH, 2400)
    m = renderer.margin

    # 页面标题
    renderer.draw_text(m, renderer.y, "参数设置 (续)", font_title, C["text_primary"])
    renderer.y += 28

    # ============================================
    # 7. 面板设置
    # ============================================
    renderer.draw_section_header("面板设置", expanded=True, has_checkbox=True, checked=True)

    # 填充类型 - 使用等分按钮
    renderer.draw_radio_row("填充类型", ["面板", "网格", "底板"], selected=0)

    params_panel = [
        ("填充间距", "8", "mm"),
        ("填充间距2", "0.9", "mm"),
        ("边界距离", "1.4", "mm"),
        ("角度", "45", "度"),
        ("填充高度", "0.6", "mm"),
        ("填充速度", "40", "mm/s"),
        ("吐丝宽度", "1.2", "mm"),
    ]
    for label, value, unit in params_panel:
        renderer.draw_param_row(label, value, unit)

    renderer.draw_dropdown_row("填充模式", "自动连接")

    renderer.draw_radio_row("指定挤出机", ["无", "2号", "3号"], selected=0)

    # 复选框行 - 等分布局
    check_row_w = renderer.content_w - 16
    half_w = check_row_w // 2
    renderer.draw_checkbox(m + 8, renderer.y + 2, True, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "连襟不参与", font_small, C["text_secondary"])
    renderer.draw_checkbox(m + 8 + half_w, renderer.y + 2, True, 14)
    renderer.draw_text(m + 28 + half_w, renderer.y + 2, "面板不参与", font_small, C["text_secondary"])
    renderer.y += 28

    # 花纹设置
    renderer.draw_text(m + 8, renderer.y + 2, "面板花纹", font_label, C["text_secondary"])
    renderer.draw_checkbox(renderer.margin + 106, renderer.y, False, 14)
    renderer.y += 24

    params_pattern = [
        ("花纹高度", "0.2", "mm"),
        ("花纹速度", "40", "mm/s"),
    ]
    for label, value, unit in params_pattern:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 8. 底板设置
    # ============================================
    renderer.draw_section_header("底板设置", expanded=True, has_checkbox=True, checked=False)

    params_base = [
        ("填充间距", "0.95", "mm"),
        ("边界距离", "1.4", "mm"),
        ("角度", "45", "度"),
        ("填充高度", "1.5", "mm"),
        ("填充速度", "50", "mm/s"),
    ]
    for label, value, unit in params_base:
        renderer.draw_param_row(label, value, unit)

    renderer.draw_dropdown_row("填充模式", "自动连接")

    # 生成底板DXF
    renderer.draw_checkbox(m + 8, renderer.y + 2, True, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "生成底板 DXF", font_label, C["text_secondary"])
    renderer.y += 24

    renderer.draw_param_row("对齐补偿", "-0.4", "mm")

    # 生成面板DXF
    renderer.draw_checkbox(m + 8, renderer.y + 2, True, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "生成面板 DXF", font_label, C["text_secondary"])
    renderer.y += 24

    renderer.draw_param_row("对齐补偿", "0", "mm")

    renderer.add_space()

    # ============================================
    # 9. 速度设置
    # ============================================
    renderer.draw_section_header("速度设置", expanded=True)

    params_speed = [
        ("打印速度", "40", "mm/s"),
        ("首层打印速度", "30", "mm/s"),
        ("空程速度", "300", "mm/s"),
        ("换色速度", "30", "mm/s"),
        ("台阶速度", "30", "mm/s"),
        ("勾包边速度", "30", "mm/s"),
        ("防翘速度", "30", "mm/s"),
    ]
    for label, value, unit in params_speed:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 10. 填充
    # ============================================
    renderer.draw_section_header("填充", expanded=True)

    params_fill = [
        ("填充密度", "20", "%"),
        ("填充角度", "45", "度"),
    ]
    for label, value, unit in params_fill:
        renderer.draw_param_row(label, value, unit)

    renderer.draw_dropdown_row("填充图案", "线性")

    renderer.draw_checkbox(m + 8, renderer.y + 2, True, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "生成内填充", font_small, C["text_secondary"])
    renderer.y += 26

    renderer.add_space()

    # ============================================
    # 11. 机器设置
    # ============================================
    renderer.draw_section_header("机器设置", expanded=True)

    # 机器类型
    renderer.draw_dropdown_row("机台类型", "AD-F4 (800×1200mm)")

    params_machine = [
        ("喷头1温度", "220", "°C"),
        ("喷头2温度", "220", "°C"),
        ("喷头3温度", "220", "°C"),
        ("材料直径", "1.75", "mm"),
        ("抬头回抽", "3", "mm"),
        ("换料回抽", "30", "mm"),
        ("换料补偿", "20", "mm"),
    ]
    for label, value, unit in params_machine:
        renderer.draw_param_row(label, value, unit)

    renderer.y += 4

    # 其他选项 - 等分布局
    check_row_w = renderer.content_w - 16
    half_w = check_row_w // 2
    renderer.draw_checkbox(m + 8, renderer.y + 2, False, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "头尾交替打印", font_small, C["text_secondary"])
    renderer.draw_checkbox(m + 8 + half_w, renderer.y + 2, False, 14)
    renderer.draw_text(m + 28 + half_w, renderer.y + 2, "结束完成不回抽", font_small, C["text_secondary"])
    renderer.y += 28

    # 模板操作 - 等分按钮
    btn_gap = 8
    btn_count = 2
    btn_w = (renderer.content_w - 16 - btn_gap * (btn_count - 1)) // btn_count
    renderer.draw_button(m + 8, renderer.y, btn_w, 24, "保存模板")
    renderer.draw_button(m + 8 + btn_w + btn_gap, renderer.y, btn_w, 24, "读取模板")
    renderer.y += 36

    renderer.add_space()

    # ============================================
    # 底部操作按钮
    # ============================================
    btn_gap = 8
    btn_count = 3
    btn_w = (renderer.content_w - btn_gap * (btn_count - 1)) // btn_count
    renderer.draw_button(m, renderer.y, btn_w, 36, "计算路径", primary=True)
    renderer.draw_button(m + btn_w + btn_gap, renderer.y, btn_w, 36, "预览字边")
    renderer.draw_button(m + (btn_w + btn_gap) * 2, renderer.y, btn_w, 36, "文件输出", primary=True)
    renderer.y += 48

    img = renderer.crop_to_content()
    return img


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(output_dir, exist_ok=True)

    # 生成 Part 1
    img1 = generate_part1()
    path1 = os.path.join(output_dir, "UI_Params_Part1.png")
    img1.save(path1, "PNG", quality=95)
    print(f"Saved: {path1} ({img1.width}x{img1.height})")

    root_path1 = os.path.join(os.path.dirname(__file__), "..", "UI_Params_Part1.png")
    img1.save(root_path1, "PNG", quality=95)
    print(f"Saved: {root_path1}")

    # 生成 Part 2
    img2 = generate_part2()
    path2 = os.path.join(output_dir, "UI_Params_Part2.png")
    img2.save(path2, "PNG", quality=95)
    print(f"Saved: {path2} ({img2.width}x{img2.height})")

    root_path2 = os.path.join(os.path.dirname(__file__), "..", "UI_Params_Part2.png")
    img2.save(root_path2, "PNG", quality=95)
    print(f"Saved: {root_path2}")

    print("\nParams UI generated successfully!")
    print("  - UI_Params_Part1.png (Preset + Sections 1-6)")
    print("  - UI_Params_Part2.png (Sections 7-11)")


if __name__ == "__main__":
    main()
