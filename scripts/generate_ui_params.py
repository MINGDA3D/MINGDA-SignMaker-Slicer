"""
SignMaker Slicer - 参数设置界面
完整版 - 包含所有12个参数分组
"""

from PIL import Image, ImageDraw, ImageFont
import os

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
    "extruder_1": "#3B82F6",  # 蓝色 - 挤出机1
    "extruder_2": "#EC4899",  # 粉色 - 挤出机2
    "extruder_3": "#F59E0B",  # 橙色 - 挤出机3
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

C = {k: hex_to_rgb(v) for k, v in COLORS.items()}

# 图片尺寸
WIDTH = 480
# 高度将根据内容动态计算

# 字体加载
try:
    font_title = ImageFont.truetype("msyh.ttc", 16)
    font_section = ImageFont.truetype("msyh.ttc", 13)
    font_label = ImageFont.truetype("msyh.ttc", 11)
    font_small = ImageFont.truetype("msyh.ttc", 10)
    font_value = ImageFont.truetype("consola.ttf", 11)
except:
    font_title = font_section = font_label = font_small = font_value = ImageFont.load_default()


def draw_rounded_rect(draw, x, y, w, h, r, fill=None, outline=None, width=1):
    """绘制圆角矩形"""
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline, width=width)

def draw_text(draw, x, y, text, font=None, fill=None):
    """绘制文字"""
    draw.text((x, y), text, font=font or font_label, fill=fill or C["text_secondary"])

def draw_checkbox(draw, x, y, checked=False, size=16):
    """绘制复选框"""
    if checked:
        draw_rounded_rect(draw, x, y, size, size, 3, fill=C["accent_primary"])
        # 绘制勾选标记
        draw.line([(x+3, y+8), (x+6, y+11)], fill=(255, 255, 255), width=2)
        draw.line([(x+6, y+11), (x+12, y+5)], fill=(255, 255, 255), width=2)
    else:
        draw_rounded_rect(draw, x, y, size, size, 3, fill=C["bg_input"], outline=C["border_default"])

def draw_input_field(draw, x, y, w, h, value="", unit=""):
    """绘制输入框"""
    draw_rounded_rect(draw, x, y, w, h, 4, fill=C["bg_input"], outline=C["border_default"])
    draw_text(draw, x + 8, y + (h - 12) // 2, str(value), font_value, C["text_primary"])
    if unit:
        unit_x = x + w + 4
        draw_text(draw, unit_x, y + (h - 10) // 2, unit, font_small, C["text_muted"])

def draw_dropdown(draw, x, y, w, h, value=""):
    """绘制下拉选择框"""
    draw_rounded_rect(draw, x, y, w, h, 4, fill=C["bg_input"], outline=C["border_default"])
    draw_text(draw, x + 8, y + (h - 12) // 2, value, font_label, C["text_primary"])
    # 下拉箭头
    arrow_x = x + w - 16
    arrow_y = y + h // 2
    draw.polygon([(arrow_x, arrow_y - 2), (arrow_x + 8, arrow_y - 2), (arrow_x + 4, arrow_y + 3)],
                 fill=C["text_muted"])

def draw_button(draw, x, y, w, h, text, primary=False, color=None):
    """绘制按钮"""
    if color:
        fill_color = color
    elif primary:
        fill_color = C["accent_primary"]
    else:
        fill_color = C["bg_elevated"]

    draw_rounded_rect(draw, x, y, w, h, 4, fill=fill_color, outline=C["border_default"] if not primary else None)

    # 文字居中
    bbox = draw.textbbox((0, 0), text, font=font_label)
    text_w = bbox[2] - bbox[0]
    text_x = x + (w - text_w) // 2
    text_y = y + (h - 12) // 2
    draw_text(draw, text_x, text_y, text, font_label, (255, 255, 255) if primary or color else C["text_secondary"])

def draw_radio_group(draw, x, y, options, selected=0):
    """绘制单选按钮组"""
    btn_w = 60
    btn_h = 24
    gap = 4

    for i, opt in enumerate(options):
        bx = x + i * (btn_w + gap)
        if i == selected:
            draw_rounded_rect(draw, bx, y, btn_w, btn_h, 4, fill=C["accent_primary"])
            draw_text(draw, bx + 12, y + 5, opt, font_small, (255, 255, 255))
        else:
            draw_rounded_rect(draw, bx, y, btn_w, btn_h, 4, fill=C["bg_elevated"])
            draw_text(draw, bx + 12, y + 5, opt, font_small, C["text_muted"])

def draw_section_header(draw, x, y, w, title, expanded=True, has_checkbox=False, checked=False):
    """绘制分组标题"""
    # 背景
    draw_rounded_rect(draw, x, y, w, 32, 6, fill=C["bg_card"])

    # 展开/收起三角形
    tri_x = x + 12
    tri_y = y + 12
    if expanded:
        draw.polygon([(tri_x, tri_y), (tri_x + 10, tri_y), (tri_x + 5, tri_y + 6)],
                     fill=C["accent_primary"])
    else:
        draw.polygon([(tri_x, tri_y), (tri_x + 6, tri_y + 5), (tri_x, tri_y + 10)],
                     fill=C["text_muted"])

    # 复选框（如果有）
    text_x = tri_x + 16
    if has_checkbox:
        draw_checkbox(draw, text_x, y + 8, checked, 16)
        text_x += 24

    # 标题文字
    draw_text(draw, text_x, y + 9, title, font_section, C["text_primary"])

    return y + 36


def draw_param_row(draw, x, y, label, value, unit="", input_w=60):
    """绘制参数行（标签 + 输入框 + 单位）"""
    draw_text(draw, x, y + 5, label, font_label, C["text_secondary"])
    input_x = x + 140
    draw_input_field(draw, input_x, y, input_w, 24, value, unit)
    return y + 32


def generate_params_image():
    """生成参数设置界面图片"""

    # 预计算高度（12个分组 + 标题 + 间距）
    HEIGHT = 4200

    img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_base"])
    draw = ImageDraw.Draw(img)

    # 页面边距
    margin = 16
    content_w = WIDTH - margin * 2

    y = 16

    # ============================================
    # 页面标题
    # ============================================
    draw_text(draw, margin, y, "参数设置 - 完整版 (所有功能)", font_title, C["text_primary"])
    y += 36

    # ============================================
    # 1. 字壳工艺
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "1. 字壳工艺", expanded=True)

    # 异形边选择
    draw_text(draw, margin + 8, y + 5, "异形边选择", font_label, C["text_secondary"])
    btn_x = margin + 100
    draw_button(draw, btn_x, y, 50, 24, "添加")
    draw_button(draw, btn_x + 56, y, 50, 24, "选中")
    draw_button(draw, btn_x + 112, y, 50, 24, "删除")
    y += 32

    # 预设下拉
    draw_text(draw, margin + 8, y + 5, "字边预设", font_label, C["text_secondary"])
    draw_dropdown(draw, margin + 100, y, 180, 24, "斜边")
    y += 36

    # 打印模式
    draw_text(draw, margin + 8, y + 5, "打印模式", font_label, C["text_secondary"])
    draw_radio_group(draw, margin + 100, y, ["镜像打印", "正常打印"], selected=1)
    y += 32

    # 字边类型
    draw_text(draw, margin + 8, y + 5, "字边类型", font_label, C["text_secondary"])
    draw_radio_group(draw, margin + 100, y, ["直边", "斜边", "异形边"], selected=1)
    y += 36

    # 参数列表
    params_1 = [
        ("字壳高度", "30", "mm"),
        ("斜边宽度", "5", "mm"),
        ("面板厚度", "3", "mm"),
        ("底板厚度", "10", "mm"),
        ("层高", "0.3", "mm"),
        ("预打边线偏移", "20", "mm"),
        ("预打边线次数", "1", "次"),
        ("雕刻刀刃宽", "3", "mm"),
        ("壁厚", "1.2", "mm"),
        ("壁厚补偿", "0", "mm"),
        ("走线次数", "1", "次"),
        ("走线高度", "0", "mm"),
        ("走线偏移", "0.8", "mm"),
        ("字芯高度", "0", "mm"),
        ("字芯斜边宽度", "0", "mm"),
    ]

    for label, value, unit in params_1:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    y += 8

    # ============================================
    # 2. 放样设置
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "2. 放样设置", expanded=True)

    params_2 = [
        ("整体外扩", "0", "mm"),
        ("整体内缩", "0", "mm"),
        ("孔内扩", "0", "mm"),
        ("孔外缩", "0", "mm"),
        ("勾边外扩", "1.2", "mm"),
        ("勾边内缩", "0", "mm"),
        ("包边外扩", "0", "mm"),
        ("包边内缩", "1.2", "mm"),
        ("字芯外扩", "0", "mm"),
        ("字芯内缩", "0", "mm"),
    ]

    for label, value, unit in params_2:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    y += 8

    # ============================================
    # 3. 换色层设置
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "3. 换色层设置", expanded=True, has_checkbox=True, checked=True)

    # 换色层表格
    draw_text(draw, margin + 8, y + 5, "换色层数 (最多7层)", font_label, C["text_secondary"])
    y += 28

    # 表头
    col_x = [margin + 8, margin + 60, margin + 140, margin + 220, margin + 300]
    draw_text(draw, col_x[0], y, "层", font_small, C["text_muted"])
    draw_text(draw, col_x[1], y, "层高(mm)", font_small, C["text_muted"])
    draw_text(draw, col_x[2], y, "挤出机", font_small, C["text_muted"])
    draw_text(draw, col_x[3], y, "启用", font_small, C["text_muted"])
    y += 20

    # 换色层数据
    color_layers = [
        ("1", "10", "1", True, C["extruder_1"]),
        ("2", "5", "2", True, C["extruder_2"]),
        ("3", "5", "3", True, C["extruder_3"]),
        ("4", "10", "1", True, C["extruder_1"]),
        ("5", "0", "1", False, C["extruder_1"]),
        ("6", "0", "1", False, C["extruder_1"]),
        ("7", "0", "1", False, C["extruder_1"]),
    ]

    for layer_num, height, ext, enabled, color in color_layers:
        # 颜色指示条
        if enabled:
            draw_rounded_rect(draw, col_x[0], y + 2, 4, 20, 2, fill=color)
        draw_text(draw, col_x[0] + 10, y + 5, layer_num, font_label, C["text_primary"] if enabled else C["text_muted"])
        draw_input_field(draw, col_x[1], y, 50, 24, height)
        draw_dropdown(draw, col_x[2], y, 50, 24, ext)
        draw_checkbox(draw, col_x[3], y + 4, enabled, 16)
        y += 30

    # 添加换色层按钮
    draw_button(draw, margin + 8, y, 120, 28, "+ 添加换色层")
    y += 40

    # 启用喷头2设置
    draw_text(draw, margin + 8, y, "启用喷头2 (双层壁厚)", font_label, C["text_secondary"])
    draw_checkbox(draw, margin + 160, y, False, 16)
    y += 28

    params_3_extra = [
        ("双层吐丝宽度", "1.2", "mm"),
        ("双层走线偏移", "0.8", "mm"),
        ("双层走线次数", "1", "次"),
        ("双层走线速度", "40", "mm/s"),
    ]

    for label, value, unit in params_3_extra:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    y += 8

    # ============================================
    # 4. 台阶V槽
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "4. 台阶V槽", expanded=True, has_checkbox=True, checked=True)

    # 台阶表格
    draw_text(draw, margin + 8, y + 5, "台阶数量 (最多7个)", font_label, C["text_secondary"])
    y += 28

    # 表头
    col_x = [margin + 8, margin + 50, margin + 130, margin + 210, margin + 290]
    draw_text(draw, col_x[0], y, "序号", font_small, C["text_muted"])
    draw_text(draw, col_x[1], y, "位置(mm)", font_small, C["text_muted"])
    draw_text(draw, col_x[2], y, "高度(mm)", font_small, C["text_muted"])
    draw_text(draw, col_x[3], y, "宽度(mm)", font_small, C["text_muted"])
    draw_text(draw, col_x[4], y, "启用", font_small, C["text_muted"])
    y += 20

    # 台阶数据
    steps = [
        ("1", "4", "1.2", "1.2", True),
        ("2", "27", "1.2", "1.2", True),
        ("3", "0", "0", "0", False),
        ("4", "0", "0", "0", False),
    ]

    for step_num, pos, height, width, enabled in steps:
        draw_text(draw, col_x[0], y + 5, step_num, font_label, C["text_primary"] if enabled else C["text_muted"])
        draw_input_field(draw, col_x[1], y, 55, 24, pos)
        draw_input_field(draw, col_x[2], y, 55, 24, height)
        draw_input_field(draw, col_x[3], y, 55, 24, width)
        draw_checkbox(draw, col_x[4], y + 4, enabled, 16)
        y += 30

    y += 8

    # 台阶打印参数
    draw_text(draw, margin + 8, y, "台阶打印参数", font_label, C["text_muted"])
    y += 24

    params_4 = [
        ("台阶速度", "30", "mm/s"),
        ("喷头水平偏移", "0", "mm"),
        ("喷头吐丝宽度", "1.2", "mm"),
        ("台阶厚度", "0.3", "mm"),
    ]

    for label, value, unit in params_4:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    y += 8

    # ============================================
    # 5. 防翘裙边
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "5. 防翘裙边", expanded=True, has_checkbox=True, checked=True)

    # 防翘位置
    draw_text(draw, margin + 8, y + 5, "防翘位置", font_label, C["text_secondary"])
    draw_radio_group(draw, margin + 100, y, ["外防翘", "内防翘"], selected=0)
    y += 32

    params_5 = [
        ("压线宽度", "0.5", "mm"),
        ("吐丝宽度", "1.2", "mm"),
        ("防翘速度", "30", "mm/s"),
        ("防翘高度", "0.3", "mm"),
        ("防翘长度", "10", "mm"),
        ("防翘宽度", "5", "mm"),
        ("V型开口宽度", "3", "mm"),
    ]

    for label, value, unit in params_5:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    y += 8

    # ============================================
    # 6. 连襟字
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "6. 连襟字", expanded=True, has_checkbox=True, checked=False)

    # 连襟类型
    draw_text(draw, margin + 8, y + 5, "连襟类型", font_label, C["text_secondary"])
    draw_radio_group(draw, margin + 100, y, ["三角形", "菱形"], selected=0)
    y += 32

    params_6 = [
        ("连襟宽度", "15", "mm"),
        ("连襟高度", "5", "mm"),
        ("连襟底座高度", "5", "mm"),
        ("连襟支撑偏移", "2.5", "mm"),
        ("整板排序行距", "0", "mm"),
    ]

    for label, value, unit in params_6:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    # 说明
    draw_text(draw, margin + 8, y, "说明: 连襟高度 + 连襟底座高度 = 连襟总高度", font_small, C["text_muted"])
    y += 28

    y += 8

    # ============================================
    # 7. 包边勾边字
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "7. 包边勾边字", expanded=True)

    # 功能选项
    draw_text(draw, margin + 8, y + 5, "勾边有效", font_label, C["text_secondary"])
    draw_checkbox(draw, margin + 100, y + 4, True, 16)
    draw_text(draw, margin + 200, y + 5, "包边有效", font_label, C["text_secondary"])
    draw_checkbox(draw, margin + 290, y + 4, False, 16)
    y += 28

    # 位置
    draw_text(draw, margin + 8, y + 5, "位置", font_label, C["text_secondary"])
    draw_radio_group(draw, margin + 100, y, ["内部", "外部"], selected=0)
    y += 32

    params_7 = [
        ("包边高度", "1.2", "mm"),
        ("勾边高度", "1.2", "mm"),
        ("勾包边宽度", "3", "mm"),
        ("勾包边速度", "30", "mm/s"),
        ("包边压线偏移", "0", "mm"),
        ("勾边压线偏移", "0", "mm"),
        ("吐丝宽度", "1.2", "mm"),
    ]

    for label, value, unit in params_7:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    y += 8

    # ============================================
    # 8. 面板打印
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "8. 面板打印", expanded=True)

    # 填充类型选择
    draw_text(draw, margin + 8, y + 5, "填充类型", font_label, C["text_secondary"])
    btn_x = margin + 100
    draw_button(draw, btn_x, y, 50, 24, "面板", primary=True)
    draw_button(draw, btn_x + 56, y, 50, 24, "网格")
    draw_button(draw, btn_x + 112, y, 50, 24, "底板")
    y += 36

    # 填充参数
    draw_text(draw, margin + 8, y, "填充参数设置", font_label, C["text_muted"])
    y += 24

    params_8_fill = [
        ("填充间距(正面)", "8", "mm"),
        ("填充间距2(背面)", "0.9", "mm"),
        ("边界距离", "1.4", "mm"),
        ("角度", "45", "度"),
    ]

    for label, value, unit in params_8_fill:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    # 不参与填充选项
    draw_checkbox(draw, margin + 8, y + 4, True, 16)
    draw_text(draw, margin + 30, y + 5, "连襟不参与", font_label, C["text_secondary"])
    draw_checkbox(draw, margin + 150, y + 4, True, 16)
    draw_text(draw, margin + 172, y + 5, "面板不参与", font_label, C["text_secondary"])
    y += 32

    # 1类填充
    draw_text(draw, margin + 8, y, "1类填充 (正面)", font_label, C["accent_secondary"])
    y += 24

    params_8_1 = [
        ("填充高度", "0.6", "mm"),
        ("填充模式", "自动连接", ""),
        ("吐丝宽度", "1.2", "mm"),
        ("填充速度", "40", "mm/s"),
        ("压线宽度", "0.8", "mm"),
    ]

    for label, value, unit in params_8_1:
        if unit == "":
            draw_text(draw, margin + 8, y + 5, label, font_label, C["text_secondary"])
            draw_dropdown(draw, margin + 140, y, 120, 24, value)
            y += 32
        else:
            y = draw_param_row(draw, margin + 8, y, label, value, unit)

    # 指定挤出机
    draw_text(draw, margin + 8, y + 5, "指定挤出机", font_label, C["text_secondary"])
    draw_radio_group(draw, margin + 100, y, ["无", "2号", "3号"], selected=0)
    y += 36

    # 2类填充
    draw_text(draw, margin + 8, y, "2类填充 (背面)", font_label, C["accent_secondary"])
    y += 24

    params_8_2 = [
        ("填充高度", "1.5", "mm"),
        ("填充速度", "60", "mm/s"),
    ]

    for label, value, unit in params_8_2:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    # 指定挤出机
    draw_text(draw, margin + 8, y + 5, "指定挤出机", font_label, C["text_secondary"])
    draw_radio_group(draw, margin + 100, y, ["无", "2号", "3号"], selected=0)
    y += 40

    # 花纹打印
    draw_text(draw, margin + 8, y, "面板花纹打印", font_label, C["text_muted"])
    draw_checkbox(draw, margin + 120, y, False, 16)
    y += 28

    params_8_pattern = [
        ("花纹类型", "直边", ""),
        ("打印高度", "0.2", "mm"),
        ("斜边宽度", "1.2", "mm"),
        ("底座厚度", "0.6", "mm"),
        ("打印速度", "40", "mm/s"),
        ("吐丝宽度", "1.2", "mm"),
    ]

    for label, value, unit in params_8_pattern:
        if unit == "":
            draw_text(draw, margin + 8, y + 5, label, font_label, C["text_secondary"])
            draw_radio_group(draw, margin + 100, y, ["直边", "斜边"], selected=0)
            y += 32
        else:
            y = draw_param_row(draw, margin + 8, y, label, value, unit)

    y += 8

    # ============================================
    # 9. 路径顺序
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "9. 路径顺序", expanded=True)

    draw_text(draw, margin + 8, y + 5, "打印顺序", font_label, C["text_secondary"])
    draw_dropdown(draw, margin + 100, y, 180, 24, "外轮廓优先")
    y += 32

    draw_text(draw, margin + 8, y + 5, "路径优化", font_label, C["text_secondary"])
    draw_checkbox(draw, margin + 100, y + 4, True, 16)
    draw_text(draw, margin + 124, y + 5, "启用路径优化", font_label, C["text_secondary"])
    y += 36

    y += 8

    # ============================================
    # 10. 填充
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "10. 填充", expanded=True)

    params_10 = [
        ("填充密度", "20", "%"),
        ("填充角度", "45", "度"),
        ("填充图案", "线性", ""),
    ]

    for label, value, unit in params_10:
        if unit == "":
            draw_text(draw, margin + 8, y + 5, label, font_label, C["text_secondary"])
            draw_dropdown(draw, margin + 140, y, 120, 24, value)
            y += 32
        else:
            y = draw_param_row(draw, margin + 8, y, label, value, unit)

    # 填充模式选项
    draw_checkbox(draw, margin + 8, y + 4, True, 16)
    draw_text(draw, margin + 30, y + 5, "生成内填充", font_label, C["text_secondary"])
    y += 28

    draw_checkbox(draw, margin + 8, y + 4, False, 16)
    draw_text(draw, margin + 30, y + 5, "稀疏填充模式", font_label, C["text_secondary"])
    y += 36

    y += 8

    # ============================================
    # 11. 文件读取/保存 DXF
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "11. 文件读取/保存 DXF", expanded=True)

    # 生成底板
    draw_checkbox(draw, margin + 8, y + 4, True, 16)
    draw_text(draw, margin + 30, y + 5, "生成底板 DXF", font_label, C["text_secondary"])
    y += 28

    draw_text(draw, margin + 8, y + 5, "对齐补偿", font_label, C["text_secondary"])
    draw_input_field(draw, margin + 100, y, 60, 24, "-0.4", "mm")
    y += 32

    draw_button(draw, margin + 8, y, 120, 28, "另存为...")
    y += 40

    # 生成面板
    draw_checkbox(draw, margin + 8, y + 4, True, 16)
    draw_text(draw, margin + 30, y + 5, "生成面板 DXF", font_label, C["text_secondary"])
    y += 28

    draw_text(draw, margin + 8, y + 5, "对齐补偿", font_label, C["text_secondary"])
    draw_input_field(draw, margin + 100, y, 60, 24, "0", "mm")
    y += 32

    draw_button(draw, margin + 8, y, 120, 28, "另存为...")
    y += 44

    y += 8

    # ============================================
    # 12. 文件输出
    # ============================================
    y = draw_section_header(draw, margin, y, content_w, "12. 文件输出", expanded=True)

    # 文件名
    draw_text(draw, margin + 8, y + 5, "文件名", font_label, C["text_secondary"])
    draw_rounded_rect(draw, margin + 100, y, 200, 24, 4, fill=C["bg_input"], outline=C["border_default"])
    draw_text(draw, margin + 108, y + 5, "output.gcode", font_value, C["text_primary"])
    draw_button(draw, margin + 310, y, 70, 24, "另存为")
    y += 36

    params_12 = [
        ("打印速度", "40", "mm/s"),
        ("首层打印速度", "30", "mm/s"),
        ("空程速度", "300", "mm/s"),
        ("喷头1温度", "220", "°C"),
        ("喷头2温度", "220", "°C"),
        ("喷头3温度", "220", "°C"),
    ]

    for label, value, unit in params_12:
        y = draw_param_row(draw, margin + 8, y, label, value, unit)

    # 机台类型
    draw_text(draw, margin + 8, y + 5, "机台类型", font_label, C["text_secondary"])
    draw_dropdown(draw, margin + 100, y, 120, 24, "ZC-80")
    y += 36

    # 其他选项
    draw_checkbox(draw, margin + 8, y + 4, False, 16)
    draw_text(draw, margin + 30, y + 5, "头尾交替打印", font_label, C["text_secondary"])
    y += 28

    draw_checkbox(draw, margin + 8, y + 4, False, 16)
    draw_text(draw, margin + 30, y + 5, "结束完成不回抽", font_label, C["text_secondary"])
    y += 36

    # 模板操作按钮
    draw_button(draw, margin + 8, y, 100, 28, "保存模板")
    draw_button(draw, margin + 116, y, 100, 28, "读取模板")
    y += 44

    # ============================================
    # 底部操作按钮
    # ============================================
    y += 16
    draw_button(draw, margin, y, content_w // 3 - 8, 40, "计算路径", primary=True)
    draw_button(draw, margin + content_w // 3, y, content_w // 3 - 8, 40, "预览字边")
    draw_button(draw, margin + content_w * 2 // 3, y, content_w // 3, 40, "文件输出", primary=True)
    y += 60

    # 裁剪到实际内容高度
    actual_height = y + 16
    img = img.crop((0, 0, WIDTH, actual_height))

    # 保存
    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "UI_Params_Generated.png")
    img.save(output_path, "PNG", quality=95)
    print(f"Saved: {output_path}")

    root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Params_Generated.png")
    img.save(root_path, "PNG", quality=95)
    print(f"Saved: {root_path}")

    return actual_height


if __name__ == "__main__":
    height = generate_params_image()
    print(f"\nParams UI generated successfully!")
    print(f"Image size: {WIDTH} x {height}")
