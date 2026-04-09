"""Build helper for the native SoftkeyYT88 bridge."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.license_guard.build_flags import is_truthy
from src.license_guard.constants import (
    CODE_DOG_ENV_VAR,
    CODE_DOG_MARKER_NAME,
    NATIVE_DIR_NAME,
    RUNTIME_DIR_NAME,
    SOFTKEY_BRIDGE_NAME,
)

BRIDGE_SOURCE = PROJECT_ROOT / "native" / "softkey_bridge" / "softkey_bridge.cpp"
SDK_SOURCE = PROJECT_ROOT / "SoftkeyYT88" / "windows" / "SoftkeyYT88.cpp"
SDK_INCLUDE_DIR = PROJECT_ROOT / "SoftkeyYT88" / "windows"
BUILD_NATIVE_DIR = PROJECT_ROOT / "build" / NATIVE_DIR_NAME
BUILD_RUNTIME_DIR = PROJECT_ROOT / "build" / RUNTIME_DIR_NAME
BRIDGE_OUTPUT = BUILD_NATIVE_DIR / SOFTKEY_BRIDGE_NAME
MARKER_OUTPUT = BUILD_RUNTIME_DIR / CODE_DOG_MARKER_NAME


@dataclass(frozen=True)
class CodeDogBuildArtifacts:
    enabled: bool
    bridge_dll: Path | None = None
    marker_file: Path | None = None


def collect_code_dog_artifacts(project_root: Path | None = None) -> CodeDogBuildArtifacts:
    """Build and return CODE_DOG artifacts when enabled."""
    del project_root  # compatibility for spec callers

    if not is_truthy(os.environ.get(CODE_DOG_ENV_VAR)):
        return CodeDogBuildArtifacts(enabled=False)

    if sys.platform != "win32":
        raise RuntimeError("CODE_DOG is currently only supported on Windows builds.")

    _build_bridge()
    _write_marker()
    return CodeDogBuildArtifacts(
        enabled=True,
        bridge_dll=BRIDGE_OUTPUT,
        marker_file=MARKER_OUTPUT,
    )


def _build_bridge() -> None:
    BUILD_NATIVE_DIR.mkdir(parents=True, exist_ok=True)
    vcvars64 = _find_vcvars64()
    compile_command = (
        f"call \"{vcvars64}\" >nul && "
        "cl /nologo /O2 /EHsc /MT /LD /D_CRT_SECURE_NO_WARNINGS "
        f"/I \"{SDK_INCLUDE_DIR}\" "
        f"\"{BRIDGE_SOURCE}\" "
        f"\"{SDK_SOURCE}\" "
        f"/Fe:\"{BRIDGE_OUTPUT}\" "
        "/link user32.lib /INCREMENTAL:NO /OPT:REF /OPT:ICF"
    )
    subprocess.run(
        compile_command,
        cwd=PROJECT_ROOT,
        check=True,
        shell=True,
    )


def _write_marker() -> None:
    BUILD_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    MARKER_OUTPUT.write_text("CODE_DOG=1\n", encoding="utf-8")


def _find_vcvars64() -> Path:
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not vswhere.exists():
        raise RuntimeError("vswhere.exe not found. Install Visual Studio Build Tools.")

    result = subprocess.run(
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    install_path = result.stdout.strip()
    if not install_path:
        raise RuntimeError("Unable to locate a Visual C++ toolchain.")

    vcvars64 = Path(install_path) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    if not vcvars64.exists():
        raise RuntimeError(f"vcvars64.bat not found: {vcvars64}")
    return vcvars64


def main() -> int:
    artifacts = collect_code_dog_artifacts()
    if not artifacts.enabled:
        print("CODE_DOG is disabled; bridge build skipped.")
        return 0

    print(f"Built bridge: {artifacts.bridge_dll}")
    print(f"Wrote marker: {artifacts.marker_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
