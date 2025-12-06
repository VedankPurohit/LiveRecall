"""
LiveRecall Configuration
Platform-specific paths and settings
"""
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal

# Platform detection
PLATFORM: Literal["macos", "windows", "linux"] = (
    "macos" if sys.platform == "darwin"
    else "windows" if sys.platform == "win32"
    else "linux"
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


@dataclass
class CaptureSettings:
    """Screen capture settings"""
    mode: str = "normal"
    interval: float = 2.0  # seconds between captures
    threshold: float = 0.9  # SSIM threshold for change detection
    save_threshold: float = 0.6  # SSIM threshold for saving
    quality: int = 85  # JPEG quality

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
    encryption_enabled: bool = True
    safe_mode_enabled: bool = True
    safe_mode_level: str = "mid"  # low, mid, high

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


# Global config instance
config = Config()


if __name__ == "__main__":
    print(f"Platform: {PLATFORM}")
    print(f"Data directory: {get_data_dir()}")
    print(f"Screenshots directory: {get_screenshots_dir()}")
    print(f"Database path: {get_database_path()}")
