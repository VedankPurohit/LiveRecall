"""
LiveRecall Text Chunking

Splits OCR text into chunks for semantic search.
Uses dual chunking strategy: small (512 tokens) and large (2048 tokens).

Small chunks: Precise matching, good for short specific queries
Large chunks: Better context, good for conceptual queries

Both chunk sizes are searched and combined using RRF (Reciprocal Rank Fusion).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ChunkInfo:
    """A single text chunk with position info"""

    text: str
    start_char: int
    end_char: int
    index: int


@dataclass
class ChunkedText:
    """Result of dual-size chunking"""

    small: list[ChunkInfo]
    large: list[ChunkInfo]


# Default chunk settings
DEFAULT_SMALL_SIZE = 512  # tokens (~2000 chars)
DEFAULT_SMALL_OVERLAP = 50  # tokens (~200 chars)
DEFAULT_LARGE_SIZE = 2048  # tokens (~8000 chars)
DEFAULT_LARGE_OVERLAP = 200  # tokens (~800 chars)

# Approximate chars per token (for rough estimation)
CHARS_PER_TOKEN = 4

# Minimum chunk size (skip tiny chunks)
MIN_CHUNK_CHARS = 50


def estimate_tokens(text: str) -> int:
    """Estimate number of tokens in text (rough approximation)"""
    return len(text) // CHARS_PER_TOKEN


def create_chunks(
    text: str,
    chunk_size: int = DEFAULT_SMALL_SIZE,
    overlap: int = DEFAULT_SMALL_OVERLAP,
    min_chunk_chars: int = MIN_CHUNK_CHARS,
) -> list[ChunkInfo]:
    """
    Create chunks from text with overlap.

    Uses paragraph and sentence boundaries when possible for cleaner splits.

    Args:
        text: The text to chunk
        chunk_size: Target chunk size in tokens
        overlap: Overlap between chunks in tokens
        min_chunk_chars: Minimum characters for a chunk (skip smaller)

    Returns:
        List of ChunkInfo with text and position info
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # Convert token sizes to character sizes (rough)
    chunk_chars = chunk_size * CHARS_PER_TOKEN
    overlap_chars = overlap * CHARS_PER_TOKEN

    # If text is small enough, return as single chunk
    if len(text) <= chunk_chars:
        return [
            ChunkInfo(
                text=text,
                start_char=0,
                end_char=len(text),
                index=0,
            )
        ]

    chunks: list[ChunkInfo] = []

    # Split into paragraphs first (preserve structure)
    paragraphs = re.split(r"\n\n+", text)

    current_chunk = ""
    current_start = 0
    char_position = 0
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            char_position += 2  # Account for newlines
            continue

        # If adding this paragraph exceeds chunk size
        if len(current_chunk) + len(para) + 2 > chunk_chars:
            # Save current chunk if it has content
            if current_chunk and len(current_chunk) >= min_chunk_chars:
                chunks.append(
                    ChunkInfo(
                        text=current_chunk.strip(),
                        start_char=current_start,
                        end_char=current_start + len(current_chunk),
                        index=chunk_index,
                    )
                )
                chunk_index += 1

                # Start new chunk with overlap from previous
                if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                    # Get last overlap_chars from current chunk
                    overlap_text = current_chunk[-overlap_chars:]
                    # Try to start at a word boundary
                    space_idx = overlap_text.find(" ")
                    if space_idx > 0:
                        overlap_text = overlap_text[space_idx + 1 :]
                    current_chunk = overlap_text + "\n\n"
                    current_start = char_position - len(overlap_text)
                else:
                    current_chunk = ""
                    current_start = char_position

            # Handle oversized paragraph by splitting on sentences
            if len(para) > chunk_chars:
                para_chunks = _split_paragraph(
                    para, chunk_chars, overlap_chars, min_chunk_chars, char_position, chunk_index
                )
                for pc in para_chunks:
                    chunks.append(pc)
                    chunk_index += 1

                # Reset current chunk
                current_chunk = ""
                current_start = char_position + len(para)
            else:
                current_chunk = para
                current_start = char_position
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
                current_start = char_position

        char_position += len(para) + 2

    # Don't forget the last chunk
    if current_chunk and len(current_chunk) >= min_chunk_chars:
        chunks.append(
            ChunkInfo(
                text=current_chunk.strip(),
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                index=chunk_index,
            )
        )

    return chunks


def _split_paragraph(
    para: str,
    chunk_chars: int,
    overlap_chars: int,
    min_chunk_chars: int,
    base_position: int,
    base_index: int,
) -> list[ChunkInfo]:
    """Split a large paragraph by sentences"""
    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", para)

    chunks: list[ChunkInfo] = []
    current_chunk = ""
    current_start = base_position
    chunk_index = base_index
    char_offset = 0

    for sentence in sentences:
        if not sentence.strip():
            continue

        if len(current_chunk) + len(sentence) + 1 > chunk_chars:
            # Save current chunk
            if current_chunk and len(current_chunk) >= min_chunk_chars:
                chunks.append(
                    ChunkInfo(
                        text=current_chunk.strip(),
                        start_char=current_start,
                        end_char=current_start + len(current_chunk),
                        index=chunk_index,
                    )
                )
                chunk_index += 1

            # Start new chunk with overlap
            if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                overlap_text = current_chunk[-overlap_chars:]
                space_idx = overlap_text.find(" ")
                if space_idx > 0:
                    overlap_text = overlap_text[space_idx + 1 :]
                current_chunk = overlap_text + " " + sentence
                current_start = base_position + char_offset - len(overlap_text)
            else:
                current_chunk = sentence
                current_start = base_position + char_offset
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
                current_start = base_position + char_offset

        char_offset += len(sentence) + 1

    # Last chunk
    if current_chunk and len(current_chunk) >= min_chunk_chars:
        chunks.append(
            ChunkInfo(
                text=current_chunk.strip(),
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                index=chunk_index,
            )
        )

    return chunks


def chunk_ocr_text(
    full_text: str,
    small_size: int = DEFAULT_SMALL_SIZE,
    small_overlap: int = DEFAULT_SMALL_OVERLAP,
    large_size: int = DEFAULT_LARGE_SIZE,
    large_overlap: int = DEFAULT_LARGE_OVERLAP,
) -> ChunkedText:
    """
    Create dual-size chunks from OCR text.

    Args:
        full_text: The full OCR text to chunk
        small_size: Size for small chunks (tokens)
        small_overlap: Overlap for small chunks (tokens)
        large_size: Size for large chunks (tokens)
        large_overlap: Overlap for large chunks (tokens)

    Returns:
        ChunkedText with both small and large chunk lists
    """
    small_chunks = create_chunks(full_text, small_size, small_overlap)
    large_chunks = create_chunks(full_text, large_size, large_overlap)

    return ChunkedText(small=small_chunks, large=large_chunks)


def get_chunk_count(text: str, chunk_size: int = DEFAULT_SMALL_SIZE) -> int:
    """Estimate number of chunks that will be created"""
    if not text:
        return 0

    text_chars = len(text.strip())
    chunk_chars = chunk_size * CHARS_PER_TOKEN

    if text_chars <= chunk_chars:
        return 1

    # Rough estimate accounting for overlap
    return max(1, (text_chars // chunk_chars) + 1)


if __name__ == "__main__":
    # Test chunking
    test_text = """
    This is the first paragraph of test text. It contains multiple sentences.
    The sentences are meant to test the chunking functionality.

    This is the second paragraph. It's separate from the first one.
    We want to make sure paragraph boundaries are respected.

    Here is a third paragraph with more content. The chunking algorithm
    should handle this text and split it appropriately based on the
    configured chunk size and overlap settings.

    Finally, this is the last paragraph. It wraps up our test text
    and provides enough content for meaningful chunk testing.
    """

    print("Testing chunking module...")
    print(f"Input text length: {len(test_text)} chars")
    print(f"Estimated tokens: {estimate_tokens(test_text)}")

    # Test dual chunking
    result = chunk_ocr_text(test_text)

    print(f"\nSmall chunks ({len(result.small)}):")
    for chunk in result.small:
        print(f"  [{chunk.index}] chars {chunk.start_char}-{chunk.end_char}: {chunk.text[:50]}...")

    print(f"\nLarge chunks ({len(result.large)}):")
    for chunk in result.large:
        print(f"  [{chunk.index}] chars {chunk.start_char}-{chunk.end_char}: {chunk.text[:50]}...")

    print("\nDone!")
