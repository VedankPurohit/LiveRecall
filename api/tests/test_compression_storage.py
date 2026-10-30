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
        service.is_running = False
        try:
            asyncio.run(_auto_compress())
        finally:
            assert service.start.call_count == int(enabled)


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
