"""
Abstract base class for platform-specific operations.

This module defines the interface that all platform implementations must follow.
Each platform (macOS, Windows, Linux) provides its own concrete implementation.
"""

from __future__ import annotations

import logging
import sys
import webbrowser
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Application constants
APP_NAME = "LiveRecall"
APP_BUNDLE_ID = "com.liverecall.app"


def is_frozen() -> bool:
    """Check if running as a frozen PyInstaller application."""
    return getattr(sys, "frozen", False)


def get_executable_path() -> Path | None:
    """Get path to the executable when running as frozen app.

    Returns:
        Path to the executable, or None if running in development mode.
    """
    if is_frozen():
        return Path(sys.executable)
    return None


class PlatformBase(ABC):
    """Abstract base class for platform-specific operations.

    This class defines the interface that all platform implementations
    must follow. Each platform (macOS, Windows, Linux) provides its
    own concrete implementation.

    Example:
        >>> from core.platform import current_platform
        >>> data_dir = current_platform.get_data_dir()
        >>> print(data_dir)
        /Users/username/Library/Application Support/LiveRecall

        >>> current_platform.open_folder(data_dir)
        >>> current_platform.enable_autostart()
    """

    @property
    @abstractmethod
    def name(self) -> Literal["macos", "windows", "linux"]:
        """Return the platform identifier.

        Returns:
            One of "macos", "windows", or "linux".
        """
        ...

    # -------------------------------------------------------------------------
    # Path Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def get_data_dir(self) -> Path:
        """Get the platform-specific application data directory.

        Creates the directory if it doesn't exist.

        Returns:
            Path to the data directory.
                - macOS: ~/Library/Application Support/LiveRecall
                - Windows: %APPDATA%/LiveRecall
                - Linux: $XDG_DATA_HOME/LiveRecall or ~/.local/share/LiveRecall
        """
        ...

    def get_config_path(self) -> Path:
        """Get the configuration file path.

        Returns:
            Path to config.json in the data directory.
        """
        return self.get_data_dir() / "config.json"

    def get_database_path(self) -> Path:
        """Get the database file path.

        Returns:
            Path to liverecall.db in the data directory.
        """
        return self.get_data_dir() / "liverecall.db"

    def get_screenshots_dir(self) -> Path:
        """Get the screenshots storage directory.

        Creates the directory if it doesn't exist.

        Returns:
            Path to the screenshots subdirectory.
        """
        screenshots_dir = self.get_data_dir() / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        return screenshots_dir

    # -------------------------------------------------------------------------
    # System Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    def open_folder(self, path: Path) -> None:
        """Open a folder in the system's file explorer.

        Args:
            path: Path to the folder to open.
        """
        ...

    def open_url(self, url: str) -> None:
        """Open a URL in the default browser.

        Args:
            url: The URL to open.
        """
        webbrowser.open(url)

    # -------------------------------------------------------------------------
    # Screen Recording Permissions
    # -------------------------------------------------------------------------

    @abstractmethod
    def needs_screen_permission(self) -> bool:
        """Check if this platform requires explicit screen recording permission.

        Returns:
            True if the platform requires permission setup, False otherwise.
        """
        ...

    @abstractmethod
    def check_screen_permission(self) -> bool:
        """Check if screen recording permission is currently granted.

        Returns:
            True if permission is granted, False otherwise.
        """
        ...

    @abstractmethod
    def request_screen_permission(self) -> bool:
        """Request screen recording permission from the user.

        Returns:
            True if the request was made (user may still deny), False on error.
        """
        ...

    @abstractmethod
    def reset_screen_permission(self) -> tuple[bool, str]:
        """Reset screen recording permission to trigger a new permission prompt.

        This is useful when the app has been updated and permissions need
        to be re-granted.

        Returns:
            Tuple of (success, message) where success indicates if the reset
            was performed, and message provides details or error information.
        """
        ...

    # -------------------------------------------------------------------------
    # Auto-start on Login
    # -------------------------------------------------------------------------

    @abstractmethod
    def is_autostart_enabled(self) -> bool:
        """Check if auto-start on login is enabled.

        Returns:
            True if the app will start automatically on login.
        """
        ...

    @abstractmethod
    def enable_autostart(self) -> bool:
        """Enable auto-start on login.

        Returns:
            True if successfully enabled, False otherwise.
        """
        ...

    @abstractmethod
    def disable_autostart(self) -> bool:
        """Disable auto-start on login.

        Returns:
            True if successfully disabled, False otherwise.
        """
        ...

    # -------------------------------------------------------------------------
    # UI Configuration
    # -------------------------------------------------------------------------

    @abstractmethod
    def get_tray_icon_size(self) -> tuple[int, int]:
        """Get the appropriate system tray icon size for this platform.

        Returns:
            Tuple of (width, height) for the icon.
        """
        ...
