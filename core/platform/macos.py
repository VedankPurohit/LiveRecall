"""
macOS platform implementation.

Handles macOS-specific operations including:
- Data storage in ~/Library/Application Support
- Screen recording permission via TCC
- Auto-start via Login Items (stub for now)
- Menu bar icon sizing (22x22)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Literal

from .base import APP_BUNDLE_ID, APP_NAME, PlatformBase, get_executable_path

logger = logging.getLogger(__name__)


class MacOSPlatform(PlatformBase):
    """macOS-specific platform implementation."""

    @property
    def name(self) -> Literal["macos", "windows", "linux"]:
        """
        Platform identifier for this implementation.
        
        Returns:
            str: The literal "macos".
        """
        return "macos"

    # -------------------------------------------------------------------------
    # Path Methods
    # -------------------------------------------------------------------------

    def get_data_dir(self) -> Path:
        """
        Return the macOS application data directory, creating it if missing.
        
        Returns:
            Path: Path to the application's data directory at ~/Library/Application Support/<APP_NAME>.
        """
        data_dir = Path.home() / "Library" / "Application Support" / APP_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    # -------------------------------------------------------------------------
    # System Operations
    # -------------------------------------------------------------------------

    def open_folder(self, path: Path) -> None:
        """
        Open the given folder in macOS Finder.
        
        Attempts to launch Finder for the provided path. On failure the error is logged and no exception is propagated.
        
        Parameters:
            path (Path): Filesystem path to the folder to open.
        """
        try:
            subprocess.run(["open", str(path)], check=False)
        except Exception as e:
            logger.error(f"Failed to open folder {path}: {e}")

    # -------------------------------------------------------------------------
    # Screen Recording Permissions
    # -------------------------------------------------------------------------

    def needs_screen_permission(self) -> bool:
        """
        Indicates that macOS requires explicit screen recording permission.
        
        Returns:
            True if the platform requires screen recording permission, False otherwise.
        """
        return True

    def check_screen_permission(self) -> bool:
        """
        Report whether screen recording permission is considered granted.
        
        Because macOS does not provide a reliable programmatic check without attempting capture, this method assumes permission is granted.
        
        Returns:
            bool: `True` indicating permission is assumed to be granted; actual denial may only be detected when performing a screen capture.
        """
        # TODO: Could potentially check TCC database or attempt a test capture
        return True

    def request_screen_permission(self) -> bool:
        """Request screen recording permission.

        On macOS, the system automatically prompts for permission when
        the app first attempts to capture the screen. This method is
        essentially a no-op as the OS handles the prompt.

        Returns:
            True - the request flow is handled by the OS.
        """
        # On macOS, permission is requested automatically when screen
        # capture is first attempted via mss
        return True

    def reset_screen_permission(self) -> tuple[bool, str]:
        """
        Reset the app's screen recording permission using tccutil.
        
        Runs `tccutil reset ScreenCapture <APP_BUNDLE_ID>` to clear macOS screen-capture permissions for the application. On success returns a message instructing the user to grant permission when prompted; on failure returns a descriptive error message (e.g., command failure, timeout, or missing `tccutil`).
        
        Returns:
            (success, message): `True` and a success message if the reset succeeded; `False` and a human-readable error message otherwise.
        """
        try:
            result = subprocess.run(
                ["tccutil", "reset", "ScreenCapture", APP_BUNDLE_ID],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                logger.warning(f"tccutil reset failed: {error_msg}")
                return False, f"Permission reset failed: {error_msg}"

            return True, "Screen capture permissions reset. Please grant permission when prompted."

        except subprocess.TimeoutExpired:
            logger.error("tccutil reset timed out")
            return False, "Permission reset timed out. Please try again."
        except FileNotFoundError:
            logger.error("tccutil not found")
            return False, "tccutil command not found. Are you running on macOS?"
        except Exception as e:
            logger.error(f"Permission reset error: {e}")
            return False, f"Permission reset error: {e}"

    # -------------------------------------------------------------------------
    # Auto-start on Login
    # -------------------------------------------------------------------------

    def is_autostart_enabled(self) -> bool:
        """
        Report whether the application is configured to automatically start at macOS login.
        
        Currently unimplemented on macOS; this stub always returns False.
        
        Returns:
            True if auto-start is enabled, False otherwise.
        """
        # TODO: Check Login Items via SMAppService or LaunchAgent
        # For now, return False as this feature needs more work on macOS
        return False

    def enable_autostart(self) -> bool:
        """
        Enable application auto-start at user login.
        
        Currently unimplemented for macOS; this method always returns `False`. If the application executable path cannot be determined (development mode), it logs a warning and returns `False`.
        
        Returns:
            bool: `True` if auto-start was enabled, `False` otherwise.
        """
        exe_path = get_executable_path()
        if exe_path is None:
            logger.warning("Cannot enable autostart in development mode")
            return False

        # TODO: Implement using osascript or LaunchAgent
        # Example with osascript:
        # osascript -e 'tell application "System Events" to make login item at end
        #   with properties {path:"/path/to/app", hidden:false}'
        logger.info("macOS autostart not yet implemented")
        return False

    def disable_autostart(self) -> bool:
        """
        Disable application auto-start on macOS login.
        
        Currently unimplemented; calling this always leaves auto-start unchanged and returns `False`.
        
        Returns:
            `False` because disabling auto-start is not implemented.
        """
        # TODO: Implement removal of login item
        logger.info("macOS autostart disable not yet implemented")
        return False

    # -------------------------------------------------------------------------
    # UI Configuration
    # -------------------------------------------------------------------------

    def get_tray_icon_size(self) -> tuple[int, int]:
        """
        Provides the recommended size for a macOS menu bar (tray) icon.
        
        Returns:
            tuple[int, int]: Width and height in pixels for the icon — (22, 22).
        """
        return (22, 22)