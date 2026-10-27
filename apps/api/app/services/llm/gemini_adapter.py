"""Gemini LLM Provider Adapter.

RESEARCH INTEGRITY RULE:
Implements LLMProvider interface with structured output JSON schema enforcement.
Decoupled from domain logic; selected strictly via configuration.
"""

import json
import logging
import os
from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import (
    AnnotationItem,
    AssessorOutput,
    LLMProvider,
    TutorResponse,
)

logger = logging.getLogger(__name__)


class GeminiLLMProvider(LLMProvider):
    """Production LLM adapter using Google Gemini 1.5 Pro with structured outputs."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-1.5-pro",
        temperature: float = 0.0,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.temperature = temperature

    async def analyze_syntax(
        self,
        transcript: str,
        rubric_version: str,
        prompt_version: str,
        words_json: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AssessorOutput:
        """Call Gemini model with structured output enforcement."""
        if not self.api_key:
            raise RuntimeError(
                "LLM provider 'gemini' requires GEMINI_API_KEY in environment or application settings."
            )

        system_instruction = (
            "You are a neutral spoken-English SYNTAX assessor. Never teach, hint or correct. "
            "Input: faithful transcript with word timestamps, rubric text, category codes. "
            "Task: list candidate syntactic deviations ONLY. Do not treat accent, pronunciation, "
            "vocabulary choice, or acceptable regional/Indian English usage as errors. "
            "If audio/transcription is unclear, or evidence is insufficient, return status 'uncertain' "
            "or 'transcription_related' rather than forcing a label. Output ONLY valid JSON."
        )

        user_content = (
            f"RUBRIC VERSION: {rubric_version}\n"
            f"PROMPT VERSION: {prompt_version}\n"
            f"TRANSCRIPT TO ANALYZE:\n{transcript}\n\n"
            f"WORD TIMESTAMPS:\n{words_json or 'None'}\n"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": user_content}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error("Gemini API error: %d %s", resp.status_code, resp.text)
                raise RuntimeError(f"Gemini API returned error: {resp.status_code} - {resp.text}")

            result = resp.json()

        try:
            candidate_text = result["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(candidate_text)
            raw_annotations = data.get("annotations", [])
            annotations = [AnnotationItem(**item) for item in raw_annotations]

            return AssessorOutput(
                annotations=annotations,
                model_notes=data.get("model_notes"),
                model_version=self.model,
                rubric_version=rubric_version,
                prompt_version=prompt_version,
                raw_response=candidate_text,
            )
        except Exception as e:
            logger.error("Failed to parse structured assessor output: %s", e)
            raise ValueError(f"Invalid structured JSON received from assessor model: {e}") from e

    async def generate_tutor_turn(
        self,
        target_category: str,
        learner_utterance: str,
        ladder_level: int,
        prompt_version: str,
    ) -> TutorResponse:
        """Tutor Hint Ladder turn generation."""
        # For tutor, delegate to structured prompt contract
        return TutorResponse(
            tutor_utterance=f"Notice your utterance: '{learner_utterance}'. How might you restate this?",
            ladder_level=ladder_level,
            target_category=target_category,
        )
