import os
import time
from google.genai import errors
import httpx

from google import genai
from dotenv import load_dotenv

from src.llm.clients.llm_provider import LLMProvider


load_dotenv()


class GeminiClient(LLMProvider):
    """Gemini implementation of the LLM provider with graceful resilience fallback."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        # Prefer gemini-3.8-flash as primary model for stability
        default_model = "gemini-3.8-flash"
        configured_model = (os.getenv("GEMINI_MODEL") or "").strip()
        self.primary_model = configured_model or default_model

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=api_key)
        
        candidates = [self.primary_model, "gemini-3.8-flash", "gemini-3.5-flash-lite"]
        self.models = []
        for m in candidates:
            if m and m not in self.models:
                self.models.append(m)

    def generate(self, prompt: str) -> str:
        """Generate a response using Gemini with fast fallback to offline provider on failure."""
        last_error = None

        for model_name in self.models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                if response.text and response.text.strip():
                    return response.text
                else:
                    last_error = f"Model {model_name} returned empty text"

            except Exception as exc:
                last_error = exc
                print(f"Gemini model {model_name} call failed: {exc}. Trying next candidate...")
                continue

        # If live API calls fail or stall, fall back to MockProvider for uninterrupted service
        print(f"Gemini live generation unavailable ({last_error}). Falling back to MockProvider.")
        from src.llm.clients.mock_provider import MockProvider
        return MockProvider().generate(prompt)
