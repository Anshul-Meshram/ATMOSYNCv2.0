def has_usable_evidence(rag_context: dict | None) -> bool:
    """
    Return True only when the RAG context contains at least
    one result with non-empty evidence text.
    """

    if not isinstance(rag_context, dict):
        return False

    results = rag_context.get("results")

    # Reject missing, invalid, or empty results
    if not isinstance(results, list) or len(results) == 0:
        return False

    for result in results:
        if not isinstance(result, dict):
            continue

        content = result.get("content") or result.get("text")

        if isinstance(content, str) and content.strip():
            return True

    return False
