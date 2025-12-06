"""
Backend subprocess manager
Spawns and manages the FastAPI uvicorn server
"""
import subprocess
import sys
import time
import signal
import threading
from pathlib import Path
from typing import Optional

from .config import API_HOST, API_PORT, STARTUP_TIMEOUT
from .api_client import api_client


class BackendManager:
    """Manages the FastAPI backend as a subprocess"""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._restart_thread: Optional[threading.Thread] = None
        self._should_restart = True
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """Check if backend process is running"""
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self) -> bool:
        """
        Start the backend server
        Returns True if started successfully
        """
        if self.is_running:
            return True

        with self._lock:
            try:
                # Find the main.py in the project root
                project_root = Path(__file__).parent.parent
                main_py = project_root / "main.py"

                if not main_py.exists():
                    print(f"Error: {main_py} not found")
                    return False

                # Start uvicorn as subprocess
                self._process = subprocess.Popen(
                    [
                        sys.executable,
                        str(main_py),
                        "--api-only",
                        "--host", API_HOST,
                        "--port", str(API_PORT),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
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
            if self._process and self._process.poll() is not None:
                return False

        return False

    def stop(self):
        """Stop the backend server gracefully"""
        self._should_restart = False

        with self._lock:
            if self._process is None:
                return

            try:
                # Send SIGTERM for graceful shutdown
                self._process.terminate()

                # Wait up to 5 seconds for graceful shutdown
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    self._process.kill()
                    self._process.wait()

            except Exception as e:
                print(f"Error stopping backend: {e}")
            finally:
                self._process = None

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
