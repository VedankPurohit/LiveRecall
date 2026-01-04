"""
LiveRecall - Entry Point
Launch API server or system tray application
"""

import argparse
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Check if running as a frozen PyInstaller app"""
    return getattr(sys, "frozen", False)


def get_app_path() -> Path:
    """Get the application root path (works for both development and frozen)"""
    if is_frozen():
        # PyInstaller: executable is in the app bundle
        return Path(sys.executable).parent
    else:
        # Development: main.py location
        return Path(__file__).parent


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="LiveRecall - Screen Recall with Semantic Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Launch system tray (default)
  python main.py --tray       # Launch system tray
  python main.py --api-only   # Launch API server only
  python main.py --api-only --host 0.0.0.0 --port 8000
        """,
    )

    parser.add_argument("--tray", action="store_true", help="Launch system tray application (default)")
    parser.add_argument("--api-only", action="store_true", help="Launch API server only (no tray)")
    parser.add_argument("--host", default="127.0.0.1", help="API server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8742, help="API server port (default: 8742)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    if args.api_only:
        # Launch API server only
        import uvicorn

        from api.main import app

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload if not is_frozen() else False,
        )
    else:
        # Launch system tray (default)
        from tray.app import run_tray

        run_tray()


if __name__ == "__main__":
    main()
