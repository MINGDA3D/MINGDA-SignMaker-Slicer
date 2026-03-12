"""
Text Dialog - UI for text generation
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from typing import List, Optional
from ..core.font_manager import FontManager
from ..core.text_generator import TextGenerator
from ..core.types import Contour


class TextDialog(QDialog):
    """Text generation dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.font_manager = FontManager()
        self.text_generator = TextGenerator()
        self.contours: List[Contour] = []
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(self.tr("Generate Text"))
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Font selection
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(self.tr("Font:")))
        self.font_combo = QComboBox()
        self.font_combo.addItems(self.font_manager.get_font_names())
        font_layout.addWidget(self.font_combo, 1)
        layout.addLayout(font_layout)

        # Text input
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel(self.tr("Text:")))
        self.text_input = QLineEdit()
        text_layout.addWidget(self.text_input, 1)
        layout.addLayout(text_layout)

        # Font size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel(self.tr("Font Size (mm):")))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 1000)
        self.size_spin.setValue(50)
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        # Character spacing
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel(self.tr("Character Spacing (mm):")))
        self.spacing_spin = QDoubleSpinBox()
        self.spacing_spin.setRange(-50, 100)
        self.spacing_spin.setValue(0)
        self.spacing_spin.setSingleStep(0.5)
        spacing_layout.addWidget(self.spacing_spin)
        spacing_layout.addStretch()
        layout.addLayout(spacing_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton(self.tr("Cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        self.btn_ok = QPushButton(self.tr("OK"))
        self.btn_ok.clicked.connect(self._on_ok)
        self.btn_ok.setDefault(True)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        """Generate contours and accept dialog"""
        text = self.text_input.text().strip()
        if not text:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please enter text"))
            return

        font_name = self.font_combo.currentText()
        font_path = self.font_manager.get_font_path(font_name)
        if not font_path:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Font not found"))
            return

        try:
            self.contours = self.text_generator.generate_text_contours(
                text=text,
                font_path=font_path,
                font_size=self.size_spin.value(),
                spacing=self.spacing_spin.value()
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def get_contours(self) -> List[Contour]:
        """Get generated contours"""
        return self.contours

