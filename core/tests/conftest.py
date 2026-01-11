"""
Core module test fixtures
"""

import sys

import pytest

# macOS CI runners have SQLite without extension loading support
# Skip database tests that require sqlite-vec on macOS CI
_is_macos_ci = sys.platform == "darwin" and "CI" in __import__("os").environ

requires_sqlite_extensions = pytest.mark.skipif(
    _is_macos_ci,
    reason="macOS CI runners don't support SQLite extension loading",
)


@pytest.fixture
def mock_db(temp_dir):
    """Create a mock database for testing.

    Note: This fixture requires sqlite-vec extension which may not be available
    on all platforms (e.g., macOS CI runners).
    """
    if _is_macos_ci:
        pytest.skip("macOS CI runners don't support SQLite extension loading")

    from core.database import Database

    db_path = temp_dir / "test.db"
    db = Database(db_path)
    db.connect()
    yield db
    db.disconnect()


@pytest.fixture
def sample_screenshot(temp_dir):
    """Create a sample screenshot file for testing"""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    img_path = temp_dir / "test_screenshot.jpg"
    img.save(str(img_path), "JPEG", quality=95)
    return img_path


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    from core.config import CaptureSettings, CompressionSettings, Config

    return Config(
        capture=CaptureSettings(
            mode="normal",
            interval=2.0,
            threshold=0.9,
            save_threshold=0.6,
            quality=95,
        ),
        compression=CompressionSettings(
            enabled=False,
            after_days=60,
            quality=85,
        ),
    )
