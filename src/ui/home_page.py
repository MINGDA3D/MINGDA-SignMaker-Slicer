"""
MINGDA SignMaker - 首页组件
Home Page Widget - 完全按照 generate_ui_home.py 设计规范实现
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QLinearGradient,
    QRadialGradient, QPixmap, QPen, QBrush, QFontMetrics
)


# ============================================
# 配色方案 - 与 generate_ui_home.py 完全一致
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
    "preview_bg": "#2D323C",  # (45, 50, 60)
    "wire_color": "#7887A0",  # (120, 135, 160)
}


def hex_to_qcolor(hex_color: str) -> QColor:
    """将十六进制颜色转换为 QColor"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return QColor(r, g, b)


class ProjectCard(QFrame):
    """最近项目卡片 - 按照设计规范实现"""

    clicked = Signal(str)

    def __init__(
        self,
        name: str,
        date: str,
        preview_char: str = "字",
        file_path: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.file_path = file_path
        self.name = name
        self.date = date
        self.preview_char = preview_char
        self._hovered = False

        # 尺寸：card_size = 260, preview_size = 180
        self.card_width = 260
        self.card_height = 260
        self.preview_size = 180
        self.preview_margin = (self.card_width - self.preview_size) // 2

        self.setFixedSize(self.card_width, self.card_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        """绘制卡片"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        card_rect = QRectF(0, 0, self.card_width, self.card_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(hex_to_qcolor(COLORS["bg_card"]))
        painter.drawRoundedRect(card_rect, 12, 12)

        if self._hovered:
            painter.setPen(QPen(hex_to_qcolor(COLORS["accent_primary"]), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(card_rect.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)

        # 预览区域位置
        preview_x = self.preview_margin
        preview_y = 14
        preview_size = self.preview_size

        # 绘制预览背景 (圆角矩形)
        preview_rect = QRectF(preview_x, preview_y, preview_size, preview_size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(hex_to_qcolor(COLORS["preview_bg"]))
        painter.drawRoundedRect(preview_rect, 10, 10)

        # 悬浮时的边框
        if self._hovered:
            painter.setPen(QPen(hex_to_qcolor(COLORS["accent_primary"]), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(preview_rect, 10, 10)

        # 绘制预览字符（线框效果）
        icon_cx = preview_x + preview_size // 2
        icon_cy = preview_y + preview_size // 2

        # 字体设置 - 72px
        font = QFont("Microsoft YaHei UI", 54)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)

        # 绘制字符轮廓（线框效果）
        char_path = QPainterPath()
        fm = QFontMetrics(font)
        char_rect = fm.boundingRect(self.preview_char)
        char_x = icon_cx - char_rect.width() / 2
        char_y = icon_cy + char_rect.height() / 4
        char_path.addText(char_x, char_y, font, self.preview_char)

        # 描边效果
        painter.setPen(QPen(hex_to_qcolor(COLORS["wire_color"]), 2))
        painter.setBrush(hex_to_qcolor(COLORS["preview_bg"]))
        painter.drawPath(char_path)

        # 文件名
        text_y = preview_y + preview_size + 8
        font_name = QFont("Microsoft YaHei UI", 10)
        painter.setFont(font_name)
        painter.setPen(hex_to_qcolor(COLORS["text_primary"]))

        display_name = QFontMetrics(font_name).elidedText(
            self.name,
            Qt.TextElideMode.ElideRight,
            self.preview_size,
        )
        painter.drawText(preview_x, int(text_y + 12), display_name)

        # 日���
        time_y = text_y + 18
        font_date = QFont("Microsoft YaHei UI", 8)
        painter.setFont(font_date)
        painter.setPen(hex_to_qcolor(COLORS["text_muted"]))
        painter.drawText(preview_x, int(time_y + 10), self.date)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)


class CaseCard(QFrame):
    """精选案例卡片 - 按照设计规范实现"""

    clicked = Signal(str)

    def __init__(
        self,
        brand: str,
        style: str,
        logo_path: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.brand = brand
        self.style = style
        self.logo_path = logo_path
        self._hovered = False
        self._logo_pixmap = None

        # 尺寸：case_card_w = 260, case_card_h = 220
        self.card_width = 260
        self.card_height = 220
        self.logo_size = 140

        self.setFixedSize(self.card_width, self.card_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        # 加载logo
        self._load_logo()

    def _load_logo(self):
        """加载logo图片"""
        if self.logo_path and Path(self.logo_path).exists():
            pixmap = QPixmap(self.logo_path)
            if not pixmap.isNull():
                # 缩放到 80x80
                max_size = 80
                self._logo_pixmap = pixmap.scaled(
                    max_size, max_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

    def paintEvent(self, event):
        """绘制卡片"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # 卡片背景
        card_rect = QRectF(0, 0, self.card_width, self.card_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(hex_to_qcolor(COLORS["bg_card"]))
        painter.drawRoundedRect(card_rect, 12, 12)

        # 悬浮效果
        if self._hovered:
            painter.setPen(QPen(hex_to_qcolor(COLORS["accent_primary"]), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(card_rect.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)

        # Logo区域位置
        logo_margin = (self.card_width - self.logo_size) // 2
        logo_x = logo_margin
        logo_y = 15

        # Logo背景
        logo_rect = QRectF(logo_x, logo_y, self.logo_size, self.logo_size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(hex_to_qcolor(COLORS["preview_bg"]))
        painter.drawRoundedRect(logo_rect, 10, 10)

        # 绘制Logo或首字母
        logo_cx = logo_x + self.logo_size // 2
        logo_cy = logo_y + self.logo_size // 2

        if self._logo_pixmap and not self._logo_pixmap.isNull():
            paste_x = int(logo_cx - self._logo_pixmap.width() / 2)
            paste_y = int(logo_cy - self._logo_pixmap.height() / 2)
            painter.drawPixmap(paste_x, paste_y, self._logo_pixmap)
        else:
            # 显示首字母
            font = QFont("Microsoft YaHei UI", 20)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(hex_to_qcolor(COLORS["accent_primary"]))
            painter.drawText(
                int(logo_cx - 10), int(logo_cy + 8),
                self.brand[0] if self.brand else "?"
            )

        # 品牌名称（居中）
        text_y = logo_y + self.logo_size + 10
        font_brand = QFont("Microsoft YaHei UI", 10)
        painter.setFont(font_brand)
        painter.setPen(hex_to_qcolor(COLORS["text_primary"]))

        fm = QFontMetrics(font_brand)
        brand_w = fm.horizontalAdvance(self.brand)
        brand_x = (self.card_width - brand_w) // 2
        painter.drawText(brand_x, int(text_y + 12), self.brand)

        # 工艺类型（居中）
        font_style = QFont("Microsoft YaHei UI", 8)
        painter.setFont(font_style)
        painter.setPen(hex_to_qcolor(COLORS["text_muted"]))

        fm = QFontMetrics(font_style)
        style_w = fm.horizontalAdvance(self.style)
        style_x = (self.card_width - style_w) // 2
        painter.drawText(style_x, int(text_y + 32), self.style)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.brand)
        super().mousePressEvent(event)


class HomePage(QWidget):
    """首页组件 - 完全按��� generate_ui_home.py 设计规范实现"""

    # 信号
    new_project_clicked = Signal()
    open_file_clicked = Signal()
    recent_project_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homePage")

        # 数据
        self._recent_projects = []
        self._cards = []

        # 布局参数
        self.hero_top = 88
        self.button_spacing = 20
        self.section_gap = 92
        self.section_title_gap = 54
        self.card_gap_x = 20
        self.card_gap_y = 18
        self.card_max_columns = 5
        self.content_margin = 72
        self.bottom_padding = 40
        self.empty_state_height = 180
        self._content_height = 720

        # 初始化
        self._load_demo_data()

    def _load_demo_data(self):
        """初始化首页数据。"""
        self._recent_projects = []
        self._cards = []

    def _get_layout_metrics(self) -> dict:
        """根据当前窗口尺寸计算首页布局。"""
        hero_y = max(72, min(110, self.height() // 8))
        btn_y = hero_y + 160
        section_y = btn_y + self.section_gap
        content_y = section_y + self.section_title_gap
        return {
            "hero_y": hero_y,
            "btn_y": btn_y,
            "section_y": section_y,
            "content_y": content_y,
        }

    def _get_card_layout(self) -> dict:
        """计算最近项目卡片布局和所需内容高度。"""
        metrics = self._get_layout_metrics()
        card_size = 260
        available_width = max(
            card_size,
            self.width() - self.content_margin * 2,
        )
        cols = max(
            1,
            min(
                self.card_max_columns,
                (available_width + self.card_gap_x) // (card_size + self.card_gap_x),
            ),
        )
        total_width = cols * card_size + max(0, cols - 1) * self.card_gap_x
        start_x = max(self.content_margin, (self.width() - total_width) // 2)

        if self._recent_projects:
            rows = (min(len(self._recent_projects), 10) + cols - 1) // cols
            required_height = (
                metrics["content_y"]
                + rows * card_size
                + max(0, rows - 1) * self.card_gap_y
                + self.bottom_padding
            )
        else:
            required_height = (
                metrics["content_y"]
                + self.empty_state_height
                + self.bottom_padding
            )

        return {
            "metrics": metrics,
            "card_size": card_size,
            "cols": cols,
            "start_x": start_x,
            "required_height": required_height,
        }

    def _sync_content_height(self):
        """更新首页在滚动容器中的最小高度。"""
        layout = self._get_card_layout()
        self._content_height = max(720, layout["required_height"])
        self.setMinimumHeight(self._content_height)
        self.updateGeometry()

    def _create_cards(self):
        """创建卡片组件"""
        # 清除旧卡片
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards = []

        for project in self._recent_projects[:10]:
            card = ProjectCard(
                name=project["name"],
                date=project["date"],
                preview_char=project.get("char", "S"),
                file_path=project.get("path", ""),
                parent=self
            )
            card.clicked.connect(self.recent_project_clicked.emit)
            self._cards.append(card)

        self._sync_content_height()
        self._position_cards()

    def _position_cards(self):
        """定位卡片"""
        if not self._cards:
            self._sync_content_height()
            return

        layout = self._get_card_layout()
        metrics = layout["metrics"]
        card_size = layout["card_size"]
        cols = layout["cols"]
        start_x = layout["start_x"]
        self._sync_content_height()

        for i, card in enumerate(self._cards):
            row = i // cols
            col = i % cols
            cx = start_x + col * (card_size + self.card_gap_x)
            cy = metrics["content_y"] + row * (card_size + self.card_gap_y)
            card.move(cx, cy)
            card.show()

    def set_recent_projects(self, projects: List[dict]):
        """设置最近项目列表"""
        self._recent_projects = projects
        self._create_cards()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(max(1200, self.width()), self._content_height)

    def minimumSizeHint(self) -> QSize:
        return QSize(960, self._content_height)

    def paintEvent(self, event):
        """绘制整个首页"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()
        metrics = self._get_layout_metrics()
        hero_y = metrics["hero_y"]
        btn_y = metrics["btn_y"]
        section_y = metrics["section_y"]

        # ============================================
        # 背景：深邃渐变
        # ============================================
        bg_color = hex_to_qcolor(COLORS["bg_base"])
        painter.fillRect(self.rect(), bg_color)

        # ============================================
        # 多层光晕效果
        # ============================================
        self._draw_soft_glow(painter, w // 2, h // 2 - 100, 600, hex_to_qcolor(COLORS["accent_primary"]), 0.06)
        self._draw_soft_glow(painter, w // 2 - 300, h // 2 - 50, 400, hex_to_qcolor(COLORS["info"]), 0.04)
        self._draw_soft_glow(painter, w // 2 + 300, h // 2 - 50, 400, hex_to_qcolor(COLORS["accent_secondary"]), 0.04)

        # ============================================
        # 英雄区域
        # ============================================
        # 主标题 "SignMakerSlicer"
        font_display = QFont("Microsoft YaHei UI", 42)
        font_display.setWeight(QFont.Weight.Bold)
        painter.setFont(font_display)
        painter.setPen(hex_to_qcolor(COLORS["text_primary"]))

        title = "MINGDA SignMaker"
        fm = QFontMetrics(font_display)
        title_w = fm.horizontalAdvance(title)
        title_x = (w - title_w) // 2
        painter.drawText(title_x, hero_y + 40, title)

        # 副标题（渐变色）
        subtitle = self.tr("Professional Illuminated Sign Slicer")
        font_h2 = QFont("Microsoft YaHei UI", 12)
        self._draw_gradient_text(
            painter, subtitle, font_h2,
            hero_y + 75,
            hex_to_qcolor(COLORS["accent_primary"]),
            hex_to_qcolor(COLORS["accent_secondary"]),
            w
        )

        # 功能点（渐变色）
        features = self.tr("One-click G-code  ·  Multiple Edge Types  ·  High Precision")
        font_body = QFont("Microsoft YaHei UI", 9)
        self._draw_gradient_text(
            painter, features, font_body,
            hero_y + 108,
            QColor(6, 182, 212),
            QColor(168, 85, 247),
            w
        )

        # ============================================
        # 核心操作按钮
        # ============================================
        btn_w = 160
        btn_h = 48
        btn_gap = 20
        btn1_x = (w - btn_w * 2 - btn_gap) // 2
        btn2_x = btn1_x + btn_w + btn_gap

        # 新建项目按钮（蓝色填充）
        btn1_rect = QRectF(btn1_x, btn_y, btn_w, btn_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(hex_to_qcolor(COLORS["accent_primary"]))
        painter.drawRoundedRect(btn1_rect, 10, 10)

        font_btn = QFont("Microsoft YaHei UI", 10)
        painter.setFont(font_btn)
        painter.setPen(QColor(255, 255, 255))
        fm = QFontMetrics(font_btn)
        btn1_text = self.tr("+ New Project")
        btn1_tw = fm.horizontalAdvance(btn1_text)
        painter.drawText(int(btn1_x + (btn_w - btn1_tw) / 2), int(btn_y + btn_h / 2 + 5), btn1_text)

        # 打开文件按钮（边框）
        btn2_rect = QRectF(btn2_x, btn_y, btn_w, btn_h)
        painter.setPen(QPen(hex_to_qcolor(COLORS["border_default"]), 1))
        painter.setBrush(hex_to_qcolor(COLORS["bg_card"]))
        painter.drawRoundedRect(btn2_rect, 10, 10)

        painter.setPen(hex_to_qcolor(COLORS["text_secondary"]))
        btn2_text = self.tr("Open File")
        btn2_tw = fm.horizontalAdvance(btn2_text)
        painter.drawText(int(btn2_x + (btn_w - btn2_tw) / 2), int(btn_y + btn_h / 2 + 5), btn2_text)

        # 保存按钮区域用于点击检测
        self._btn1_rect = btn1_rect
        self._btn2_rect = btn2_rect

        # 最近项目区域
        section_width = min(1400, w - self.content_margin * 2)
        section_x = (w - section_width) // 2
        section_title = self.tr("Recent Projects")

        font_section = QFont("Microsoft YaHei UI", 14)
        font_section.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font_section)
        painter.setPen(hex_to_qcolor(COLORS["text_primary"]))
        painter.drawText(section_x, section_y, section_title)

        line_y = section_y + 16
        painter.setPen(QPen(hex_to_qcolor(COLORS["border_subtle"]), 1))
        painter.drawLine(section_x + 150, line_y, section_x + section_width, line_y)

        if not self._recent_projects:
            empty_rect = QRectF(section_x, metrics["content_y"] + 10, section_width, 170)
            painter.setPen(QPen(hex_to_qcolor(COLORS["border_subtle"]), 1))
            painter.setBrush(hex_to_qcolor(COLORS["bg_primary"]))
            painter.drawRoundedRect(empty_rect, 16, 16)

            empty_title_font = QFont("Microsoft YaHei UI", 13)
            empty_title_font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(empty_title_font)
            painter.setPen(hex_to_qcolor(COLORS["text_primary"]))
            painter.drawText(
                empty_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                "\n" + self.tr("No recent projects yet"),
            )

            body_font = QFont("Microsoft YaHei UI", 10)
            painter.setFont(body_font)
            painter.setPen(hex_to_qcolor(COLORS["text_secondary"]))
            body_rect = empty_rect.adjusted(40, 68, -40, -36)
            painter.drawText(
                body_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                self.tr("Open or save a SignMaker project to see it here."),
            )

    def _draw_soft_glow(self, painter: QPainter, cx: int, cy: int, radius: int, color: QColor, intensity: float):
        """绘制柔和光晕"""
        for r in range(radius, 0, -20):
            alpha = int(255 * intensity * (r / radius) ** 3)
            if alpha > 0:
                glow_color = QColor(color.red(), color.green(), color.blue(), alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow_color)
                painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    def _draw_gradient_text(self, painter: QPainter, text: str, font: QFont, y: int,
                            color_start: QColor, color_end: QColor, width: int):
        """绘制渐变色文字"""
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(text)
        x = (width - text_w) // 2

        # 创建渐变
        gradient = QLinearGradient(x, 0, x + text_w, 0)
        gradient.setColorAt(0, color_start)
        gradient.setColorAt(1, color_end)

        painter.setPen(QPen(QBrush(gradient), 1))
        painter.drawText(x, y + fm.ascent(), text)

    def mousePressEvent(self, event):
        """处理鼠标点击"""
        pos = event.position()

        # 检查按钮点击
        if hasattr(self, '_btn1_rect') and self._btn1_rect.contains(pos):
            self.new_project_clicked.emit()
            return

        if hasattr(self, '_btn2_rect') and self._btn2_rect.contains(pos):
            self.open_file_clicked.emit()
            return

        super().mousePressEvent(event)

    def resizeEvent(self, event):
        """窗口大小改变时重新定位卡片"""
        self._position_cards()
        super().resizeEvent(event)
