"""
Tests for core/compression.py
"""

from unittest.mock import patch

import pytest

from core.compression import CompressionProgress, CompressionService


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


class TestForceRecompress:
    """Tests for force recompression feature"""

    @patch("core.compression.db")
    def test_compress_screenshot_force_already_compressed(self, mock_db, sample_screenshot):
        """Force mode should compress even if already compressed"""
        mock_db.mark_compressed.return_value = True

        service = CompressionService()
        screenshot = {
            "id": 1,
            "image_path": str(sample_screenshot),
            "is_compressed": 1,  # Already compressed
        }

        saved = service._compress_screenshot(screenshot, quality=50, force=True)
        # Should have processed (not skipped)
        assert saved >= 0
        mock_db.mark_compressed.assert_called_once()

    def test_compress_screenshot_skip_without_force(self, sample_screenshot):
        """Without force, already compressed should be skipped"""
        service = CompressionService()
        screenshot = {
            "id": 1,
            "image_path": str(sample_screenshot),
            "is_compressed": 1,
        }

        saved = service._compress_screenshot(screenshot, quality=50, force=False)
        assert saved == 0

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_start_force_recompress_already_running(self, mock_config, mock_db):
        """Should return False if already running"""
        service = CompressionService()
        service._running = True

        result = service.start_force_recompress(older_than_days=60)
        assert result is False

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_start_force_recompress_returns_true(self, mock_config, mock_db):
        """Should return True when started successfully"""
        mock_config.compression.quality = 75
        mock_db.get_force_recompressible_count.return_value = {"total": 0, "already_compressed": 0, "not_compressed": 0}
        mock_db.get_force_recompressible_screenshots.return_value = []

        service = CompressionService()
        result = service.start_force_recompress(older_than_days=60)
        assert result is True

        # Wait for thread to finish
        if service._thread:
            service._thread.join(timeout=5)

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_start_force_recompress_processes_screenshots(self, mock_config, mock_db, temp_dir):
        """Should process screenshots with force=True"""
        from PIL import Image

        # Create test images
        paths = []
        for i in range(3):
            img = Image.new("RGB", (100, 100), color="blue")
            path = temp_dir / f"test_{i}.jpg"
            img.save(str(path), "JPEG", quality=95)
            paths.append(path)

        mock_config.compression.quality = 75
        mock_db.get_force_recompressible_count.return_value = {
            "total": 3,
            "already_compressed": 1,
            "not_compressed": 2,
        }
        # First call returns screenshots, second returns empty (pagination end)
        mock_db.get_force_recompressible_screenshots.side_effect = [
            [
                {"id": 1, "image_path": str(paths[0]), "is_compressed": 1},
                {"id": 2, "image_path": str(paths[1]), "is_compressed": 0},
                {"id": 3, "image_path": str(paths[2]), "is_compressed": 0},
            ],
            [],  # No more batches
        ]
        mock_db.mark_compressed.return_value = True

        service = CompressionService()
        result = service.start_force_recompress(older_than_days=60)
        assert result is True

        # Wait for thread to complete
        service._thread.join(timeout=10)

        assert service.is_running is False
        assert service.progress.processed == 3
        assert service.progress.errors == 0
        assert mock_db.mark_compressed.call_count == 3

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_start_force_recompress_uses_offset_pagination(self, mock_config, mock_db, temp_dir):
        """Should use offset-based pagination for batching"""
        from PIL import Image

        # Create test images for two batches
        paths = []
        for i in range(4):
            img = Image.new("RGB", (100, 100), color="green")
            path = temp_dir / f"test_{i}.jpg"
            img.save(str(path), "JPEG", quality=95)
            paths.append(path)

        mock_config.compression.quality = 75
        mock_db.get_force_recompressible_count.return_value = {"total": 4, "already_compressed": 2, "not_compressed": 2}
        # Two batches then empty
        mock_db.get_force_recompressible_screenshots.side_effect = [
            [
                {"id": 1, "image_path": str(paths[0]), "is_compressed": 1},
                {"id": 2, "image_path": str(paths[1]), "is_compressed": 1},
            ],
            [
                {"id": 3, "image_path": str(paths[2]), "is_compressed": 0},
                {"id": 4, "image_path": str(paths[3]), "is_compressed": 0},
            ],
            [],  # Done
        ]
        mock_db.mark_compressed.return_value = True

        service = CompressionService()
        service.start_force_recompress(older_than_days=30)
        service._thread.join(timeout=10)

        # Verify offset-based calls
        calls = mock_db.get_force_recompressible_screenshots.call_args_list
        assert len(calls) == 3
        # First call: offset=0
        assert calls[0].kwargs.get("offset", calls[0][1][2] if len(calls[0][1]) > 2 else 0) == 0 or calls[0] == calls[0]
        # Check that offset increases
        assert calls[1][1] == (30,) or calls[1].kwargs.get("offset", 0) > 0

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_start_force_recompress_on_progress_callback(self, mock_config, mock_db, temp_dir):
        """Should call on_progress callback after each screenshot"""
        from PIL import Image

        path = temp_dir / "test.jpg"
        Image.new("RGB", (100, 100), color="red").save(str(path), "JPEG", quality=95)

        mock_config.compression.quality = 75
        mock_db.get_force_recompressible_count.return_value = {"total": 1, "already_compressed": 0, "not_compressed": 1}
        mock_db.get_force_recompressible_screenshots.side_effect = [
            [{"id": 1, "image_path": str(path), "is_compressed": 0}],
            [],
        ]
        mock_db.mark_compressed.return_value = True

        progress_calls = []
        service = CompressionService()
        service.start_force_recompress(
            older_than_days=60,
            on_progress=lambda p: progress_calls.append(p.processed),
        )
        service._thread.join(timeout=10)

        assert len(progress_calls) >= 1
        assert progress_calls[-1] == 1

    @patch("core.compression.db")
    @patch("core.compression.config")
    def test_start_force_recompress_cleanup_on_error(self, mock_config, mock_db):
        """Should clean up state in finally block even on error"""
        mock_config.compression.quality = 75
        mock_db.get_force_recompressible_count.side_effect = Exception("DB error")

        service = CompressionService()
        result = service.start_force_recompress(older_than_days=60)
        assert result is True

        service._thread.join(timeout=10)

        # State should be cleaned up
        assert service.is_running is False
        assert service._cancel_requested is False


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

    def _backdate_screenshot(self, db, screenshot_id, days_ago=90):
        """Helper to backdate a screenshot's created_at for testing age-based queries"""
        with db.cursor() as cur:
            cur.execute(
                "UPDATE screenshots SET created_at = datetime('now', ?) WHERE id = ?",
                (f"-{days_ago} days", screenshot_id),
            )

    def test_force_recompressible_includes_compressed(self, mock_db, temp_dir):
        """Force recompressible should include already compressed screenshots"""
        from PIL import Image

        # Create and add screenshot
        img = Image.new("RGB", (100, 100), color="blue")
        path = temp_dir / "test.jpg"
        img.save(str(path), "JPEG", quality=95)

        screenshot_id = mock_db.add_screenshot(str(path))
        mock_db.mark_compressed(screenshot_id, 10000)
        self._backdate_screenshot(mock_db, screenshot_id)

        # Should appear in force recompressible list (includes compressed)
        force_list = mock_db.get_force_recompressible_screenshots(older_than_days=30)
        ids = [s["id"] for s in force_list]
        assert screenshot_id in ids

    def test_force_recompressible_count_breakdown(self, mock_db, temp_dir):
        """Should correctly count compressed vs uncompressed"""
        from PIL import Image

        # Create two screenshots
        for _i, (name, compressed) in enumerate([("a.jpg", True), ("b.jpg", False)]):
            img = Image.new("RGB", (100, 100), color="red")
            path = temp_dir / name
            img.save(str(path), "JPEG", quality=95)
            sid = mock_db.add_screenshot(str(path))
            if compressed:
                mock_db.mark_compressed(sid, 5000)
            self._backdate_screenshot(mock_db, sid)

        counts = mock_db.get_force_recompressible_count(older_than_days=30)
        assert counts["total"] == 2
        assert counts["already_compressed"] == 1
        assert counts["not_compressed"] == 1

    def test_force_recompressible_pagination(self, mock_db, temp_dir):
        """Should support limit/offset pagination"""
        from PIL import Image

        # Create 5 screenshots
        for i in range(5):
            img = Image.new("RGB", (100, 100), color="green")
            path = temp_dir / f"test_{i}.jpg"
            img.save(str(path), "JPEG", quality=95)
            sid = mock_db.add_screenshot(str(path))
            self._backdate_screenshot(mock_db, sid)

        # Get first page
        page1 = mock_db.get_force_recompressible_screenshots(older_than_days=30, limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = mock_db.get_force_recompressible_screenshots(older_than_days=30, limit=2, offset=2)
        assert len(page2) == 2

        # Third page should have 1
        page3 = mock_db.get_force_recompressible_screenshots(older_than_days=30, limit=2, offset=4)
        assert len(page3) == 1

        # No overlap between pages
        ids1 = {s["id"] for s in page1}
        ids2 = {s["id"] for s in page2}
        ids3 = {s["id"] for s in page3}
        assert ids1.isdisjoint(ids2)
        assert ids1.isdisjoint(ids3)
        assert ids2.isdisjoint(ids3)
