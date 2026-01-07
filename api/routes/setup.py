"""
Setup API Routes
Handle first-run and version-change setup flow for screen recording permissions
"""

import subprocess
import sys

from fastapi import APIRouter, HTTPException

from api.schemas import SetupStatus, SuccessResponse
from core.config import config
from core.updater import VERSION

router = APIRouter(prefix="/setup", tags=["Setup"])


@router.get("/status", response_model=SetupStatus)
async def get_setup_status():
    """
    Check if setup is needed.

    Returns whether the app version has changed since last run,
    which indicates that screen recording permissions may need to be reset.
    """
    needs_setup = config.last_seen_version != VERSION
    return SetupStatus(
        current_version=VERSION,
        last_seen_version=config.last_seen_version,
        needs_setup=needs_setup,
    )


@router.post("/reset-permissions", response_model=SuccessResponse)
async def reset_screen_capture_permissions():
    """
    Reset screen capture permissions for LiveRecall.

    This runs: tccutil reset ScreenCapture com.liverecall.app

    Note: This will prompt the user for their admin password via macOS dialog.
    Only available on macOS.
    """
    if sys.platform != "darwin":
        raise HTTPException(
            status_code=400,
            detail="Permission reset is only available on macOS",
        )

    try:
        # Run tccutil to reset screen capture permissions
        # This will prompt for admin password via macOS system dialog
        result = subprocess.run(
            ["tccutil", "reset", "ScreenCapture", "com.liverecall.app"],
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout for user to enter password
        )

        if result.returncode != 0:
            return SuccessResponse(
                success=False,
                message=f"Permission reset failed: {result.stderr or 'Unknown error'}",
            )

        return SuccessResponse(
            success=True,
            message="Screen capture permissions reset. Please grant permission when prompted.",
        )
    except subprocess.TimeoutExpired:
        return SuccessResponse(
            success=False,
            message="Permission reset timed out. Please try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


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
