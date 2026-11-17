
from src.llm.clients.llm_provider import LLMProvider
from src.llm.context.assembler import assemble_context
from src.llm.generation.generation_service import GenerationService
from src.llm.schemas.request import LLMRequest


class MockProvider(LLMProvider):
    """Fake provider for testing without an API call."""

    def __init__(self):
        self.received_prompt = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return "Mock climate explanation generated successfully."


def main():
    provider = MockProvider()
    service = GenerationService(provider)

    request = LLMRequest(
        user_query="Why is Alberta experiencing unusual heat?",
        ml_context={
            "event": {
                "type": "heatwave",
                "severity": "high",
            }
        },
        rag_context={
            "results": [
                {
                    "content": "Test climate evidence.",
                    "source": "test_report.pdf",
                    "page": 8,
                }
            ]
        },
    )

    result = service.generate(request)

    # Verify the response
    assert result == "Mock climate explanation generated successfully."

    # Verify the provider received the assembled prompt
    assert provider.received_prompt is not None
    assert request.user_query in provider.received_prompt
    assert "ML CONTEXT:" in provider.received_prompt
    assert "RETRIEVED RAG EVIDENCE:" in provider.received_prompt

    print("Generation service test: SUCCESS")
    print("Provider received assembled prompt: YES")
    print("Mock response:", result)


if __name__ == "__main__":
    main()
