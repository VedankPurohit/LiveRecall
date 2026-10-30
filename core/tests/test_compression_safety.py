"""Exercise compression against real image files and database transactions."""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw

from core.compression import CompressionService


def screenshot(mock_db, temp_dir):
    path = temp_dir / "capture.jpg"
    image = Image.new("RGB", (800, 500), "white")
    # Deterministic edges resemble a text screenshot without private content.
    draw = ImageDraw.Draw(image)
    for y in range(10, 490, 15):
        draw.text((10, y), "Storage safety regression 0123456789 " * 3, fill="black")
    image.save(path, "JPEG", quality=95)
    sid = mock_db.add_screenshot(str(path), "260101120000")
    return mock_db.get_screenshot(sid), path


def test_encoder_failure_preserves_original(mock_db, temp_dir):
    row, path = screenshot(mock_db, temp_dir)
    before = path.read_bytes()

    def fail_after_write(image, target, *args, **kwargs):
        # Pillow can write bytes before disk-full or another encoder failure.
        if hasattr(target, "write"):
            target.write(b"partial")
        else:
            Path(target).write_bytes(b"partial")
        raise OSError("disk full")

    with (
        patch("core.compression.db", mock_db),
        patch.object(Image.Image, "save", fail_after_write),
        pytest.raises(OSError, match="disk full"),
    ):
        CompressionService()._compress_screenshot(row, 85)
    assert path.read_bytes() == before
    assert mock_db.get_screenshot(row["id"])["is_compressed"] == 0
    assert list(temp_dir.glob("*.jpg")) == [path]


def test_webp_updates_path_and_keeps_search_metadata(mock_db, temp_dir):
    row, original = screenshot(mock_db, temp_dir)
    with patch("core.compression.db", mock_db):
        saved = CompressionService()._compress_screenshot(row, 85, image_format="webp")
    updated = mock_db.get_screenshot(row["id"])
    target = Path(updated["image_path"])
    assert saved > 0
    assert target.suffix == ".webp"
    with Image.open(target) as image:
        assert image.format == "WEBP"
        assert image.size == (800, 500)
    assert not original.exists()
    assert updated["timestamp"] == row["timestamp"]
    assert updated["has_embedding"] == row["has_embedding"]
    assert updated["has_ocr"] == row["has_ocr"]


def test_failed_database_commit_preserves_original(mock_db, temp_dir):
    row, path = screenshot(mock_db, temp_dir)
    before = path.read_bytes()
    with (
        patch("core.compression.db", mock_db),
        patch.object(mock_db, "mark_compressed", side_effect=RuntimeError("commit failed")),
        pytest.raises(RuntimeError, match="commit failed"),
    ):
        CompressionService()._compress_screenshot(row, 75)
    assert path.read_bytes() == before
    assert mock_db.get_screenshot(row["id"])["image_path"] == str(path)
    assert len(list(temp_dir.glob("*.jpg"))) == 1


def test_compression_never_grows_a_file(mock_db, temp_dir):
    path = temp_dir / "small.jpg"
    Image.new("RGB", (100, 100), "white").save(path, "JPEG", quality=1, optimize=True)
    sid = mock_db.add_screenshot(str(path), "260101120000")
    before = path.read_bytes()
    with patch("core.compression.db", mock_db):
        saved = CompressionService()._compress_screenshot(mock_db.get_screenshot(sid), 95)
    assert saved == 0
    assert path.read_bytes() == before
    assert mock_db.get_screenshot(sid)["is_compressed"] == 1


def test_worker_passes_missing_images_and_finishes(mock_db, temp_dir):
    missing = mock_db.add_screenshot(str(temp_dir / "missing.jpg"), "260101120000")
    row, _ = screenshot(mock_db, temp_dir)
    with mock_db.cursor() as cursor:
        cursor.execute("UPDATE screenshots SET created_at = '2020-01-01'")
    service = CompressionService()
    service._running = True
    with patch("core.compression.db", mock_db):
        service._compress_loop(30, 75, 1)
    assert not service.is_running
    assert service.progress.errors == 1
    assert service.progress.processed == 1
    assert mock_db.get_screenshot(missing)["is_compressed"] == 0
    assert mock_db.get_screenshot(row["id"])["is_compressed"] == 1


def test_worker_resets_running_after_database_error():
    service = CompressionService()
    service._running = True
    with patch("core.compression.db") as database:
        database.get_compressible_count.side_effect = RuntimeError("unavailable")
        service._compress_loop(30, 75, 1)
    assert not service.is_running
    assert service.progress.errors == 1


def test_recompression_preserves_original_size(mock_db, temp_dir):
    row, _ = screenshot(mock_db, temp_dir)
    with patch("core.compression.db", mock_db):
        service = CompressionService()
        service._compress_screenshot(row, 85)
        once = mock_db.get_screenshot(row["id"])
        service._compress_screenshot(once, 70, force=True)
    twice = mock_db.get_screenshot(row["id"])
    assert twice["original_size_bytes"] == once["original_size_bytes"]


def test_directory_sync_failure_prevents_database_change(mock_db, temp_dir):
    row, path = screenshot(mock_db, temp_dir)
    before = path.read_bytes()
    with (
        patch("core.compression.db", mock_db),
        patch("core.compression._sync_directory", side_effect=OSError("directory sync failed")),
        pytest.raises(OSError, match="directory sync failed"),
    ):
        CompressionService()._compress_screenshot(row, 85, image_format="webp")
    assert path.read_bytes() == before
    assert mock_db.get_screenshot(row["id"])["image_path"] == str(path)
    assert not list(temp_dir.glob("*.webp"))


def test_database_path_changes_only_after_directory_sync(mock_db, temp_dir):
    from core.compression import _sync_directory

    row, _ = screenshot(mock_db, temp_dir)
    events = []
    mark_compressed = mock_db.mark_compressed

    def sync(path):
        _sync_directory(path)
        events.append("directory synced")

    def mark(*args, **kwargs):
        assert events == ["directory synced"]
        return mark_compressed(*args, **kwargs)

    with (
        patch("core.compression.db", mock_db),
        patch("core.compression._sync_directory", sync),
        patch.object(mock_db, "mark_compressed", mark),
    ):
        CompressionService()._compress_screenshot(row, 85, image_format="webp")


def test_timeline_and_storage_use_database_timestamp_after_conversion(mock_db, temp_dir):
    from datetime import datetime

    from api.routes.analytics import get_storage_analytics

    row, _ = screenshot(mock_db, temp_dir)
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    with mock_db.cursor() as cursor:
        cursor.execute("UPDATE screenshots SET timestamp = ?", (timestamp,))
    with patch("core.compression.db", mock_db):
        CompressionService()._compress_screenshot(row, 85, image_format="webp")
    updated = mock_db.get_all_screenshots()[0]
    assert ".compressed-" in updated["image_path"]
    assert updated["timestamp"] == timestamp
    assert mock_db.get_date_range() == {"min_date": timestamp, "max_date": timestamp}
    with (
        patch("api.routes.analytics.db", mock_db),
        patch("api.routes.analytics.get_screenshots_dir", return_value=temp_dir),
    ):
        storage = get_storage_analytics(days=30)
    assert storage["largest_files"][0]["timestamp"] == timestamp
    assert storage["largest_files"][0]["size_bytes"] == Path(updated["image_path"]).stat().st_size


def test_clip_loader_decodes_webp_without_loading_a_model(temp_dir):
    import numpy as np

    from core.embeddings import get_image_embedding

    path = temp_dir / "Snap-260101120000.compressed-test.webp"
    Image.new("RGB", (64, 64), "white").save(path, "WEBP")

    class Model:
        def encode(self, image, **kwargs):
            image.load()
            assert image.format == "WEBP"
            assert image.size == (64, 64)
            return np.array([1.0, 0.0])

    with patch("core.embeddings._load_model", return_value=Model()):
        assert get_image_embedding(str(path)) == [1.0, 0.0]
