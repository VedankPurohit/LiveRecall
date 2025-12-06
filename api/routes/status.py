"""
Status API Routes
System health and status endpoints
"""
from fastapi import APIRouter

from api.schemas import (
    SystemStatus,
    RecordingStatus,
    DatabaseStats,
    ModelStatus,
    AppConfig,
    CaptureConfig,
    ConfigUpdateRequest,
    SuccessResponse,
    CaptureMode,
    SafeModeLevel,
)
from core.database import db
from core.capture import capture_service
from core.config import config
from core.embeddings import get_model_status, set_auto_unload_timeout

# Version
VERSION = "2.0.0"

router = APIRouter(tags=["Status"])


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    Get overall system status.

    This is the main health check endpoint that provides
    information about all components.
    """
    # Recording status
    recording = RecordingStatus(
        is_recording=capture_service.is_running,
        mode=CaptureMode(config.capture.mode),
        interval=config.capture.interval,
        threshold=config.capture.threshold,
    )

    # Database stats
    stats = db.get_stats()
    database = DatabaseStats(
        total_screenshots=stats["total_screenshots"],
        synced=stats["synced"],
        unsynced=stats["unsynced"],
    )

    # Model status
    model_status = get_model_status()
    model = ModelStatus(
        loaded=model_status["loaded"],
        device=model_status["device"],
        idle_seconds=model_status["idle_seconds"],
        auto_unload_seconds=model_status["auto_unload_seconds"],
    )

    return SystemStatus(
        healthy=True,
        version=VERSION,
        recording=recording,
        database=database,
        model=model,
        data_directory=str(config.data_dir),
    )


@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "version": VERSION}


@router.get("/config", response_model=AppConfig)
async def get_config():
    """Get current application configuration"""
    return AppConfig(
        capture=CaptureConfig(
            mode=CaptureMode(config.capture.mode),
            interval=config.capture.interval,
            threshold=config.capture.threshold,
            save_threshold=config.capture.save_threshold,
            quality=config.capture.quality,
        ),
        encryption_enabled=config.encryption_enabled,
        safe_mode_enabled=config.safe_mode_enabled,
        safe_mode_level=SafeModeLevel(config.safe_mode_level),
        auto_unload_seconds=get_model_status()["auto_unload_seconds"],
    )


@router.put("/config", response_model=SuccessResponse)
async def update_config(request: ConfigUpdateRequest):
    """
    Update application configuration.

    Only provided fields will be updated.
    """
    updated = []

    if request.capture_mode is not None:
        config.capture.set_mode(request.capture_mode.value)
        updated.append(f"capture_mode={request.capture_mode.value}")

    if request.capture_interval is not None:
        config.capture.interval = request.capture_interval
        updated.append(f"capture_interval={request.capture_interval}")

    if request.capture_threshold is not None:
        config.capture.threshold = request.capture_threshold
        updated.append(f"capture_threshold={request.capture_threshold}")

    if request.safe_mode_enabled is not None:
        config.safe_mode_enabled = request.safe_mode_enabled
        updated.append(f"safe_mode_enabled={request.safe_mode_enabled}")

    if request.safe_mode_level is not None:
        config.safe_mode_level = request.safe_mode_level.value
        updated.append(f"safe_mode_level={request.safe_mode_level.value}")

    if request.auto_unload_seconds is not None:
        set_auto_unload_timeout(request.auto_unload_seconds)
        updated.append(f"auto_unload_seconds={request.auto_unload_seconds}")

    if not updated:
        return SuccessResponse(
            success=True,
            message="No changes made",
        )

    return SuccessResponse(
        success=True,
        message=f"Updated: {', '.join(updated)}",
    )
