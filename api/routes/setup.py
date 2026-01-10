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
    Report setup and permission status for the current platform.
    
    Returns:
        SetupStatus: Contains:
            - current_version: the running application version.
            - last_seen_version: the last version recorded in persistent config.
            - needs_setup: `true` if `last_seen_version` is different from `current_version`.
            - needs_permission: `true` if the current platform requires screen recording permission.
            - platform: the name of the current platform.
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
    Reset the operating system's screen capture permission state for the application.
    
    Delegates the reset operation to the current platform implementation and returns a result describing whether the reset succeeded.
    
    Returns:
        SuccessResponse: `success` is `True` if the permission reset succeeded, `False` otherwise; `message` contains a human-readable result or error description.
    
    Raises:
        HTTPException: Raised with status code 500 and the platform-provided error message if the reset operation fails.
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
    Report the system's auto-start-on-login status and whether the current platform supports controlling it.
    
    Returns:
        autostart_status (AutostartStatus): Object with fields:
            - enabled: `true` if auto-start on login is enabled, `false` otherwise.
            - supported: `true` if the current platform supports auto-start control, `false` otherwise.
            - platform: the current platform's name.
    """
    return AutostartStatus(
        enabled=current_platform.is_autostart_enabled(),
        supported=current_platform.name in ("windows", "linux"),
        platform=current_platform.name,
    )


@router.post("/autostart", response_model=SuccessResponse)
async def set_autostart(request: AutostartSetRequest):
    """
    Set whether the application should start automatically on user login.
    
    Parameters:
        request (AutostartSetRequest): Desired auto-start state; set `request.enabled` to `True` to enable auto-start or `False` to disable it.
    
    Returns:
        SuccessResponse: Object with `success` indicating the operation result and a human-readable `message`.
    
    Raises:
        HTTPException: If enabling or disabling auto-start fails (HTTP 500).
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