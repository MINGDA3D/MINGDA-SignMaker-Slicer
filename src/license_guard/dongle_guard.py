"""Application-level USB dongle guard."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from src.app_info import APP_NAME

from .constants import (
    BRIDGE_INVALID_ARGUMENT,
    BRIDGE_LIBRARY_NOT_FOUND,
    BRIDGE_LOAD_FAILED,
    BRIDGE_NOT_INITIALIZED,
    DEFAULT_CHECK_INTERVAL_MS,
    SDK_ERR_GET_DATA,
    SDK_ERR_SEND_DATA,
    SDK_NOT_FOUND_KEY,
)
from .softkey_bridge import NativeSoftkeyClient, SoftkeyBridgeError


class DongleGuard(QObject):
    """Startup and runtime presence guard for the USB dongle."""

    def __init__(
        self,
        app: QApplication,
        *,
        client_factory: Callable[[], NativeSoftkeyClient] | None = None,
        check_interval_ms: int = DEFAULT_CHECK_INTERVAL_MS,
    ) -> None:
        super().__init__(app)
        self._app = app
        self._client_factory = client_factory or NativeSoftkeyClient
        self._client: Optional[NativeSoftkeyClient] = None
        self._window: Optional[QWidget] = None
        self._failure_handled = False
        self._timer = QTimer(self)
        self._timer.setInterval(check_interval_ms)
        self._timer.timeout.connect(self._on_timer_timeout)
        self._app.aboutToQuit.connect(self.shutdown)

    def initialize(self) -> bool:
        """Create the native client and perform the startup presence check."""
        try:
            self._client = self._client_factory()
        except SoftkeyBridgeError as exc:
            self._log(f"failed to create bridge client: {exc}")
            return self._handle_startup_failure(self._message_for_bridge_error(exc.code))

        self._log(f"bridge initialized: {self._client.bridge_path}")
        if self._client.initialize_code != 0 or not self._client.is_load:
            self._log(f"SDK load failed: initialize_code={self._client.initialize_code}")
            return self._handle_startup_failure(self._message_for_sdk_load_failure())

        return self._check_presence(startup=True)

    def attach_window(self, window: QWidget) -> None:
        """Attach the main window for modal dialogs."""
        self._window = window

    def start_monitoring(self) -> None:
        """Begin periodic presence checks."""
        if self._client is None or self._failure_handled:
            return
        if not self._timer.isActive():
            self._log(f"starting timer: interval_ms={self._timer.interval()}")
            self._timer.start()

    def shutdown(self) -> None:
        """Stop monitoring and release native resources."""
        if self._timer.isActive():
            self._timer.stop()
        if self._client is not None:
            self._client.close()
            self._client = None

    def _on_timer_timeout(self) -> None:
        self._check_presence(startup=False)

    def _check_presence(self, *, startup: bool) -> bool:
        if self._client is None:
            return self._handle_failure(
                self._message_for_bridge_error(BRIDGE_NOT_INITIALIZED),
                startup=startup,
            )

        result = self._client.find_port()
        if result.ok:
            self._log(f"FindPort succeeded: {result.device_path or '<empty>'}")
            return True

        self._log(f"FindPort failed: code={result.code}")
        return self._handle_failure(
            self._message_for_find_port_failure(result.code, startup=startup),
            startup=startup,
        )

    def _handle_startup_failure(self, message: str) -> bool:
        return self._handle_failure(message, startup=True)

    def _handle_failure(self, message: str, *, startup: bool) -> bool:
        if self._failure_handled:
            return False

        self._failure_handled = True
        self.shutdown()
        self._show_critical_message(message)

        if not startup:
            self._request_exit()
        return False

    def _show_critical_message(self, message: str) -> None:
        QMessageBox.critical(self._dialog_parent(), APP_NAME, message)

    def _request_exit(self) -> None:
        self._app.exit(1)

    def _dialog_parent(self) -> QWidget | None:
        if self._window is not None:
            return self._window
        active_window = self._app.activeWindow()
        return active_window if isinstance(active_window, QWidget) else None

    def _message_for_sdk_load_failure(self) -> str:
        return (
            self.tr(
                "Failed to load USB dongle runtime library. The application cannot start.\n"
                "Please verify the system environment or rebuild the dongle module and try again."
            )
        )

    def _message_for_bridge_error(self, code: int) -> str:
        if code == BRIDGE_LIBRARY_NOT_FOUND:
            return (
                self.tr(
                    "USB dongle validation module is missing from this build. The application cannot start.\n"
                    "Please rebuild with CODE_DOG=1 and include native/softkey_bridge.dll."
                )
            )
        if code == BRIDGE_INVALID_ARGUMENT:
            return self.tr(
                "USB dongle validation module received invalid arguments. The application cannot start."
            )
        if code in (BRIDGE_LOAD_FAILED, BRIDGE_NOT_INITIALIZED):
            return self._message_for_sdk_load_failure()
        return self.tr("USB dongle validation module initialization failed. Error code: {code}").format(
            code=code
        )

    def _message_for_find_port_failure(self, code: int, *, startup: bool) -> str:
        if code == SDK_NOT_FOUND_KEY:
            if startup:
                return self.tr("USB dongle not found. Please insert it and try again.")
            return self.tr(
                "USB dongle was removed. The application will now exit.\n"
                "Please reinsert it and try again."
            )

        if code in (SDK_ERR_SEND_DATA, SDK_ERR_GET_DATA):
            if startup:
                return self.tr(
                    "USB dongle communication failed. Please check the connection and try again.\n"
                    "Error code: {code}"
                ).format(code=code)
            return self.tr(
                "USB dongle communication error detected. The application will now exit.\n"
                "Error code: {code}"
            ).format(code=code)

        return self.tr("USB dongle validation failed. Error code: {code}").format(code=code)

    def _log(self, message: str) -> None:
        print(f"[dongle] {message}")
