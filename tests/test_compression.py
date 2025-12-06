"""
Tests for core/compression.py
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from core.compression import CompressionService, CompressionProgress


class TestCompressionProgress:
    """Test CompressionProgress dataclass"""

    def test_percent_zero_total(self):
        """Should return 100% when total is 0"""
        progress = CompressionProgress(total=0, processed=0)
        assert progress.percent == 100.0

    def test_percent_calculation(self):
        """Should calculate percentage correctly"""
        progress = CompressionProgress(total=10, processed=5)
        assert progress.percent == 50.0

    def test_bytes_saved_tracking(self):
        """Should track bytes saved"""
        progress = CompressionProgress(bytes_saved=1024)
        assert progress.bytes_saved == 1024


class TestCompressionService:
    """Test CompressionService class"""

    def test_initial_state(self):
        """Service should start in non-running state"""
        service = CompressionService()
        assert service.is_running is False
        assert service.progress.is_running is False

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_start_already_running(self, mock_config, mock_db):
        """Should not start if already running"""
        service = CompressionService()
        service._running = True

        service.start()  # Should return early

        mock_db.get_compressible_count.assert_not_called()

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_stop(self, mock_config, mock_db):
        """Should stop compression"""
        service = CompressionService()
        service._running = True

        service.stop()

        assert service._cancel_requested is True
        assert service._running is False

    def test_compress_screenshot_file_not_found(self, temp_dir):
        """Should raise error for missing file"""
        service = CompressionService()
        screenshot = {
            "id": 1,
            "image_path": str(temp_dir / "nonexistent.jpg"),
            "is_compressed": 0,
        }

        with pytest.raises(FileNotFoundError):
            service._compress_screenshot(screenshot, quality=85)

    def test_compress_screenshot_already_compressed(self, sample_screenshot):
        """Should skip already compressed screenshots"""
        service = CompressionService()
        screenshot = {
            "id": 1,
            "image_path": str(sample_screenshot),
            "is_compressed": 1,  # Already compressed
        }

        saved = service._compress_screenshot(screenshot, quality=85)
        assert saved == 0

    @patch("core.compression.db")
    def test_compress_screenshot_success(self, mock_db, sample_screenshot):
        """Should compress and update database"""
        mock_db.mark_compressed.return_value = True

        service = CompressionService()
        screenshot = {
            "id": 1,
            "image_path": str(sample_screenshot),
            "is_compressed": 0,
        }

        # Get original size
        original_size = sample_screenshot.stat().st_size

        saved = service._compress_screenshot(screenshot, quality=50)

        # Should have saved some bytes (lower quality)
        assert saved >= 0
        mock_db.mark_compressed.assert_called_once()

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_compress_now_empty(self, mock_config, mock_db):
        """Should handle no compressible screenshots"""
        mock_config.compression.after_days = 60
        mock_config.compression.quality = 85
        mock_db.get_compressible_screenshots.return_value = []

        service = CompressionService()
        result = service.compress_now()

        assert result.total == 0
        assert result.processed == 0
        assert result.is_running is False

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_compress_now_with_screenshots(self, mock_config, mock_db, temp_dir):
        """Should compress all eligible screenshots"""
        from PIL import Image

        # Create test images
        paths = []
        for i in range(2):
            img = Image.new("RGB", (100, 100), color="blue")
            path = temp_dir / f"test_{i}.jpg"
            img.save(str(path), "JPEG", quality=95)
            paths.append(path)

        mock_config.compression.after_days = 60
        mock_config.compression.quality = 85
        mock_db.get_compressible_screenshots.return_value = [
            {"id": 1, "image_path": str(paths[0]), "is_compressed": 0},
            {"id": 2, "image_path": str(paths[1]), "is_compressed": 0},
        ]
        mock_db.mark_compressed.return_value = True

        service = CompressionService()
        result = service.compress_now()

        assert result.total == 2
        assert result.processed == 2
        assert result.errors == 0
        assert mock_db.mark_compressed.call_count == 2


class TestCompressionIntegration:
    """Integration tests for compression with real database"""

    def test_compression_prevents_recompression(self, mock_db, temp_dir):
        """Once compressed, screenshot should not be compressed again"""
        from PIL import Image

        # Create and add screenshot
        img = Image.new("RGB", (100, 100), color="green")
        path = temp_dir / "test.jpg"
        img.save(str(path), "JPEG", quality=95)

        screenshot_id = mock_db.add_screenshot(str(path))

        # Mark as compressed
        mock_db.mark_compressed(screenshot_id, 10000)

        # Should not appear in compressible list
        compressible = mock_db.get_compressible_screenshots(older_than_days=0)
        ids = [s["id"] for s in compressible]
        assert screenshot_id not in ids
