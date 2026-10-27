"""Error Analysis Engine & Evidence Lens Endpoints (Phase P8).

Implements:
- POST /assessments/{id}/analyze: Runs candidate syntactic error detection.
- GET /assessments/{id}/report: Evidence Lens data provider with participant visibility gating.
- POST /assessments/{id}/release: Researcher releases assessment results to participant.
- GET /assessments/review-queue: Lists assessments requiring reviewer adjudication.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.assessment import Assessment, ErrorAnnotation
from app.models.identity import User, UserRole
from app.models.research import Participant
from app.services.analysis import error_analysis_service

router = APIRouter(prefix="/assessments", tags=["Error Analysis & Evidence Lens"])


class AnnotationResponse(BaseModel):
    annotation_id: uuid.UUID
    start_char: int
    end_char: int
    start_time_ms: int | None
    end_time_ms: int | None
    candidate_error: str
    suggested_correction: str
    category_code: str
    explanation: str
    confidence: float
    ai_status: str
    flag: str
    rubric_version: str
    prompt_version: str
    model_version: str


class AssessmentReportResponse(BaseModel):
    assessment_id: uuid.UUID
    assessment_type: str
    status: str
    transcript: str | None
    word_count: int
    is_visible_to_participant: bool
    banner_notice: str
    rubric_version: str
    prompt_version: str | None
    model_version: str
    annotations: list[AnnotationResponse]


class ReleaseResponse(BaseModel):
    status: str
    assessment_id: uuid.UUID
    is_visible_to_participant: bool
    message: str


class ReviewQueueItem(BaseModel):
    assessment_id: uuid.UUID
    participant_code: str
    assessment_type: str
    needs_review_count: int
    total_annotations: int
    created_at: str


async def get_participant_for_user(user: User, db: AsyncSession) -> Participant:
    stmt = select(Participant).where(Participant.user_id == user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current user is not registered as an active research participant.",
        )
    return participant


@router.post("/{assessment_id}/analyze", response_model=list[AnnotationResponse])
async def trigger_error_analysis(
    assessment_id: uuid.UUID,
    force_retry: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnnotationResponse]:
    """Trigger candidate syntactic error analysis via decoupled LLMProvider."""
    stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    if current_user.role == UserRole.PARTICIPANT:
        participant = await get_participant_for_user(current_user, db)
        if assessment.participant_id != participant.participant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        annotations = await error_analysis_service.analyze_assessment(
            db=db,
            assessment_id=assessment_id,
            force_retry=force_retry,
        )
        return [
            AnnotationResponse(
                annotation_id=a.annotation_id,
                start_char=a.start_char,
                end_char=a.end_char,
                start_time_ms=a.start_time_ms,
                end_time_ms=a.end_time_ms,
                candidate_error=a.candidate_error,
                suggested_correction=a.suggested_correction,
                category_code=a.category_code,
                explanation=a.explanation,
                confidence=a.confidence,
                ai_status=a.ai_status,
                flag=a.flag,
                rubric_version=a.rubric_version,
                prompt_version=a.prompt_version,
                model_version=a.model_version,
            )
            for a in annotations
        ]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{assessment_id}/report", response_model=AssessmentReportResponse)
async def get_assessment_report(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentReportResponse:
    """Evidence Lens data provider with participant visibility gating (Signature Feature A)."""
    stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    # Authorization & Participant Visibility Check
    is_participant = current_user.role == UserRole.PARTICIPANT
    if is_participant:
        participant = await get_participant_for_user(current_user, db)
        if assessment.participant_id != participant.participant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Fetch annotations
    ann_stmt = (
        select(ErrorAnnotation)
        .where(ErrorAnnotation.assessment_id == assessment_id)
        .order_by(ErrorAnnotation.start_char.asc())
    )
    annotations = (await db.execute(ann_stmt)).scalars().all()

    # If user is participant and results are not released, redact annotations
    if is_participant and not assessment.is_visible_to_participant:
        return AssessmentReportResponse(
            assessment_id=assessment.assessment_id,
            assessment_type=assessment.assessment_type.value,
            status=assessment.status,
            transcript=assessment.transcript,
            word_count=assessment.word_count,
            is_visible_to_participant=False,
            banner_notice="Automated candidate analysis is being evaluated and will be released following review.",
            rubric_version=assessment.rubric_version,
            prompt_version=assessment.prompt_version,
            model_version=assessment.model_version,
            annotations=[],
        )

    return AssessmentReportResponse(
        assessment_id=assessment.assessment_id,
        assessment_type=assessment.assessment_type.value,
        status=assessment.status,
        transcript=assessment.transcript,
        word_count=assessment.word_count,
        is_visible_to_participant=assessment.is_visible_to_participant,
        banner_notice="Automated candidate analysis, not final until reviewed",
        rubric_version=assessment.rubric_version,
        prompt_version=assessment.prompt_version,
        model_version=assessment.model_version,
        annotations=[
            AnnotationResponse(
                annotation_id=a.annotation_id,
                start_char=a.start_char,
                end_char=a.end_char,
                start_time_ms=a.start_time_ms,
                end_time_ms=a.end_time_ms,
                candidate_error=a.candidate_error,
                suggested_correction=a.suggested_correction,
                category_code=a.category_code,
                explanation=a.explanation,
                confidence=a.confidence,
                ai_status=a.ai_status,
                flag=a.flag,
                rubric_version=a.rubric_version,
                prompt_version=a.prompt_version,
                model_version=a.model_version,
            )
            for a in annotations
        ],
    )


@router.post("/{assessment_id}/release", response_model=ReleaseResponse)
async def release_assessment_results(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> ReleaseResponse:
    """Release assessment candidate analysis for participant view."""
    try:
        updated = await error_analysis_service.release_results(
            db=db,
            assessment_id=assessment_id,
            researcher=current_user,
        )
        return ReleaseResponse(
            status="released",
            assessment_id=updated.assessment_id,
            is_visible_to_participant=updated.is_visible_to_participant,
            message="Assessment analysis results are now visible to the participant.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/review-queue", response_model=list[ReviewQueueItem])
async def get_review_queue(
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewQueueItem]:
    """List assessments with candidate annotations flagged for human review."""
    stmt = (
        select(Assessment)
        .where(Assessment.status.in_(["analyzed", "completed"]))
        .order_by(Assessment.created_at.desc())
    )
    assessments = (await db.execute(stmt)).scalars().all()

    queue_items: list[ReviewQueueItem] = []
    for ass in assessments:
        ann_stmt = select(ErrorAnnotation).where(ErrorAnnotation.assessment_id == ass.assessment_id)
        annotations = (await db.execute(ann_stmt)).scalars().all()

        needs_review = [a for a in annotations if a.ai_status == "needs_human_review"]
        if needs_review:
            part_stmt = select(Participant).where(Participant.participant_id == ass.participant_id)
            part = (await db.execute(part_stmt)).scalar_one_or_none()
            code = part.research_code if part else "UNKNOWN"

            queue_items.append(
                ReviewQueueItem(
                    assessment_id=ass.assessment_id,
                    participant_code=code,
                    assessment_type=ass.assessment_type.value,
                    needs_review_count=len(needs_review),
                    total_annotations=len(annotations),
                    created_at=ass.created_at.isoformat(),
                )
            )

    return queue_items
