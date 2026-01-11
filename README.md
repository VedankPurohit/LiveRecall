# LiveRecall

**LiveRecall** is an open-source screen recall application with semantic search. It captures screenshots of your screen and lets you find them using natural language queries.

## Features

- **Semantic Search** - Find screenshots by describing what you're looking for
- **OCR Text Extraction** - Automatically extracts text from screenshots for text-based search
- **Hybrid Search** - Combines image similarity and text matching for best results
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

**Note:** On first launch, required AI models will be downloaded automatically:
- Image embedding model (~400MB) for visual search
- Text embedding model (~130MB) for OCR text search

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
3. **Sync**: Processing pipeline generates embeddings and extracts text (runs on-demand)
4. **Search**: Natural language queries matched against image and text content

### Search Modes

LiveRecall supports multiple search modes:

- **Auto (Hybrid)** - Default. Combines all search methods using Reciprocal Rank Fusion for best results
- **Image** - Finds screenshots where the visual content matches your query (e.g., "cat on a keyboard")
- **Text Fuzzy** - Fast text matching with typo tolerance using trigram search
- **Text Semantic** - Finds screenshots containing text with similar meaning to your query

### OCR Processing

When sync runs, each screenshot goes through:
1. **Image embedding** - Visual features extracted for semantic image search
2. **OCR extraction** - Text extracted using platform-native OCR (Vision on macOS, Tesseract on Windows)
3. **Text chunking** - Extracted text split into searchable chunks
4. **Text embedding** - Semantic embeddings generated for text search

You can view extracted text for any screenshot using the "View Text" button in the web UI.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/status` | GET | System status |
| `/api/v1/recording/start` | POST | Start capture |
| `/api/v1/recording/stop` | POST | Stop capture |
| `/api/v1/sync/start` | POST | Start embedding/OCR sync |
| `/api/v1/search` | POST | Hybrid search (supports search_mode parameter) |
| `/api/v1/screenshots` | GET | List screenshots |
| `/api/v1/screenshots/{id}/ocr` | GET | Get OCR text for a screenshot |

Full API docs at http://localhost:8742/docs

## Configuration

Settings available in the web UI or via API:

- **Capture Mode**: normal, games, fast, coding, video, presentation
- **Capture Interval**: 1-10 seconds
- **Quality**: 50-100%
- **Safe Mode**: Filter sensitive content from search
- **Auto-compress**: Compress old screenshots
- **OCR Enabled**: Enable/disable text extraction (enabled by default)
- **Search Mode**: auto (hybrid), image, text_fuzzy, text_semantic

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
