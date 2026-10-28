"""Practice and Hint Ladder Tutor Models.

Tracks conversational tutoring, Hint Ladder levels (L0-L3), and independent vs
hint-assisted self-correction per SRS FR-11, FR-12, FR-13, and FR-14.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
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


class AttemptType(str, Enum):
    INDEPENDENT = "independent"
    HINT_ASSISTED = "hint_assisted"
    REVEALED = "revealed"


class PracticeSession(Base, TimestampMixin):
    """Conversational tutoring session (SRS FR-11, FR-13)."""
    __tablename__ = "practice_sessions"
    __table_args__ = {"schema": "research"}

    session_id: Mapped[uuid.UUID] = mapped_column(
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
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    active_duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tutor_prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_categories_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    turns_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idle_duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interruption_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    events: Mapped[list["PracticeEvent"]] = relationship(
        "PracticeEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class PracticeEvent(Base, TimestampMixin):
    """Granular tutor step, interruption, and learner self-correction attempt (SRS FR-12, FR-14)."""
    __tablename__ = "practice_events"
    __table_args__ = {"schema": "research"}

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.practice_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_category: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    learner_phrase: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 0, 1, 2, 3
    hint_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_type: Mapped[AttemptType] = mapped_column(
        SQLEnum(AttemptType, name="attempt_type", schema="research"),
        nullable=False,
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    transfer_phrase: Mapped[str | None] = mapped_column(Text, nullable=True)
    transfer_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    learner_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    tutor_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    transfer_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    utterance_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), default="turn_attempt", nullable=False)
    is_first_occurrence: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    elapsed_active_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship
    session: Mapped["PracticeSession"] = relationship(
        "PracticeSession",
        back_populates="events",
    )


class UtterancePattern(Base, TimestampMixin):
    """Normalized utterance pattern for longitudinal recurrence tracking (SRS FR-14)."""
    __tablename__ = "utterance_patterns"
    __table_args__ = {"schema": "research"}

    pattern_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.participants.participant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_category: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    utterance_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    canonical_phrase: Mapped[str] = mapped_column(Text, nullable=False)
    construction_type: Mapped[str] = mapped_column(String(100), default="generic_pattern", nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    first_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    last_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    resolved_independently: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
