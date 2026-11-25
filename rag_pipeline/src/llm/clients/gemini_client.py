import os
import time
from google.genai import errors
import httpx

from google import genai
from dotenv import load_dotenv

from src.llm.clients.llm_provider import LLMProvider


load_dotenv()


class GeminiClient(LLMProvider):
    """Gemini implementation of the LLM provider."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        default_model = "gemini-3.5-flash-lite"
        configured_model = (os.getenv("GEMINI_MODEL") or "").strip()
        self.primary_model = configured_model or default_model

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=api_key)
        
        candidates = [self.primary_model, "gemini-3.5-flash-lite", "gemini-3.8-flash"]
        self.models = []
        for m in candidates:
            if m and m not in self.models:
                self.models.append(m)

    def generate(self, prompt: str) -> str:
        """Generate a response using Gemini with controlled retries and fallback models."""
        last_error = None

        for model_name in self.models:
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )

                    if not response.text:
                        raise RuntimeError(f"Gemini model {model_name} returned an empty response.")

                    return response.text

                except (errors.APIError, httpx.HTTPError) as exc:
                    last_error = exc
                    status_code = getattr(exc, "code", getattr(exc, "status_code", None))

                    # If 404 (model retired/not found) or 503 (high demand), switch to fallback model immediately
                    if status_code in (404, 503):
                        print(f"Model {model_name} unavailable ({status_code}). Trying fallback model...")
                        break

                    if status_code in (429, 500, 502, 504) and attempt < max_attempts - 1:
                        delay = 2 ** attempt
                        print(f"Gemini {model_name} temporarily unavailable (HTTP {status_code}). Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    elif attempt < max_attempts - 1:
                        time.sleep(1)
                        continue
                    else:
                        break

        raise RuntimeError(f"Gemini generation failed: {last_error}")
