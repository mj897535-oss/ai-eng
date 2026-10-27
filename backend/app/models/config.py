"""Research Configuration and Versioning Models (SRS FR-20).

Enforces freezing rubrics, prompts, and scoring rules per assessment period.
"""

import uuid

from sqlalchemy import UUID, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RubricVersion(Base, TimestampMixin):
    __tablename__ = "rubric_versions"
    __table_args__ = {"schema": "research"}

    rubric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    version_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    taxonomy_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PromptVersion(Base, TimestampMixin):
    __tablename__ = "prompt_versions"
    __table_args__ = {"schema": "research"}

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    prompt_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pre_test, tutor, post_test
    version_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
