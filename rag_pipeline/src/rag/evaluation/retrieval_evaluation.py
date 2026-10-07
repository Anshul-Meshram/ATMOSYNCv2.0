def precision_at_k(
        retrieved_ids: list[str],
        relevant_ids: list[str],
        k: int
) -> float:
    if k <= 0:
        raise ValueError("K must be greater than zero.")
    retrieved = retrieved_ids[:k]

    if not retrieved:
        return 0.0

    relevant_count = sum(
        1 for chunk_id in retrieved
        if chunk_id in relevant_ids
    )

    return relevant_count /len(retrieved)

def recall_at_k(
        retrieved_ids: list[str],
        relevant_ids: list[str],
        k: int
) -> float:
    if k <= 0:
        raise ValueError("K must be greater than zero.")
    if not relevant_ids:
        return 0.0
    retrieved = retrieved_ids[:k]

    relevant_count = sum(
        1 for chunk_id in retrieved
        if chunk_id in relevant_ids
    )
    return relevant_count / len(relevant_ids)

    
def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return 1 / rank

    return 0.0
    