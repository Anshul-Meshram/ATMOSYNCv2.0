
import uuid
from pathlib import Path

from qdrant_client.models import PointStruct

from src.rag.embeddings.embedding_model import generate_embedding
from src.rag.vector_db.qdrant_client import client, COLLECTION_NAME


def index_chunks(
    chunks: list[dict],
    document_name: str
) -> int:

    points = []

    document_id = Path(document_name).stem

    for chunk in chunks:

        text = chunk["text"].strip()

        if not text:
            continue

        vector = generate_embedding(text)

        chunk_id = (
            f"{document_id}_{chunk['chunk_id']}"
        )

        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                chunk_id
            )
        )

        point = PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "document_id": document_id,
                "document_name": document_name,
                "chunk_id": chunk_id,
                "page": chunk["page"],
                "text": text,
                "char_count": len(text),
            },
        )

        points.append(point)

    if points:

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

    return len(points)