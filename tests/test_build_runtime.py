"""Packaging must not let unrelated applications replace Windows' ICU ABI."""

from pathlib import Path

from tools.build_runtime import filter_windows_system_runtime_binaries


def test_foreign_root_icu_and_api_sets_are_excluded_when_os_icu_exists(tmp_path: Path) -> None:
    """An unrelated ICU has versioned exports that cannot satisfy Qt6Core."""
    (tmp_path / "icuuc.dll").touch()
    (tmp_path / "ucrtbase.dll").touch()
    binaries = [
        ("icuuc.dll", "unrelated-app/icuuc.dll", "BINARY"),
        ("ucrtbase.dll", "unrelated-app/ucrtbase.dll", "BINARY"),
        ("api-ms-win-core-synch-l1-2-0.dll", "unrelated-app/api.dll", "BINARY"),
        ("ext-ms-win-ntuser-window-l1-1-0.dll", "unrelated-app/ext.dll", "BINARY"),
        ("VCRUNTIME140.dll", "python/VCRUNTIME140.dll", "BINARY"),
    ]
    assert filter_windows_system_runtime_binaries(binaries, tmp_path, "win32") == [binaries[-1]]


def test_namespaced_package_runtimes_and_non_binaries_are_preserved(tmp_path: Path) -> None:
    """Only root search-path collisions are filtered; package-specific DLLs survive."""
    (tmp_path / "icuuc.dll").touch()
    binaries = [
        (r"package\icuuc.dll", "package/icuuc.dll", "BINARY"),
        ("package/icuuc.dll", "package/icuuc.dll", "BINARY"),
        (r"PySide6\Qt6Core.dll", "PySide6/Qt6Core.dll", "BINARY"),
        ("icuuc.dll", "fixtures/icuuc.dll", "DATA"),
    ]
    assert filter_windows_system_runtime_binaries(binaries, tmp_path, "win32") == binaries


def test_concrete_runtime_is_retained_when_system_does_not_supply_it(tmp_path: Path) -> None:
    binaries = [("icuuc.dll", "package/icuuc.dll", "BINARY")]
    assert filter_windows_system_runtime_binaries(binaries, tmp_path, "win32") == binaries


def test_non_windows_build_is_unchanged(tmp_path: Path) -> None:
    (tmp_path / "icuuc.dll").touch()
    binaries = [("icuuc.dll", "package/icuuc.dll", "BINARY")]
    assert filter_windows_system_runtime_binaries(binaries, tmp_path, "linux") == binaries
