from typing import Any

from src.llm.clients.llm_provider import LLMProvider
from src.llm.generation.evidence_validator import has_usable_evidence
from src.llm.generation.generation_service import GenerationService
from src.llm.schemas.request import LLMRequest
from src.llm.schemas.response import Citation, EventSummary, LLMResponse
from src.rag.retrieval.retriever import retrieve_chunks


class ClimateRAGService:
    """
    Unified RAG and LLM service for the AtmoSync Climate Intelligence System.

    Coordinates:
    1. Retrieval of grounded scientific climate evidence from Qdrant.
    2. Evidence validation to prevent hallucinations.
    3. Context assembly with ML model predictions.
    4. Generation of cited, scientifically backed answers.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        if provider is None:
            # Lazy import to allow testing without GEMINI_API_KEY when mock is used
            from src.llm.clients.gemini_client import GeminiClient
            self.provider: LLMProvider = GeminiClient()
        else:
            self.provider = provider

        self.generation_service = GenerationService(self.provider)

    def explain_climate_event(
        self,
        user_query: str,
        ml_context: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> LLMResponse:
        """
        Retrieve literature evidence and generate a cited explanation.

        Args:
            user_query: The question or climate event description.
            ml_context: Optional quantitative predictions or anomalies from ML API.
            top_k: Number of relevant evidence chunks to retrieve from Qdrant.

        Returns:
            Structured LLMResponse containing grounded answer, citations, and metadata.
        """
        if not user_query or not user_query.strip():
            raise ValueError("user_query must be a non-empty string.")

        # 1. Retrieve evidence from Qdrant vector store
        chunks = retrieve_chunks(user_query.strip(), top_k=top_k)

        rag_context = {
            "query": user_query.strip(),
            "results": chunks,
        }

        # 2. Check for usable scientific evidence
        usable = has_usable_evidence(rag_context)

        # 3. Assemble standardized LLM request
        request = LLMRequest(
            user_query=user_query.strip(),
            ml_context=ml_context,
            rag_context=rag_context,
        )

        # 4. Generate answer via provider
        raw_answer = self.generation_service.generate(request)

        # 5. Extract citations from retrieved chunks
        citations: list[Citation] = []
        seen_citations = set()

        for chunk in chunks:
            source = chunk.get("source") or chunk.get("document_name")
            page = chunk.get("page")
            chunk_id = chunk.get("chunk_id") or chunk.get("id")

            if source:
                key = (source, page, chunk_id)
                if key not in seen_citations:
                    seen_citations.add(key)
                    citations.append(
                        Citation(
                            source=str(source),
                            page=page,
                            chunk_id=chunk_id,
                        )
                    )

        # 6. Extract event summary and confidence from ML context if present
        event_summary = None
        confidence = None

        if isinstance(ml_context, dict):
            confidence = ml_context.get("confidence")
            event_info = ml_context.get("event")

            if isinstance(event_info, dict):
                event_summary = EventSummary(
                    event_type=event_info.get("type"),
                    severity=event_info.get("severity"),
                )
            elif "station" in ml_context:
                station = ml_context.get("station")
                model_name = ml_context.get("model", "ML Forecaster")
                event_summary = EventSummary(
                    event_type=f"{model_name} Forecast",
                    severity=f"station: {station}",
                )

        return LLMResponse(
            answer=raw_answer,
            event_summary=event_summary,
            citation=citations,
            grounded=usable,
            insufficient_evidence=not usable,
            confidence=confidence,
        )

    def explain_ml_forecast(
        self,
        forecast_data: dict[str, Any],
        custom_query: str | None = None,
        top_k: int = 5,
    ) -> LLMResponse:
        """
        Specialized helper that consumes the ML module's API output (e.g. /predict or /forecasts)
        and generates a cited scientific climate explanation.

        Args:
            forecast_data: The JSON payload returned from the ML API endpoint.
            custom_query: Optional custom user question. If omitted, an optimal query is auto-built.
            top_k: Number of evidence chunks to retrieve.
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
            top_k=top_k,
        )


def create_climate_rag_service(
    provider: LLMProvider | None = None,
) -> ClimateRAGService:
    """Factory helper to construct the ClimateRAGService."""
    return ClimateRAGService(provider=provider)
