"""Database-Enforced Immutability Tests for Audit Trail.

NON-NEGOTIABLE RULE 3:
Audit logs are strictly APPEND-ONLY.
Triggers prevent updating or deleting any audit log record.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DatabaseError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.services.audit import AuditService


@pytest.mark.asyncio
async def test_audit_log_update_fails_due_to_trigger(test_session: AsyncSession) -> None:
    """Updating an audit log entry must raise a database trigger exception."""
    log_id = uuid.uuid4()
    entry = AuditLog(
        log_id=log_id,
        action="login_success",
        record_type="user",
        record_id=str(uuid.uuid4()),
        outcome="success",
        timestamp=datetime.utcnow(),
    )
    test_session.add(entry)
    await test_session.commit()

    # Attempting to mutate any field in the audit record
    stmt = update(AuditLog).where(AuditLog.log_id == log_id).values(outcome="tampered_outcome")
    with pytest.raises((OperationalError, DatabaseError)) as exc_info:
        await test_session.execute(stmt)
        await test_session.commit()

    await test_session.rollback()
    assert "RESEARCH INTEGRITY VIOLATION" in str(exc_info.value) or "append-only" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_audit_log_delete_fails_due_to_trigger(test_session: AsyncSession) -> None:
    """Deleting an audit log entry must raise a database trigger exception."""
    log_id = uuid.uuid4()
    entry = AuditLog(
        log_id=log_id,
        action="user_deactivated",
        record_type="user",
        record_id=str(uuid.uuid4()),
        outcome="success",
        timestamp=datetime.utcnow(),
    )
    test_session.add(entry)
    await test_session.commit()

    # Attempting to delete the audit record
    stmt = delete(AuditLog).where(AuditLog.log_id == log_id)
    with pytest.raises((OperationalError, DatabaseError)) as exc_info:
        await test_session.execute(stmt)
        await test_session.commit()

    await test_session.rollback()
    assert "RESEARCH INTEGRITY VIOLATION" in str(exc_info.value) or "append-only" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_audit_service_logs_all_required_events(test_session: AsyncSession) -> None:
    """Verify that AuditService correctly appends all required event types."""
    actor_id = uuid.uuid4()
    test_events = [
        ("login_success", "user", "success"),
        ("login_failure", "auth", "failure"),
        ("logout", "user", "success"),
        ("password_reset_request", "user", "success"),
        ("password_reset_complete", "user", "success"),
        ("password_change", "user", "success"),
        ("consent_given", "consent", "success"),
        ("audio_submission", "assessment", "success"),
        ("review_edit", "review", "success"),
        ("export", "dataset", "success"),
        ("deletion", "participant", "success"),
        ("role_change", "user", "success"),
        ("recording_access", "recording", "success"),
    ]

    for action, rec_type, outcome in test_events:
        await AuditService.log(
            db=test_session,
            action=action,
            record_type=rec_type,
            record_id=str(uuid.uuid4()),
            actor_id=actor_id,
            role="researcher_admin",
            outcome=outcome,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Suite",
            details={"test_flag": True},
        )

    # Query all records
    res = await test_session.execute(select(AuditLog).where(AuditLog.actor_id == actor_id))
    saved_records = res.scalars().all()
    assert len(saved_records) == len(test_events)
    saved_actions = {r.action for r in saved_records}
    for action, _, _ in test_events:
        assert action in saved_actions
