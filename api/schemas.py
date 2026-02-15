"""
LiveRecall API Schemas
Pydantic models for request/response validation
"""

from enum import Enum

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


class VisibilityFilter(str, Enum):
    """Visibility filter for screenshots"""

    VISIBLE_ONLY = "visible_only"
    HIDDEN_ONLY = "hidden_only"
    ALL = "all"


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
        json_schema_extra = {"example": {"is_recording": True, "mode": "normal", "interval": 2.0, "threshold": 0.9}}


class RecordingStartRequest(BaseModel):
    """Request to start recording"""

    mode: CaptureMode | None = None
    interval: float | None = Field(None, ge=0.5, le=60.0)
    threshold: float | None = Field(None, ge=0.5, le=0.99)


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
            "example": {"is_syncing": True, "total": 100, "processed": 45, "errors": 2, "progress_percent": 45.0}
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

    older_than_days: int | None = Field(None, ge=7, le=365)
    quality: int | None = Field(None, ge=50, le=90)


class CompressionStartResponse(BaseModel):
    """Response after starting compression"""

    success: bool
    message: str
    compressible_count: int


class ForceRecompressPreviewRequest(BaseModel):
    """Request to preview force recompression"""

    older_than_days: int = Field(ge=30, le=365)


class ForceRecompressPreviewResponse(BaseModel):
    """Preview of force recompression impact"""

    total_count: int
    already_compressed_count: int
    not_compressed_count: int
    warning: str


class ForceRecompressRequest(BaseModel):
    """Request to start force recompression"""

    older_than_days: int = Field(ge=30, le=365)
    quality: int | None = Field(None, ge=50, le=90)
    confirm: bool = False


class ForceRecompressResponse(BaseModel):
    """Response after starting force recompression"""

    success: bool
    message: str
    affected_count: int


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


class SearchMode(str, Enum):
    """Available search modes"""

    AUTO = "auto"  # Hybrid - combines all methods (default)
    IMAGE = "image"  # CLIP image semantic search only
    TEXT_FUZZY = "text_fuzzy"  # FTS5 trigram text search only
    TEXT_SEMANTIC = "text_semantic"  # BGE text embedding search only


class SearchRequest(BaseModel):
    """Search request with mode selection"""

    query: str = Field(default="", max_length=500)
    image: int | str | None = Field(
        default=None, description="Screenshot ID (int) or base64 image data (string) to use as image query"
    )
    limit: int = Field(default=20, ge=1, le=100)
    search_mode: SearchMode = Field(
        default=SearchMode.AUTO,
        description="Search mode: 'auto' (hybrid), 'image', 'text_fuzzy', 'text_semantic'",
    )
    safe_mode: bool = Field(default=False)  # Off by default for personal recall app
    safe_mode_level: SafeModeLevel = Field(default=SafeModeLevel.MID)
    negative_texts: list[str] | None = Field(default=None)
    negative_weight: float = Field(default=1.0, ge=0.0, le=3.0)
    start_date: str | None = Field(default=None, description="Filter after this timestamp (YYMMDDHHMMSS)")
    end_date: str | None = Field(default=None, description="Filter before this timestamp (YYMMDDHHMMSS)")
    visibility: VisibilityFilter = Field(default=VisibilityFilter.VISIBLE_ONLY, description="Filter by visibility")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "blue shirt on website",
                "limit": 20,
                "search_mode": "auto",
                "safe_mode": True,
                "safe_mode_level": "mid",
                "start_date": "251201000000",
                "end_date": "251206235959",
                "visibility": "visible_only",
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
                "image_url": "/api/v1/screenshots/42/image",
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
    is_hidden: bool = False
    created_at: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "image_path": "/path/to/screenshot.jpg",
                "timestamp": "251206143022",
                "has_embedding": True,
                "is_hidden": False,
                "created_at": "2025-12-06 14:30:22",
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

    min_date: str | None = Field(description="Earliest timestamp (YYMMDDHHMMSS)")
    max_date: str | None = Field(description="Latest timestamp (YYMMDDHHMMSS)")


class DensityBucket(BaseModel):
    """Single bucket in timeline density data"""

    start: str = Field(description="Start timestamp (YYMMDDHHMMSS)")
    end: str = Field(description="End timestamp (YYMMDDHHMMSS)")
    count: int = Field(description="Number of screenshots in this bucket")


class DensityResponse(BaseModel):
    """Timeline density data for visualization"""

    buckets: list[DensityBucket]
    total: int = Field(description="Total screenshots in range")
    min_date: str | None = Field(description="Earliest timestamp")
    max_date: str | None = Field(description="Latest timestamp")


class ScreenshotDeleteResponse(BaseModel):
    """Response after deleting screenshots"""

    success: bool
    deleted_count: int
    message: str


class ScreenshotOCRResponse(BaseModel):
    """Response containing OCR text for a screenshot"""

    has_ocr: bool = Field(description="Whether OCR has been processed for this screenshot")
    text: str = Field(default="", description="Extracted text from the screenshot")
    confidence: float | None = Field(default=None, description="OCR confidence score (0-1)")
    word_count: int = Field(default=0, description="Number of words extracted")

    class Config:
        json_schema_extra = {
            "example": {
                "has_ocr": True,
                "text": "Hello World\nThis is extracted text from the screenshot.",
                "confidence": 0.95,
                "word_count": 8,
            }
        }


# =============================================================================
# Bulk Operations
# =============================================================================


class BulkOperationRequest(BaseModel):
    """Request for bulk screenshot operations"""

    screenshot_ids: list[int] = Field(..., min_length=1, max_length=1000)


class BulkOperationResponse(BaseModel):
    """Response for bulk screenshot operations"""

    success: bool
    affected_count: int
    message: str


# =============================================================================
# Incognito Mode
# =============================================================================


class IncognitoStatus(BaseModel):
    """Incognito mode status"""

    active: bool
    remaining_seconds: int
    until_timestamp: float | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "active": True,
                "remaining_seconds": 847,
                "until_timestamp": 1704567890.123,
            }
        }


class IncognitoSetRequest(BaseModel):
    """Request to set incognito mode"""

    duration_minutes: int = Field(..., ge=0, le=120, description="0 to disable, or 5/15/30/60 minutes")


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
    device: str | None
    idle_seconds: float
    auto_unload_seconds: int


class SystemStatus(BaseModel):
    """Overall system status"""

    healthy: bool
    version: str
    recording: RecordingStatus
    database: DatabaseStats
    model: ModelStatus
    incognito: IncognitoStatus
    data_directory: str

    class Config:
        json_schema_extra = {
            "example": {
                "healthy": True,
                "version": "2.0.0",
                "recording": {"is_recording": False, "mode": "normal", "interval": 2.0, "threshold": 0.9},
                "database": {"total_screenshots": 1247, "synced": 1200, "unsynced": 47},
                "model": {"loaded": False, "device": None, "idle_seconds": 0, "auto_unload_seconds": 300},
                "incognito": {"active": False, "remaining_seconds": 0, "until_timestamp": None},
                "data_directory": "~/Library/Application Support/LiveRecall",
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
    max_time_without_save: float


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

    capture_mode: CaptureMode | None = None
    capture_interval: float | None = Field(None, ge=0.5, le=60.0)
    capture_threshold: float | None = Field(None, ge=0.5, le=0.99)
    capture_quality: int | None = Field(None, ge=50, le=100)
    capture_max_time_without_save: float | None = Field(None, ge=0, le=120)
    compression_enabled: bool | None = None
    compression_after_days: int | None = Field(None, ge=7, le=365)
    compression_quality: int | None = Field(None, ge=50, le=90)
    safe_mode_enabled: bool | None = None
    safe_mode_level: SafeModeLevel | None = None
    similarity_metric: SimilarityMetric | None = None
    auto_unload_seconds: int | None = Field(None, ge=0, le=3600)


# =============================================================================
# Setup
# =============================================================================


class SetupStatus(BaseModel):
    """Setup status for version change detection"""

    current_version: str
    last_seen_version: str
    needs_setup: bool
    needs_permission: bool  # Whether platform needs screen permission
    platform: str  # Current platform (macos, windows, linux)


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
    detail: str | None = None


# =============================================================================
# OCR Types
# =============================================================================


class OCRResult(BaseModel):
    """Result from OCR text extraction"""

    text: str = Field(description="Extracted text (may be empty)")
    confidence: float | None = Field(default=None, description="Average confidence 0-1")
    word_count: int = Field(default=0, description="Number of words extracted")
    language: str = Field(default="en", description="Detected language")


class ChunkInfo(BaseModel):
    """A single text chunk with position info"""

    text: str
    start_char: int
    end_char: int
    index: int


class ChunkedText(BaseModel):
    """Result of dual-size chunking"""

    small: list[ChunkInfo] = Field(description="Small chunks (512 tokens)")
    large: list[ChunkInfo] = Field(description="Large chunks (2048 tokens)")


class OCRStats(BaseModel):
    """OCR processing statistics"""

    total_screenshots: int
    with_ocr: int = Field(description="Screenshots with OCR processed")
    without_ocr: int = Field(description="Screenshots pending OCR")
    with_text: int = Field(description="Screenshots with non-empty text")
    avg_confidence: float | None = Field(description="Average OCR confidence")


# =============================================================================
# Search Types
# =============================================================================


class MatchSource(str, Enum):
    """Source that contributed to a search match"""

    IMAGE = "image"  # CLIP image similarity
    TEXT_FTS = "text_fts"  # FTS5 fuzzy text match
    TEXT_SEMANTIC_SMALL = "text_semantic_small"  # BGE small chunk match
    TEXT_SEMANTIC_LARGE = "text_semantic_large"  # BGE large chunk match


class EnhancedSearchResult(BaseModel):
    """Search result with OCR information"""

    id: int
    image_path: str
    timestamp: str
    similarity: float = Field(description="Combined similarity score 0-1")
    image_url: str = Field(description="URL to fetch the image")
    match_sources: list[MatchSource] = Field(
        default_factory=list,
        description="Which search methods matched this result",
    )
    ocr_snippet: str | None = Field(
        default=None,
        description="Highlighted text snippet if text search matched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "image_path": "/path/to/screenshot.jpg",
                "timestamp": "251206143022",
                "similarity": 0.89,
                "image_url": "/api/v1/screenshots/42/image",
                "match_sources": ["image", "text_fts"],
                "ocr_snippet": "...searched **term** found here...",
            }
        }


# =============================================================================
# Model Download Types
# =============================================================================


class ModelEventType(str, Enum):
    """Types of model-related events for SSE"""

    DOWNLOAD_STARTED = "download_started"
    DOWNLOAD_PROGRESS = "download_progress"
    DOWNLOAD_COMPLETE = "download_complete"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class ModelType(str, Enum):
    """Types of ML models used"""

    CLIP = "clip"
    TEXT_EMBEDDING = "text_embedding"
    OCR = "ocr"


class ModelEvent(BaseModel):
    """SSE event for model download/loading progress"""

    event: ModelEventType
    model: ModelType
    progress: float | None = Field(default=None, ge=0, le=100, description="Download progress 0-100")
    size_mb: int | None = Field(default=None, description="Total size in MB")
    message: str | None = Field(default=None, description="Status message")


class AllModelsStatus(BaseModel):
    """Status of all ML models"""

    clip: ModelStatus
    text_embedding: ModelStatus | None = Field(
        default=None,
        description="Text embedding model status (BGE)",
    )
    ocr: str = Field(
        default="ready",
        description="OCR status: 'ready', 'not_available', provider name",
    )


# =============================================================================
# Enhanced Sync Types
# =============================================================================


class EnhancedSyncStatus(BaseModel):
    """Sync status with OCR tracking"""

    is_syncing: bool
    total: int = Field(description="Total screenshots to process")
    processed: int = Field(description="Screenshots fully processed")
    errors: int = Field(description="Number of errors")
    progress_percent: float = Field(description="Overall progress percentage")

    # Detailed breakdown
    current_phase: str = Field(
        default="",
        description="Current phase: 'embedding', 'ocr', 'text_embedding'",
    )
    embeddings_done: int = Field(default=0, description="CLIP embeddings completed")
    ocr_done: int = Field(default=0, description="OCR extractions completed")
    text_embeddings_done: int = Field(default=0, description="Text embeddings completed")

    class Config:
        json_schema_extra = {
            "example": {
                "is_syncing": True,
                "total": 100,
                "processed": 45,
                "errors": 2,
                "progress_percent": 45.0,
                "current_phase": "ocr",
                "embeddings_done": 100,
                "ocr_done": 45,
                "text_embeddings_done": 40,
            }
        }


# =============================================================================
# OCR Config Types
# =============================================================================


class OCRConfig(BaseModel):
    """OCR configuration settings"""

    enabled: bool = Field(default=True, description="Whether OCR is enabled")
    provider: str = Field(
        default="auto",
        description="OCR provider: 'auto', 'apple_vision', 'tesseract'",
    )


class TextEmbeddingConfig(BaseModel):
    """Text embedding configuration settings"""

    model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Sentence transformer model name",
    )
    dimensions: int = Field(default=384, description="Embedding dimensions")


class ChunkingConfig(BaseModel):
    """Text chunking configuration settings"""

    small_size: int = Field(default=512, description="Small chunk size in tokens")
    small_overlap: int = Field(default=50, description="Small chunk overlap in tokens")
    large_size: int = Field(default=2048, description="Large chunk size in tokens")
    large_overlap: int = Field(default=200, description="Large chunk overlap in tokens")


# =============================================================================
# Migration Types
# =============================================================================


class MigrationStatus(BaseModel):
    """Status of OCR migration for existing screenshots"""

    needs_migration: bool = Field(description="Whether there are screenshots needing OCR")
    total_screenshots: int = Field(description="Total number of screenshots")
    screenshots_with_ocr: int = Field(description="Screenshots with OCR completed")
    screenshots_without_ocr: int = Field(description="Screenshots pending OCR")
    progress_percent: float = Field(description="Migration progress percentage")
    estimated_time_minutes: float | None = Field(
        default=None,
        description="Estimated time to complete in minutes",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "needs_migration": True,
                "total_screenshots": 1000,
                "screenshots_with_ocr": 350,
                "screenshots_without_ocr": 650,
                "progress_percent": 35.0,
                "estimated_time_minutes": 26.0,
            }
        }


# =============================================================================
# Analytics Types
# =============================================================================


class AnalyticsOverviewResponse(BaseModel):
    """Overview statistics for the analytics dashboard"""

    total_screenshots: int
    total_storage_bytes: int
    compressed_count: int
    avg_file_size: int
    screenshots_today: int
    screenshots_yesterday: int
    screenshots_this_week: int
    ocr_processed_count: int


class StorageDailyData(BaseModel):
    date: str
    screenshots: int
    bytes_added: int
    cumulative_bytes: int


class StorageCompression(BaseModel):
    compressed_count: int
    uncompressed_count: int
    original_bytes: int
    current_bytes: int
    bytes_saved: int


class StorageMonthEntry(BaseModel):
    month: str
    bytes: int
    count: int


class StorageLargestFile(BaseModel):
    path: str
    size: int
    timestamp: str


class AnalyticsStorageResponse(BaseModel):
    """Storage analytics breakdown"""

    daily_data: list[StorageDailyData]
    compression: StorageCompression
    largest_files: list[StorageLargestFile]
    storage_by_month: list[StorageMonthEntry]


class HourlyDistribution(BaseModel):
    hour: int
    count: int


class DailyDistribution(BaseModel):
    day: str
    count: int


class WeeklyTrend(BaseModel):
    week: str
    count: int


class HeatmapItem(BaseModel):
    date: str
    day_of_week: int
    day_label: str
    hour: int
    count: int


class AnalyticsActivityResponse(BaseModel):
    """Activity distribution analytics"""

    heatmap_data: list[HeatmapItem]
    hourly_distribution: list[HourlyDistribution]
    daily_distribution: list[DailyDistribution]
    weekly_trend: list[WeeklyTrend]
    peak_hour: int
    peak_day: str
    total_in_period: int


class WeekHeatmapItem(BaseModel):
    date: str
    day_of_week: int
    day_label: str
    hour: int
    count: int
    screenshot_ids: list[int]


class WeekPeak(BaseModel):
    day: str
    hour: int
    count: int


class AnalyticsActivityWeekResponse(BaseModel):
    """Week-based activity heatmap"""

    week_start: str
    week_end: str
    week_offset: int
    heatmap_data: list[WeekHeatmapItem]
    total_screenshots: int
    peak: WeekPeak | None


class GapEntry(BaseModel):
    start_time: str
    end_time: str
    duration_seconds: int
    type: str


class AnalyticsGapsResponse(BaseModel):
    """Timeline gaps analytics"""

    gaps: list[GapEntry]
    total_gap_time_seconds: int
    longest_gap_seconds: int
    avg_gap_seconds: int
    gap_count: int


class SizeDistributionEntry(BaseModel):
    range: str
    count: int


class QualityCompressionStats(BaseModel):
    compressed_count: int
    uncompressed_count: int
    original_bytes_before_compression: int


class AnalyticsQualityResponse(BaseModel):
    """File quality and size distribution"""

    avg_file_size: int
    min_file_size: int
    max_file_size: int
    median_file_size: int
    size_distribution: list[SizeDistributionEntry]
    total_files: int
    compression_stats: QualityCompressionStats


class TrendsDailyData(BaseModel):
    date: str
    count: int
    moving_avg: float


class TrendsDayInfo(BaseModel):
    date: str | None
    count: int


class TrendsSummary(BaseModel):
    total_screenshots: int
    synced_count: int
    ocr_processed_count: int
    avg_per_day: float
    days_with_recordings: int
    best_day: TrendsDayInfo | None
    worst_day: TrendsDayInfo | None


class AnalyticsTrendsResponse(BaseModel):
    """Screenshot trends over time"""

    daily_data: list[TrendsDailyData]
    summary: TrendsSummary


class EnhancedSetupStatus(BaseModel):
    """Comprehensive setup status including models and migration"""

    # Version info
    current_version: str
    last_seen_version: str
    needs_setup: bool = Field(description="Whether version-based setup is needed")

    # Platform info
    platform: str = Field(description="Current platform (macos, windows, linux)")
    needs_permission: bool = Field(description="Whether screen permission is needed")

    # Model status
    models_ready: bool = Field(description="Whether all required models are ready")
    clip_status: str = Field(description="CLIP status: 'not_downloaded', 'downloading', 'ready'")
    text_embedding_status: str = Field(description="Text embedding status: 'not_downloaded', 'downloading', 'ready'")
    ocr_status: str = Field(description="OCR status: 'ready', 'not_available'")

    # Migration info
    migration_status: MigrationStatus | None = Field(
        default=None,
        description="OCR migration status if applicable",
    )
