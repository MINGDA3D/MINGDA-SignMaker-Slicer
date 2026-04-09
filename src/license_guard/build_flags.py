"""Runtime helpers for CODE_DOG enablement and bridge discovery."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .constants import (
    CODE_DOG_ENV_VAR,
    CODE_DOG_MARKER_NAME,
    NATIVE_DIR_NAME,
    RUNTIME_DIR_NAME,
    SOFTKEY_BRIDGE_NAME,
    SOFTKEY_BRIDGE_PATH_ENV_VAR,
    TRUTHY_VALUES,
)


def project_root() -> Path:
    """Return the repository root in source mode."""
    return Path(__file__).resolve().parents[2]


def is_truthy(value: str | None) -> bool:
    """Return whether an environment-style flag is enabled."""
    if value is None:
        return False
    return value.strip().lower() in TRUTHY_VALUES


def is_code_dog_enabled() -> bool:
    """Return whether the dongle guard should be active."""
    if is_truthy(os.environ.get(CODE_DOG_ENV_VAR)):
        return True
    return any(path.exists() for path in marker_candidates())


def marker_candidates() -> list[Path]:
    """Return candidate enablement marker paths."""
    return _dedupe_paths(
        root / RUNTIME_DIR_NAME / CODE_DOG_MARKER_NAME
        for root in resource_root_candidates()
    )


def bridge_candidates() -> list[Path]:
    """Return candidate locations for the native bridge DLL."""
    env_path = os.environ.get(SOFTKEY_BRIDGE_PATH_ENV_VAR, "").strip()
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))

    for root in resource_root_candidates():
        candidates.append(root / NATIVE_DIR_NAME / SOFTKEY_BRIDGE_NAME)

    repo_root = project_root()
    candidates.extend(
        [
            repo_root / "build" / NATIVE_DIR_NAME / SOFTKEY_BRIDGE_NAME,
            repo_root / "dist" / "SignMaker" / NATIVE_DIR_NAME / SOFTKEY_BRIDGE_NAME,
        ]
    )
    return _dedupe_paths(candidates)


def resource_root_candidates() -> list[Path]:
    """Return roots where runtime artifacts may be located."""
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(Path(meipass))
        candidates.append(Path(sys.executable).resolve().parent)
    else:
        repo_root = project_root()
        candidates.extend([repo_root, repo_root / "build"])

    return _dedupe_paths(candidates)


def _dedupe_paths(paths) -> list[Path]:
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        resolved = Path(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped
