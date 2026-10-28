"""Audio Recording, Presigned Upload, and Assessment Ingestion Endpoints (Phase P6).

Implements:
- Direct upload to private S3/MinIO via short-lived presigned URLs.
- Participant consent gating: rejects audio endpoints without valid consent (FR-03).
- Strict idempotency: retries never create duplicate assessments (NFR-REL-01).
- Single official submission enforcement with researcher-authorized retake.
- Blinded status polling (queued, transcribing, analyzing, completed).
- Audio playback URL strictly gated to authorized reviewers / researchers (NFR-SEC-03).
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.assessment import (
    Assessment,
    AssessmentType,
    STTJobMetric,
    TranscriptRevision,
)
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
from app.services.stt_pipeline import stt_pipeline_service

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


class TranscriptRevisionCreate(BaseModel):
    revised_transcript: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


class TranscriptRevisionResponse(BaseModel):
    revision_id: uuid.UUID
    assessment_id: uuid.UUID
    revised_transcript: str
    revised_word_count: int
    reviewer_id: uuid.UUID
    reason: str
    diff_json: str | None
    created_at: str


class TranscriptResponse(BaseModel):
    assessment_id: uuid.UUID
    status: str
    transcript: str | None
    word_count: int
    stt_confidence: float | None
    low_confidence_flag: bool
    words: list[dict[str, Any]]
    revisions: list[TranscriptRevisionResponse]
    retry_count: int
    last_error: str | None


class STTMetricsSummary(BaseModel):
    total_runs: int
    total_audio_seconds: float
    total_cost_usd: float
    average_latency_ms: float
    average_confidence: float
    low_confidence_count: int
    recent_jobs: list[dict[str, Any]]


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


@router.post("/{assessment_id}/transcribe", response_model=TranscriptResponse)
async def trigger_transcription(
    assessment_id: uuid.UUID,
    force_retry: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TranscriptResponse:
    """Trigger or retry speech-to-text background job."""
    stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    if current_user.role == UserRole.PARTICIPANT:
        participant = await get_participant_for_user(current_user, db)
        if assessment.participant_id != participant.participant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        updated = await stt_pipeline_service.process_transcription_job(
            db=db,
            assessment_id=assessment_id,
            force_retry=force_retry,
        )
        words_data = json.loads(updated.words_json) if updated.words_json else []
        revisions_stmt = (
            select(TranscriptRevision)
            .where(TranscriptRevision.assessment_id == assessment_id)
            .order_by(TranscriptRevision.created_at.desc())
        )
        revisions = (await db.execute(revisions_stmt)).scalars().all()

        return TranscriptResponse(
            assessment_id=updated.assessment_id,
            status=updated.status,
            transcript=updated.transcript,
            word_count=updated.word_count,
            stt_confidence=updated.stt_confidence,
            low_confidence_flag=updated.low_confidence_flag,
            words=words_data,
            revisions=[
                TranscriptRevisionResponse(
                    revision_id=r.revision_id,
                    assessment_id=r.assessment_id,
                    revised_transcript=r.revised_transcript,
                    revised_word_count=r.revised_word_count,
                    reviewer_id=r.reviewer_id,
                    reason=r.reason,
                    diff_json=r.diff_json,
                    created_at=r.created_at.isoformat(),
                )
                for r in revisions
            ],
            retry_count=updated.retry_count,
            last_error=updated.last_error,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{assessment_id}/transcript", response_model=TranscriptResponse)
async def get_assessment_transcript(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TranscriptResponse:
    """Fetch faithful verbatim transcript, word timestamps, and human revisions."""
    stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    if current_user.role == UserRole.PARTICIPANT:
        participant = await get_participant_for_user(current_user, db)
        if assessment.participant_id != participant.participant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    words_data = json.loads(assessment.words_json) if assessment.words_json else []
    rev_stmt = (
        select(TranscriptRevision)
        .where(TranscriptRevision.assessment_id == assessment_id)
        .order_by(TranscriptRevision.created_at.desc())
    )
    revisions = (await db.execute(rev_stmt)).scalars().all()

    return TranscriptResponse(
        assessment_id=assessment.assessment_id,
        status=assessment.status,
        transcript=assessment.transcript,
        word_count=assessment.word_count,
        stt_confidence=assessment.stt_confidence,
        low_confidence_flag=assessment.low_confidence_flag,
        words=words_data,
        revisions=[
            TranscriptRevisionResponse(
                revision_id=r.revision_id,
                assessment_id=r.assessment_id,
                revised_transcript=r.revised_transcript,
                revised_word_count=r.revised_word_count,
                reviewer_id=r.reviewer_id,
                reason=r.reason,
                diff_json=r.diff_json,
                created_at=r.created_at.isoformat(),
            )
            for r in revisions
        ],
        retry_count=assessment.retry_count,
        last_error=assessment.last_error,
    )


@router.post("/{assessment_id}/revisions", response_model=TranscriptRevisionResponse)
async def create_transcript_revision(
    assessment_id: uuid.UUID,
    payload: TranscriptRevisionCreate,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> TranscriptRevisionResponse:
    """Create an immutable human revision referencing the original transcript (SRS FR-06)."""
    try:
        revision = await stt_pipeline_service.create_transcript_revision(
            db=db,
            assessment_id=assessment_id,
            revised_transcript=payload.revised_transcript,
            reason=payload.reason,
            reviewer=current_user,
        )
        return TranscriptRevisionResponse(
            revision_id=revision.revision_id,
            assessment_id=revision.assessment_id,
            revised_transcript=revision.revised_transcript,
            revised_word_count=revision.revised_word_count,
            reviewer_id=revision.reviewer_id,
            reason=revision.reason,
            diff_json=revision.diff_json,
            created_at=revision.created_at.isoformat(),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/metrics/stt", response_model=STTMetricsSummary)
async def get_stt_metrics(
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> STTMetricsSummary:
    """Pilot Kit performance, latency, cost, and reliability metrics across STT runs."""
    stmt = select(STTJobMetric).order_by(STTJobMetric.created_at.desc())
    metrics = (await db.execute(stmt)).scalars().all()

    total_runs = len(metrics)
    total_audio_sec = sum(m.audio_duration_seconds for m in metrics)
    total_cost = sum(m.estimated_cost_usd for m in metrics)
    avg_latency = (sum(m.latency_ms for m in metrics) / total_runs) if total_runs else 0.0
    avg_conf = (sum(m.average_confidence for m in metrics) / total_runs) if total_runs else 1.0
    low_conf_count = sum(m.low_confidence_count for m in metrics)

    recent_jobs = [
        {
            "metric_id": str(m.metric_id),
            "assessment_id": str(m.assessment_id),
            "provider": m.provider,
            "model_version": m.model_version,
            "audio_duration_seconds": m.audio_duration_seconds,
            "latency_ms": m.latency_ms,
            "estimated_cost_usd": m.estimated_cost_usd,
            "word_count": m.word_count,
            "average_confidence": m.average_confidence,
            "low_confidence_count": m.low_confidence_count,
            "retry_count": m.retry_count,
            "created_at": m.created_at.isoformat(),
        }
        for m in metrics[:25]
    ]

    return STTMetricsSummary(
        total_runs=total_runs,
        total_audio_seconds=round(total_audio_sec, 2),
        total_cost_usd=round(total_cost, 4),
        average_latency_ms=round(avg_latency, 1),
        average_confidence=round(avg_conf, 3),
        low_confidence_count=low_conf_count,
        recent_jobs=recent_jobs,
    )



