"""Abstract LLM Provider interface & Structured Output Schemas.

RESEARCH INTEGRITY RULE:
LLM access MUST sit behind this interface. Zero vendor names appear in business logic.
Structured output schemas are strictly validated via Pydantic.
Original AI outputs are immutable and append-only.
"""

from abc import ABC, abstractmethod
from typing import Any, Literal
from pydantic import BaseModel, Field


SyntacticCategoryCode = Literal[
    "TNS",  # Tense & Aspect
    "SVA",  # Subject-Verb Agreement
    "WO",   # Word Order
    "AUX",  # Auxiliary / Modal Usage
    "ART",  # Determiners & Articles
    "PREP", # Prepositions
    "PRO",  # Pronoun Reference & Resumptive Pronouns
    "OTH",  # Other Agreed Syntactic Codes
]

AnnotationFlag = Literal[
    "candidate_error",      # Definite candidate syntactic deviation
    "uncertain",            # Inconclusive evidence or ambiguous audio
    "transcription_related",# Likely STT artifact rather than speaker error
    "acceptable_variation", # Acceptable regional standard (e.g. Indian English stative progressive)
    "needs_human_review",   # Routed for mandatory human reviewer adjudication
]


class AnnotationItem(BaseModel):
    """Pydantic schema for individual syntactic candidate deviation."""
    span_text: str = Field(..., description="Exact substring from transcript")
    char_start: int = Field(..., ge=0, description="0-indexed start character offset in transcript")
    char_end: int = Field(..., gt=0, description="0-indexed end character offset in transcript")
    time_start: float | None = Field(None, ge=0.0, description="Audio timestamp in seconds")
    time_end: float | None = Field(None, ge=0.0, description="Audio timestamp in seconds")
    category_code: SyntacticCategoryCode = Field(..., description="Rubric category taxonomy code")
    proposed_correction: str = Field(..., description="Syntactically standard replacement")
    explanation: str = Field(..., max_length=500, description="Rule statement in max 2 sentences")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    flag: AnnotationFlag = Field(default="candidate_error", description="Research adjudication flag")

    @property
    def candidate_error(self) -> str:
        return self.span_text

    @property
    def suggested_correction(self) -> str:
        return self.proposed_correction

    @property
    def start_char(self) -> int:
        return self.char_start

    @property
    def end_char(self) -> int:
        return self.char_end


class AssessorOutput(BaseModel):
    """Structured output schema returned by the pre/post-test syntactic assessor."""
    annotations: list[AnnotationItem] = Field(default_factory=list)
    model_notes: str | None = Field(None, description="Global model context or acoustic notes")
    model_version: str
    rubric_version: str
    prompt_version: str
    raw_response: str

    @property
    def candidate_errors(self) -> list[AnnotationItem]:
        return self.annotations


class TutorResponse(BaseModel):
    """Tutor Hint Ladder turn response."""
    tutor_utterance: str
    ladder_level: int
    target_category: str
    hint_question: str | None = None
    rule_cue: str | None = None
    revealed_answer: str | None = None
    transfer_prompt: str | None = None


class LLMProvider(ABC):
    """Abstract interface for all Large Language Model adapters."""

    @abstractmethod
    async def analyze_syntax(
        self,
        transcript: str,
        rubric_version: str = "v1.0-jam-phd",
        prompt_version: str = "v1.0-assessor",
        words_json: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AssessorOutput:
        """Perform neutral, structured syntactic error assessment on faithful transcript."""
        pass

    @abstractmethod
    async def generate_tutor_turn(
        self,
        target_category: str,
        learner_utterance: str,
        ladder_level: int,
        prompt_version: str,
    ) -> TutorResponse:
        """Generate Hint Ladder tutor step without altering official assessment scores."""
        pass
