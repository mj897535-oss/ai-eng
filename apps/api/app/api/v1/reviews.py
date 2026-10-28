"""Reviewer Cockpit API Endpoints (Phase P9, Signature Feature D).

Implements:
- GET /reviews/queue: Filtered review queue with reviewer workload statistics.
- POST /reviews/assignments: Assign assessment to reviewer(s).
- GET /reviews/cockpit/{id}: Cockpit data provider with waveform alignment and effective annotation set.
- POST /reviews/cockpit/{id}/decisions: Record append-only decision (Accept/Reject/Edit/Recategorise/Uncertain).
- POST /reviews/cockpit/{id}/annotations: Add reviewer-originated missed candidate error.
- GET /reviews/agreement-stats: Category-wise AI concordance and Cohen's Kappa.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.assessment import (
    Assessment,
    ErrorAnnotation,
    ReviewDecisionType,
    ReviewerAssignment,
)
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.services.review import review_service

router = APIRouter(prefix="/reviews", tags=["Reviewer Cockpit & Adjudication"])


# --- Schemas ---

class AssignmentCreate(BaseModel):
    assessment_id: uuid.UUID
    reviewer_id: uuid.UUID
    review_round: int = Field(default=1, ge=1, le=2)


class DecisionCreate(BaseModel):
    annotation_id: uuid.UUID
    decision: ReviewDecisionType
    edited_span: str | None = None
    edited_start_char: int | None = None
    edited_end_char: int | None = None
    edited_category: str | None = None
    edited_correction: str | None = None
    edited_explanation: str | None = None
    reason: str | None = None
    notes: str | None = None


class AddMissedAnnotationCreate(BaseModel):
    span_text: str
    start_char: int
    end_char: int
    category_code: str
    suggested_correction: str
    explanation: str
    reason: str | None = None
    start_time_ms: int | None = None
    end_time_ms: int | None = None


class QueueItemResponse(BaseModel):
    assessment_id: uuid.UUID
    participant_code: str
    study_group: str
    assessment_type: str
    review_status: str
    is_verified: bool
    total_candidates: int
    resolved_candidates: int
    unresolved_candidates: int
    assigned_reviewers: list[str]
    submitted_at: str


class CockpitCandidateItem(BaseModel):
    annotation_id: str
    start_char: int
    end_char: int
    start_time_ms: int | None
    end_time_ms: int | None
    span_text: str
    category_code: str
    suggested_correction: str
    explanation: str
    confidence: float
    origin: str  # "ai" or "reviewer"
    review_status: str  # "unreviewed", "accepted", "rejected", "edited", etc.
    decision_id: str | None
    reason: str | None
    is_active_for_metrics: bool
    flag: str


class CockpitDataResponse(BaseModel):
    assessment_id: uuid.UUID
    participant_code: str
    study_group: str
    assessment_type: str
    review_status: str
    is_verified: bool
    transcript: str
    word_count: int
    audio_key: str
    audio_url: str | None
    rubric_version: str
    model_version: str
    effective_annotations: list[CockpitCandidateItem]


# --- Endpoints ---

@router.get("/queue", response_model=dict[str, Any])
async def get_reviewer_queue(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    confidence_band: str | None = Query(default=None),  # "low", "high"
    assessment_type: str | None = Query(default=None),
    study_group: str | None = Query(default=None),
    reviewer_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Multi-criteria filtered review queue with workload counts."""
    # 1. Base query for analyzed or completed assessments
    query = (
        select(Assessment, Participant)
        .join(Participant, Assessment.participant_id == Participant.participant_id)
        .where(Assessment.status.in_(["analyzed", "completed"]))
        .order_by(Assessment.created_at.desc())
    )

    # 2. Row-Level Ownership: If role is reviewer, only show assigned assessments
    if current_user.role == UserRole.REVIEWER:
        assigned_subquery = (
            select(ReviewerAssignment.assessment_id)
            .where(
                ReviewerAssignment.reviewer_id == current_user.id,
                ReviewerAssignment.status == "active",
            )
        )
        query = query.where(Assessment.assessment_id.in_(assigned_subquery))
    elif reviewer_id:
        assigned_subquery = (
            select(ReviewerAssignment.assessment_id)
            .where(
                ReviewerAssignment.reviewer_id == reviewer_id,
                ReviewerAssignment.status == "active",
            )
        )
        query = query.where(Assessment.assessment_id.in_(assigned_subquery))

    # 3. Filters
    if status_filter:
        if status_filter == "unreviewed":
            query = query.where(Assessment.review_status == "unreviewed")
        elif status_filter == "partially_reviewed":
            query = query.where(Assessment.review_status == "partially_reviewed")
        elif status_filter == "verified":
            query = query.where(Assessment.review_status == "verified")

    if assessment_type:
        query = query.where(Assessment.assessment_type == assessment_type)

    if study_group:
        query = query.where(Participant.study_group == study_group)

    rows = (await db.execute(query)).all()

    queue_items: list[QueueItemResponse] = []
    for ass, part in rows:
        # Fetch annotations for candidate breakdown
        ann_stmt = select(ErrorAnnotation).where(ErrorAnnotation.assessment_id == ass.assessment_id)
        annotations = (await db.execute(ann_stmt)).scalars().all()

        if category and not any(a.category_code == category for a in annotations):
            continue

        if confidence_band:
            if confidence_band == "low" and not any(a.confidence < 0.85 for a in annotations):
                continue
            if confidence_band == "high" and not any(a.confidence >= 0.85 for a in annotations):
                continue

        # Effective status counts
        eff_list = await review_service.get_effective_annotations(db, ass.assessment_id)
        resolved = sum(1 for e in eff_list if e["review_status"] != "unreviewed")
        total = len(eff_list)

        # Assigned reviewers
        asgn_stmt = (
            select(User.full_name)
            .join(ReviewerAssignment, User.id == ReviewerAssignment.reviewer_id)
            .where(ReviewerAssignment.assessment_id == ass.assessment_id)
        )
        asgn_names = (await db.execute(asgn_stmt)).scalars().all()

        queue_items.append(
            QueueItemResponse(
                assessment_id=ass.assessment_id,
                participant_code=part.research_code,
                study_group=part.study_group.value if hasattr(part.study_group, "value") else str(part.study_group),
                assessment_type=ass.assessment_type.value,
                review_status=ass.review_status,
                is_verified=ass.is_verified,
                total_candidates=total,
                resolved_candidates=resolved,
                unresolved_candidates=total - resolved,
                assigned_reviewers=list(asgn_names),
                submitted_at=ass.created_at.isoformat(),
            )
        )

    # Workload summary
    workload = await review_service.get_workload_counts(db, current_user)

    return {
        "items": queue_items,
        "total": len(queue_items),
        "workload": workload,
    }


@router.post("/assignments", response_model=dict[str, Any])
async def create_reviewer_assignment(
    payload: AssignmentCreate,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Assign an assessment to a reviewer."""
    assignment = await review_service.assign_reviewer(
        db=db,
        assessment_id=payload.assessment_id,
        reviewer_id=payload.reviewer_id,
        assigned_by=current_user.id,
        review_round=payload.review_round,
    )
    return {
        "status": "assigned",
        "assignment_id": assignment.assignment_id,
        "assessment_id": assignment.assessment_id,
        "reviewer_id": assignment.reviewer_id,
        "review_round": assignment.review_round,
    }


@router.get("/cockpit/{assessment_id}", response_model=CockpitDataResponse)
async def get_assessment_cockpit_data(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> CockpitDataResponse:
    """Cockpit data provider: audio key, transcript, and effective annotation set."""
    # Enforce row-level assignment access
    has_access = await review_service.check_reviewer_access(db, assessment_id, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not assigned to review this assessment.",
        )

    stmt = (
        select(Assessment, Participant)
        .join(Participant, Assessment.participant_id == Participant.participant_id)
        .where(Assessment.assessment_id == assessment_id)
    )
    res = (await db.execute(stmt)).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    assessment, participant = res

    # Compute effective annotations
    target_rev = current_user.id if current_user.role == UserRole.REVIEWER else None
    effective_items = await review_service.get_effective_annotations(
        db=db,
        assessment_id=assessment_id,
        target_reviewer_id=target_rev,
    )

    return CockpitDataResponse(
        assessment_id=assessment.assessment_id,
        participant_code=participant.research_code,
        study_group=participant.study_group.value if hasattr(participant.study_group, "value") else str(participant.study_group),
        assessment_type=assessment.assessment_type.value,
        review_status=assessment.review_status,
        is_verified=assessment.is_verified,
        transcript=assessment.transcript or "",
        word_count=assessment.word_count,
        audio_key=assessment.audio_key,
        audio_url=f"/api/v1/assessments/{assessment.assessment_id}/audio-url",
        rubric_version=assessment.rubric_version,
        model_version=assessment.model_version,
        effective_annotations=[CockpitCandidateItem(**item) for item in effective_items],
    )


@router.post("/cockpit/{assessment_id}/decisions", response_model=dict[str, Any])
async def record_candidate_decision(
    assessment_id: uuid.UUID,
    payload: DecisionCreate,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record an append-only reviewer decision (Accept/Reject/Edit/Recategorise/Uncertain)."""
    # Enforce row-level assignment access
    has_access = await review_service.check_reviewer_access(db, assessment_id, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not assigned to review this assessment.",
        )

    decision = await review_service.record_decision(
        db=db,
        assessment_id=assessment_id,
        annotation_id=payload.annotation_id,
        reviewer=current_user,
        decision=payload.decision,
        edited_span=payload.edited_span,
        edited_start_char=payload.edited_start_char,
        edited_end_char=payload.edited_end_char,
        edited_category=payload.edited_category,
        edited_correction=payload.edited_correction,
        edited_explanation=payload.edited_explanation,
        reason=payload.reason,
        notes=payload.notes,
    )

    return {
        "status": "recorded",
        "decision_id": decision.decision_id,
        "annotation_id": decision.annotation_id,
        "decision": decision.decision.value,
        "timestamp": decision.created_at.isoformat(),
    }


@router.post("/cockpit/{assessment_id}/annotations", response_model=dict[str, Any])
async def add_missed_candidate_annotation(
    assessment_id: uuid.UUID,
    payload: AddMissedAnnotationCreate,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add a reviewer-originated annotation for an error missed by AI."""
    # Enforce row-level assignment access
    has_access = await review_service.check_reviewer_access(db, assessment_id, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not assigned to review this assessment.",
        )

    ann = await review_service.add_reviewer_annotation(
        db=db,
        assessment_id=assessment_id,
        reviewer=current_user,
        span_text=payload.span_text,
        start_char=payload.start_char,
        end_char=payload.end_char,
        category_code=payload.category_code,
        suggested_correction=payload.suggested_correction,
        explanation=payload.explanation,
        reason=payload.reason,
        start_time_ms=payload.start_time_ms,
        end_time_ms=payload.end_time_ms,
    )

    return {
        "status": "added",
        "annotation_id": ann.annotation_id,
        "origin": ann.origin,
        "category_code": ann.category_code,
        "candidate_error": ann.candidate_error,
    }


@router.get("/agreement-stats", response_model=dict[str, Any])
async def get_agreement_statistics(
    assessment_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get Reviewer-vs-AI agreement breakdown by category and inter-reviewer Cohen's Kappa."""
    return await review_service.calculate_agreement_stats(db, assessment_id)
