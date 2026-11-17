import os
from sentence_transformers import SentenceTransformer

# Centralized embedding model
MODEL_NAME = "all-MiniLM-L6-v2"

# Prefer local cached files if available to operate reliably in offline/sandboxed environments
try:
    model = SentenceTransformer(MODEL_NAME, local_files_only=True)
except Exception:
    model = SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> list[float]:
    """
    Generate an embeddings vector for a single text chunk.

    Args:
        text : Text to convert into an embeddings.
    Returns:
        Embeddings vector as the list of floats.
    """
    if not text:
        raise ValueError("Text cannot be empty.")

    embeddings = model.encode(text)
    return embeddings.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate the embeddings for the multiple text chunks.

    Args:
        texts : List of text chunks.
    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []

    embeddings = model.encode(texts)
    return embeddings.tolist()
