# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LiveRecall is an open-source screen recall application with semantic search. It captures screenshots and enables natural language queries using CLIP embeddings. The app runs as a system tray application that manages a FastAPI backend, which serves a Next.js web UI.

## Common Commands

```bash
# Install dependencies
uv sync                              # Python (creates .venv automatically)
cd web && npm install && cd ..       # Web UI

# Run the application
uv run python main.py                # System tray app (recommended)
uv run python main.py --api-only     # API server only
cd web && npm run dev                # Web UI dev server (hot reload)

# Testing
uv run pytest                        # All tests
uv run pytest tests/test_api.py -v   # Specific test file
uv run pytest tests/test_api.py::TestHealthEndpoints::test_health_endpoint -v  # Single test

# Building
uv run python scripts/build_release.py         # Full build
uv run python scripts/build_release.py --quick # Skip web rebuild
```

## Architecture

**Data Flow:** Tray App → spawns Backend subprocess → FastAPI serves Web UI + REST API

### Key Components

- **core/capture.py** - CaptureService: Screenshot capture using mss, SSIM-based change detection
- **core/database.py** - SQLite + sqlite-vec for vector similarity search
- **core/embeddings.py** - CLIP model with lazy loading and 5-minute auto-unload
- **core/processor.py** - Background sync service for processing screenshots
- **tray/app.py** - TrayApp: System tray menu, spawns backend via subprocess
- **tray/backend.py** - Manages FastAPI server as subprocess
- **api/main.py** - FastAPI app that serves REST API + static Next.js build from web/out/

### API Routes Structure

Routes in `api/routes/` with prefixes: `/recording`, `/sync`, `/search`, `/screenshots`, `/compression`, `/incognito`, `/setup`

### Web UI Structure

Next.js app in `web/src/app/` with static export to `web/out/`. Pages: timeline (main), settings, setup.

## Code Conventions

### Attribution
- Never add "Claude Code", "Claude", or AI attribution to commits or code
- Do not include AI co-author tags

### Python
- Python 3.10+ with type hints, double quotes for strings
- Services use global singleton instances at module level
- Private attributes use `_leading_underscore`

### FastAPI Patterns
```python
router = APIRouter(prefix="/endpoint", tags=["Tag"])

@router.get("", response_model=Schema)
async def get_something():
    """Docstring"""
    return result
```

### TypeScript/React
- Functional components with hooks
- Tailwind CSS for styling

## Data Storage

macOS: `~/Library/Application Support/LiveRecall/` (SQLite database + screenshots folder)

## API Documentation

When running: http://localhost:8742/docs (Swagger) or http://localhost:8742/redoc
