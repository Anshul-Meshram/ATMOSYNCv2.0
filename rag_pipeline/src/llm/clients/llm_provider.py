from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger("llm.provider")


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a text response from the LLM.

        Args:
            prompt: Input prompt for the language model.

        Returns:
            Generated text response.
        """
        pass


def get_llm_provider() -> LLMProvider:
    """
    Provider factory supporting Gemini (live) and Mock (offline/testing) providers.
    Controlled by LLM_PROVIDER ('gemini' | 'mock') or key presence.
    """
    provider_pref = os.getenv("LLM_PROVIDER", "").strip().lower()

    if provider_pref == "mock":
        from src.llm.clients.mock_provider import MockProvider
        logger.info("Using configured MockProvider for LLM generation.")
        return MockProvider()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        from src.llm.clients.mock_provider import MockProvider
        logger.warning("GEMINI_API_KEY is not configured. Falling back to MockProvider.")
        return MockProvider()

    try:
        from src.llm.clients.gemini_client import GeminiClient
        client = GeminiClient()
        logger.info("Using GeminiClient with models: %s", client.models)
        return client
    except Exception as exc:
        from src.llm.clients.mock_provider import MockProvider
        logger.warning("Failed to initialize GeminiClient: %s. Falling back to MockProvider.", exc)
        return MockProvider()
