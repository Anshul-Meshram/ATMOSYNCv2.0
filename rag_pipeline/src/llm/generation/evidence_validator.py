from __future__ import annotations

from typing import Any


def has_usable_evidence(rag_context: dict | None) -> bool:
    """
    Return True only when the RAG context contains at least
    one result with non-empty evidence text.
    """
    if not isinstance(rag_context, dict):
        return False

    results = rag_context.get("results")
    if not isinstance(results, list) or len(results) == 0:
        return False

    for result in results:
        if isinstance(result, dict):
            content = result.get("text") or result.get("content")
            if isinstance(content, str) and content.strip():
                return True
        elif hasattr(result, "text"):
            if result.text and result.text.strip():
                return True

    return False


def validate_evidence_sufficiency(
    rag_context: dict | None,
    min_score: float = 0.35,
) -> tuple[bool, float]:
    """
    Evaluate evidence sufficiency based on non-emptiness and cosine similarity threshold.
    
    Returns:
        (is_sufficient: bool, best_score: float)
    """
    if not has_usable_evidence(rag_context):
        return False, 0.0

    results = rag_context.get("results", [])
    scores = []
    for r in results:
        score = getattr(r, "score", None) if hasattr(r, "score") else (r.get("score") if isinstance(r, dict) else None)
        if score is not None:
            scores.append(float(score))

    best_score = max(scores, default=0.0)
    return best_score >= min_score, best_score
