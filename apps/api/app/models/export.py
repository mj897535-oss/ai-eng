"""Export Snapshot Model for Research Data Export (P14).

Each export creates an immutable frozen snapshot stored alongside its checksum.
Re-downloads serve the frozen bytes — not a re-query of live data.
"""

import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExportSnapshot(Base):
    """Immutable research data export snapshot (SRS FR-18).

    Every export — default or elevated — is stored as frozen bytes alongside
    its SHA-256 checksum, enabling exact re-download and audit.
    """

    __tablename__ = "export_snapshots"
    __table_args__ = {"schema": "research"}

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    exported_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    export_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="default",
    )  # "default" | "elevated"
    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    frozen_csv_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    frozen_dict_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="csv")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
