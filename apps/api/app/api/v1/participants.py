"""Researcher Participant Management Endpoints.

Enforces:
- Participant creation with collision-safe unique pseudonymous IDs.
- Duplicate IDs rejected with a clear message.
- Bulk CSV import with dry-run preview (valid rows, rejected rows, duplicate detection).
- Participant deactivation / reactivation and study group assignment.
- Research queries never expose or join identity tables.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import hash_ip_address
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.services.participant import (
    CSVImportResult,
    ParticipantCreateInput,
    participant_service,
)

router = APIRouter(tags=["Participant Management"])


class ParticipantResponse(BaseModel):
    participant_id: uuid.UUID
    research_code: str
    study_group: str
    is_group_blinded: bool
    is_active: bool
    is_withdrawn: bool
    age: int | None = None
    age_band: str | None = None
    mother_tongue: str | None = None
    school_medium: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    current_consent_version: str | None = None
    consented_at: str | None = None
    withdrawn_at: str | None = None
    withdrawal_reason: str | None = None
    onboarding_completed: bool
    onboarding_step: str
    created_at: str


class ParticipantStatusUpdateInput(BaseModel):
    is_active: bool


class ParticipantGroupUpdateInput(BaseModel):
    study_group: StudyGroup


class CSVImportInput(BaseModel):
    csv_content: str = Field(..., description="Raw CSV string to parse and validate")


@router.get("/admin/participants", response_model=dict[str, Any])
async def list_participants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by research code"),
    study_group: StudyGroup | None = Query(None, description="Filter by study group"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_withdrawn: bool | None = Query(None, description="Filter by withdrawal status"),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List participants with filters and pagination for researchers."""
    query = select(Participant)

    if search:
        query = query.where(Participant.research_code.ilike(f"%{search.strip()}%"))
    if study_group:
        query = query.where(Participant.study_group == study_group)
    if is_active is not None:
        query = query.where(Participant.is_active == is_active)
    if is_withdrawn is not None:
        query = query.where(Participant.is_withdrawn == is_withdrawn)

    # Total count
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate
    query = query.order_by(Participant.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    participants = result.scalars().all()

    items = [
        {
            "participant_id": str(p.participant_id),
            "research_code": p.research_code,
            "study_group": p.study_group.value,
            "is_group_blinded": p.is_group_blinded,
            "is_active": p.is_active,
            "is_withdrawn": p.is_withdrawn,
            "age": p.age,
            "age_band": p.age_band,
            "mother_tongue": p.mother_tongue,
            "school_medium": p.school_medium,
            "country": p.country,
            "state": p.state,
            "city": p.city,
            "current_consent_version": p.current_consent_version,
            "consented_at": p.consented_at.isoformat() if p.consented_at else None,
            "withdrawn_at": p.withdrawn_at.isoformat() if p.withdrawn_at else None,
            "withdrawal_reason": p.withdrawal_reason,
            "onboarding_completed": p.onboarding_completed,
            "onboarding_step": p.onboarding_step,
            "created_at": p.created_at.isoformat(),
        }
        for p in participants
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
    }


@router.post("/admin/participants", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_single_participant(
    payload: ParticipantCreateInput,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Enroll a single participant with unique pseudonymous ID."""
    ip_hash = hash_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("User-Agent")

    try:
        participant = await participant_service.create_participant(
            db=db,
            input_data=payload,
            actor_id=current_user.id,
            actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    return {
        "participant_id": str(participant.participant_id),
        "research_code": participant.research_code,
        "study_group": participant.study_group.value,
        "is_active": participant.is_active,
        "created_at": participant.created_at.isoformat(),
    }


@router.post("/admin/participants/import", response_model=CSVImportResult)
async def import_participants_csv(
    payload: CSVImportInput,
    request: Request,
    dry_run: bool = Query(True, description="When true, performs validation only without writing to DB"),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER])),
    db: AsyncSession = Depends(get_db),
) -> CSVImportResult:
    """Bulk import participants from CSV with dry-run preview and duplicate detection."""
    ip_hash = hash_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("User-Agent")

    result = await participant_service.parse_and_process_csv(
        db=db,
        csv_text=payload.csv_content,
        dry_run=dry_run,
        actor_id=current_user.id,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        ip_hash=ip_hash,
        user_agent=user_agent,
    )

    if not dry_run and result.can_commit:
        await db.commit()

    return result


@router.get("/admin/participants/{participant_id}", response_model=dict[str, Any])
async def get_participant_details(
    participant_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full researcher record for a participant."""
    stmt = select(Participant).where(Participant.participant_id == participant_id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Participant {participant_id} not found.")

    return {
        "participant_id": str(participant.participant_id),
        "research_code": participant.research_code,
        "study_group": participant.study_group.value,
        "is_group_blinded": participant.is_group_blinded,
        "is_active": participant.is_active,
        "is_withdrawn": participant.is_withdrawn,
        "age": participant.age,
        "age_band": participant.age_band,
        "mother_tongue": participant.mother_tongue,
        "school_medium": participant.school_medium,
        "country": participant.country,
        "state": participant.state,
        "city": participant.city,
        "current_consent_version": participant.current_consent_version,
        "consented_at": participant.consented_at.isoformat() if participant.consented_at else None,
        "withdrawn_at": participant.withdrawn_at.isoformat() if participant.withdrawn_at else None,
        "withdrawal_reason": participant.withdrawal_reason,
        "onboarding_completed": participant.onboarding_completed,
        "onboarding_step": participant.onboarding_step,
        "created_at": participant.created_at.isoformat(),
    }


@router.patch("/admin/participants/{participant_id}/status", response_model=dict[str, Any])
async def update_participant_status(
    participant_id: uuid.UUID,
    payload: ParticipantStatusUpdateInput,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Deactivate or reactivate a participant."""
    ip_hash = hash_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("User-Agent")

    try:
        participant = await participant_service.update_status(
            db=db,
            participant_id=participant_id,
            is_active=payload.is_active,
            actor_id=current_user.id,
            actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return {
        "participant_id": str(participant.participant_id),
        "research_code": participant.research_code,
        "is_active": participant.is_active,
    }


@router.patch("/admin/participants/{participant_id}/group", response_model=dict[str, Any])
async def update_participant_group(
    participant_id: uuid.UUID,
    payload: ParticipantGroupUpdateInput,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Assign or modify study group for a participant."""
    ip_hash = hash_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("User-Agent")

    try:
        participant = await participant_service.assign_group(
            db=db,
            participant_id=participant_id,
            study_group=payload.study_group,
            actor_id=current_user.id,
            actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return {
        "participant_id": str(participant.participant_id),
        "research_code": participant.research_code,
        "study_group": participant.study_group.value,
    }
