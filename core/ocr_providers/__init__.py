"""
LiveRecall OCR Providers

This package contains OCR provider implementations.
Each provider implements the OCRProvider protocol from core.ocr.

Available providers:
- apple_vision: Native macOS Vision framework (macOS only)
- tesseract: Tesseract OCR engine (cross-platform)

To add a new provider:
1. Create a new file in this directory (e.g., paddleocr.py)
2. Implement the OCRProvider protocol
3. Register it in core/ocr.py _register_providers()
"""

from __future__ import annotations

# Providers are imported conditionally in core/ocr.py based on availability
__all__ = []
