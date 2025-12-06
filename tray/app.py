"""
Main system tray application
"""
import threading
import time
from typing import Optional

import pystray

from .config import STATUS_POLL_INTERVAL
from .api_client import api_client, SystemStatus
from .backend import backend_manager
from .icons import get_app_icon
from .menu import MenuBuilder


class TrayApp:
    """Main system tray application"""

    def __init__(self):
        self._icon: Optional[pystray.Icon] = None
        self._menu_builder: Optional[MenuBuilder] = None
        self._status = SystemStatus()
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None

    def _on_toggle_recording(self):
        """Handle recording toggle"""
        api_client.toggle_recording(self._status.is_recording)
        # Poll immediately to update UI
        self._poll_status()

    def _on_sync(self):
        """Handle sync trigger"""
        api_client.start_sync()
        self._poll_status()

    def _on_set_mode(self, mode: str):
        """Handle mode selection"""
        api_client.set_capture_mode(mode)
        self._poll_status()

    def _on_quit(self):
        """Handle quit"""
        self._running = False
        self.stop()

    def _poll_status(self):
        """Poll API for current status"""
        healthy = api_client.health_check()

        if healthy:
            self._status = api_client.get_status()
            self._status.healthy = True
        else:
            self._status = SystemStatus()
            self._status.healthy = False

        self._update_menu()

    def _update_menu(self):
        """Update menu based on current status"""
        if self._icon is None or self._menu_builder is None:
            return

        # Update menu (icon stays the same)
        self._menu_builder.update_status(self._status)
        self._icon.menu = self._menu_builder.build()

    def _poll_loop(self):
        """Background polling loop"""
        while self._running:
            self._poll_status()
            time.sleep(STATUS_POLL_INTERVAL)

    def start(self):
        """Start the tray application"""
        # Start backend
        print("Starting LiveRecall backend...")
        if not backend_manager.start():
            print("Warning: Backend failed to start, continuing anyway...")

        backend_manager.enable_auto_restart()

        # Create menu builder
        self._menu_builder = MenuBuilder(
            on_toggle_recording=self._on_toggle_recording,
            on_sync=self._on_sync,
            on_set_mode=self._on_set_mode,
            on_quit=self._on_quit,
        )

        # Initial status poll
        self._poll_status()

        # Create tray icon with static app icon
        self._icon = pystray.Icon(
            name="LiveRecall",
            icon=get_app_icon(),
            title="LiveRecall",
            menu=self._menu_builder.build(),
        )

        # Start polling thread
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        # Run tray (blocking)
        print("LiveRecall tray started")
        self._icon.run()

    def stop(self):
        """Stop the tray application"""
        self._running = False

        # Stop icon
        if self._icon:
            self._icon.stop()
            self._icon = None

        # Close API client
        api_client.close()

        # Stop backend
        print("Stopping backend...")
        backend_manager.stop()

        print("LiveRecall stopped")


def run_tray():
    """Entry point for tray application"""
    app = TrayApp()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    run_tray()
