from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query

from src.rag.schemas import (
    RetrievedChunk,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGIngestRequest,
)
from src.rag.retrieval.retriever import retrieve_chunks
from src.rag.ingestion.auto_ingest import (
    ingest_pdf_document,
    scan_and_ingest_directory,
    get_db_connection,
)
from src.rag.vector_db.qdrant_client import client, COLLECTION_NAME, QDRANT_PATH

logger = logging.getLogger("rag.api")

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/health")
def rag_health():
    """Check RAG system health, embedding readiness, and Qdrant storage."""
    qdrant_ok = False
    collection_points = 0
    error_msg = None

    try:
        col_info = client.get_collection(COLLECTION_NAME)
        collection_points = col_info.points_count
        qdrant_ok = True
    except Exception as exc:
        error_msg = str(exc)

    return {
        "status": "ok" if qdrant_ok else "degraded",
        "collection": COLLECTION_NAME,
        "collection_ready": qdrant_ok,
        "total_points": collection_points,
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "error": error_msg,
    }


@router.get("/stats")
def rag_stats():
    """Return comprehensive indexing statistics and ingestion history."""
    try:
        col_info = client.get_collection(COLLECTION_NAME)
        points_count = col_info.points_count
    except Exception as exc:
        raise HTTPException(502, detail=f"Failed to query Qdrant collection: {exc}")

    # Query ingestion history
    recent_ingestions = []
    try:
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT document_id, document_name, doc_type, source_category,
                   page_count, points_indexed, status, ingested_at
            FROM ingestion_log
            ORDER BY id DESC LIMIT 50
            """
        ).fetchall()
        recent_ingestions = [dict(row) for row in rows]
        conn.close()
    except Exception as exc:
        logger.warning("Could not read ingestion history: %s", exc)

    return {
        "collection_name": COLLECTION_NAME,
        "total_points": points_count,
        "storage_path": str(QDRANT_PATH),
        "recent_ingestions_count": len(recent_ingestions),
        "recent_ingestions": recent_ingestions,
    }


@router.post("/search", response_model=RAGSearchResponse)
def rag_search(request: RAGSearchRequest):
    """Semantic vector search across climate documents and weather reports."""
    try:
        raw_results = retrieve_chunks(
            query=request.query,
            top_k=request.top_k,
            doc_type=request.doc_type,
            station=request.station,
            min_score=request.min_score,
        )
    except Exception as exc:
        logger.exception("RAG search failed for query '%s'", request.query)
        raise HTTPException(500, detail=f"Search failed: {exc}") from exc

    chunks = [RetrievedChunk(**res) for res in raw_results]

    return RAGSearchResponse(
        query=request.query,
        total=len(chunks),
        results=chunks,
    )


@router.post("/ingest")
def rag_ingest(request: RAGIngestRequest):
    """Idempotently ingest a PDF into Qdrant."""
    path = Path(request.file_path)
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        raise HTTPException(404, detail=f"File not found: {request.file_path}")

    try:
        result = ingest_pdf_document(
            pdf_path=path,
            doc_type=request.doc_type,
            source_category=request.source_category,
            force=request.force,
        )
        return result
    except Exception as exc:
        logger.exception("Ingestion failed for %s", request.file_path)
        raise HTTPException(500, detail=f"Ingestion failed: {exc}") from exc


@router.post("/sync-reports")
def rag_sync_reports(
    reports_dir: str | None = Query(default=None, description="Directory path to scan for reports"),
    force: bool = Query(default=False, description="Force re-indexing"),
):
    """Scan the weather reports directory and ingest all new/modified reports."""
    target_dir = reports_dir or str(Path.cwd() / "weather_pipeline" / "data" / "reports")
    try:
        results = scan_and_ingest_directory(
            directory_path=target_dir,
            doc_type="weather_report",
            source_category="weather_reports",
            force=force,
        )
        return {
            "status": "complete",
            "directory": target_dir,
            "processed_count": len(results),
            "results": results,
        }
    except Exception as exc:
        logger.exception("Sync reports failed: %s", exc)
        raise HTTPException(500, detail=f"Sync failed: {exc}") from exc


app = FastAPI(title="AtmoSync RAG API", version="2.0.0")
app.include_router(router)
