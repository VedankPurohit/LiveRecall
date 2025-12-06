"""
Recording API Routes
Control screen capture recording
"""
from fastapi import APIRouter, HTTPException

from api.schemas import (
    RecordingStatus,
    RecordingStartRequest,
    RecordingStartResponse,
    SuccessResponse,
    CaptureMode,
)
from core.capture import capture_service
from core.config import config

router = APIRouter(prefix="/recording", tags=["Recording"])


def get_recording_status() -> RecordingStatus:
    """Helper to get current recording status"""
    return RecordingStatus(
        is_recording=capture_service.is_running,
        mode=CaptureMode(config.capture.mode),
        interval=config.capture.interval,
        threshold=config.capture.threshold,
    )


@router.get("", response_model=RecordingStatus)
@router.get("/status", response_model=RecordingStatus)
async def get_status():
    """Get current recording status"""
    return get_recording_status()


@router.post("/start", response_model=RecordingStartResponse)
async def start_recording(request: RecordingStartRequest = None):
    """
    Start screen capture recording.

    Recording is lightweight - it only captures screenshots and saves them
    to the database WITHOUT generating CLIP embeddings. Use /sync to
    process screenshots for search.
    """
    if capture_service.is_running:
        return RecordingStartResponse(
            success=False,
            message="Recording is already running",
            status=get_recording_status(),
        )

    # Apply optional settings
    if request:
        if request.mode:
            config.capture.set_mode(request.mode.value)
        if request.interval is not None:
            config.capture.interval = request.interval
        if request.threshold is not None:
            config.capture.threshold = request.threshold

    # Start capture
    capture_service.start()

    return RecordingStartResponse(
        success=True,
        message="Recording started",
        status=get_recording_status(),
    )


@router.post("/stop", response_model=RecordingStartResponse)
async def stop_recording():
    """Stop screen capture recording"""
    if not capture_service.is_running:
        return RecordingStartResponse(
            success=False,
            message="Recording is not running",
            status=get_recording_status(),
        )

    capture_service.stop()

    return RecordingStartResponse(
        success=True,
        message="Recording stopped",
        status=get_recording_status(),
    )


@router.post("/mode/{mode}", response_model=RecordingStatus)
async def set_capture_mode(mode: CaptureMode):
    """
    Set capture mode preset.

    Available modes:
    - normal: Balanced settings for everyday use
    - games: Less frequent captures for gaming
    - fast: Higher sensitivity for more captures
    - presentation: Optimized for slide decks
    - video: Captures key scenes in videos
    - coding: Tracks meaningful code changes
    - security: Minimizes false triggers
    - timelapse: Regular interval captures
    """
    config.capture.set_mode(mode.value)
    return get_recording_status()


@router.post("/capture", response_model=SuccessResponse)
async def capture_now():
    """
    Capture a screenshot immediately.

    This captures a single screenshot regardless of whether
    continuous recording is running.
    """
    try:
        filepath = capture_service.capture_now()
        return SuccessResponse(
            success=True,
            message=f"Screenshot captured: {filepath}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
