"""Abstract Speech-To-Text interface.

RESEARCH INTEGRITY & STACK RULE:
STT access MUST sit behind this interface. No vendor name appears in business logic.
Selected strictly by config (settings.STT_PROVIDER).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class STTWord:
    word: str
    start: float  # seconds
    end: float    # seconds
    confidence: float

    @property
    def start_ms(self) -> int:
        return int(self.start * 1000)

    @property
    def end_ms(self) -> int:
        return int(self.end * 1000)


@dataclass(frozen=True)
class STTResponse:
    text: str
    words: list[STTWord]
    provider: str
    model_version: str
    raw_response_ref: str | dict[str, Any] | None = None
    overall_confidence: float = 1.0

    @property
    def transcript(self) -> str:
        return self.text

    @property
    def stt_version(self) -> str:
        return self.model_version


class STTProvider(ABC):
    """Abstract interface for all Speech-To-Text adapters."""

    @abstractmethod
    async def transcribe(
        self,
        audio_ref: str | bytes,
        language_hint: str = "en",
        options: dict[str, Any] | None = None,
    ) -> STTResponse:
        """Transcribe audio into faithful verbatim text with word timestamps.

        Args:
            audio_ref: Storage key, audio bytes, or audio file path.
            language_hint: Expected audio language (default 'en').
            options: Optional provider options (audio_duration, checksum, etc.).

        Returns:
            STTResponse containing text, words list, provider, model_version, raw_response_ref.
        """
        pass
