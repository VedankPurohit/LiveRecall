"""
Incognito Mode API Routes
Timed private mode where captures are hidden by default
"""

from fastapi import APIRouter

from api.schemas import IncognitoSetRequest, IncognitoStatus, SuccessResponse
from core.config import config

router = APIRouter(prefix="/incognito", tags=["Incognito"])


@router.get("", response_model=IncognitoStatus)
@router.get("/status", response_model=IncognitoStatus)
async def get_incognito_status():
    """
    Get current incognito mode status.

    Returns whether incognito is active and remaining time.
    """
    # Check and auto-expire if needed
    is_active = config.is_incognito_mode()

    return IncognitoStatus(
        active=is_active,
        remaining_seconds=config.get_incognito_remaining_seconds(),
        until_timestamp=config.incognito.until if is_active else None,
    )


@router.post("/set", response_model=SuccessResponse)
async def set_incognito_mode(request: IncognitoSetRequest):
    """
    Set incognito mode with duration.

    - duration_minutes: 0 to disable, or 5/15/30/60 minutes to enable

    When enabled, all new captures will be saved as hidden.
    Mode auto-disables after the specified duration.
    """
    if request.duration_minutes <= 0:
        config.disable_incognito()
        return SuccessResponse(
            success=True,
            message="Incognito mode disabled",
        )

    config.enable_incognito(request.duration_minutes)
    return SuccessResponse(
        success=True,
        message=f"Incognito mode enabled for {request.duration_minutes} minutes",
    )


@router.post("/stop", response_model=SuccessResponse)
async def stop_incognito():
    """
    Stop incognito mode immediately.

    Alternative to set with duration_minutes=0.
    """
    config.disable_incognito()
    return SuccessResponse(
        success=True,
        message="Incognito mode disabled",
    )
