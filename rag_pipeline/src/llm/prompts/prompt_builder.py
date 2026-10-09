from src.llm.prompts.system_prompt import SYSTEM_PROMPT


def build_prompt(
    user_query: str,
    ml_context: dict | None = None,
    rag_context: dict | None = None,
) -> str:
    """
    Build the complete prompt sent to the LLM.

    The function only assembles information. It does not
    perform ML inference or RAG retrieval.
    """

    prompt_parts = [
        SYSTEM_PROMPT,
        "\n\nUSER QUERY:\n",
        user_query,
    ]

    if ml_context is not None:
        prompt_parts.extend([
            "\n\nML CONTEXT:\n",
            str(ml_context),
        ])

    if rag_context is not None:
        prompt_parts.extend([
            "\n\nRETRIEVED RAG EVIDENCE:\n",
            str(rag_context),
        ])

    return "".join(prompt_parts)