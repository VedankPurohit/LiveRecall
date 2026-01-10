"""
Linux platform implementation (STUB).

Linux is not officially supported yet. This stub exists to:
1. Prevent crashes if someone runs on Linux
2. Provide a foundation for future Linux support

The implementation follows XDG specifications where applicable.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Literal

from .base import APP_NAME, PlatformBase, get_executable_path

logger = logging.getLogger(__name__)

# XDG autostart directory
_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
_DESKTOP_FILE_NAME = f"{APP_NAME.lower()}.desktop"


class LinuxPlatform(PlatformBase):
    """Linux-specific platform implementation."""

    @property
    def name(self) -> Literal["macos", "windows", "linux"]:
        """Return the platform identifier."""
        return "linux"

    # -------------------------------------------------------------------------
    # Path Methods
    # -------------------------------------------------------------------------

    def get_data_dir(self) -> Path:
        """Get Linux application data directory following XDG Base Directory spec.

        Returns:
            Path to $XDG_DATA_HOME/LiveRecall or ~/.local/share/LiveRecall
        """
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"

        data_dir = base / APP_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    # -------------------------------------------------------------------------
    # System Operations
    # -------------------------------------------------------------------------

    def open_folder(self, path: Path) -> None:
        """Open a folder using xdg-open.

        Args:
            path: Path to the folder to open.
        """
        try:
            subprocess.run(["xdg-open", str(path)], check=False)
        except FileNotFoundError:
            logger.error("xdg-open not found. Cannot open folder.")
        except Exception as e:
            logger.error(f"Failed to open folder {path}: {e}")

    # -------------------------------------------------------------------------
    # Screen Recording Permissions
    # -------------------------------------------------------------------------

    def needs_screen_permission(self) -> bool:
        """Check if Linux requires screen recording permission.

        On X11, screen recording generally works without permission.
        On Wayland, it depends on the compositor and may require portal access.

        Returns:
            False - we assume permission works and let capture fail if not.
        """
        # TODO: Detect Wayland vs X11 and handle accordingly
        return False

    def check_screen_permission(self) -> bool:
        """Check if screen recording permission is granted.

        Returns:
            True - assume granted, let capture fail if not.
        """
        # TODO: On Wayland, could check portal permissions
        return True

    def request_screen_permission(self) -> bool:
        """Request screen recording permission.

        On Wayland, this would involve the xdg-desktop-portal.

        Returns:
            True - request flow varies by desktop environment.
        """
        # TODO: Implement Wayland portal request if needed
        return True

    def reset_screen_permission(self) -> tuple[bool, str]:
        """Reset screen recording permission.

        Linux doesn't have a centralized permission system like macOS TCC.

        Returns:
            Tuple indicating no action needed.
        """
        return True, "No permission reset needed on Linux. Screen capture permissions vary by desktop environment."

    # -------------------------------------------------------------------------
    # Auto-start on Login
    # -------------------------------------------------------------------------

    def is_autostart_enabled(self) -> bool:
        """Check if auto-start is enabled via XDG autostart.

        Returns:
            True if the desktop file exists in ~/.config/autostart
        """
        desktop_file = _AUTOSTART_DIR / _DESKTOP_FILE_NAME
        return desktop_file.exists()

    def enable_autostart(self) -> bool:
        """Enable auto-start via XDG autostart desktop file.

        Creates a .desktop file in ~/.config/autostart/

        Returns:
            True if successfully enabled, False otherwise.
        """
        exe_path = get_executable_path()
        if exe_path is None:
            logger.warning("Cannot enable autostart in development mode")
            return False

        try:
            _AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)

            desktop_content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Screen recall and search application
Exec={exe_path}
Icon={APP_NAME.lower()}
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
StartupWMClass={APP_NAME}
"""
            desktop_file = _AUTOSTART_DIR / _DESKTOP_FILE_NAME
            desktop_file.write_text(desktop_content)
            logger.info(f"Created autostart desktop file: {desktop_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable autostart: {e}")
            return False

    def disable_autostart(self) -> bool:
        """Disable auto-start by removing the desktop file.

        Returns:
            True if successfully disabled, False otherwise.
        """
        try:
            desktop_file = _AUTOSTART_DIR / _DESKTOP_FILE_NAME
            if desktop_file.exists():
                desktop_file.unlink()
                logger.info(f"Removed autostart desktop file: {desktop_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable autostart: {e}")
            return False

    # -------------------------------------------------------------------------
    # UI Configuration
    # -------------------------------------------------------------------------

    def get_tray_icon_size(self) -> tuple[int, int]:
        """Get Linux system tray icon size.

        Most Linux desktop environments use 32x32 for system tray icons.

        Returns:
            (32, 32) for Linux system tray.
        """
        return (32, 32)
