from __future__ import annotations

import logging
from typing import Any
from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.rag.embeddings.embedding_model import generate_embedding
from src.rag.vector_db.qdrant_client import client, COLLECTION_NAME

logger = logging.getLogger("rag.retriever")


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    doc_type: str | None = None,
    station: str | None = None,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant document chunks from Qdrant with optional metadata filtering.

    Returns source-aware results containing:
    document name, page number, chunk ID, similarity score, canonical text,
    and backwards-compatible content.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    query_vector = generate_embedding(query.strip())

    must_conditions = []
    if doc_type:
        must_conditions.append(
            FieldCondition(key="doc_type", match=MatchValue(value=doc_type))
        )
    if station:
        must_conditions.append(
            FieldCondition(key="stations", match=MatchValue(value=station.lower()))
        )

    query_filter = Filter(must=must_conditions) if must_conditions else None

    # Fetch slightly more if filtering by min_score
    fetch_limit = min(top_k * 2 if min_score > 0 else top_k, 100)

    try:
        search_results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=fetch_limit,
            with_payload=True,
            with_vectors=False,
        ).points

        # Fallback to general semantic retrieval if station filter yields no results
        if not search_results and query_filter is not None:
            search_results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=fetch_limit,
                with_payload=True,
                with_vectors=False,
            ).points
    except Exception as exc:
        logger.exception("Qdrant query failed: %s", exc)
        return []

    results = []
    for result in search_results:
        score = float(result.score)
        if score < min_score:
            continue

        payload = result.payload or {}
        text_content = payload.get("text", "")
        doc_name = payload.get("document_name") or payload.get("source", "")
        chunk_id = payload.get("chunk_id") or payload.get("id", str(result.id))

        results.append({
            "score": round(score, 4),
            "document_id": payload.get("document_id") or doc_name.replace(".pdf", ""),
            "document_name": doc_name,
            "source": doc_name,
            "chunk_id": chunk_id,
            "id": chunk_id,
            "page": payload.get("page"),
            "text": text_content,
            "content": text_content,
            "char_count": payload.get("char_count", len(text_content)),
            "doc_type": payload.get("doc_type", "research"),
            "source_category": payload.get("source_category", "general"),
            "report_date": payload.get("report_date"),
            "publication_date": payload.get("publication_date"),
            "stations": payload.get("stations", []),
        })

        if len(results) >= top_k:
            break

    return results
