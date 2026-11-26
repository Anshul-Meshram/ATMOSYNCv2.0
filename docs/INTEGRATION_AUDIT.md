# AtmoSync Full-Stack Integration Audit (Phase 0)

**Date**: November 25, 2026  
**Auditor**: Senior Full-Stack + ML + RAG Integration Engineer  
**Scope**: Complete codebase audit across `weather_pipeline`, `ml_model_v2`, `rag_pipeline`, and `frontend_backend`.

---

## 1. Actual System Architecture

AtmoSync is designed as a four-tier architecture:

```
               [ ECCC Public Climate API ]
                            │
                            ▼
           ┌─────────────────────────────────┐
           │     Weather Data Pipeline       │
           │  (FastAPI, SQLAlchemy, Alembic) │
           └──────────────┬──────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                                 ▼
[ PostgreSQL / Supabase ]           [ Weekly 7-Day PDF Report ]
  Table: weather_observations        (ReportLab in memory)
         │                                 │
         │ (HTTP /weather/{city})          │  *MISSING AUTO-INGESTION LINK*
         ▼                                 ▼
┌───────────────────────────────┐   ┌─────────────────────────────┐
│       ML Forecaster           │   │      RAG & LLM Engine       │
│ (LightGBM 7-Day + Legacy TCN) │   │ (Qdrant 'climate_documents' │
│  FastAPI Gateway in ml_model  │   │  MiniLM-L6-v2 + Gemini LLM) │
└──────────────┬────────────────┘   └──────────────┬──────────────┘
               │                                   │
               │ *MISSING LINK*                    │ (In-process python import)
               │ (Server uses MOCK_FORECASTS)      │
               ▼                                   ▼
        ┌─────────────────────────────────────────────────┐
        │        AtmoSync Unified Gateway & Web UI        │
        │      (Flask on :8000 + Vanilla JS/Chart.js)     │
        └─────────────────────────────────────────────────┘
```

### Module Roles:
1. **`weather_pipeline`**: Ingests daily climate observations from Environment and Climate Change Canada (ECCC) for 9 Canadian stations, normalizes them, stores them in PostgreSQL/Supabase, and generates 7-day observation summary PDFs using ReportLab.
2. **`ml_model_v2`** (and dummy `ml_model`): Houses the 7-day multi-output LightGBM forecaster (28 estimators: 7 leads × 4 targets), legacy TCN models, and a FastAPI service (`app.py`) for predictions and forecast persistence to Supabase.
3. **`rag_pipeline`**: Document ingestion (PyMuPDF), chunking (2000 chars, 300 overlap), embeddings (`sentence-transformers/all-MiniLM-L6-v2`), local vector storage (Qdrant collection `climate_documents` with 43 points), and Gemini LLM provider.
4. **`frontend_backend`**: Flask server on port 8000 serving an interactive dashboard (Chart.js) and acting as an API gateway for stations, forecasts, and RAG queries.

---

## 2. HTTP Endpoint Catalog

### A. Weather Pipeline (`weather_pipeline/app/main.py`)
| Method | Path | Request Model / Params | Response Model / Type | Source File |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | None | `{"status": "ok"}` | [main.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/main.py#L197) |
| `GET` | `/weather/stations` | None | `list[WeatherStationResponse]` (city, climate_identifier, available_from) | [api/weather.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/api/weather.py#L25) |
| `GET` | `/weather/report/weekly` | Query: `start_date` (date) | Binary PDF (`application/pdf`) | [api/weather.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/api/weather.py#L40) |
| `GET` | `/weather/{city}` | Path: `city`, Query: `start_date`, `end_date` | `list[WeatherObservation]` (temperatures, precip, flags) | [api/weather.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/api/weather.py#L72) |
| `POST` | `/rag/explain` | Body: `ExplainRequest` (`query`, `station`, `ml_forecast`, `top_k`) | `ExplainResponse` (`answer`, `citations`, `grounded`, `confidence`, `event_summary`) | [api/rag.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/api/rag.py#L59) |
| `GET` | `/rag/health` | None | `{"status": "ok", "service": "ClimateRAGService"}` | [api/rag.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/api/rag.py#L105) |

### B. Machine Learning Service (`ml_model_v2/app.py`)
| Method | Path | Request Model / Params | Response Model / Type | Source File |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | None | `{"service": "...", "status": "ok", "docs": "/docs", ...}` | [app.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/app.py#L142) |
| `GET` | `/health` | None | `{"status": "...", "models": {...}, "forecast_storage_configured": bool, ...}` | [app.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/app.py#L156) |
| `POST` | `/predict` | Body: `PredictionRequest` (`history`: 30 daily feature dicts) | `{"model": "TCN", "forecast": [...]}` (legacy 30-day TCN) | [app.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/app.py#L191) |
| `GET` | `/forecasts` | Query: `station`, `start_date`, `end_date`, `limit` (default 50) | `{"count": int, "forecasts": list[dict]}` | [app.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/app.py#L305) |
| `POST` | `/forecasts/refresh` | Header: `X-Atmosync-Refresh-Token` | `{"status": "success", "stations_processed": 9, "rows_upserted": 63, ...}` | [app.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/app.py#L560) |
| `GET` | `/weather/{city}` | Path: `city`, Query: `start_date`, `end_date` | `{"station": city, "observations": [...]}` (with forecast fallback) | [app.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/app.py#L441) |

### C. Frontend / Backend Gateway (`frontend_backend/server.py`)
| Method | Path | Request Model / Params | Response Model / Type | Source File |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | None | HTML (`static/index.html`) | [server.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/frontend_backend/server.py#L97) |
| `GET` | `/api/weather/stations` | None | `list[dict]` (9 Canadian stations) | [server.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/frontend_backend/server.py#L103) |
| `GET` | `/api/weather/forecast` | Query: `station` | `{"station": "...", "model": "LightGBM", "predictions": [...]}` *(Currently Mock)* | [server.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/frontend_backend/server.py#L109) |
| `POST` | `/api/rag/explain` | Body: `{"query": str, "station": str, "ml_forecast": dict, "top_k": int}` | `{"answer": str, "citations": [...], "grounded": bool, ...}` | [server.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/frontend_backend/server.py#L140) |
| `GET` | `/api/health` | None | `{"status": "ok", "system": "...", "modules": [...]}` | [server.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/frontend_backend/server.py#L190) |

---

## 3. Database Table Schema Analysis

### Table 1: `public.weather_observations` (PostgreSQL)
* **Location**: `weather_pipeline/alembic/versions/001_weather_observation.py`
* **Primary Key**: `id` (`BigInteger`, Identity)
* **Unique Constraint**: `uq_weather_observations_station_date` on `(climate_identifier, observation_date)`
* **Indexes**: `ix_weather_observations_lookup` on `(climate_identifier, observation_date DESC)`
* **Columns**:
  * `climate_identifier` (`VARCHAR(32)`, NOT NULL)
  * `observation_date` (`DATE`, NOT NULL)
  * `mean_temperature`, `min_temperature`, `max_temperature` (`NUMERIC`) + flag strings (`VARCHAR(8)`)
  * `total_precipitation`, `total_rain`, `total_snow`, `snow_on_ground` (`NUMERIC`) + flags
  * `direction_max_gust`, `speed_max_gust` (`NUMERIC`) + flags
  * `cooling_degree_days`, `heating_degree_days`, `min_relative_humidity` (`NUMERIC`) + flags
  * `created_at`, `updated_at` (`TIMESTAMP`, server default `CURRENT_TIMESTAMP`)

### Table 2: `public.weather_forecasts` (Supabase / PostgreSQL)
* **Schema Conflict Discovered**:
  * **File Definition** ([supabase_new_table.sql](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/supabase_new_table.sql)):
    Columns: `id`, `station`, `station_id`, `history_start` (NOT NULL), `history_end` (NOT NULL), `forecast_date` (NOT NULL), `forecast_horizon_day` (NOT NULL), `model`, `model_version`, `predicted_max_temp_c`, `predicted_min_temp_c`, `predicted_mean_temp_c`, `predicted_precip_mm`, `forecast_generated_at`, `created_at`.
  * **Application Code Expectation** ([ml_model_v2/app.py:746-759](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/app.py#L746)):
    Inserts: `station`, `station_id`, `forecast_date`, `generated_at`, `created_at`, `model_name`, `model_version`, `max_temp_c`, `min_temp_c`, `mean_temp_c`, `precip_mm`, `updated_at`.
    Omits: `history_start`, `history_end`, `forecast_horizon_day`.
  * **Root Cause of Empty Forecasts**: If the table was provisioned using `supabase_new_table.sql`, any insertion from `app.py` fails with column not found (`max_temp_c` vs `predicted_max_temp_c`) and NOT NULL constraint violations on `history_start`, `history_end`, and `forecast_horizon_day`.

---

## 4. Inter-Module Dependency Map

1. **Weather Pipeline → ECCC API**:
   * Protocol: HTTPS GET
   * Client: `httpx.AsyncClient` in [weather_pipeline/app/clients/eccc.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/clients/eccc.py)
   * Behavior: Paginated GeoJSON feature collection retrieval.
2. **Weather Pipeline → PostgreSQL Database**:
   * Protocol: Async SQLAlchemy via `asyncpg` / `psycopg2-binary`.
   * Connection: `DATABASE_URL` in [weather_pipeline/app/db/session.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/db/session.py).
3. **ML Pipeline (`LightGBMForecaster`) → Weather Pipeline**:
   * Protocol: HTTP GET (`requests.get`)
   * URL: `ATMOSYNC_WEATHER_API_BASE_URL/weather/{station}?start_date=...&end_date=...`
   * Requirement: 90 calendar days of consecutive history.
4. **ML Pipeline (`app.py`) → Supabase**:
   * Protocol: HTTPS PostgREST REST API
   * Endpoints: `SUPABASE_URL/rest/v1/weather_forecasts`
   * Headers: `apikey`, `Authorization: Bearer <key>`.
5. **Frontend / Backend → RAG Pipeline**:
   * Protocol: In-process Python import (`from src.llm.services.llm_service import create_climate_rag_service`).
   * Service: `ClimateRAGService.explain_climate_event()`.
6. **RAG Pipeline → Qdrant Vector Store**:
   * Protocol: Local embedded storage (`QdrantClient(path='rag_pipeline/qdrant_storage')`).
   * Collection: `climate_documents` (384-dimensional vectors, Cosine distance).
   * Verified Data: **43 indexed points** verified in SQLite storage.
7. **RAG Pipeline → Google Gemini**:
   * Protocol: HTTPS via `google-genai` SDK.
   * Model: `gemini-3.5-flash-lite` / `gemini-3.8-flash` with retry and fallback handling.

---

## 5. Comprehensive Gap List (Ranked by Severity)

| Rank | Severity | Issue Description | Root Cause / Impact | Location |
| :---: | :---: | :--- | :--- | :--- |
| **1** | **CRITICAL** | **Supabase Forecast Schema Mismatch & Persistence Failure** | DDL in `supabase_new_table.sql` uses `predicted_max_temp_c` and mandates NOT NULL on `history_start`, `history_end`, `forecast_horizon_day`. Meanwhile, `app.py` inserts `max_temp_c` and omits those 3 fields. Causes upserts to fail, leading to `GET /forecasts` returning empty. | [ml_model_v2/app.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/app.py) vs [supabase_new_table.sql](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/supabase_new_table.sql) |
| **2** | **CRITICAL** | **Frontend/Gateway Severed from Real ML Forecasts** | `server.py` returns hardcoded `MOCK_FORECASTS` dict. Does not invoke `LightGBMForecaster` or query Supabase. Consequently, the RAG assistant is grounded on mock forecast numbers. | [frontend_backend/server.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/frontend_backend/server.py#L48) |
| **3** | **CRITICAL** | **Missing PDF Report Auto-Ingestion Pipeline** | `weather_pipeline/app/services/report.py` generates weekly PDF reports in memory, but there is no hook, watcher, or ingestion pipeline to chunk, embed, and upsert them into Qdrant `climate_documents`. | [weather_pipeline/app/services/report.py](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/weather_pipeline/app/services/report.py) & [rag_pipeline](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/rag_pipeline) |
| **4** | **HIGH** | **Anomaly Detection and Classification Do Not Exist in Code** | No anomaly detection or classification implementation exists in any Python file in the repository. Mentions only exist in indexed research proposal PDFs. | [ml_model_v2/](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2) |
| **5** | **HIGH** | **No Standalone RAG HTTP API** | `rag_pipeline` lacks its own HTTP API router (e.g. `POST /rag/search`, `POST /rag/ingest`, `GET /rag/stats`). It is currently invoked via direct file imports only. | [rag_pipeline/](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/rag_pipeline) |
| **6** | **HIGH** | **Lack of Offline / Mock LLM Provider for Resilient Operation** | When Gemini API is unavailable or unconfigured, the system crashes on explain queries. Needs a first-class deterministic Mock Provider selectable via environment variable. | [rag_pipeline/src/llm/clients/](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/rag_pipeline/src/llm/clients) |
| **7** | **MEDIUM** | **Misplaced Scheduled Workflow** | `daily-forecast.yml` is in `ml_model_v2/.github/workflows/`, which GitHub Actions completely ignores. It must be at the root `.github/workflows/`. | [ml_model_v2/.github/workflows/daily-forecast.yml](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/ml_model_v2/.github/workflows/daily-forecast.yml) |
| **8** | **MEDIUM** | **Dual Directory Confusion (`ml_model` vs `ml_model_v2`)** | An empty `ml_model` directory exists alongside `ml_model_v2`, while `README_RENDER.md` and configuration files refer to `ml_model`. | Repository Root |
| **9** | **MEDIUM** | **Missing Python Dependencies in Local Environment** | `lightgbm`, `fastapi`, and `psycopg` are not installed locally and missing from root `requirements.txt`. | [requirements.txt](file:///m:/sem7/Major%20Project/ATMOSYNCv2.0/requirements.txt) |
| **10** | **LOW** | **Root Directory Clutter** | Terminal dump files (`hul`, `o`, `◎ git status`) and backup zip (`rag_pipeline.zip`) exist in the repository root. | Repository Root |

---

## 6. Audit Verdict

The individual scientific and algorithmic components (ECCC ingestion client, ReportLab PDF layout, LightGBM 28-model inference pipeline, Qdrant vector database, and Gemini client) are functional. However, the data contracts and pipelines connecting them are broken or unbuilt.

With this audit complete, we are ready to proceed with **Phase 1: Weather data verification + 7-day report PDF deterministic generation and export**.
