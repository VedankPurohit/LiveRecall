"""
LiveRecall Text Embeddings
Specialized text embedding model for OCR semantic search

Separate from CLIP to optimize for text-to-text similarity.
Uses lazy loading with auto-unload for memory management.

=============================================================================
TEXT EMBEDDING MODEL OPTIONS
=============================================================================

Current: BAAI/bge-small-en-v1.5 (384-dim, 130MB, MTEB 62.2)
  - Great balance of accuracy and speed
  - Optimized for semantic text similarity

Lighter alternatives (if memory constrained):
  - all-MiniLM-L6-v2: 384-dim, 80MB, MTEB 56.3
  - thenlper/gte-small: 384-dim, 70MB

Higher accuracy alternatives:
  - BAAI/bge-base-en-v1.5: 768-dim, 440MB, MTEB 63.5
  - all-mpnet-base-v2: 768-dim, 420MB
  - nomic-embed-text-v1.5: 768-dim, 550MB

To switch model:
  1. Update config: config.text_embeddings.model = "BAAI/bge-base-en-v1.5"
  2. Note: Changing dimensions requires recreating vector tables!
  3. Run: text_embedding_service.recompute_all()
=============================================================================
"""

from __future__ import annotations

import os
import threading
import time
import warnings

# Suppress HuggingFace warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", message=".*use_fast.*")
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np  # noqa: E402
import torch  # noqa: E402

# Lazy loading state
_model = None
_device: str | None = None
_last_used: float = 0
_auto_unload_timer: threading.Timer | None = None
_lock = threading.Lock()

# Configuration
AUTO_UNLOAD_SECONDS = 300  # 5 minutes of idle before unloading
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384  # Dimension for bge-small

# Model name (can be changed via config)
_current_model_name = DEFAULT_MODEL


def _get_device() -> str:
    """Get the best available device"""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon
    return "cpu"


def _load_model(model_name: str | None = None):
    """Load the text embedding model (only called once)"""
    global _model, _device, _last_used, _current_model_name

    if model_name is None:
        model_name = _current_model_name

    with _lock:
        if _model is not None:
            _last_used = time.time()
            return _model

        print(f"Loading text embedding model: {model_name}...")

        from sentence_transformers import SentenceTransformer

        _device = _get_device()
        print(f"Using device: {_device}")

        try:
            _model = SentenceTransformer(model_name, device=_device)
            _current_model_name = model_name
        except Exception as e:
            print(f"Error loading on {_device}, falling back to CPU: {e}")
            _device = "cpu"
            _model = SentenceTransformer(model_name, device="cpu")
            _current_model_name = model_name

        _last_used = time.time()
        print(f"Text embedding model loaded successfully (dim={_model.get_sentence_embedding_dimension()})")

        # Start auto-unload timer
        _schedule_auto_unload()

        return _model


def _schedule_auto_unload():
    """Schedule auto-unload after idle timeout"""
    global _auto_unload_timer

    # Cancel existing timer
    if _auto_unload_timer is not None:
        _auto_unload_timer.cancel()

    if AUTO_UNLOAD_SECONDS > 0:
        # Schedule new timer
        _auto_unload_timer = threading.Timer(AUTO_UNLOAD_SECONDS, _check_and_unload)
        _auto_unload_timer.daemon = True
        _auto_unload_timer.start()


def _check_and_unload():
    """Check if model should be unloaded due to inactivity"""
    global _last_used

    idle_time = time.time() - _last_used
    if idle_time >= AUTO_UNLOAD_SECONDS:
        print(f"Text embedding model idle for {idle_time:.0f}s, unloading...")
        unload_model()
    else:
        # Reschedule check
        _schedule_auto_unload()


def unload_model():
    """Explicitly unload the text embedding model to free memory"""
    global _model, _device, _auto_unload_timer

    with _lock:
        if _model is None:
            return

        print("Unloading text embedding model...")

        # Cancel auto-unload timer
        if _auto_unload_timer is not None:
            _auto_unload_timer.cancel()
            _auto_unload_timer = None

        # Delete model
        del _model
        _model = None

        # Clear GPU memory if applicable
        if _device == "cuda":
            torch.cuda.empty_cache()

        _device = None
        print("Text embedding model unloaded")


def is_loaded() -> bool:
    """Check if the model is currently loaded"""
    return _model is not None


def is_downloaded() -> bool:
    """Check if the text embedding model is downloaded in HuggingFace cache"""
    try:
        from huggingface_hub import try_to_load_from_cache

        # Check for the sentence-transformers config file
        result = try_to_load_from_cache(_current_model_name, "config_sentence_transformers.json")
        if result is not None:
            return True
        # Fallback: some models use config.json
        result = try_to_load_from_cache(_current_model_name, "config.json")
        return result is not None
    except Exception:
        return False


def get_model_status() -> dict:
    """Get detailed model status"""
    return {
        "loaded": _model is not None,
        "downloaded": is_downloaded(),
        "model_name": _current_model_name,
        "device": _device,
        "last_used": _last_used,
        "idle_seconds": time.time() - _last_used if _last_used > 0 else 0,
        "auto_unload_seconds": AUTO_UNLOAD_SECONDS,
        "embedding_dim": EMBEDDING_DIM,
    }


def set_auto_unload_timeout(seconds: int):
    """Set the auto-unload timeout (0 to disable)"""
    global AUTO_UNLOAD_SECONDS
    AUTO_UNLOAD_SECONDS = seconds
    if seconds > 0 and _model is not None:
        _schedule_auto_unload()


def _normalize(embedding: np.ndarray) -> list[float]:
    """Normalize embedding to unit length for cosine similarity"""
    arr = np.array(embedding)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


def get_text_embedding(text: str) -> list[float]:
    """
    Generate normalized embedding for a text string.

    Args:
        text: The text to encode

    Returns:
        Normalized embedding as list of floats (384-dim for bge-small)
    """
    global _last_used

    model = _load_model()
    _last_used = time.time()

    try:
        # BGE models work best with instruction prefix for queries
        # But for storing document chunks, we use text as-is
        embedding = model.encode(text, convert_to_tensor=False)
        return _normalize(embedding)
    except Exception as e:
        print(f"Error generating text embedding: {e}")
        raise


def get_query_embedding(query: str) -> list[float]:
    """
    Generate embedding for a search query.

    For BGE models, queries should be prefixed with "Represent this sentence:"
    for optimal retrieval performance.

    Args:
        query: The search query text

    Returns:
        Normalized embedding as list of floats
    """
    global _last_used

    model = _load_model()
    _last_used = time.time()

    try:
        # BGE instruction for query encoding
        instruction = "Represent this sentence for searching relevant passages: "
        embedding = model.encode(instruction + query, convert_to_tensor=False)
        return _normalize(embedding)
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        raise


def get_batch_embeddings(texts: list[str], show_progress: bool = False) -> list[list[float]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of texts to encode
        show_progress: Whether to show progress bar

    Returns:
        List of normalized embeddings
    """
    global _last_used

    if not texts:
        return []

    model = _load_model()
    _last_used = time.time()

    try:
        embeddings = model.encode(texts, convert_to_tensor=False, batch_size=32, show_progress_bar=show_progress)

        # Normalize all embeddings
        result = []
        for emb in embeddings:
            result.append(_normalize(emb))

        return result
    except Exception as e:
        print(f"Error generating batch embeddings: {e}")
        raise


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings produced by the current model"""
    if _model is not None:
        return _model.get_sentence_embedding_dimension()
    return EMBEDDING_DIM


def cosine_similarity(emb1: list[float], emb2: list[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    a = np.array(emb1)
    b = np.array(emb2)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# =============================================================================
# Service wrapper for consistent interface with other services
# =============================================================================


class TextEmbeddingService:
    """Wrapper class for text embedding functions to provide service-like interface.

    This wrapper provides the same functionality as the module functions
    but in a class-based API for consistency with other services.
    """

    def get_text_embedding(self, text: str) -> list[float]:
        """Generate embedding for document text"""
        return get_text_embedding(text)

    def get_query_embedding(self, query: str) -> list[float]:
        """Generate embedding for search query"""
        return get_query_embedding(query)

    def get_batch_embeddings(self, texts: list[str], show_progress: bool = False) -> list[list[float]]:
        """Generate embeddings for multiple texts"""
        return get_batch_embeddings(texts, show_progress)

    def get_model_status(self) -> dict:
        """Get model status"""
        return get_model_status()

    def unload_model(self):
        """Unload the model"""
        unload_model()

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return is_loaded()

    def is_downloaded(self) -> bool:
        """Check if model is downloaded"""
        return is_downloaded()


# Global service instance
text_embedding_service = TextEmbeddingService()


if __name__ == "__main__":
    # Test text embeddings module
    print("Testing text embeddings module...")
    print(f"Status: {get_model_status()}")

    # Test text embedding (this will load the model)
    text_emb = get_text_embedding("This is a test sentence for embedding")
    print(f"Text embedding shape: {len(text_emb)}")
    print(f"Status after load: {get_model_status()}")

    # Test query embedding
    query_emb = get_query_embedding("search for test")
    print(f"Query embedding shape: {len(query_emb)}")

    # Test batch embeddings
    batch_emb = get_batch_embeddings(["Hello world", "How are you?", "Test batch"])
    print(f"Batch embeddings: {len(batch_emb)} embeddings")

    # Test similarity
    sim = cosine_similarity(text_emb, query_emb)
    print(f"Similarity between text and query: {sim:.4f}")

    # Test unload
    print("Testing unload...")
    unload_model()
    print(f"Status after unload: {get_model_status()}")

    print("Done!")
