"""
HTTP client for communicating with the FastAPI backend
"""
import httpx
from typing import Optional
from dataclasses import dataclass

from .config import API_BASE_URL, HEALTH_CHECK_TIMEOUT


@dataclass
class SystemStatus:
    """Parsed system status from API"""
    is_recording: bool = False
    recording_mode: str = "normal"
    total_screenshots: int = 0
    unsynced: int = 0
    is_syncing: bool = False
    sync_progress: int = 0
    sync_total: int = 0
    model_loaded: bool = False
    model_device: Optional[str] = None
    healthy: bool = False


class APIClient:
    """Async HTTP client for LiveRecall API"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=HEALTH_CHECK_TIMEOUT)
        return self._client

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def health_check(self) -> bool:
        """Check if API is responding"""
        try:
            resp = self.client.get(f"{self.base_url}/health")
            return resp.status_code == 200
        except Exception:
            return False

    def get_status(self) -> SystemStatus:
        """Get full system status"""
        status = SystemStatus()
        try:
            resp = self.client.get(f"{self.base_url}/status")
            if resp.status_code == 200:
                data = resp.json()
                status.healthy = data.get("healthy", False)

                # Recording
                recording = data.get("recording", {})
                status.is_recording = recording.get("is_recording", False)
                status.recording_mode = recording.get("mode", "normal")

                # Database
                db = data.get("database", {})
                status.total_screenshots = db.get("total_screenshots", 0)
                status.unsynced = db.get("unsynced", 0)

                # Model
                model = data.get("model", {})
                status.model_loaded = model.get("loaded", False)
                status.model_device = model.get("device")
        except Exception:
            pass

        # Get sync status separately
        try:
            resp = self.client.get(f"{self.base_url}/sync/status")
            if resp.status_code == 200:
                data = resp.json()
                status.is_syncing = data.get("is_syncing", False)
                status.sync_progress = data.get("processed", 0)
                status.sync_total = data.get("total", 0)
        except Exception:
            pass

        return status

    def start_recording(self) -> bool:
        """Start screen recording"""
        try:
            resp = self.client.post(f"{self.base_url}/recording/start")
            return resp.status_code == 200
        except Exception:
            return False

    def stop_recording(self) -> bool:
        """Stop screen recording"""
        try:
            resp = self.client.post(f"{self.base_url}/recording/stop")
            return resp.status_code == 200
        except Exception:
            return False

    def toggle_recording(self, currently_recording: bool) -> bool:
        """Toggle recording state"""
        if currently_recording:
            return self.stop_recording()
        return self.start_recording()

    def start_sync(self) -> bool:
        """Start embedding sync"""
        try:
            resp = self.client.post(f"{self.base_url}/sync/start")
            return resp.status_code == 200
        except Exception:
            return False

    def set_capture_mode(self, mode: str) -> bool:
        """Set capture mode"""
        try:
            resp = self.client.put(
                f"{self.base_url}/config",
                json={"capture_mode": mode}
            )
            return resp.status_code == 200
        except Exception:
            return False


# Global client instance
api_client = APIClient()
