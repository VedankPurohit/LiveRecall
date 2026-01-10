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
        """Return the platform identifier."""
        return "macos"

    # -------------------------------------------------------------------------
    # Path Methods
    # -------------------------------------------------------------------------

    def get_data_dir(self) -> Path:
        """Get macOS application data directory.

        Returns:
            Path to ~/Library/Application Support/LiveRecall
        """
        data_dir = Path.home() / "Library" / "Application Support" / APP_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    # -------------------------------------------------------------------------
    # System Operations
    # -------------------------------------------------------------------------

    def open_folder(self, path: Path) -> None:
        """Open a folder in Finder.

        Args:
            path: Path to the folder to open.
        """
        try:
            subprocess.run(["open", str(path)], check=False)
        except Exception as e:
            logger.error(f"Failed to open folder {path}: {e}")

    # -------------------------------------------------------------------------
    # Screen Recording Permissions
    # -------------------------------------------------------------------------

    def needs_screen_permission(self) -> bool:
        """macOS requires explicit screen recording permission.

        Returns:
            True - macOS always requires permission.
        """
        return True

    def check_screen_permission(self) -> bool:
        """Check if screen recording permission is granted.

        Note: There's no reliable programmatic way to check this on macOS
        without actually attempting a screen capture. The mss library will
        fail if permission is not granted.

        Returns:
            True - we assume permission is granted and let capture fail if not.
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
        """Reset screen recording permission via tccutil.

        This runs: tccutil reset ScreenCapture com.liverecall.app

        This is useful after app updates when macOS invalidates the
        permission for unsigned apps.

        Returns:
            Tuple of (success, message).
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
        """Check if auto-start is enabled.

        Note: macOS Login Items are managed differently and checking
        programmatically is complex. This is a stub for future implementation.

        Returns:
            False - stub implementation.
        """
        # TODO: Check Login Items via SMAppService or LaunchAgent
        # For now, return False as this feature needs more work on macOS
        return False

    def enable_autostart(self) -> bool:
        """Enable auto-start on login.

        Note: This is a stub. macOS auto-start requires either:
        - SMAppService (for sandboxed apps)
        - LaunchAgent plist (for non-sandboxed apps)
        - Login Items via AppleScript/osascript

        Returns:
            False - not yet implemented.
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
        """Disable auto-start on login.

        Returns:
            False - not yet implemented.
        """
        # TODO: Implement removal of login item
        logger.info("macOS autostart disable not yet implemented")
        return False

    # -------------------------------------------------------------------------
    # UI Configuration
    # -------------------------------------------------------------------------

    def get_tray_icon_size(self) -> tuple[int, int]:
        """Get macOS menu bar icon size.

        macOS menu bar icons should be smaller (22x22) to match
        the native menu bar aesthetic.

        Returns:
            (22, 22) for macOS menu bar.
        """
        return (22, 22)
