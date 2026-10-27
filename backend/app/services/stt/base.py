"""Abstract Speech-To-Text interface.

RESEARCH INTEGRITY & STACK RULE:
STT access MUST sit behind this interface. No vendor name appears in business logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class WordTimestamp:
    word: str
    start_ms: int
    end_ms: int
    confidence: float


@dataclass(frozen=True)
class STTResult:
    transcript: str
    words: list[WordTimestamp]
    overall_confidence: float
    stt_version: str
    raw_payload: str  # For append-only audit trail and pilot analysis


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, filename: str) -> STTResult:
        """Transcribe audio into text with timestamps where supported."""
