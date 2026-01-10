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
    """
    Return whether the current process is a frozen executable (for example, created by PyInstaller).
    
    Returns:
        bool: `True` if running as a frozen executable, `False` otherwise.
    """
    return getattr(sys, "frozen", False)


def get_executable_path() -> Path | None:
    """
    Return the path to the bundled executable when running as a frozen application.
    
    Returns:
        Path: Path to the executable when running frozen, or None when running in a non-frozen (development) environment.
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
        """
        Return the platform-specific application data directory, creating it if necessary.
        
        This is the directory where the application stores user data:
        - macOS: ~/Library/Application Support/LiveRecall
        - Windows: %APPDATA%/LiveRecall
        - Linux: $XDG_DATA_HOME/LiveRecall or ~/.local/share/LiveRecall
        
        Returns:
            Path to the platform data directory.
        """
        ...

    def get_config_path(self) -> Path:
        """
        Get the path to the platform configuration file.
        
        Returns:
            Path to the 'config.json' file located in the platform data directory.
        """
        return self.get_data_dir() / "config.json"

    def get_database_path(self) -> Path:
        """
        Return the path to the application's SQLite database file.
        
        Returns:
            Path: Path to the `liverecall.db` file inside the platform-specific data directory.
        """
        return self.get_data_dir() / "liverecall.db"

    def get_screenshots_dir(self) -> Path:
        """
        Locate and ensure the application's screenshots storage directory exists.
        
        Returns:
            Path to the screenshots subdirectory, created if it did not exist.
        """
        screenshots_dir = self.get_data_dir() / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        return screenshots_dir

    # -------------------------------------------------------------------------
    # System Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    def open_folder(self, path: Path) -> None:
        """
        Open the given directory in the system file explorer.
        
        Parameters:
            path (Path): Path to the directory to open.
        """
        ...

    def open_url(self, url: str) -> None:
        """
        Open the given URL using the system's default web browser.
        
        Parameters:
            url (str): The URL to open. Should be a valid absolute web URL (e.g., starting with "http://" or "https://").
        """
        webbrowser.open(url)

    # -------------------------------------------------------------------------
    # Screen Recording Permissions
    # -------------------------------------------------------------------------

    @abstractmethod
    def needs_screen_permission(self) -> bool:
        """
        Determine whether the current platform requires an explicit screen-recording permission.
        
        Returns:
            `True` if the platform requires screen recording permission, `False` otherwise.
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
        """
        Prompt the user to grant screen recording permission.
        
        Returns:
            `True` if the permission request was issued (the user may still deny), `False` if the request could not be initiated.
        """
        ...

    @abstractmethod
    def reset_screen_permission(self) -> tuple[bool, str]:
        """
        Reset the platform-specific screen-recording permission state to force the system to re-prompt for permission.
        
        Per-platform implementations may perform any necessary actions to clear or reset stored permission state. Returns whether the reset was performed and a human-readable message with details or error information.
        
        Returns:
            Tuple where the first element is `True` if the reset succeeded, `False` otherwise; the second element is a human-readable message describing the result.
        """
        ...

    # -------------------------------------------------------------------------
    # Auto-start on Login
    # -------------------------------------------------------------------------

    @abstractmethod
    def is_autostart_enabled(self) -> bool:
        """
        Check whether the application is configured to start automatically on user login.
        
        Returns:
            `True` if the application will start automatically on login, `False` otherwise.
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
        """
        Determine the ideal system tray icon size for the current platform.
        
        Returns:
            (width, height) — Icon dimensions in pixels suitable for the platform.
        """
        ...