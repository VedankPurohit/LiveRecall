"""
LiveRecall Processor
Sync service for generating embeddings for unsynced screenshots.

Supports multiple processing phases:
1. CLIP image embeddings (visual semantic search)
2. OCR text extraction (exact/fuzzy text search)
3. BGE text embeddings (text semantic search)

OCR and text embedding providers can be configured in config.py.
To change models, update config and call processor_service.recompute_ocr().
"""

import contextlib
import threading
from collections.abc import Callable
from dataclasses import dataclass

from core.config import config
from core.database import db
from core.embeddings import get_image_embedding


class OCRProcessingError(Exception):
    """Raised when OCR processing fails for expected reasons (corrupted image, etc.)"""

    pass


@dataclass
class SyncProgress:
    """Progress information for sync operation with detailed phase tracking

    Phases:
    1. embedding: Generate CLIP image embeddings
    2. ocr: Extract text via OCR
    3. text_embedding: Generate BGE text embeddings for chunks
    """

    total: int = 0
    processed: int = 0
    errors: int = 0
    is_running: bool = False

    # Detailed phase tracking
    current_phase: str = ""  # "embedding", "ocr", "text_embedding"
    embeddings_done: int = 0
    ocr_done: int = 0
    text_embeddings_done: int = 0

    # Error tracking for visibility
    last_error: str = ""
    error_type: str = ""  # "ocr_failed", "db_error", "code_error"

    @property
    def remaining(self) -> int:
        return self.total - self.processed - self.errors

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.processed / self.total) * 100


class ProcessorService:
    """Service for syncing screenshots (embeddings + OCR + text embeddings)

    Processing pipeline:
    1. Generate CLIP image embeddings for unsynced screenshots
    2. Run OCR on screenshots without OCR data (if enabled)
    3. Generate BGE text embeddings for OCR text chunks

    Configuration:
    - OCR provider: config.ocr.provider ("auto", "apple_vision", "tesseract")
    - Text model: config.text_embedding.model (default: "BAAI/bge-small-en-v1.5")
    - Chunk sizes: config.chunking.small_size, config.chunking.large_size

    To change OCR/embedding models:
    1. Update config settings
    2. Call processor_service.recompute_ocr() to reprocess all screenshots
    """

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._progress = SyncProgress()
        self._on_progress: Callable[[SyncProgress], None] | None = None
        self._cancel_requested = False

        # Lazy-loaded services (imported on first use to avoid circular imports)
        self._ocr_service = None
        self._text_embedding_service = None
        self._chunking_module = None

    def _get_ocr_service(self):
        """Lazy load OCR service"""
        if self._ocr_service is None:
            from core.ocr import ocr_service

            self._ocr_service = ocr_service
        return self._ocr_service

    def _get_text_embedding_service(self):
        """Lazy load text embedding service"""
        if self._text_embedding_service is None:
            from core.text_embeddings import text_embedding_service

            self._text_embedding_service = text_embedding_service
        return self._text_embedding_service

    def _get_chunking(self):
        """Lazy load chunking module"""
        if self._chunking_module is None:
            from core import chunking

            self._chunking_module = chunking
        return self._chunking_module

    def _unload_models(self):
        """Unload both embedding models after heavy processing completes."""
        from core.embeddings import unload_model as unload_clip_model
        from core.text_embeddings import unload_model as unload_text_embedding_model

        unload_clip_model()
        unload_text_embedding_model()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def progress(self) -> SyncProgress:
        return self._progress

    def start(self, batch_size: int = 10, on_progress: Callable[[SyncProgress], None] | None = None):
        """Start processing unsynced screenshots in background"""
        if self._running:
            return

        self._running = True
        self._cancel_requested = False
        self._on_progress = on_progress
        self._thread = threading.Thread(target=self._process_loop, args=(batch_size,), daemon=True)
        self._thread.start()

    def start_ocr_migration(self, batch_size: int = 10, on_progress: Callable[[SyncProgress], None] | None = None):
        """Start OCR migration for screenshots that have CLIP but no OCR.

        This only processes existing screenshots that need OCR migration,
        NOT new screenshots that haven't been synced yet.
        Use start() for full sync including new screenshots.
        """
        if self._running:
            return

        # Only start if there are OCR-pending screenshots
        ocr_pending = db.get_ocr_pending_count() if config.ocr.enabled else 0
        if ocr_pending == 0:
            return

        self._running = True
        self._cancel_requested = False
        self._on_progress = on_progress
        self._thread = threading.Thread(target=self._ocr_migration_loop, args=(batch_size,), daemon=True)
        self._thread.start()

    def _ocr_migration_loop(self, batch_size: int):
        """Background loop for OCR migration only (no CLIP processing)"""
        ocr_pending = db.get_ocr_pending_count() if config.ocr.enabled else 0

        if ocr_pending == 0:
            self._running = False
            self._progress = SyncProgress(total=0, processed=0, errors=0, is_running=False)
            return

        self._progress = SyncProgress(total=ocr_pending, processed=0, errors=0, is_running=True)
        self._progress.current_phase = "ocr"

        print(f"🔄 Auto-syncing OCR for {ocr_pending} existing screenshots...")

        # Only process OCR migration (skip CLIP phase)
        self._process_pending_ocr(batch_size)

        # Mark as complete
        self._running = False
        self._progress.is_running = False
        self._unload_models()
        print(f"✅ OCR migration complete: {self._progress.processed} processed, {self._progress.errors} errors")

    def stop(self):
        """Stop processing"""
        self._cancel_requested = True
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        self._unload_models()

    def sync_all(self, on_progress: Callable[[SyncProgress], None] | None = None):
        """Synchronously process all unsynced screenshots (blocking)"""
        self._on_progress = on_progress
        self._cancel_requested = False

        # Get unsynced count
        unsynced = db.get_unsynced_screenshots()
        self._progress = SyncProgress(total=len(unsynced), processed=0, errors=0, is_running=True)
        self._progress.current_phase = "embedding"

        if self._on_progress:
            self._on_progress(self._progress)

        for screenshot in unsynced:
            if self._cancel_requested:
                break

            try:
                # Phase 1: Generate CLIP embedding
                embedding = get_image_embedding(screenshot["image_path"])
                db.add_embedding(screenshot["id"], embedding)
                self._progress.embeddings_done += 1

                # Phase 2: OCR (if enabled)
                if config.ocr.enabled:
                    self._process_ocr_for_screenshot(screenshot["id"], screenshot["image_path"])

                self._progress.processed += 1
            except Exception as e:
                print(f"Error processing {screenshot['image_path']}: {e}")
                self._progress.errors += 1

            if self._on_progress:
                self._on_progress(self._progress)

        self._progress.is_running = False
        self._unload_models()
        if self._on_progress:
            self._on_progress(self._progress)

        return self._progress

    def _process_loop(self, batch_size: int):
        """Background processing - processes all unsynced then stops"""
        # Phase 1: Process screenshots without CLIP embeddings
        total_unsynced = db.get_unsynced_count()
        ocr_pending = db.get_ocr_pending_count() if config.ocr.enabled else 0

        total = total_unsynced + ocr_pending
        if total == 0:
            self._running = False
            self._progress = SyncProgress(total=0, processed=0, errors=0, is_running=False)
            return

        self._progress = SyncProgress(total=total, processed=0, errors=0, is_running=True)
        self._progress.current_phase = "embedding"

        print(f"🔄 Syncing {total_unsynced} screenshots + {ocr_pending} OCR pending...")

        # Process CLIP embeddings in batches
        while self._running and not self._cancel_requested:
            unsynced = db.get_unsynced_screenshots(limit=batch_size)
            if not unsynced:
                break

            for screenshot in unsynced:
                if self._cancel_requested:
                    break

                try:
                    # Generate CLIP embedding
                    embedding = get_image_embedding(screenshot["image_path"])
                    db.add_embedding(screenshot["id"], embedding)
                    self._progress.embeddings_done += 1

                    # Run OCR immediately after embedding (before compression)
                    if config.ocr.enabled:
                        self._process_ocr_for_screenshot(screenshot["id"], screenshot["image_path"])

                    self._progress.processed += 1
                    print(f"  ✓ {self._progress.processed}/{self._progress.total}")
                except OCRProcessingError as e:
                    # Expected OCR failure - skip and continue
                    print(f"  ⚠ Skipped OCR for {screenshot['id']}: {e}")
                    self._progress.errors += 1
                    self._progress.last_error = str(e)
                    self._progress.error_type = "ocr_failed"
                    # Still count as processed since embedding worked
                    self._progress.processed += 1
                    with contextlib.suppress(Exception):
                        db.mark_ocr_complete(screenshot["id"])
                except (TypeError, AttributeError, KeyError) as e:
                    # Likely a code bug - log clearly but continue with other screenshots
                    error_msg = f"{type(e).__name__}: {e}"
                    print(f"  ❌ Code error for {screenshot['id']}: {error_msg}")
                    self._progress.errors += 1
                    self._progress.last_error = error_msg
                    self._progress.error_type = "code_error"
                    # Don't mark as complete - can retry after fix
                except (FileNotFoundError, OSError) as e:
                    # Image file issue - skip and continue
                    print(f"  ⚠ Skipped {screenshot['id']}: Cannot read image - {e}")
                    self._progress.errors += 1
                    self._progress.last_error = str(e)
                    self._progress.error_type = "file_error"
                except Exception as e:
                    # Other error - log and continue
                    error_msg = f"{type(e).__name__}: {e}"
                    print(f"  ✗ Error: {error_msg}")
                    self._progress.errors += 1
                    self._progress.last_error = error_msg
                    self._progress.error_type = "unknown"

                if self._on_progress:
                    self._on_progress(self._progress)

        # Phase 2: Process any remaining OCR (migration for existing screenshots)
        if config.ocr.enabled and not self._cancel_requested:
            self._progress.current_phase = "ocr"
            self._process_pending_ocr(batch_size)

        # Mark as complete
        self._running = False
        self._progress.is_running = False
        self._unload_models()
        print(f"✅ Sync complete: {self._progress.processed} processed, {self._progress.errors} errors")

    def _process_ocr_for_screenshot(self, screenshot_id: int, image_path: str):
        """Run OCR pipeline for a single screenshot

        Pipeline:
        1. Extract text via OCR provider
        2. Store OCR result
        3. Chunk text (small + large)
        4. Generate BGE embeddings for chunks (batched for speed)
        5. Store chunks and embeddings

        Raises:
            OCRProcessingError: For expected OCR failures (corrupted image, etc.)
            TypeError/AttributeError: Re-raised for code bugs (should not be silenced)
            Exception: Other unexpected errors are re-raised
        """
        self._progress.current_phase = "ocr"

        ocr_service = self._get_ocr_service()
        text_emb_service = self._get_text_embedding_service()
        chunking = self._get_chunking()

        # Step 1: Extract text
        try:
            ocr_result = ocr_service.extract_text(image_path)
        except (FileNotFoundError, OSError) as e:
            # Expected failures - image missing or corrupted
            raise OCRProcessingError(f"Cannot read image: {e}") from e
        except Exception:
            # Unexpected OCR error - could be a bug, re-raise
            raise

        # Step 2: Store OCR result (even if empty, for tracking)
        # This is a critical step - if it fails, it's likely a code bug
        # Returns the ocr_id which we need for adding chunks
        ocr_id = db.add_ocr_text(
            screenshot_id=screenshot_id,
            full_text=ocr_result.text,
            confidence=ocr_result.confidence,
            word_count=ocr_result.word_count,
        )

        self._progress.ocr_done += 1

        # Step 3-5: Only if we have text
        if ocr_result.text.strip():
            self._progress.current_phase = "text_embedding"

            # Chunk the text (dual chunking: small + large)
            chunked = chunking.chunk_ocr_text(
                ocr_result.text,
                small_size=config.chunking.small_size,
                small_overlap=config.chunking.small_overlap,
                large_size=config.chunking.large_size,
                large_overlap=config.chunking.large_overlap,
            )

            # Collect all chunks for batch processing
            all_chunks = []
            for chunk in chunked.small:
                all_chunks.append(("small", chunk))
            for chunk in chunked.large:
                all_chunks.append(("large", chunk))

            if all_chunks:
                # Batch generate embeddings (much faster than individual calls)
                all_texts = [chunk.text for _, chunk in all_chunks]
                all_embeddings = text_emb_service.get_batch_embeddings(all_texts)

                # Store chunks and embeddings
                for (chunk_size, chunk), embedding in zip(all_chunks, all_embeddings, strict=False):
                    chunk_id = db.add_ocr_chunk(
                        ocr_id=ocr_id,
                        chunk_size=chunk_size,
                        chunk_index=chunk.index,
                        chunk_text=chunk.text,
                        start_char=chunk.start_char,
                        end_char=chunk.end_char,
                    )
                    db.add_text_embedding(chunk_id, embedding)

            self._progress.text_embeddings_done += len(all_chunks)

        # Mark OCR complete for this screenshot
        db.mark_ocr_complete(screenshot_id)

    def _process_pending_ocr(self, batch_size: int):
        """Process OCR for screenshots that have embeddings but no OCR (migration)"""
        while self._running and not self._cancel_requested:
            pending = db.get_screenshots_without_ocr(limit=batch_size)
            if not pending:
                break

            for screenshot in pending:
                if self._cancel_requested:
                    break

                try:
                    self._process_ocr_for_screenshot(screenshot["id"], screenshot["image_path"])
                    self._progress.processed += 1
                    print(f"  ✓ {self._progress.processed}/{self._progress.total}")
                except OCRProcessingError as e:
                    # Expected failure (corrupted image, etc.) - skip and continue
                    print(f"  ⚠ Skipped {screenshot['id']}: {e}")
                    self._progress.errors += 1
                    self._progress.last_error = str(e)
                    self._progress.error_type = "ocr_failed"
                    # Mark as complete so we don't retry
                    with contextlib.suppress(Exception):
                        db.mark_ocr_complete(screenshot["id"])
                except (TypeError, AttributeError, KeyError) as e:
                    # Likely a code bug - log clearly but continue with other screenshots
                    error_msg = f"{type(e).__name__}: {e}"
                    print(f"  ❌ Code error for {screenshot['id']}: {error_msg}")
                    self._progress.errors += 1
                    self._progress.last_error = error_msg
                    self._progress.error_type = "code_error"
                    # Don't mark as complete - can retry after fix
                except Exception as e:
                    # Unexpected error - log but continue (could be transient)
                    error_msg = f"{type(e).__name__}: {e}"
                    print(f"  ✗ Error: {error_msg}")
                    self._progress.errors += 1
                    self._progress.last_error = error_msg
                    self._progress.error_type = "unknown"

                if self._on_progress:
                    self._on_progress(self._progress)

    def recompute_ocr(self, on_progress: Callable[[SyncProgress], None] | None = None):
        """Recompute OCR for all screenshots (use after changing OCR/embedding model)

        This will:
        1. Clear all existing OCR data
        2. Re-run OCR on all screenshots
        3. Regenerate all text chunks and embeddings
        """
        if self._running:
            raise RuntimeError("Cannot recompute while sync is running")

        self._on_progress = on_progress
        self._cancel_requested = False

        # Clear existing OCR data
        print("🗑️ Clearing existing OCR data...")
        db.reset_all_ocr()

        # Get total count
        total = db.get_screenshot_count()
        self._progress = SyncProgress(total=total, processed=0, errors=0, is_running=True)
        self._progress.current_phase = "ocr"

        if self._on_progress:
            self._on_progress(self._progress)

        print(f"🔄 Recomputing OCR for {total} screenshots...")

        # Process all screenshots
        batch_size = 10
        while not self._cancel_requested:
            screenshots = db.get_screenshots_without_ocr(limit=batch_size)
            if not screenshots:
                break

            for screenshot in screenshots:
                if self._cancel_requested:
                    break

                try:
                    self._process_ocr_for_screenshot(screenshot["id"], screenshot["image_path"])
                    self._progress.processed += 1
                    print(f"  ✓ {self._progress.processed}/{self._progress.total}")
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    self._progress.errors += 1

                if self._on_progress:
                    self._on_progress(self._progress)

        self._progress.is_running = False
        self._unload_models()
        if self._on_progress:
            self._on_progress(self._progress)

        print(f"✅ OCR recompute complete: {self._progress.processed} processed, {self._progress.errors} errors")
        return self._progress


# Global processor service instance
processor_service = ProcessorService()


def sync_screenshots(on_progress: Callable[[SyncProgress], None] | None = None) -> SyncProgress:
    """
    Convenience function to sync all unsynced screenshots
    This is a blocking call - use processor_service.start() for background processing
    """
    return processor_service.sync_all(on_progress)


if __name__ == "__main__":
    from core.database import db

    db.connect()

    print(f"Unsynced screenshots: {db.get_unsynced_count()}")

    def print_progress(progress: SyncProgress):
        print(f"Progress: {progress.processed}/{progress.total} ({progress.percent:.1f}%)")

    print("Starting sync...")
    result = sync_screenshots(on_progress=print_progress)

    print("\nSync complete!")
    print(f"  Processed: {result.processed}")
    print(f"  Errors: {result.errors}")
    print(f"  Stats: {db.get_stats()}")

    db.disconnect()
