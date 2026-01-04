"""
LiveRecall Compression Service
Auto-compress old screenshots to save storage
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from core.config import config
from core.database import db


@dataclass
class CompressionProgress:
    """Progress information for compression operation"""

    total: int = 0
    processed: int = 0
    errors: int = 0
    bytes_saved: int = 0
    is_running: bool = False

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.processed / self.total) * 100


class CompressionService:
    """Service for compressing old screenshots"""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._progress = CompressionProgress()
        self._on_progress: Callable[[CompressionProgress], None] | None = None
        self._cancel_requested = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def progress(self) -> CompressionProgress:
        return self._progress

    def start(
        self,
        older_than_days: int | None = None,
        quality: int | None = None,
        batch_size: int = 20,
        on_progress: Callable[[CompressionProgress], None] | None = None,
    ):
        """Start compressing old screenshots in background"""
        if self._running:
            return

        # Use config defaults if not specified
        if older_than_days is None:
            older_than_days = config.compression.after_days
        if quality is None:
            quality = config.compression.quality

        self._running = True
        self._cancel_requested = False
        self._on_progress = on_progress
        self._thread = threading.Thread(
            target=self._compress_loop, args=(older_than_days, quality, batch_size), daemon=True
        )
        self._thread.start()

    def stop(self):
        """Stop compression"""
        self._cancel_requested = True
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    def _compress_loop(self, older_than_days: int, quality: int, batch_size: int):
        """Background compression loop - processes all eligible then stops"""
        # Get total count upfront
        total_compressible = db.get_compressible_count(older_than_days)

        if total_compressible == 0:
            self._running = False
            self._progress = CompressionProgress(total=0, processed=0, errors=0, is_running=False)
            return

        self._progress = CompressionProgress(
            total=total_compressible, processed=0, errors=0, bytes_saved=0, is_running=True
        )

        print(f"🗜️ Compressing {total_compressible} old screenshots...")

        # Process in batches
        while self._running and not self._cancel_requested:
            # Get next batch
            screenshots = db.get_compressible_screenshots(older_than_days, limit=batch_size)

            if not screenshots:
                # All done
                break

            for screenshot in screenshots:
                if self._cancel_requested:
                    break

                try:
                    saved = self._compress_screenshot(screenshot, quality)
                    self._progress.processed += 1
                    self._progress.bytes_saved += saved
                    print(f"  ✓ {self._progress.processed}/{self._progress.total} (-{saved // 1024}KB)")
                except Exception as e:
                    print(f"  ✗ Error: {screenshot['image_path']}: {e}")
                    self._progress.errors += 1

                if self._on_progress:
                    self._on_progress(self._progress)

        # Mark as complete
        self._running = False
        self._progress.is_running = False
        print(
            f"✅ Compression complete: {self._progress.processed} processed, {self._progress.bytes_saved // 1024}KB saved"
        )

    def _compress_screenshot(self, screenshot: dict, quality: int) -> int:
        """
        Compress a single screenshot.
        Returns bytes saved.
        """
        image_path = Path(screenshot["image_path"])

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Double-check not already compressed (safety)
        if screenshot.get("is_compressed"):
            return 0

        # Get original size
        original_size = image_path.stat().st_size

        # Open and re-save at lower quality
        with Image.open(image_path) as img:
            # Ensure RGB mode for JPEG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Save with lower quality (overwrites original)
            img.save(str(image_path), "JPEG", quality=quality, optimize=True)

        # Get new size
        new_size = image_path.stat().st_size

        # Update database
        db.mark_compressed(screenshot["id"], original_size)

        return original_size - new_size

    def compress_now(
        self,
        older_than_days: int | None = None,
        quality: int | None = None,
    ) -> CompressionProgress:
        """
        Synchronously compress all eligible screenshots (blocking).
        For use in CLI or testing.
        """
        if older_than_days is None:
            older_than_days = config.compression.after_days
        if quality is None:
            quality = config.compression.quality

        screenshots = db.get_compressible_screenshots(older_than_days)

        self._progress = CompressionProgress(
            total=len(screenshots), processed=0, errors=0, bytes_saved=0, is_running=True
        )

        for screenshot in screenshots:
            try:
                saved = self._compress_screenshot(screenshot, quality)
                self._progress.processed += 1
                self._progress.bytes_saved += saved
            except Exception as e:
                print(f"Error compressing {screenshot['image_path']}: {e}")
                self._progress.errors += 1

        self._progress.is_running = False
        return self._progress


# Global compression service instance
compression_service = CompressionService()


if __name__ == "__main__":
    from core.database import db

    db.connect()

    print("Compression settings:")
    print(f"  Enabled: {config.compression.enabled}")
    print(f"  After days: {config.compression.after_days}")
    print(f"  Quality: {config.compression.quality}")

    compressible = db.get_compressible_count(config.compression.after_days)
    print(f"\nCompressible screenshots: {compressible}")

    if compressible > 0:
        print("\nStarting compression...")
        result = compression_service.compress_now()
        print("\nDone!")
        print(f"  Processed: {result.processed}")
        print(f"  Errors: {result.errors}")
        print(f"  Bytes saved: {result.bytes_saved:,}")

    db.disconnect()
