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

    def draw_radio_group(self, x, y, options, selected=0, btn_w=None, btn_h=26, total_w=None):
        """
        现代分段控制器 - iOS风格
        外层容器 + 选中项高亮背景
        """
        gap = 2
        padding = 3

        # 计算按钮宽度
        if btn_w is None and total_w is not None:
            inner_w = total_w - padding * 2
            btn_w = (inner_w - gap * (len(options) - 1)) // len(options)
        elif btn_w is None:
            btn_w = 60

        container_w = btn_w * len(options) + gap * (len(options) - 1) + padding * 2
        container_h = btn_h + padding * 2

        # 外层容器 - 深色背景
        self.draw_rounded_rect(x, y, container_w, container_h, 6,
                               fill=C["bg_input"], outline=C["border_subtle"])

        btn_y = y + padding
        for i, opt in enumerate(options):
            bx = x + padding + i * (btn_w + gap)

            if i == selected:
                # 选中状态 - 高亮背景
                self.draw_rounded_rect(bx, btn_y, btn_w, btn_h, 4, fill=C["accent_primary"])
                # 文字
                bbox = self.draw.textbbox((0, 0), opt, font=font_small)
                text_w = bbox[2] - bbox[0]
                text_x = bx + (btn_w - text_w) // 2
                self.draw_text(text_x, btn_y + (btn_h - 10) // 2, opt, font_small, (255, 255, 255))
            else:
                # 未选中 - 透明背景
                bbox = self.draw.textbbox((0, 0), opt, font=font_small)
                text_w = bbox[2] - bbox[0]
                text_x = bx + (btn_w - text_w) // 2
                self.draw_text(text_x, btn_y + (btn_h - 10) // 2, opt, font_small, C["text_muted"])

    def draw_radio_row(self, label, options, selected=0):
        """绘制带标签的单选按钮行 - 使用紧凑型单选"""
        x = self.margin + 8
        label_w = 90
        self.draw_text(x, self.y + 2, label, font_label, C["text_secondary"])
        radio_x = self.margin + label_w + 16
        radio_w = self.content_w - label_w - 24
        self.draw_radio_buttons(radio_x, self.y, options, selected, total_w=radio_w)
        self.y += 24

    def draw_radio_buttons(self, x, y, options, selected=0, total_w=None):
        """
        紧凑型单选按钮 - 无边框
        ● 选中  ○ 未选中
        """
        gap = 6
        radio_size = 12

        if total_w is not None:
            item_w = (total_w - gap * (len(options) - 1)) // len(options)
        else:
            item_w = 80

        for i, opt in enumerate(options):
            ix = x + i * (item_w + gap)

            # 圆圈位置
            circle_x = ix + 4
            circle_y = y + 2

            if i == selected:
                # 选中 - 实心圆
                self.draw.ellipse([circle_x, circle_y, circle_x + radio_size, circle_y + radio_size],
                                 fill=C["accent_primary"])
                # 内部小白点
                inner_margin = 3
                self.draw.ellipse([circle_x + inner_margin, circle_y + inner_margin,
                                  circle_x + radio_size - inner_margin, circle_y + radio_size - inner_margin],
                                 fill=(255, 255, 255))
                text_color = C["text_primary"]
            else:
                # 未选中 - 空心圆
                self.draw.ellipse([circle_x, circle_y, circle_x + radio_size, circle_y + radio_size],
                                 outline=C["border_default"], width=1)
                text_color = C["text_muted"]

            # 文字
            text_x = circle_x + radio_size + 6
            self.draw_text(text_x, y + 1, opt, font_label, text_color)

    def draw_dropdown_row(self, label, value):
        """绘制带标签的下拉框行"""
        x = self.margin + 8
        self.draw_text(x, self.y + 4, label, font_label, C["text_secondary"])
        # 下拉框对齐输入框，宽度一致
        dropdown_w = 120  # 与输入框宽度一致
        center_x = self.margin + self.content_w // 2
        dropdown_x = center_x
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
        # 输入框固定宽度，靠中线对齐
        if input_w is None:
            input_w = 120  # 固定宽度（原80增大1.5倍）
        # 中线位置：面板宽度的一半
        center_x = self.margin + self.content_w // 2
        # 输入框左边缘对齐到中线
        input_x = center_x
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

    # 常用标签 - 紧凑型单选按钮
    renderer.draw_text(m + 8, renderer.y, "常用", font_small, C["text_muted"])
    renderer.y += 16

    tags = ["勾边字", "包边字", "连襟字", "无边字"]
    available_width = renderer.content_w - 16
    renderer.draw_radio_buttons(m + 8, renderer.y, tags, selected=0, total_w=available_width)
    renderer.y += 24

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

    # 基本参数
    params_basic = [
        ("字壳高度", "30", "mm"),
        ("层高", "0.3", "mm"),
        ("壁厚", "1.2", "mm"),
        ("壁厚补偿", "0", "mm"),
    ]
    for label, value, unit in params_basic:
        renderer.draw_param_row(label, value, unit)

    # 顶部(Top)参数 - 新增（借鉴SASM3D）
    renderer.draw_text(m + 8, renderer.y + 2, "顶部参数 (Top)", font_small, C["accent_secondary"])
    renderer.y += 18
    params_top = [
        ("台阶高度", "3.0", "mm"),
        ("台阶宽度", "0.4", "mm"),
    ]
    for label, value, unit in params_top:
        renderer.draw_param_row(label, value, unit)

    # 斜边参数
    renderer.draw_text(m + 8, renderer.y + 2, "斜边参数", font_small, C["accent_secondary"])
    renderer.y += 18
    params_bevel = [
        ("斜边宽度", "5", "mm"),
        ("斜边角度", "75", "°"),
        ("面板厚度", "3", "mm"),
        ("底板厚度", "10", "mm"),
    ]
    for label, value, unit in params_bevel:
        renderer.draw_param_row(label, value, unit)

    # 底部(Bottom)参数 - 新增（借鉴SASM3D）
    renderer.draw_text(m + 8, renderer.y + 2, "底部参数 (Bottom)", font_small, C["accent_secondary"])
    renderer.y += 18
    params_bottom = [
        ("底边高度", "2.0", "mm"),
        ("凹槽高度", "2.0", "mm"),
    ]
    for label, value, unit in params_bottom:
        renderer.draw_param_row(label, value, unit)

    # 多层壁厚参数
    renderer.draw_text(m + 8, renderer.y + 2, "多层壁厚", font_small, C["accent_secondary"])
    renderer.y += 18
    params_wall = [
        ("走线次数", "1", "次"),
        ("走线高度", "0", "mm"),
        ("走线偏移", "0.8", "mm"),
    ]
    for label, value, unit in params_wall:
        renderer.draw_param_row(label, value, unit)

    # 字芯参数
    renderer.draw_text(m + 8, renderer.y + 2, "字芯参数", font_small, C["accent_secondary"])
    renderer.y += 18
    params_core = [
        ("字芯高度", "0", "mm"),
        ("字芯斜边宽度", "0", "mm"),
    ]
    for label, value, unit in params_core:
        renderer.draw_param_row(label, value, unit)

    # 预打边线参数
    renderer.draw_text(m + 8, renderer.y + 2, "预打边线 (Skirt)", font_small, C["accent_secondary"])
    renderer.y += 18
    params_skirt = [
        ("预打边线偏移", "20", "mm"),
        ("预打边线次数", "1", "次"),
    ]
    for label, value, unit in params_skirt:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 2. 换色层设置
    # ============================================
    renderer.draw_section_header("换色层设置", expanded=True, has_checkbox=True, checked=True)

    renderer.draw_text(m + 8, renderer.y + 2, "换色层数", font_small, C["text_muted"])
    renderer.y += 18

    color_layers = [
        ("1", "10", "1", True, C["extruder_1"]),
        ("2", "5", "2", True, C["extruder_2"]),
        ("3", "5", "3", True, C["extruder_3"]),
        ("4", "10", "1", True, C["extruder_1"]),
        ("5", "0", "1", False, C["extruder_1"]),
    ]

    # 换色层布局优化 - 均匀分布
    row_start = m + 8
    row_end = m + renderer.content_w - 8
    total_w = row_end - row_start  # 可用总宽度
    center_x = m + renderer.content_w // 2  # 中线位置

    # 布局分配
    col1_x = row_start  # 层号
    col2_x = row_start + 50  # 高度输入框
    col3_x = center_x  # 挤出机标签从中线开始
    col4_x = center_x + 60  # 挤出机下拉框
    col5_x = row_end - 18  # 复选框靠右

    for layer_num, height, ext, enabled, color in color_layers:
        # 色条指示器
        if enabled:
            renderer.draw_rounded_rect(col1_x, renderer.y + 2, 4, 18, 2, fill=color)

        # 层号标签
        renderer.draw_text(col1_x + 10, renderer.y + 4, f"层{layer_num}", font_small, C["text_primary"] if enabled else C["text_muted"])

        # 高度输入框
        renderer.draw_input(int(col2_x), renderer.y, 80, 20, height, "mm")

        # 挤出机标签 - 从中线开始
        renderer.draw_text(int(col3_x), renderer.y + 4, "挤出机", font_small, C["text_muted"])

        # 挤出机下拉框
        renderer.draw_dropdown(int(col4_x), renderer.y, 70, 20, ext)

        # 启用复选框
        renderer.draw_checkbox(int(col5_x), renderer.y + 3, enabled, 14)
        renderer.y += 24

    # 添加换色层按钮 - 居中对齐
    btn_w = 120
    btn_x = m + (renderer.content_w - btn_w) // 2
    renderer.draw_button(btn_x, renderer.y, btn_w, 24, "+ 添加换色层")
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

    renderer.draw_text(m + 8, renderer.y + 2, "台阶数量", font_small, C["text_muted"])
    renderer.y += 18

    # 台阶布局 - 均匀分布
    row_start = m + 8
    row_end = m + renderer.content_w - 8
    total_w = row_end - row_start

    # 列位置计算 - 序号和启用之间三等分
    col_seq = row_start  # 序号
    seq_w = 35  # 序号列宽度
    col_enable = row_end - 18  # 启用 - 与换色层复选框对齐

    # 中间区域三等分
    middle_start = row_start + seq_w
    middle_end = col_enable - 20  # 留出启用列空间
    middle_w = middle_end - middle_start
    third_w = middle_w // 3

    col_pos = middle_start  # 位置
    col_height = middle_start + third_w  # 高度
    col_width = middle_start + third_w * 2  # 宽度

    input_w = third_w - 10  # 输入框宽度，留出间距

    # 表头 - 文字与输入框居中对齐
    renderer.draw_text(int(col_seq), renderer.y, "序号", font_small, C["text_muted"])
    # 位置、高度、宽度居中于输入框
    renderer.draw_text(int(col_pos) + input_w // 2 - 10, renderer.y, "位置", font_small, C["text_muted"])
    renderer.draw_text(int(col_height) + input_w // 2 - 10, renderer.y, "高度", font_small, C["text_muted"])
    renderer.draw_text(int(col_width) + input_w // 2 - 10, renderer.y, "宽度", font_small, C["text_muted"])
    renderer.draw_text(int(col_enable) - 2, renderer.y, "启用", font_small, C["text_muted"])
    renderer.y += 16

    steps = [
        ("1", "4", "1.2", "1.2", True),
        ("2", "27", "1.2", "1.2", True),
        ("3", "0", "0", "0", False),
    ]

    for step_num, pos, height, width, enabled in steps:
        renderer.draw_text(int(col_seq) + 4, renderer.y + 4, step_num, font_small, C["text_primary"] if enabled else C["text_muted"])
        renderer.draw_input(int(col_pos), renderer.y, input_w, 20, pos)
        renderer.draw_input(int(col_height), renderer.y, input_w, 20, height)
        renderer.draw_input(int(col_width), renderer.y, input_w, 20, width)
        renderer.draw_checkbox(int(col_enable), renderer.y + 3, enabled, 14)
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

    renderer.draw_dropdown_row("指定挤出机", "无")

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
    # 10. 排版设置（新增）
    # ============================================
    renderer.draw_section_header("排版设置", expanded=True, has_checkbox=True, checked=True)

    # 排版模式
    renderer.draw_radio_row("排版模式", ["整版打印", "单个打印"], selected=1)

    # 边界设置
    renderer.draw_text(m + 8, renderer.y + 2, "边界设置", font_small, C["accent_secondary"])
    renderer.y += 18
    params_layout_border = [
        ("横轴边界距离", "10", "mm"),
        ("纵轴边界距离", "10", "mm"),
    ]
    for label, value, unit in params_layout_border:
        renderer.draw_param_row(label, value, unit)

    # 间隙设置
    renderer.draw_text(m + 8, renderer.y + 2, "图形间隙", font_small, C["accent_secondary"])
    renderer.y += 18
    params_layout_gap = [
        ("X图形间隙", "15", "mm"),
        ("Y图形间隙", "15", "mm"),
    ]
    for label, value, unit in params_layout_gap:
        renderer.draw_param_row(label, value, unit)

    renderer.add_space()

    # ============================================
    # 11. 输出设置（新增）
    # ============================================
    renderer.draw_section_header("输出设置", expanded=True)

    # 文件名
    renderer.draw_param_row("文件名", "output", "")

    # 导出选项
    renderer.draw_text(m + 8, renderer.y + 2, "导出格式", font_small, C["accent_secondary"])
    renderer.y += 18

    # G-code导出
    renderer.draw_checkbox(m + 8, renderer.y + 2, True, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "导出G-code (.gcode)", font_small, C["text_primary"])
    renderer.y += 22

    # STL导出（新增，借鉴SASM3D）
    renderer.draw_checkbox(m + 8, renderer.y + 2, False, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "导出STL (.stl)", font_small, C["text_secondary"])
    renderer.y += 22

    # PLT导出（新增）
    renderer.draw_checkbox(m + 8, renderer.y + 2, False, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "导出PLT (.plt)", font_small, C["text_secondary"])
    renderer.y += 22

    # DXF导出
    renderer.draw_checkbox(m + 8, renderer.y + 2, False, 14)
    renderer.draw_text(m + 28, renderer.y + 2, "导出DXF (.dxf)", font_small, C["text_secondary"])
    renderer.y += 26

    renderer.add_space()

    # ============================================
    # 12. 填充
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
    # 13. 机器设置
    # ============================================
    renderer.draw_section_header("机器设置", expanded=True)

    # 机器类型
    renderer.draw_dropdown_row("机台类型", "AD-F4 (800×1200mm)")

    # 基础参数
    renderer.draw_text(m + 8, renderer.y + 2, "基础参数", font_small, C["accent_secondary"])
    renderer.y += 18
    params_machine_basic = [
        ("喷头1温度", "220", "°C"),
        ("喷头2温度", "220", "°C"),
        ("喷头3温度", "220", "°C"),
        ("材料直径", "1.75", "mm"),
        ("抬头回抽", "3", "mm"),
        ("换料回抽", "30", "mm"),
        ("换料补偿", "20", "mm"),
    ]
    for label, value, unit in params_machine_basic:
        renderer.draw_param_row(label, value, unit)

    # 空走参数（新增）
    renderer.draw_text(m + 8, renderer.y + 2, "空走参数", font_small, C["accent_secondary"])
    renderer.y += 18
    params_travel = [
        ("空走抬头高度1", "1", "mm"),
        ("空走抬头高度2", "3", "mm"),
        ("空走最长距离", "100", "mm"),
    ]
    for label, value, unit in params_travel:
        renderer.draw_param_row(label, value, unit)

    # 喷头参数（新增）
    renderer.draw_text(m + 8, renderer.y + 2, "喷头参数", font_small, C["accent_secondary"])
    renderer.y += 18
    params_nozzle = [
        ("结束喷头位置", "50", "mm"),
        ("清洗喷头", "10", "mm"),
        ("提前关胶距离", "0.5", "mm"),
    ]
    for label, value, unit in params_nozzle:
        renderer.draw_param_row(label, value, unit)

    # 速度参数（新增）
    renderer.draw_text(m + 8, renderer.y + 2, "速度参数", font_small, C["accent_secondary"])
    renderer.y += 18
    params_speed_machine = [
        ("Z轴抬落速度", "60", "mm/s"),
        ("抬头挤出速度", "30", "mm/s"),
        ("抬头回抽速度", "50", "mm/s"),
        ("换色速度", "30", "mm/s"),
        ("换色回抽速度", "50", "mm/s"),
    ]
    for label, value, unit in params_speed_machine:
        renderer.draw_param_row(label, value, unit)

    # 缺料补偿（新增）
    renderer.draw_text(m + 8, renderer.y + 2, "缺料补偿", font_small, C["accent_secondary"])
    renderer.y += 18
    params_shortage = [
        ("近距离缺料补偿", "0.4", "mm"),
        ("远距离缺料补偿", "0.4", "mm"),
        ("远近距离分界线", "100", "mm"),
    ]
    for label, value, unit in params_shortage:
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
