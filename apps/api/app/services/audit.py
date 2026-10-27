"""Research and Security Audit Log Service.

NON-NEGOTIABLE RULE 3:
Audit logs are strictly APPEND-ONLY.
Every security-relevant and research-relevant event is written to research.audit_logs.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_ip
from app.models.audit import AuditLog

logger = logging.getLogger("syntaxlens.audit")


class AuditService:
    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        record_type: str,
        record_id: str,
        actor_id: uuid.UUID | None = None,
        role: str | None = None,
        outcome: str = "success",
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Append an immutable audit entry."""
        ip_hash = hash_ip(ip_address)
        details_str = json.dumps(details) if details else None

        entry = AuditLog(
            log_id=uuid.uuid4(),
            actor_id=actor_id,
            role=role,
            action=action,
            record_type=record_type,
            record_id=str(record_id),
            outcome=outcome,
            ip_hash=ip_hash,
            user_agent=user_agent[:255] if user_agent else None,
            details=details_str,
            timestamp=datetime.utcnow(),
        )

        db.add(entry)
        try:
            await db.commit()
            await db.refresh(entry)
        except Exception as e:
            await db.rollback()
            logger.error("Failed to commit audit log entry (%s): %s", action, e)
            raise

        return entry

    @classmethod
    async def log_login_success(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        role: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        return await cls.log(
            db=db,
            action="login_success",
            record_type="user",
            record_id=str(user_id),
            actor_id=user_id,
            role=role,
            outcome="success",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    async def log_login_failure(
        cls,
        db: AsyncSession,
        identifier: str,
        reason: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        return await cls.log(
            db=db,
            action="login_failure",
            record_type="auth",
            record_id=identifier[:100],
            outcome="failure",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": reason},
        )

    @classmethod
    async def log_logout(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        role: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        return await cls.log(
            db=db,
            action="logout",
            record_type="user",
            record_id=str(user_id),
            actor_id=user_id,
            role=role,
            outcome="success",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    async def log_password_reset_request(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID | None,
        identifier: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        return await cls.log(
            db=db,
            action="password_reset_request",
            record_type="user",
            record_id=str(user_id) if user_id else identifier[:100],
            actor_id=user_id,
            outcome="success" if user_id else "unknown_user",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    async def log_password_reset_complete(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        return await cls.log(
            db=db,
            action="password_reset_complete",
            record_type="user",
            record_id=str(user_id),
            actor_id=user_id,
            outcome="success",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    async def log_password_change(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        role: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        return await cls.log(
            db=db,
            action="password_change",
            record_type="user",
            record_id=str(user_id),
            actor_id=user_id,
            role=role,
            outcome="success",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    async def log_recording_access(
        cls,
        db: AsyncSession,
        actor_id: uuid.UUID,
        role: str,
        assessment_id: uuid.UUID,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        return await cls.log(
            db=db,
            action="recording_access",
            record_type="recording",
            record_id=str(assessment_id),
            actor_id=actor_id,
            role=role,
            outcome="success",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    async def log_event(
        cls,
        db: AsyncSession,
        action: str,
        actor_id: uuid.UUID | None = None,
        role: str | None = None,
        record_type: str = "research",
        record_id: str | None = None,
        outcome: str = "success",
        ip_hash: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Helper to append an audit entry with already-hashed IP or explicit details."""
        details_str = json.dumps(details) if details else None
        entry = AuditLog(
            log_id=uuid.uuid4(),
            actor_id=actor_id,
            role=role,
            action=action,
            record_type=record_type,
            record_id=str(record_id or "system"),
            outcome=outcome,
            ip_hash=ip_hash,
            user_agent=user_agent[:255] if user_agent else None,
            details=details_str,
            timestamp=datetime.utcnow(),
        )
        db.add(entry)
        try:
            await db.commit()
            await db.refresh(entry)
        except Exception as e:
            await db.rollback()
            logger.error("Failed to commit audit log event (%s): %s", action, e)
        return entry


audit_service = AuditService()

