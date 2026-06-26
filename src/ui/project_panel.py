"""
MINGDA SignMaker - project panel widget

Displays imported assets and individual contours in a structured list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

from src.core.asset_utils import get_contour_asset_id, get_contour_asset_name
from src.core.types import Contour
from .icon_utils import build_theme_icon
from .theme import COLORS


@dataclass
class _PanelRow:
    kind: str
    indices: List[int]
    item: "_ProjectListItem"
    asset_id: str = ""


class _ElidedLabel(QLabel):
    """QLabel variant that can shrink inside a fixed-width row."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setMinimumWidth(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API override
        self._full_text = text or ""
        self.setToolTip(self._full_text)
        self._refresh_elided_text()

    def resizeEvent(self, event):  # noqa: N802 - Qt API override
        super().resizeEvent(event)
        self._refresh_elided_text()

    def refresh_elision(self) -> None:
        self._refresh_elided_text()

    def _refresh_elided_text(self) -> None:
        # The label stylesheet gives the name 12px horizontal padding.
        available_width = max(0, self.contentsRect().width() - 24)
        text = self.fontMetrics().elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            available_width,
        )
        if QLabel.text(self) != text:
            QLabel.setText(self, text)


class _ProjectListItem(QFrame):
    """Shared row widget used by both asset rows and contour rows."""

    clicked = Signal(object)
    delete_clicked = Signal(object)
    toggle_clicked = Signal(object)
    release_clicked = Signal(object)

    COLORS = [
        "#E91E63",
        "#9C27B0",
        "#3F51B5",
        "#2196F3",
        "#00BCD4",
        "#4CAF50",
        "#FF9800",
        "#F44336",
    ]

    def __init__(
        self,
        row_key: object,
        title: str,
        *,
        color_index: int = 0,
        secondary_text: str = "",
        indent: int = 0,
        collapsible: bool = False,
        expanded: bool = False,
        releasable: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.row_key = row_key
        self._selection_state = "none"
        self._expanded = expanded
        self._color = self.COLORS[color_index % len(self.COLORS)]
        self.setObjectName("projectListItem")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(indent, 0, 8, 0)
        layout.setSpacing(0)

        self.color_bar = QFrame()
        self.color_bar.setFixedWidth(4)
        self.color_bar.setStyleSheet(
            f"background-color: {self._color}; border-radius: 2px;"
        )
        layout.addWidget(self.color_bar)

        if collapsible:
            self.toggle_btn = QPushButton("-" if expanded else "+")
            self.toggle_btn.setObjectName("rowToggle")
            self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle_btn.setFixedSize(20, 20)
            self.toggle_btn.clicked.connect(
                lambda: self.toggle_clicked.emit(self.row_key)
            )
            layout.addWidget(self.toggle_btn)
        else:
            spacer = QWidget()
            spacer.setFixedWidth(20)
            layout.addWidget(spacer)
            self.toggle_btn = None

        self.name_label = _ElidedLabel(title)
        self.name_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self.name_label.setStyleSheet(
            f"""
            color: {COLORS.text_primary};
            font-size: 13px;
            padding: 0 12px;
        """
        )
        self.name_label.refresh_elision()
        layout.addWidget(self.name_label, 1)

        self.secondary_label = QLabel(secondary_text)
        self.secondary_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.secondary_label.setStyleSheet(
            f"""
            color: {COLORS.text_muted};
            font-size: 12px;
            padding: 0 8px 0 0;
        """
        )
        self.secondary_label.setVisible(bool(secondary_text))
        layout.addWidget(self.secondary_label)

        if releasable:
            self.release_btn = QPushButton()
            self.release_btn.setFixedSize(28, 28)
            self.release_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.release_btn.setIconSize(QSize(18, 18))
            self.release_btn.setIcon(self._build_row_icon("explode_asset.svg"))
            self.release_btn.setToolTip(self.tr("Explode Asset"))
            self.release_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: rgba(31, 111, 235, 0.16);
                }
            """
            )
            self.release_btn.clicked.connect(
                lambda: self.release_clicked.emit(self.row_key)
            )
            layout.addWidget(self.release_btn)
        else:
            self.release_btn = None

        self.delete_btn = QPushButton()
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setIconSize(QSize(18, 18))
        self.delete_btn.setIcon(self._build_row_icon("delete.png"))
        self.delete_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.2);
            }
        """
        )
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.row_key))
        layout.addWidget(self.delete_btn)

        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    @staticmethod
    def _build_row_icon(name: str) -> QIcon:
        return build_theme_icon(
            f":/icons/icons/{name}",
            QSize(18, 18),
            light_color=COLORS.accent_primary,
            disabled_light_color=COLORS.text_muted,
        )

    def apply_theme(self):
        self.name_label.setStyleSheet(
            f"""
            color: {COLORS.text_primary};
            font-size: 13px;
            padding: 0 12px;
        """
        )
        self.name_label.refresh_elision()
        self.secondary_label.setStyleSheet(
            f"""
            color: {COLORS.text_muted};
            font-size: 12px;
            padding: 0 8px 0 0;
        """
        )
        if self.release_btn is not None:
            self.release_btn.setIcon(self._build_row_icon("explode_asset.svg"))
        self.delete_btn.setIcon(self._build_row_icon("delete.png"))
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.row_key)
        super().mousePressEvent(event)

    def set_selection_state(self, state: str):
        self._selection_state = state
        self._update_style()

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        if self.toggle_btn is not None:
            self.toggle_btn.setText("-" if expanded else "+")

    def _update_style(self):
        if self._selection_state == "full":
            background = COLORS.editor_list_item_bg
            border = COLORS.accent_primary
        elif self._selection_state == "partial":
            background = COLORS.bg_panel
            border = COLORS.border_hover
        else:
            background = COLORS.editor_list_item_bg
            border = COLORS.border_default

        self.setStyleSheet(
            f"""
            QFrame#projectListItem {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QFrame#projectListItem:hover {{
                background-color: {COLORS.bg_panel};
                border-color: {COLORS.border_hover};
            }}
            QPushButton#rowToggle {{
                background-color: transparent;
                border: none;
                color: {COLORS.text_secondary};
                font-size: 12px;
            }}
            QPushButton#rowToggle:hover {{
                color: {COLORS.text_primary};
            }}
        """
        )


class ProjectPanel(QWidget):
    """Project panel with logical asset grouping."""

    contour_selected = Signal(int)
    selection_changed = Signal(list)
    contour_deleted = Signal(int)
    delete_requested = Signal(list)
    release_asset_requested = Signal(str)
    import_clicked = Signal()
    order_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("projectPanel")

        self._contours: List[Contour] = []
        self._rows: List[_PanelRow] = []
        self._selected_indices: List[int] = []
        self._asset_expanded: Dict[str, bool] = {}
        self._asset_members: Dict[str, List[int]] = {}
        self._asset_names: Dict[str, str] = {}
        self._asset_color_indices: Dict[str, int] = {}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title_label = QLabel(self.tr("Shape List"))
        self.title_label.setStyleSheet(
            f"""
            padding: 12px 14px 12px 12px;
            background-color: {COLORS.editor_sidebar_right_header_bg};
            color: {COLORS.text_primary};
            font-size: 13px;
            font-weight: 600;
            border-bottom: 1px solid {COLORS.editor_sidebar_right_accent};
            border-right: 4px solid {COLORS.editor_sidebar_right_accent};
        """
        )
        layout.addWidget(self.title_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                background-color: {COLORS.editor_sidebar_right_bg};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS.editor_sidebar_right_bg};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS.border_default};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS.border_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """
        )

        self.list_container = QWidget()
        self.list_container.setStyleSheet(
            f"background-color: {COLORS.editor_sidebar_right_bg};"
        )
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(4, 4, 4, 4)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area, 1)

        self.import_btn = QPushButton(self.tr("+ Import Shape"))
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.setFixedHeight(52)
        self.import_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS.editor_list_item_bg};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.editor_toolbar_border};
                border-radius: 4px;
                margin: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bg_panel};
                border-color: {COLORS.border_hover};
                color: {COLORS.text_primary};
            }}
        """
        )
        self.import_btn.clicked.connect(self.import_clicked.emit)
        layout.addWidget(self.import_btn)

    def apply_theme(self):
        """Refresh panel and row styles after the global theme changes."""
        self.title_label.setStyleSheet(
            f"""
            padding: 12px 14px 12px 12px;
            background-color: {COLORS.editor_sidebar_right_header_bg};
            color: {COLORS.text_primary};
            font-size: 13px;
            font-weight: 600;
            border-bottom: 1px solid {COLORS.editor_sidebar_right_accent};
            border-right: 4px solid {COLORS.editor_sidebar_right_accent};
        """
        )
        self.scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                background-color: {COLORS.editor_sidebar_right_bg};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS.editor_sidebar_right_bg};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS.border_default};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS.border_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """
        )
        self.list_container.setStyleSheet(
            f"background-color: {COLORS.editor_sidebar_right_bg};"
        )
        self.import_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS.editor_list_item_bg};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.editor_toolbar_border};
                border-radius: 4px;
                margin: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bg_panel};
                border-color: {COLORS.border_hover};
                color: {COLORS.text_primary};
            }}
        """
        )
        for row in self._rows:
            row.item.apply_theme()
        self.update()

    def update_contours(self, contours: List[Contour]):
        self._contours = contours
        self._rebuild_asset_maps()
        self._prune_expand_state()
        self._clear_rows()

        rendered_assets = set()
        for index, contour in enumerate(contours):
            asset_id = get_contour_asset_id(contour)
            if asset_id:
                if asset_id in rendered_assets:
                    continue
                rendered_assets.add(asset_id)
                self._add_asset_rows(asset_id)
                continue

            self._add_contour_row(index)

        self.list_layout.addStretch()
        self._selected_indices = self._normalize_selected_indices(
            self._selected_indices,
            len(self._contours),
        )
        self._refresh_selection_styles()

    def _rebuild_asset_maps(self):
        self._asset_members = {}
        self._asset_names = {}
        self._asset_color_indices = {}

        for index, contour in enumerate(self._contours):
            asset_id = get_contour_asset_id(contour)
            if not asset_id:
                continue

            self._asset_members.setdefault(asset_id, []).append(index)
            self._asset_color_indices.setdefault(asset_id, index)

            asset_name = get_contour_asset_name(contour)
            if asset_name and asset_id not in self._asset_names:
                self._asset_names[asset_id] = asset_name

        for asset_id in self._asset_members:
            self._asset_names.setdefault(asset_id, self.tr("Asset"))

    def _prune_expand_state(self):
        valid_asset_ids = set(self._asset_members)
        self._asset_expanded = {
            asset_id: expanded
            for asset_id, expanded in self._asset_expanded.items()
            if asset_id in valid_asset_ids
        }
        for asset_id, indices in self._asset_members.items():
            if len(indices) > 1:
                self._asset_expanded.setdefault(asset_id, False)

    def _clear_rows(self):
        self._rows.clear()
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_asset_rows(self, asset_id: str):
        member_indices = list(self._asset_members.get(asset_id, []))
        if not member_indices:
            return

        expanded = self._asset_expanded.get(asset_id, False)
        row = _ProjectListItem(
            asset_id,
            self._asset_names.get(asset_id, self.tr("Asset")),
            color_index=self._asset_color_indices.get(asset_id, 0),
            secondary_text=f"({len(member_indices)})" if len(member_indices) > 1 else "",
            collapsible=len(member_indices) > 1,
            expanded=expanded,
            releasable=len(member_indices) > 1,
        )
        row.clicked.connect(self._on_asset_clicked)
        row.delete_clicked.connect(self._on_asset_delete)
        row.toggle_clicked.connect(self._on_asset_toggled)
        row.release_clicked.connect(self._on_asset_release)
        self.list_layout.addWidget(row)
        self._rows.append(
            _PanelRow(kind="asset", indices=member_indices, item=row, asset_id=asset_id)
        )

        if expanded and len(member_indices) > 1:
            for contour_index in member_indices:
                self._add_contour_row(
                    contour_index,
                    indent=20,
                    color_index=self._asset_color_indices.get(asset_id, contour_index),
                )

    def _add_contour_row(
        self,
        index: int,
        *,
        indent: int = 0,
        color_index: int | None = None,
    ):
        contour = self._contours[index]
        row = _ProjectListItem(
            index,
            self._contour_label(index, contour),
            color_index=index if color_index is None else color_index,
            indent=indent,
        )
        row.clicked.connect(self._on_contour_clicked)
        row.delete_clicked.connect(self._on_item_delete)
        self.list_layout.addWidget(row)
        self._rows.append(_PanelRow(kind="contour", indices=[index], item=row))

    def _contour_label(self, index: int, contour: Contour) -> str:
        if contour.name:
            return contour.name
        return self.tr("Letter-{index}").format(index=index + 1)

    def _toggle_selection(self, target_indices: List[int]) -> List[int]:
        if Qt.KeyboardModifier.ControlModifier in QApplication.keyboardModifiers():
            selected = list(self._selected_indices)
            if all(index in selected for index in target_indices):
                return [index for index in selected if index not in target_indices]

            existing = set(selected)
            selected.extend(index for index in target_indices if index not in existing)
            return selected

        return list(target_indices)

    def _on_asset_clicked(self, asset_id: str):
        target_indices = list(self._asset_members.get(asset_id, []))
        if not target_indices:
            return

        self._selected_indices = self._normalize_selected_indices(
            self._toggle_selection(target_indices),
            len(self._contours),
        )
        self._refresh_selection_styles()
        self.selection_changed.emit(list(self._selected_indices))

    def _on_asset_toggled(self, asset_id: str):
        self._asset_expanded[asset_id] = not self._asset_expanded.get(asset_id, False)
        self.update_contours(self._contours)

    def _on_asset_delete(self, asset_id: str):
        indices = list(self._asset_members.get(asset_id, []))
        if indices:
            self.delete_requested.emit(indices)

    def _on_asset_release(self, asset_id: str):
        self.release_asset_requested.emit(asset_id)

    def _on_contour_clicked(self, index: int):
        target_indices = [index]
        self._selected_indices = self._normalize_selected_indices(
            self._toggle_selection(target_indices),
            len(self._contours),
        )
        self._refresh_selection_styles()
        self.selection_changed.emit(list(self._selected_indices))
        if index in self._selected_indices:
            self.contour_selected.emit(index)

    def _on_item_clicked(self, index: int):
        """Compatibility helper used by existing tests."""
        self._on_contour_clicked(index)

    def _on_item_delete(self, index: int):
        self.contour_deleted.emit(index)
        self.delete_requested.emit([index])

    def get_selected_indices(self) -> List[int]:
        return self._normalize_selected_indices(self._selected_indices, len(self._contours))

    @staticmethod
    def _normalize_selected_indices(indices: List[int], upper_bound: int) -> List[int]:
        normalized: List[int] = []
        seen = set()
        for idx in indices:
            if 0 <= idx < upper_bound and idx not in seen:
                normalized.append(idx)
                seen.add(idx)
        return normalized

    def _refresh_selection_styles(self):
        selected = set(self.get_selected_indices())
        for row in self._rows:
            if row.kind == "asset":
                row_set = set(row.indices)
                if row_set and row_set.issubset(selected):
                    state = "full"
                elif row_set & selected:
                    state = "partial"
                else:
                    state = "none"
            else:
                state = "full" if row.indices[0] in selected else "none"
            row.item.set_selection_state(state)

    def set_selected_indices(self, indices: List[int]):
        normalized: List[int] = []
        seen = set()
        for idx in indices:
            if 0 <= idx < len(self._contours) and idx not in seen:
                normalized.append(idx)
                seen.add(idx)

        self._selected_indices = normalized
        self._refresh_selection_styles()

    def set_selected(self, index: int):
        self.set_selected_indices([index])

    def clear_selection(self):
        self.set_selected_indices([])
