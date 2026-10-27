"""Tests for Mock STT Provider.

Validates zero-API key execution, deterministic timestamps, and interface adherence.
"""

import pytest

from app.services.stt.mock import MockSTTProvider


@pytest.mark.asyncio
async def test_mock_stt_transcription():
    provider = MockSTTProvider()
    result = await provider.transcribe(b"dummy_audio_bytes", "test.wav")

    assert result.transcript == "He go to college every day by bus."
    assert len(result.words) == 8
    assert result.stt_version == "mock-stt-v1.0"
    assert result.overall_confidence > 0.9

    # Verify timestamps are sequential and non-overlapping
    last_end = 0
    for word_info in result.words:
        assert word_info.start_ms >= last_end
        assert word_info.end_ms > word_info.start_ms
        last_end = word_info.end_ms


@pytest.mark.asyncio
async def test_mock_stt_custom_transcript():
    custom_text = "I have seen him yesterday at the library."
    provider = MockSTTProvider(default_transcript=custom_text)
    result = await provider.transcribe(b"dummy_bytes", "custom.wav")

    assert result.transcript == custom_text
    assert len(result.words) == 8
