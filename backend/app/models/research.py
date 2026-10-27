"""Research Participant Model.

RESEARCH INTEGRITY & PRIVACY RULE:
Participants are identified strictly by pseudonymous research identifiers.
Zero direct PII (name, email) exists in this table.
"""

import uuid
from enum import Enum

from sqlalchemy import UUID, Boolean, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StudyGroup(str, Enum):
    INTERVENTION = "intervention"
    CONTROL = "control"


class Participant(Base, TimestampMixin):
    __tablename__ = "participants"
    __table_args__ = {"schema": "research"}

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Pseudonymous research code, e.g. "SL-2026-001"
    research_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mother_tongue: Mapped[str] = mapped_column(String(100), nullable=False)
    school_medium: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    study_group: Mapped[StudyGroup] = mapped_column(
        SQLEnum(StudyGroup, name="study_group", schema="research"),
        default=StudyGroup.INTERVENTION,
        nullable=False,
    )
    is_withdrawn: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
