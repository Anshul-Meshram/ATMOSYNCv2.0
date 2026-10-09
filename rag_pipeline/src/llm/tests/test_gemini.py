from src.llm.clients.gemini_client import GeminiClient

def main():
    client = GeminiClient()
    response = client.generate(
        "interesting hollywood movies release in year 2026."
    )
    print("\nGemini Response:")
    print(response)
if __name__ == "__main__":
    main()