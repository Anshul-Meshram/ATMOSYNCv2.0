from src.llm.schemas.request import LLMRequest
from src.llm.prompts.prompt_builder import build_prompt

def assemble_context(request: LLMRequest)-> str:
    """
    Validate an LLM request and assemble the final prompt.

    This function does not perform ML inference, RAG retrieval or LLM generation.
    """
    #Validate tne request object
    if not isinstance(request, LLMRequest):
        raise TypeError("request must be an LLMRequest instance.")
    
    # Validate optional context query
    if not isinstance(request.user_query, str) or  not request.user_query.strip():
        raise ValueError("user_query must be a non-empty string.")

    #Validate optional context types
    if request.ml_context is not None and not isinstance(request.ml_context,dict):
        raise TypeError("ml_context must be a dictionary or None.")

    if request.rag_context is not None and not isinstance (request.rag_context, dict):
        raise TypeError("rag_context must be a dictionary or None.")
    return build_prompt(
        user_query = request.user_query,
        ml_context = request.ml_context,
        rag_context = request.rag_context,
    )
