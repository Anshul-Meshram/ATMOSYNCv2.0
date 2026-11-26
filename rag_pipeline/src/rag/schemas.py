from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, model_validator


class RetrievedChunk(BaseModel):
    """
    Unified canonical schema for retrieved document chunks across RAG and LLM modules.
    
    Provides both `text` (canonical field) and `content` (property/alias) to eliminate
    the text vs content mismatch permanently.
    """
    document_id: str = Field(..., description="Unique document identifier, typically stem of filename")
    document_name: str = Field(..., description="Filename of the source document")
    source: str = Field(..., description="Document source or filename (alias for document_name)")
    chunk_id: str = Field(..., description="Deterministic chunk ID (e.g. doc_page_1_chunk_1)")
    page: int | None = Field(default=None, description="Page number where the chunk originated (1-indexed)")
    text: str = Field(..., description="Canonical text content of the retrieved chunk")
    score: float = Field(default=0.0, description="Cosine similarity score (0.0 to 1.0)")
    char_count: int = Field(default=0, description="Character length of chunk text")
    doc_type: str = Field(default="research", description="Document type: weather_report or research")
    source_category: str = Field(default="general", description="Category: ipcc, environment_canada, weather_reports, etc.")
    report_date: str | None = Field(default=None, description="Report date if applicable (YYYY-MM-DD)")
    publication_date: str | None = Field(default=None, description="Publication date if applicable")
    stations: list[str] = Field(default_factory=list, description="Associated stations or locations")

    @model_validator(mode="before")
    @classmethod
    def reconcile_text_and_source(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Canonicalize text vs content
            if "text" not in values and "content" in values:
                values["text"] = values["content"]
            elif "content" not in values and "text" in values:
                values["content"] = values["text"]
            
            # Canonicalize document_name vs source
            if "document_name" not in values and "source" in values:
                values["document_name"] = values["source"]
            elif "source" not in values and "document_name" in values:
                values["source"] = values["document_name"]
            
            # Populate char count if missing
            if not values.get("char_count") and values.get("text"):
                values["char_count"] = len(values["text"])

            # Populate document_id if missing
            if not values.get("document_id") and values.get("document_name"):
                from pathlib import Path
                values["document_id"] = Path(values["document_name"]).stem

            # Sanitize stations list if it contains dicts or non-strings
            if "stations" in values and isinstance(values["stations"], list):
                sanitized_stations = []
                for s in values["stations"]:
                    if isinstance(s, dict):
                        sanitized_stations.append(s.get("city") or s.get("name") or str(s))
                    elif s is not None:
                        sanitized_stations.append(str(s))
                values["stations"] = sanitized_stations
        return values

    @property
    def content(self) -> str:
        """Compatibility property for legacy consumers expecting chunk.content."""
        return self.text


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of chunks to retrieve")
    doc_type: str | None = Field(default=None, description="Filter by doc_type: 'weather_report' or 'research'")
    station: str | None = Field(default=None, description="Filter by station name")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum cosine similarity score threshold")


class RAGSearchResponse(BaseModel):
    query: str
    total: int
    results: list[RetrievedChunk]


class RAGIngestRequest(BaseModel):
    file_path: str = Field(..., description="Absolute or relative path to PDF file")
    doc_type: str = Field(default="weather_report", description="Document type: 'weather_report' or 'research'")
    source_category: str | None = Field(default=None, description="Category folder or publisher name")
    force: bool = Field(default=False, description="Whether to re-index even if already ingested")
