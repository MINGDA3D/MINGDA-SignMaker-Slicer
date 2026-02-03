"""
MINGDA SignMaker UI Mockup Generator
生成带有预设模板功能的现代化UI界面设计图
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 颜色定义 - 深色主题
COLORS = {
    'bg_dark': '#1e1e1e',
    'bg_panel': '#252526',
    'bg_canvas': '#2d2d30',
    'bg_input': '#3c3c3c',
    'bg_button': '#0e639c',
    'bg_button_hover': '#1177bb',
    'bg_selected': '#094771',
    'border': '#3c3c3c',
    'border_light': '#4a4a4a',
    'text_primary': '#cccccc',
    'text_secondary': '#858585',
    'text_white': '#ffffff',
    'accent_blue': '#0078d4',
    'accent_green': '#4ec9b0',
    'accent_orange': '#ce9178',
    'path_outer': '#4fc3f7',
    'path_inner': '#81d4fa',
    'grid': '#333333',
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

class UIGenerator:
    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height
        self.img = Image.new('RGB', (width, height), hex_to_rgb(COLORS['bg_dark']))
        self.draw = ImageDraw.Draw(self.img)

        # 尝试加载字体
        self.font_large = self._load_font(18)
        self.font_normal = self._load_font(14)
        self.font_small = self._load_font(12)
        self.font_title = self._load_font(16)
        self.font_icon = self._load_font(20)

    def _load_font(self, size):
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

    def draw_rect(self, x, y, w, h, fill=None, outline=None, radius=0):
        """绘制矩形（可带圆角）"""
        fill_rgb = hex_to_rgb(fill) if fill else None
        outline_rgb = hex_to_rgb(outline) if outline else None

        if radius > 0:
            # 简化的圆角矩形
            self.draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=fill_rgb, outline=outline_rgb)
        else:
            self.draw.rectangle([x, y, x+w, y+h], fill=fill_rgb, outline=outline_rgb)

    def draw_text(self, x, y, text, color='#cccccc', font=None):
        """绘制文本"""
        if font is None:
            font = self.font_normal
        self.draw.text((x, y), text, fill=hex_to_rgb(color), font=font)

    def draw_menu_bar(self):
        """绘制菜单栏"""
        self.draw_rect(0, 0, self.width, 30, fill='#333333')

        menus = ['文件(F)', '编辑(E)', '视图(V)', '工艺(P)', '设备(D)', '帮助(H)']
        x = 10
        for menu in menus:
            self.draw_text(x, 6, menu, '#cccccc', self.font_normal)
            x += 80

        # 标题
        title = "MINGDA SignMaker v1.0 - [未保存项目]"
        title_x = self.width // 2 - 120
        self.draw_text(title_x, 6, title, '#cccccc', self.font_normal)

        # 窗口控制按钮
        self.draw_text(self.width - 100, 6, "─  □  ✕", '#cccccc', self.font_normal)

    def draw_toolbar(self):
        """绘制工具栏"""
        y = 30
        self.draw_rect(0, y, self.width, 45, fill='#2d2d30')
        self.draw_rect(0, y+45, self.width, 1, fill='#3c3c3c')

        # 工具栏按钮
        buttons = [
            ('📂 导入', True), ('💾 保存', True), ('|', False),
            ('📐 排版', True), ('👁 预览', True), ('|', False),
            ('⚙ 计算', True), ('📤 输出', True), ('|', False),
            ('⚡ 设置', True),
        ]

        x = 15
        for btn_text, is_button in buttons:
            if btn_text == '|':
                self.draw_rect(x, y+10, 1, 25, fill='#4a4a4a')
                x += 15
            else:
                btn_width = 75
                self.draw_rect(x, y+8, btn_width, 30, fill='#3c3c3c', radius=4)
                self.draw_text(x+10, y+14, btn_text, '#cccccc', self.font_normal)
                x += btn_width + 8

    def draw_left_panel(self):
        """绘制左侧工艺选择面板"""
        x, y = 0, 76
        panel_width = 180
        panel_height = self.height - 76 - 35

        self.draw_rect(x, y, panel_width, panel_height, fill='#252526')
        self.draw_rect(x + panel_width, y, 1, panel_height, fill='#3c3c3c')

        # 工艺类型
        self.draw_text(x+15, y+15, "工艺类型", '#ffffff', self.font_title)

        process_types = [
            ('○ 直边', False),
            ('● 斜边', True),
            ('○ 异形边', False),
        ]

        py = y + 45
        for text, selected in process_types:
            if selected:
                self.draw_rect(x+10, py-3, panel_width-20, 24, fill='#094771', radius=3)
            self.draw_text(x+20, py, text, '#ffffff' if selected else '#cccccc', self.font_normal)
            py += 30

        # 分隔线
        py += 10
        self.draw_rect(x+15, py, panel_width-30, 1, fill='#4a4a4a')
        py += 20

        # 最近项目
        self.draw_text(x+15, py, "最近项目", '#ffffff', self.font_title)
        py += 35

        recent_files = ['招牌A.dxf', '门头发光字.dxf', '茶字样品.dxf']
        for f in recent_files:
            self.draw_text(x+20, py, f"📄 {f}", '#858585', self.font_small)
            py += 25

    def draw_canvas_area(self):
        """绘制2D画布区域"""
        x, y = 181, 76
        canvas_width = self.width - 181 - 320
        canvas_height = self.height - 76 - 35

        # 画布背景
        self.draw_rect(x, y, canvas_width, canvas_height, fill='#1a1a1a')

        # 网格线
        grid_color = hex_to_rgb('#2a2a2a')
        grid_spacing = 40
        for gx in range(x, x + canvas_width, grid_spacing):
            self.draw.line([(gx, y), (gx, y + canvas_height)], fill=grid_color, width=1)
        for gy in range(y, y + canvas_height, grid_spacing):
            self.draw.line([(x, gy), (x + canvas_width, gy)], fill=grid_color, width=1)

        # 绘制"发光字"轮廓示意
        self._draw_character_outlines(x + canvas_width//2 - 200, y + canvas_height//2 - 80)

        # 画布边框
        self.draw_rect(x, y, canvas_width, canvas_height, outline='#3c3c3c')

        # 版面尺寸标注
        self.draw_text(x + 10, y + 10, "版面: 800 x 600 mm", '#666666', self.font_small)

        # 坐标轴
        self.draw_text(x + canvas_width - 60, y + canvas_height - 25, "X →", '#666666', self.font_small)
        self.draw_text(x + 10, y + canvas_height - 45, "↑\nY", '#666666', self.font_small)

    def _draw_character_outlines(self, start_x, start_y):
        """绘制发光字轮廓示意"""
        # 简化的"发"字轮廓
        outer_color = hex_to_rgb('#4fc3f7')
        inner_color = hex_to_rgb('#29b6f6')

        chars = ['发', '光', '字']
        x = start_x

        for i, char in enumerate(chars):
            # 外轮廓框
            char_width = 120
            char_height = 140

            self.draw_rect(x, start_y, char_width, char_height, outline='#4fc3f7')
            self.draw_rect(x+8, start_y+8, char_width-16, char_height-16, outline='#29b6f6')

            # 字符标签
            self.draw_text(x + char_width//2 - 10, start_y + char_height//2 - 10,
                          char, '#4fc3f7', self.font_large)

            x += char_width + 25

    def draw_right_panel(self):
        """绘制右侧参数面板 - 重点：包含预设模板"""
        x = self.width - 320
        y = 76
        panel_width = 320
        panel_height = self.height - 76 - 35

        self.draw_rect(x, y, panel_width, panel_height, fill='#252526')
        self.draw_rect(x, y, 1, panel_height, fill='#3c3c3c')

        # ========== 预设模板区域（新增功能）==========
        py = y + 15

        # 预设模板标题
        self.draw_text(x+15, py, "⭐ 预设模板", '#4fc3f7', self.font_title)
        py += 30

        # 下拉选择框
        self.draw_rect(x+15, py, panel_width-30, 32, fill='#3c3c3c', outline='#555555', radius=4)
        self.draw_text(x+25, py+7, "30cm斜边字（常用）", '#ffffff', self.font_normal)
        self.draw_text(x+panel_width-45, py+7, "▼", '#888888', self.font_normal)
        py += 40

        # 预设列表提示
        presets = ['✓ 30cm斜边字（常用）', '  50cm直边字', '  连襟字模板', '  面板一体成型']
        for preset in presets[:2]:
            self.draw_text(x+25, py, preset, '#888888', self.font_small)
            py += 20
        py += 5

        # 智能推荐按钮（蓝色高亮）
        btn_width = panel_width - 30
        self.draw_rect(x+15, py, btn_width, 36, fill='#0078d4', radius=4)
        self.draw_text(x + 15 + btn_width//2 - 45, py+9, "⚡ 智能推荐", '#ffffff', self.font_title)
        py += 50

        # 分隔线
        self.draw_rect(x+15, py, panel_width-30, 1, fill='#4a4a4a')
        py += 20

        # ========== 基础参数区域 ==========
        self.draw_text(x+15, py, "基础参数", '#ffffff', self.font_title)
        py += 30

        params = [
            ('字壳高度', '30', 'mm'),
            ('斜边宽度', '5', 'mm'),
            ('壁厚', '1.2', 'mm'),
            ('层高', '0.3', 'mm'),
            ('底板厚度', '10', 'mm'),
        ]

        for label, value, unit in params:
            # 标签
            self.draw_text(x+20, py+5, label, '#cccccc', self.font_normal)
            # 输入框
            input_x = x + 110
            self.draw_rect(input_x, py, 120, 28, fill='#3c3c3c', outline='#555555', radius=3)
            self.draw_text(input_x+10, py+5, value, '#ffffff', self.font_normal)
            # 单位
            self.draw_text(input_x+130, py+5, unit, '#888888', self.font_normal)
            py += 38

        # 分隔线
        py += 10
        self.draw_rect(x+15, py, panel_width-30, 1, fill='#4a4a4a')
        py += 20

        # ========== 打印参数 ==========
        self.draw_text(x+15, py, "打印参数", '#ffffff', self.font_title)
        py += 30

        print_params = [
            ('打印速度', '40', 'mm/s'),
            ('喷头温度', '225', '°C'),
        ]

        for label, value, unit in print_params:
            self.draw_text(x+20, py+5, label, '#cccccc', self.font_normal)
            input_x = x + 110
            self.draw_rect(input_x, py, 120, 28, fill='#3c3c3c', outline='#555555', radius=3)
            self.draw_text(input_x+10, py+5, value, '#ffffff', self.font_normal)
            self.draw_text(input_x+130, py+5, unit, '#888888', self.font_normal)
            py += 38

        # ========== 选项卡区域 ==========
        py += 15
        self.draw_rect(x+15, py, panel_width-30, 1, fill='#4a4a4a')
        py += 15

        # 选项卡
        tabs = ['字壳', '换色', '台阶', '防翘', '连襟', '包边', '面板']
        tab_width = (panel_width - 30) // len(tabs)

        for i, tab in enumerate(tabs):
            tab_x = x + 15 + i * tab_width
            if i == 0:
                self.draw_rect(tab_x, py, tab_width-2, 28, fill='#094771', radius=3)
                self.draw_text(tab_x + tab_width//2 - 12, py+6, tab, '#ffffff', self.font_small)
            else:
                self.draw_text(tab_x + tab_width//2 - 12, py+6, tab, '#888888', self.font_small)

        py += 40

        # 高级参数折叠
        self.draw_text(x+20, py, "▶ 高级参数", '#888888', self.font_normal)

    def draw_status_bar(self):
        """绘制底部状态栏"""
        y = self.height - 35
        self.draw_rect(0, y, self.width, 35, fill='#007acc')

        # 状态信息
        status_items = [
            "⏱ 预计时间: 2h 35m",
            "📏 耗材: 128.5m",
            "🖨 机器: ZC-80",
            "🟢 已连接",
        ]

        x = 20
        for item in status_items:
            self.draw_text(x, y+9, item, '#ffffff', self.font_normal)
            x += 180

        # 右侧版本信息
        self.draw_text(self.width - 200, y+9, "MINGDA SignMaker v1.0", '#ffffff', self.font_small)

    def generate(self):
        """生成完整UI"""
        self.draw_menu_bar()
        self.draw_toolbar()
        self.draw_left_panel()
        self.draw_canvas_area()
        self.draw_right_panel()
        self.draw_status_bar()

        return self.img

    def save(self, filepath):
        """保存图片"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.img.save(filepath, 'PNG', quality=95)
        print(f"UI design saved to: {filepath}")


if __name__ == "__main__":
    generator = UIGenerator(1920, 1080)
    img = generator.generate()

    output_path = r"E:\MINGDA SignMaker\docs\UI\UI_Modern_WithPresets.png"
    generator.save(output_path)
    print("Done!")
