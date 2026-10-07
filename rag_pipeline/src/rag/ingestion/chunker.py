"""
Document chunking module for the AtmoSync RAG pipeline.

This module converts cleaned page-level text into smaller,
retrieval-friendly chunks while preserving page information.
"""

import re


# Chunk configuration
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 300


def normalize_paragraphs(text: str) -> list[str]:
    """
    Split text into meaningful paragraphs.

    Multiple blank lines are treated as paragraph boundaries.
    """

    paragraphs = re.split(r"\n\s*\n", text)

    return [
        paragraph.strip()
        for paragraph in paragraphs
        if paragraph.strip()
    ]


def create_chunks_from_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into chunks while attempting to preserve
    paragraph boundaries.

    Args:
        text: Cleaned page text.
        chunk_size: Target maximum size of a chunk.
        overlap: Number of characters repeated between chunks.

    Returns:
        List of text chunks.
    """

    if not text or not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    paragraphs = normalize_paragraphs(text)

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:

        # If adding the paragraph still fits,
        # keep it in the current chunk.
        if len(current_chunk) + len(paragraph) + 2 <= chunk_size:

            if current_chunk:
                current_chunk += "\n\n"

            current_chunk += paragraph
            continue

        # Save current chunk before starting another.
        if current_chunk:
            chunks.append(current_chunk.strip())

        # If paragraph itself is larger than chunk_size,
        # split it safely.
        if len(paragraph) > chunk_size:

            start = 0

            while start < len(paragraph):

                end = start + chunk_size

                chunk = paragraph[start:end].strip()

                if chunk:
                    chunks.append(chunk)

                start = end - overlap

            current_chunk = ""
            continue

        # Start a new chunk with the paragraph.
        current_chunk = paragraph

    # Add remaining text.
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Convert page-level PDF text into retrieval-ready chunks.

    Args:
        pages: Output from the PDF ingestion pipeline.

    Returns:
        List of chunks containing chunk ID, page number,
        text, and character count.
    """

    all_chunks = []

    for page_data in pages:

        page_number = page_data["page"]
        text = page_data["text"]

        page_chunks = create_chunks_from_text(text)

        for chunk_number, chunk_text in enumerate(
            page_chunks,
            start=1,
        ):

            all_chunks.append(
                {
                    "chunk_id": (
                        f"page_{page_number}_chunk_{chunk_number}"
                    ),
                    "page": page_number,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                }
            )

    return all_chunks


if __name__ == "__main__":

    sample_text = """
    Climate change is affecting temperature patterns across Canada.

    Extreme heat events are becoming an important area of climate
    research and monitoring.

    Changes in precipitation patterns can also affect drought and
    flooding conditions.
    """

    chunks = create_chunks_from_text(sample_text)

    print("Chunking test completed successfully.")
    print(f"Total chunks: {len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\n--- Chunk {index} ---")
        print(chunk)