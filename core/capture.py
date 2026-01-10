"""
LiveRecall Screen Capture
Cross-platform screenshot capture using mss
Lightweight - no CLIP model, just saves images with has_embedding=0
"""

import threading
import time
from collections.abc import Callable

import cv2
import mss
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

from core.config import config, get_screenshots_dir
from core.database import db


class CaptureService:
    """Screen capture service - runs in background thread"""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._previous_screenshot: np.ndarray | None = None
        self._on_capture: Callable[[str], None] | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, on_capture: Callable[[str], None] | None = None):
        """Start capturing screenshots in background"""
        if self._running:
            return

        self._running = True
        self._on_capture = on_capture
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print("Capture service started")

    def stop(self):
        """Stop capturing"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        print("Capture service stopped")

    def _grab_screen(self) -> Image.Image:
        """Capture the current screen using mss"""
        with mss.mss() as sct:
            # Capture primary monitor
            monitor = sct.monitors[1]  # monitors[0] is all monitors combined
            screenshot = sct.grab(monitor)
            # Convert to PIL Image
            return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    def _image_to_array(self, image: Image.Image) -> np.ndarray:
        """Convert PIL Image to numpy array"""
        return np.array(image)

    def _calculate_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calculate Structural Similarity Index between two images"""
        # Convert to grayscale for SSIM
        gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)

        # Resize if dimensions don't match
        if gray1.shape != gray2.shape:
            gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))

        score, _ = ssim(gray1, gray2, full=True)
        return score

    def _generate_filename(self) -> str:
        """Generate filename with timestamp"""
        timestamp = time.strftime("%y%m%d%H%M%S")
        return f"Snap-{timestamp}.jpg"

    def _save_screenshot(self, image: Image.Image) -> str:
        """Save screenshot to disk and database"""
        screenshots_dir = get_screenshots_dir()
        filename = self._generate_filename()
        filepath = screenshots_dir / filename

        # Convert to RGB if needed (for JPEG)
        if image.mode == "RGBA":
            image = image.convert("RGB")

        # Save image
        image.save(str(filepath), "JPEG", quality=config.capture.quality)

        # Check if incognito mode is active (auto-expires if needed)
        is_hidden = config.is_incognito_mode()

        # Add to database (without embedding)
        timestamp = time.strftime("%y%m%d%H%M%S")
        db.add_screenshot(str(filepath), timestamp, is_hidden=is_hidden)

        return str(filepath)

    def _capture_loop(self):
        """Main capture loop"""
        # Initialize with first screenshot
        self._previous_screenshot = self._image_to_array(self._grab_screen())

        while self._running:
            try:
                time.sleep(config.capture.interval)

                if not self._running:
                    break

                # Capture current screen
                current_image = self._grab_screen()
                current_array = self._image_to_array(current_image)

                # Calculate similarity with previous
                similarity = self._calculate_ssim(self._previous_screenshot, current_array)

                # Check if screen changed enough
                if similarity < config.capture.threshold:
                    print(f"Change detected (similarity: {similarity:.2f})")
                    self._previous_screenshot = current_array

                    # Wait for screen to stabilize
                    stable_checks = 3
                    while stable_checks > 0 and self._running:
                        stable_checks -= 1
                        time.sleep(config.capture.interval * 0.3)

                        new_image = self._grab_screen()
                        new_array = self._image_to_array(new_image)
                        stability = self._calculate_ssim(self._previous_screenshot, new_array)

                        if stability <= config.capture.save_threshold:
                            # Still changing, reset
                            break
                    else:
                        # Screen is stable, save screenshot
                        filepath = self._save_screenshot(current_image)
                        print(f"Screenshot saved: {filepath}")

                        if self._on_capture:
                            self._on_capture(filepath)

                        self._previous_screenshot = current_array

            except Exception as e:
                print(f"Capture error: {e}")
                time.sleep(config.capture.interval)

    def capture_now(self) -> str:
        """Manually capture a screenshot immediately"""
        image = self._grab_screen()
        filepath = self._save_screenshot(image)
        self._previous_screenshot = self._image_to_array(image)
        return filepath


# Global capture service instance
capture_service = CaptureService()


if __name__ == "__main__":
    # Test capture
    from core.database import db

    db.connect()

    print("Testing single capture...")
    filepath = capture_service.capture_now()
    print(f"Captured: {filepath}")

    print("\nDatabase stats:", db.get_stats())

    print("\nStarting continuous capture (Ctrl+C to stop)...")
    capture_service.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        capture_service.stop()
        print("\nStopped")

    db.disconnect()
