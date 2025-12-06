"""
Backend subprocess manager
Spawns and manages the FastAPI uvicorn server
"""
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Optional, Union

from .config import API_HOST, API_PORT, STARTUP_TIMEOUT
from .api_client import api_client


def is_frozen() -> bool:
    """Check if running as a frozen PyInstaller app"""
    return getattr(sys, 'frozen', False)


def _run_api_server_thread(host: str, port: int, ready_event: threading.Event):
    """
    Run the FastAPI server in a thread.
    This is used when running as a frozen PyInstaller app.
    """
    import uvicorn
    from api.main import app

    # Create a custom config to signal when ready
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    # Signal ready before starting (server will be ready shortly after)
    ready_event.set()

    # Run the server (blocking)
    server.run()


class BackendManager:
    """Manages the FastAPI backend as a subprocess or thread"""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._server_thread: Optional[threading.Thread] = None
        self._restart_thread: Optional[threading.Thread] = None
        self._should_restart = True
        self._lock = threading.Lock()
        self._frozen = is_frozen()
        self._ready_event = threading.Event()

    @property
    def is_running(self) -> bool:
        """Check if backend process/thread is running"""
        with self._lock:
            if self._frozen:
                # Thread-based for frozen apps
                return self._server_thread is not None and self._server_thread.is_alive()
            else:
                # subprocess.Popen for development
                if self._process is None:
                    return False
                return self._process.poll() is None

    def start(self) -> bool:
        """
        Start the backend server
        Returns True if started successfully
        """
        if self.is_running:
            return True

        with self._lock:
            try:
                if self._frozen:
                    # Frozen app: use threading (more reliable in PyInstaller)
                    self._ready_event.clear()
                    self._server_thread = threading.Thread(
                        target=_run_api_server_thread,
                        args=(API_HOST, API_PORT, self._ready_event),
                        daemon=True
                    )
                    self._server_thread.start()
                    # Wait for thread to signal it's starting
                    self._ready_event.wait(timeout=5)
                else:
                    # Development: use subprocess
                    project_root = Path(__file__).parent.parent
                    main_py = project_root / "main.py"

                    if not main_py.exists():
                        print(f"Error: {main_py} not found")
                        return False

                    # Start uvicorn as subprocess
                    # Inherit stdout/stderr so logs appear in console
                    self._process = subprocess.Popen(
                        [
                            sys.executable,
                            str(main_py),
                            "--api-only",
                            "--host", API_HOST,
                            "--port", str(API_PORT),
                        ],
                        stdout=None,  # Inherit parent's stdout
                        stderr=None,  # Inherit parent's stderr
                        cwd=str(project_root),
                    )

            except Exception as e:
                print(f"Failed to start backend: {e}")
                return False

        # Wait for health check
        return self._wait_for_health()

    def _wait_for_health(self) -> bool:
        """Wait for backend to become healthy"""
        start_time = time.time()
        while time.time() - start_time < STARTUP_TIMEOUT:
            if api_client.health_check():
                return True
            time.sleep(0.5)

            # Check if process died
            if not self.is_running:
                return False

        return False

    def stop(self):
        """Stop the backend server gracefully"""
        self._should_restart = False

        with self._lock:
            try:
                if self._frozen:
                    # Thread-based: threads can't be killed directly
                    # The daemon thread will terminate when the main app exits
                    # For now, we just mark it as stopped
                    self._server_thread = None
                else:
                    # subprocess.Popen
                    if self._process is None:
                        return
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                        self._process.wait()
                    self._process = None

            except Exception as e:
                print(f"Error stopping backend: {e}")

    def restart(self):
        """Restart the backend server"""
        self.stop()
        self._should_restart = True
        return self.start()

    def enable_auto_restart(self):
        """Enable automatic restart on crash"""
        self._should_restart = True
        if self._restart_thread is None or not self._restart_thread.is_alive():
            self._restart_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self._restart_thread.start()

    def _monitor_loop(self):
        """Monitor process and restart if it crashes"""
        while self._should_restart:
            time.sleep(2)

            if not self._should_restart:
                break

            if not self.is_running and self._should_restart:
                print("Backend crashed, restarting...")
                self.start()


# Global backend manager instance
backend_manager = BackendManager()
