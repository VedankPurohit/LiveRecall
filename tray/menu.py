"""
Menu construction for system tray
"""

from __future__ import annotations

import sys
import webbrowser
from collections.abc import Callable
from typing import Any

from pystray import Menu
from pystray import MenuItem as Item

from core.platform import current_platform

from .api_client import SystemStatus
from .config import CAPTURE_MODES, WEB_UI_URL

# Windows has issues with default=True on menu items
IS_WINDOWS = sys.platform == "win32"


def open_data_folder():
    """Open the data folder in file explorer"""
    data_dir = current_platform.get_data_dir()
    current_platform.open_folder(data_dir)


def open_web_search():
    """Open web UI search page"""
    webbrowser.open(f"{WEB_UI_URL}?view=search")


def open_web_timeline():
    """Open web UI timeline page"""
    webbrowser.open(WEB_UI_URL)


INCOGNITO_DURATIONS = [
    (0, "Off"),
    (5, "5 minutes"),
    (15, "15 minutes"),
    (30, "30 minutes"),
    (60, "1 hour"),
]


def format_remaining_time(seconds: int) -> str:
    """Format remaining seconds as MM:SS"""
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


class MenuBuilder:
    """Builds and updates the system tray menu"""

    def __init__(
        self,
        on_toggle_recording: Callable,
        on_sync: Callable,
        on_set_mode: Callable[[str], None],
        on_set_incognito: Callable[[int], None],
        on_quit: Callable,
        on_download_update: Callable = None,
    ):
        self.on_toggle_recording = on_toggle_recording
        self.on_sync = on_sync
        self.on_set_mode = on_set_mode
        self.on_set_incognito = on_set_incognito
        self.on_quit = on_quit
        self.on_download_update = on_download_update

        # Current state
        self._status = SystemStatus()
        self._update_info: dict[str, Any] | None = None

    def update_status(self, status: SystemStatus, update_info: dict[str, Any] | None = None):
        """Update internal status"""
        self._status = status
        if update_info is not None:
            self._update_info = update_info

    def _make_mode_handler(self, mode: str):
        """Create a handler for mode selection"""

        def handler():
            self.on_set_mode(mode)

        return handler

    def _is_mode_checked(self, mode: str):
        """Check if mode is currently selected"""

        def check(item):
            return self._status.recording_mode == mode

        return check

    def _make_incognito_handler(self, duration: int):
        """Create a handler for incognito duration selection"""

        def handler():
            self.on_set_incognito(duration)

        return handler

    def _is_incognito_checked(self, duration: int):
        """Check if incognito duration is currently active"""

        def check(item):
            if duration == 0:
                return not self._status.incognito_active
            # For non-zero durations, check if incognito is active
            # (we can't easily know which duration was selected, so just show active state)
            return self._status.incognito_active and duration > 0

        return check

    def build(self) -> Menu:
        """Build the menu structure"""
        status = self._status

        # Recording button: "Start" (green) when not recording, "Stop" (red) when recording
        # Note: pystray doesn't support colored text, but we use clear labels
        # On Windows, avoid Unicode symbols that may not render correctly
        if IS_WINDOWS:
            recording_text = "Stop Recording" if status.is_recording else "Start Recording"
        else:
            recording_text = "■ Stop Recording" if status.is_recording else "▶ Start Recording"

        # Sync text with count
        if status.is_syncing:
            sync_text = f"Syncing... ({status.sync_progress}/{status.sync_total})"
        elif status.unsynced > 0:
            sync_text = f"Sync ({status.unsynced} pending)"
        else:
            sync_text = "Sync (up to date)"

        # Stats
        snapshots_text = f"{status.total_screenshots:,} snapshots"
        model_text = f"Model: {status.model_device or 'unloaded'}"

        # Mode submenu
        mode_items = [
            Item(mode, self._make_mode_handler(mode), checked=self._is_mode_checked(mode), radio=True)
            for mode in CAPTURE_MODES
        ]

        # Incognito submenu
        incognito_items = [
            Item(
                label, self._make_incognito_handler(duration), checked=self._is_incognito_checked(duration), radio=True
            )
            for duration, label in INCOGNITO_DURATIONS
        ]

        # Incognito menu label with remaining time if active
        # Note: Icon badge shows incognito state, no emoji needed in label
        if status.incognito_active:
            incognito_label = f"Incognito ({format_remaining_time(status.incognito_remaining_seconds)})"
        else:
            incognito_label = "Incognito Mode"

        # Build menu items
        # Note: default=True causes issues on Windows, so we only use it on macOS
        items = [
            Item(recording_text, self.on_toggle_recording, default=not IS_WINDOWS),
            Item(incognito_label, Menu(*incognito_items)),
            Menu.SEPARATOR,
            Item(f"Mode: {status.recording_mode}", Menu(*mode_items)),
            Menu.SEPARATOR,
            Item(sync_text, self.on_sync, enabled=not status.is_syncing),
            Menu.SEPARATOR,
            Item(snapshots_text, None, enabled=False),
            Item(model_text, None, enabled=False),
            Menu.SEPARATOR,
            Item("Search...", open_web_search),
            Item("Open Timeline", open_web_timeline),
            Item("Open Data Folder", open_data_folder),
        ]

        # Add update notification if available
        if self._update_info and self.on_download_update:
            items.append(Menu.SEPARATOR)
            items.append(Item(f"Update Available: v{self._update_info['latest_version']}", self.on_download_update))

        items.append(Menu.SEPARATOR)
        items.append(Item("Quit", self.on_quit))

        return Menu(*items)
