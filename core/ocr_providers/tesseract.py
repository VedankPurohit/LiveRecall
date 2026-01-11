"""
Tesseract OCR Provider

Uses Tesseract OCR engine via pytesseract library.
This is the recommended provider for Windows and as a cross-platform fallback.

Advantages:
- Cross-platform (Windows, macOS, Linux)
- Lightweight (~50MB memory)
- Fast processing (~100ms per image)
- Well-tested and stable

Requirements:
- Tesseract binary installed on system:
  - Windows: choco install tesseract OR download from https://github.com/UB-Mannheim/tesseract/wiki
  - macOS: brew install tesseract
  - Linux: apt install tesseract-ocr
- pip install pytesseract
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.ocr import OCRResult


class TesseractOCR:
    """
    OCR provider using Tesseract OCR engine.

    This provider works cross-platform and is the default
    for Windows systems. It requires the Tesseract binary
    to be installed on the system.
    """

    name = "tesseract"

    def __init__(self):
        self._pytesseract = None

    def _get_pytesseract(self):
        """Lazy load pytesseract"""
        if self._pytesseract is None:
            try:
                import pytesseract

                self._pytesseract = pytesseract
            except ImportError as e:
                raise ImportError(
                    "pytesseract is required for Tesseract OCR. Install it with: pip install pytesseract"
                ) from e
        return self._pytesseract

    def extract_text(self, image_path: str | Path) -> OCRResult:
        """
        Extract text from an image using Tesseract.

        Args:
            image_path: Path to the image file

        Returns:
            OCRResult with extracted text and confidence
        """
        from core.ocr import OCRResult

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        pytesseract = self._get_pytesseract()

        try:
            from PIL import Image

            image = Image.open(image_path)

            # Get detailed OCR data including confidence scores
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            # Filter and collect text with confidence
            words = []
            confidences = []

            for i, conf in enumerate(data["conf"]):
                # Tesseract returns -1 for non-text elements
                if int(conf) > 0:
                    text = data["text"][i]
                    if text and text.strip():
                        words.append(text.strip())
                        confidences.append(int(conf))

            # Join words into full text
            full_text = " ".join(words)

            # Calculate average confidence (Tesseract uses 0-100 scale)
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else None

            return OCRResult(
                text=full_text,
                confidence=avg_confidence,
                word_count=len(words),
                language="en",
            )

        except Exception as e:
            print(f"Tesseract OCR error: {e}")
            return OCRResult.empty()

    def is_available(self) -> bool:
        """Check if Tesseract is available"""
        # Check if pytesseract is installed
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            return False

        # Check if tesseract binary is available
        tesseract_cmd = shutil.which("tesseract")
        return tesseract_cmd is not None

    def get_model_info(self) -> dict:
        """Get information about the Tesseract installation"""
        tesseract_path = shutil.which("tesseract")
        version = None

        if tesseract_path:
            try:
                import subprocess

                result = subprocess.run([tesseract_path, "--version"], capture_output=True, text=True, timeout=5)
                # First line contains version
                version = result.stdout.split("\n")[0] if result.stdout else None
            except Exception:
                pass

        return {
            "engine": "Tesseract OCR",
            "binary_path": tesseract_path,
            "version": version,
            "requires_download": True,
            "memory_overhead": "~50MB",
            "supported_languages": self._get_installed_languages(),
        }

    def _get_installed_languages(self) -> list[str]:
        """Get list of installed Tesseract language packs"""
        try:
            pytesseract = self._get_pytesseract()
            langs = pytesseract.get_languages()
            return langs if langs else ["eng"]
        except Exception:
            return ["eng"]  # Default assumption
