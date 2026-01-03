"""
LiveRecall API
FastAPI application for controlling LiveRecall
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from api.routes import recording, sync, search, screenshots, status, compression
from core.database import db


def _get_static_dir() -> Path:
    """Get the path to static web UI files (works for both dev and frozen)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller: look in _MEIPASS (temp extraction dir) or next to executable
        base = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
        # Try _MEIPASS/web/out first, then next to exe
        if (base / "web" / "out").exists():
            return base / "web" / "out"
        return Path(sys.executable).parent / "web" / "out"
    else:
        # Development: relative to this file
        return Path(__file__).parent.parent / "web" / "out"


# Path to static web UI files (built Next.js)
STATIC_DIR = _get_static_dir()

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
    version="0.1.2",
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


# Middleware to strip trailing slashes from API routes
@app.middleware("http")
async def strip_trailing_slash(request: Request, call_next):
    """Redirect API requests with trailing slashes to non-trailing slash version"""
    path = request.url.path
    # Only handle /api/ routes with trailing slash (but not just "/api/")
    if path.startswith("/api/") and path.endswith("/") and len(path) > 5:
        # Preserve query string
        new_path = path.rstrip("/")
        if request.url.query:
            new_url = f"{new_path}?{request.url.query}"
        else:
            new_url = new_path
        return RedirectResponse(url=new_url, status_code=307)
    return await call_next(request)


# Include routers
app.include_router(status.router, prefix="/api/v1")
app.include_router(recording.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(screenshots.router, prefix="/api/v1")
app.include_router(compression.router, prefix="/api/v1")


# Serve static web UI if available
if STATIC_DIR.exists():
    # Mount static files for assets (_next, images, etc.)
    app.mount("/_next", StaticFiles(directory=STATIC_DIR / "_next"), name="next_static")

    # Catch-all route for SPA - must be after API routes
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve static files or index.html for SPA routing"""
        # Try to serve the exact file first
        file_path = STATIC_DIR / full_path

        # Handle trailing slash - look for index.html in directory
        if file_path.is_dir():
            index_file = file_path / "index.html"
            if index_file.exists():
                return FileResponse(index_file)

        # Serve exact file if it exists
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Try with .html extension (Next.js static export)
        html_file = STATIC_DIR / f"{full_path}.html"
        if html_file.exists():
            return FileResponse(html_file)

        # Fall back to index.html for SPA routing
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        # No static files available
        return {"error": "Not found", "path": full_path}

    # Root serves index.html
    @app.get("/")
    async def root():
        """Serve web UI"""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {
            "name": "LiveRecall API",
            "version": "2.0.0",
            "docs": "/docs",
            "web_ui": "Not built. Run 'npm run build' in web/ directory.",
        }
else:
    # No static files - serve API info at root
    @app.get("/")
    async def root():
        """API root - no web UI available"""
        return {
            "name": "LiveRecall API",
            "version": "2.0.0",
            "docs": "/docs",
            "status": "/api/v1/status",
            "web_ui": f"Not found at {STATIC_DIR}. Build with 'npm run build' in web/",
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
