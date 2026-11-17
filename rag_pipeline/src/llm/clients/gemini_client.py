import os
import time
from google.genai import errors

from google import genai
from dotenv import load_dotenv

from src.llm.clients.llm_provider import LLMProvider


load_dotenv()


class GeminiClient(LLMProvider):
    """Gemini implementation of the LLM provider."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        default_model = "gemini-2.5-flash"
        configured_model = (os.getenv("GEMINI_MODEL") or "").strip()
        model = configured_model or default_model

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        normalized_model = model.lower()
        if not normalized_model.startswith("gemini-2.") and not normalized_model.startswith("gemini-1."):
            model = default_model

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        """Generate a response using Gemini with controlled retries."""

        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )

                if not response.text:
                    raise RuntimeError("Gemini returned an empty response.")

                return response.text

            except errors.APIError as exc:
                status_code = getattr(exc, "code", None)

                # Retry only temporary server/rate-limit errors.
                if status_code not in (429, 500, 502, 503, 504):
                    raise

                if attempt == max_attempts - 1:
                    raise

                delay = 2 ** attempt
                print(
                    f"Gemini temporarily unavailable "
                    f"(HTTP {status_code}). "
                    f"Retrying in {delay} seconds..."
                )
                time.sleep(delay)

        raise RuntimeError("Gemini generation failed after retries.")
