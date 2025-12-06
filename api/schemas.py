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

    class Config:
        json_schema_extra = {
            "example": {
                "query": "blue shirt on website",
                "limit": 20,
                "safe_mode": True,
                "safe_mode_level": "mid"
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


class AppConfig(BaseModel):
    """Application configuration"""
    capture: CaptureConfig
    encryption_enabled: bool
    safe_mode_enabled: bool
    safe_mode_level: SafeModeLevel
    auto_unload_seconds: int


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration"""
    capture_mode: Optional[CaptureMode] = None
    capture_interval: Optional[float] = Field(None, ge=0.5, le=60.0)
    capture_threshold: Optional[float] = Field(None, ge=0.5, le=0.99)
    capture_quality: Optional[int] = Field(None, ge=50, le=100)
    safe_mode_enabled: Optional[bool] = None
    safe_mode_level: Optional[SafeModeLevel] = None
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
