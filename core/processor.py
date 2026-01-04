"""
LiveRecall Processor
Sync service for generating embeddings for unsynced screenshots
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass

from core.database import db
from core.embeddings import get_image_embedding


@dataclass
class SyncProgress:
    """Progress information for sync operation"""

    total: int = 0
    processed: int = 0
    errors: int = 0
    is_running: bool = False

    @property
    def remaining(self) -> int:
        return self.total - self.processed - self.errors

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.processed / self.total) * 100


class ProcessorService:
    """Service for syncing screenshots (generating embeddings)"""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._progress = SyncProgress()
        self._on_progress: Callable[[SyncProgress], None] | None = None
        self._cancel_requested = False

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

    def stop(self):
        """Stop processing"""
        self._cancel_requested = True
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    def sync_all(self, on_progress: Callable[[SyncProgress], None] | None = None):
        """Synchronously process all unsynced screenshots (blocking)"""
        self._on_progress = on_progress
        self._cancel_requested = False

        # Get unsynced count
        unsynced = db.get_unsynced_screenshots()
        self._progress = SyncProgress(total=len(unsynced), processed=0, errors=0, is_running=True)

        if self._on_progress:
            self._on_progress(self._progress)

        for screenshot in unsynced:
            if self._cancel_requested:
                break

            try:
                # Generate embedding
                embedding = get_image_embedding(screenshot["image_path"])

                # Save to database
                db.add_embedding(screenshot["id"], embedding)

                self._progress.processed += 1
            except Exception as e:
                print(f"Error processing {screenshot['image_path']}: {e}")
                self._progress.errors += 1

            if self._on_progress:
                self._on_progress(self._progress)

        self._progress.is_running = False
        if self._on_progress:
            self._on_progress(self._progress)

        return self._progress

    def _process_loop(self, batch_size: int):
        """Background processing - processes all unsynced then stops"""
        # Get total unsynced count upfront
        total_unsynced = db.get_unsynced_count()

        if total_unsynced == 0:
            self._running = False
            self._progress = SyncProgress(total=0, processed=0, errors=0, is_running=False)
            return

        self._progress = SyncProgress(total=total_unsynced, processed=0, errors=0, is_running=True)

        print(f"🔄 Syncing {total_unsynced} screenshots...")

        # Process in batches until done
        while self._running and not self._cancel_requested:
            # Get next batch
            unsynced = db.get_unsynced_screenshots(limit=batch_size)

            if not unsynced:
                # All done!
                break

            for screenshot in unsynced:
                if self._cancel_requested:
                    break

                try:
                    # Generate embedding
                    embedding = get_image_embedding(screenshot["image_path"])

                    # Save to database
                    db.add_embedding(screenshot["id"], embedding)

                    self._progress.processed += 1
                    print(f"  ✓ {self._progress.processed}/{self._progress.total}")
                except Exception as e:
                    print(f"  ✗ Error: {screenshot['image_path']}: {e}")
                    self._progress.errors += 1

                if self._on_progress:
                    self._on_progress(self._progress)

        # Mark as complete
        self._running = False
        self._progress.is_running = False
        print(f"✅ Sync complete: {self._progress.processed} processed, {self._progress.errors} errors")


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
