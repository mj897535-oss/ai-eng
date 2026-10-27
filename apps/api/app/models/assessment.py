"""Assessment and Error Annotation Models.

RESEARCH INTEGRITY RULE:
Original AI outputs, transcripts, and baseline assessments are strictly APPEND-ONLY.
Reviewer decisions are stored in a separate table that references the original candidate,
ensuring model outputs are never overwritten or mutated.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.research import Participant


class AssessmentType(str, Enum):
    PRE = "pre"
    POST = "post"


class ReviewDecisionType(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    UNCERTAIN = "uncertain"


class AssessmentTask(Base, TimestampMixin):
    """Standardized task instructions and topic pool (SRS FR-05)."""
    __tablename__ = "assessment_tasks"
    __table_args__ = {"schema": "research"}

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    prep_time_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    equivalence_group: Mapped[str] = mapped_column(String(100), default="pair_daily_routine", nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), default="any", nullable=False)  # pre, post, any
    rubric_version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Assessment(Base, TimestampMixin):
    """Immutable assessment record (SRS FR-04, FR-06). APPEND-ONLY."""
    __tablename__ = "assessments"
    __table_args__ = {"schema": "research"}

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.participants.participant_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.assessment_tasks.task_id", ondelete="RESTRICT"),
        nullable=False,
    )
    assessment_type: Mapped[AssessmentType] = mapped_column(
        SQLEnum(AssessmentType, name="assessment_type", schema="research"),
        nullable=False,
        index=True,
    )
    audio_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued_for_transcription", nullable=False, index=True)
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retake_authorized_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    retake_authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retake_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    error_annotations: Mapped[list["ErrorAnnotation"]] = relationship(
        "ErrorAnnotation",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list["ReviewerAssignment"]] = relationship(
        "ReviewerAssignment",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    participant: Mapped["Participant"] = relationship(
        "Participant",
        foreign_keys=[participant_id],
    )


class ErrorAnnotation(Base, TimestampMixin):
    """Candidate syntactic deviation identified by AI (SRS FR-07, FR-08). APPEND-ONLY."""
    __tablename__ = "error_annotations"
    __table_args__ = {"schema": "research"}

    annotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.assessments.assessment_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    start_char: Mapped[int] = mapped_column(Integer, nullable=False)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_error: Mapped[str] = mapped_column(String(255), nullable=False)
    suggested_correction: Mapped[str] = mapped_column(String(255), nullable=False)
    category_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    ai_status: Mapped[str] = mapped_column(String(50), default="candidate", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationship
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="error_annotations",
    )
    reviewer_decisions: Mapped[list["ReviewerDecision"]] = relationship(
        "ReviewerDecision",
        back_populates="annotation",
        cascade="all, delete-orphan",
    )


class ReviewerDecision(Base, TimestampMixin):
    """Separate reviewer decision referencing candidate error (SRS FR-10)."""
    __tablename__ = "reviewer_decisions"
    __table_args__ = {"schema": "research"}

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    annotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.error_annotations.annotation_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[ReviewDecisionType] = mapped_column(
        SQLEnum(ReviewDecisionType, name="review_decision_type", schema="research"),
        nullable=False,
    )
    edited_category: Mapped[str | None] = mapped_column(String(10), nullable=True)
    edited_correction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    annotation: Mapped["ErrorAnnotation"] = relationship(
        "ErrorAnnotation",
        back_populates="reviewer_decisions",
    )


class ReviewerAssignment(Base, TimestampMixin):
    """Assignment of an assessment to a specific reviewer (SRS FR-10, P3 row-level ownership)."""
    __tablename__ = "reviewer_assignments"
    __table_args__ = {"schema": "research"}

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.assessments.assessment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="assignments",
    )
