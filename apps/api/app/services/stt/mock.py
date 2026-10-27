"""Deterministic Mock STT Provider.

RESEARCH INTEGRITY RULE:
Faithful transcription: preserve disfluencies, repetitions, false starts,
and non-standard grammar exactly as spoken. NEVER normalise or correct grammar.
Transcript fixtures are deterministically keyed by audio hash.
"""

import hashlib
import json
from typing import Any

from app.services.stt.base import STTProvider, STTResponse, STTWord

# Canonical research fixtures preserving ungrammatical forms and disfluencies verbatim
FIXTURE_DISFLUENCY = "um... I think that, that he go"
FIXTURE_UNGRAMMATICAL = "He go to college every day."
FIXTURE_COMPOUND_CONTRACTIONS = "I don't think it's a state-of-the-art laboratory, um... but we attend daily."
FIXTURE_FLUENT_DAILY = "I wake up early in the morning, attend my engineering lectures, and work on computer lab projects."
FIXTURE_WEEKEND_ROUTINE = "On weekends I usually relax at home with my family, play cricket with friends, and revise my coursework."

# Fixture hash directory
FIXTURE_MAP: dict[str, str] = {
    # Direct semantic keys
    "disfluency": FIXTURE_DISFLUENCY,
    "ungrammatical": FIXTURE_UNGRAMMATICAL,
    "compound": FIXTURE_COMPOUND_CONTRACTIONS,
    "fluent": FIXTURE_FLUENT_DAILY,
    "weekend": FIXTURE_WEEKEND_ROUTINE,
    # Deterministic SHA256 hashes of fixture names
    hashlib.sha256(b"disfluency").hexdigest(): FIXTURE_DISFLUENCY,
    hashlib.sha256(b"ungrammatical").hexdigest(): FIXTURE_UNGRAMMATICAL,
    hashlib.sha256(b"compound").hexdigest(): FIXTURE_COMPOUND_CONTRACTIONS,
    hashlib.sha256(b"fluent").hexdigest(): FIXTURE_FLUENT_DAILY,
    hashlib.sha256(b"weekend").hexdigest(): FIXTURE_WEEKEND_ROUTINE,
    hashlib.sha256(b"dummy_audio_bytes").hexdigest(): "He go to college every day by bus.",
}

FIXTURE_POOL = [
    FIXTURE_UNGRAMMATICAL,
    FIXTURE_DISFLUENCY,
    FIXTURE_COMPOUND_CONTRACTIONS,
    FIXTURE_FLUENT_DAILY,
    FIXTURE_WEEKEND_ROUTINE,
]


class MockSTTProvider(STTProvider):
    """Deterministic, key-addressed mock STT provider for tests and local development."""

    def __init__(self, default_transcript: str | None = None, model_version: str = "mock-stt-v1.0"):
        self.model_version = model_version
        self._custom_default = default_transcript is not None
        self.default_transcript = default_transcript or "He go to college every day by bus."

    async def transcribe(
        self,
        audio_ref: str | bytes,
        language_hint: str = "en",
        options: dict[str, Any] | None = None,
    ) -> STTResponse:
        """Deterministically look up or generate transcript from audio hash.

        FAITHFUL: Preserves repetitions, stutters, and ungrammatical forms verbatim.
        """
        options = options or {}
        # 1. Determine key/hash from options or audio_ref
        key_candidate = options.get("checksum") or options.get("audio_hash")
        if not key_candidate:
            if isinstance(audio_ref, bytes):
                key_candidate = hashlib.sha256(audio_ref).hexdigest()
            elif isinstance(audio_ref, str):
                key_candidate = audio_ref
            else:
                key_candidate = "default"

        key_candidate_str = str(key_candidate)

        # 2. Check direct fixture map
        if self._custom_default:
            chosen_transcript = self.default_transcript
        elif key_candidate_str in FIXTURE_MAP:
            chosen_transcript = FIXTURE_MAP[key_candidate_str]
        elif options.get("fixture"):
            chosen_transcript = FIXTURE_MAP.get(options["fixture"], self.default_transcript)
        else:
            # Deterministic selection based on sha256 hash modulo
            digest = hashlib.sha256(key_candidate_str.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % len(FIXTURE_POOL)
            chosen_transcript = FIXTURE_POOL[idx]

        # 3. Generate faithful word timestamps and confidences
        tokens = chosen_transcript.split()
        words: list[STTWord] = []
        current_time = 0.5  # Start at 0.5s

        total_confidence = 0.0
        for token in tokens:
            clean_word = token.strip(".,!?:;\"'")
            duration = max(0.25, len(clean_word) * 0.08)
            end_time = round(current_time + duration, 3)

            # Disfluencies and fillers have slightly lower confidence per acoustic models
            is_filler = clean_word.lower() in {"um", "uh", "ah"}
            conf = 0.88 if is_filler else 0.98

            words.append(
                STTWord(
                    word=token,  # Keep token with boundary marks
                    start=round(current_time, 3),
                    end=end_time,
                    confidence=conf,
                )
            )
            total_confidence += conf
            current_time = round(end_time + 0.12, 3)

        overall_conf = round(total_confidence / max(1, len(words)), 3)

        # 4. Mock raw provider response payload
        raw_payload = {
            "provider": "mock",
            "model_version": self.model_version,
            "language": language_hint,
            "audio_ref": str(audio_ref) if isinstance(audio_ref, str) else "<bytes>",
            "result": {
                "text": chosen_transcript,
                "words": [
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "confidence": w.confidence,
                    }
                    for w in words
                ],
            },
        }

        return STTResponse(
            text=chosen_transcript,
            words=words,
            provider="mock",
            model_version=self.model_version,
            raw_response_ref=json.dumps(raw_payload),
            overall_confidence=overall_conf,
        )
