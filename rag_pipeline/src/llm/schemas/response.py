from dataclasses import dataclass, field
from typing import Any

@dataclass
class Citation:
    """Reference to a source used by the LLM."""
    source: str
    page: int| None=None
    chunk_id: str| None=None

@dataclass
class EventSummary:
    """Summary of the detected climate event."""
    event_type: str| None=None
    severity: str| None=None

@dataclass
class LLMResponse:
    """
    Standardized output contract returned by the LLM.
    This structure is provider-independent and can be consumed 
    by the Backend without knowing Gemini internals.
    """
    answer: str
    event_summary: EventSummary | None = None

    citation: list[Citation] = field(default_factory=list)

    grounded: bool = False
    insufficient_evidence: bool = False
    confidence : float| None=None