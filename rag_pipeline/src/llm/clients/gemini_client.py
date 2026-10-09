import os

from google import genai
from dotenv import load_dotenv

from src.llm.clients.llm_provider import LLMProvider


load_dotenv()


class GeminiClient(LLMProvider):
    """Gemini implementation of the LLM provider."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        """Generate a response using Gemini."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return response.text