"""
Tests for API endpoints
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create a test client for the API"""
    # Mock the database connection before importing the app
    with patch("core.database.db") as mock_db:
        mock_db.connect.return_value = mock_db
        mock_db.get_stats.return_value = {
            "total_screenshots": 10,
            "synced": 5,
            "unsynced": 5,
            "compressed": 2,
        }

        from api.main import app
        client = TestClient(app)
        yield client


class TestHealthEndpoints:
    """Test health and status endpoints"""

    @patch("api.routes.status.db")
    @patch("api.routes.status.capture_service")
    @patch("api.routes.status.config")
    @patch("api.routes.status.get_model_status")
    def test_health_check(self, mock_model, mock_config, mock_capture, mock_db):
        """Health endpoint should return ok"""
        from api.routes.status import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    @patch("api.routes.status.db")
    @patch("api.routes.status.capture_service")
    @patch("api.routes.status.config")
    @patch("api.routes.status.get_model_status")
    def test_status_endpoint(self, mock_model, mock_config, mock_capture, mock_db):
        """Status endpoint should return system status"""
        from api.routes.status import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        # Setup mocks
        mock_db.get_stats.return_value = {
            "total_screenshots": 100,
            "synced": 80,
            "unsynced": 20,
        }
        mock_capture.is_running = False
        mock_config.capture.mode = "normal"
        mock_config.capture.interval = 2.0
        mock_config.capture.threshold = 0.9
        mock_config.data_dir = "/test/path"
        mock_model.return_value = {
            "loaded": False,
            "device": None,
            "idle_seconds": 0,
            "auto_unload_seconds": 300,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is True
        assert "recording" in data
        assert "database" in data
        assert "model" in data


class TestConfigEndpoints:
    """Test configuration endpoints"""

    @patch("api.routes.status.db")
    @patch("api.routes.status.config")
    @patch("api.routes.status.get_model_status")
    def test_get_config(self, mock_model, mock_config, mock_db):
        """Should return current configuration"""
        from api.routes.status import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        # Setup mock config
        mock_config.capture.mode = "normal"
        mock_config.capture.interval = 2.0
        mock_config.capture.threshold = 0.9
        mock_config.capture.save_threshold = 0.6
        mock_config.capture.quality = 95
        mock_config.compression.enabled = False
        mock_config.compression.after_days = 60
        mock_config.compression.quality = 85
        mock_config.encryption_enabled = True
        mock_config.safe_mode_enabled = True
        mock_config.safe_mode_level = "mid"
        mock_model.return_value = {"auto_unload_seconds": 300}

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "capture" in data
        assert "compression" in data
        assert data["capture"]["quality"] == 95

    @patch("api.routes.status.db")
    @patch("api.routes.status.config")
    @patch("api.routes.status.set_auto_unload_timeout")
    def test_update_config(self, mock_set_timeout, mock_config, mock_db):
        """Should update configuration"""
        from api.routes.status import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_config.capture.quality = 95
        mock_config.compression.enabled = False

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.put("/config", json={
            "capture_quality": 90,
            "compression_enabled": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestCompressionEndpoints:
    """Test compression API endpoints"""

    @patch("api.routes.compression.compression_service")
    def test_get_compression_status(self, mock_service):
        """Should return compression status"""
        from api.routes.compression import router
        from core.compression import CompressionProgress
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_service.progress = CompressionProgress(
            total=10,
            processed=5,
            errors=0,
            bytes_saved=50000,
            is_running=True,
        )

        app = FastAPI()
        app.include_router(router)  # Router already has /compression prefix
        client = TestClient(app)

        response = client.get("/compression/status")
        assert response.status_code == 200
        data = response.json()
        assert data["is_compressing"] is True
        assert data["total"] == 10
        assert data["processed"] == 5

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    @patch("api.routes.compression.config")
    def test_start_compression(self, mock_config, mock_db, mock_service):
        """Should start compression"""
        from api.routes.compression import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_service.is_running = False
        mock_config.compression.after_days = 60
        mock_config.compression.quality = 85
        mock_db.get_compressible_count.return_value = 10

        app = FastAPI()
        app.include_router(router)  # Router already has /compression prefix
        client = TestClient(app)

        response = client.post("/compression/start")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["compressible_count"] == 10
        mock_service.start.assert_called_once()

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    @patch("api.routes.compression.config")
    def test_start_compression_already_running(self, mock_config, mock_db, mock_service):
        """Should not start if already running"""
        from api.routes.compression import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_service.is_running = True

        app = FastAPI()
        app.include_router(router)  # Router already has /compression prefix
        client = TestClient(app)

        response = client.post("/compression/start")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "already running" in data["message"]

    @patch("api.routes.compression.db")
    @patch("api.routes.compression.config")
    def test_get_compression_stats(self, mock_config, mock_db):
        """Should return compression statistics"""
        from api.routes.compression import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_config.compression.after_days = 60
        mock_db.get_compression_stats.return_value = {
            "compressed_count": 50,
            "uncompressed_count": 100,
            "original_size_bytes": 500000,
        }
        mock_db.get_compressible_count.return_value = 20

        app = FastAPI()
        app.include_router(router)  # Router already has /compression prefix
        client = TestClient(app)

        response = client.get("/compression/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["compressed_count"] == 50
        assert data["compressible_count"] == 20


class TestSearchEndpoints:
    """Test search API endpoints"""

    @patch("api.routes.search.db")
    @patch("api.routes.search.get_text_embedding")
    def test_search_no_synced(self, mock_embedding, mock_db):
        """Should error if no synced screenshots"""
        from api.routes.search import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_db.get_stats.return_value = {"synced": 0}

        app = FastAPI()
        app.include_router(router)  # Router already has /search prefix
        client = TestClient(app)

        response = client.post("/search", json={"query": "test"})
        assert response.status_code == 400
        assert "No synced screenshots" in response.json()["detail"]

    @patch("api.routes.search.db")
    @patch("api.routes.search.get_text_embedding")
    def test_search_success(self, mock_get_embedding, mock_db):
        """Should return search results"""
        from api.routes.search import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_db.get_stats.return_value = {"synced": 10}
        mock_get_embedding.return_value = [0.1] * 768
        mock_db.search_similar.return_value = [
            {
                "id": 1,
                "image_path": "/path/to/img.jpg",
                "timestamp": "251206120000",
                "similarity": 0.85,
            }
        ]

        app = FastAPI()
        app.include_router(router)  # Router already has /search prefix
        client = TestClient(app)

        response = client.post("/search", json={
            "query": "blue shirt",
            "limit": 10,
            "safe_mode": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        assert len(data["results"]) == 1


class TestRecordingEndpoints:
    """Test recording API endpoints"""

    @patch("api.routes.recording.capture_service")
    @patch("api.routes.recording.config")
    def test_start_recording(self, mock_config, mock_service):
        """Should start recording"""
        from api.routes.recording import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_service.is_running = False
        mock_config.capture.mode = "normal"
        mock_config.capture.interval = 2.0
        mock_config.capture.threshold = 0.9

        app = FastAPI()
        app.include_router(router)  # Router already has /recording prefix
        client = TestClient(app)

        response = client.post("/recording/start")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_service.start.assert_called_once()

    @patch("api.routes.recording.capture_service")
    @patch("api.routes.recording.config")
    def test_stop_recording(self, mock_config, mock_service):
        """Should stop recording"""
        from api.routes.recording import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_service.is_running = True
        mock_config.capture.mode = "normal"
        mock_config.capture.interval = 2.0
        mock_config.capture.threshold = 0.9

        app = FastAPI()
        app.include_router(router)  # Router already has /recording prefix
        client = TestClient(app)

        response = client.post("/recording/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_service.stop.assert_called_once()
