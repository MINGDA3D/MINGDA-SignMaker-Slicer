"""
SignMaker Slicer UI Mockup Generator
生成UI效果图
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 颜色定义
COLORS = {
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_panel": "#21262D",
    "bg_hover": "#30363D",
    "text_primary": "#F0F6FC",
    "text_secondary": "#C9D1D9",
    "text_muted": "#8B949E",
    "accent_primary": "#58A6FF",
    "accent_success": "#3FB950",
    "accent_warning": "#F59E0B",
    "accent_error": "#F85149",
    "border_default": "#30363D",
    "canvas_bg": "#1A1D21",
    "path_blue": "#58A6FF",
}

def hex_to_rgb(hex_color):
    """十六进制转RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# 转换颜色
C = {k: hex_to_rgb(v) for k, v in COLORS.items()}

# 画布尺寸
WIDTH = 1400
HEIGHT = 900

# 布局尺寸
MENUBAR_H = 28
TOOLBAR_H = 44
STATUSBAR_H = 26
SIDEBAR_LEFT_W = 200
SIDEBAR_RIGHT_W = 320

# 创建画布
img = Image.new('RGB', (WIDTH, HEIGHT), C["bg_primary"])
draw = ImageDraw.Draw(img)

# 尝试加载字体
try:
    font_title = ImageFont.truetype("msyh.ttc", 14)
    font_body = ImageFont.truetype("msyh.ttc", 11)
    font_small = ImageFont.truetype("msyh.ttc", 10)
    font_mono = ImageFont.truetype("consola.ttf", 11)
    font_icon = ImageFont.truetype("seguisym.ttf", 16)
    font_large = ImageFont.truetype("msyh.ttc", 48)
except:
    font_title = ImageFont.load_default()
    font_body = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_mono = ImageFont.load_default()
    font_icon = ImageFont.load_default()
    font_large = ImageFont.load_default()

def draw_rect(x, y, w, h, fill=None, outline=None):
    """绘制矩形"""
    draw.rectangle([x, y, x+w, y+h], fill=fill, outline=outline)

def draw_rounded_rect(x, y, w, h, r, fill=None, outline=None):
    """绘制圆角矩形"""
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=outline)

def draw_text(x, y, text, font=None, fill=None):
    """绘制文本"""
    draw.text((x, y), text, font=font or font_body, fill=fill or C["text_secondary"])

# ============================================
# 菜单栏
# ============================================
draw_rect(0, 0, WIDTH, MENUBAR_H, fill=C["bg_secondary"])
draw.line([(0, MENUBAR_H), (WIDTH, MENUBAR_H)], fill=C["border_default"], width=1)

menus = ["文件(F)", "编辑(E)", "视图(V)", "工具(T)", "帮助(H)"]
menu_x = 12
for menu in menus:
    draw_text(menu_x, 6, menu, font_body, C["text_secondary"])
    menu_x += 70

# 窗口控制按钮
draw_text(WIDTH - 80, 6, "—  ☐  ✕", font_body, C["text_muted"])

# ============================================
# 工具栏
# ============================================
toolbar_y = MENUBAR_H
draw_rect(0, toolbar_y, WIDTH, TOOLBAR_H, fill=C["bg_secondary"])
draw.line([(0, toolbar_y + TOOLBAR_H), (WIDTH, toolbar_y + TOOLBAR_H)], fill=C["border_default"], width=1)

# 工具按钮
tools = [
    ("📂", "打开"),
    ("💾", "保存"),
    ("📥", "导入"),
    ("📤", "导出"),
    ("|", ""),
    ("🔗", "结合"),
    ("✂", "打散"),
    ("🔄", "旋转"),
    ("↔", "镜像"),
    ("|", ""),
    ("👁", "预览"),
    ("⚙", "设置"),
]

tool_x = 12
for icon, tip in tools:
    if icon == "|":
        # 分隔线
        draw.line([(tool_x + 4, toolbar_y + 8), (tool_x + 4, toolbar_y + TOOLBAR_H - 8)],
                  fill=C["border_default"], width=1)
        tool_x += 16
    else:
        # 工具按钮
        draw_rounded_rect(tool_x, toolbar_y + 6, 32, 32, 4, fill=C["bg_panel"])
        draw_text(tool_x + 8, toolbar_y + 12, icon, font_icon, C["text_secondary"])
        tool_x += 40

# ============================================
# 左侧边栏 - 项目面板
# ============================================
content_y = MENUBAR_H + TOOLBAR_H
content_h = HEIGHT - content_y - STATUSBAR_H

draw_rect(0, content_y, SIDEBAR_LEFT_W, content_h, fill=C["bg_secondary"])
draw.line([(SIDEBAR_LEFT_W, content_y), (SIDEBAR_LEFT_W, content_y + content_h)],
          fill=C["border_default"], width=1)

# 面板标题
draw_rect(0, content_y, SIDEBAR_LEFT_W, 32, fill=C["bg_panel"])
draw_text(12, content_y + 8, "📁 项目文件", font_title, C["text_primary"])

# 文件列表
files = [
    ("📄", "招牌字.dxf", True),
    ("📄", "门头字.dxf", False),
    ("📄", "广告字.dxf", False),
]
file_y = content_y + 44
for icon, name, selected in files:
    if selected:
        draw_rounded_rect(8, file_y, SIDEBAR_LEFT_W - 16, 28, 4, fill=C["bg_hover"])
    draw_text(16, file_y + 6, f"{icon} {name}", font_body,
              C["text_primary"] if selected else C["text_secondary"])
    file_y += 32

# ============================================
# 右侧边栏 - 参数面板
# ============================================
right_x = WIDTH - SIDEBAR_RIGHT_W
draw_rect(right_x, content_y, SIDEBAR_RIGHT_W, content_h, fill=C["bg_secondary"])
draw.line([(right_x, content_y), (right_x, content_y + content_h)],
          fill=C["border_default"], width=1)

# 标签页
tabs = ["字壳工艺", "换色层", "台阶V槽", "防翘裙边"]
tab_x = right_x
tab_w = SIDEBAR_RIGHT_W // len(tabs)
for i, tab in enumerate(tabs):
    if i == 0:
        draw_rect(tab_x, content_y, tab_w, 32, fill=C["bg_panel"])
        draw.line([(tab_x, content_y + 31), (tab_x + tab_w, content_y + 31)],
                  fill=C["accent_primary"], width=2)
        draw_text(tab_x + 12, content_y + 8, tab, font_body, C["text_primary"])
    else:
        draw_text(tab_x + 12, content_y + 8, tab, font_body, C["text_muted"])
    tab_x += tab_w

# 参数内容区
panel_y = content_y + 40
draw_rect(right_x, panel_y, SIDEBAR_RIGHT_W, content_h - 40, fill=C["bg_panel"])

# 分组: 基本设置
group_y = panel_y + 16
draw_rounded_rect(right_x + 12, group_y, SIDEBAR_RIGHT_W - 24, 160, 6,
                  fill=C["bg_secondary"], outline=C["border_default"])
draw_text(right_x + 24, group_y - 8, " 基本设置 ", font_body, C["text_secondary"])

# 参数项
params = [
    ("字边类型", "直边", "dropdown"),
    ("字壳高度", "30", "mm"),
    ("层高", "0.3", "mm"),
    ("壁厚", "1.2", "mm"),
]
param_y = group_y + 20
for label, value, unit in params:
    draw_text(right_x + 24, param_y, label, font_body, C["text_secondary"])
    # 输入框
    input_x = right_x + 120
    input_w = 120 if unit != "dropdown" else 140
    draw_rounded_rect(input_x, param_y - 2, input_w, 24, 4,
                      fill=C["bg_primary"], outline=C["border_default"])
    draw_text(input_x + 8, param_y, value, font_mono, C["text_primary"])
    if unit == "dropdown":
        draw_text(input_x + input_w - 20, param_y, "▼", font_small, C["text_muted"])
    elif unit:
        draw_text(input_x + input_w + 8, param_y, unit, font_small, C["text_muted"])
    param_y += 32

# 分组: 斜边设置
group_y = panel_y + 190
draw_rounded_rect(right_x + 12, group_y, SIDEBAR_RIGHT_W - 24, 100, 6,
                  fill=C["bg_secondary"], outline=C["border_default"])
draw_text(right_x + 24, group_y - 8, " 斜边设置 ", font_body, C["text_secondary"])

params2 = [
    ("斜边宽度", "5", "mm"),
    ("底板厚度", "10", "mm"),
]
param_y = group_y + 20
for label, value, unit in params2:
    draw_text(right_x + 24, param_y, label, font_body, C["text_secondary"])
    input_x = right_x + 120
    draw_rounded_rect(input_x, param_y - 2, 120, 24, 4,
                      fill=C["bg_primary"], outline=C["border_default"])
    draw_text(input_x + 8, param_y, value, font_mono, C["text_primary"])
    draw_text(input_x + 128, param_y, unit, font_small, C["text_muted"])
    param_y += 32

# 操作按钮
btn_y = content_y + content_h - 60
draw_rounded_rect(right_x + 12, btn_y, 90, 32, 6, fill=C["accent_primary"])
draw_text(right_x + 28, btn_y + 8, "计算路径", font_body, (255, 255, 255))

draw_rounded_rect(right_x + 112, btn_y, 90, 32, 6, fill=C["bg_hover"], outline=C["border_default"])
draw_text(right_x + 140, btn_y + 8, "预览", font_body, C["text_secondary"])

draw_rounded_rect(right_x + 212, btn_y, 90, 32, 6, fill=C["bg_hover"], outline=C["border_default"])
draw_text(right_x + 228, btn_y + 8, "文件输出", font_body, C["text_secondary"])

# ============================================
# 中央画布区域
# ============================================
canvas_x = SIDEBAR_LEFT_W + 1
canvas_w = WIDTH - SIDEBAR_LEFT_W - SIDEBAR_RIGHT_W - 2
canvas_y = content_y
canvas_h = content_h

draw_rect(canvas_x, canvas_y, canvas_w, canvas_h, fill=C["canvas_bg"])

# 网格线 (淡色)
grid_color = (30, 35, 42)
for gx in range(canvas_x, canvas_x + canvas_w, 50):
    draw.line([(gx, canvas_y), (gx, canvas_y + canvas_h)], fill=grid_color, width=1)
for gy in range(canvas_y, canvas_y + canvas_h, 50):
    draw.line([(canvas_x, gy), (canvas_x + canvas_w, gy)], fill=grid_color, width=1)

# 绘制"字"的轮廓路径
center_x = canvas_x + canvas_w // 2
center_y = canvas_y + canvas_h // 2

# 简化的"字"字形轮廓
char_points = [
    # 外轮廓 (简化的矩形表示)
    [(center_x - 80, center_y - 100), (center_x + 80, center_y - 100),
     (center_x + 80, center_y + 100), (center_x - 80, center_y + 100)],
]

# 绘制字形外框
draw_rounded_rect(center_x - 100, center_y - 120, 200, 240, 8,
                  outline=C["path_blue"])

# 绘制"字"
draw_text(center_x - 40, center_y - 50, "字", font_large, C["path_blue"])

# 绘制起点标记
draw.ellipse([center_x - 95, center_y - 115, center_x - 85, center_y - 105],
             fill=C["accent_success"])
draw_text(center_x - 78, center_y - 118, "起点", font_small, C["accent_success"])

# 画布工具栏 (右下角)
tool_bg_x = canvas_x + canvas_w - 140
tool_bg_y = canvas_y + canvas_h - 50
draw_rounded_rect(tool_bg_x, tool_bg_y, 130, 40, 6, fill=C["bg_panel"])

canvas_tools = ["🔍+", "🔍-", "⊡", "🎯"]
ct_x = tool_bg_x + 10
for ct in canvas_tools:
    draw_rounded_rect(ct_x, tool_bg_y + 6, 28, 28, 4, fill=C["bg_hover"])
    draw_text(ct_x + 6, tool_bg_y + 10, ct, font_small, C["text_secondary"])
    ct_x += 30

# 坐标显示
draw_rounded_rect(canvas_x + 10, canvas_y + canvas_h - 50, 150, 30, 6, fill=C["bg_panel"])
draw_text(canvas_x + 20, canvas_y + canvas_h - 42, "X: 125.5  Y: 89.2", font_mono, C["text_muted"])

# ============================================
# 状态栏
# ============================================
status_y = HEIGHT - STATUSBAR_H
draw_rect(0, status_y, WIDTH, STATUSBAR_H, fill=C["bg_secondary"])
draw.line([(0, status_y), (WIDTH, status_y)], fill=C["border_default"], width=1)

draw_text(12, status_y + 6, "就绪", font_small, C["text_muted"])
draw_text(WIDTH - 350, status_y + 6, "图形: 3 个  |  打印时间: 2h 15m  |  耗材: 125.8m",
          font_small, C["text_muted"])

# ============================================
# 保存图片
# ============================================
output_path = os.path.join(os.path.dirname(__file__), "..", "docs", "UI_Mockup.png")
os.makedirs(os.path.dirname(output_path), exist_ok=True)
img.save(output_path, "PNG", quality=95)
print(f"UI Mockup saved to: {output_path}")

# 同时保存到项目根目录方便查看
root_path = os.path.join(os.path.dirname(__file__), "..", "UI_Mockup.png")
img.save(root_path, "PNG", quality=95)
print(f"UI Mockup also saved to: {root_path}")
