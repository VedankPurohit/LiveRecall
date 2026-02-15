"""
Tests for API endpoints
"""

from unittest.mock import patch

import pytest
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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.status import router

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.status import router

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.status import router

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
        mock_config.similarity_metric = "cosine"
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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.status import router

        mock_config.capture.quality = 95
        mock_config.compression.enabled = False

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.put(
            "/config",
            json={
                "capture_quality": 90,
                "compression_enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestCompressionEndpoints:
    """Test compression API endpoints"""

    @patch("api.routes.compression.compression_service")
    def test_get_compression_status(self, mock_service):
        """Should return compression status"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router
        from core.compression import CompressionProgress

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

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

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    def test_force_recompress_preview(self, mock_db, mock_service):
        """Should return force recompress preview"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

        mock_db.get_force_recompressible_count.return_value = {
            "total": 100,
            "already_compressed": 30,
            "not_compressed": 70,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/compression/force-recompress/preview",
            json={"older_than_days": 60},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 100
        assert data["already_compressed_count"] == 30
        assert data["not_compressed_count"] == 70

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    def test_force_recompress_preview_with_warning(self, mock_db, mock_service):
        """Should include warning when already-compressed screenshots exist"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

        mock_db.get_force_recompressible_count.return_value = {
            "total": 50,
            "already_compressed": 20,
            "not_compressed": 30,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/compression/force-recompress/preview",
            json={"older_than_days": 90},
        )
        assert response.status_code == 200
        data = response.json()
        assert "20" in data["warning"]
        assert "already compressed" in data["warning"]

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    def test_force_recompress_requires_confirm(self, mock_db, mock_service):
        """Should reject without confirm=true"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/compression/force-recompress",
            json={"older_than_days": 60, "confirm": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "confirm" in data["message"].lower()

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    def test_force_recompress_already_running(self, mock_db, mock_service):
        """Should not start if compression already running"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

        mock_service.is_running = True

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/compression/force-recompress",
            json={"older_than_days": 60, "confirm": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "already running" in data["message"]

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    def test_force_recompress_success(self, mock_db, mock_service):
        """Should start force recompression"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

        mock_service.is_running = False
        mock_db.get_force_recompressible_count.return_value = {
            "total": 50,
            "already_compressed": 10,
            "not_compressed": 40,
        }
        mock_service.start_force_recompress.return_value = True

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/compression/force-recompress",
            json={"older_than_days": 60, "confirm": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["affected_count"] == 50
        mock_service.start_force_recompress.assert_called_once()

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    def test_force_recompress_no_eligible(self, mock_db, mock_service):
        """Should handle no eligible screenshots"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

        mock_service.is_running = False
        mock_db.get_force_recompressible_count.return_value = {
            "total": 0,
            "already_compressed": 0,
            "not_compressed": 0,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/compression/force-recompress",
            json={"older_than_days": 365, "confirm": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["affected_count"] == 0

    @patch("api.routes.compression.compression_service")
    @patch("api.routes.compression.db")
    def test_force_recompress_start_fails(self, mock_db, mock_service):
        """Should handle TOCTOU race where start returns False"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.compression import router

        mock_service.is_running = False
        mock_db.get_force_recompressible_count.return_value = {
            "total": 10,
            "already_compressed": 5,
            "not_compressed": 5,
        }
        mock_service.start_force_recompress.return_value = False

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/compression/force-recompress",
            json={"older_than_days": 60, "confirm": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "failed" in data["message"].lower() or "already" in data["message"].lower()


class TestSearchEndpoints:
    """Test search API endpoints"""

    @patch("api.routes.search.db")
    @patch("api.routes.search.get_text_embedding")
    def test_search_no_synced(self, mock_embedding, mock_db):
        """Should error if no synced screenshots"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.search import router

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.search import router

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

        response = client.post(
            "/search",
            json={
                "query": "blue shirt",
                "limit": 10,
                "safe_mode": False,
                "search_mode": "image",  # Use image mode to test CLIP-only search
            },
        )
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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.recording import router

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.recording import router

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


class TestSetupEndpoints:
    """Test setup API endpoints for version-change detection"""

    @patch("api.routes.setup.config")
    @patch("api.routes.setup.VERSION", "0.1.2")
    def test_get_setup_status_needs_setup(self, mock_config):
        """Should return needs_setup=True when version differs"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        mock_config.last_seen_version = "0.1.1"

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/setup/status")
        assert response.status_code == 200
        data = response.json()
        assert data["current_version"] == "0.1.2"
        assert data["last_seen_version"] == "0.1.1"
        assert data["needs_setup"] is True

    @patch("api.routes.setup.config")
    @patch("api.routes.setup.VERSION", "0.1.2")
    def test_get_setup_status_no_setup_needed(self, mock_config):
        """Should return needs_setup=False when version matches"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        mock_config.last_seen_version = "0.1.2"

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/setup/status")
        assert response.status_code == 200
        data = response.json()
        assert data["needs_setup"] is False

    @patch("api.routes.setup.config")
    @patch("api.routes.setup.VERSION", "0.1.2")
    def test_get_setup_status_first_run(self, mock_config):
        """Should return needs_setup=True on first run (empty version)"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        mock_config.last_seen_version = ""

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/setup/status")
        assert response.status_code == 200
        data = response.json()
        assert data["needs_setup"] is True

    @patch("api.routes.setup.current_platform")
    def test_reset_permissions_macos(self, mock_platform):
        """Should run tccutil on macOS (via platform abstraction)"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        # Mock the platform to simulate macOS behavior
        mock_platform.reset_screen_permission.return_value = (
            True,
            "Screen capture permissions reset.",
        )

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post("/setup/reset-permissions")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_platform.reset_screen_permission.assert_called_once()

    @patch("api.routes.setup.current_platform")
    def test_reset_permissions_windows(self, mock_platform):
        """Should succeed on Windows (no-op via platform abstraction)"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        # Mock the platform to simulate Windows behavior
        mock_platform.reset_screen_permission.return_value = (
            True,
            "No permission reset needed on Windows.",
        )

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post("/setup/reset-permissions")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Windows" in data["message"] or "No permission" in data["message"]

    @patch("api.routes.setup.config")
    @patch("api.routes.setup.VERSION", "0.1.2")
    def test_complete_setup(self, mock_config):
        """Should update last_seen_version and save"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post("/setup/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert mock_config.last_seen_version == "0.1.2"
        mock_config.save.assert_called_once()


class TestEventsEndpoints:
    """Test SSE events API endpoints"""

    @patch("api.routes.events.db")
    def test_get_all_status(self, mock_db):
        """Should return status of all models and sync"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.events import router

        mock_db.get_ocr_stats.return_value = {
            "with_ocr": 50,
            "without_ocr": 10,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/events/status")
        assert response.status_code == 200
        data = response.json()
        assert "clip" in data
        assert "text_embedding" in data
        assert "ocr" in data
        assert "sync" in data
        assert "ocr_stats" in data


class TestEnhancedSetupEndpoints:
    """Test enhanced setup API endpoints"""

    @patch("api.routes.setup.config")
    @patch("api.routes.setup.current_platform")
    @patch("api.routes.setup.VERSION", "0.1.2")
    def test_get_model_status(self, mock_platform, mock_config):
        """Should return model status"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/setup/models")
        assert response.status_code == 200
        data = response.json()
        assert "clip" in data
        assert "text_embedding" in data
        assert "ocr" in data
        assert "all_ready" in data

    @patch("core.database.db")
    @patch("api.routes.setup.config")
    @patch("api.routes.setup.current_platform")
    @patch("api.routes.setup.VERSION", "0.1.2")
    def test_get_migration_status(self, mock_platform, mock_config, mock_db):
        """Should return OCR migration status"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        mock_db.get_ocr_stats.return_value = {
            "total_screenshots": 100,
            "with_ocr": 60,
            "without_ocr": 40,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/setup/migration")
        assert response.status_code == 200
        data = response.json()
        assert data["needs_migration"] is True
        assert data["total_screenshots"] == 100
        assert data["screenshots_with_ocr"] == 60
        assert data["screenshots_without_ocr"] == 40
        assert data["progress_percent"] == 60.0

    @patch("core.database.db")
    @patch("api.routes.setup.config")
    @patch("api.routes.setup.current_platform")
    @patch("api.routes.setup.VERSION", "0.1.2")
    def test_get_enhanced_setup_status(self, mock_platform, mock_config, mock_db):
        """Should return comprehensive setup status"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.setup import router

        mock_config.last_seen_version = "0.1.1"
        mock_platform.name = "macos"
        mock_platform.needs_screen_permission.return_value = True
        mock_db.get_ocr_stats.return_value = {
            "total_screenshots": 100,
            "with_ocr": 100,
            "without_ocr": 0,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/setup/enhanced-status")
        assert response.status_code == 200
        data = response.json()
        assert data["current_version"] == "0.1.2"
        assert data["needs_setup"] is True
        assert data["platform"] == "macos"
        assert "clip_status" in data
        assert "text_embedding_status" in data
        assert "ocr_status" in data


class TestSearchModes:
    """Test search with different modes"""

    @patch("api.routes.search.db")
    @patch("api.routes.search.get_text_embedding")
    def test_search_image_mode(self, mock_get_embedding, mock_db):
        """Should perform image-only search"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.search import router

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
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/search",
            json={
                "query": "test query",
                "limit": 10,
                "safe_mode": False,
                "search_mode": "image",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1

    @patch("api.routes.search.db")
    @patch("api.routes.search.get_text_embedding")
    def test_search_text_fuzzy_mode(self, mock_get_embedding, mock_db):
        """Should perform text fuzzy search"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.search import router

        mock_db.get_stats.return_value = {"synced": 10}
        mock_db.search_text_fts.return_value = [
            {
                "id": 1,
                "image_path": "/path/to/img.jpg",
                "timestamp": "251206120000",
                "similarity": 0.9,
            }
        ]

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/search",
            json={
                "query": "test query",
                "limit": 10,
                "safe_mode": False,
                "search_mode": "text_fuzzy",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Result depends on whether text_fts is implemented
        assert "results" in data

    @patch("core.text_embeddings.text_embedding_service")
    @patch("api.routes.search.db")
    @patch("api.routes.search.get_text_embedding")
    def test_search_auto_mode(self, mock_get_embedding, mock_db, mock_text_emb_service):
        """Should perform hybrid search in auto mode"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.search import router

        mock_db.get_stats.return_value = {"synced": 10}
        mock_get_embedding.return_value = [0.1] * 768
        mock_text_emb_service.get_query_embedding.return_value = [0.1] * 384
        mock_db.search_hybrid.return_value = [
            {
                "id": 1,
                "image_path": "/path/to/img.jpg",
                "timestamp": "251206120000",
                "similarity": 0.85,
                "match_sources": ["image"],
            }
        ]

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/search",
            json={
                "query": "test query",
                "limit": 10,
                "safe_mode": False,
                "search_mode": "auto",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


class TestScreenshotOCREndpoint:
    """Test screenshot OCR endpoint"""

    @patch("api.routes.screenshots.db")
    def test_get_ocr_text_success(self, mock_db):
        """Should return OCR text for a screenshot with OCR data"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.screenshots import router

        mock_db.get_screenshot.return_value = {
            "id": 1,
            "image_path": "/path/to/img.jpg",
            "timestamp": "251206120000",
            "has_embedding": 1,
            "has_ocr": 1,
            "is_hidden": 0,
        }
        mock_db.get_ocr_text.return_value = {
            "full_text": "Hello world this is sample OCR text",
            "confidence": 0.95,
            "word_count": 7,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/screenshots/1/ocr")
        assert response.status_code == 200
        data = response.json()
        assert data["has_ocr"] is True
        assert data["text"] == "Hello world this is sample OCR text"
        assert data["confidence"] == 0.95
        assert data["word_count"] == 7

    @patch("api.routes.screenshots.db")
    def test_get_ocr_text_not_processed(self, mock_db):
        """Should return has_ocr=False when OCR hasn't been processed"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.screenshots import router

        mock_db.get_screenshot.return_value = {
            "id": 1,
            "image_path": "/path/to/img.jpg",
            "timestamp": "251206120000",
            "has_embedding": 1,
            "has_ocr": 0,
            "is_hidden": 0,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/screenshots/1/ocr")
        assert response.status_code == 200
        data = response.json()
        assert data["has_ocr"] is False
        assert data["text"] == ""
        assert data["word_count"] == 0

    @patch("api.routes.screenshots.db")
    def test_get_ocr_text_screenshot_not_found(self, mock_db):
        """Should return 404 for non-existent screenshot"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.screenshots import router

        mock_db.get_screenshot.return_value = None

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/screenshots/999/ocr")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("api.routes.screenshots.db")
    def test_get_ocr_text_empty_text(self, mock_db):
        """Should handle screenshots with OCR done but no text extracted"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.screenshots import router

        mock_db.get_screenshot.return_value = {
            "id": 1,
            "image_path": "/path/to/img.jpg",
            "timestamp": "251206120000",
            "has_embedding": 1,
            "has_ocr": 1,
            "is_hidden": 0,
        }
        mock_db.get_ocr_text.return_value = {
            "full_text": "",
            "confidence": None,
            "word_count": 0,
        }

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/screenshots/1/ocr")
        assert response.status_code == 200
        data = response.json()
        assert data["has_ocr"] is True
        assert data["text"] == ""
        assert data["word_count"] == 0
