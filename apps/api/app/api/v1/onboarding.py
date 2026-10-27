"""Participant Onboarding Wizard Endpoints.

Enforces:
- Progressive, resumable participant onboarding.
- Step transitions: consent -> profile -> mic_check -> completed.
- Protocol-driven profile field validation (age vs age band, geography).
- Friendly plain-language error responses.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_active_user
from app.core.security import hash_ip_address
from app.models.identity import User
from app.models.research import Participant
from app.services.audit import audit_service

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


class ProfileUpdateInput(BaseModel):
    age: int | None = Field(None, ge=15, le=100, description="Exact age if protocol specifies exact age")
    age_band: str | None = Field(None, description="Age band if protocol specifies age band")
    mother_tongue: str = Field(..., min_length=2, max_length=100, description="Self-described mother tongue / first language")
    school_medium: str = Field(..., min_length=2, max_length=100, description="Medium of school education")
    country: str | None = Field("India", max_length=100)
    state: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)


class CompleteStepInput(BaseModel):
    step: Literal["mic_check", "completed"] = Field(..., description="The onboarding step being finished")


@router.get("/state", response_model=dict[str, Any])
async def get_onboarding_state(
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve the current participant's onboarding progression and protocol configuration."""
    stmt = select(Participant).where(Participant.user_id == current_user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant record not found for this user account.",
        )

    # Determine current step if not explicitly set
    current_step = participant.onboarding_step
    if participant.is_withdrawn:
        current_step = "withdrawn"
    elif not participant.current_consent_version:
        current_step = "consent"

    return {
        "participant_id": str(participant.participant_id),
        "research_code": participant.research_code,
        "onboarding_completed": participant.onboarding_completed,
        "current_step": current_step,
        "is_withdrawn": participant.is_withdrawn,
        "consent_status": {
            "agreed": participant.current_consent_version == settings.CURRENT_CONSENT_VERSION,
            "version": participant.current_consent_version,
            "consented_at": participant.consented_at.isoformat() if participant.consented_at else None,
        },
        "profile": {
            "age": participant.age,
            "age_band": participant.age_band,
            "mother_tongue": participant.mother_tongue,
            "school_medium": participant.school_medium,
            "country": participant.country,
            "state": participant.state,
            "city": participant.city,
        },
        "config": {
            "collect_name": settings.COLLECT_NAME,
            "age_collection_mode": settings.AGE_COLLECTION_MODE,
            "collect_geography": settings.COLLECT_GEOGRAPHY,
            "current_consent_version": settings.CURRENT_CONSENT_VERSION,
        },
    }


@router.post("/profile", response_model=dict[str, Any])
async def submit_onboarding_profile(
    payload: ProfileUpdateInput,
    request: Request,
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Submit required demographic profile during onboarding."""
    stmt = select(Participant).where(Participant.user_id == current_user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant record not found for this user account.",
        )

    if participant.is_withdrawn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant has withdrawn consent.",
        )

    # Protocol validation
    if settings.AGE_COLLECTION_MODE == "exact" and payload.age is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Protocol requires exact age in years.",
        )
    if settings.AGE_COLLECTION_MODE == "band" and not payload.age_band:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Protocol requires an age band selection.",
        )

    # Update participant demographic record
    participant.age = payload.age
    participant.age_band = payload.age_band
    participant.mother_tongue = payload.mother_tongue.strip()
    participant.school_medium = payload.school_medium.strip()
    participant.country = payload.country
    participant.state = payload.state
    participant.city = payload.city
    participant.onboarding_step = "mic_check"

    await db.flush()

    ip_hash = hash_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("User-Agent")

    await audit_service.log_event(
        db=db,
        action="participant_profile_updated",
        actor_id=current_user.id,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        record_type="participant",
        record_id=str(participant.participant_id),
        outcome="success",
        ip_hash=ip_hash,
        user_agent=user_agent,
        details={"research_code": participant.research_code},
    )

    await db.commit()

    return {
        "status": "success",
        "next_step": "mic_check",
        "research_code": participant.research_code,
    }


@router.post("/complete-step", response_model=dict[str, Any])
async def complete_onboarding_step(
    payload: CompleteStepInput,
    request: Request,
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Progress the participant to the next onboarding step or complete onboarding."""
    stmt = select(Participant).where(Participant.user_id == current_user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant record not found for this user account.",
        )

    if payload.step == "mic_check":
        participant.onboarding_step = "what_next"
    elif payload.step == "completed":
        participant.onboarding_step = "completed"
        participant.onboarding_completed = True

    await db.flush()

    ip_hash = hash_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("User-Agent")

    await audit_service.log_event(
        db=db,
        action="onboarding_step_completed",
        actor_id=current_user.id,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        record_type="participant",
        record_id=str(participant.participant_id),
        outcome="success",
        ip_hash=ip_hash,
        user_agent=user_agent,
        details={
            "completed_step": payload.step,
            "onboarding_completed": participant.onboarding_completed,
        },
    )

    await db.commit()

    return {
        "status": "success",
        "current_step": participant.onboarding_step,
        "onboarding_completed": participant.onboarding_completed,
    }
