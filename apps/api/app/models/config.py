"""Research Configuration and Versioning Models (SRS FR-05, FR-08, FR-20).

NON-NEGOTIABLE RULE 3:
Rubrics, prompts, scoring rules and topic banks are versioned and FROZEN per assessment period.
Every assessment stores rubric_version, prompt_version, model_version, stt_version.
Once frozen, records are immutable and enforced at the database level.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import UUID, Boolean, DateTime, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LifecycleState(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    FROZEN = "frozen"


class PromptRole(str, Enum):
    PRE_TEST_ASSESSOR = "pre_test_assessor"
    TUTOR = "tutor"
    POST_TEST_ASSESSOR = "post_test_assessor"


class RubricVersion(Base, TimestampMixin):
    """Versioned syntax assessment rubric taxonomy and counting rules."""
    __tablename__ = "rubric_versions"
    __table_args__ = {"schema": "research"}

    rubric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    version_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LifecycleState] = mapped_column(
        SQLEnum(LifecycleState, name="lifecycle_state", schema="research"),
        default=LifecycleState.FROZEN,
        nullable=False,
    )
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Serialized JSON array of 8 core categories + any agreed expanded categories
    categories_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Explicit counting rules: multiple errors in one sentence, assessable units, regional variation
    counting_rules: Mapped[str] = mapped_column(Text, nullable=False)

    # Pure word-counting specification: contractions, compounds, fillers
    word_counting_rules: Mapped[str] = mapped_column(Text, nullable=False)

    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class PromptVersion(Base, TimestampMixin):
    """Versioned system and tutor prompt templates for each AI role."""
    __tablename__ = "prompt_versions"
    __table_args__ = {"schema": "research"}

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    prompt_role: Mapped[PromptRole] = mapped_column(
        SQLEnum(PromptRole, name="prompt_role", schema="research"),
        nullable=False,
    )
    version_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema_version: Mapped[str] = mapped_column(String(50), default="json-schema-v1.0", nullable=False)
    output_schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LifecycleState] = mapped_column(
        SQLEnum(LifecycleState, name="lifecycle_state", schema="research"),
        default=LifecycleState.FROZEN,
        nullable=False,
    )
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class AssessmentPeriod(Base, TimestampMixin):
    """Configuration binding active rubric, prompt, and task pool for a cohort."""
    __tablename__ = "assessment_periods"
    __table_args__ = {"schema": "research"}

    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    period_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    rubric_version_code: Mapped[str] = mapped_column(String(50), nullable=False)
    pre_prompt_version_code: Mapped[str] = mapped_column(String(50), nullable=False)
    tutor_prompt_version_code: Mapped[str] = mapped_column(String(50), nullable=False)
    post_prompt_version_code: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[LifecycleState] = mapped_column(
        SQLEnum(LifecycleState, name="lifecycle_state", schema="research"),
        default=LifecycleState.FROZEN,
        nullable=False,
    )
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
