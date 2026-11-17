from src.llm.context.assembler import assemble_context
from src.llm.schemas.request import LLMRequest


def main():
    # 1. Test basic prompt assembly
    request = LLMRequest(
        user_query="Why is Alberta experiencing unusual heat?",
        ml_context={
            "event": {"type": "heatwave", "severity": "high"},
            "measurements": {"temperature": 31.0, "historical_average": 22.0},
        },
        rag_context={
            "query": "Why is Alberta experiencing unusual heat?",
            "results": [
                {
                    "content": "Canadian heatwaves often associate with high-pressure ridges.",
                    "source": "climate_report.pdf",
                    "page": 5,
                }
            ],
        },
    )

    prompt = assemble_context(request)

    assert isinstance(prompt, str), "Prompt should be a string"
    assert "Why is Alberta experiencing unusual heat?" in prompt
    assert "ML CONTEXT:" in prompt
    assert "RETRIEVED RAG EVIDENCE:" in prompt
    assert "climate_report.pdf" in prompt

    # 2. Test assembly with only user_query
    minimal_request = LLMRequest(user_query="General climate trend in Canada.")
    minimal_prompt = assemble_context(minimal_request)
    assert "General climate trend in Canada." in minimal_prompt
    assert "ML CONTEXT:" not in minimal_prompt
    assert "RETRIEVED RAG EVIDENCE:" not in minimal_prompt

    print("Context assembler test: SUCCESS")


if __name__ == "__main__":
    main()
