"""
Compression API Routes
Manage old screenshot compression
"""

from fastapi import APIRouter

from api.schemas import (
    CompressionStartRequest,
    CompressionStartResponse,
    CompressionStats,
    CompressionStatus,
)
from core.compression import CompressionProgress, compression_service
from core.config import config
from core.database import db

router = APIRouter(prefix="/compression", tags=["Compression"])


def progress_to_status(progress: CompressionProgress) -> CompressionStatus:
    """Convert internal progress to API schema"""
    return CompressionStatus(
        is_compressing=progress.is_running,
        total=progress.total,
        processed=progress.processed,
        errors=progress.errors,
        bytes_saved=progress.bytes_saved,
        progress_percent=progress.percent,
    )


@router.get("", response_model=CompressionStatus)
@router.get("/status", response_model=CompressionStatus)
async def get_compression_status():
    """Get current compression operation status"""
    return progress_to_status(compression_service.progress)


@router.post("/start", response_model=CompressionStartResponse)
async def start_compression(request: CompressionStartRequest = None):
    """
    Start compressing old screenshots.

    Compresses screenshots older than the specified days (default: 60)
    to a lower quality (default: 85) to save storage space.

    This runs in the background - use /compression/status to monitor progress.

    Important:
    - Already compressed screenshots are skipped (no re-compression)
    - Embeddings are not affected (search still works)
    - Original files are overwritten (not reversible)
    """
    if compression_service.is_running:
        return CompressionStartResponse(
            success=False,
            message="Compression is already running",
            compressible_count=0,
        )

    # Get parameters
    older_than_days = request.older_than_days if request and request.older_than_days else config.compression.after_days
    quality = request.quality if request and request.quality else config.compression.quality

    # Check how many are eligible
    compressible_count = db.get_compressible_count(older_than_days)

    if compressible_count == 0:
        return CompressionStartResponse(
            success=True,
            message=f"No screenshots older than {older_than_days} days to compress",
            compressible_count=0,
        )

    # Start compression in background
    compression_service.start(
        older_than_days=older_than_days,
        quality=quality,
    )

    return CompressionStartResponse(
        success=True,
        message=f"Compression started for {compressible_count} screenshots",
        compressible_count=compressible_count,
    )


@router.post("/stop", response_model=CompressionStatus)
async def stop_compression():
    """Stop the current compression operation"""
    compression_service.stop()
    return progress_to_status(compression_service.progress)


@router.get("/stats", response_model=CompressionStats)
async def get_compression_stats():
    """
    Get compression statistics.

    Shows how many screenshots are compressed, how much space was saved,
    and how many are eligible for compression.
    """
    stats = db.get_compression_stats()
    compressible = db.get_compressible_count(config.compression.after_days)

    # Estimate savings: assume ~50% reduction for compressible images
    # This is a rough estimate based on typical JPEG compression
    estimated_savings = 0
    if compressible > 0 and stats["compressed_count"] > 0:
        # Calculate average savings per image from compressed ones
        avg_original = stats["original_size_bytes"] / stats["compressed_count"]
        estimated_savings = int(compressible * avg_original * 0.5)

    return CompressionStats(
        compressed_count=stats["compressed_count"],
        uncompressed_count=stats["uncompressed_count"],
        compressible_count=compressible,
        original_size_bytes=stats["original_size_bytes"],
        estimated_savings_bytes=estimated_savings,
    )
