"""Speech-to-Text (STT) Service Package."""

from app.services.stt.base import STTProvider, STTResponse, STTWord
from app.services.stt.factory import get_stt_provider
from app.services.stt.mock import MockSTTProvider
from app.services.stt.word_counter import count_words, tokenize_words

__all__ = [
    "MockSTTProvider",
    "STTProvider",
    "STTResponse",
    "STTWord",
    "count_words",
    "get_stt_provider",
    "tokenize_words",
]
