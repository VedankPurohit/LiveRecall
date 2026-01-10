"""
Tests for tray/icons.py
"""

import sys

from PIL import Image

from tray.config import ICON_SIZE_DEFAULT, ICON_SIZE_MAC, get_icon_size
from tray.icons import create_app_icon, get_app_icon

IS_WINDOWS = sys.platform == "win32"


class TestCreateAppIcon:
    """Test create_app_icon function"""

    def test_creates_image(self):
        """Should create a PIL Image"""
        icon = create_app_icon()
        assert isinstance(icon, Image.Image)

    def test_default_size(self):
        """Should use platform default size when no size specified"""
        icon = create_app_icon()
        expected_size = get_icon_size()
        assert icon.size == expected_size

    def test_custom_size(self):
        """Should respect custom size"""
        custom_size = (64, 64)
        icon = create_app_icon(size=custom_size)
        assert icon.size == custom_size

    def test_rgba_mode(self):
        """Should create RGBA image for transparency"""
        icon = create_app_icon()
        assert icon.mode == "RGBA"

    def test_mac_size(self):
        """Should work with Mac icon size"""
        icon = create_app_icon(size=ICON_SIZE_MAC)
        assert icon.size == ICON_SIZE_MAC

    def test_default_platform_size(self):
        """Should work with default platform size"""
        icon = create_app_icon(size=ICON_SIZE_DEFAULT)
        assert icon.size == ICON_SIZE_DEFAULT

    def test_various_sizes(self):
        """Should handle various icon sizes"""
        sizes = [(16, 16), (22, 22), (32, 32), (48, 48), (64, 64)]
        for size in sizes:
            icon = create_app_icon(size=size)
            assert icon.size == size


class TestGetAppIcon:
    """Test get_app_icon function"""

    def test_returns_image(self):
        """Should return a PIL Image"""
        icon = get_app_icon()
        assert isinstance(icon, Image.Image)

    def test_has_correct_size(self):
        """Should have platform-appropriate size"""
        icon = get_app_icon()
        expected_size = get_icon_size()
        assert icon.size == expected_size

    def test_is_rgba(self):
        """Should be RGBA on macOS/Linux, RGB on Windows"""
        icon = get_app_icon()
        # Windows converts to RGB with solid background for better tray visibility
        expected_mode = "RGB" if IS_WINDOWS else "RGBA"
        assert icon.mode == expected_mode
