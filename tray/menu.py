"""
Menu construction for system tray
"""

from __future__ import annotations

import subprocess
import webbrowser
from collections.abc import Callable
from typing import Any

from pystray import Menu
from pystray import MenuItem as Item

from .api_client import SystemStatus
from .config import CAPTURE_MODES, PLATFORM, WEB_UI_URL


def open_data_folder():
    """Open the data folder in file explorer"""
    from core.config import get_data_dir

    data_dir = get_data_dir()

    if PLATFORM == "macos":
        subprocess.run(["open", str(data_dir)])
    elif PLATFORM == "windows":
        subprocess.run(["explorer", str(data_dir)])
    else:  # linux
        subprocess.run(["xdg-open", str(data_dir)])


def open_web_search():
    """Open web UI search page"""
    webbrowser.open(f"{WEB_UI_URL}?view=search")


def open_web_timeline():
    """Open web UI timeline page"""
    webbrowser.open(WEB_UI_URL)


class MenuBuilder:
    """Builds and updates the system tray menu"""

    def __init__(
        self,
        on_toggle_recording: Callable,
        on_sync: Callable,
        on_set_mode: Callable[[str], None],
        on_quit: Callable,
        on_download_update: Callable = None,
    ):
        self.on_toggle_recording = on_toggle_recording
        self.on_sync = on_sync
        self.on_set_mode = on_set_mode
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

    def build(self) -> Menu:
        """Build the menu structure"""
        status = self._status

        # Recording button: "Start" (green) when not recording, "Stop" (red) when recording
        # Note: pystray doesn't support colored text, but we use clear labels
        recording_text = "■ Stop Recording" if status.is_recording else "▶ Start Recording"

        # Sync text with count
        if status.is_syncing:
            sync_text = f"↻ Syncing... ({status.sync_progress}/{status.sync_total})"
        elif status.unsynced > 0:
            sync_text = f"↻ Sync ({status.unsynced} pending)"
        else:
            sync_text = "↻ Sync (up to date)"

        # Stats
        snapshots_text = f"{status.total_screenshots:,} snapshots"
        model_text = f"Model: {status.model_device or 'unloaded'}"

        # Mode submenu
        mode_items = [
            Item(mode, self._make_mode_handler(mode), checked=self._is_mode_checked(mode), radio=True)
            for mode in CAPTURE_MODES
        ]

        # Build menu items
        items = [
            Item(recording_text, self.on_toggle_recording, default=True),
            Menu.SEPARATOR,
            Item(f"Mode: {status.recording_mode}", Menu(*mode_items)),
            Menu.SEPARATOR,
            Item(sync_text, self.on_sync, enabled=not status.is_syncing),
            Menu.SEPARATOR,
            Item(snapshots_text, None, enabled=False),
            Item(model_text, None, enabled=False),
            Menu.SEPARATOR,
            Item("Search...", lambda: open_web_search()),
            Item("Open Timeline", lambda: open_web_timeline()),
            Item("Open Data Folder", lambda: open_data_folder()),
        ]

        # Add update notification if available
        if self._update_info and self.on_download_update:
            items.append(Menu.SEPARATOR)
            items.append(Item(f"Update Available: v{self._update_info['latest_version']}", self.on_download_update))

        items.append(Menu.SEPARATOR)
        items.append(Item("Quit", self.on_quit))

        return Menu(*items)
