import asyncio
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image


@pytest.mark.parametrize("enabled", [False, True])
def test_auto_compression_honors_setting(enabled):
    from api.main import _auto_compress

    async def stop_after_check(delay):
        assert delay == 3600
        raise asyncio.CancelledError

    with (
        patch("core.config.config") as config,
        patch("core.compression.compression_service") as service,
        patch("api.main.asyncio.sleep", stop_after_check),
        pytest.raises(asyncio.CancelledError),
    ):
        config.compression.enabled = enabled
        config.compression.image_format = "webp"
        service.is_running = False
        try:
            asyncio.run(_auto_compress())
        finally:
            assert service.start.call_count == int(enabled)
            if enabled:
                service.start.assert_called_once_with(image_format="webp")


def test_compression_api_passes_opt_in_webp():
    from api.routes.compression import router

    app = FastAPI()
    app.include_router(router)
    with patch("api.routes.compression.compression_service") as service, patch("api.routes.compression.db") as database:
        service.is_running = False
        database.get_compressible_count.return_value = 1
        response = TestClient(app).post(
            "/compression/start", json={"older_than_days": 30, "quality": 85, "image_format": "webp"}
        )
    assert response.status_code == 200
    service.start.assert_called_once_with(older_than_days=30, quality=85, image_format="webp")


@pytest.mark.parametrize("route", ["/screenshots/1/image", "/screenshots/image"])
def test_screenshot_routes_serve_webp_media_type(temp_dir, route):
    from api.routes.screenshots import router

    path = temp_dir / "compressed.webp"
    Image.new("RGB", (32, 32), "white").save(path, "WEBP")
    app = FastAPI()
    app.include_router(router)
    with (
        patch("api.routes.screenshots.db") as database,
        patch("api.routes.screenshots.get_screenshots_dir", return_value=temp_dir),
    ):
        database.get_screenshot.return_value = {"image_path": str(path)}
        response = TestClient(app).get(route, params={"path": str(path)})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert response.content == path.read_bytes()


def test_delete_all_includes_compressed_webp(temp_dir):
    from api.routes.screenshots import router

    path = temp_dir / "compressed.webp"
    Image.new("RGB", (32, 32), "white").save(path, "WEBP")
    app = FastAPI()
    app.include_router(router)
    with (
        patch("api.routes.screenshots.db") as database,
        patch("api.routes.screenshots.get_screenshots_dir", return_value=temp_dir),
    ):
        database.get_stats.return_value = {"total_screenshots": 1}
        response = TestClient(app).delete("/screenshots", params={"confirm": "true"})
    assert response.status_code == 200
    assert not path.exists()
    database.clear_all.assert_called_once()


def test_format_setting_round_trip_through_api(temp_dir):
    from api.routes.status import router
    from core.config import Config

    app = FastAPI()
    app.include_router(router)
    config = Config()
    with (
        patch("core.config.get_config_path", return_value=temp_dir / "config.json"),
        patch("api.routes.status.config", config),
        patch("api.routes.status.get_model_status", return_value={"auto_unload_seconds": 300}),
    ):
        client = TestClient(app)
        assert client.get("/config").json()["compression"]["image_format"] == "jpeg"
        assert client.put("/config", json={"compression_image_format": "webp"}).status_code == 200
        assert client.get("/config").json()["compression"]["image_format"] == "webp"
        reloaded = Config()
        reloaded.load()
        assert reloaded.compression.image_format == "webp"
        assert client.put("/config", json={"compression_image_format": "unknown"}).status_code == 422


def test_manual_compression_uses_saved_format_when_request_omits_it():
    from api.routes.compression import router

    app = FastAPI()
    app.include_router(router)
    with (
        patch("api.routes.compression.compression_service") as service,
        patch("api.routes.compression.db") as database,
        patch("api.routes.compression.config") as config,
    ):
        service.is_running = False
        config.compression.image_format = "webp"
        config.compression.after_days = 30
        config.compression.quality = 85
        database.get_compressible_count.return_value = 1
        response = TestClient(app).post("/compression/start")
    assert response.status_code == 200
    service.start.assert_called_once_with(older_than_days=30, quality=85, image_format="webp")


def test_force_recompression_uses_saved_format():
    from api.routes.compression import router

    app = FastAPI()
    app.include_router(router)
    with (
        patch("api.routes.compression.compression_service") as service,
        patch("api.routes.compression.db") as database,
        patch("api.routes.compression.config") as config,
    ):
        service.is_running = False
        service.start_force_recompress.return_value = True
        config.compression.image_format = "webp"
        database.get_force_recompressible_count.return_value = {"total": 1}
        response = TestClient(app).post("/compression/force-recompress", json={"older_than_days": 30, "confirm": True})
    assert response.status_code == 200
    service.start_force_recompress.assert_called_once_with(older_than_days=30, quality=None, image_format="webp")
