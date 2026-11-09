"""Keep Windows system runtime DLLs out of the application's root bundle."""

from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
import sys
from typing import Iterable


BinaryEntry = tuple[str, str, str]
_SYSTEM_RUNTIME_NAMES = {"icu.dll", "icuuc.dll", "icuin.dll", "icudt.dll", "ucrtbase.dll"}


def filter_windows_system_runtime_binaries(
    binaries: Iterable[BinaryEntry],
    system_directory: Path | None = None,
    platform: str | None = None,
) -> list[BinaryEntry]:
    """Exclude root OS runtimes accidentally resolved from another app's PATH.

    Qt on supported Windows versions uses the OS ICU with unversioned exports.
    A different program's ICU can have the same DLL name but incompatible
    exports, causing QtWidgets to fail before the application can start.
    Namespaced package libraries are preserved. Concrete OS runtime DLLs are
    excluded only when Windows supplies them; API-set contracts are supplied
    virtually by the OS and need not have physical files in System32.
    """
    entries = list(binaries)
    if (sys.platform if platform is None else platform) != "win32":
        return entries
    if system_directory is None:
        system_directory = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"

    filtered = []
    for entry in entries:
        destination, _source, kind = entry
        path = PureWindowsPath(destination)
        if kind != "BINARY" or path.parent != PureWindowsPath("."):
            filtered.append(entry)
            continue
        name = path.name.lower()
        is_api_set = name.endswith(".dll") and name.startswith(("api-ms-win-", "ext-ms-win-"))
        is_os_runtime = name in _SYSTEM_RUNTIME_NAMES and (system_directory / name).is_file()
        if not is_api_set and not is_os_runtime:
            filtered.append(entry)
    return filtered
