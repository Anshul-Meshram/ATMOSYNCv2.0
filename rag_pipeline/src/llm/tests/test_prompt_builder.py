from src.llm.prompts.prompt_builder import build_prompt


def main():
    user_query = "Why is Alberta experiencing unusual heat?"

    ml_context = {
        "event": {
            "type": "heatwave",
            "detected": True,
            "severity": "high",
        },
        "measurements": {
            "temperature": 31.0,
            "historical_average": 22.0,
            "deviation": 9.0,
        },
        "confidence": 0.91,
    }

    rag_context = {
        "query": user_query,
        "results": [
            {
                "id": "test_chunk_1",
                "content": "Retrieved climate evidence.",
                "source": "test_report.pdf",
                "page": 8,
                "score": 0.5077,
            }
        ],
    }

    prompt = build_prompt(
        user_query=user_query,
        ml_context=ml_context,
        rag_context=rag_context,
    )

    # Basic validation
    assert user_query in prompt
    assert "ML CONTEXT:" in prompt
    assert "RETRIEVED RAG EVIDENCE:" in prompt
    assert "heatwave" in prompt
    assert "test_report.pdf" in prompt

    print("\nPrompt builder test: SUCCESS")
    print("\nGenerated Prompt:")
    print("=" * 60)
    print(prompt)
    print("=" * 60)


if __name__ == "__main__":
    main()