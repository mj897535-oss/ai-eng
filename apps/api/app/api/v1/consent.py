"""Consent Management and Right to Withdraw Endpoints.

Enforces:
- Versioned consent document viewing and acceptance.
- Append-only consent event tracking (consented / withdrawn).
- Right to withdraw workflow halting further data collection.
- Audit logging of all consent lifecycle events.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_active_user
from app.core.security import hash_ip_address
from app.models.identity import User, UserRole
from app.models.research import Participant
from app.services.consent import consent_service

router = APIRouter(prefix="/consent", tags=["Consent & Ethics"])


class ConsentAgreeInput(BaseModel):
    consent_version: str = Field(..., description="The exact consent version being accepted")


class ConsentWithdrawInput(BaseModel):
    reason: str | None = Field(None, max_length=500, description="Optional withdrawal feedback")


@router.get("/current", response_model=dict[str, Any])
async def get_current_consent(
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve current versioned consent document and participant consent state."""
    participant: Participant | None = None
    if current_user.role in {UserRole.PARTICIPANT, UserRole.STUDENT}:
        stmt = select(Participant).where(Participant.user_id == current_user.id)
        participant = (await db.execute(stmt)).scalar_one_or_none()

    return consent_service.get_current_consent_metadata(participant=participant)


@router.post("/agree", response_model=dict[str, Any])
async def agree_to_consent(
    payload: ConsentAgreeInput,
    request: Request,
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record participant agreement to the current research consent document."""
    stmt = select(Participant).where(Participant.user_id == current_user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant record not found for this user account.",
        )

    ip_hash = hash_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("User-Agent")

    try:
        record = await consent_service.agree_to_consent(
            db=db,
            participant_id=participant.participant_id,
            version=payload.consent_version,
            actor_id=current_user.id,
            actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return {
        "consent_id": str(record.consent_id),
        "status": record.status.value,
        "consent_version": record.consent_version,
        "created_at": record.created_at.isoformat(),
    }


@router.post("/withdraw", response_model=dict[str, Any])
async def withdraw_consent(
    payload: ConsentWithdrawInput,
    request: Request,
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute voluntary research consent withdrawal.

    Halts further data collection and flags record as withdrawn.
    """
    stmt = select(Participant).where(Participant.user_id == current_user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant record not found for this user account.",
        )

    ip_hash = hash_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("User-Agent")

    try:
        record = await consent_service.withdraw_consent(
            db=db,
            participant_id=participant.participant_id,
            reason=payload.reason,
            actor_id=current_user.id,
            actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return {
        "consent_id": str(record.consent_id),
        "status": record.status.value,
        "is_withdrawn": True,
        "message": "Consent successfully withdrawn. All future data collection has been halted.",
    }


@router.get("/history", response_model=list[dict[str, Any]])
async def get_consent_history(
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve immutable audit trail of consent events for current participant."""
    stmt = select(Participant).where(Participant.user_id == current_user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant record not found for this user account.",
        )

    history = await consent_service.get_participant_consent_history(
        db=db,
        participant_id=participant.participant_id,
    )
    return [
        {
            "consent_id": str(c.consent_id),
            "consent_version": c.consent_version,
            "status": c.status.value,
            "created_at": c.created_at.isoformat(),
        }
        for c in history
    ]
