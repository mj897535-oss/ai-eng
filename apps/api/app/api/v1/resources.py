"""Protected Research Resources Router.

Exposes endpoints for participants and assessments, strictly guarded by row-level
ownership and assignment policies (SRS FR-01, FR-02, FR-10, NFR-PRIV-01).
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_active_user
from app.core.policies import (
    authorize_assessment_access,
    authorize_participant_access,
    authorize_recording_access,
)
from app.models.identity import User
from app.models.practice import PracticeSession

router = APIRouter(prefix="", tags=["Protected Resources"])


# --- Schemas ---

class ParticipantProfileResponse(BaseModel):
    participant_id: uuid.UUID
    research_code: str
    age: int | None
    mother_tongue: str | None = None
    school_medium: str | None = None
    country: str | None = None
    study_group: str
    is_withdrawn: bool


class AssessmentDetailResponse(BaseModel):
    assessment_id: uuid.UUID
    participant_id: uuid.UUID
    task_id: uuid.UUID
    assessment_type: str
    word_count: int
    stt_version: str
    rubric_version: str
    model_version: str
    created_at: datetime


class AudioAccessResponse(BaseModel):
    assessment_id: uuid.UUID
    audio_key: str
    presigned_url: str
    expires_in_seconds: int


class PracticeSessionResponse(BaseModel):
    session_id: uuid.UUID
    participant_id: uuid.UUID
    start_time: datetime
    active_duration_seconds: int
    status: str


# --- Endpoints ---

@router.get("/participants/{participant_id}", response_model=ParticipantProfileResponse)
async def get_participant(
    participant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_active_user)],
) -> ParticipantProfileResponse:
    """Retrieve participant research profile. Row-level ownership enforced."""
    participant = await authorize_participant_access(current_user, participant_id, db)
    return ParticipantProfileResponse(
        participant_id=participant.participant_id,
        research_code=participant.research_code,
        age=participant.age,
        mother_tongue=participant.mother_tongue,
        school_medium=participant.school_medium,
        country=participant.country,
        study_group=participant.study_group.value if hasattr(participant.study_group, "value") else str(participant.study_group),
        is_withdrawn=participant.is_withdrawn,
    )


@router.get("/assessments/{assessment_id}", response_model=AssessmentDetailResponse)
async def get_assessment(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_active_user)],
) -> AssessmentDetailResponse:
    """Retrieve assessment details. Row-level ownership/assignment enforced."""
    assessment = await authorize_assessment_access(current_user, assessment_id, db)
    return AssessmentDetailResponse(
        assessment_id=assessment.assessment_id,
        participant_id=assessment.participant_id,
        task_id=assessment.task_id,
        assessment_type=assessment.assessment_type.value if hasattr(assessment.assessment_type, "value") else str(assessment.assessment_type),
        word_count=assessment.word_count,
        stt_version=assessment.stt_version,
        rubric_version=assessment.rubric_version,
        model_version=assessment.model_version,
        created_at=assessment.created_at,
    )


@router.get("/assessments/{assessment_id}/audio", response_model=AudioAccessResponse)
async def get_assessment_audio(
    assessment_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_active_user)],
) -> AudioAccessResponse:
    """Retrieve secure temporary presigned audio access. Audited on every access."""
    assessment = await authorize_recording_access(current_user, assessment_id, db, request)
    # Simulated short-lived presigned URL
    presigned = f"http://localhost:9000/syntaxlens-audio/{assessment.audio_key}?token=mock-presigned-token-valid-15m"
    return AudioAccessResponse(
        assessment_id=assessment.assessment_id,
        audio_key=assessment.audio_key,
        presigned_url=presigned,
        expires_in_seconds=900,
    )


@router.get("/practice-sessions/{session_id}", response_model=PracticeSessionResponse)
async def get_practice_session(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_active_user)],
) -> PracticeSessionResponse:
    """Retrieve practice session. Row-level ownership enforced."""
    stmt = select(PracticeSession).where(PracticeSession.session_id == session_id)
    res = await db.execute(stmt)
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found.")

    # Check participant ownership
    await authorize_participant_access(current_user, sess.participant_id, db)

    return PracticeSessionResponse(
        session_id=sess.session_id,
        participant_id=sess.participant_id,
        start_time=sess.start_time,
        active_duration_seconds=sess.active_duration_seconds,
        status=sess.status,
    )
