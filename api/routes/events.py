"""
SSE Events API Routes
Server-Sent Events for real-time model download and sync progress updates.

Events:
- model_download: Progress for CLIP/BGE model downloads
- sync_progress: Progress for sync operations (embeddings, OCR, text embeddings)
- model_status: Model loading/unloading status changes
"""

import asyncio
import contextlib
import json
import logging
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Events"])

# Global event queue for broadcasting events to all connected clients
# Protected by _subscribers_lock for thread-safe access
_event_subscribers: list[asyncio.Queue] = []
_subscribers_lock = threading.Lock()


def broadcast_event(event_type: str, data: dict):
    """Broadcast an event to all connected SSE clients.

    Thread-safe: Makes a copy of the subscriber list before iterating
    to prevent race conditions with subscribe/unsubscribe operations.
    """
    event_data = {"type": event_type, **data}
    # Copy list under lock to prevent modification during iteration
    with _subscribers_lock:
        subscribers = list(_event_subscribers)
    for queue in subscribers:
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(event_data)


@asynccontextmanager
async def subscribe_to_events():
    """Context manager for subscribing to events.

    Thread-safe: Uses lock when modifying the subscriber list.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    with _subscribers_lock:
        _event_subscribers.append(queue)
    try:
        yield queue
    finally:
        with _subscribers_lock:
            _event_subscribers.remove(queue)


async def event_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events for connected clients"""
    async with subscribe_to_events() as queue:
        # Send initial status
        yield format_sse_event("connected", {"message": "Connected to event stream"})

        # Send initial model status
        try:
            from core.embeddings import get_model_status as get_clip_status

            clip_status = get_clip_status()
            yield format_sse_event(
                "model_status",
                {
                    "model": "clip",
                    "loaded": clip_status["loaded"],
                    "device": clip_status["device"],
                },
            )
        except Exception as e:
            logger.warning("Error getting CLIP model status: %s", e)

        try:
            from core.text_embeddings import get_model_status as get_bge_status

            bge_status = get_bge_status()
            yield format_sse_event(
                "model_status",
                {
                    "model": "text_embedding",
                    "loaded": bge_status["loaded"],
                    "device": bge_status["device"],
                },
            )
        except Exception as e:
            logger.warning("Error getting text embedding model status: %s", e)

        # Send initial sync status
        try:
            from core.processor import processor_service

            progress = processor_service.progress
            yield format_sse_event(
                "sync_progress",
                {
                    "is_syncing": progress.is_running,
                    "total": progress.total,
                    "processed": progress.processed,
                    "errors": progress.errors,
                    "current_phase": progress.current_phase,
                    "embeddings_done": progress.embeddings_done,
                    "ocr_done": progress.ocr_done,
                    "text_embeddings_done": progress.text_embeddings_done,
                },
            )
        except Exception as e:
            logger.warning("Error getting sync progress: %s", e)

        # Listen for new events
        while True:
            try:
                # Wait for event with timeout (to send keepalive)
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield format_sse_event(event["type"], event)
            except asyncio.TimeoutError:
                # Send keepalive comment
                yield ": keepalive\n\n"


def format_sse_event(event_type: str, data: dict) -> str:
    """Format data as Server-Sent Event"""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@router.get("/stream")
async def event_stream():
    """
    SSE endpoint for real-time events.

    Events sent:
    - connected: Initial connection confirmation
    - model_status: Model loading/unloading status (clip, text_embedding)
    - model_download: Model download progress (progress %, size)
    - sync_progress: Sync operation progress (phase, counts)
    - ocr_progress: OCR processing progress
    """
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/status")
async def get_all_status():
    """
    Get current status of all models and sync operations.

    This is a polling alternative to SSE for clients that don't support it.
    """
    # CLIP model status
    clip_status: dict[str, bool | str | None] = {
        "loaded": False,
        "device": None,
        "downloading": False,
        "downloaded": False,
    }
    try:
        from core.embeddings import get_model_status as get_clip_status

        status = get_clip_status()
        clip_status = {
            "loaded": status["loaded"],
            "device": status["device"],
            "downloading": False,
            "downloaded": status.get("downloaded", False),
        }
    except Exception as e:
        print(f"Error getting CLIP status: {e}")

    # Text embedding model status
    text_status: dict[str, bool | str | None] = {
        "loaded": False,
        "device": None,
        "downloading": False,
        "downloaded": False,
    }
    try:
        from core.text_embeddings import get_model_status as get_bge_status

        status = get_bge_status()
        text_status = {
            "loaded": status["loaded"],
            "device": status["device"],
            "downloading": False,
            "downloaded": status.get("downloaded", False),
        }
    except Exception as e:
        print(f"Error getting text embedding status: {e}")

    # OCR status
    ocr_status: dict[str, bool | str | None] = {"available": False, "provider": None}
    try:
        from core.ocr import ocr_service

        ocr_status = {
            "available": ocr_service.is_available(),
            "provider": ocr_service.get_provider_name() if ocr_service.is_available() else None,
        }
    except Exception as e:
        print(f"Error getting OCR status: {e}")

    # Sync status
    sync_status = {
        "is_syncing": False,
        "total": 0,
        "processed": 0,
        "current_phase": "",
        "embeddings_done": 0,
        "ocr_done": 0,
        "text_embeddings_done": 0,
    }
    try:
        from core.processor import processor_service

        progress = processor_service.progress
        sync_status = {
            "is_syncing": progress.is_running,
            "total": progress.total,
            "processed": progress.processed,
            "current_phase": progress.current_phase,
            "embeddings_done": progress.embeddings_done,
            "ocr_done": progress.ocr_done,
            "text_embeddings_done": progress.text_embeddings_done,
        }
    except Exception as e:
        print(f"Error getting sync status: {e}")

    # OCR stats
    ocr_stats = {"pending": 0, "completed": 0}
    try:
        stats = db.get_ocr_stats()
        ocr_stats = {
            "pending": stats["without_ocr"],
            "completed": stats["with_ocr"],
        }
    except Exception as e:
        print(f"Error getting OCR stats: {e}")

    return {
        "clip": clip_status,
        "text_embedding": text_status,
        "ocr": ocr_status,
        "sync": sync_status,
        "ocr_stats": ocr_stats,
    }


# Helper function to be called from other modules
def emit_model_download_progress(model: str, progress: float, size_mb: int | None = None):
    """Emit model download progress event"""
    broadcast_event(
        "model_download",
        {
            "model": model,
            "progress": progress,
            "size_mb": size_mb,
            "status": "downloading" if progress < 100 else "complete",
        },
    )


def emit_model_status(model: str, loaded: bool, device: str | None = None):
    """Emit model status change event"""
    broadcast_event(
        "model_status",
        {
            "model": model,
            "loaded": loaded,
            "device": device,
        },
    )


def emit_sync_progress(
    is_syncing: bool,
    total: int,
    processed: int,
    phase: str,
    embeddings_done: int = 0,
    ocr_done: int = 0,
    text_embeddings_done: int = 0,
):
    """Emit sync progress event"""
    broadcast_event(
        "sync_progress",
        {
            "is_syncing": is_syncing,
            "total": total,
            "processed": processed,
            "current_phase": phase,
            "embeddings_done": embeddings_done,
            "ocr_done": ocr_done,
            "text_embeddings_done": text_embeddings_done,
        },
    )
