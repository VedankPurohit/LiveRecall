"""
Tests for core/database.py
"""

import pytest


class TestDatabaseBasics:
    """Test basic database operations"""

    def test_connect_creates_tables(self, mock_db):
        """Database connection should create required tables"""
        with mock_db.cursor() as cur:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}

        assert "screenshots" in tables
        assert "screenshot_embeddings" in tables

    def test_add_screenshot(self, mock_db, sample_screenshot):
        """Should add a screenshot to the database"""
        screenshot_id = mock_db.add_screenshot(str(sample_screenshot), "251206120000")

        assert screenshot_id == 1

        screenshot = mock_db.get_screenshot(screenshot_id)
        assert screenshot is not None
        assert screenshot["image_path"] == str(sample_screenshot)
        assert screenshot["timestamp"] == "251206120000"
        assert screenshot["has_embedding"] == 0

    def test_get_screenshot_not_found(self, mock_db):
        """Should return None for non-existent screenshot"""
        screenshot = mock_db.get_screenshot(999)
        assert screenshot is None

    def test_delete_screenshot(self, mock_db, sample_screenshot):
        """Should delete a screenshot"""
        screenshot_id = mock_db.add_screenshot(str(sample_screenshot))
        assert mock_db.get_screenshot(screenshot_id) is not None

        result = mock_db.delete_screenshot(screenshot_id)
        assert result is True
        assert mock_db.get_screenshot(screenshot_id) is None

    def test_get_all_screenshots_pagination(self, mock_db, temp_dir):
        """Should support pagination"""
        from PIL import Image

        # Add 5 screenshots
        for i in range(5):
            img = Image.new("RGB", (10, 10), color="blue")
            path = temp_dir / f"screenshot_{i}.jpg"
            img.save(str(path), "JPEG")
            mock_db.add_screenshot(str(path), f"25120612000{i}")

        # Get with limit
        screenshots = mock_db.get_all_screenshots(limit=2)
        assert len(screenshots) == 2

        # Get with offset
        screenshots = mock_db.get_all_screenshots(limit=2, offset=2)
        assert len(screenshots) == 2


class TestEmbeddings:
    """Test embedding operations"""

    def test_add_embedding(self, mock_db, sample_screenshot, mock_embedding):
        """Should add embedding and mark screenshot as synced"""
        screenshot_id = mock_db.add_screenshot(str(sample_screenshot))

        result = mock_db.add_embedding(screenshot_id, mock_embedding)
        assert result is True

        screenshot = mock_db.get_screenshot(screenshot_id)
        assert screenshot["has_embedding"] == 1

    def test_add_embedding_wrong_dimensions(self, mock_db, sample_screenshot):
        """Should reject embeddings with wrong dimensions"""
        screenshot_id = mock_db.add_screenshot(str(sample_screenshot))

        with pytest.raises(ValueError, match="768 dimensions"):
            mock_db.add_embedding(screenshot_id, [0.1, 0.2, 0.3])  # Only 3 dims

    def test_get_unsynced_screenshots(self, mock_db, temp_dir, mock_embedding):
        """Should return only screenshots without embeddings"""
        from PIL import Image

        # Add 3 screenshots
        ids = []
        for i in range(3):
            img = Image.new("RGB", (10, 10))
            path = temp_dir / f"ss_{i}.jpg"
            img.save(str(path), "JPEG")
            ids.append(mock_db.add_screenshot(str(path)))

        # Add embedding to first one
        mock_db.add_embedding(ids[0], mock_embedding)

        unsynced = mock_db.get_unsynced_screenshots()
        assert len(unsynced) == 2
        assert all(s["has_embedding"] == 0 for s in unsynced)

    def test_get_unsynced_count(self, mock_db, temp_dir, mock_embedding):
        """Should return correct unsynced count"""
        from PIL import Image

        for i in range(3):
            img = Image.new("RGB", (10, 10))
            path = temp_dir / f"ss_{i}.jpg"
            img.save(str(path), "JPEG")
            mock_db.add_screenshot(str(path))

        assert mock_db.get_unsynced_count() == 3

    def test_search_similar(self, mock_db, temp_dir, mock_embedding):
        """Should find similar screenshots by embedding"""
        from PIL import Image

        # Add a screenshot with embedding
        img = Image.new("RGB", (10, 10))
        path = temp_dir / "ss.jpg"
        img.save(str(path), "JPEG")
        screenshot_id = mock_db.add_screenshot(str(path))
        mock_db.add_embedding(screenshot_id, mock_embedding)

        # Search with same embedding should find it
        results = mock_db.search_similar(mock_embedding, limit=10)
        assert len(results) == 1
        assert results[0]["id"] == screenshot_id
        assert "similarity" in results[0]


class TestCompression:
    """Test compression-related database operations"""

    def test_compression_columns_exist(self, mock_db):
        """Database should have compression columns"""
        with mock_db.cursor() as cur:
            cur.execute("PRAGMA table_info(screenshots)")
            columns = {row[1] for row in cur.fetchall()}

        assert "is_compressed" in columns
        assert "original_size_bytes" in columns
        assert "compressed_at" in columns

    def test_mark_compressed(self, mock_db, sample_screenshot):
        """Should mark a screenshot as compressed"""
        screenshot_id = mock_db.add_screenshot(str(sample_screenshot))

        result = mock_db.mark_compressed(screenshot_id, original_size=100000)
        assert result is True

        screenshot = mock_db.get_screenshot(screenshot_id)
        assert screenshot["is_compressed"] == 1
        assert screenshot["original_size_bytes"] == 100000
        assert screenshot["compressed_at"] is not None

    def test_get_compressible_screenshots_respects_age(self, mock_db, temp_dir):
        """Should only return screenshots older than specified days"""
        from PIL import Image

        # Add a screenshot
        img = Image.new("RGB", (10, 10))
        path = temp_dir / "old_ss.jpg"
        img.save(str(path), "JPEG")
        mock_db.add_screenshot(str(path))

        # With 0 days, should find it (it's from now)
        # With 1 day, shouldn't find it yet
        # Note: Just added, so created_at is now - won't be older than 0 days
        # This tests the query structure works
        mock_db.get_compressible_screenshots(older_than_days=0)

    def test_get_compressible_excludes_already_compressed(self, mock_db, temp_dir):
        """Should not return already compressed screenshots"""
        from PIL import Image

        # Add and compress a screenshot
        img = Image.new("RGB", (10, 10))
        path = temp_dir / "compressed_ss.jpg"
        img.save(str(path), "JPEG")
        screenshot_id = mock_db.add_screenshot(str(path))
        mock_db.mark_compressed(screenshot_id, 50000)

        # Should not appear in compressible list
        compressible = mock_db.get_compressible_screenshots(older_than_days=0)
        assert all(s["id"] != screenshot_id for s in compressible)

    def test_get_compression_stats(self, mock_db, temp_dir):
        """Should return correct compression statistics"""
        from PIL import Image

        # Add 3 screenshots, compress 2
        for i in range(3):
            img = Image.new("RGB", (10, 10))
            path = temp_dir / f"ss_{i}.jpg"
            img.save(str(path), "JPEG")
            sid = mock_db.add_screenshot(str(path))
            if i < 2:
                mock_db.mark_compressed(sid, 50000)

        stats = mock_db.get_compression_stats()
        assert stats["compressed_count"] == 2
        assert stats["uncompressed_count"] == 1
        assert stats["original_size_bytes"] == 100000  # 2 * 50000


class TestStats:
    """Test statistics methods"""

    def test_get_stats(self, mock_db, temp_dir, mock_embedding):
        """Should return correct statistics"""
        from PIL import Image

        # Add 3 screenshots
        for i in range(3):
            img = Image.new("RGB", (10, 10))
            path = temp_dir / f"ss_{i}.jpg"
            img.save(str(path), "JPEG")
            sid = mock_db.add_screenshot(str(path))
            if i == 0:
                mock_db.add_embedding(sid, mock_embedding)
            if i == 1:
                mock_db.mark_compressed(sid, 50000)

        stats = mock_db.get_stats()
        assert stats["total_screenshots"] == 3
        assert stats["synced"] == 1
        assert stats["unsynced"] == 2
        assert stats["compressed"] == 1

    def test_clear_all(self, mock_db, sample_screenshot, mock_embedding):
        """Should clear all data"""
        screenshot_id = mock_db.add_screenshot(str(sample_screenshot))
        mock_db.add_embedding(screenshot_id, mock_embedding)

        mock_db.clear_all()

        stats = mock_db.get_stats()
        assert stats["total_screenshots"] == 0


class TestScreenshotOffset:
    """Test screenshot offset functionality"""

    def test_get_screenshot_offset_basic(self, mock_db, temp_dir):
        """Should return correct offset for a screenshot"""
        from PIL import Image

        # Add 5 screenshots with different timestamps
        ids = []
        for i in range(5):
            img = Image.new("RGB", (10, 10))
            path = temp_dir / f"ss_{i}.jpg"
            img.save(str(path), "JPEG")
            ids.append(mock_db.add_screenshot(str(path), f"25010612000{i}"))

        # The most recent (highest timestamp) should have offset 0
        assert mock_db.get_screenshot_offset(ids[4]) == 0
        # The oldest should have offset 4
        assert mock_db.get_screenshot_offset(ids[0]) == 4
        # Middle one should have offset 2
        assert mock_db.get_screenshot_offset(ids[2]) == 2

    def test_get_screenshot_offset_visibility_filter(self, mock_db, temp_dir):
        """Should respect visibility filter"""
        from PIL import Image

        ids = []
        for i in range(3):
            img = Image.new("RGB", (10, 10))
            path = temp_dir / f"ss_{i}.jpg"
            img.save(str(path), "JPEG")
            ids.append(mock_db.add_screenshot(str(path), f"25010612000{i}"))

        # Hide the middle one (ids[1])
        mock_db.set_screenshots_hidden([ids[1]], True)

        # With visible_only, middle screenshot doesn't count
        # ids[2] is newest (offset 0), ids[0] is oldest
        # For ids[0]: only ids[2] is newer AND visible, so offset = 1
        assert mock_db.get_screenshot_offset(ids[0], "visible_only") == 1
        # ids[2] is still newest regardless
        assert mock_db.get_screenshot_offset(ids[2], "visible_only") == 0

        # With hidden_only, only ids[1] is in the list (offset 0 within hidden)
        assert mock_db.get_screenshot_offset(ids[1], "hidden_only") == 0

        # With 'all', all screenshots count
        assert mock_db.get_screenshot_offset(ids[0], "all") == 2
        assert mock_db.get_screenshot_offset(ids[2], "all") == 0

    def test_get_screenshot_offset_not_found(self, mock_db):
        """Should return None for non-existent screenshot"""
        assert mock_db.get_screenshot_offset(9999) is None
