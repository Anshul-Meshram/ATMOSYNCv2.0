import datetime
import uuid
from pathlib import Path
from typing import Any

from qdrant_client.models import PointStruct

from src.rag.embeddings.embedding_model import generate_embeddings
from src.rag.vector_db.qdrant_client import client, COLLECTION_NAME


def index_chunks(
    chunks: list[dict],
    document_name: str,
    doc_type: str = "weather_report",
    source_category: str | None = None,
    report_date: str | None = None,
    publication_date: str | None = None,
    stations: list[str] | None = None,
    doc_hash: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> int:
    """
    Idempotently index document chunks into Qdrant collection `climate_documents`.

    Point IDs are deterministically derived from (document_id, chunk_id),
    ensuring that re-indexing a document overwrites points in place rather
    than duplicating them.
    """
    if not chunks:
        return 0

    document_id = Path(document_name).stem
    ingested_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    valid_chunks = []
    texts_to_embed = []
    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if not text:
            continue
        valid_chunks.append(chunk)
        texts_to_embed.append(text)

    if not valid_chunks:
        return 0

    # Batch embedding generation for efficiency
    vectors = generate_embeddings(texts_to_embed)

    points = []
    for chunk, text, vector in zip(valid_chunks, texts_to_embed, vectors):
        chunk_id = f"{document_id}_{chunk['chunk_id']}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

        payload = {
            "document_id": document_id,
            "document_name": document_name,
            "source": document_name,
            "chunk_id": chunk_id,
            "page": chunk.get("page"),
            "text": text,
            "content": text,  # Compatibility adapter for systems expecting 'content'
            "char_count": len(text),
            "doc_type": doc_type,
            "source_category": source_category or doc_type,
            "report_date": report_date,
            "publication_date": publication_date or report_date,
            "stations": stations or [],
            "doc_hash": doc_hash or "",
            "ingested_at": ingested_at,
        }
        if extra_metadata:
            payload.update(extra_metadata)

        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

    return len(points)
