"""
Screenshots API Routes
CRUD operations for screenshots
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from api.schemas import (
    Screenshot,
    ScreenshotList,
    ScreenshotDeleteResponse,
    SuccessResponse,
)
from core.database import db
from core.config import get_screenshots_dir

router = APIRouter(prefix="/screenshots", tags=["Screenshots"])


def db_row_to_screenshot(row: dict) -> Screenshot:
    """Convert database row to Screenshot schema"""
    return Screenshot(
        id=row["id"],
        image_path=row["image_path"],
        timestamp=row["timestamp"],
        has_embedding=bool(row["has_embedding"]),
        created_at=row.get("created_at"),
    )


@router.get("", response_model=ScreenshotList)
async def list_screenshots(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    synced_only: bool = Query(default=False),
    unsynced_only: bool = Query(default=False),
):
    """
    List screenshots with pagination.

    - limit: Max number of results (1-500)
    - offset: Skip N results
    - synced_only: Only show screenshots with embeddings
    - unsynced_only: Only show screenshots without embeddings
    """
    if synced_only and unsynced_only:
        raise HTTPException(
            status_code=400,
            detail="Cannot use both synced_only and unsynced_only",
        )

    # Get screenshots from database
    if unsynced_only:
        screenshots = db.get_unsynced_screenshots(limit=limit)
        total = db.get_unsynced_count()
    else:
        screenshots = db.get_all_screenshots(limit=limit, offset=offset)
        stats = db.get_stats()
        if synced_only:
            screenshots = [s for s in screenshots if s["has_embedding"]]
            total = stats["synced"]
        else:
            total = stats["total_screenshots"]

    return ScreenshotList(
        total=total,
        offset=offset,
        limit=limit,
        screenshots=[db_row_to_screenshot(s) for s in screenshots],
    )


@router.get("/{screenshot_id}", response_model=Screenshot)
async def get_screenshot(screenshot_id: int):
    """Get a single screenshot by ID"""
    screenshot = db.get_screenshot(screenshot_id)

    if not screenshot:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return db_row_to_screenshot(screenshot)


@router.get("/{screenshot_id}/image")
async def get_screenshot_image(
    screenshot_id: int,
    decrypt_key: Optional[str] = Query(default=None),
):
    """
    Get the actual screenshot image file.

    If the image is encrypted, provide the decrypt_key parameter.
    For unencrypted images (DevMode), no key is needed.
    """
    screenshot = db.get_screenshot(screenshot_id)

    if not screenshot:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    image_path = Path(screenshot["image_path"])

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    # TODO: Handle decryption if decrypt_key is provided
    # For now, return the file directly

    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
        filename=image_path.name,
    )


@router.delete("/{screenshot_id}", response_model=SuccessResponse)
async def delete_screenshot(screenshot_id: int, delete_file: bool = True):
    """
    Delete a screenshot.

    - delete_file: Also delete the image file from disk (default: true)
    """
    screenshot = db.get_screenshot(screenshot_id)

    if not screenshot:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    # Delete file if requested
    if delete_file:
        image_path = Path(screenshot["image_path"])
        if image_path.exists():
            image_path.unlink()

    # Delete from database
    success = db.delete_screenshot(screenshot_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete screenshot")

    return SuccessResponse(
        success=True,
        message=f"Screenshot {screenshot_id} deleted",
    )


@router.delete("", response_model=ScreenshotDeleteResponse)
async def delete_all_screenshots(
    confirm: bool = Query(default=False),
    delete_files: bool = Query(default=True),
):
    """
    Delete ALL screenshots.

    This is a destructive operation. You must pass confirm=true.

    - confirm: Must be true to proceed
    - delete_files: Also delete image files from disk (default: true)
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="You must pass confirm=true to delete all screenshots",
        )

    stats = db.get_stats()
    total = stats["total_screenshots"]

    if total == 0:
        return ScreenshotDeleteResponse(
            success=True,
            deleted_count=0,
            message="No screenshots to delete",
        )

    # Delete files if requested
    if delete_files:
        screenshots_dir = get_screenshots_dir()
        deleted_files = 0
        for f in screenshots_dir.iterdir():
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                f.unlink()
                deleted_files += 1

    # Clear database
    db.clear_all()

    return ScreenshotDeleteResponse(
        success=True,
        deleted_count=total,
        message=f"Deleted {total} screenshots" + (f" and {deleted_files} files" if delete_files else ""),
    )
