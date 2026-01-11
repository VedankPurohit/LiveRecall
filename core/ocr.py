"""
LiveRecall OCR Service
Abstraction layer for OCR text extraction with pluggable providers

=============================================================================
OCR PROVIDER OPTIONS
=============================================================================

Current: Apple Vision (macOS) / Tesseract (Windows)
  - Apple Vision: Native macOS, zero memory overhead, fast (~200ms), excellent on UI text
  - Tesseract: Cross-platform, lightweight (~50MB), stable

Upgrade options (better accuracy):
  - PaddleOCR PP-OCRv4: pip install paddleocr paddlepaddle
    Best balance of accuracy/speed, complex macOS install
  - docTR: pip install python-doctr[torch]
    Good accuracy, clean install, Apache 2.0
  - EasyOCR: pip install easyocr
    Easy install but heavy (1-2GB memory)

High-end (if hardware allows):
  - GOT-OCR2: State-of-the-art, 8GB+ VRAM required
  - Surya: Excellent accuracy but GPL license (problematic for MIT projects)

To switch provider:
  1. Update config: config.ocr.provider = "paddleocr"
  2. Run: ocr_service.recompute_all_ocr()
=============================================================================
"""

from __future__ import annotations

import platform
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class OCRResult:
    """Result from OCR text extraction"""

    text: str
    confidence: float | None = None
    word_count: int = 0
    language: str = "en"

    @classmethod
    def empty(cls) -> OCRResult:
        """Create an empty OCR result for images with no text"""
        return cls(text="", confidence=None, word_count=0)


@runtime_checkable
class OCRProvider(Protocol):
    """
    Abstract interface for OCR engines.

    Implement this protocol to add a new OCR provider.
    See core/ocr_providers/ for example implementations.
    """

    name: str

    def extract_text(self, image_path: str | Path) -> OCRResult:
        """Extract text from an image file"""
        ...

    def is_available(self) -> bool:
        """Check if this provider is available on the current system"""
        ...

    def get_model_info(self) -> dict:
        """Get information about the OCR model/engine"""
        ...


class OCRService:
    """
    OCR service with pluggable providers.

    Supports automatic provider selection based on platform and config.
    Providers are registered and can be switched at runtime.
    """

    _providers: dict[str, type[OCRProvider]] = {}

    def __init__(self):
        self._current_provider: OCRProvider | None = None
        self._provider_cache: dict[str, OCRProvider] = {}
        self._lock = threading.Lock()

    @classmethod
    def register(cls, name: str, provider_class: type[OCRProvider]) -> None:
        """Register an OCR provider"""
        cls._providers[name] = provider_class

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of registered provider names"""
        return list(cls._providers.keys())

    def get_provider(self, provider_name: str | None = None) -> OCRProvider:
        """
        Get an OCR provider instance.

        Args:
            provider_name: Specific provider to use. If None or "auto",
                          automatically selects based on platform.
        """
        if provider_name is None or provider_name == "auto":
            provider_name = self._get_default_provider_name()

        if provider_name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(f"Unknown OCR provider: {provider_name}. Available: {available}")

        # Check cache first (fast path without lock)
        if provider_name in self._provider_cache:
            return self._provider_cache[provider_name]

        # Double-checked locking for thread-safe initialization
        with self._lock:
            # Re-check inside lock in case another thread initialized
            if provider_name in self._provider_cache:
                return self._provider_cache[provider_name]

            provider_class = self._providers[provider_name]
            provider = provider_class()

            if not provider.is_available():
                raise RuntimeError(f"OCR provider '{provider_name}' is not available on this system")

            # Cache for reuse
            self._provider_cache[provider_name] = provider
            return provider

    def _get_default_provider_name(self) -> str:
        """Get the default provider name based on platform"""
        system = platform.system()

        if system == "Darwin" and "apple_vision" in self._providers:
            return "apple_vision"
        elif system == "Windows" and "tesseract" in self._providers:
            return "tesseract"

        # Fallback to tesseract if available
        if "tesseract" in self._providers:
            return "tesseract"

        # Return first available provider
        if self._providers:
            return next(iter(self._providers.keys()))

        raise RuntimeError("No OCR providers registered")

    def extract_text(self, image_path: str | Path, provider_name: str | None = None) -> OCRResult:
        """
        Extract text from an image.

        Args:
            image_path: Path to the image file
            provider_name: Specific provider to use (None for auto)

        Returns:
            OCRResult with extracted text and metadata
        """
        provider = self.get_provider(provider_name)
        return provider.extract_text(image_path)

    def get_current_provider_info(self, provider_name: str | None = None) -> dict:
        """Get information about the current/specified provider"""
        provider = self.get_provider(provider_name)
        return {
            "name": provider.name,
            "available": provider.is_available(),
            **provider.get_model_info(),
        }

    def is_available(self) -> bool:
        """Check if any OCR provider is available"""
        try:
            self.get_provider()
            return True
        except (ValueError, RuntimeError):
            return False

    def get_provider_name(self) -> str:
        """Get the name of the current/default provider"""
        try:
            provider = self.get_provider()
            return provider.name
        except (ValueError, RuntimeError):
            return "none"


# Global OCR service instance
ocr_service = OCRService()


def _register_providers():
    """Register available OCR providers"""
    # Import and register Apple Vision provider (macOS only)
    if platform.system() == "Darwin":
        try:
            from core.ocr_providers.apple_vision import AppleVisionOCR

            OCRService.register("apple_vision", AppleVisionOCR)
        except ImportError:
            pass  # ocrmac not installed

    # Import and register Tesseract provider (cross-platform)
    try:
        from core.ocr_providers.tesseract import TesseractOCR

        OCRService.register("tesseract", TesseractOCR)
    except ImportError:
        pass  # pytesseract not installed


# Register providers on module load
_register_providers()


# Convenience functions
def extract_text(image_path: str | Path, provider_name: str | None = None) -> OCRResult:
    """Extract text from an image (convenience function)"""
    return ocr_service.extract_text(image_path, provider_name)


def get_ocr_provider_info(provider_name: str | None = None) -> dict:
    """Get OCR provider information (convenience function)"""
    return ocr_service.get_current_provider_info(provider_name)


def get_available_providers() -> list[str]:
    """Get list of available OCR providers"""
    return OCRService.get_available_providers()


if __name__ == "__main__":
    print("OCR Service Test")
    print(f"Platform: {platform.system()}")
    print(f"Available providers: {get_available_providers()}")

    if get_available_providers():
        info = get_ocr_provider_info()
        print(f"Default provider info: {info}")
