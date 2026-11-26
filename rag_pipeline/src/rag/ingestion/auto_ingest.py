from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.rag.ingestion.pdf_loader import extract_pages_from_pdf, check_pdf_text
from src.rag.ingestion.text_cleaner import clean_text
from src.rag.ingestion.chunker import chunk_pages
from src.rag.vector_db.indexer import index_chunks

logger = logging.getLogger("rag.ingestion")

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
DB_PATH = DATA_DIR / "ingestion_history.db"


def get_db_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                document_id TEXT NOT NULL,
                document_name TEXT NOT NULL,
                doc_hash TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                source_category TEXT,
                page_count INTEGER,
                chunk_count INTEGER,
                points_indexed INTEGER,
                status TEXT NOT NULL,
                error_message TEXT,
                ingested_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ingestion_hash ON ingestion_log (doc_hash)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ingestion_doc_id ON ingestion_log (document_id)
        """)
    return conn


def compute_file_hash(file_path: Path | str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_already_ingested(file_path: Path | str, doc_hash: str) -> bool:
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT id FROM ingestion_log WHERE doc_hash = ? AND status = 'done'",
            (doc_hash,),
        ).fetchone()
        conn.close()
        return row is not None
    except Exception as exc:
        logger.warning("Could not check ingestion status: %s", exc)
        return False


def log_ingestion_result(
    file_path: str,
    document_id: str,
    document_name: str,
    doc_hash: str,
    doc_type: str,
    source_category: str | None,
    page_count: int,
    chunk_count: int,
    points_indexed: int,
    status: str,
    error_message: str | None = None,
) -> None:
    try:
        conn = get_db_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO ingestion_log (
                    file_path, document_id, document_name, doc_hash,
                    doc_type, source_category, page_count, chunk_count,
                    points_indexed, status, error_message, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_path,
                    document_id,
                    document_name,
                    doc_hash,
                    doc_type,
                    source_category,
                    page_count,
                    chunk_count,
                    points_indexed,
                    status,
                    error_message,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        conn.close()
    except Exception as exc:
        logger.warning("Failed to record ingestion log: %s", exc)


def extract_report_metadata(file_path: Path, text: str) -> dict[str, Any]:
    """Extract report dates and station mentions from filename or text."""
    meta: dict[str, Any] = {}
    name = file_path.name

    # Try pattern weather_report_YYYY-MM-DD_YYYY-MM-DD or weather_report_YYYY-MM-DD
    match = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})", name)
    if match:
        meta["report_start_date"] = match.group(1)
        meta["report_end_date"] = match.group(2)
        meta["report_date"] = match.group(1)
    else:
        match_single = re.search(r"(\d{4}-\d{2}-\d{2})", name)
        if match_single:
            meta["report_date"] = match_single.group(1)

    # Check companion .meta.json if present
    meta_json_path = file_path.with_suffix(".pdf.meta.json")
    if not meta_json_path.exists():
        meta_json_path = file_path.parent / f"{file_path.name}.meta.json"
    if meta_json_path.exists():
        try:
            with open(meta_json_path, "r", encoding="utf-8") as f:
                saved_meta = json.load(f)
                meta.update(saved_meta)
        except Exception:
            pass

    return meta


def ingest_pdf_document(
    pdf_path: str | Path,
    doc_type: str = "weather_report",
    source_category: str | None = None,
    force: bool = False,
    retries: int = 2,
) -> dict[str, Any]:
    """
    Complete idempotent PDF ingestion pipeline:
    1. Verify file and calculate SHA-256 hash.
    2. Check if already ingested with matching hash.
    3. Extract and validate text across pages.
    4. Clean, normalize, and chunk text.
    5. Generate embeddings and index deterministically in Qdrant.
    6. Record ingestion status in SQLite audit log.
    """
    path = Path(pdf_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path.suffix}")

    doc_name = path.name
    doc_id = path.stem
    doc_hash = compute_file_hash(path)

    if not force and is_already_ingested(str(path), doc_hash):
        logger.info("PDF %s already indexed (hash %s), skipping.", doc_name, doc_hash[:8])
        return {
            "status": "already_indexed",
            "document_id": doc_id,
            "document_name": doc_name,
            "doc_hash": doc_hash,
            "points_indexed": 0,
            "message": "Document is already indexed with identical hash. Use force=True to re-index.",
        }

    attempt = 0
    last_error = None
    while attempt <= retries:
        attempt += 1
        try:
            pages = extract_pages_from_pdf(str(path))
            if not check_pdf_text(pages):
                msg = f"No extractable text found in PDF {doc_name}. Scanned or image-based."
                logger.error(msg)
                log_ingestion_result(
                    str(path), doc_id, doc_name, doc_hash, doc_type,
                    source_category, len(pages), 0, 0, "empty", msg
                )
                return {
                    "status": "failed",
                    "error": msg,
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "points_indexed": 0,
                }

            processed_pages = []
            full_text_parts = []
            for page in pages:
                cleaned = clean_text(page["text"])
                if cleaned:
                    processed_pages.append({"page": page["page"], "text": cleaned})
                    full_text_parts.append(cleaned)

            chunks = chunk_pages(processed_pages)
            if not chunks:
                msg = "No non-empty chunks generated from document."
                logger.warning(msg)
                log_ingestion_result(
                    str(path), doc_id, doc_name, doc_hash, doc_type,
                    source_category, len(pages), 0, 0, "empty", msg
                )
                return {
                    "status": "empty",
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "points_indexed": 0,
                }

            combined_text = "\n".join(full_text_parts)
            meta = extract_report_metadata(path, combined_text)

            stations = meta.get("stations", [])
            report_date = meta.get("report_date")

            indexed_count = index_chunks(
                chunks=chunks,
                document_name=doc_name,
                doc_type=doc_type,
                source_category=source_category or ("weather_report" if doc_type == "weather_report" else "research"),
                report_date=report_date,
                stations=stations,
                doc_hash=doc_hash,
                extra_metadata={
                    "report_start_date": meta.get("report_start_date"),
                    "report_end_date": meta.get("report_end_date"),
                },
            )

            log_ingestion_result(
                str(path), doc_id, doc_name, doc_hash, doc_type,
                source_category, len(pages), len(chunks), indexed_count, "done"
            )

            logger.info("Successfully ingested %s: %d chunks indexed.", doc_name, indexed_count)
            return {
                "status": "done",
                "document_id": doc_id,
                "document_name": doc_name,
                "doc_hash": doc_hash,
                "pages": len(pages),
                "chunks": len(chunks),
                "points_indexed": indexed_count,
            }

        except Exception as exc:
            last_error = exc
            logger.warning("Ingestion attempt %d failed for %s: %s", attempt, doc_name, exc)
            if attempt <= retries:
                time.sleep(1.0 * attempt)

    error_str = str(last_error)
    logger.exception("All %d ingestion attempts failed for %s", retries + 1, doc_name)
    log_ingestion_result(
        str(path), doc_id, doc_name, doc_hash, doc_type,
        source_category, 0, 0, 0, "failed", error_str
    )
    return {
        "status": "failed",
        "document_id": doc_id,
        "document_name": doc_name,
        "error": error_str,
        "points_indexed": 0,
    }


def scan_and_ingest_directory(
    directory_path: str | Path,
    doc_type: str = "research",
    source_category: str | None = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Scan a directory recursively for PDFs and ingest any unindexed documents."""
    dir_path = Path(directory_path).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        logger.warning("Directory does not exist for scanning: %s", dir_path)
        return []

    results = []
    for pdf_file in dir_path.rglob("*.pdf"):
        # Determine source category from parent directory if not explicitly passed
        cat = source_category or pdf_file.parent.name
        dtype = "weather_report" if "report" in pdf_file.stem.lower() else doc_type
        res = ingest_pdf_document(pdf_file, doc_type=dtype, source_category=cat, force=force)
        results.append(res)

    return results


def weather_report_auto_ingest_hook(report_path: Path, metadata: dict[str, Any]) -> None:
    """Hook function registered with weather_pipeline report generator."""
    try:
        logger.info("Report hook triggered for %s. Auto-ingesting into RAG...", report_path.name)
        result = ingest_pdf_document(
            pdf_path=report_path,
            doc_type="weather_report",
            source_category="weather_reports",
            force=False,
        )
        logger.info("Report hook ingestion finished: %s", result.get("status"))
    except Exception as exc:
        logger.exception("Auto-ingestion hook failed for %s: %s", report_path, exc)
