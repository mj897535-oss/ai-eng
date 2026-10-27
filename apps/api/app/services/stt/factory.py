"""STT Provider Factory.

RESEARCH INTEGRITY RULE:
Domain code only requests an STTProvider from this factory.
No vendor names appear in business logic. Selected solely by configuration.
"""

from app.core.config import settings
from app.services.stt.base import STTProvider
from app.services.stt.mock import MockSTTProvider
from app.services.stt.whisper_adapter import WhisperSTTProvider


def get_stt_provider(provider_override: str | None = None) -> STTProvider:
    """Return the configured STTProvider instance."""
    provider_name = (provider_override or settings.STT_PROVIDER or "mock").lower()

    if provider_name == "mock":
        return MockSTTProvider()
    elif provider_name in {"whisper", "openai"}:
        return WhisperSTTProvider()
    else:
        raise ValueError(
            f"Unsupported STT provider: '{provider_name}'. Supported providers: 'mock', 'whisper'."
        )
