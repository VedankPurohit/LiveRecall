"""
LiveRecall Compression Service
Auto-compress old screenshots to save storage
"""

import logging
import os
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from core.config import config
from core.database import db

logger = logging.getLogger(__name__)


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
        image_format: str = "jpeg",
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
            target=self._compress_loop, args=(older_than_days, quality, batch_size, image_format), daemon=True
        )
        self._thread.start()

    def stop(self):
        """Stop compression"""
        self._cancel_requested = True
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    def _compress_loop(self, older_than_days: int, quality: int, batch_size: int, image_format: str = "jpeg"):
        try:
            self._run_batches(older_than_days, quality, batch_size, image_format)
        except Exception:
            self._progress.errors += 1
            logger.exception("Compression worker failed")
        finally:
            self._running = False
            self._progress.is_running = False

    def _run_batches(self, older_than_days: int, quality: int, batch_size: int, image_format: str):
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
        after_id = 0
        while self._running and not self._cancel_requested:
            # Get next batch
            screenshots = db.get_compressible_screenshots(older_than_days, limit=batch_size, after_id=after_id)

            if not screenshots:
                # All done
                break

            for screenshot in screenshots:
                if self._cancel_requested:
                    break

                try:
                    saved = self._compress_screenshot(screenshot, quality, image_format=image_format)
                    self._progress.processed += 1
                    self._progress.bytes_saved += saved
                    print(f"  ✓ {self._progress.processed}/{self._progress.total} (-{saved // 1024}KB)")
                except Exception as e:
                    print(f"  ✗ Error: {screenshot['image_path']}: {e}")
                    self._progress.errors += 1
                finally:
                    # A missing/corrupt file must not trap the worker in the first batch.
                    after_id = screenshot["id"]

                if self._on_progress:
                    self._on_progress(self._progress)

        # Mark as complete
        self._running = False
        self._progress.is_running = False
        print(
            f"✅ Compression complete: {self._progress.processed} processed, {self._progress.bytes_saved // 1024}KB saved"
        )

    def _compress_screenshot(
        self, screenshot: dict, quality: int, force: bool = False, image_format: str = "jpeg"
    ) -> int:
        """
        Compress a single screenshot. Returns bytes saved.

        Args:
            screenshot: Screenshot dict from database
            quality: JPEG quality (1-100)
            force: If True, compress even if already compressed (for force recompression)
            image_format: "jpeg" or opt-in "webp". Existing embeddings and OCR stay intact.
        """
        image_path = Path(screenshot["image_path"])
        if image_format not in ("jpeg", "webp"):
            raise ValueError("image_format must be jpeg or webp")

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Skip already compressed unless force mode
        if screenshot.get("is_compressed") and not force:
            return 0

        # Get original size
        original_size = image_path.stat().st_size

        suffix = ".webp" if image_format == "webp" else ".jpg"
        # Keep the original until a complete, decodable file and committed DB row exist.
        # An interrupted process may leave an extra file, never a truncated original.
        fd, filename = tempfile.mkstemp(prefix=f"{image_path.stem}.compressed-", suffix=suffix, dir=image_path.parent)
        target = Path(filename)
        committed = False
        try:
            with os.fdopen(fd, "wb") as output, Image.open(image_path) as source:
                image = source.convert("RGB")
                options = (
                    {"quality": quality, "method": 4}
                    if image_format == "webp"
                    else {"quality": quality, "optimize": True}
                )
                image.save(output, image_format.upper(), **options)
                output.flush()
                os.fsync(output.fileno())
            with Image.open(target) as verification:
                verification.load()
                if verification.size != image.size:
                    raise ValueError("Compressed image dimensions changed")
            new_size = target.stat().st_size
            if new_size >= original_size:
                # Record the attempt so automatic compression won't retry forever.
                db.mark_compressed(screenshot["id"], original_size)
                return 0
            if not db.mark_compressed(
                screenshot["id"], original_size, image_path=str(target), expected_image_path=str(image_path)
            ):
                raise RuntimeError("Screenshot changed or was deleted during compression")
            committed = True
            try:
                image_path.unlink()
            except OSError:
                # DB already references the durable candidate. Leave the extra original
                # rather than reporting a failed encode and degrading it on retry.
                logger.warning("Could not remove original screenshot after compression", exc_info=True)
            return original_size - new_size
        finally:
            if not committed:
                target.unlink(missing_ok=True)

    def compress_now(
        self,
        older_than_days: int | None = None,
        quality: int | None = None,
        image_format: str = "jpeg",
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
                saved = self._compress_screenshot(screenshot, quality, image_format=image_format)
                self._progress.processed += 1
                self._progress.bytes_saved += saved
            except Exception as e:
                print(f"Error compressing {screenshot['image_path']}: {e}")
                self._progress.errors += 1

        self._progress.is_running = False
        return self._progress

    def start_force_recompress(
        self,
        older_than_days: int,
        quality: int | None = None,
        on_progress: Callable[[CompressionProgress], None] | None = None,
        image_format: str = "jpeg",
    ):
        """Start force recompression in background thread"""
        if self._running:
            return False

        if quality is None:
            quality = config.compression.quality

        self._running = True
        self._cancel_requested = False
        self._on_progress = on_progress

        def run():
            try:
                total = db.get_force_recompressible_count(older_than_days)["total"]
                self._progress = CompressionProgress(total=total, processed=0, errors=0, bytes_saved=0, is_running=True)

                batch_size = 50
                offset = 0

                while self._running and not self._cancel_requested:
                    screenshots = db.get_force_recompressible_screenshots(
                        older_than_days, limit=batch_size, offset=offset
                    )

                    if not screenshots:
                        break

                    for screenshot in screenshots:
                        if self._cancel_requested:
                            break
                        try:
                            saved = self._compress_screenshot(
                                screenshot, quality, force=True, image_format=image_format
                            )
                            self._progress.processed += 1
                            self._progress.bytes_saved += saved
                        except Exception as e:
                            print(f"Error compressing {screenshot['image_path']}: {e}")
                            self._progress.errors += 1

                        if self._on_progress:
                            self._on_progress(self._progress)

                    offset += batch_size
            except Exception:
                self._progress.errors += 1
                logger.exception("Force compression worker failed")
            finally:
                self._progress.is_running = False
                self._cancel_requested = False
                self._running = False

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        return True


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
