import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Ensure rag_pipeline is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAG_PATH = PROJECT_ROOT / "rag_pipeline"
if str(RAG_PATH) not in sys.path:
    sys.path.insert(0, str(RAG_PATH))

from src.llm.services.llm_service import create_climate_rag_service

router = APIRouter(
    prefix="/rag",
    tags=["rag"],
)

# Initialize service singleton
_rag_service = None


def get_rag_service():
    global _rag_service
    if _rag_service is None:
        _rag_service = create_climate_rag_service()
    return _rag_service


class ExplainRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Climate question or event to explain")
    station: str | None = Field(None, description="Optional city or station name")
    ml_forecast: dict[str, Any] | None = Field(None, description="Optional ML prediction payload")
    top_k: int = Field(5, ge=1, le=10, description="Number of evidence passages to retrieve")


class CitationModel(BaseModel):
    source: str
    page: int | None = None
    chunk_id: str | None = None


class EventSummaryModel(BaseModel):
    event_type: str | None = None
    severity: str | None = None


class ExplainResponse(BaseModel):
    answer: str
    citations: list[CitationModel]
    grounded: bool
    insufficient_evidence: bool
    confidence: float | None = None
    event_summary: EventSummaryModel | None = None


@router.post("/explain", response_model=ExplainResponse)
async def explain_climate_event(request: ExplainRequest) -> ExplainResponse:
    """
    Generate an evidence-backed scientific climate explanation using Qdrant and Gemini.
    """
    try:
        service = get_rag_service()

        ml_context = request.ml_forecast
        if ml_context is None and request.station:
            ml_context = {"station": request.station}

        result = service.explain_climate_event(
            user_query=request.query,
            ml_context=ml_context,
            top_k=request.top_k,
        )

        citations = [
            CitationModel(
                source=c.source,
                page=c.page,
                chunk_id=c.chunk_id,
            )
            for c in result.citation
        ]

        event_summary = None
        if result.event_summary:
            event_summary = EventSummaryModel(
                event_type=result.event_summary.event_type,
                severity=result.event_summary.severity,
            )

        return ExplainResponse(
            answer=result.answer,
            citations=citations,
            grounded=result.grounded,
            insufficient_evidence=result.insufficient_evidence,
            confidence=result.confidence,
            event_summary=event_summary,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def rag_health() -> dict[str, str]:
    return {"status": "ok", "service": "ClimateRAGService"}
