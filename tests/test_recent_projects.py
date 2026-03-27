import os
import shutil
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.business.project_format import save_project
from src.business.settings_manager import SettingsManager
from src.core.types import Project, ProjectMeta
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


def _create_project_file(base_dir: Path, file_name: str, project_name: str) -> Path:
    file_path = base_dir / file_name
    save_project(Project(meta=ProjectMeta(name=project_name)), str(file_path))
    return file_path


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

    window._save_project(str(file_path))

    assert window.settings_manager.get_recent_files()[0] == str(file_path.resolve())
    assert window.home_page._recent_projects[0]["path"] == str(file_path.resolve())
    assert window.home_page._recent_projects[0]["name"] == "saved_from_window"


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
