"""Audio Recording, Presigned Upload, and Assessment Ingestion Endpoints (Phase P6).

Implements:
- Direct upload to private S3/MinIO via short-lived presigned URLs.
- Participant consent gating: rejects audio endpoints without valid consent (FR-03).
- Strict idempotency: retries never create duplicate assessments (NFR-REL-01).
- Single official submission enforcement with researcher-authorized retake.
- Blinded status polling (queued, transcribing, analyzing, completed).
- Audio playback URL strictly gated to authorized reviewers / researchers (NFR-SEC-03).
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.assessment import Assessment, AssessmentType
from app.models.identity import User, UserRole
from app.models.research import Participant
from app.services.audio import (
    AssessmentSubmitInput,
    PresignedUploadRequest,
    PresignedUploadResponse,
    RetakeAuthInput,
    audio_service,
)
from app.services.storage import storage_provider

router = APIRouter(prefix="/assessments", tags=["Audio Recording & Upload"])


class AssessmentStatusResponse(BaseModel):
    assessment_id: uuid.UUID
    assessment_type: str
    status: str
    is_official: bool
    created_at: str


class RetakeResponse(BaseModel):
    status: str
    message: str
    assessment_id: uuid.UUID
    retake_authorized_at: str


# Helper to resolve participant_id from current_user
async def get_participant_for_user(user: User, db: AsyncSession) -> Participant:
    stmt = select(Participant).where(Participant.user_id == user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current user is not registered as an active research participant.",
        )
    return participant


@router.post("/pre/presigned-url", response_model=PresignedUploadResponse)
async def get_pre_test_presigned_url(
    payload: PresignedUploadRequest = PresignedUploadRequest(),
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT, UserRole.ADMIN, UserRole.RESEARCHER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> PresignedUploadResponse:
    """Request short-lived presigned PUT URL for pre-test audio recording directly to private storage."""
    participant = await get_participant_for_user(current_user, db)
    try:
        res = await audio_service.prepare_upload(
            db=db,
            participant_id=participant.participant_id,
            assessment_type=AssessmentType.PRE,
            codec=payload.codec,
            task_id=payload.task_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/post/presigned-url", response_model=PresignedUploadResponse)
async def get_post_test_presigned_url(
    payload: PresignedUploadRequest = PresignedUploadRequest(),
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT, UserRole.ADMIN, UserRole.RESEARCHER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> PresignedUploadResponse:
    """Request short-lived presigned PUT URL for post-test audio recording."""
    participant = await get_participant_for_user(current_user, db)
    try:
        res = await audio_service.prepare_upload(
            db=db,
            participant_id=participant.participant_id,
            assessment_type=AssessmentType.POST,
            codec=payload.codec,
            task_id=payload.task_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/submit", response_model=AssessmentStatusResponse, status_code=status.HTTP_201_CREATED)
async def submit_assessment(
    payload: AssessmentSubmitInput,
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT, UserRole.ADMIN, UserRole.RESEARCHER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> AssessmentStatusResponse:
    """Finalize assessment submission. Idempotent: retries return existing record."""
    participant = await get_participant_for_user(current_user, db)
    try:
        assessment = await audio_service.submit_assessment(
            db=db,
            participant_id=participant.participant_id,
            payload=payload,
            actor_id=current_user.id,
        )
        await db.commit()
        return AssessmentStatusResponse(
            assessment_id=assessment.assessment_id,
            assessment_type=assessment.assessment_type.value,
            status=assessment.status,
            is_official=assessment.is_official,
            created_at=assessment.created_at.isoformat(),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{assessment_id}/status", response_model=AssessmentStatusResponse)
async def get_assessment_status(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentStatusResponse:
    """Transparent status polling (queued_for_transcription, transcribing, analyzing, completed)."""
    stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    # Authorization: participants can only view their own records
    if current_user.role == UserRole.PARTICIPANT:
        participant = await get_participant_for_user(current_user, db)
        if assessment.participant_id != participant.participant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return AssessmentStatusResponse(
        assessment_id=assessment.assessment_id,
        assessment_type=assessment.assessment_type.value,
        status=assessment.status,
        is_official=assessment.is_official,
        created_at=assessment.created_at.isoformat(),
    )


@router.get("/{assessment_id}/audio-url")
async def get_presigned_audio_playback_url(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate short-lived presigned GET URL for researcher playback. Anonymous access is strictly denied."""
    stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    # Generate presigned download URL
    url = storage_provider.generate_presigned_download_url(
        key=assessment.audio_key,
        expires_in=settings.S3_PRESIGNED_EXPIRATION_SECONDS,
    )
    return {
        "assessment_id": str(assessment.assessment_id),
        "playback_url": url,
        "expires_in_seconds": settings.S3_PRESIGNED_EXPIRATION_SECONDS,
    }


@router.post("/retake/{participant_id}", response_model=RetakeResponse)
async def authorize_retake(
    participant_id: uuid.UUID,
    payload: RetakeAuthInput,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> RetakeResponse:
    """Authorize an official assessment retake for a participant (SRS FR-04)."""
    try:
        assessment = await audio_service.authorize_retake(
            db=db,
            participant_id=participant_id,
            assessment_type=payload.assessment_type,
            reason=payload.reason,
            researcher_id=current_user.id,
        )
        await db.commit()
        return RetakeResponse(
            status="authorized",
            message=f"Official {payload.assessment_type.value} retake authorized.",
            assessment_id=assessment.assessment_id,
            retake_authorized_at=assessment.retake_authorized_at.isoformat() if assessment.retake_authorized_at else "",
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
