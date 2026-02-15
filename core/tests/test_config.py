"""
Tests for core/config.py
"""

from pathlib import Path


class TestPlatformDetection:
    """Test platform detection"""

    def test_platform_is_valid(self):
        """Platform should be one of the expected values"""
        from core.config import PLATFORM

        assert PLATFORM in ("macos", "windows", "linux")


class TestPaths:
    """Test path functions"""

    def test_get_data_dir_exists(self):
        """Data directory should be created"""
        from core.config import get_data_dir

        data_dir = get_data_dir()
        assert isinstance(data_dir, Path)
        assert data_dir.exists()

    def test_get_screenshots_dir_exists(self):
        """Screenshots directory should be created"""
        from core.config import get_screenshots_dir

        screenshots_dir = get_screenshots_dir()
        assert isinstance(screenshots_dir, Path)
        assert screenshots_dir.exists()
        assert screenshots_dir.parent.name == "LiveRecall"

    def test_get_database_path(self):
        """Database path should be in data directory"""
        from core.config import get_data_dir, get_database_path

        db_path = get_database_path()
        assert isinstance(db_path, Path)
        assert db_path.parent == get_data_dir()
        assert db_path.name == "liverecall.db"


class TestCaptureSettings:
    """Test CaptureSettings dataclass"""

    def test_default_values(self):
        """Should have sensible defaults"""
        from core.config import CaptureSettings

        settings = CaptureSettings()
        assert settings.mode == "normal"
        assert settings.interval == 2.0
        assert settings.threshold == 0.9
        assert settings.save_threshold == 0.6
        assert settings.quality == 95

    def test_set_mode_valid(self):
        """Should apply mode presets"""
        from core.config import CaptureSettings

        settings = CaptureSettings()
        settings.set_mode("games")

        assert settings.mode == "games"
        assert settings.threshold == 0.75
        assert settings.interval == 4

    def test_set_mode_invalid(self):
        """Should ignore invalid modes"""
        from core.config import CaptureSettings

        settings = CaptureSettings()
        original_threshold = settings.threshold

        settings.set_mode("invalid_mode")

        # Should not change
        assert settings.threshold == original_threshold

    def test_all_modes_exist(self):
        """All documented modes should exist"""
        from core.config import CaptureSettings

        expected_modes = ["normal", "games", "fast", "presentation", "video", "coding", "security", "timelapse"]

        for mode in expected_modes:
            assert mode in CaptureSettings.MODES


class TestCompressionSettings:
    """Test CompressionSettings dataclass"""

    def test_default_values(self):
        """Should have sensible defaults"""
        from core.config import CompressionSettings

        settings = CompressionSettings()
        assert settings.enabled is False  # Off by default
        assert settings.after_days == 60
        assert settings.quality == 75

    def test_quality_range(self):
        """Quality should be reasonable"""
        from core.config import CompressionSettings

        settings = CompressionSettings()
        assert 50 <= settings.quality <= 100


class TestConfig:
    """Test main Config class"""

    def test_default_config(self):
        """Should have all required sections"""
        from core.config import Config

        config = Config()
        assert hasattr(config, "capture")
        assert hasattr(config, "compression")
        assert hasattr(config, "encryption_enabled")
        assert hasattr(config, "safe_mode_enabled")
        assert hasattr(config, "safe_mode_level")

    def test_path_properties(self):
        """Should have path properties"""
        from core.config import Config

        config = Config()
        assert isinstance(config.data_dir, Path)
        assert isinstance(config.screenshots_dir, Path)
        assert isinstance(config.database_path, Path)

    def test_global_config_instance(self):
        """Global config instance should exist"""
        from core.config import config

        assert config is not None
        assert hasattr(config, "capture")
        assert hasattr(config, "compression")
