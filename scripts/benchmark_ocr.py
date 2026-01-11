#!/usr/bin/env python3
"""
Benchmark script for OCR and embedding performance.

Tests:
1. CLIP image embedding
2. OCR text extraction
3. Text chunking
4. Text embedding generation (single + batch)

Usage:
    uv run python scripts/benchmark_ocr.py
    uv run python scripts/benchmark_ocr.py --count 50
    uv run python scripts/benchmark_ocr.py --show-ocr
"""

import argparse
import contextlib
import random
import statistics
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def warmup_models():
    """Pre-load all models so benchmark isn't skewed by loading time"""
    print("\n" + "=" * 60)
    print("WARMING UP MODELS (loading into memory)")
    print("=" * 60)

    # CLIP model
    print("  Loading CLIP model...", end=" ", flush=True)
    start = time.perf_counter()
    # Create a tiny test image to trigger model load
    import tempfile

    from PIL import Image

    from core.embeddings import get_image_embedding

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img = Image.new("RGB", (100, 100), color="white")
        img.save(f.name)
        with contextlib.suppress(Exception):
            get_image_embedding(f.name)
        Path(f.name).unlink()
    print(f"done ({time.perf_counter() - start:.1f}s)")

    # OCR service
    print("  Loading OCR service...", end=" ", flush=True)
    start = time.perf_counter()
    from core.ocr import ocr_service

    if ocr_service.is_available():
        print(f"done - {ocr_service.get_provider_name()} ({time.perf_counter() - start:.1f}s)")
    else:
        print("not available")

    # Text embedding model
    print("  Loading text embedding model...", end=" ", flush=True)
    start = time.perf_counter()
    from core.text_embeddings import text_embedding_service

    text_embedding_service.get_text_embedding("warmup test")
    print(f"done ({time.perf_counter() - start:.1f}s)")

    print("  All models loaded!\n")


def get_random_images(directory: str, count: int) -> list[Path]:
    """Get random sample of images from directory"""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    images = list(dir_path.glob("*.jpg")) + list(dir_path.glob("*.jpeg")) + list(dir_path.glob("*.png"))
    if not images:
        print(f"Error: No images found in {directory}")
        sys.exit(1)

    count = min(count, len(images))
    return random.sample(images, count)


def benchmark_clip(images: list[Path]) -> dict:
    """Benchmark CLIP image embedding"""
    from core.embeddings import get_image_embedding

    print("\n" + "=" * 60)
    print("CLIP IMAGE EMBEDDING BENCHMARK")
    print("=" * 60)

    times = []
    for i, img in enumerate(images):
        start = time.perf_counter()
        embedding = get_image_embedding(str(img))
        elapsed = time.perf_counter() - start
        times.append(elapsed)

        if i < 3:  # Show first few
            print(f"  [{i+1}] {img.name}: {elapsed*1000:.1f}ms (dim={len(embedding)})")
        elif i == 3:
            print(f"  ... processing {len(images) - 3} more ...")

    return {
        "name": "CLIP Embedding",
        "count": len(times),
        "total": sum(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
    }


def benchmark_ocr(images: list[Path], show_output: bool = False) -> dict:
    """Benchmark OCR text extraction"""
    from core.ocr import ocr_service

    print("\n" + "=" * 60)
    print("OCR TEXT EXTRACTION BENCHMARK")
    print("=" * 60)

    if not ocr_service.is_available():
        print("  ERROR: OCR service not available")
        return {"name": "OCR", "error": "not available"}

    print(f"  Provider: {ocr_service.get_provider_name()}")

    times = []
    results = []
    for i, img in enumerate(images):
        start = time.perf_counter()
        result = ocr_service.extract_text(str(img))
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        results.append(result)

        word_count = result.word_count
        text_preview = (
            result.text[:50].replace("\n", " ") + "..." if len(result.text) > 50 else result.text.replace("\n", " ")
        )

        if i < 5 or show_output:  # Show first few or all if requested
            print(f"  [{i+1}] {img.name}: {elapsed*1000:.1f}ms")
            conf_str = f"{result.confidence:.2f}" if result.confidence is not None else "N/A"
            print(f"       Words: {word_count}, Confidence: {conf_str}")
            if show_output:
                print(f"       Text: {text_preview}")
                print()
        elif i == 5:
            print(f"  ... processing {len(images) - 5} more ...")

    # Show OCR result structure
    if results:
        print("\n  OCR Result Structure:")
        print("    - text: str (full extracted text)")
        print("    - confidence: float | None (0-1)")
        print("    - word_count: int")
        print("    - language: str (default 'en')")

        # Show a full example
        if show_output and results[0].text:
            print("\n  Full OCR Output Example (first image with text):")
            for r in results:
                if r.text.strip():
                    print("-" * 40)
                    print(r.text[:500])
                    if len(r.text) > 500:
                        print(f"... ({len(r.text)} chars total)")
                    print("-" * 40)
                    break

    return {
        "name": "OCR Extraction",
        "count": len(times),
        "total": sum(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
        "avg_words": statistics.mean([r.word_count for r in results]),
        "empty_count": sum(1 for r in results if not r.text.strip()),
    }


def benchmark_chunking(ocr_texts: list[str]) -> dict:
    """Benchmark text chunking"""
    from core import chunking

    print("\n" + "=" * 60)
    print("TEXT CHUNKING BENCHMARK")
    print("=" * 60)

    times = []
    chunk_counts = []

    for i, text in enumerate(ocr_texts):
        if not text.strip():
            continue

        start = time.perf_counter()
        result = chunking.chunk_ocr_text(
            text,
            small_size=512,
            small_overlap=50,
            large_size=2048,
            large_overlap=200,
        )
        elapsed = time.perf_counter() - start
        times.append(elapsed)

        total_chunks = len(result.small) + len(result.large)
        chunk_counts.append(total_chunks)

        if i < 3:
            print(f"  [{i+1}] {len(text)} chars: {elapsed*1000:.2f}ms")
            print(f"       Small chunks: {len(result.small)}, Large chunks: {len(result.large)}")

    if not times:
        print("  No text to chunk (all OCR results were empty)")
        return {"name": "Chunking", "error": "no text"}

    print("\n  Chunk Structure (ChunkInfo):")
    print("    - text: str (chunk content)")
    print("    - start_char: int")
    print("    - end_char: int")
    print("    - index: int")

    return {
        "name": "Text Chunking",
        "count": len(times),
        "total": sum(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
        "avg_chunks": statistics.mean(chunk_counts),
    }


def benchmark_text_embedding(texts: list[str]) -> dict:
    """Benchmark text embedding generation"""
    from core.text_embeddings import text_embedding_service

    print("\n" + "=" * 60)
    print("TEXT EMBEDDING BENCHMARK")
    print("=" * 60)

    # Filter to non-empty texts and take a sample
    valid_texts = [t[:1000] for t in texts if t.strip()][:50]  # Cap at 1000 chars, 50 texts

    if not valid_texts:
        print("  No valid texts to embed")
        return {"name": "Text Embedding", "error": "no text"}

    print(
        f"  Model: {text_embedding_service._current_model_name if hasattr(text_embedding_service, '_current_model_name') else 'BGE'}"
    )

    # Single embedding benchmark
    print("\n  Single embedding (one at a time):")
    single_times = []
    for i, text in enumerate(valid_texts[:10]):  # Just first 10 for single
        start = time.perf_counter()
        emb = text_embedding_service.get_text_embedding(text)
        elapsed = time.perf_counter() - start
        single_times.append(elapsed)
        if i < 3:
            print(f"    [{i+1}] {len(text)} chars: {elapsed*1000:.1f}ms (dim={len(emb)})")

    # Batch embedding benchmark
    print("\n  Batch embedding (all at once):")
    batch_sizes = [10, 25, 50]
    batch_results = {}

    for batch_size in batch_sizes:
        if batch_size > len(valid_texts):
            continue

        batch = valid_texts[:batch_size]
        start = time.perf_counter()
        _ = text_embedding_service.get_batch_embeddings(batch)
        elapsed = time.perf_counter() - start

        per_item = elapsed / batch_size
        batch_results[batch_size] = {
            "total": elapsed,
            "per_item": per_item,
        }
        print(f"    Batch of {batch_size}: {elapsed*1000:.1f}ms total, {per_item*1000:.1f}ms/item")

    return {
        "name": "Text Embedding",
        "single_mean": statistics.mean(single_times),
        "single_count": len(single_times),
        "batch_results": batch_results,
    }


def print_summary(results: list[dict]):
    """Print summary of all benchmarks"""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for r in results:
        if "error" in r:
            print(f"\n  {r['name']}: ERROR - {r['error']}")
            continue

        print(f"\n  {r['name']}:")
        if "mean" in r:
            print(f"    Mean:   {r['mean']*1000:.1f}ms")
            print(f"    Median: {r['median']*1000:.1f}ms")
            print(f"    Min:    {r['min']*1000:.1f}ms")
            print(f"    Max:    {r['max']*1000:.1f}ms")
            if r.get("stdev"):
                print(f"    StdDev: {r['stdev']*1000:.1f}ms")
        if "avg_words" in r:
            print(f"    Avg words/image: {r['avg_words']:.1f}")
            print(f"    Empty OCR count: {r['empty_count']}")
        if "avg_chunks" in r:
            print(f"    Avg chunks/text: {r['avg_chunks']:.1f}")
        if "batch_results" in r:
            print(f"    Single embedding: {r['single_mean']*1000:.1f}ms")
            for bs, br in r["batch_results"].items():
                print(f"    Batch {bs}: {br['per_item']*1000:.1f}ms/item ({br['total']*1000:.0f}ms total)")

    # Estimate total processing time per image
    print("\n" + "-" * 60)
    print("  ESTIMATED TOTAL PER IMAGE:")

    clip_time = next((r["mean"] for r in results if r["name"] == "CLIP Embedding" and "mean" in r), 0)
    ocr_time = next((r["mean"] for r in results if r["name"] == "OCR Extraction" and "mean" in r), 0)
    chunk_time = next((r["mean"] for r in results if r["name"] == "Text Chunking" and "mean" in r), 0)

    # Get best batch embedding time
    emb_result = next((r for r in results if r["name"] == "Text Embedding"), None)
    emb_time = 0
    if emb_result and "batch_results" in emb_result:
        # Use largest batch per-item time
        largest = max(emb_result["batch_results"].keys())
        emb_time = emb_result["batch_results"][largest]["per_item"]
        avg_chunks = next((r["avg_chunks"] for r in results if "avg_chunks" in r), 6)
        emb_time = emb_time * avg_chunks  # Multiply by avg chunks per image

    total = clip_time + ocr_time + chunk_time + emb_time
    print(f"    CLIP:      {clip_time*1000:.0f}ms")
    print(f"    OCR:       {ocr_time*1000:.0f}ms")
    print(f"    Chunking:  {chunk_time*1000:.0f}ms")
    print(f"    Embedding: {emb_time*1000:.0f}ms (batch, ~{avg_chunks:.0f} chunks)")
    print("    ─────────────────────")
    print(f"    TOTAL:     {total*1000:.0f}ms/image")
    print(f"\n    For 20,000 images: ~{total*20000/60:.0f} minutes")


def main():
    parser = argparse.ArgumentParser(description="Benchmark OCR and embedding performance")
    parser.add_argument(
        "--dir",
        default="/Users/vedank/Library/Application Support/LiveRecall/screenshots",
        help="Directory containing screenshots",
    )
    parser.add_argument("--count", type=int, default=100, help="Number of images to test")
    parser.add_argument("--show-ocr", action="store_true", help="Show full OCR output for each image")
    parser.add_argument("--skip-clip", action="store_true", help="Skip CLIP benchmark")
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR benchmark")
    parser.add_argument("--skip-embedding", action="store_true", help="Skip embedding benchmark")

    args = parser.parse_args()

    print(f"Benchmarking with {args.count} random images from:")
    print(f"  {args.dir}")

    images = get_random_images(args.dir, args.count)
    print(f"  Found {len(images)} images")

    # Warmup - load all models first
    warmup_models()

    results = []

    # CLIP benchmark
    if not args.skip_clip:
        results.append(benchmark_clip(images[:20]))  # CLIP is slow, just do 20

    # OCR benchmark
    ocr_texts = []
    if not args.skip_ocr:
        ocr_result = benchmark_ocr(images, show_output=args.show_ocr)
        results.append(ocr_result)

        # Get OCR texts for chunking benchmark
        from core.ocr import ocr_service

        for img in images:
            try:
                r = ocr_service.extract_text(str(img))
                ocr_texts.append(r.text)
            except Exception:
                ocr_texts.append("")

    # Chunking benchmark
    if ocr_texts:
        results.append(benchmark_chunking(ocr_texts))

    # Text embedding benchmark
    if not args.skip_embedding and ocr_texts:
        results.append(benchmark_text_embedding(ocr_texts))

    # Summary
    print_summary(results)


if __name__ == "__main__":
    main()
