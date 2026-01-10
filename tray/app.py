"""
Main system tray application
"""

import contextlib
import sys
import threading
import time
import webbrowser

import pystray

from core.updater import VERSION, check_for_updates_async

from .api_client import SystemStatus, api_client
from .backend import backend_manager
from .config import STATUS_POLL_INTERVAL, WEB_UI_URL
from .icons import get_app_icon
from .menu import MenuBuilder

IS_WINDOWS = sys.platform == "win32"


class TrayApp:
    """Main system tray application"""

    def __init__(self):
        self._icon: pystray.Icon | None = None
        self._menu_builder: MenuBuilder | None = None
        self._status = SystemStatus()
        self._running = False
        self._poll_thread: threading.Thread | None = None
        self._update_info: dict | None = None

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

    def _on_set_incognito(self, duration_minutes: int):
        """Handle incognito mode toggle"""
        if duration_minutes == 0:
            api_client.stop_incognito_mode()
        else:
            api_client.set_incognito_mode(duration_minutes)
        self._poll_status()

    def _on_quit(self):
        """Handle quit"""
        self._running = False
        self.stop()

    def _on_update_available(self, update_info: dict | None):
        """Callback when update check completes"""
        if update_info:
            self._update_info = update_info
            print(f"Update available: v{update_info['latest_version']}")
            # Update menu to show update option
            self._update_menu()

    def _on_download_update(self):
        """Open browser to download update"""
        if self._update_info:
            webbrowser.open(self._update_info["release_url"])

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
        """Update menu and icon based on current status"""
        if self._icon is None or self._menu_builder is None:
            return

        # Update menu
        self._menu_builder.update_status(self._status, self._update_info)
        self._icon.menu = self._menu_builder.build()

        # On Windows, we need to explicitly call update_menu() to refresh
        if IS_WINDOWS and hasattr(self._icon, "update_menu"):
            with contextlib.suppress(Exception):
                self._icon.update_menu()

    def _poll_loop(self):
        """
        Continuously poll the backend status while the tray app is running.
        
        Repeatedly calls the instance's status poll routine and then waits STATUS_POLL_INTERVAL seconds between iterations. The loop stops when the app's running flag is cleared.
        """
        while self._running:
            self._poll_status()
            time.sleep(STATUS_POLL_INTERVAL)

    def _check_and_open_setup(self):
        """Check if setup is needed and open setup page"""
        try:
            # Wait a moment for backend to be ready
            time.sleep(1)

            # Check setup status via API
            status = api_client.get_json("/setup/status")

            if status and status.get("needs_setup", False):
                last_version = status.get("last_seen_version", "none")
                current_version = status.get("current_version", "unknown")
                print(f"Version change detected: {last_version} -> {current_version}")
                print("Opening setup page...")
                webbrowser.open(f"{WEB_UI_URL}/setup")
        except Exception as e:
            print(f"Warning: Could not check setup status: {e}")

    def start(self):
        """Start the tray application"""
        # Start backend
        print("Starting LiveRecall backend...")
        if not backend_manager.start():
            print("Warning: Backend failed to start, continuing anyway...")

        backend_manager.enable_auto_restart()

        # Check if setup is needed (version change or first run)
        self._check_and_open_setup()

        # Create menu builder
        self._menu_builder = MenuBuilder(
            on_toggle_recording=self._on_toggle_recording,
            on_sync=self._on_sync,
            on_set_mode=self._on_set_mode,
            on_set_incognito=self._on_set_incognito,
            on_quit=self._on_quit,
            on_download_update=self._on_download_update,
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

        # Check for updates in background
        check_for_updates_async(self._on_update_available)

        # Run tray (blocking)
        print(f"LiveRecall v{VERSION} tray started")
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