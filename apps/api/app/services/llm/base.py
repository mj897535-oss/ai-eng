"""Abstract LLM Provider interface.

RESEARCH INTEGRITY & STACK RULE:
LLM access MUST sit behind this interface. No vendor name appears in business logic.
Original AI outputs are immutable and append-only.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateError:
    candidate_error: str
    suggested_correction: str
    category_code: str  # TNS, SVA, WO, AUX, ART, PREP, PRO, OTH
    explanation: str
    confidence: float
    start_char: int
    end_char: int
    start_time_ms: int | None = None
    end_time_ms: int | None = None


@dataclass(frozen=True)
class AnalysisResult:
    candidate_errors: list[CandidateError]
    model_version: str
    rubric_version: str
    raw_response: str


@dataclass(frozen=True)
class TutorResponse:
    tutor_utterance: str
    ladder_level: int  # 0: quote phrase, 1: hint question, 2: rule cue, 3: reveal
    target_category: str
    hint_question: str | None
    rule_cue: str | None
    revealed_answer: str | None
    transfer_prompt: str | None


class LLMProvider(ABC):
    @abstractmethod
    async def analyze_syntax(
        self,
        transcript: str,
        rubric_version: str,
    ) -> AnalysisResult:
        """Analyze faithful transcript against frozen rubric version."""

    @abstractmethod
    async def generate_tutor_turn(
        self,
        target_category: str,
        learner_utterance: str,
        ladder_level: int,
        prompt_version: str,
    ) -> TutorResponse:
        """Generate Hint Ladder tutor step without altering official assessment scores."""
