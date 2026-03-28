import os
import shutil
import uuid
import zipfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.business.project_format import PREVIEW_FILE, save_project
from src.business.settings_manager import SettingsManager
from src.core.types import Contour, Path as ContourPath, Point, Project, ProjectMeta
from src.ui.main_window import MainWindow


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def workspace_tmp_dir():
    tmpdir = Path.cwd() / f".tmp_recent_projects_{uuid.uuid4().hex}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def window(qapp, workspace_tmp_dir, monkeypatch):
    settings_dir = workspace_tmp_dir / "settings"
    monkeypatch.setattr(
        "src.ui.main_window.init_settings_manager",
        lambda: SettingsManager(str(settings_dir)),
    )
    window = MainWindow()
    try:
        yield window
    finally:
        window.close()


def _create_project_file(
    base_dir: Path,
    file_name: str,
    project_name: str,
    *,
    contours: list[Contour] | None = None,
    preview_png: bytes | None = None,
) -> Path:
    file_path = base_dir / file_name
    save_project(
        Project(
            meta=ProjectMeta(name=project_name),
            contours=list(contours or []),
        ),
        str(file_path),
        preview_png=preview_png,
    )
    return file_path


def _rect_contour(x1: float, y1: float, x2: float, y2: float, name: str = "") -> Contour:
    return Contour(
        outer=ContourPath(
            points=[
                Point(x1, y1),
                Point(x2, y1),
                Point(x2, y2),
                Point(x1, y2),
            ],
            is_closed=True,
        ),
        name=name,
    )


def test_settings_manager_remove_recent_file_preserves_remaining_order(workspace_tmp_dir):
    sm = SettingsManager(str(workspace_tmp_dir / "config"))

    sm.add_recent_file("C:/projects/first.smp")
    sm.add_recent_file("C:/projects/second.smp")
    sm.add_recent_file("C:/projects/third.smp")

    sm.remove_recent_file("C:/projects/second.smp")

    assert sm.get_recent_files() == [
        str(Path("C:/projects/third.smp").resolve()),
        str(Path("C:/projects/first.smp").resolve()),
    ]


def test_save_project_updates_home_recent_projects(window, workspace_tmp_dir):
    file_path = workspace_tmp_dir / "saved_from_window.smp"
    window.contours = [_rect_contour(0, 0, 10, 10, "A")]

    assert window._save_project(str(file_path)) is True

    with zipfile.ZipFile(file_path, "r") as zf:
        assert PREVIEW_FILE in zf.namelist()

    assert window.settings_manager.get_recent_files()[0] == str(file_path.resolve())
    assert window.home_page._recent_projects[0]["path"] == str(file_path.resolve())
    assert window.home_page._recent_projects[0]["name"] == "saved_from_window"
    assert window.home_page._recent_projects[0]["preview_pixmap"] is not None
    assert window.home_page._cards[0].preview_pixmap is not None


def test_open_project_moves_recent_project_to_front(window, workspace_tmp_dir):
    older_project = _create_project_file(workspace_tmp_dir, "older.smp", "Older Project")
    newer_project = _create_project_file(workspace_tmp_dir, "newer.smp", "Newer Project")

    window.settings_manager.add_recent_file(str(older_project))
    window._refresh_home_recent_projects()

    assert window._load_project(str(newer_project)) is True

    assert window.settings_manager.get_recent_files()[0] == str(newer_project.resolve())
    assert window.home_page._recent_projects[0]["path"] == str(newer_project.resolve())
    assert window.home_page._recent_projects[0]["name"] == "Newer Project"


def test_refresh_home_recent_projects_filters_missing_and_non_smp_entries(window, workspace_tmp_dir):
    valid_project = _create_project_file(workspace_tmp_dir, "valid.smp", "Valid Project")
    missing_project = workspace_tmp_dir / "missing.smp"
    imported_dxf = workspace_tmp_dir / "imported.dxf"
    imported_dxf.write_text("0\nEOF\n", encoding="utf-8")

    window.settings_manager.add_recent_file(str(imported_dxf))
    window.settings_manager.add_recent_file(str(missing_project))
    window.settings_manager.add_recent_file(str(valid_project))

    window._refresh_home_recent_projects()

    assert window.settings_manager.get_recent_files() == [str(valid_project.resolve())]
    assert [project["path"] for project in window.home_page._recent_projects] == [
        str(valid_project.resolve())
    ]


def test_home_recent_projects_render_preview_for_legacy_project_without_embedded_thumbnail(
    window,
    workspace_tmp_dir,
):
    legacy_project = _create_project_file(
        workspace_tmp_dir,
        "legacy.smp",
        "Legacy Project",
        contours=[_rect_contour(0, 0, 20, 10, "L"), _rect_contour(30, 5, 45, 25, "G")],
    )

    with zipfile.ZipFile(legacy_project, "r") as zf:
        assert PREVIEW_FILE not in zf.namelist()

    window.settings_manager.add_recent_file(str(legacy_project))
    window._refresh_home_recent_projects()

    project = window.home_page._recent_projects[0]
    assert project["path"] == str(legacy_project.resolve())
    assert project["preview_pixmap"] is not None
    assert window.home_page._cards[0].preview_pixmap is not None


def test_home_recent_projects_fall_back_to_char_when_embedded_thumbnail_is_invalid(
    window,
    workspace_tmp_dir,
):
    broken_preview_project = _create_project_file(
        workspace_tmp_dir,
        "corrupt_preview.smp",
        "Corrupt Preview",
        contours=[_rect_contour(0, 0, 20, 10, "C")],
        preview_png=b"not-a-valid-png",
    )

    window.settings_manager.add_recent_file(str(broken_preview_project))
    window._refresh_home_recent_projects()

    project = window.home_page._recent_projects[0]
    card = window.home_page._cards[0]

    assert project["preview_pixmap"] is None
    assert card.preview_pixmap is None
    assert project["char"] == "C"
    assert card.preview_char == "C"


def test_home_recent_project_card_opens_target_project(window, workspace_tmp_dir, qapp, monkeypatch):
    project_path = _create_project_file(workspace_tmp_dir, "card_target.smp", "Card Target")
    opened_paths = []

    window.settings_manager.add_recent_file(str(project_path))
    window._refresh_home_recent_projects()
    window.show()
    qapp.processEvents()

    monkeypatch.setattr(
        window,
        "_load_project",
        lambda file_path: opened_paths.append(file_path) or True,
    )

    card = window.home_page._cards[0]
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert opened_paths == [str(project_path.resolve())]


def test_home_clear_all_button_clears_recent_projects(window, workspace_tmp_dir, qapp):
    first_project = _create_project_file(workspace_tmp_dir, "first.smp", "First Project")
    second_project = _create_project_file(workspace_tmp_dir, "second.smp", "Second Project")

    window.settings_manager.add_recent_file(str(first_project))
    window.settings_manager.add_recent_file(str(second_project))
    window._refresh_home_recent_projects()
    window.resize(1280, 760)
    window._on_nav_changed("home")
    window.show()
    window.home_page.repaint()
    qapp.processEvents()

    assert len(window.home_page._cards) == 2
    assert not window.home_page._clear_all_rect.isNull()

    QTest.mouseClick(
        window.home_page,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        window.home_page._clear_all_rect.center().toPoint(),
    )
    qapp.processEvents()

    assert window.settings_manager.get_recent_files() == []
    assert window.home_page._recent_projects == []
    assert window.home_page._cards == []


def test_home_recent_project_context_menu_can_remove_single_project(
    window,
    workspace_tmp_dir,
    qapp,
    monkeypatch,
):
    first_project = _create_project_file(workspace_tmp_dir, "first.smp", "First Project")
    second_project = _create_project_file(workspace_tmp_dir, "second.smp", "Second Project")

    window.settings_manager.add_recent_file(str(first_project))
    window.settings_manager.add_recent_file(str(second_project))
    window._refresh_home_recent_projects()
    window._on_nav_changed("home")
    window.show()
    qapp.processEvents()

    first_project_path = str(first_project.resolve())
    second_project_path = str(second_project.resolve())
    card = next(card for card in window.home_page._cards if card.file_path == first_project_path)

    monkeypatch.setattr(
        card,
        "_show_context_menu",
        lambda menu, event: menu.actions()[1],
    )

    card.contextMenuEvent(
        QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse,
            QPoint(20, 20),
            card.mapToGlobal(QPoint(20, 20)),
        )
    )
    qapp.processEvents()

    assert window.settings_manager.get_recent_files() == [second_project_path]
    assert [project["path"] for project in window.home_page._recent_projects] == [second_project_path]


def test_home_recent_project_context_menu_can_open_containing_folder(
    window,
    workspace_tmp_dir,
    qapp,
    monkeypatch,
):
    project_path = _create_project_file(workspace_tmp_dir, "folder_target.smp", "Folder Target")
    opened_folders = []

    window.settings_manager.add_recent_file(str(project_path))
    window._refresh_home_recent_projects()
    window._on_nav_changed("home")
    window.show()
    qapp.processEvents()

    monkeypatch.setattr(
        "src.ui.main_window.QDesktopServices.openUrl",
        lambda url: opened_folders.append(url.toLocalFile()) or True,
    )
    card = window.home_page._cards[0]
    monkeypatch.setattr(
        card,
        "_show_context_menu",
        lambda menu, event: menu.actions()[0],
    )
    card.contextMenuEvent(
        QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse,
            QPoint(20, 20),
            card.mapToGlobal(QPoint(20, 20)),
        )
    )
    qapp.processEvents()

    assert [str(Path(path).resolve()) for path in opened_folders] == [
        str(project_path.resolve().parent)
    ]


def test_home_recent_projects_enable_vertical_scroll_on_small_height(window, workspace_tmp_dir, qapp):
    for index in range(6):
        _create_project_file(
            workspace_tmp_dir,
            f"scroll_{index}.smp",
            f"Scroll Project {index}",
        )
        window.settings_manager.add_recent_file(str(workspace_tmp_dir / f"scroll_{index}.smp"))

    window._refresh_home_recent_projects()
    window.resize(1280, 760)
    window._on_nav_changed("home")
    window.show()
    qapp.processEvents()

    assert window.home_scroll.verticalScrollBar().maximum() > 0
