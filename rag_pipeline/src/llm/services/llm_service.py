from __future__ import annotations

import logging
from typing import Any

from src.llm.clients.llm_provider import LLMProvider, get_llm_provider
from src.llm.generation.evidence_validator import has_usable_evidence, validate_evidence_sufficiency
from src.llm.generation.generation_service import GenerationService
from src.llm.schemas.request import LLMRequest
from src.llm.schemas.response import Citation, EventSummary, LLMResponse
from src.rag.retrieval.retriever import retrieve_chunks
from src.llm.context.structured_context import build_structured_context

logger = logging.getLogger("llm.service")


class ClimateRAGService:
    """
    Unified RAG and LLM service for the AtmoSync Climate Intelligence System.

    Coordinates:
    1. Structured context assembly with ML model predictions and anomalies.
    2. Semantic retrieval of grounded scientific climate evidence from Qdrant.
    3. Evidence validation to detect sufficiency and prevent hallucinations.
    4. Generation of cited, scientifically backed answers across Gemini or Mock providers.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_llm_provider()
        self.generation_service = GenerationService(self.provider)

    def explain_climate_event(
        self,
        user_query: str,
        ml_context: dict[str, Any] | None = None,
        station: str | None = None,
        top_k: int = 5,
        min_score: float = 0.35,
    ) -> LLMResponse:
        """
        Build unified structured context, retrieve evidence, and generate cited explanation.

        Args:
            user_query: User question or climate event query.
            ml_context: Optional explicit ML payload (forecasts/anomalies).
            station: Optional target station name.
            top_k: Number of relevant evidence chunks to retrieve.
            min_score: Threshold for evidence sufficiency.
        """
        if not user_query or not user_query.strip():
            raise ValueError("user_query must be a non-empty string.")

        # 1. Build unified structured context
        struct_ctx = build_structured_context(
            query=user_query,
            station=station,
            ml_context_override=ml_context,
            top_k=top_k,
            min_score_threshold=min_score,
        )

        # 2. Package for legacy and new prompts
        ml_data = {
            "station": struct_ctx.detected_station or "Regional Canada",
            "station_id": struct_ctx.station_id,
            "forecasts": struct_ctx.ml_forecasts,
            "anomalies": struct_ctx.ml_anomalies,
            **struct_ctx.ml_metadata,
        } if struct_ctx.ml_available else None

        rag_data = {
            "query": user_query.strip(),
            "results": [c.model_dump() for c in struct_ctx.rag_chunks],
        }

        request = LLMRequest(
            user_query=user_query.strip(),
            ml_context=ml_data,
            rag_context=rag_data,
        )

        # 3. Generate answer via provider
        raw_answer = self.generation_service.generate(request)

        # 4. Extract citations from retrieved chunks
        citations: list[Citation] = []
        seen = set()
        for chunk in struct_ctx.rag_chunks:
            source = chunk.document_name
            page = chunk.page
            chunk_id = chunk.chunk_id
            if source:
                key = (source, page, chunk_id)
                if key not in seen:
                    seen.add(key)
                    citations.append(
                        Citation(
                            source=str(source),
                            page=page,
                            chunk_id=chunk_id,
                        )
                    )

        # 5. Extract event summary from anomalies/forecast
        event_summary = None
        if struct_ctx.ml_anomalies:
            first_anom = struct_ctx.ml_anomalies[0]
            event_summary = EventSummary(
                event_type=first_anom.get("label", "Climate Anomaly"),
                severity=first_anom.get("status", "warning"),
            )
        elif struct_ctx.ml_available:
            event_summary = EventSummary(
                event_type="LightGBM 7-Day Forecast",
                severity=f"station: {struct_ctx.detected_station}",
            )

        return LLMResponse(
            answer=raw_answer,
            event_summary=event_summary,
            citation=citations,
            grounded=struct_ctx.rag_sufficient,
            insufficient_evidence=not struct_ctx.rag_sufficient,
            confidence=0.92 if struct_ctx.rag_sufficient and struct_ctx.ml_available else (0.75 if struct_ctx.rag_sufficient or struct_ctx.ml_available else 0.40),
        )

    def explain_ml_forecast(
        self,
        forecast_data: dict[str, Any],
        custom_query: str | None = None,
        top_k: int = 5,
    ) -> LLMResponse:
        """
        Specialized helper that consumes the ML module's API output and generates a cited scientific explanation.
        """
        station = forecast_data.get("station", "Unknown station").capitalize()

        if custom_query and custom_query.strip():
            query = custom_query.strip()
        else:
            query = (
                f"Explain climate patterns, seasonal baselines, and temperature/precipitation "
                f"variability relevant to weather forecasts in {station}, Canada."
            )

        return self.explain_climate_event(
            user_query=query,
            ml_context=forecast_data,
            station=station,
            top_k=top_k,
        )


def create_climate_rag_service(
    provider: LLMProvider | None = None,
) -> ClimateRAGService:
    """Factory helper to construct the ClimateRAGService."""
    return ClimateRAGService(provider=provider)
