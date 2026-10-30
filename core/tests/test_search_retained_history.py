"""Retained OCR must stay searchable after all older CLIP vectors are archived."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.parametrize("mode", ["text_fuzzy", "text_semantic", "auto"])
def test_ocr_search_works_without_clip_vectors(mock_db, temp_dir, mode):
    from api.routes.search import router

    screenshot_id = mock_db.add_screenshot(str(temp_dir / "retained.jpg"), "260830000000")
    ocr_id = mock_db.add_ocr_text(screenshot_id, "Retained project memory", confidence=0.99)
    vector = [1.0] + [0.0] * 383
    chunk_id = mock_db.add_ocr_chunk(ocr_id, "small", 0, "Retained project memory")
    mock_db.add_text_embedding(chunk_id, vector)
    assert mock_db.get_stats()["synced"] == 0
    app = FastAPI()
    app.include_router(router)
    with (
        patch("api.routes.search.db", mock_db),
        patch("api.routes.search.get_text_embedding") as clip,
        patch("core.text_embeddings.text_embedding_service") as text,
    ):
        text.get_query_embedding.return_value = vector
        response = TestClient(app).post("/search", json={"query": "project", "search_mode": mode})
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == screenshot_id
    clip.assert_not_called()
    if mode == "text_fuzzy":
        text.get_query_embedding.assert_not_called()


def test_explicit_image_search_still_requires_clip_vectors(mock_db):
    from api.routes.search import router

    app = FastAPI()
    app.include_router(router)
    with patch("api.routes.search.db", mock_db), patch("api.routes.search.get_text_embedding") as clip:
        response = TestClient(app).post("/search", json={"query": "project", "search_mode": "image"})
    assert response.status_code == 400
    clip.assert_not_called()
