"""
Tests for tray/config.py
"""

from tray.config import (
    API_BASE_URL,
    API_HOST,
    API_PORT,
    CAPTURE_MODES,
    COLOR_ERROR,
    COLOR_IDLE,
    COLOR_RECORDING,
    COLOR_SYNCING,
    HEALTH_CHECK_TIMEOUT,
    ICON_SIZE_DEFAULT,
    ICON_SIZE_MAC,
    PLATFORM,
    STATUS_POLL_INTERVAL,
    get_icon_size,
)


class TestConstants:
    """Test configuration constants"""

    def test_api_config(self):
        """API configuration should be valid"""
        assert API_HOST == "127.0.0.1"
        assert isinstance(API_PORT, int)
        assert API_PORT > 0
        assert f"http://{API_HOST}:{API_PORT}/api/v1" == API_BASE_URL

    def test_timing_config(self):
        """Timing configuration should be reasonable"""
        assert STATUS_POLL_INTERVAL > 0
        assert HEALTH_CHECK_TIMEOUT > 0

    def test_icon_sizes(self):
        """Icon sizes should be valid tuples"""
        assert isinstance(ICON_SIZE_MAC, tuple)
        assert len(ICON_SIZE_MAC) == 2
        assert all(isinstance(s, int) and s > 0 for s in ICON_SIZE_MAC)

        assert isinstance(ICON_SIZE_DEFAULT, tuple)
        assert len(ICON_SIZE_DEFAULT) == 2
        assert all(isinstance(s, int) and s > 0 for s in ICON_SIZE_DEFAULT)

    def test_colors(self):
        """Colors should be valid RGB tuples"""
        colors = [COLOR_IDLE, COLOR_RECORDING, COLOR_SYNCING, COLOR_ERROR]
        for color in colors:
            assert isinstance(color, tuple)
            assert len(color) == 3
            assert all(0 <= c <= 255 for c in color)

    def test_platform(self):
        """Platform should be one of expected values"""
        assert PLATFORM in ("macos", "windows", "linux")


class TestGetIconSize:
    """Test get_icon_size function"""

    def test_returns_tuple(self):
        """Should return a size tuple"""
        size = get_icon_size()
        assert isinstance(size, tuple)
        assert len(size) == 2
        assert all(isinstance(s, int) and s > 0 for s in size)

    def test_platform_specific_size(self):
        """Should return platform-specific size"""
        size = get_icon_size()
        if PLATFORM == "macos":
            assert size == ICON_SIZE_MAC
        else:
            assert size == ICON_SIZE_DEFAULT


class TestCaptureModes:
    """Test capture modes configuration"""

    def test_capture_modes_exist(self):
        """Expected capture modes should exist"""
        expected_modes = ["normal", "games", "fast", "presentation", "video", "coding"]
        for mode in expected_modes:
            assert mode in CAPTURE_MODES

    def test_capture_modes_is_list(self):
        """Capture modes should be a list of strings"""
        assert isinstance(CAPTURE_MODES, list)
        for mode in CAPTURE_MODES:
            assert isinstance(mode, str)
            assert len(mode) > 0
