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
