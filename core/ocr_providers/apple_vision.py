"""
Apple Vision OCR Provider

Uses macOS native Vision framework via the ocrmac library.
This is the recommended provider for macOS due to:
- Native Apple Silicon optimization (Neural Engine)
- Zero additional memory overhead (uses system APIs)
- Fast processing (~200ms per image)
- Excellent accuracy on UI text and screen content

Requirements:
- macOS 10.15+ (Catalina or later)
- pip install ocrmac
"""

from __future__ import annotations

import platform
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ocrmac.ocrmac import OCR as OCRType

    from core.ocr import OCRResult

# Module-level singleton for OCR class (following codebase conventions)
_ocr_class: type[OCRType] | None = None
_ocr_class_lock = threading.Lock()


def _get_ocr_class() -> type[OCRType]:
    """Get the OCR class, loading it if necessary (module-level singleton)"""
    global _ocr_class
    # Fast path: check without lock
    if _ocr_class is not None:
        return _ocr_class

    # Double-checked locking for thread-safe initialization
    with _ocr_class_lock:
        # Re-check inside lock
        if _ocr_class is None:
            try:
                from ocrmac.ocrmac import OCR

                _ocr_class = OCR
            except ImportError as e:
                raise ImportError("ocrmac is required for Apple Vision OCR. Install it with: pip install ocrmac") from e
    return _ocr_class


class AppleVisionOCR:
    """
    OCR provider using Apple's Vision framework.

    This provider is only available on macOS and uses the native
    Vision framework for text recognition, which provides:
    - Hardware acceleration on Apple Silicon
    - No additional model downloads required
    - Excellent accuracy for screen content
    """

    name = "apple_vision"

    def extract_text(self, image_path: str | Path) -> OCRResult:
        """
        Extract text from an image using Apple Vision.

        Args:
            image_path: Path to the image file

        Returns:
            OCRResult with extracted text and confidence
        """
        from core.ocr import OCRResult

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        OCR = _get_ocr_class()

        try:
            # ocrmac returns list of (text, confidence, bbox) tuples
            results = OCR(str(image_path)).recognize()

            if not results:
                return OCRResult.empty()

            # Combine all text with newlines between blocks
            texts = []
            confidences = []

            for item in results:
                if len(item) >= 2:
                    text, confidence = item[0], item[1]
                    if text and text.strip():
                        texts.append(text.strip())
                        if confidence is not None:
                            confidences.append(confidence)

            full_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else None
            word_count = len(full_text.split()) if full_text else 0

            return OCRResult(
                text=full_text,
                confidence=avg_confidence,
                word_count=word_count,
                language="en",  # Vision framework auto-detects but we default to en
            )

        except Exception as e:
            print(f"Apple Vision OCR error: {e}")
            # Return empty result on error rather than raising
            return OCRResult.empty()

    def is_available(self) -> bool:
        """Check if Apple Vision OCR is available"""
        if platform.system() != "Darwin":
            return False

        try:
            from ocrmac.ocrmac import OCR  # noqa: F401

            return True
        except ImportError:
            return False

    def get_model_info(self) -> dict:
        """Get information about the Vision framework"""
        import platform as plat

        return {
            "engine": "Apple Vision Framework",
            "platform": "macOS",
            "macos_version": plat.mac_ver()[0] if plat.system() == "Darwin" else None,
            "requires_download": False,
            "memory_overhead": "minimal (uses system APIs)",
            "supported_languages": ["en", "zh", "ja", "ko", "de", "fr", "it", "pt", "es"],
        }
