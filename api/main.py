"""
LiveRecall API
FastAPI application for controlling LiveRecall
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import recording, sync, search, screenshots, status, compression
from core.database import db

# Configure logging - reduce uvicorn noise
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🧠 LiveRecall API starting...")
    db.connect()
    stats = db.get_stats()
    print(f"📁 Database: {db.db_path}")
    print(f"📊 Screenshots: {stats['total_screenshots']} total, {stats['synced']} synced")

    yield

    # Shutdown
    print("🛑 LiveRecall API shutting down...")
    from core.capture import capture_service
    from core.processor import processor_service
    from core.embeddings import unload_model

    # Stop services
    capture_service.stop()
    processor_service.stop()
    unload_model()
    db.disconnect()
    print("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="LiveRecall API",
    description="""
    LiveRecall - Screen Recall with Semantic Search

    ## Features
    - **Recording**: Capture screenshots automatically when screen changes
    - **Sync**: Generate CLIP embeddings for semantic search
    - **Search**: Find screenshots using natural language queries

    ## Workflow
    1. Start recording with `POST /api/v1/recording/start`
    2. Screenshots are saved but NOT processed (lightweight)
    3. When ready to search, run `POST /api/v1/sync/start`
    4. Search with `POST /api/v1/search`

    ## Model Management
    The CLIP model is loaded lazily (on first sync/search) and
    automatically unloads after 5 minutes of inactivity to save memory.
    """,
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(status.router, prefix="/api/v1")
app.include_router(recording.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(screenshots.router, prefix="/api/v1")
app.include_router(compression.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """API root - redirects to docs"""
    return {
        "name": "LiveRecall API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "/api/v1/status",
    }


# Run with: uvicorn api.main:app --reload --port 8742
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8742,
        reload=True,
    )
