from src.llm.clients.gemini_client import GeminiClient
from src.llm.clients.llm_provider import LLMProvider 

def main():
    provider =GeminiClient()

    if not isinstance(provider,LLMProvider):
        raise TypeError(
            "GeminiClient does not implement LLMProvider."
        )
    response = provider.generate(
        "In one sentence, explain climate anomaly detection."
    )
    print("\nProvider verification: SUCCESS")
    print("Provider:",type(provider).__name__)
    print("Response:",response)

if __name__ == "__main__":
    main()
