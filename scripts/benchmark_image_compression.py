"""Read-only screenshot codec benchmark. Writes aggregate metrics, never images or OCR.

Run with the application Python environment. Source files are only opened for reading.
"""

import argparse
import io
import json
import time
from pathlib import Path
from typing import TypedDict

import numpy as np
from PIL import Image, features
from skimage.metrics import structural_similarity


class CodecMetrics(TypedDict):
    bytes: int
    encode_seconds: float
    ssim: list[float]


def benchmark(directory: Path, sample_count: int) -> dict:
    paths = sorted(path for path in directory.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".webp"})
    if not paths:
        raise ValueError("No JPEG or WebP images found")
    indices = sorted(set(np.linspace(0, len(paths) - 1, min(sample_count, len(paths)), dtype=int)))
    codecs = [
        ("jpeg85", "JPEG", {"quality": 85, "optimize": True}),
        ("jpeg75", "JPEG", {"quality": 75, "optimize": True}),
        ("webp85", "WEBP", {"quality": 85, "method": 4}),
        ("webp85_fast", "WEBP", {"quality": 85, "method": 0}),
        ("webp80", "WEBP", {"quality": 80, "method": 4}),
        ("webp_lossless", "WEBP", {"lossless": True, "method": 4}),
    ]
    results: dict[str, CodecMetrics] = {name: {"bytes": 0, "encode_seconds": 0.0, "ssim": []} for name, _, _ in codecs}
    original_bytes = 0
    for index in indices:
        path = paths[index]
        original_bytes += path.stat().st_size
        with Image.open(path) as source:
            image = source.convert("RGB")
        # Full-resolution luminance SSIM measures text edges without exporting pixels.
        reference = np.asarray(image.convert("L"))
        for name, codec, options in codecs:
            buffer = io.BytesIO()
            started = time.perf_counter()
            image.save(buffer, codec, **options)
            results[name]["encode_seconds"] += time.perf_counter() - started
            results[name]["bytes"] += buffer.tell()
            buffer.seek(0)
            with Image.open(buffer) as decoded:
                candidate = np.asarray(decoded.convert("L"))
            score = structural_similarity(reference, candidate, data_range=255)
            results[name]["ssim"].append(float(score))
    summary = {}
    for name, result in results.items():
        summary[name] = {
            "bytes": result["bytes"],
            "encode_seconds": result["encode_seconds"],
            "ssim_mean": float(np.mean(result["ssim"])),
            "ssim_min": min(result["ssim"]),
            "saving_percent": 100 * (1 - result["bytes"] / original_bytes),
            "encode_ms_per_image": result["encode_seconds"] * 1000 / len(indices),
        }
    return {
        "available_images": len(paths),
        "sample_count": len(indices),
        "original_bytes": original_bytes,
        "sampling": "evenly spaced lexicographic filenames, includes oldest and newest",
        "pillow_webp_available": features.check("webp"),
        "results": summary,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    metrics = benchmark(args.directory, args.samples)
    args.output.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))
