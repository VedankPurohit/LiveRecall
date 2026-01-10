"""
Windows platform implementation.

Handles Windows-specific operations including:
- Data storage in %APPDATA%
- Screen recording (no permission needed)
- Auto-start via Registry
- System tray icon sizing (32x32)
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from .base import APP_NAME, PlatformBase, get_executable_path

# Import winreg only on Windows to avoid mypy errors on other platforms
_winreg: Any = None
if sys.platform == "win32":
    import winreg as _winreg

logger = logging.getLogger(__name__)

# Windows Registry key for auto-start
_REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REGISTRY_APP_NAME = APP_NAME


class WindowsPlatform(PlatformBase):
    """Windows-specific platform implementation."""

    @property
    def name(self) -> Literal["macos", "windows", "linux"]:
        """
        Platform identifier for this implementation.
        
        Returns:
            'windows': The platform identifier string literal for Windows.
        """
        return "windows"

    # -------------------------------------------------------------------------
    # Path Methods
    # -------------------------------------------------------------------------

    def get_data_dir(self) -> Path:
        """
        Return the application's data directory within the user's roaming AppData.
        
        Ensures the directory exists before returning it.
        
        Returns:
            Path to the application's data directory (e.g., %APPDATA%\\LiveRecall or C:/Users/<user>/AppData/Roaming/LiveRecall)
        """
        # Use APPDATA environment variable, fall back to standard location
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"

        data_dir = base / APP_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    # -------------------------------------------------------------------------
    # System Operations
    # -------------------------------------------------------------------------

    def open_folder(self, path: Path) -> None:
        """
        Open the given directory in Windows Explorer.
        
        Parameters:
            path (Path): Directory path to open in Explorer.
        """
        try:
            # Use explorer.exe to open the folder
            subprocess.run(["explorer", str(path)], check=False)
        except Exception as e:
            logger.error(f"Failed to open folder {path}: {e}")

    # -------------------------------------------------------------------------
    # Screen Recording Permissions
    # -------------------------------------------------------------------------

    def needs_screen_permission(self) -> bool:
        """
        Indicates whether the current platform requires explicit screen-recording permission.
        
        Returns:
            `True` if screen recording permission is considered granted on this platform, `False` otherwise.
        """
        return False

    def check_screen_permission(self) -> bool:
        """
        Indicates whether screen recording permission is granted on Windows.
        
        Returns:
            True indicating screen recording permission is considered granted on Windows.
        """
        return True

    def request_screen_permission(self) -> bool:
        """
        No-op that confirms screen recording permission is available on Windows.
        
        Returns:
            True if permission is available and no request was performed.
        """
        return True

    def reset_screen_permission(self) -> tuple[bool, str]:
        """
        Reset screen recording permission.
        
        No operation on Windows because screen capture permission is managed by the system and cannot be reset by the application.
        
        Returns:
            tuple[bool, str]: A pair where the first element is `True` indicating no action was required, and the second element is a human-readable message explaining the outcome.
        """
        return True, "No permission reset needed on Windows. Screen capture works automatically."

    # -------------------------------------------------------------------------
    # Auto-start on Login
    # -------------------------------------------------------------------------

    def is_autostart_enabled(self) -> bool:
        """Check if auto-start is enabled via Windows Registry.

        Returns:
            True if the registry key exists, False otherwise.
        """
        if _winreg is None:
            logger.warning("winreg module not available (not on Windows)")
            return False

        try:
            key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, _REGISTRY_KEY, 0, _winreg.KEY_READ)
            try:
                _winreg.QueryValueEx(key, _REGISTRY_APP_NAME)
                return True
            except FileNotFoundError:
                return False
            finally:
                _winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to check autostart status: {e}")
            return False

    def enable_autostart(self) -> bool:
        """Enable auto-start via Windows Registry.

        Adds an entry to HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run

        Returns:
            True if successfully enabled, False otherwise.
        """
        if _winreg is None:
            logger.warning("winreg module not available (not on Windows)")
            return False

        exe_path = get_executable_path()
        if exe_path is None:
            logger.warning("Cannot enable autostart in development mode")
            return False

        try:
            key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, _REGISTRY_KEY, 0, _winreg.KEY_WRITE)
            try:
                _winreg.SetValueEx(key, _REGISTRY_APP_NAME, 0, _winreg.REG_SZ, str(exe_path))
                logger.info(f"Enabled autostart for {exe_path}")
                return True
            finally:
                _winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to enable autostart: {e}")
            return False

    def disable_autostart(self) -> bool:
        """
        Remove the application's autostart entry from the current user's Windows Run registry key.
        
        Returns:
            True if the autostart entry was removed or did not exist, False on error or when the Windows registry API is unavailable.
        """
        if _winreg is None:
            logger.warning("winreg module not available (not on Windows)")
            return False

        try:
            key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, _REGISTRY_KEY, 0, _winreg.KEY_WRITE)
            try:
                _winreg.DeleteValue(key, _REGISTRY_APP_NAME)
                logger.info("Disabled autostart")
                return True
            except FileNotFoundError:
                # Key doesn't exist, which means autostart is already disabled
                logger.info("Autostart was not enabled")
                return True
            finally:
                _winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to disable autostart: {e}")
            return False

    # -------------------------------------------------------------------------
    # UI Configuration
    # -------------------------------------------------------------------------

    def get_tray_icon_size(self) -> tuple[int, int]:
        """
        Provide the standard Windows system tray icon size.
        
        Returns:
            tuple[int, int]: Width and height in pixels (32, 32).
        """
        return (32, 32)