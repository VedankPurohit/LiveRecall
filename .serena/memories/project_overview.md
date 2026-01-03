# LiveRecall Project Overview

## Purpose
LiveRecall is an open-source screen recall application with semantic search. It captures screenshots of your screen and lets you find them using natural language queries powered by CLIP embeddings.

## Tech Stack

### Backend (Python 3.10+)
- **FastAPI** - REST API server
- **SQLite + sqlite-vec** - Database with vector search
- **sentence-transformers** - CLIP model for embeddings
- **torch** - ML framework (MPS on Apple Silicon, CUDA on Windows)
- **mss** - Cross-platform screen capture
- **opencv-python / scikit-image** - Image processing (SSIM for change detection)
- **pystray** - System tray application
- **PyInstaller** - Application bundling

### Frontend (Next.js)
- **Next.js** - React framework with static export
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Styling

### Package Management
- **uv** - Python package manager (creates .venv automatically)
- **npm** - Node.js package manager

## Architecture

```
LiveRecall/
├── core/           # Core functionality
│   ├── capture.py      # Screen capture service (mss-based)
│   ├── database.py     # SQLite + vector search
│   ├── embeddings.py   # CLIP model (lazy loaded, auto-unloads after 5min)
│   ├── processor.py    # Background sync service
│   ├── compression.py  # Image compression
│   ├── config.py       # Configuration
│   └── updater.py      # Update checker
├── api/            # FastAPI backend
│   ├── main.py         # App entry point, serves web UI
│   ├── schemas.py      # Pydantic models
│   └── routes/         # API endpoints (recording, sync, search, etc.)
├── tray/           # System tray application
│   ├── app.py          # Main tray app
│   ├── menu.py         # Menu builder
│   ├── backend.py      # Subprocess manager (spawns API server)
│   ├── api_client.py   # HTTP client for API communication
│   └── config.py       # Tray configuration
├── web/            # Next.js web interface
│   └── src/
│       ├── app/        # Pages (timeline, settings, search)
│       ├── components/ # UI components
│       └── lib/        # API client
├── scripts/        # Build scripts
│   ├── build_release.py    # One-click builder
│   └── generate_icons.py   # Icon generator
├── tests/          # Test suite
└── main.py         # Entry point (tray or api-only mode)
```

## Key Components

1. **CaptureService** (`core/capture.py`) - Captures screenshots using mss, uses SSIM to detect changes
2. **Database** (`core/database.py`) - SQLite with sqlite-vec for vector similarity search
3. **Embeddings** (`core/embeddings.py`) - CLIP model management with lazy loading and auto-unload
4. **TrayApp** (`tray/app.py`) - System tray with menu, spawns backend via subprocess
5. **FastAPI** (`api/main.py`) - REST API + serves static Next.js build

## Data Storage
- macOS: `~/Library/Application Support/LiveRecall/`
- Contains: SQLite database, screenshots folder
