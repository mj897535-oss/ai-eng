"""AI Tutor API Endpoints (Phase P10, Signature Feature C).

Implements:
- GET /tutor/status: Verification gating check and pre-test summary for participant.
- POST /tutor/sessions: Initialize personalized tutoring session.
- POST /tutor/sessions/{id}/turns: Process learner turn through the Hint Ladder.
- POST /tutor/sessions/{id}/end: Conclude practice session.
- GET /tutor/sessions/{id}/history: Message trajectory for active session.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.identity import User, UserRole
from app.models.practice import PracticeEvent, PracticeSession
from app.models.research import Participant
from app.services.tutor import TutorGatingError, tutor_service

router = APIRouter(prefix="/tutor", tags=["AI Tutor & Hint Ladder"])


# --- Schemas ---

class StartSessionRequest(BaseModel):
    interests: str | None = Field(None, max_length=500, description="Learner interests to guide natural conversation")


class LearnerTurnRequest(BaseModel):
    utterance: str = Field(..., min_length=1, max_length=2000, description="Learner speech or text input")


class InterruptionRequest(BaseModel):
    interruption_type: str = Field(..., max_length=50, description="Type of technical interruption (e.g. disconnect, mic_failure)")
    details: str | None = Field(None, max_length=500, description="Diagnostic details")


class TutorTurnResponseSchema(BaseModel):
    reply_text: str
    target_category: str
    learner_phrase_quoted: str | None = None
    hint_level: int
    expects_attempt: bool
    transfer_prompt: str | None = None
    is_off_topic: bool = False
    safety_refusal: bool = False
    is_self_correction: bool = False
    attempt_type: str


class TutorStatusResponse(BaseModel):
    can_start_tutoring: bool
    is_pretest_verified: bool
    priority_categories: list[str]
    saved_interests: str | None = None
    gating_message: str | None = None
    study_group: str


# --- Helper ---

async def get_participant(user: User, db: AsyncSession) -> Participant:
    stmt = select(Participant).where(Participant.user_id == user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current user is not registered as a research participant.",
        )
    return participant


# --- Endpoints ---

@router.get("/status", response_model=TutorStatusResponse)
async def get_tutor_eligibility_status(
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT, UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> TutorStatusResponse:
    """Check participant tutoring eligibility and verified pre-test baseline status."""
    participant = await get_participant(current_user, db)

    pretest = await tutor_service.get_verified_pretest_summary(db, participant.participant_id)

    if not pretest:
        return TutorStatusResponse(
            can_start_tutoring=False,
            is_pretest_verified=False,
            priority_categories=[],
            saved_interests=participant.learner_interests,
            gating_message="Tutoring is locked until your baseline pre-test assessment has been reviewed and verified.",
            study_group=participant.study_group.value if hasattr(participant.study_group, "value") else str(participant.study_group),
        )

    return TutorStatusResponse(
        can_start_tutoring=True,
        is_pretest_verified=True,
        priority_categories=pretest["priority_categories"],
        saved_interests=participant.learner_interests,
        gating_message=None,
        study_group=participant.study_group.value if hasattr(participant.study_group, "value") else str(participant.study_group),
    )


@router.post("/sessions", response_model=dict[str, Any])
async def start_tutoring_session(
    payload: StartSessionRequest,
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start a new conversational tutoring session."""
    participant = await get_participant(current_user, db)

    try:
        return await tutor_service.start_session(
            db=db,
            participant_id=participant.participant_id,
            interests=payload.interests,
        )
    except TutorGatingError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions/{session_id}/turns", response_model=TutorTurnResponseSchema)
async def submit_learner_turn(
    session_id: uuid.UUID,
    payload: LearnerTurnRequest,
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT])),
    db: AsyncSession = Depends(get_db),
) -> TutorTurnResponseSchema:
    """Submit learner speech/text and receive structured Hint Ladder feedback."""
    participant = await get_participant(current_user, db)

    try:
        res = await tutor_service.process_turn(
            db=db,
            session_id=session_id,
            participant_id=participant.participant_id,
            learner_utterance=payload.utterance,
        )
        return TutorTurnResponseSchema(**res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions/{session_id}/end", response_model=dict[str, Any])
async def end_tutoring_session(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Conclude an active practice session."""
    participant = await get_participant(current_user, db)

    try:
        return await tutor_service.end_session(
            db=db,
            session_id=session_id,
            participant_id=participant.participant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/sessions/{session_id}/history", response_model=list[dict[str, Any]])
async def get_session_history(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT, UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve event trajectory for a practice session."""
    participant = await get_participant(current_user, db)

    sess_stmt = select(PracticeSession).where(
        PracticeSession.session_id == session_id,
        PracticeSession.participant_id == participant.participant_id,
    )
    session = (await db.execute(sess_stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    ev_stmt = (
        select(PracticeEvent)
        .where(PracticeEvent.session_id == session_id)
        .order_by(PracticeEvent.created_at.asc())
    )
    events = (await db.execute(ev_stmt)).scalars().all()

    return [
        {
            "event_id": str(e.event_id),
            "learner_input": e.learner_input,
            "tutor_reply": e.tutor_reply,
            "hint_level": e.feedback_level,
            "target_category": e.target_category,
            "is_correct": e.is_correct,
            "attempt_type": e.attempt_type.value,
            "transfer_prompt": e.transfer_prompt,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.post("/sessions/{session_id}/interruptions", response_model=dict[str, Any])
async def log_session_interruption(
    session_id: uuid.UUID,
    payload: InterruptionRequest,
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record technical interruptions (e.g. mic failure, disconnect) during a session."""
    participant = await get_participant(current_user, db)

    try:
        return await tutor_service.log_interruption(
            db=db,
            session_id=session_id,
            participant_id=participant.participant_id,
            interruption_type=payload.interruption_type,
            details=payload.details,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history", response_model=dict[str, Any])
async def get_participant_practice_history(
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT, UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full practice session history and independent correction rate metrics."""
    participant = await get_participant(current_user, db)
    return await tutor_service.get_participant_history(db, participant.participant_id)


@router.get("/recurrence", response_model=list[dict[str, Any]])
async def get_participant_recurrence_patterns(
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT, UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve participant longitudinal recurring utterance patterns."""
    participant = await get_participant(current_user, db)
    return await tutor_service.get_recurrence_patterns(db, participant.participant_id)


@router.get("/adherence", response_model=dict[str, Any])
async def get_intervention_adherence_statistics(
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve cohort intervention adherence statistics (SRS Section 10)."""
    return await tutor_service.get_cohort_adherence(db)
