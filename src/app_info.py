"""Application metadata helpers."""

from __future__ import annotations

import os
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path

APP_NAME = "MINGDA SignMaker"
VERSION_ENV_VAR = "MINGDA_SIGNMAKER_VERSION"
DEFAULT_VERSION = "0.0.0"
VERSION_FILE_NAME = "VERSION"
DISTRIBUTION_NAMES = (
    "mingda-signmaker",
    "signmaker-slicer",
    "MINGDA SignMaker",
)


def _candidate_version_files() -> tuple[Path, ...]:
    module_root = Path(__file__).resolve().parent
    return (
        module_root.parent / VERSION_FILE_NAME,
        module_root / VERSION_FILE_NAME,
    )


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """Return the application version from the best available source."""
    env_version = os.environ.get(VERSION_ENV_VAR, "").strip()
    if env_version:
        return env_version

    for dist_name in DISTRIBUTION_NAMES:
        try:
            installed_version = metadata_version(dist_name).strip()
        except PackageNotFoundError:
            continue
        if installed_version:
            return installed_version

    for version_file in _candidate_version_files():
        try:
            file_version = version_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if file_version:
            return file_version

    return DEFAULT_VERSION
