"""LLM Provider Factory.

RESEARCH INTEGRITY RULE:
Domain code only requests an LLMProvider from this factory.
Zero vendor names appear in business logic.
Selected strictly by settings.LLM_PROVIDER.
"""

from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.gemini_adapter import GeminiLLMProvider
from app.services.llm.mock import MockLLMProvider


def get_llm_provider(provider_override: str | None = None) -> LLMProvider:
    """Return the configured LLMProvider instance."""
    name = (provider_override or settings.LLM_PROVIDER or "mock").lower()

    if name == "mock":
        return MockLLMProvider()
    elif name in {"gemini", "google"}:
        return GeminiLLMProvider()
    else:
        raise ValueError(
            f"Unsupported LLM provider: '{name}'. Supported providers: 'mock', 'gemini'."
        )
