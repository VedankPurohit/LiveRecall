"""
Platform abstraction layer for LiveRecall.

This module provides a unified interface for platform-specific operations,
automatically detecting the current platform and exposing the appropriate
implementation.

Usage:
    from core.platform import current_platform

    # Get platform-specific paths
    data_dir = current_platform.get_data_dir()
    screenshots_dir = current_platform.get_screenshots_dir()

    # System operations
    current_platform.open_folder(data_dir)
    current_platform.open_url("https://example.com")

    # Permissions
    if current_platform.needs_screen_permission():
        current_platform.request_screen_permission()

    # Auto-start
    current_platform.enable_autostart()
    current_platform.disable_autostart()
    is_enabled = current_platform.is_autostart_enabled()

    # UI config
    icon_size = current_platform.get_tray_icon_size()

Supported platforms:
    - macOS (darwin)
    - Windows (win32)
    - Linux (other)
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from .base import PlatformBase

if TYPE_CHECKING:
    pass


def _get_platform() -> PlatformBase:
    """Detect and instantiate the appropriate platform implementation.

    Returns:
        Platform implementation for the current OS.
    """
    if sys.platform == "darwin":
        from .macos import MacOSPlatform

        return MacOSPlatform()
    elif sys.platform == "win32":
        from .windows import WindowsPlatform

        return WindowsPlatform()
    else:
        from .linux import LinuxPlatform

        return LinuxPlatform()


# Singleton instance of the current platform
current_platform: PlatformBase = _get_platform()

__all__ = [
    "current_platform",
    "PlatformBase",
]
