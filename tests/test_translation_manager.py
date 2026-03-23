"""
MINGDA SignMaker - 翻译管理器测试
"""

import uuid
import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from src.i18n.translation_manager import TranslationManager


class FakeSystemLocale:
    """用于模拟系统语言环境。"""

    def __init__(self, name: str, ui_languages: list[str]):
        self._name = name
        self._ui_languages = ui_languages

    def name(self) -> str:
        return self._name

    def uiLanguages(self) -> list[str]:
        return list(self._ui_languages)


class TestTranslationManager:
    @pytest.fixture
    def qapp(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def temp_settings_dir(self):
        base_dir = Path.cwd() / ".tmp_pytest_i18n"
        base_dir.mkdir(parents=True, exist_ok=True)
        tmpdir = base_dir / f"case_{uuid.uuid4().hex}"
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            yield tmpdir
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _patch_settings(self, monkeypatch, settings_dir: Path) -> Path:
        settings_file = settings_dir / "translation_settings.ini"
        monkeypatch.setattr(
            "src.i18n.translation_manager.QSettings",
            lambda *args, **kwargs: QSettings(
                str(settings_file),
                QSettings.Format.IniFormat
            )
        )
        return settings_file

    def test_first_run_uses_supported_system_language(self, qapp, temp_settings_dir, monkeypatch):
        self._patch_settings(monkeypatch, temp_settings_dir)
        monkeypatch.setattr(
            "src.i18n.translation_manager.QLocale.system",
            lambda: FakeSystemLocale("de_DE", ["de-DE", "de"])
        )

        manager = TranslationManager(qapp)

        assert manager.get_current_language() == "de_DE"

    def test_first_run_falls_back_to_supported_language_family(self, qapp, temp_settings_dir, monkeypatch):
        self._patch_settings(monkeypatch, temp_settings_dir)
        monkeypatch.setattr(
            "src.i18n.translation_manager.QLocale.system",
            lambda: FakeSystemLocale("pt_PT", ["pt-PT", "pt"])
        )

        manager = TranslationManager(qapp)

        assert manager.get_current_language() == "pt_BR"

    def test_first_run_falls_back_to_english_when_system_language_unsupported(
        self, qapp, temp_settings_dir, monkeypatch
    ):
        self._patch_settings(monkeypatch, temp_settings_dir)
        monkeypatch.setattr(
            "src.i18n.translation_manager.QLocale.system",
            lambda: FakeSystemLocale("nl_NL", ["nl-NL", "nl"])
        )

        manager = TranslationManager(qapp)

        assert manager.get_current_language() == "en_US"

    def test_saved_language_overrides_system_language(self, qapp, temp_settings_dir, monkeypatch):
        settings_file = self._patch_settings(monkeypatch, temp_settings_dir)
        settings = QSettings(str(settings_file), QSettings.Format.IniFormat)
        settings.setValue("language", "ja_JP")
        settings.sync()

        monkeypatch.setattr(
            "src.i18n.translation_manager.QLocale.system",
            lambda: FakeSystemLocale("de_DE", ["de-DE", "de"])
        )

        manager = TranslationManager(qapp)

        assert manager.get_current_language() == "ja_JP"

    def test_set_language_preference_only_updates_next_start_preference(
        self, qapp, temp_settings_dir, monkeypatch
    ):
        settings_file = self._patch_settings(monkeypatch, temp_settings_dir)
        monkeypatch.setattr(
            "src.i18n.translation_manager.QLocale.system",
            lambda: FakeSystemLocale("de_DE", ["de-DE", "de"])
        )

        manager = TranslationManager(qapp)
        translations_dir = temp_settings_dir / "translations"
        translations_dir.mkdir(parents=True, exist_ok=True)
        (translations_dir / "signmaker_ja_JP.qm").write_bytes(b"qm")
        manager._translations_dir = translations_dir

        changed_languages = []
        manager.language_changed.connect(changed_languages.append)

        assert manager.set_language_preference("ja_JP") is True
        assert manager.get_current_language() == "de_DE"
        assert changed_languages == []

        settings = QSettings(str(settings_file), QSettings.Format.IniFormat)
        assert settings.value("language", "", type=str) == "ja_JP"

    def test_set_language_preference_rejects_missing_translation(
        self, qapp, temp_settings_dir, monkeypatch
    ):
        settings_file = self._patch_settings(monkeypatch, temp_settings_dir)
        monkeypatch.setattr(
            "src.i18n.translation_manager.QLocale.system",
            lambda: FakeSystemLocale("en_US", ["en-US", "en"])
        )

        manager = TranslationManager(qapp)
        translations_dir = temp_settings_dir / "translations"
        translations_dir.mkdir(parents=True, exist_ok=True)
        manager._translations_dir = translations_dir

        assert manager.set_language_preference("fr_FR") is False

        settings = QSettings(str(settings_file), QSettings.Format.IniFormat)
        assert settings.value("language", "", type=str) == ""
