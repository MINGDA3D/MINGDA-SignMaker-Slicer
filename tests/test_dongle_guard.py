import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.license_guard.build_flags import is_code_dog_enabled
from src.license_guard.constants import BRIDGE_OK, BRIDGE_LIBRARY_NOT_FOUND, SDK_NOT_FOUND_KEY
from src.license_guard.dongle_guard import DongleGuard
from src.license_guard.softkey_bridge import FindPortResult, SoftkeyBridgeError


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class FakeClient:
    def __init__(self, results, *, is_load=True, initialize_code=0):
        self.bridge_path = "fake-bridge.dll"
        self.initialize_code = initialize_code
        self.is_load = is_load
        self._results = list(results)
        self.closed = False

    def find_port(self):
        if self._results:
            return self._results.pop(0)
        return FindPortResult(BRIDGE_OK, r"\\?\hid#device")

    def close(self):
        self.closed = True


def test_code_dog_enable_flag_uses_environment(monkeypatch):
    monkeypatch.setenv("CODE_DOG", "1")
    assert is_code_dog_enabled() is True


def test_initialize_succeeds_when_dongle_present(qapp):
    client = FakeClient([FindPortResult(BRIDGE_OK, r"\\?\hid#device")])
    guard = DongleGuard(qapp, client_factory=lambda: client)

    try:
        assert guard.initialize() is True
        guard.start_monitoring()
        assert guard._timer.isActive() is True
    finally:
        guard.shutdown()
        assert client.closed is True


def test_initialize_shows_message_when_dongle_missing(qapp):
    client = FakeClient([FindPortResult(SDK_NOT_FOUND_KEY, "")])
    guard = DongleGuard(qapp, client_factory=lambda: client)
    messages = []
    guard._show_critical_message = messages.append

    try:
        assert guard.initialize() is False
        assert messages == ["USB dongle not found. Please insert it and try again."]
    finally:
        guard.shutdown()


def test_runtime_recheck_exits_when_dongle_removed(qapp):
    client = FakeClient(
        [
            FindPortResult(BRIDGE_OK, r"\\?\hid#device"),
            FindPortResult(SDK_NOT_FOUND_KEY, ""),
        ]
    )
    guard = DongleGuard(qapp, client_factory=lambda: client, check_interval_ms=1)
    messages = []
    exit_calls = []
    guard._show_critical_message = messages.append
    guard._request_exit = lambda: exit_calls.append(1)

    try:
        assert guard.initialize() is True
        guard.start_monitoring()
        guard._on_timer_timeout()
        assert messages == [
            "USB dongle was removed. The application will now exit.\n"
            "Please reinsert it and try again."
        ]
        assert exit_calls == [1]
    finally:
        guard.shutdown()


def test_initialize_reports_missing_bridge(qapp):
    def _raise():
        raise SoftkeyBridgeError(
            "missing",
            code=BRIDGE_LIBRARY_NOT_FOUND,
        )

    guard = DongleGuard(qapp, client_factory=_raise)
    messages = []
    guard._show_critical_message = messages.append

    try:
        assert guard.initialize() is False
        assert "missing from this build" in messages[0]
    finally:
        guard.shutdown()
