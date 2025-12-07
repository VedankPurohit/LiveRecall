"""
LiveRecall API Schemas
Pydantic models for request/response validation
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class CaptureMode(str, Enum):
    """Available capture modes"""
    NORMAL = "normal"
    GAMES = "games"
    FAST = "fast"
    PRESENTATION = "presentation"
    VIDEO = "video"
    CODING = "coding"
    SECURITY = "security"
    TIMELAPSE = "timelapse"


class SafeModeLevel(str, Enum):
    """Safe mode moderation levels"""
    LOW = "low"
    LOWMID = "lowmid"
    MID = "mid"
    MIDHIGH = "midhigh"
    HIGH = "high"
    VERYHIGH = "veryhigh"
    EXTREME = "extreme"


class SimilarityMetric(str, Enum):
    """Similarity calculation method"""
    COSINE = "cosine"
    DISTANCE = "distance"


# =============================================================================
# Recording
# =============================================================================

class RecordingStatus(BaseModel):
    """Recording service status"""
    is_recording: bool
    mode: CaptureMode = CaptureMode.NORMAL
    interval: float = Field(description="Seconds between capture checks")
    threshold: float = Field(description="SSIM threshold for change detection")

    class Config:
        json_schema_extra = {
            "example": {
                "is_recording": True,
                "mode": "normal",
                "interval": 2.0,
                "threshold": 0.9
            }
        }


class RecordingStartRequest(BaseModel):
    """Request to start recording"""
    mode: Optional[CaptureMode] = None
    interval: Optional[float] = Field(None, ge=0.5, le=60.0)
    threshold: Optional[float] = Field(None, ge=0.5, le=0.99)


class RecordingStartResponse(BaseModel):
    """Response after starting recording"""
    success: bool
    message: str
    status: RecordingStatus


# =============================================================================
# Sync
# =============================================================================

class SyncStatus(BaseModel):
    """Sync operation status"""
    is_syncing: bool
    total: int = Field(description="Total screenshots to sync")
    processed: int = Field(description="Screenshots processed so far")
    errors: int = Field(description="Number of errors")
    progress_percent: float = Field(description="Progress percentage")

    class Config:
        json_schema_extra = {
            "example": {
                "is_syncing": True,
                "total": 100,
                "processed": 45,
                "errors": 2,
                "progress_percent": 45.0
            }
        }


# =============================================================================
# Compression
# =============================================================================

class CompressionStatus(BaseModel):
    """Compression operation status"""
    is_compressing: bool
    total: int = Field(description="Total screenshots to compress")
    processed: int = Field(description="Screenshots compressed so far")
    errors: int = Field(description="Number of errors")
    bytes_saved: int = Field(description="Total bytes saved")
    progress_percent: float = Field(description="Progress percentage")


class CompressionStats(BaseModel):
    """Compression statistics"""
    compressed_count: int = Field(description="Number of compressed screenshots")
    uncompressed_count: int = Field(description="Number of uncompressed screenshots")
    compressible_count: int = Field(description="Number eligible for compression")
    original_size_bytes: int = Field(description="Total original size of compressed images")
    estimated_savings_bytes: int = Field(description="Estimated bytes that can be saved")


class CompressionStartRequest(BaseModel):
    """Request to start compression"""
    older_than_days: Optional[int] = Field(None, ge=7, le=365)
    quality: Optional[int] = Field(None, ge=50, le=90)


class CompressionStartResponse(BaseModel):
    """Response after starting compression"""
    success: bool
    message: str
    compressible_count: int


class SyncStartRequest(BaseModel):
    """Request to start sync"""
    batch_size: int = Field(default=10, ge=1, le=100)


class SyncStartResponse(BaseModel):
    """Response after starting sync"""
    success: bool
    message: str
    unsynced_count: int


# =============================================================================
# Search
# =============================================================================

class SearchRequest(BaseModel):
    """Search request"""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    safe_mode: bool = Field(default=True)
    safe_mode_level: SafeModeLevel = Field(default=SafeModeLevel.MID)
    negative_texts: Optional[list[str]] = Field(default=None)
    negative_weight: float = Field(default=1.0, ge=0.0, le=3.0)
    start_date: Optional[str] = Field(default=None, description="Filter after this timestamp (YYMMDDHHMMSS)")
    end_date: Optional[str] = Field(default=None, description="Filter before this timestamp (YYMMDDHHMMSS)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "blue shirt on website",
                "limit": 20,
                "safe_mode": True,
                "safe_mode_level": "mid",
                "start_date": "251201000000",
                "end_date": "251206235959"
            }
        }


class SearchResult(BaseModel):
    """Single search result"""
    id: int
    image_path: str
    timestamp: str
    similarity: float = Field(description="Similarity score 0-1")
    image_url: str = Field(description="URL to fetch the image")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "image_path": "/path/to/screenshot.jpg",
                "timestamp": "251206143022",
                "similarity": 0.89,
                "image_url": "/api/v1/screenshots/42/image"
            }
        }


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    total_results: int
    results: list[SearchResult]


# =============================================================================
# Screenshots
# =============================================================================

class Screenshot(BaseModel):
    """Screenshot metadata"""
    id: int
    image_path: str
    timestamp: str
    has_embedding: bool
    created_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "image_path": "/path/to/screenshot.jpg",
                "timestamp": "251206143022",
                "has_embedding": True,
                "created_at": "2025-12-06 14:30:22"
            }
        }


class ScreenshotList(BaseModel):
    """List of screenshots with pagination"""
    total: int
    offset: int
    limit: int
    screenshots: list[Screenshot]


class DateRange(BaseModel):
    """Date range for screenshots"""
    min_date: Optional[str] = Field(description="Earliest timestamp (YYMMDDHHMMSS)")
    max_date: Optional[str] = Field(description="Latest timestamp (YYMMDDHHMMSS)")


class DensityBucket(BaseModel):
    """Single bucket in timeline density data"""
    start: str = Field(description="Start timestamp (YYMMDDHHMMSS)")
    end: str = Field(description="End timestamp (YYMMDDHHMMSS)")
    count: int = Field(description="Number of screenshots in this bucket")


class DensityResponse(BaseModel):
    """Timeline density data for visualization"""
    buckets: list[DensityBucket]
    total: int = Field(description="Total screenshots in range")
    min_date: Optional[str] = Field(description="Earliest timestamp")
    max_date: Optional[str] = Field(description="Latest timestamp")


class ScreenshotDeleteResponse(BaseModel):
    """Response after deleting screenshots"""
    success: bool
    deleted_count: int
    message: str


# =============================================================================
# Status / Health
# =============================================================================

class DatabaseStats(BaseModel):
    """Database statistics"""
    total_screenshots: int
    synced: int
    unsynced: int
    compressed: int = 0


class ModelStatus(BaseModel):
    """CLIP model status"""
    loaded: bool
    device: Optional[str]
    idle_seconds: float
    auto_unload_seconds: int


class SystemStatus(BaseModel):
    """Overall system status"""
    healthy: bool
    version: str
    recording: RecordingStatus
    database: DatabaseStats
    model: ModelStatus
    data_directory: str

    class Config:
        json_schema_extra = {
            "example": {
                "healthy": True,
                "version": "2.0.0",
                "recording": {
                    "is_recording": False,
                    "mode": "normal",
                    "interval": 2.0,
                    "threshold": 0.9
                },
                "database": {
                    "total_screenshots": 1247,
                    "synced": 1200,
                    "unsynced": 47
                },
                "model": {
                    "loaded": False,
                    "device": None,
                    "idle_seconds": 0,
                    "auto_unload_seconds": 300
                },
                "data_directory": "~/Library/Application Support/LiveRecall"
            }
        }


# =============================================================================
# Config
# =============================================================================

class CaptureConfig(BaseModel):
    """Capture configuration"""
    mode: CaptureMode
    interval: float
    threshold: float
    save_threshold: float
    quality: int


class CompressionConfig(BaseModel):
    """Compression configuration"""
    enabled: bool
    after_days: int
    quality: int


class AppConfig(BaseModel):
    """Application configuration"""
    capture: CaptureConfig
    compression: CompressionConfig
    encryption_enabled: bool
    safe_mode_enabled: bool
    safe_mode_level: SafeModeLevel
    similarity_metric: SimilarityMetric
    auto_unload_seconds: int


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration"""
    capture_mode: Optional[CaptureMode] = None
    capture_interval: Optional[float] = Field(None, ge=0.5, le=60.0)
    capture_threshold: Optional[float] = Field(None, ge=0.5, le=0.99)
    capture_quality: Optional[int] = Field(None, ge=50, le=100)
    compression_enabled: Optional[bool] = None
    compression_after_days: Optional[int] = Field(None, ge=7, le=365)
    compression_quality: Optional[int] = Field(None, ge=50, le=90)
    safe_mode_enabled: Optional[bool] = None
    safe_mode_level: Optional[SafeModeLevel] = None
    similarity_metric: Optional[SimilarityMetric] = None
    auto_unload_seconds: Optional[int] = Field(None, ge=0, le=3600)


# =============================================================================
# Generic Responses
# =============================================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None
