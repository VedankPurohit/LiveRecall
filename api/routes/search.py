"""
Search API Routes
Semantic search for screenshots
"""
from fastapi import APIRouter, HTTPException

from api.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from core.database import db
from core.embeddings import (
    get_text_embedding,
    get_combined_embedding,
    get_safe_search_embedding,
)

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def search_screenshots(request: SearchRequest):
    """
    Search for screenshots using natural language.

    This loads the CLIP model (if not already loaded) and performs
    semantic similarity search against all synced screenshots.

    Examples:
    - "blue shirt on amazon"
    - "error message in terminal"
    - "video call with team"
    """
    # Check if we have any synced screenshots
    stats = db.get_stats()
    if stats["synced"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No synced screenshots. Run sync first to generate embeddings.",
        )

    # Generate query embedding
    try:
        if request.safe_mode:
            embedding = get_safe_search_embedding(
                text=request.query,
                safe_mode_level=request.safe_mode_level.value,
            )
        elif request.negative_texts:
            embedding = get_combined_embedding(
                base_text=request.query,
                negative_texts=request.negative_texts,
                negative_weight=request.negative_weight,
            )
        else:
            embedding = get_text_embedding(request.query)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embedding: {str(e)}",
        )

    # Search database
    try:
        results = db.search_similar(embedding, limit=request.limit)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}",
        )

    # Convert to response
    search_results = [
        SearchResult(
            id=r["id"],
            image_path=r["image_path"],
            timestamp=r["timestamp"],
            similarity=r["similarity"],
            image_url=f"/api/v1/screenshots/{r['id']}/image",
        )
        for r in results
    ]

    return SearchResponse(
        query=request.query,
        total_results=len(search_results),
        results=search_results,
    )


@router.get("/quick", response_model=SearchResponse)
async def quick_search(
    q: str,
    limit: int = 20,
    safe_mode: bool = True,
):
    """
    Quick search with query parameters (simpler than POST).

    Example: /api/v1/search/quick?q=blue+shirt&limit=10
    """
    request = SearchRequest(
        query=q,
        limit=limit,
        safe_mode=safe_mode,
    )
    return await search_screenshots(request)
