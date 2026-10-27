"""Deterministic Mock STT Provider.

Allows running the entire application and automated test suites with ZERO API keys.
"""


from app.services.stt.base import STTProvider, STTResult, WordTimestamp


class MockSTTProvider(STTProvider):
    def __init__(self, default_transcript: str | None = None):
        self._default_transcript = default_transcript or "He go to college every day by bus."
        self.version = "mock-stt-v1.0"

    async def transcribe(self, audio_bytes: bytes, filename: str) -> STTResult:
        # Generate deterministic word timestamps for the transcript
        words_raw = self._default_transcript.split()
        timestamps: list[WordTimestamp] = []
        current_ms = 250

        for word in words_raw:
            clean_word = word.strip(".,!?:;")
            duration = max(200, len(clean_word) * 80)
            end_ms = current_ms + duration
            timestamps.append(
                WordTimestamp(
                    word=clean_word,
                    start_ms=current_ms,
                    end_ms=end_ms,
                    confidence=0.98,
                )
            )
            current_ms = end_ms + 120

        return STTResult(
            transcript=self._default_transcript,
            words=timestamps,
            overall_confidence=0.98,
            stt_version=self.version,
            raw_payload='{"provider": "mock", "model": "mock-stt-v1.0", "status": "success"}',
        )
