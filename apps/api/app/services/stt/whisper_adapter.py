"""Whisper STT Adapter.

RESEARCH INTEGRITY RULE:
Implements STTProvider interface with zero vendor leak into core domain logic.
Configured for verbatim, faithful transcription without normalizing grammar or disfluencies.
"""

import json
import logging
import os
from typing import Any

import httpx

from app.services.stt.base import STTProvider, STTResponse, STTWord

logger = logging.getLogger(__name__)


class WhisperSTTProvider(STTProvider):
    """Real STT adapter using OpenAI Whisper API or compatible local endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "whisper-1",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("STT_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def transcribe(
        self,
        audio_ref: str | bytes,
        language_hint: str = "en",
        options: dict[str, Any] | None = None,
    ) -> STTResponse:
        """Call Whisper endpoint for word-level faithful speech-to-text."""
        if not self.api_key:
            raise RuntimeError(
                "STT provider 'whisper' requires OPENAI_API_KEY or STT_API_KEY in environment or settings."
            )

        options = options or {}
        audio_bytes = options.get("audio_bytes")
        if not audio_bytes and isinstance(audio_ref, bytes):
            audio_bytes = audio_ref

        if not audio_bytes:
            raise ValueError("Whisper transcription requires raw audio bytes.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "model": self.model,
            "language": language_hint,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word",
            "temperature": "0.0",  # Deterministic faithful output
        }
        files = {
            "file": ("recording.webm", audio_bytes, "audio/webm"),
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers=headers,
                data=data,
                files=files,
            )
            if resp.status_code != 200:
                logger.error("Whisper API error: %d %s", resp.status_code, resp.text)
                raise RuntimeError(f"STT Whisper upstream error: {resp.status_code} - {resp.text}")

            result = resp.json()

        text = result.get("text", "").strip()
        words_data = result.get("words", [])
        words: list[STTWord] = []
        total_conf = 0.0

        for item in words_data:
            word_str = item.get("word", "")
            start = float(item.get("start", 0.0))
            end = float(item.get("end", 0.0))
            # Whisper verbose_json doesn't always provide word-level confidence, default to 0.95
            conf = float(item.get("confidence", 0.95))
            words.append(STTWord(word=word_str, start=start, end=end, confidence=conf))
            total_conf += conf

        overall_conf = round(total_conf / max(1, len(words)), 3) if words else 0.95

        return STTResponse(
            text=text,
            words=words,
            provider="whisper",
            model_version=self.model,
            raw_response_ref=json.dumps(result),
            overall_confidence=overall_conf,
        )
