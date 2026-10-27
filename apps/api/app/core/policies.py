"""Row-Level Object Ownership & Access Control Policies.

Enforces:
- Participants can ONLY read or modify their own participant and assessment records.
- Reviewers can ONLY access assessments explicitly assigned to them via reviewer_assignments.
- Researcher administrators can access research data across the entire cohort.
- Access to raw audio recordings is verified and automatically audited (SRS FR-19).
"""

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment, ReviewerAssignment
from app.models.identity import User, UserRole
from app.models.research import Participant
from app.services.audit import AuditService


async def authorize_participant_access(
    current_user: User,
    participant_id: uuid.UUID,
    db: AsyncSession,
) -> Participant:
    """Authorize access to a Participant entity."""
    stmt = select(Participant).where(Participant.participant_id == participant_id)
    result = await db.execute(stmt)
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found.",
        )

    # Lead Researcher / Admin has cohort-wide oversight
    if current_user.role in {UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER}:
        return participant

    # Participant role: strict ownership check
    if current_user.role in {UserRole.PARTICIPANT, UserRole.STUDENT}:
        if participant.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view other participants' research records.",
            )
        return participant

    # Reviewers cannot access raw participant identity/demographics directly
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Reviewers cannot access participant profiles.",
    )


async def authorize_assessment_access(
    current_user: User,
    assessment_id: uuid.UUID,
    db: AsyncSession,
) -> Assessment:
    """Authorize access to an Assessment record."""
    stmt = (
        select(Assessment)
        .options(selectinload(Assessment.participant))
        .where(Assessment.assessment_id == assessment_id)
    )
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment {assessment_id} not found.",
        )

    # 1. Lead Researcher / Admin: authorized
    if current_user.role in {UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER}:
        return assessment

    # 2. Participant: authorized only if it belongs to their own participant profile
    if current_user.role in {UserRole.PARTICIPANT, UserRole.STUDENT}:
        if not assessment.participant or assessment.participant.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view another participant's assessment.",
            )
        return assessment

    # 3. Reviewer: authorized ONLY if explicitly assigned
    if current_user.role == UserRole.REVIEWER:
        assign_stmt = select(ReviewerAssignment).where(
            ReviewerAssignment.reviewer_id == current_user.id,
            ReviewerAssignment.assessment_id == assessment_id,
            ReviewerAssignment.status == "active",
        )
        assign_res = await db.execute(assign_stmt)
        assignment = assign_res.scalar_one_or_none()

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Reviewers may only access assessments explicitly assigned to them.",
            )
        return assessment

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Unauthorized role.",
    )


async def authorize_recording_access(
    current_user: User,
    assessment_id: uuid.UUID,
    db: AsyncSession,
    request: Request,
) -> Assessment:
    """Authorize access to raw audio recording and log to append-only audit trail."""
    assessment = await authorize_assessment_access(current_user, assessment_id, db)

    # Audit the recording access event per SRS FR-19
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await AuditService.log_recording_access(
        db=db,
        actor_id=current_user.id,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        assessment_id=assessment.assessment_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return assessment
