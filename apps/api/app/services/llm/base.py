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
    """Tutor Hint Ladder turn response (SRS §7, §8, FR-11, FR-12, Signature Feature C)."""
    reply_text: str = Field(..., description="Conversational tutor response text")
    target_category: str = Field(..., description="Target syntactic error category, e.g. SVA, TNS")
    learner_phrase_quoted: str | None = Field(None, description="Verbatim quote of learner's erroneous phrase")
    hint_level: int = Field(default=0, ge=0, le=3, description="Hint Ladder level 0 to 3")
    expects_attempt: bool = Field(default=True, description="Whether tutor expects a learner attempt next")
    transfer_prompt: str | None = Field(None, description="Prompt for a brand-new sentence on L3 transfer check")
    is_off_topic: bool = Field(default=False, description="Whether learner input was off-topic or safety violation")
    safety_refusal: bool = Field(default=False, description="Whether safety guardrails triggered polite refusal")
    prompt_version: str = Field(default="v1.0-tutor-ladder", description="Frozen prompt version ID")

    # Legacy fields
    hint_question: str | None = None
    rule_cue: str | None = None
    revealed_answer: str | None = None

    def __init__(self, **data: Any):
        if "tutor_utterance" in data and "reply_text" not in data:
            data["reply_text"] = data.pop("tutor_utterance")
        if "ladder_level" in data and "hint_level" not in data:
            data["hint_level"] = data.pop("ladder_level")
        super().__init__(**data)

    @property
    def tutor_utterance(self) -> str:
        return self.reply_text

    @property
    def ladder_level(self) -> int:
        return self.hint_level


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
        prompt_version: str = "v1.0-tutor-ladder",
        learner_phrase_quoted: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> TutorResponse:
        """Generate Hint Ladder tutor step without altering official assessment scores."""
        pass
