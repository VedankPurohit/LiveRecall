"""
LiveRecall Configuration
Platform-specific paths and settings with persistence
"""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Platform detection
PLATFORM: Literal["macos", "windows", "linux"] = (
    "macos" if sys.platform == "darwin" else "windows" if sys.platform == "win32" else "linux"
)


def get_data_dir() -> Path:
    """Get platform-specific data directory"""
    if PLATFORM == "macos":
        base = Path.home() / "Library" / "Application Support"
    elif PLATFORM == "windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:  # linux
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / "LiveRecall"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_screenshots_dir() -> Path:
    """Get screenshots storage directory"""
    screenshots_dir = get_data_dir() / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    return screenshots_dir


def get_database_path() -> Path:
    """Get database file path"""
    return get_data_dir() / "liverecall.db"


def get_config_path() -> Path:
    """Get config file path"""
    return get_data_dir() / "config.json"


@dataclass
class CompressionSettings:
    """Auto-compression settings for old screenshots"""

    enabled: bool = False  # Off by default
    after_days: int = 60  # Compress screenshots older than 2 months
    quality: int = 85  # JPEG quality for compressed images


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
class Config:
    """Main configuration"""

    capture: CaptureSettings = field(default_factory=CaptureSettings)
    compression: CompressionSettings = field(default_factory=CompressionSettings)
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
