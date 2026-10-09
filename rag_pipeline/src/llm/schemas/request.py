from dataclasses import dataclass
from typing import Any


@dataclass
class LLMRequest:
    """
    Standardized input contract for the LLM.

    The LLM receives prepared information from other modules
    rather than depending on their internal implementation.
    """

    user_query: str
    ml_context: dict[str, Any] | None = None
    rag_context: dict[str, Any] | None = None