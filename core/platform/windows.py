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
        """Return the platform identifier."""
        return "windows"

    # -------------------------------------------------------------------------
    # Path Methods
    # -------------------------------------------------------------------------

    def get_data_dir(self) -> Path:
        """Get Windows application data directory.

        Returns:
            Path to %APPDATA%/LiveRecall (typically C:/Users/<user>/AppData/Roaming/LiveRecall)
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
        """Open a folder in Windows Explorer.

        Args:
            path: Path to the folder to open.
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
        """Windows does not require explicit screen recording permission.

        Returns:
            False - Windows grants screen capture automatically.
        """
        return False

    def check_screen_permission(self) -> bool:
        """Check if screen recording permission is granted.

        Windows always grants this permission.

        Returns:
            True - always granted on Windows.
        """
        return True

    def request_screen_permission(self) -> bool:
        """Request screen recording permission.

        No-op on Windows as permission is automatically granted.

        Returns:
            True - no request needed.
        """
        return True

    def reset_screen_permission(self) -> tuple[bool, str]:
        """Reset screen recording permission.

        No-op on Windows as there's no permission to reset.

        Returns:
            Tuple of (True, message) indicating no action needed.
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
        """Disable auto-start by removing the Registry entry.

        Returns:
            True if successfully disabled, False otherwise.
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
        """Get Windows system tray icon size.

        Windows system tray typically uses 32x32 icons.

        Returns:
            (32, 32) for Windows system tray.
        """
        return (32, 32)
