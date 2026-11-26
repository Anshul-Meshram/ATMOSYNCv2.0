from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from src.rag.schemas import RetrievedChunk
from src.rag.retrieval.retriever import retrieve_chunks

logger = logging.getLogger("llm.context")

# Canonical station names across AtmoSync
KNOWN_STATIONS = {
    "vancouver": "1108395",
    "edmonton": "3012210",
    "calgary": "3031094",
    "winnipeg": "5023222",
    "ottawa": "6106000",
    "toronto": "6158355",
    "montreal": "7025251",
    "quebec city": "701S001",
    "quebec": "701S001",
    "halifax": "8202251",
}

DEFAULT_MIN_SCORE_THRESHOLD = float(os.getenv("RAG_MIN_SCORE", "0.35"))
MAX_RAG_CHARS = 12000  # Cap total literature context


class StructuredContext(BaseModel):
    """
    Unified multimodal context container feeding the prompt builder and LLM.
    Strictly partitions empirical ML metrics from scientific RAG literature.
    """
    question: str
    detected_station: str | None = None
    station_id: str | None = None
    
    # ML Section
    ml_available: bool = False
    ml_forecasts: list[dict[str, Any]] = Field(default_factory=list)
    ml_anomalies: list[dict[str, Any]] = Field(default_factory=list)
    ml_metadata: dict[str, Any] = Field(default_factory=dict)
    
    # RAG Section
    rag_sufficient: bool = False
    rag_chunks: list[RetrievedChunk] = Field(default_factory=list)
    rag_metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Metadata & Timestamps
    meta: dict[str, Any] = Field(default_factory=dict)


def detect_station(query: str) -> str | None:
    """Detect if any Canadian target station is referenced in the natural language query."""
    q_lower = query.lower()
    for station_name in KNOWN_STATIONS:
        pattern = r"\b" + re.escape(station_name) + r"\b"
        if re.search(pattern, q_lower):
            return "quebec city" if station_name == "quebec" else station_name
    return None


def fetch_ml_data_for_station(station: str) -> tuple[list[dict], list[dict], dict]:
    """Retrieve verified forecasts and anomalies from ML local storage/API."""
    try:
        import sys
        from pathlib import Path
        ml_path = Path(__file__).resolve().parents[3] / "ml_model_v2"
        if str(ml_path) not in sys.path:
            sys.path.insert(0, str(ml_path))

        from forecasting.forecast_storage import get_forecast_rows, get_anomaly_rows
        forecasts = get_forecast_rows(station=station, limit=7)
        anomalies = get_anomaly_rows(station=station, limit=10)

        meta = {
            "model_name": "LightGBM",
            "model_version": "lightgbm-v1",
            "units": {"temperature": "°C", "precipitation": "mm"},
            "forecast_count": len(forecasts),
            "anomalies_count": len(anomalies),
            "generated_at": forecasts[0].get("generated_at") if forecasts else None,
        }
        return forecasts, anomalies, meta
    except Exception as exc:
        logger.warning("Could not fetch ML data for station %s: %s", station, exc)
        return [], [], {"error": str(exc)}


def build_structured_context(
    query: str,
    station: str | None = None,
    ml_context_override: dict[str, Any] | None = None,
    top_k: int = 5,
    min_score_threshold: float = DEFAULT_MIN_SCORE_THRESHOLD,
) -> StructuredContext:
    """
    Construct a unified, partitioned context object.
    
    Applies strict evidence sufficiency policies:
    - If ML data is absent, marks ml_available = False with diagnostic reason.
    - If RAG retrieval yields low scores (< threshold), marks rag_sufficient = False.
    """
    clean_query = query.strip()
    target_station = (station or detect_station(clean_query) or "").lower()
    target_station_id = KNOWN_STATIONS.get(target_station)

    # 1. Retrieve empirical ML forecasts & anomalies
    ml_forecasts: list[dict] = []
    ml_anomalies: list[dict] = []
    ml_meta: dict[str, Any] = {}

    if ml_context_override:
        ml_forecasts = ml_context_override.get("forecasts", [])
        ml_anomalies = ml_context_override.get("anomalies", [])
        ml_meta = {
            "model_name": ml_context_override.get("model_name", "LightGBM"),
            "model_version": ml_context_override.get("model_version", "lightgbm-v1"),
            "generated_at": ml_context_override.get("generated_at"),
            "source": "api_override",
        }
    elif target_station:
        ml_forecasts, ml_anomalies, ml_meta = fetch_ml_data_for_station(target_station)

    ml_available = len(ml_forecasts) > 0

    # 2. Retrieve authoritative literature from Qdrant
    raw_chunks = retrieve_chunks(
        query=clean_query,
        top_k=top_k,
        station=target_station if target_station else None,
        min_score=0.0,  # Fetch raw to evaluate against threshold
    )

    # De-duplicate chunks by (document_name, page, chunk_id) and filter by score
    seen_keys = set()
    valid_chunks = []
    total_chars = 0

    for ch in raw_chunks:
        key = (ch.get("document_name"), ch.get("page"), ch.get("chunk_id"))
        if key in seen_keys:
            continue
        seen_keys.add(key)

        score = float(ch.get("score", 0.0))
        chunk_obj = RetrievedChunk(**ch)

        # Check character budget
        if total_chars + chunk_obj.char_count > MAX_RAG_CHARS:
            break

        valid_chunks.append(chunk_obj)
        total_chars += chunk_obj.char_count

    # Evidence sufficiency policy for RAG
    best_score = max([c.score for c in valid_chunks], default=0.0)
    rag_sufficient = len(valid_chunks) > 0 and best_score >= min_score_threshold

    now_iso = datetime.now(timezone.utc).isoformat()
    meta = {
        "timestamp_query_utc": now_iso,
        "score_threshold": min_score_threshold,
        "best_rag_score": best_score,
        "evidence_status": {
            "ml_data_available": ml_available,
            "rag_evidence_sufficient": rag_sufficient,
        },
    }

    return StructuredContext(
        question=clean_query,
        detected_station=target_station or None,
        station_id=target_station_id,
        ml_available=ml_available,
        ml_forecasts=ml_forecasts,
        ml_anomalies=ml_anomalies,
        ml_metadata=ml_meta,
        rag_sufficient=rag_sufficient,
        rag_chunks=valid_chunks,
        rag_metadata={
            "retrieved_count": len(valid_chunks),
            "best_score": best_score,
            "score_threshold": min_score_threshold,
        },
        meta=meta,
    )
