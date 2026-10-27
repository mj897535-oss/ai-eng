"""Consent Model.

RESEARCH INTEGRITY RULE:
Consent records are strictly APPEND-ONLY.
Consent events, withdrawals, and version acceptances are recorded as new immutable rows.
Database triggers prohibit UPDATE and DELETE.
"""

import uuid
from enum import Enum

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ConsentStatus(str, Enum):
    CONSENTED = "consented"
    WITHDRAWN = "withdrawn"


class Consent(Base, TimestampMixin):
    __tablename__ = "consents"
    __table_args__ = {"schema": "research"}

    consent_id: Mapped[uuid.UUID] = mapped_column(
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
    consent_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ConsentStatus] = mapped_column(
        SQLEnum(ConsentStatus, name="consent_status", schema="research"),
        default=ConsentStatus.CONSENTED,
        nullable=False,
    )
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
