"""
Sync API Routes
Process unsynced screenshots with CLIP embeddings + OCR text extraction.

The sync process has multiple phases:
1. CLIP image embeddings (for visual semantic search)
2. OCR text extraction (for exact/fuzzy text search)
3. BGE text embeddings (for text semantic search)
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.schemas import (
    AllModelsStatus,
    EnhancedSyncStatus,
    ModelStatus,
    OCRConfig,
    OCRStats,
    SuccessResponse,
    SyncStartRequest,
    SyncStartResponse,
    SyncStatus,
)
from core.config import config
from core.database import db
from core.embeddings import (
    get_model_status,
    is_loaded,
    set_auto_unload_timeout,
    unload_model,
)
from core.processor import SyncProgress, processor_service
from core.text_embeddings import (
    is_loaded as is_text_model_loaded,
)
from core.text_embeddings import (
    set_auto_unload_timeout as set_text_auto_unload_timeout,
)
from core.text_embeddings import (
    unload_model as unload_text_model,
)

logger = logging.getLogger(__name__)

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


def progress_to_enhanced_status(progress: SyncProgress) -> EnhancedSyncStatus:
    """Convert internal progress to enhanced API schema with OCR tracking"""
    return EnhancedSyncStatus(
        is_syncing=progress.is_running,
        total=progress.total,
        processed=progress.processed,
        errors=progress.errors,
        progress_percent=progress.percent,
        current_phase=progress.current_phase,
        embeddings_done=progress.embeddings_done,
        ocr_done=progress.ocr_done,
        text_embeddings_done=progress.text_embeddings_done,
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

    This processes screenshots in multiple phases:
    1. CLIP image embeddings (for visual semantic search)
    2. OCR text extraction (for exact/fuzzy text search)
    3. BGE text embeddings (for text semantic search)

    The sync runs in the background - use /sync/status to monitor progress.
    """
    if processor_service.is_running:
        return SyncStartResponse(
            success=False,
            message="Sync is already running",
            unsynced_count=db.get_unsynced_count(),
        )

    # Check both CLIP unsynced AND OCR pending
    unsynced_count = db.get_unsynced_count()
    ocr_pending = db.get_ocr_pending_count() if config.ocr.enabled else 0
    total_pending = unsynced_count + ocr_pending

    if total_pending == 0:
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
        message=f"Sync started for {total_pending} screenshots ({unsynced_count} new, {ocr_pending} OCR pending)",
        unsynced_count=total_pending,
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
    Manually unload the embedding models to free memory.

    The models will be automatically reloaded when needed
    (on next search or sync).
    """
    clip_loaded = is_loaded()
    text_loaded = is_text_model_loaded()

    if not clip_loaded and not text_loaded:
        return SuccessResponse(
            success=True,
            message="Models are not loaded",
        )

    unload_model()
    unload_text_model()

    return SuccessResponse(
        success=True,
        message="Embedding models unloaded successfully",
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
    set_text_auto_unload_timeout(seconds)

    if seconds == 0:
        return SuccessResponse(
            success=True,
            message="Auto-unload disabled",
        )

    return SuccessResponse(
        success=True,
        message=f"Auto-unload set to {seconds} seconds",
    )


# =============================================================================
# OCR Management
# =============================================================================


@router.get("/enhanced", response_model=EnhancedSyncStatus)
async def get_enhanced_sync_status():
    """Get detailed sync status including OCR phase information"""
    return progress_to_enhanced_status(processor_service.progress)


@router.get("/ocr/status", response_model=OCRStats)
async def get_ocr_status():
    """Get OCR processing statistics

    Returns counts of screenshots with/without OCR, average confidence, etc.
    """
    stats = db.get_ocr_stats()
    return OCRStats(
        total_screenshots=stats["total_screenshots"],
        with_ocr=stats["with_ocr"],
        without_ocr=stats["without_ocr"],
        with_text=stats["with_text"],
        avg_confidence=stats["avg_confidence"],
    )


@router.get("/ocr/config", response_model=OCRConfig)
async def get_ocr_config():
    """Get current OCR configuration"""
    return OCRConfig(
        enabled=config.ocr.enabled,
        provider=config.ocr.provider,
    )


@router.put("/ocr/config", response_model=SuccessResponse)
async def update_ocr_config(new_config: OCRConfig):
    """Update OCR configuration

    Note: Changing provider may require reprocessing all screenshots.
    Use /sync/ocr/recompute to regenerate OCR data.
    """
    config.ocr.enabled = new_config.enabled
    config.ocr.provider = new_config.provider
    config.save()

    return SuccessResponse(
        success=True,
        message=f"OCR config updated: enabled={new_config.enabled}, provider={new_config.provider}",
    )


@router.post("/ocr/recompute", response_model=SyncStartResponse)
async def recompute_ocr():
    """Recompute OCR for all screenshots

    Use this after changing OCR or text embedding models to regenerate
    all text data. This will:
    1. Clear existing OCR data
    2. Re-run OCR on all screenshots
    3. Regenerate text chunks and embeddings

    Warning: This may take a long time for large databases.
    """
    if processor_service.is_running:
        raise HTTPException(
            status_code=409,
            detail="Cannot recompute while sync is running",
        )

    if not config.ocr.enabled:
        raise HTTPException(
            status_code=400,
            detail="OCR is disabled. Enable it in settings first.",
        )

    total = db.get_screenshot_count()

    # Start recompute in background
    import threading

    def run_recompute():
        try:
            processor_service.recompute_ocr()
        except Exception as e:
            logger.exception("Error during OCR recompute: %s", e)

    thread = threading.Thread(target=run_recompute, daemon=True)
    thread.start()

    return SyncStartResponse(
        success=True,
        message=f"OCR recompute started for {total} screenshots",
        unsynced_count=total,
    )


@router.get("/models", response_model=AllModelsStatus)
async def get_all_models_status():
    """Get status of all ML models (CLIP, BGE, OCR)"""
    # CLIP status
    clip_status = get_model_status()
    clip = ModelStatus(
        loaded=clip_status["loaded"],
        device=clip_status["device"],
        idle_seconds=clip_status["idle_seconds"],
        auto_unload_seconds=clip_status["auto_unload_seconds"],
    )

    # Text embedding status (lazy import)
    text_emb = None
    try:
        from core.text_embeddings import text_embedding_service

        text_status = text_embedding_service.get_model_status()
        text_emb = ModelStatus(
            loaded=text_status["loaded"],
            device=text_status["device"],
            idle_seconds=text_status["idle_seconds"],
            auto_unload_seconds=text_status["auto_unload_seconds"],
        )
    except Exception as e:
        logger.warning("Error getting text embedding model status: %s", e)

    # OCR status
    ocr_status = "not_available"
    try:
        from core.ocr import ocr_service

        if ocr_service.is_available():
            ocr_status = ocr_service.get_provider_name()
    except Exception as e:
        logger.warning("Error getting OCR status: %s", e)

    return AllModelsStatus(
        clip=clip,
        text_embedding=text_emb,
        ocr=ocr_status,
    )
