
from src.rag.embeddings.embedding_model import generate_embedding
from src.rag.vector_db.qdrant_client import client, COLLECTION_NAME


def retrieve_chunks(query: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve relevant document chunks from Qdrant.

    Returns source-aware results containing:
    document name, page number, chunk ID,
    similarity score, and text.
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    query_vector = generate_embedding(query.strip())

    search_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    ).points

    results = []

    for result in search_results:

        payload = result.payload or {}

        results.append({
            "score": result.score,
            "document_id": payload.get("document_id"),
            "document_name": payload.get("document_name"),
            "chunk_id": payload.get("chunk_id"),
            "page": payload.get("page"),
            "text": payload.get("text", ""),
            "char_count": payload.get("char_count"),
        })

    return results