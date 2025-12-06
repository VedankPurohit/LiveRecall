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
    DateRange,
    DensityBucket,
    DensityResponse,
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
    start_date: Optional[str] = Query(default=None, description="Filter after this timestamp (YYMMDDHHMMSS)"),
    end_date: Optional[str] = Query(default=None, description="Filter before this timestamp (YYMMDDHHMMSS)"),
):
    """
    List screenshots with pagination and optional date filtering.

    - limit: Max number of results (1-500)
    - offset: Skip N results
    - synced_only: Only show screenshots with embeddings
    - unsynced_only: Only show screenshots without embeddings
    - start_date: Filter screenshots after this timestamp (YYMMDDHHMMSS format)
    - end_date: Filter screenshots before this timestamp (YYMMDDHHMMSS format)
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
        screenshots = db.get_all_screenshots(
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )
        total = db.get_screenshots_count(start_date=start_date, end_date=end_date)
        if synced_only:
            screenshots = [s for s in screenshots if s["has_embedding"]]
            # Note: This count is approximate when using synced_only with date filters
            stats = db.get_stats()
            total = stats["synced"]

    return ScreenshotList(
        total=total,
        offset=offset,
        limit=limit,
        screenshots=[db_row_to_screenshot(s) for s in screenshots],
    )


# IMPORTANT: Static routes must come BEFORE dynamic routes
@router.get("/image")
async def get_image_by_path(
    path: str = Query(..., description="Full path to the image file"),
):
    """
    Get an image by its full path.
    Used by the web frontend to display screenshots.
    """
    image_path = Path(path)

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    # Security: Only allow serving files from the screenshots directory
    screenshots_dir = get_screenshots_dir()
    try:
        image_path.relative_to(screenshots_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
        filename=image_path.name,
    )


@router.get("/date-range", response_model=DateRange)
async def get_date_range():
    """
    Get the min and max timestamps of all screenshots.
    Useful for initializing timeline bounds.
    """
    date_range = db.get_date_range()
    return DateRange(
        min_date=date_range["min_date"],
        max_date=date_range["max_date"],
    )


@router.get("/density", response_model=DensityResponse)
async def get_density(
    buckets: int = Query(default=100, ge=10, le=500, description="Number of time buckets"),
):
    """
    Get screenshot density data for timeline visualization.

    Returns counts of screenshots per time bucket across the entire date range.
    Used to render the density bar in the timeline scrubber.

    - buckets: Number of time buckets to divide the range into (10-500)
    """
    density_data = db.get_density_data(buckets=buckets)

    if not density_data:
        return DensityResponse(
            buckets=[],
            total=0,
            min_date=None,
            max_date=None,
        )

    total = sum(b["count"] for b in density_data)

    return DensityResponse(
        buckets=[
            DensityBucket(start=b["start"], end=b["end"], count=b["count"])
            for b in density_data
        ],
        total=total,
        min_date=density_data[0]["start"] if density_data else None,
        max_date=density_data[-1]["end"] if density_data else None,
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
