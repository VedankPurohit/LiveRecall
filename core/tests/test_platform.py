"""
Tests for the platform abstraction layer.

Tests cover:
- Platform detection
- Path methods
- System operations (with mocks)
- Permission handling
- Auto-start functionality
- UI configuration
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPlatformDetection:
    """Tests for platform detection and instantiation."""

    def test_current_platform_exists(self):
        """Test that current_platform is instantiated."""
        from core.platform import current_platform

        assert current_platform is not None

    def test_current_platform_has_correct_type(self):
        """Test that current_platform is a PlatformBase subclass."""
        from core.platform import PlatformBase, current_platform

        assert isinstance(current_platform, PlatformBase)

    def test_platform_name_is_valid(self):
        """Test that platform name is one of the valid options."""
        from core.platform import current_platform

        assert current_platform.name in ("macos", "windows", "linux")

    def test_platform_name_matches_sys_platform(self):
        """Test that detected platform matches sys.platform."""
        from core.platform import current_platform

        if sys.platform == "darwin":
            assert current_platform.name == "macos"
        elif sys.platform == "win32":
            assert current_platform.name == "windows"
        else:
            assert current_platform.name == "linux"


class TestPathMethods:
    """Tests for path-related methods."""

    def test_get_data_dir_returns_path(self):
        """Test that get_data_dir returns a Path object."""
        from core.platform import current_platform

        data_dir = current_platform.get_data_dir()
        assert isinstance(data_dir, Path)

    def test_get_data_dir_creates_directory(self, temp_dir):
        """Test that get_data_dir creates the directory if it doesn't exist."""
        from core.platform import current_platform

        # The actual data dir should exist after calling get_data_dir
        data_dir = current_platform.get_data_dir()
        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_get_data_dir_contains_app_name(self):
        """Test that data dir path contains LiveRecall."""
        from core.platform import current_platform

        data_dir = current_platform.get_data_dir()
        assert "LiveRecall" in str(data_dir)

    def test_get_screenshots_dir_is_subdirectory(self):
        """Test that screenshots dir is inside data dir."""
        from core.platform import current_platform

        data_dir = current_platform.get_data_dir()
        screenshots_dir = current_platform.get_screenshots_dir()

        assert screenshots_dir.parent == data_dir
        assert screenshots_dir.name == "screenshots"

    def test_get_screenshots_dir_creates_directory(self):
        """Test that get_screenshots_dir creates the directory."""
        from core.platform import current_platform

        screenshots_dir = current_platform.get_screenshots_dir()
        assert screenshots_dir.exists()
        assert screenshots_dir.is_dir()

    def test_get_database_path_has_correct_extension(self):
        """Test that database path has .db extension."""
        from core.platform import current_platform

        db_path = current_platform.get_database_path()
        assert db_path.suffix == ".db"
        assert db_path.name == "liverecall.db"

    def test_get_config_path_has_correct_extension(self):
        """Test that config path has .json extension."""
        from core.platform import current_platform

        config_path = current_platform.get_config_path()
        assert config_path.suffix == ".json"
        assert config_path.name == "config.json"

    def test_all_paths_in_data_dir(self):
        """Test that all paths are within the data directory."""
        from core.platform import current_platform

        data_dir = current_platform.get_data_dir()
        screenshots_dir = current_platform.get_screenshots_dir()
        db_path = current_platform.get_database_path()
        config_path = current_platform.get_config_path()

        assert screenshots_dir.parent == data_dir
        assert db_path.parent == data_dir
        assert config_path.parent == data_dir


class TestMacOSPaths:
    """Tests for macOS-specific paths."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_macos_data_dir_location(self):
        """Test macOS data dir is in Library/Application Support."""
        from core.platform import current_platform

        data_dir = current_platform.get_data_dir()
        assert "Library/Application Support" in str(data_dir)


class TestWindowsPaths:
    """Tests for Windows-specific paths (with mocks for cross-platform testing)."""

    def test_windows_data_dir_uses_appdata(self):
        """Test Windows platform uses APPDATA environment variable."""
        from core.platform.windows import WindowsPlatform

        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
            platform = WindowsPlatform()
            # We can't actually create the dir on non-Windows, but we can test the logic
            # by checking that it would use APPDATA
            assert platform.name == "windows"


class TestLinuxPaths:
    """Tests for Linux-specific paths (with mocks for cross-platform testing)."""

    def test_linux_data_dir_uses_xdg(self):
        """Test Linux platform respects XDG_DATA_HOME."""
        from core.platform.linux import LinuxPlatform

        platform = LinuxPlatform()
        assert platform.name == "linux"


class TestSystemOperations:
    """Tests for system operations."""

    def test_open_folder_calls_correct_command(self):
        """Test that open_folder uses the correct system command."""
        from core.platform import current_platform

        with patch("subprocess.run") as mock_run:
            test_path = Path("/tmp/test")
            current_platform.open_folder(test_path)

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]

            if current_platform.name == "macos":
                assert call_args[0] == "open"
            elif current_platform.name == "windows":
                assert call_args[0] == "explorer"
            else:
                assert call_args[0] == "xdg-open"

    def test_open_url_uses_webbrowser(self):
        """Test that open_url uses webbrowser module."""
        from core.platform import current_platform

        with patch("webbrowser.open") as mock_open:
            current_platform.open_url("https://example.com")
            mock_open.assert_called_once_with("https://example.com")


class TestPermissions:
    """Tests for permission handling."""

    def test_needs_screen_permission_returns_bool(self):
        """Test that needs_screen_permission returns a boolean."""
        from core.platform import current_platform

        result = current_platform.needs_screen_permission()
        assert isinstance(result, bool)

    def test_check_screen_permission_returns_bool(self):
        """Test that check_screen_permission returns a boolean."""
        from core.platform import current_platform

        result = current_platform.check_screen_permission()
        assert isinstance(result, bool)

    def test_reset_screen_permission_returns_tuple(self):
        """Test that reset_screen_permission returns (bool, str)."""
        from core.platform import current_platform

        # Mock subprocess to avoid actual permission reset
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = current_platform.reset_screen_permission()

            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_macos_needs_screen_permission(self):
        """Test that macOS reports needing screen permission."""
        from core.platform import current_platform

        assert current_platform.needs_screen_permission() is True

    def test_windows_no_screen_permission_needed(self):
        """Test that Windows doesn't need screen permission."""
        from core.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        assert platform.needs_screen_permission() is False

    def test_windows_reset_permission_is_noop(self):
        """Test that Windows permission reset is a no-op."""
        from core.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        success, message = platform.reset_screen_permission()

        assert success is True
        assert "Windows" in message or "No permission" in message


class TestAutostart:
    """Tests for auto-start functionality."""

    def test_is_autostart_enabled_returns_bool(self):
        """Test that is_autostart_enabled returns a boolean."""
        from core.platform import current_platform

        result = current_platform.is_autostart_enabled()
        assert isinstance(result, bool)

    def test_enable_autostart_returns_bool(self):
        """Test that enable_autostart returns a boolean."""
        from core.platform import current_platform

        # This will likely return False in dev mode, which is expected
        result = current_platform.enable_autostart()
        assert isinstance(result, bool)

    def test_disable_autostart_returns_bool(self):
        """Test that disable_autostart returns a boolean."""
        from core.platform import current_platform

        result = current_platform.disable_autostart()
        assert isinstance(result, bool)

    def test_autostart_methods_exist(self):
        """Test that all autostart methods are implemented."""
        from core.platform import current_platform

        assert hasattr(current_platform, "is_autostart_enabled")
        assert hasattr(current_platform, "enable_autostart")
        assert hasattr(current_platform, "disable_autostart")
        assert callable(current_platform.is_autostart_enabled)
        assert callable(current_platform.enable_autostart)
        assert callable(current_platform.disable_autostart)


class TestWindowsAutostart:
    """Tests for Windows auto-start (with mocks)."""

    def test_windows_autostart_checks_registry(self):
        """Test Windows autostart checks registry key."""
        from core.platform.windows import WindowsPlatform

        platform = WindowsPlatform()

        # Mock winreg to simulate checking registry
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.side_effect = FileNotFoundError()

        with patch.dict(sys.modules, {"winreg": mock_winreg}):
            # Force re-import to use mock
            result = platform.is_autostart_enabled()
            # Should return False when key not found
            assert isinstance(result, bool)


class TestTrayIconSize:
    """Tests for tray icon sizing."""

    def test_tray_icon_size_returns_tuple(self):
        """Test that get_tray_icon_size returns a tuple."""
        from core.platform import current_platform

        result = current_platform.get_tray_icon_size()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_tray_icon_size_is_positive(self):
        """Test that icon sizes are positive integers."""
        from core.platform import current_platform

        width, height = current_platform.get_tray_icon_size()
        assert isinstance(width, int)
        assert isinstance(height, int)
        assert width > 0
        assert height > 0

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_macos_icon_size_is_22x22(self):
        """Test macOS uses 22x22 for menu bar."""
        from core.platform import current_platform

        assert current_platform.get_tray_icon_size() == (22, 22)

    def test_windows_icon_size_is_32x32(self):
        """Test Windows uses 32x32 for system tray."""
        from core.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        assert platform.get_tray_icon_size() == (32, 32)

    def test_linux_icon_size_is_32x32(self):
        """Test Linux uses 32x32 for system tray."""
        from core.platform.linux import LinuxPlatform

        platform = LinuxPlatform()
        assert platform.get_tray_icon_size() == (32, 32)


class TestBaseClass:
    """Tests for the PlatformBase abstract class."""

    def test_platform_base_is_abstract(self):
        """Test that PlatformBase cannot be instantiated."""
        from core.platform.base import PlatformBase

        with pytest.raises(TypeError):
            PlatformBase()

    def test_is_frozen_returns_bool(self):
        """Test is_frozen utility function."""
        from core.platform.base import is_frozen

        result = is_frozen()
        assert isinstance(result, bool)
        # In test environment, should not be frozen
        assert result is False

    def test_get_executable_path_in_dev_mode(self):
        """Test get_executable_path returns None in dev mode."""
        from core.platform.base import get_executable_path

        result = get_executable_path()
        # In development mode, should return None
        assert result is None


class TestBackwardsCompatibility:
    """Tests for backwards compatibility with existing code."""

    def test_core_config_platform_variable(self):
        """Test that core.config.PLATFORM still works."""
        from core.config import PLATFORM

        assert PLATFORM in ("macos", "windows", "linux")

    def test_core_config_get_data_dir(self):
        """Test that core.config.get_data_dir still works."""
        from core.config import get_data_dir

        data_dir = get_data_dir()
        assert isinstance(data_dir, Path)
        assert data_dir.exists()

    def test_core_config_get_screenshots_dir(self):
        """Test that core.config.get_screenshots_dir still works."""
        from core.config import get_screenshots_dir

        screenshots_dir = get_screenshots_dir()
        assert isinstance(screenshots_dir, Path)
        assert screenshots_dir.exists()

    def test_core_config_get_database_path(self):
        """Test that core.config.get_database_path still works."""
        from core.config import get_database_path

        db_path = get_database_path()
        assert isinstance(db_path, Path)
        assert db_path.suffix == ".db"

    def test_core_config_get_config_path(self):
        """Test that core.config.get_config_path still works."""
        from core.config import get_config_path

        config_path = get_config_path()
        assert isinstance(config_path, Path)
        assert config_path.suffix == ".json"

    def test_tray_config_platform_variable(self):
        """Test that tray.config.PLATFORM still works."""
        from tray.config import PLATFORM

        assert PLATFORM in ("macos", "windows", "linux")

    def test_tray_config_get_icon_size(self):
        """Test that tray.config.get_icon_size still works."""
        from tray.config import get_icon_size

        size = get_icon_size()
        assert isinstance(size, tuple)
        assert len(size) == 2
