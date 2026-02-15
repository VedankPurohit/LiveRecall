"""
LiveRecall Configuration
Platform-specific paths and settings with persistence
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from core.platform import current_platform

# Platform detection - delegate to platform layer
PLATFORM: Literal["macos", "windows", "linux"] = current_platform.name


def get_data_dir() -> Path:
    """Get platform-specific data directory.

    Delegates to the platform abstraction layer.
    """
    return current_platform.get_data_dir()


def get_screenshots_dir() -> Path:
    """Get screenshots storage directory.

    Delegates to the platform abstraction layer.
    """
    return current_platform.get_screenshots_dir()


def get_database_path() -> Path:
    """Get database file path.

    Delegates to the platform abstraction layer.
    """
    return current_platform.get_database_path()


def get_config_path() -> Path:
    """Get config file path.

    Delegates to the platform abstraction layer.
    """
    return current_platform.get_config_path()


@dataclass
class CompressionSettings:
    """Auto-compression settings for old screenshots"""

    enabled: bool = False  # Off by default
    after_days: int = 60  # Compress screenshots older than 2 months
    quality: int = 75  # JPEG quality for compressed images


# =============================================================================
# OCR SETTINGS
# =============================================================================


@dataclass
class OCRSettings:
    """OCR text extraction settings

    Provider options:
    - "auto": Auto-select best for platform (recommended)
    - "apple_vision": macOS native Vision framework (fast, zero memory)
    - "tesseract": Cross-platform Tesseract OCR (lightweight, stable)

    Future provider options (better accuracy, more memory):
    - "paddleocr": PP-OCRv4 (pip install paddleocr paddlepaddle)
    - "doctr": docTR (pip install python-doctr[torch])
    - "easyocr": EasyOCR (pip install easyocr) - heavy, 1-2GB

    To switch providers: Change provider setting, then call ocr_service.recompute_all()
    """

    enabled: bool = True  # OCR enabled by default
    provider: str = "auto"  # "auto", "apple_vision", "tesseract"


@dataclass
class TextEmbeddingSettings:
    """Text embedding model settings for semantic search

    Model options (sentence-transformers):
    - "BAAI/bge-small-en-v1.5": 384-dim, 130MB, MTEB 62.2 (default, good balance)
    - "all-MiniLM-L6-v2": 384-dim, 80MB, MTEB 56.3 (lighter)
    - "thenlper/gte-small": 384-dim, 70MB (lightest)
    - "BAAI/bge-base-en-v1.5": 768-dim, 440MB, MTEB 63.5 (higher accuracy)
    - "all-mpnet-base-v2": 768-dim, 420MB (higher accuracy)

    WARNING: Changing to a model with different dimensions requires:
    1. Update dimensions here
    2. Recreate vector tables (call text_embedding_service.recompute_all())
    """

    model: str = "BAAI/bge-small-en-v1.5"
    dimensions: int = 384  # Must match model output dimensions


@dataclass
class ChunkingSettings:
    """Text chunking settings for semantic search

    Dual chunking strategy:
    - Small chunks: Precise matching, good for short specific queries
    - Large chunks: Better context, good for conceptual queries

    Both sizes are searched and combined using RRF (Reciprocal Rank Fusion).
    """

    small_size: int = 512  # tokens (~2000 chars)
    small_overlap: int = 50  # tokens (~200 chars)
    large_size: int = 2048  # tokens (~8000 chars)
    large_overlap: int = 200  # tokens (~800 chars)


@dataclass
class CaptureSettings:
    """Screen capture settings"""

    mode: str = "normal"
    interval: float = 2.0  # seconds between captures
    threshold: float = 0.9  # SSIM threshold for change detection
    save_threshold: float = 0.6  # SSIM threshold for saving
    quality: int = 95  # JPEG quality (1-100)

    # Preset modes
    MODES = {
        "normal": {"threshold": 0.9, "save_threshold": 0.6, "interval": 2},
        "games": {"threshold": 0.75, "save_threshold": 0.55, "interval": 4},
        "fast": {"threshold": 0.96, "save_threshold": 0.47, "interval": 2},
        "presentation": {"threshold": 0.85, "save_threshold": 0.7, "interval": 3},
        "video": {"threshold": 0.8, "save_threshold": 0.5, "interval": 1},
        "coding": {"threshold": 0.95, "save_threshold": 0.85, "interval": 5},
        "security": {"threshold": 0.98, "save_threshold": 0.9, "interval": 1},
        "timelapse": {"threshold": 0.1, "save_threshold": 0.1, "interval": 30},
    }

    def set_mode(self, mode: str):
        """Apply a capture mode preset"""
        if mode in self.MODES:
            settings = self.MODES[mode]
            self.mode = mode
            self.threshold = settings["threshold"]
            self.save_threshold = settings["save_threshold"]
            self.interval = settings["interval"]


@dataclass
class IncognitoSettings:
    """Incognito/private mode settings - new captures are hidden"""

    active: bool = False
    until: float | None = None  # Unix timestamp when incognito should auto-disable

    # Duration options in minutes
    DURATION_OPTIONS = [5, 15, 30, 60]


@dataclass
class Config:
    """Main configuration"""

    capture: CaptureSettings = field(default_factory=CaptureSettings)
    compression: CompressionSettings = field(default_factory=CompressionSettings)
    incognito: IncognitoSettings = field(default_factory=IncognitoSettings)
    ocr: OCRSettings = field(default_factory=OCRSettings)
    text_embedding: TextEmbeddingSettings = field(default_factory=TextEmbeddingSettings)
    chunking: ChunkingSettings = field(default_factory=ChunkingSettings)
    encryption_enabled: bool = True
    safe_mode_enabled: bool = True
    safe_mode_level: str = "mid"  # low, mid, high
    similarity_metric: str = "cosine"  # "cosine" or "distance"
    last_seen_version: str = ""  # Track version for setup flow

    # Paths (computed)
    @property
    def data_dir(self) -> Path:
        return get_data_dir()

    @property
    def screenshots_dir(self) -> Path:
        return get_screenshots_dir()

    @property
    def database_path(self) -> Path:
        return get_database_path()

    # --- Incognito mode methods ---

    def is_incognito_mode(self) -> bool:
        """Check if incognito mode is currently active and not expired."""
        if not self.incognito.active:
            return False
        if self.incognito.until is None:
            return False

        # Check if expired
        if time.time() > self.incognito.until:
            # Auto-disable expired incognito
            self.incognito.active = False
            self.incognito.until = None
            self.save()
            return False

        return True

    def get_incognito_remaining_seconds(self) -> int:
        """Get seconds remaining in incognito mode, or 0 if not active."""
        if not self.is_incognito_mode():
            return 0
        if self.incognito.until is None:
            return 0
        return max(0, int(self.incognito.until - time.time()))

    def enable_incognito(self, duration_minutes: int):
        """Enable incognito mode with auto-expire after duration."""
        self.incognito.active = True
        self.incognito.until = time.time() + (duration_minutes * 60)
        self.save()

    def disable_incognito(self):
        """Disable incognito mode."""
        self.incognito.active = False
        self.incognito.until = None
        self.save()

    def save(self):
        """Save config to JSON file"""
        config_path = get_config_path()
        data = {
            "capture": {
                "mode": self.capture.mode,
                "interval": self.capture.interval,
                "threshold": self.capture.threshold,
                "save_threshold": self.capture.save_threshold,
                "quality": self.capture.quality,
            },
            "compression": {
                "enabled": self.compression.enabled,
                "after_days": self.compression.after_days,
                "quality": self.compression.quality,
            },
            "incognito": {
                "active": self.incognito.active,
                "until": self.incognito.until,
            },
            "ocr": {
                "enabled": self.ocr.enabled,
                "provider": self.ocr.provider,
            },
            "text_embedding": {
                "model": self.text_embedding.model,
                "dimensions": self.text_embedding.dimensions,
            },
            "chunking": {
                "small_size": self.chunking.small_size,
                "small_overlap": self.chunking.small_overlap,
                "large_size": self.chunking.large_size,
                "large_overlap": self.chunking.large_overlap,
            },
            "encryption_enabled": self.encryption_enabled,
            "safe_mode_enabled": self.safe_mode_enabled,
            "safe_mode_level": self.safe_mode_level,
            "similarity_metric": self.similarity_metric,
            "last_seen_version": self.last_seen_version,
        }
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Load config from JSON file if it exists"""
        config_path = get_config_path()
        if not config_path.exists():
            return

        try:
            with open(config_path) as f:
                data = json.load(f)

            # Load capture settings
            if "capture" in data:
                cap = data["capture"]
                self.capture.mode = cap.get("mode", self.capture.mode)
                self.capture.interval = cap.get("interval", self.capture.interval)
                self.capture.threshold = cap.get("threshold", self.capture.threshold)
                self.capture.save_threshold = cap.get("save_threshold", self.capture.save_threshold)
                self.capture.quality = cap.get("quality", self.capture.quality)

            # Load compression settings
            if "compression" in data:
                comp = data["compression"]
                self.compression.enabled = comp.get("enabled", self.compression.enabled)
                self.compression.after_days = comp.get("after_days", self.compression.after_days)
                self.compression.quality = comp.get("quality", self.compression.quality)

            # Load incognito settings
            if "incognito" in data:
                inc = data["incognito"]
                self.incognito.active = inc.get("active", self.incognito.active)
                self.incognito.until = inc.get("until", self.incognito.until)

            # Load OCR settings
            if "ocr" in data:
                ocr = data["ocr"]
                self.ocr.enabled = ocr.get("enabled", self.ocr.enabled)
                self.ocr.provider = ocr.get("provider", self.ocr.provider)

            # Load text embedding settings
            if "text_embedding" in data:
                te = data["text_embedding"]
                self.text_embedding.model = te.get("model", self.text_embedding.model)
                self.text_embedding.dimensions = te.get("dimensions", self.text_embedding.dimensions)

            # Load chunking settings
            if "chunking" in data:
                chunk = data["chunking"]
                self.chunking.small_size = chunk.get("small_size", self.chunking.small_size)
                self.chunking.small_overlap = chunk.get("small_overlap", self.chunking.small_overlap)
                self.chunking.large_size = chunk.get("large_size", self.chunking.large_size)
                self.chunking.large_overlap = chunk.get("large_overlap", self.chunking.large_overlap)

            # Load other settings
            self.encryption_enabled = data.get("encryption_enabled", self.encryption_enabled)
            self.safe_mode_enabled = data.get("safe_mode_enabled", self.safe_mode_enabled)
            self.safe_mode_level = data.get("safe_mode_level", self.safe_mode_level)
            self.similarity_metric = data.get("similarity_metric", self.similarity_metric)
            self.last_seen_version = data.get("last_seen_version", self.last_seen_version)

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load config: {e}")


# Global config instance
config = Config()
config.load()  # Load saved settings on startup


if __name__ == "__main__":
    print(f"Platform: {PLATFORM}")
    print(f"Data directory: {get_data_dir()}")
    print(f"Screenshots directory: {get_screenshots_dir()}")
    print(f"Database path: {get_database_path()}")
