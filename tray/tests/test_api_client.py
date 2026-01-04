"""
Tests for tray/api_client.py
"""

from unittest.mock import MagicMock, patch

from tray.api_client import APIClient, SystemStatus


class TestSystemStatus:
    """Test SystemStatus dataclass"""

    def test_default_values(self):
        """Should have sensible defaults"""
        status = SystemStatus()
        assert status.healthy is False
        assert status.is_recording is False
        assert status.is_syncing is False
        assert status.total_screenshots == 0
        assert status.unsynced == 0
        assert status.recording_mode == "normal"
        assert status.model_loaded is False
        assert status.model_device is None
        assert status.sync_progress == 0
        assert status.sync_total == 0

    def test_custom_values(self):
        """Should accept custom values"""
        status = SystemStatus(
            healthy=True,
            is_recording=True,
            total_screenshots=100,
            recording_mode="fast",
        )
        assert status.healthy is True
        assert status.is_recording is True
        assert status.total_screenshots == 100
        assert status.recording_mode == "fast"


class TestAPIClient:
    """Test APIClient class"""

    def test_init_default_url(self):
        """Should use default base URL"""
        from tray.config import API_BASE_URL

        client = APIClient()
        assert client.base_url == API_BASE_URL

    def test_init_custom_url(self):
        """Should accept custom base URL"""
        custom_url = "http://localhost:9999"
        client = APIClient(base_url=custom_url)
        assert client.base_url == custom_url

    def test_client_property_creates_httpx_client(self):
        """Client property should create httpx client on first access"""
        api_client = APIClient()
        assert api_client._client is None

        # Access the property
        client = api_client.client
        assert client is not None
        assert api_client._client is not None

        # Cleanup
        api_client.close()

    def test_close(self):
        """Close should clean up httpx client"""
        api_client = APIClient()
        _ = api_client.client  # Create client
        assert api_client._client is not None

        api_client.close()
        assert api_client._client is None

    @patch("tray.api_client.httpx.Client")
    def test_health_check_success(self, mock_client_class):
        """Health check should return True on success"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.health_check()

        assert result is True
        mock_client.get.assert_called_once()

    @patch("tray.api_client.httpx.Client")
    def test_health_check_failure(self, mock_client_class):
        """Health check should return False on failure"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.health_check()

        assert result is False

    @patch("tray.api_client.httpx.Client")
    def test_health_check_exception(self, mock_client_class):
        """Health check should return False on exception"""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.health_check()

        assert result is False

    @patch("tray.api_client.httpx.Client")
    def test_get_status_success(self, mock_client_class):
        """Get status should parse response correctly"""
        mock_client = MagicMock()

        # Mock status response
        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {
            "healthy": True,
            "recording": {
                "is_recording": True,
                "mode": "fast",
            },
            "database": {
                "total_screenshots": 100,
                "unsynced": 10,
            },
            "model": {
                "loaded": True,
                "device": "mps",
            },
        }

        # Mock sync status response
        sync_response = MagicMock()
        sync_response.status_code = 200
        sync_response.json.return_value = {
            "is_syncing": True,
            "processed": 5,
            "total": 10,
        }

        mock_client.get.side_effect = [status_response, sync_response]
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        status = api_client.get_status()

        assert status.healthy is True
        assert status.is_recording is True
        assert status.recording_mode == "fast"
        assert status.total_screenshots == 100
        assert status.unsynced == 10
        assert status.model_loaded is True
        assert status.model_device == "mps"
        assert status.is_syncing is True
        assert status.sync_progress == 5
        assert status.sync_total == 10

    @patch("tray.api_client.httpx.Client")
    def test_get_status_failure(self, mock_client_class):
        """Get status should return default status on failure"""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        status = api_client.get_status()

        # Should return default values
        assert status.healthy is False
        assert status.is_recording is False

    @patch("tray.api_client.httpx.Client")
    def test_start_recording_success(self, mock_client_class):
        """Start recording should return True on success"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.start_recording()

        assert result is True
        mock_client.post.assert_called_once()

    @patch("tray.api_client.httpx.Client")
    def test_stop_recording_success(self, mock_client_class):
        """Stop recording should return True on success"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.stop_recording()

        assert result is True

    @patch("tray.api_client.httpx.Client")
    def test_toggle_recording_starts_when_not_recording(self, mock_client_class):
        """Toggle should start recording when not currently recording"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.toggle_recording(currently_recording=False)

        assert result is True
        # Should call start endpoint
        call_url = mock_client.post.call_args[0][0]
        assert "start" in call_url

    @patch("tray.api_client.httpx.Client")
    def test_toggle_recording_stops_when_recording(self, mock_client_class):
        """Toggle should stop recording when currently recording"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.toggle_recording(currently_recording=True)

        assert result is True
        # Should call stop endpoint
        call_url = mock_client.post.call_args[0][0]
        assert "stop" in call_url

    @patch("tray.api_client.httpx.Client")
    def test_start_sync_success(self, mock_client_class):
        """Start sync should return True on success"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.start_sync()

        assert result is True

    @patch("tray.api_client.httpx.Client")
    def test_set_capture_mode_success(self, mock_client_class):
        """Set capture mode should return True on success"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.put.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_client = APIClient()
        result = api_client.set_capture_mode("fast")

        assert result is True
        mock_client.put.assert_called_once()
