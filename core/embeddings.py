"""
LiveRecall Embeddings
Lazy-loaded CLIP model for generating image and text embeddings
With auto-unload capability for memory management
"""

import contextlib
import gc
import os
import threading
import time
import warnings

# Suppress HuggingFace warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", message=".*use_fast.*")
warnings.filterwarnings("ignore", category=FutureWarning)

import torch  # noqa: E402
from PIL import Image  # noqa: E402

# Lazy loading state
_model = None
_device = None
_last_used: float = 0
_auto_unload_timer: threading.Timer | None = None
_lock = threading.Lock()

# Configuration
AUTO_UNLOAD_SECONDS = 300  # 5 minutes of idle before unloading


def _get_device() -> str:
    """Get the best available device"""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon
    return "cpu"


def _load_model():
    """Load the CLIP model (only called once)"""
    global _model, _device, _last_used

    with _lock:
        if _model is not None:
            _last_used = time.time()
            return _model

        print("Loading CLIP model (this may take a moment)...")

        from sentence_transformers import SentenceTransformer

        _device = _get_device()
        print(f"Using device: {_device}")

        try:
            _model = SentenceTransformer("clip-ViT-L-14", device=_device)
        except Exception as e:
            print(f"Error loading on {_device}, falling back to CPU: {e}")
            _device = "cpu"
            _model = SentenceTransformer("clip-ViT-L-14", device="cpu")

        _last_used = time.time()
        print("CLIP model loaded successfully")

        # Start auto-unload timer
        _schedule_auto_unload()

        return _model


def _schedule_auto_unload():
    """Schedule auto-unload after idle timeout"""
    global _auto_unload_timer

    # Cancel existing timer
    if _auto_unload_timer is not None:
        _auto_unload_timer.cancel()

    if AUTO_UNLOAD_SECONDS <= 0:
        _auto_unload_timer = None
        return

    # Schedule new timer
    _auto_unload_timer = threading.Timer(AUTO_UNLOAD_SECONDS, _check_and_unload)
    _auto_unload_timer.daemon = True
    _auto_unload_timer.start()


def _check_and_unload():
    """Check if model should be unloaded due to inactivity"""
    global _last_used

    idle_time = time.time() - _last_used
    if idle_time >= AUTO_UNLOAD_SECONDS:
        print(f"CLIP model idle for {idle_time:.0f}s, unloading...")
        unload_model()
    else:
        # Reschedule check
        _schedule_auto_unload()


def unload_model():
    """Explicitly unload the CLIP model to free memory"""
    global _model, _device, _auto_unload_timer

    with _lock:
        if _auto_unload_timer is not None:
            _auto_unload_timer.cancel()
            _auto_unload_timer = None

        if _model is None:
            return

        print("Unloading CLIP model...")

        # Delete model
        del _model
        _model = None
        gc.collect()

        # Clear GPU memory if applicable
        if _device == "cuda":
            torch.cuda.empty_cache()
        elif _device == "mps":
            with contextlib.suppress(Exception):
                torch.mps.empty_cache()

        _device = None
        print("CLIP model unloaded")


def is_loaded() -> bool:
    """Check if the model is currently loaded"""
    return _model is not None


def is_downloaded() -> bool:
    """Check if the CLIP model is downloaded in HuggingFace cache"""
    try:
        from huggingface_hub import try_to_load_from_cache

        # clip-ViT-L-14 maps to sentence-transformers/clip-ViT-L-14
        model_id = "sentence-transformers/clip-ViT-L-14"

        # Check for the sentence-transformers config file
        result = try_to_load_from_cache(model_id, "config_sentence_transformers.json")
        if result is not None:
            return True
        # Fallback: some caches/models may use config.json
        result = try_to_load_from_cache(model_id, "config.json")
        return result is not None
    except Exception:
        return False


def get_model_status() -> dict:
    """Get detailed model status"""
    return {
        "loaded": _model is not None,
        "downloaded": is_downloaded(),
        "device": _device,
        "last_used": _last_used,
        "idle_seconds": time.time() - _last_used if _last_used > 0 else 0,
        "auto_unload_seconds": AUTO_UNLOAD_SECONDS,
    }


def set_auto_unload_timeout(seconds: int):
    """Set the auto-unload timeout (0 to disable)"""
    global AUTO_UNLOAD_SECONDS
    AUTO_UNLOAD_SECONDS = seconds
    if seconds > 0 and _model is not None:
        _schedule_auto_unload()


def _normalize(embedding) -> list[float]:
    """Normalize embedding to unit length for cosine similarity"""
    import numpy as np

    arr = np.array(embedding)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


def get_image_embedding(image_path: str) -> list[float]:
    """Generate normalized embedding for an image file"""
    global _last_used

    model = _load_model()
    _last_used = time.time()

    try:
        with Image.open(image_path) as image:
            embedding = model.encode(image, convert_to_tensor=False)
        return _normalize(embedding)
    except Exception as e:
        print(f"Error generating image embedding: {e}")
        raise


def get_image_embedding_from_bytes(image_bytes: bytes) -> list[float]:
    """Generate normalized embedding for an image from raw bytes"""
    global _last_used

    model = _load_model()
    _last_used = time.time()

    try:
        import io

        image = Image.open(io.BytesIO(image_bytes))
        embedding = model.encode(image, convert_to_tensor=False)
        return _normalize(embedding)
    except Exception as e:
        print(f"Error generating image embedding from bytes: {e}")
        raise


def get_text_embedding(text: str) -> list[float]:
    """Generate normalized embedding for a text query"""
    global _last_used

    model = _load_model()
    _last_used = time.time()

    try:
        embedding = model.encode(text, convert_to_tensor=False)
        return _normalize(embedding)
    except Exception as e:
        print(f"Error generating text embedding: {e}")
        raise


def get_combined_embedding(
    base_text: str,
    positive_texts: list[str] | None = None,
    negative_texts: list[str] | None = None,
    positive_weight: float = 1.0,
    negative_weight: float = 1.0,
) -> list[float]:
    """
    Generate a combined embedding with positive/negative adjustments
    Used for advanced search with refinements
    """
    import numpy as np

    # Get base embedding
    base_emb = np.array(get_text_embedding(base_text))

    # Add positive texts
    if positive_texts:
        for text in positive_texts:
            pos_emb = np.array(get_text_embedding(text))
            base_emb = base_emb + (pos_emb * positive_weight)

    # Subtract negative texts
    if negative_texts:
        for text in negative_texts:
            neg_emb = np.array(get_text_embedding(text))
            base_emb = base_emb - (neg_emb * negative_weight)

    # Normalize
    norm = np.linalg.norm(base_emb)
    if norm > 0:
        base_emb = base_emb / norm

    return base_emb.tolist()


def cosine_similarity(emb1: list[float], emb2: list[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    import numpy as np

    a = np.array(emb1)
    b = np.array(emb2)

    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Safe mode negative texts for content filtering
SAFE_MODE_TEXTS = ["nsfw", "nude", "naked", "porn", "sex", "explicit", "violence", "gore", "blood", "death"]

SAFE_MODE_WEIGHTS = {
    "low": 0.6,
    "lowmid": 0.9,
    "mid": 1.2,
    "midhigh": 1.5,
    "high": 1.8,
    "veryhigh": 2.2,
    "extreme": 2.5,
}


def get_safe_search_embedding(text: str, safe_mode_level: str = "mid") -> list[float]:
    """Generate embedding with safe mode filtering"""
    weight = SAFE_MODE_WEIGHTS.get(safe_mode_level.lower(), 1.2)

    return get_combined_embedding(
        base_text=text,
        negative_texts=SAFE_MODE_TEXTS,
        negative_weight=weight,
    )


if __name__ == "__main__":
    # Test embeddings
    print("Testing embeddings module...")
    print(f"Status: {get_model_status()}")

    # Test text embedding (this will load the model)
    text_emb = get_text_embedding("a blue shirt on a website")
    print(f"Text embedding shape: {len(text_emb)}")
    print(f"Status after load: {get_model_status()}")

    # Test unload
    print("Testing unload...")
    unload_model()
    print(f"Status after unload: {get_model_status()}")

    print("Done!")
