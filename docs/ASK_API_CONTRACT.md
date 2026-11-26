# AtmoSync Unified Ask / Explain API Contract (v1.0.0)

This document specifies the frozen interface contract for the Unified Question Answering and Climate Explanation endpoints (`POST /api/ask` and `POST /api/rag/explain`) in **AtmoSync v2.0** (`frontend_backend/server.py`).

---

## 1. Overview & Capabilities

- **Endpoint**: `POST /api/ask` (with alias `POST /api/rag/explain`)
- **Backend Architecture**:
  1. Detects relevant Canadian climate station from query or explicit parameters.
  2. Queries LightGBM 7-day multi-target quantitative forecasts and detected anomaly events from the ML store.
  3. Queries semantic vector store (Qdrant `climate_documents`) using `all-MiniLM-L6-v2` dense embeddings.
  4. Assembles a partitioned `StructuredContext` enforcing evidence sufficiency ($score \ge \text{min\_score}$).
  5. Dispatches prompt to the active LLM provider (`GeminiClient` with `gemini-3.8-flash` / `gemini-3.5-flash-lite`, or `MockProvider` when running offline).
  6. Validates citations and grounds response before returning to client.

---

## 2. Request Schema

```json
{
  "query": "Explain the 7-day forecast for Toronto in the context of Canadian climate baselines.",
  "station": "toronto",
  "top_k": 4,
  "ml_forecast": null
}
```

### Fields
| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | **Yes** | Natural language user query or question. |
| `station` | string | No | Optional station name (e.g. `toronto`, `vancouver`). If omitted, auto-detected from `query`. |
| `top_k` | integer | No | Maximum number of literature evidence chunks to retrieve (default: 5, max: 10). |
| `ml_forecast` | object | No | Optional manual forecast payload override. If omitted, fetched directly from ML store. |

---

## 3. Response Schema

```json
{
  "answer": "### Climate & Meteorological Assessment for Toronto\n\nBased on the 7-day LightGBM weather forecast for Toronto, temperatures range between 1.2°C and 7.3°C...",
  "citations": [
    {
      "source": "Climate_Intelligence_System_Project_Report.pdf",
      "page": 2,
      "chunk_id": "Climate_Intelligence_System_Project_Report_page_2_chunk_1"
    },
    {
      "source": "weather_report_2026-10-01_2026-10-07.pdf",
      "page": 3,
      "chunk_id": "weather_report_2026-10-01_2026-10-07_page_3_chunk_1"
    }
  ],
  "grounded": true,
  "insufficient_evidence": false,
  "confidence": 0.92,
  "event_summary": {
    "event_type": "LightGBM 7-Day Forecast",
    "severity": "station: toronto"
  }
}
```

### Fields
| Field | Type | Description |
|---|---|---|
| `answer` | string | Formatted markdown response synthesized strictly from ML numbers and literature citations. |
| `citations` | list | List of source documents and page numbers cited in the explanation. |
| `grounded` | boolean | True if evidence met the semantic similarity threshold. |
| `insufficient_evidence` | boolean | True if retrieved evidence was weak or missing. |
| `confidence` | float | System confidence score (0.0 to 1.0) derived from evidence presence. |
| `event_summary` | object | Detected anomaly or forecast event classification. |
