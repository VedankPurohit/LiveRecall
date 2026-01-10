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
        """
        Identify the platform as Linux.
        
        Returns:
            The literal string 'linux' identifying this platform implementation.
        """
        return "linux"

    # -------------------------------------------------------------------------
    # Path Methods
    # -------------------------------------------------------------------------

    def get_data_dir(self) -> Path:
        """
        Determine the application data directory according to the XDG Base Directory specification.
        
        Returns:
            Path: The directory at $XDG_DATA_HOME/<APP_NAME> if XDG_DATA_HOME is set, otherwise ~/.local/share/<APP_NAME>. The directory is created if it does not already exist.
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
        """
        Open the given folder in the user's default file manager.
        
        Parameters:
            path (Path): Path to the folder to open.
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
        """
        Indicates whether the current Linux environment requires explicit screen recording permission.
        
        Currently always returns False; Wayland vs X11 detection is not implemented.
        
        Returns:
            `True` if the environment requires explicit screen recording permission, `False` otherwise.
        """
        # TODO: Detect Wayland vs X11 and handle accordingly
        return False

    def check_screen_permission(self) -> bool:
        """
        Report whether screen recording permission is available.
        
        On this Linux implementation the check assumes permission is granted; capture operations may still fail if the environment denies access.
        
        Returns:
            bool: `True` if permission appears to be granted; this implementation always returns `True`.
        """
        # TODO: On Wayland, could check portal permissions
        return True

    def request_screen_permission(self) -> bool:
        """
        Request screen recording permission from the user.
        
        On Wayland this typically involves xdg-desktop-portal; currently this implementation is a stub and assumes permission is granted.
        
        Returns:
            `True` if screen recording permission is granted, `False` otherwise.
        """
        # TODO: Implement Wayland portal request if needed
        return True

    def reset_screen_permission(self) -> tuple[bool, str]:
        """
        Indicates that no platform-level screen-permission reset is performed on Linux.
        
        Linux does not provide a single, system-wide screen-recording permission to reset; behavior depends on the desktop environment.
        
        Returns:
            (True, str): A tuple where `True` indicates no reset was performed and the string explains that permissions vary by desktop environment.
        """
        return True, "No permission reset needed on Linux. Screen capture permissions vary by desktop environment."

    # -------------------------------------------------------------------------
    # Auto-start on Login
    # -------------------------------------------------------------------------

    def is_autostart_enabled(self) -> bool:
        """
        Determine whether the application is configured to auto-start via XDG autostart.
        
        Returns:
            True if the autostart desktop file exists in the user's ~/.config/autostart directory, False otherwise.
        """
        desktop_file = _AUTOSTART_DIR / _DESKTOP_FILE_NAME
        return desktop_file.exists()

    def enable_autostart(self) -> bool:
        """
        Enable application autostart by creating an XDG autostart `.desktop` file.
        
        Creates or overwrites a `.desktop` file in the user's `~/.config/autostart` directory so the application launches on login. If the executable path cannot be determined (for example, in development mode), no file is written.
        
        Returns:
            `True` if the autostart file was created, `False` otherwise.
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
        """
        Provide the recommended system tray icon size for Linux desktop environments.
        
        Returns:
            A tuple `(width, height)` in pixels; typically `(32, 32)`.
        """
        return (32, 32)