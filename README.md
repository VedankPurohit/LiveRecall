# LiveRecall

**LiveRecall** is an open-source screen recall application with semantic search. It captures screenshots of your screen and lets you find them using natural language queries.

## Features

- **Semantic Search** - Find screenshots by describing what you're looking for
- **Smart Capture** - Only saves when screen content changes
- **System Tray App** - Runs quietly in your menu bar
- **Web Interface** - Beautiful timeline and search UI
- **Local & Private** - All data stays on your machine
- **GPU Accelerated** - Uses MPS on Apple Silicon, CUDA on Windows

## Download

### macOS (Apple Silicon)

1. Download the latest DMG from [Releases](https://github.com/VedankPurohit/LiveRecall/releases)
2. Open the DMG and drag LiveRecall to Applications
3. Launch LiveRecall from Applications
4. Grant **Screen Recording** permission when prompted (System Settings > Privacy & Security > Screen Recording)

**Note:** On first launch, the CLIP model (~400MB) will be downloaded automatically.

### Windows / Intel Mac

Coming soon! For now, follow the development installation below.

## Quick Start (Development)

### Prerequisites

- Python 3.10+
- Node.js 18+ (for web UI)
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/VedankPurohit/LiveRecall.git
cd LiveRecall

# Install Python dependencies (creates .venv automatically)
uv sync

# Install web UI dependencies
cd web && npm install && cd ..
```

### Running

**Option 1: System Tray App** (recommended)
```bash
uv run python main.py
```
This launches the menu bar app which manages everything.

**Option 2: API Server Only**
```bash
uv run python main.py --api-only
```

**Option 3: Web UI Development**
```bash
# Terminal 1: Start API
uv run python main.py --api-only

# Terminal 2: Start web UI
cd web && npm run dev
```

Then open http://localhost:3000

## Building from Source

To create a distributable app (.dmg for macOS, .exe for Windows):

```bash
# One-command build (installs deps, builds web, creates package)
uv run python scripts/build_release.py

# Quick build (skip web rebuild if exists)
uv run python scripts/build_release.py --quick
```

Output will be in `dist/`:
- macOS: `LiveRecall-0.1.0-macOS-arm64.dmg`
- Windows: `LiveRecall-0.1.0-Windows-x64.exe`

## Architecture

```
LiveRecall/
├── core/           # Core functionality
│   ├── capture.py      # Screen capture service
│   ├── database.py     # SQLite + vector search
│   ├── embeddings.py   # CLIP model (lazy loaded)
│   ├── processor.py    # Background sync service
│   └── compression.py  # Image compression
├── api/            # FastAPI backend
│   ├── main.py         # App entry point
│   └── routes/         # API endpoints
├── tray/           # System tray application
│   ├── app.py          # Main tray app
│   ├── menu.py         # Menu builder
│   └── backend.py      # Subprocess manager
├── web/            # Next.js web interface
│   └── src/
│       ├── app/        # Pages
│       ├── components/ # UI components
│       └── lib/        # API client
├── scripts/        # Build scripts
│   ├── build_release.py    # One-click builder
│   └── generate_icons.py   # Icon generator
├── tests/          # Test suite
└── main.py         # Entry point
```

## How It Works

1. **Capture**: Screenshots are taken at regular intervals when screen content changes
2. **Storage**: Images saved to `~/Library/Application Support/LiveRecall/` (macOS)
3. **Sync**: CLIP model generates embeddings for semantic search (runs on-demand)
4. **Search**: Natural language queries matched against embeddings

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/status` | GET | System status |
| `/api/v1/recording/start` | POST | Start capture |
| `/api/v1/recording/stop` | POST | Stop capture |
| `/api/v1/sync/start` | POST | Start embedding sync |
| `/api/v1/search` | POST | Semantic search |
| `/api/v1/screenshots` | GET | List screenshots |

Full API docs at http://localhost:8742/docs

## Configuration

Settings available in the web UI or via API:

- **Capture Mode**: normal, games, fast, coding, video, presentation
- **Capture Interval**: 1-10 seconds
- **Quality**: 50-100%
- **Safe Mode**: Filter sensitive content from search
- **Auto-compress**: Compress old screenshots

## Privacy & Security

- All data stored locally on your machine
- No cloud sync or telemetry
- Screenshots stored in user's application data folder
- Optional encryption (coming soon)

See [Privacy and Security](Privacy%20and%20Security.md) for details.

## Development

```bash
# Install dependencies (includes dev tools)
uv sync

# Run the app
uv run python main.py

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=core --cov=api

# Run specific test file
uv run pytest tests/test_api.py -v
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (`uv run pytest`)
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE)

## Contact

- GitHub: [@VedankPurohit](https://github.com/VedankPurohit)
