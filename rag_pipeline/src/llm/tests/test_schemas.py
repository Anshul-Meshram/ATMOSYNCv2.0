from dataclasses import asdict

from src.llm.schemas.request import LLMRequest
from src.llm.schemas.response import (
    Citation,
    EventSummary,
    LLMResponse,
)

def main():
    # Test request contract
    request = LLMRequest(
        user_query="Why is Alberta experiencing unusual heat?",
        ml_context={
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
        },
        rag_context={
            "query": "Why is Alberta experiencing unusual heat?",
            "results": [
                {
                    "id": "test_chunk_1",
                    "content": "Retrieved climate evidence.",
                    "source": "test_report.pdf",
                    "page": 8,
                    "score": 0.5077,
                }
            ],
        },
    )

    #Test response contract
    response = LLMResponse(
        answer = "The available evidence indicates unusually high temperatures.",
        event_summary = EventSummary(
            event_type = "heatwave",
            severity = "high",
        ),
        citation = [
            Citation(
                source = "test_report.pdf",
                page = 8,
                chunk_id = "test_chunk_1",
            )
        ],
        grounded = True,
        insufficient_evidence = False,
    )
    # Convert dataclasses to dictionaries
    request_data = asdict(request)
    response_data = asdict(response)

    print("\nSchema validation: SUCCESS")
    print("\nLLM Request:")
    print(request_data)
    print("\nLLM Response:")
    print(response_data)

if __name__ == "__main__":
    main()
