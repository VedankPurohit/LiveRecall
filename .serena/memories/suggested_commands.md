# Suggested Commands for LiveRecall Development

## Environment Setup

```bash
# Install Python dependencies (creates .venv automatically)
uv sync

# Install web UI dependencies
cd web && npm install && cd ..
```

## Running the Application

```bash
# Run system tray app (recommended - manages everything)
uv run python main.py

# Run API server only (no tray)
uv run python main.py --api-only

# Run API server with custom host/port
uv run python main.py --api-only --host 0.0.0.0 --port 8742

# Run web UI in development mode (hot reload)
cd web && npm run dev
```

## Testing

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=core --cov=api

# Run specific test file
uv run pytest tests/test_api.py -v

# Run specific test
uv run pytest tests/test_api.py::TestHealthEndpoints::test_health_endpoint -v
```

## Building for Release

```bash
# Full build (installs deps, builds web, creates package)
uv run python scripts/build_release.py

# Quick build (skip web rebuild if exists)
uv run python scripts/build_release.py --skip-web

# Skip DMG creation (macOS)
uv run python scripts/build_release.py --skip-dmg

# Generate app icons
uv run python scripts/generate_icons.py
```

## Web UI

```bash
# Development server (hot reload)
cd web && npm run dev

# Build static export
cd web && npm run build

# The build output goes to web/out/ and is served by FastAPI
```

## API Documentation

When the API is running, visit:
- http://localhost:8742/docs - Swagger UI
- http://localhost:8742/redoc - ReDoc

## Useful Git Commands

```bash
# Check status
git status

# Create feature branch
git checkout -b feature/my-feature

# Commit with conventional format
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"
```
