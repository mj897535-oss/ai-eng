"""Research Audit Log Model.

RESEARCH INTEGRITY RULE:
The research audit trail is strictly APPEND-ONLY.
Triggers prevent updating or deleting any audit log record.
"""

import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """Immutable audit trail for all security, data access, and research events.
    
    Fields strictly map to SRS §13 / FR-19:
    (actor_id, role, action, record_type, record_id, outcome, ip_hash, user_agent, timestamp)
    """
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "research"}

    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    record_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    record_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        index=True,
    )
    ip_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # Backward compatibility alias for created_at
    @property
    def created_at(self) -> datetime:
        return self.timestamp
