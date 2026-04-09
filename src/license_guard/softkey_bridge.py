"""ctypes wrapper around the native SoftkeyYT88 bridge."""

from __future__ import annotations

import ctypes
import locale
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .build_flags import bridge_candidates
from .constants import (
    BRIDGE_LIBRARY_NOT_FOUND,
    DEVICE_PATH_BUFFER_SIZE,
)


@dataclass(frozen=True)
class FindPortResult:
    """Result of a dongle presence probe."""

    code: int
    device_path: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 0


class SoftkeyBridgeError(RuntimeError):
    """Raised when the native bridge cannot be loaded."""

    def __init__(self, message: str, *, code: int, bridge_path: Path | None = None):
        super().__init__(message)
        self.code = code
        self.bridge_path = bridge_path


class NativeSoftkeyClient:
    """Thin client for the native SoftkeyYT88 bridge DLL."""

    def __init__(self, bridge_path: Path | None = None):
        if sys.platform != "win32":
            raise SoftkeyBridgeError(
                "SoftkeyYT88 bridge is only supported on Windows.",
                code=BRIDGE_LIBRARY_NOT_FOUND,
                bridge_path=bridge_path,
            )

        self._dll_directory = None
        self._bridge, self.bridge_path = self._load_bridge(bridge_path)
        self._configure_prototypes()
        self.initialize_code = self._bridge.DongleBridge_Initialize()

    @property
    def is_load(self) -> bool:
        """Return whether the underlying SDK loaded its dependencies."""
        return bool(self._bridge.DongleBridge_IsLoad())

    def find_port(self) -> FindPortResult:
        """Probe whether a dongle is present and return the device path."""
        buffer = ctypes.create_string_buffer(DEVICE_PATH_BUFFER_SIZE)
        code = self._bridge.DongleBridge_FindPort(buffer, len(buffer))
        return FindPortResult(code=code, device_path=_decode_device_path(buffer.value))

    def close(self) -> None:
        """Release the native singleton."""
        if getattr(self, "_bridge", None) is not None:
            self._bridge.DongleBridge_Destroy()

    def _load_bridge(self, bridge_path: Path | None) -> tuple[ctypes.WinDLL, Path]:
        candidates = [bridge_path] if bridge_path is not None else bridge_candidates()
        last_error: OSError | None = None

        for candidate in candidates:
            if candidate is None:
                continue
            candidate = Path(candidate)
            if not candidate.exists():
                continue

            try:
                if hasattr(os, "add_dll_directory"):
                    self._dll_directory = os.add_dll_directory(str(candidate.parent))
                return ctypes.WinDLL(str(candidate)), candidate
            except OSError as exc:
                last_error = exc

        if last_error is not None:
            raise SoftkeyBridgeError(
                f"Failed to load bridge library: {last_error}",
                code=BRIDGE_LIBRARY_NOT_FOUND,
                bridge_path=None,
            ) from last_error

        raise SoftkeyBridgeError(
            "Bridge library not found.",
            code=BRIDGE_LIBRARY_NOT_FOUND,
            bridge_path=None,
        )

    def _configure_prototypes(self) -> None:
        self._bridge.DongleBridge_Initialize.argtypes = []
        self._bridge.DongleBridge_Initialize.restype = ctypes.c_int
        self._bridge.DongleBridge_IsLoad.argtypes = []
        self._bridge.DongleBridge_IsLoad.restype = ctypes.c_int
        self._bridge.DongleBridge_FindPort.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._bridge.DongleBridge_FindPort.restype = ctypes.c_int
        self._bridge.DongleBridge_Destroy.argtypes = []
        self._bridge.DongleBridge_Destroy.restype = None


def _decode_device_path(raw: bytes) -> str:
    if not raw:
        return ""

    encodings: list[str] = []
    if sys.platform == "win32":
        encodings.append("mbcs")
    preferred = locale.getpreferredencoding(False)
    if preferred:
        encodings.append(preferred)
    encodings.extend(["utf-8", "latin-1"])

    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="ignore")
