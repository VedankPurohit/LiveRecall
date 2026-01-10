"""
Tray application configuration
"""

from core.platform import current_platform

# API settings
API_HOST = "127.0.0.1"
API_PORT = 8742
API_BASE_URL = f"http://{API_HOST}:{API_PORT}/api/v1"

# Web UI settings (served from FastAPI, same port as API)
WEB_UI_URL = f"http://{API_HOST}:{API_PORT}"

# Polling intervals (seconds)
STATUS_POLL_INTERVAL = 2.0
HEALTH_CHECK_TIMEOUT = 5.0
STARTUP_TIMEOUT = 30.0

# Icon sizes (kept for backwards compatibility with tests)
ICON_SIZE_MAC = (22, 22)
ICON_SIZE_DEFAULT = (32, 32)

# Colors (RGB)
COLOR_IDLE = (128, 128, 128)  # Gray
COLOR_RECORDING = (255, 59, 48)  # Red
COLOR_SYNCING = (0, 122, 255)  # Blue
COLOR_ERROR = (255, 149, 0)  # Orange
COLOR_WHITE = (255, 255, 255)

# Platform detection - delegate to platform layer
PLATFORM = current_platform.name


def get_icon_size() -> tuple[int, int]:
    """Get platform-appropriate icon size.

    Delegates to the platform abstraction layer.
    """
    return current_platform.get_tray_icon_size()


# Capture modes available
CAPTURE_MODES = [
    "normal",
    "games",
    "fast",
    "coding",
    "video",
    "presentation",
]
