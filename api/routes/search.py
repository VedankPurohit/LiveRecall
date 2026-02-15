"""
Search API Routes
Semantic search for screenshots with hybrid search support.

Search modes:
- auto: Hybrid search combining image + text (default, recommended)
- image: CLIP image embedding search only
- text_fuzzy: FTS5 trigram text search only
- text_semantic: BGE text embedding search only

The hybrid search uses Reciprocal Rank Fusion (RRF) to combine results
from multiple sources.
"""

from fastapi import APIRouter, HTTPException

from api.schemas import (
    SearchMode,
    SearchRequest,
    SearchResponse,
    SearchResult,
    VisibilityFilter,
)
from core.config import config
from core.database import db
from core.embeddings import (
    get_combined_embedding,
    get_safe_search_embedding,
    get_text_embedding,
)

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def search_screenshots(request: SearchRequest):
    """
    Search for screenshots using natural language.

    Supports multiple search modes:
    - auto: Hybrid search combining image + text (recommended)
    - image: CLIP semantic search only
    - text_fuzzy: FTS5 trigram text search only
    - text_semantic: BGE text embedding search only

    Optionally filter by date range using start_date and end_date.

    Examples:
    - "blue shirt on amazon" (visual search)
    - "error: connection refused" (text search)
    - "video call with team" (hybrid search)
    """
    # Check if we have any synced screenshots
    stats = db.get_stats()
    if stats["synced"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No synced screenshots. Run sync first to generate embeddings.",
        )

    # Validate: need either query or image
    if not request.query and request.image is None:
        raise HTTPException(
            status_code=400,
            detail="Either query or image must be provided.",
        )

    # Generate embeddings based on search mode
    image_embedding = None
    text_embedding = None

    # When image param is provided, use it for embedding
    if request.image is not None:
        if isinstance(request.image, int):
            # Screenshot ID — use stored embedding
            image_embedding = db.get_embedding(request.image)
            if image_embedding is None:
                raise HTTPException(
                    status_code=400,
                    detail="Screenshot has no embedding. Run sync first.",
                )
        else:
            # Base64 image data — generate embedding from bytes
            import base64

            try:
                image_bytes = base64.b64decode(request.image)
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid base64 image data") from e
            from core.embeddings import get_image_embedding_from_bytes

            try:
                image_embedding = get_image_embedding_from_bytes(image_bytes)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process image: {e}") from e

    try:
        if request.image is None and request.search_mode in (SearchMode.AUTO, SearchMode.IMAGE):
            # CLIP image embedding (for image and auto modes)
            if request.safe_mode:
                image_embedding = get_safe_search_embedding(
                    text=request.query,
                    safe_mode_level=request.safe_mode_level.value,
                )
            elif request.negative_texts:
                image_embedding = get_combined_embedding(
                    base_text=request.query,
                    negative_texts=request.negative_texts,
                    negative_weight=request.negative_weight,
                )
            else:
                image_embedding = get_text_embedding(request.query)

        # BGE text embedding (for text_semantic and auto modes) - skip when using image query
        if request.image is None and request.search_mode in (SearchMode.AUTO, SearchMode.TEXT_SEMANTIC):
            # Lazy import to avoid loading text model if not needed
            from core.text_embeddings import text_embedding_service

            text_embedding = text_embedding_service.get_query_embedding(request.query)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embedding: {str(e)}",
        ) from e

    # Search based on mode
    search_limit = request.limit * 3 if (request.start_date or request.end_date) else request.limit

    try:
        if request.search_mode == SearchMode.IMAGE:
            # Pure image search (legacy behavior)
            if image_embedding is None:
                raise HTTPException(status_code=500, detail="Failed to generate image embedding")
            results = db.search_similar(
                image_embedding,
                limit=search_limit,
                similarity_metric=config.similarity_metric,
                visibility=request.visibility.value,
            )
            # Add empty match_sources for compatibility
            for r in results:
                r["match_sources"] = ["image"]

        elif request.search_mode == SearchMode.TEXT_FUZZY:
            # Pure FTS5 text search
            results = db.search_ocr_fts(
                query=request.query,
                limit=search_limit,
                visibility=request.visibility.value,
            )
            # Normalize response format
            for r in results:
                r["similarity"] = r.get("relevance_score", 0.5)  # BM25 score as similarity
                r["match_sources"] = ["text_fts"]

        elif request.search_mode == SearchMode.TEXT_SEMANTIC:
            # Pure BGE text semantic search
            if text_embedding is None:
                raise HTTPException(status_code=500, detail="Failed to generate text embedding")
            results = db.search_text_embeddings(
                query_embedding=text_embedding,
                limit=search_limit,
                visibility=request.visibility.value,
            )
            # Normalize response format
            for r in results:
                r["similarity"] = r.get("text_similarity", 0)
                r["match_sources"] = ["text_semantic_small", "text_semantic_large"]

        else:
            # Hybrid search (auto mode - default)
            results = db.search_hybrid(
                query=request.query,
                image_embedding=image_embedding,
                text_embedding=text_embedding,
                mode="auto",
                limit=search_limit,
                visibility=request.visibility.value,
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}",
        ) from e

    # Filter by date range if specified
    if request.start_date or request.end_date:
        filtered_results = []
        for r in results:
            ts = r["timestamp"]
            if request.start_date and ts < request.start_date:
                continue
            if request.end_date and ts > request.end_date:
                continue
            filtered_results.append(r)
            if len(filtered_results) >= request.limit:
                break
        results = filtered_results

    # Filter out the source screenshot when searching by ID
    if isinstance(request.image, int):
        results = [r for r in results if r["id"] != request.image]

    # Convert to response
    search_results = [
        SearchResult(
            id=r["id"],
            image_path=r["image_path"],
            timestamp=r["timestamp"],
            similarity=r["similarity"],
            image_url=f"/api/v1/screenshots/{r['id']}/image",
        )
        for r in results[: request.limit]
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
    safe_mode: bool = False,
    start_date: str = None,
    end_date: str = None,
    visibility: VisibilityFilter = VisibilityFilter.VISIBLE_ONLY,
):
    """
    Quick search with query parameters (simpler than POST).

    Safe mode is OFF by default for personal recall apps.
    Enable it to filter potentially sensitive content from results.

    Example: /api/v1/search/quick?q=blue+shirt&limit=10
    Example with dates: /api/v1/search/quick?q=meeting&start_date=251201000000&end_date=251206235959
    Example with visibility: /api/v1/search/quick?q=meeting&visibility=all
    """
    request = SearchRequest(
        query=q,
        limit=limit,
        safe_mode=safe_mode,
        start_date=start_date,
        end_date=end_date,
        visibility=visibility,
    )
    return await search_screenshots(request)
