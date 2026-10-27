"""Audit Log Management API Router.

Enforces:
- Restricted strictly to researcher_admin role.
- Filterable and paginated querying over append-only research.audit_logs.
- Privacy preservation: displays salted ip_hash instead of raw IP.
- Zero update/delete capabilities exposed.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.audit import AuditLog
from app.models.identity import User, UserRole

router = APIRouter(prefix="/admin/audit-logs", tags=["Audit Log"])


# --- Schemas ---

class AuditLogItemResponse(BaseModel):
    log_id: uuid.UUID
    actor_id: uuid.UUID | None
    role: str | None
    action: str
    record_type: str
    record_id: str
    outcome: str
    ip_hash: str | None
    user_agent: str | None
    details: str | None
    timestamp: datetime


class PaginatedAuditLogResponse(BaseModel):
    items: list[AuditLogItemResponse]
    total: int
    limit: int
    offset: int
    distinct_actions: list[str]
    distinct_roles: list[str]


# --- Endpoints ---

@router.get("", response_model=PaginatedAuditLogResponse)
async def query_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_roles(UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER))],
    action: str | None = Query(None, description="Filter by exact action"),
    role: str | None = Query(None, description="Filter by user role"),
    record_type: str | None = Query(None, description="Filter by record type (user, assessment, recording, etc.)"),
    outcome: str | None = Query(None, description="Filter by outcome (success, failure, denied)"),
    actor_id: uuid.UUID | None = Query(None, description="Filter by actor user ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaginatedAuditLogResponse:
    """Retrieve immutable audit log records with filtering and pagination."""
    # Base count query
    count_stmt = select(func.count(AuditLog.log_id))
    if action:
        count_stmt = count_stmt.where(AuditLog.action == action)
    if role:
        count_stmt = count_stmt.where(AuditLog.role == role)
    if record_type:
        count_stmt = count_stmt.where(AuditLog.record_type == record_type)
    if outcome:
        count_stmt = count_stmt.where(AuditLog.outcome == outcome)
    if actor_id:
        count_stmt = count_stmt.where(AuditLog.actor_id == actor_id)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Query items
    stmt = (
        select(AuditLog)
        .order_by(desc(AuditLog.timestamp))
        .offset(offset)
        .limit(limit)
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if role:
        stmt = stmt.where(AuditLog.role == role)
    if record_type:
        stmt = stmt.where(AuditLog.record_type == record_type)
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)

    res = await db.execute(stmt)
    logs = res.scalars().all()

    # Query distinct actions for UI dropdown
    actions_res = await db.execute(select(AuditLog.action).distinct())
    distinct_actions = sorted([a for a in actions_res.scalars().all() if a])

    # Distinct roles for UI dropdown
    roles_res = await db.execute(select(AuditLog.role).distinct())
    distinct_roles = sorted([r for r in roles_res.scalars().all() if r])

    items = [
        AuditLogItemResponse(
            log_id=item.log_id,
            actor_id=item.actor_id,
            role=item.role,
            action=item.action,
            record_type=item.record_type,
            record_id=item.record_id,
            outcome=item.outcome,
            ip_hash=item.ip_hash,
            user_agent=item.user_agent,
            details=item.details,
            timestamp=item.timestamp,
        )
        for item in logs
    ]

    return PaginatedAuditLogResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        distinct_actions=distinct_actions,
        distinct_roles=distinct_roles,
    )
