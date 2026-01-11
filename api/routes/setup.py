"""
Setup API Routes
Handle first-run and version-change setup flow for screen recording permissions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.schemas import SetupStatus, SuccessResponse
from core.config import config
from core.platform import current_platform
from core.updater import VERSION

router = APIRouter(prefix="/setup", tags=["Setup"])


# =============================================================================
# Autostart Schemas (local to this module)
# =============================================================================


class AutostartStatus(BaseModel):
    """Auto-start status response"""

    enabled: bool
    supported: bool
    platform: str


class AutostartSetRequest(BaseModel):
    """Request to set auto-start"""

    enabled: bool


@router.get("/status", response_model=SetupStatus)
async def get_setup_status():
    """
    Check if setup is needed.

    Returns whether the app version has changed since last run,
    which indicates that screen recording permissions may need to be reset.
    Also indicates if the platform requires permission setup.
    """
    needs_setup = config.last_seen_version != VERSION
    return SetupStatus(
        current_version=VERSION,
        last_seen_version=config.last_seen_version,
        needs_setup=needs_setup,
        needs_permission=current_platform.needs_screen_permission(),
        platform=current_platform.name,
    )


@router.post("/reset-permissions", response_model=SuccessResponse)
async def reset_screen_capture_permissions():
    """
    Reset screen capture permissions for LiveRecall.

    On macOS: Runs tccutil reset ScreenCapture com.liverecall.app
    On Windows: No-op (permissions not required)
    On Linux: No-op (varies by desktop environment)

    Returns success status and a message explaining the result.
    """
    success, message = current_platform.reset_screen_permission()

    if not success:
        raise HTTPException(status_code=500, detail=message)

    return SuccessResponse(success=success, message=message)


@router.post("/complete", response_model=SuccessResponse)
async def complete_setup():
    """
    Mark setup as complete.

    Updates the last_seen_version to current version so setup won't show again
    until the next version change.
    """
    config.last_seen_version = VERSION
    config.save()

    return SuccessResponse(
        success=True,
        message=f"Setup completed. Version {VERSION} marked as seen.",
    )


# =============================================================================
# Auto-start on Login
# =============================================================================


@router.get("/autostart", response_model=AutostartStatus)
async def get_autostart_status():
    """
    Check if auto-start on login is enabled.

    Returns the current auto-start status and whether it's supported
    on the current platform.
    """
    return AutostartStatus(
        enabled=current_platform.is_autostart_enabled(),
        supported=current_platform.name in ("windows", "linux"),
        platform=current_platform.name,
    )


@router.post("/autostart", response_model=SuccessResponse)
async def set_autostart(request: AutostartSetRequest):
    """
    Enable or disable auto-start on login.

    On Windows: Uses Registry (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run)
    On Linux: Uses XDG autostart desktop files
    On macOS: Not yet implemented (requires Login Items)
    """
    if request.enabled:
        success = current_platform.enable_autostart()
        if success:
            return SuccessResponse(success=True, message="Auto-start enabled.")
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to enable auto-start. This may not be supported in development mode.",
            )
    else:
        success = current_platform.disable_autostart()
        if success:
            return SuccessResponse(success=True, message="Auto-start disabled.")
        else:
            raise HTTPException(status_code=500, detail="Failed to disable auto-start.")


# =============================================================================
# Model Status and Migration
# =============================================================================


@router.get("/models")
async def get_model_status():
    """
    Get status of all ML models (CLIP, BGE, OCR).

    Returns download/loading status for each model to show on setup page.
    Status values: "not_downloaded", "downloading", "ready"
    """
    # CLIP model status
    clip_status = "not_downloaded"
    try:
        from core.embeddings import get_model_status as get_clip_status

        status = get_clip_status()
        # Check downloaded status (model could be downloaded but not loaded)
        if status.get("loaded") or status.get("downloaded"):
            clip_status = "ready"
    except Exception:
        pass

    # Text embedding model status
    text_embedding_status = "not_downloaded"
    try:
        from core.text_embeddings import get_model_status as get_bge_status

        status = get_bge_status()
        if status.get("loaded") or status.get("downloaded"):
            text_embedding_status = "ready"
    except Exception:
        pass

    # OCR status
    ocr_status = "not_available"
    try:
        from core.ocr import ocr_service

        if ocr_service.is_available():
            ocr_status = "ready"
    except Exception:
        pass

    return {
        "clip": clip_status,
        "text_embedding": text_embedding_status,
        "ocr": ocr_status,
        "all_ready": clip_status == "ready",  # CLIP is required, others are optional
    }


@router.post("/download-models")
async def download_models():
    """
    Trigger download of required ML models.

    Downloads CLIP and BGE models if not already downloaded.
    This will block until models are downloaded.
    """

    from fastapi.responses import StreamingResponse

    async def download_stream():
        """Stream download progress as SSE events"""
        import json

        # Download CLIP model
        yield f"data: {json.dumps({'model': 'clip', 'status': 'starting'})}\n\n"
        try:
            from core.embeddings import is_downloaded as clip_is_downloaded

            if not clip_is_downloaded():
                yield f"data: {json.dumps({'model': 'clip', 'status': 'downloading'})}\n\n"
                # Import will trigger download
                from core.embeddings import get_text_embedding

                # Make a simple call to ensure model is downloaded
                _ = get_text_embedding("test")
            yield f"data: {json.dumps({'model': 'clip', 'status': 'ready'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'model': 'clip', 'status': 'error', 'error': str(e)})}\n\n"

        # Download BGE text embedding model
        yield f"data: {json.dumps({'model': 'text_embedding', 'status': 'starting'})}\n\n"
        try:
            from core.text_embeddings import is_downloaded as bge_is_downloaded

            if not bge_is_downloaded():
                yield f"data: {json.dumps({'model': 'text_embedding', 'status': 'downloading'})}\n\n"
                from core.text_embeddings import get_text_embedding as get_bge_embedding

                _ = get_bge_embedding("test")
            yield f"data: {json.dumps({'model': 'text_embedding', 'status': 'ready'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'model': 'text_embedding', 'status': 'error', 'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'status': 'complete'})}\n\n"

    return StreamingResponse(
        download_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/migration")
async def get_migration_status():
    """
    Get OCR migration status for existing screenshots.

    Returns progress of OCR processing for screenshots that existed
    before OCR was enabled.
    """
    from api.schemas import MigrationStatus
    from core.database import db

    try:
        stats = db.get_ocr_stats()
        total = stats["total_screenshots"]
        with_ocr = stats["with_ocr"]
        without_ocr = stats["without_ocr"]

        # Calculate progress
        progress_percent = (with_ocr / total * 100) if total > 0 else 100.0

        # Estimate remaining time (roughly 0.4s per image for OCR + embedding)
        estimated_minutes = (without_ocr * 0.4) / 60 if without_ocr > 0 else None

        return MigrationStatus(
            needs_migration=without_ocr > 0,
            total_screenshots=total,
            screenshots_with_ocr=with_ocr,
            screenshots_without_ocr=without_ocr,
            progress_percent=round(progress_percent, 1),
            estimated_time_minutes=round(estimated_minutes, 1) if estimated_minutes else None,
        )
    except Exception:
        return MigrationStatus(
            needs_migration=False,
            total_screenshots=0,
            screenshots_with_ocr=0,
            screenshots_without_ocr=0,
            progress_percent=100.0,
            estimated_time_minutes=None,
        )


@router.get("/enhanced-status")
async def get_enhanced_setup_status():
    """
    Get comprehensive setup status including models and migration.

    Combines version check, model status, and migration progress
    for the setup page.
    """
    from api.schemas import EnhancedSetupStatus

    # Get model status
    models = await get_model_status()

    # Get migration status
    migration = await get_migration_status()

    return EnhancedSetupStatus(
        current_version=VERSION,
        last_seen_version=config.last_seen_version,
        needs_setup=config.last_seen_version != VERSION,
        platform=current_platform.name,
        needs_permission=current_platform.needs_screen_permission(),
        models_ready=models["all_ready"],
        clip_status=models["clip"],
        text_embedding_status=models["text_embedding"],
        ocr_status=models["ocr"],
        migration_status=migration if migration.needs_migration else None,
    )
