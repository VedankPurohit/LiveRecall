"""
LiveRecall Embeddings
Lazy-loaded CLIP model for generating image and text embeddings
"""
from typing import Optional
import torch
from PIL import Image

# Lazy loading - model only loads when first used
_model = None
_device = None


def _get_device() -> str:
    """Get the best available device"""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon
    return "cpu"


def _load_model():
    """Load the CLIP model (only called once)"""
    global _model, _device

    if _model is not None:
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

    print("CLIP model loaded successfully")
    return _model


def is_loaded() -> bool:
    """Check if the model is loaded"""
    return _model is not None


def get_image_embedding(image_path: str) -> list[float]:
    """Generate embedding for an image file"""
    model = _load_model()

    try:
        image = Image.open(image_path)
        embedding = model.encode(image, convert_to_tensor=False)
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating image embedding: {e}")
        raise


def get_text_embedding(text: str) -> list[float]:
    """Generate embedding for a text query"""
    model = _load_model()

    try:
        embedding = model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating text embedding: {e}")
        raise


def get_combined_embedding(
    base_text: str,
    positive_texts: Optional[list[str]] = None,
    negative_texts: Optional[list[str]] = None,
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
SAFE_MODE_TEXTS = [
    "nsfw", "nude", "naked", "porn", "sex", "explicit",
    "violence", "gore", "blood", "death"
]

SAFE_MODE_WEIGHTS = {
    "low": 0.6,
    "lowmid": 0.9,
    "mid": 1.2,
    "midhigh": 1.5,
    "high": 1.8,
    "veryhigh": 2.2,
    "extreme": 2.5,
}


def get_safe_search_embedding(
    text: str,
    safe_mode_level: str = "mid"
) -> list[float]:
    """Generate embedding with safe mode filtering"""
    weight = SAFE_MODE_WEIGHTS.get(safe_mode_level, 1.2)

    return get_combined_embedding(
        base_text=text,
        negative_texts=SAFE_MODE_TEXTS,
        negative_weight=weight,
    )


if __name__ == "__main__":
    # Test embeddings
    print("Testing embeddings module...")

    # Test text embedding
    text_emb = get_text_embedding("a blue shirt on a website")
    print(f"Text embedding shape: {len(text_emb)}")

    # Test image embedding (if you have a test image)
    # img_emb = get_image_embedding("/path/to/test.jpg")
    # print(f"Image embedding shape: {len(img_emb)}")

    print("Done!")
