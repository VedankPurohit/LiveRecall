"""
Sync API Routes
Process unsynced screenshots with CLIP embeddings
"""

from fastapi import APIRouter, BackgroundTasks

from api.schemas import (
    ModelStatus,
    SuccessResponse,
    SyncStartRequest,
    SyncStartResponse,
    SyncStatus,
)
from core.database import db
from core.embeddings import (
    get_model_status,
    is_loaded,
    set_auto_unload_timeout,
    unload_model,
)
from core.processor import SyncProgress, processor_service

router = APIRouter(prefix="/sync", tags=["Sync"])


def progress_to_status(progress: SyncProgress) -> SyncStatus:
    """Convert internal progress to API schema"""
    return SyncStatus(
        is_syncing=progress.is_running,
        total=progress.total,
        processed=progress.processed,
        errors=progress.errors,
        progress_percent=progress.percent,
    )


@router.get("", response_model=SyncStatus)
@router.get("/status", response_model=SyncStatus)
async def get_sync_status():
    """Get current sync status"""
    return progress_to_status(processor_service.progress)


@router.post("/start", response_model=SyncStartResponse)
async def start_sync(
    request: SyncStartRequest = None,
    background_tasks: BackgroundTasks = None,
):
    """
    Start syncing unsynced screenshots.

    This loads the CLIP model (if not already loaded) and generates
    embeddings for screenshots that don't have them yet.

    The sync runs in the background - use /sync/status to monitor progress.
    """
    if processor_service.is_running:
        return SyncStartResponse(
            success=False,
            message="Sync is already running",
            unsynced_count=db.get_unsynced_count(),
        )

    unsynced_count = db.get_unsynced_count()

    if unsynced_count == 0:
        return SyncStartResponse(
            success=True,
            message="No screenshots to sync",
            unsynced_count=0,
        )

    batch_size = request.batch_size if request else 10

    # Start sync in background
    processor_service.start(batch_size=batch_size)

    return SyncStartResponse(
        success=True,
        message=f"Sync started for {unsynced_count} screenshots",
        unsynced_count=unsynced_count,
    )


@router.post("/stop", response_model=SyncStatus)
async def stop_sync():
    """Stop the current sync operation"""
    processor_service.stop()
    return progress_to_status(processor_service.progress)


@router.get("/unsynced", response_model=dict)
async def get_unsynced_count():
    """Get the number of unsynced screenshots"""
    return {
        "unsynced_count": db.get_unsynced_count(),
        "total_screenshots": db.get_stats()["total_screenshots"],
    }


# =============================================================================
# Model Management
# =============================================================================


@router.get("/model", response_model=ModelStatus)
async def get_model_status_endpoint():
    """Get CLIP model status"""
    status = get_model_status()
    return ModelStatus(
        loaded=status["loaded"],
        device=status["device"],
        idle_seconds=status["idle_seconds"],
        auto_unload_seconds=status["auto_unload_seconds"],
    )


@router.post("/model/unload", response_model=SuccessResponse)
async def unload_model_endpoint():
    """
    Manually unload the CLIP model to free memory.

    The model will be automatically reloaded when needed
    (on next search or sync).
    """
    if not is_loaded():
        return SuccessResponse(
            success=True,
            message="Model is not loaded",
        )

    unload_model()

    return SuccessResponse(
        success=True,
        message="Model unloaded successfully",
    )


@router.post("/model/auto-unload/{seconds}", response_model=SuccessResponse)
async def set_auto_unload(seconds: int):
    """
    Set the auto-unload timeout for the CLIP model.

    - 0: Disable auto-unload (model stays loaded)
    - 60-3600: Unload after N seconds of inactivity

    Default is 300 seconds (5 minutes).
    """
    if seconds < 0 or seconds > 3600:
        return SuccessResponse(
            success=False,
            message="Timeout must be between 0 and 3600 seconds",
        )

    set_auto_unload_timeout(seconds)

    if seconds == 0:
        return SuccessResponse(
            success=True,
            message="Auto-unload disabled",
        )

    return SuccessResponse(
        success=True,
        message=f"Auto-unload set to {seconds} seconds",
    )
