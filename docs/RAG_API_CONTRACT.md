# AtmoSync RAG API Contract (v1.0.0)

This document specifies the frozen interface contract for the Retrieval-Augmented Generation (RAG) and Document Ingestion service in **AtmoSync v2.0** (`rag_pipeline`).

---

## 1. Overview & Architecture

- **Vector Database**: Qdrant (`collection: climate_documents`).
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors, Cosine distance).
- **Chunking Parameters**:
  - `CHUNK_SIZE`: 2000 characters
  - `CHUNK_OVERLAP`: 300 characters
  - Structure-aware paragraph boundary splitting.
- **Idempotency Guarantee**: Point IDs are generated deterministically using UUIDv5 over `(document_id, chunk_id)`:
  $$\text{point\_id} = \text{uuid5}(\text{NAMESPACE\_URL}, f"{document\_id}\_{chunk\_id}")$$
  Re-indexing an existing document overwrites chunks in place without creating duplicates.
- **Audit Registry**: SQLite tracking log (`rag_pipeline/data/ingestion_history.db`) recording file paths, SHA-256 hashes, status, page/chunk counts, and ISO UTC timestamps.

---

## 2. Canonical Chunk Schema (`RetrievedChunk`)

To permanently eliminate any text vs. content mismatch between RAG and LLM validation modules, the schema standardizes on **`text`** as canonical, providing **`content`** as an automatic backward-compatible property.

```json
{
  "document_id": "weather_report_2026-10-01_2026-10-07",
  "document_name": "weather_report_2026-10-01_2026-10-07.pdf",
  "source": "weather_report_2026-10-01_2026-10-07.pdf",
  "chunk_id": "weather_report_2026-10-01_2026-10-07_page_1_chunk_1",
  "page": 1,
  "text": "AtmoSync 7-Day Regional Weather Report\nPeriod: 2026-10-01 to 2026-10-07...",
  "content": "AtmoSync 7-Day Regional Weather Report\nPeriod: 2026-10-01 to 2026-10-07...",
  "score": 0.8245,
  "char_count": 850,
  "doc_type": "weather_report",
  "source_category": "weather_reports",
  "report_date": "2026-10-01",
  "publication_date": "2026-10-01",
  "stations": ["Vancouver", "Toronto", "Montreal"]
}
```

---

## 3. Endpoints

### 3.1 `POST /rag/search`
Query semantic vector store with optional filters.

- **Request Body**:
```json
{
  "query": "What are the seasonal precipitation baselines for Vancouver?",
  "top_k": 5,
  "doc_type": "research",
  "station": "vancouver",
  "min_score": 0.35
}
```
- **Response Body**:
```json
{
  "query": "What are the seasonal precipitation baselines for Vancouver?",
  "total": 3,
  "results": [
    {
      "document_id": "Climate_Intelligence_System_Project_Report",
      "document_name": "Climate_Intelligence_System_Project_Report.pdf",
      "source": "Climate_Intelligence_System_Project_Report.pdf",
      "chunk_id": "Climate_Intelligence_System_Project_Report_page_2_chunk_1",
      "page": 2,
      "text": "Historical precipitation anomalies in coastal British Columbia...",
      "content": "Historical precipitation anomalies in coastal British Columbia...",
      "score": 0.7891,
      "char_count": 520,
      "doc_type": "research",
      "source_category": "research_papers",
      "report_date": null,
      "publication_date": null,
      "stations": []
    }
  ]
}
```

### 3.2 `POST /rag/ingest`
Idempotently ingest a single PDF document.

- **Request Body**:
```json
{
  "file_path": "weather_pipeline/data/reports/weather_report_2026-10-01_2026-10-07.pdf",
  "doc_type": "weather_report",
  "source_category": "weather_reports",
  "force": false
}
```
- **Response Body**:
```json
{
  "status": "done",
  "document_id": "weather_report_2026-10-01_2026-10-07",
  "document_name": "weather_report_2026-10-01_2026-10-07.pdf",
  "doc_hash": "a4b5c6...",
  "pages": 1,
  "chunks": 2,
  "points_indexed": 2
}
```

### 3.3 `GET /rag/health`
Verify health and status of vector database and embedding models.

- **Response Body**:
```json
{
  "status": "ok",
  "collection": "climate_documents",
  "collection_ready": true,
  "total_points": 45,
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_dimension": 384,
  "error": null
}
```

### 3.4 `GET /rag/stats`
Return index statistics and recent ingestion history.

---

## 4. Automated Report Ingestion Hook

When `weather_pipeline` generates a 7-day weather report PDF, `save_weekly_report` automatically triggers `weather_report_auto_ingest_hook`:
1. Extracts text from each generated page.
2. Flags scanned or empty PDFs.
3. Generates paragraph-aligned chunks.
4. Generates dense embeddings.
5. Upserts points into Qdrant collection `climate_documents`.
6. Records ingestion status in the local audit database.
