"""Researcher Admin User Management Router.

Enforces:
- Restricted to researcher_admin role.
- Cohort user listing, search, and filtering.
- Account provisioning with auto-assigned pseudonymous research codes for participants.
- Account deactivation with immediate session termination.
- Reviewer assignment to assessments (for row-level review access).
- Audit trail logging on all administrative actions.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import generate_secure_token, get_password_hash, validate_password_strength
from app.core.session import session_store
from app.models.assessment import Assessment, ReviewerAssignment
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.services.audit import AuditService

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


# --- Schemas ---

class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="User email address")
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole
    password: str | None = Field(default=None, description="Initial password; auto-generated if omitted")
    must_change_password: bool = True
    # Participant demographic fields (required if role is participant)
    research_code: str | None = None
    study_group: StudyGroup = StudyGroup.INTERVENTION
    mother_tongue: str = "English"
    school_medium: str = "English"
    age: int | None = None


class UserDetailResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    participant_id: uuid.UUID | None = None
    participant_code: str | None = None
    study_group: str | None = None


class PaginatedUsersResponse(BaseModel):
    items: list[UserDetailResponse]
    total: int
    limit: int
    offset: int


class ToggleStatusRequest(BaseModel):
    is_active: bool


class AssignReviewerRequest(BaseModel):
    reviewer_id: uuid.UUID
    assessment_id: uuid.UUID


# --- Endpoints ---

@router.get("", response_model=PaginatedUsersResponse)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_roles(UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER))],
    query: str | None = Query(None, description="Search by name, email, or research code"),
    role: str | None = Query(None, description="Filter by user role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaginatedUsersResponse:
    """List and filter users across the cohort."""
    # Count total
    count_stmt = select(func.count(User.id))
    if role:
        count_stmt = count_stmt.where(User.role == role)
    if is_active is not None:
        count_stmt = count_stmt.where(User.is_active == is_active)
    if query:
        pattern = f"%{query}%"
        count_stmt = count_stmt.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))

    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Query items
    stmt = select(User).order_by(desc(User.created_at)).offset(offset).limit(limit)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))

    users_res = await db.execute(stmt)
    users = users_res.scalars().all()

    # Bulk load participants for participant accounts
    user_ids = [u.id for u in users]
    part_stmt = select(Participant).where(Participant.user_id.in_(user_ids))
    part_res = await db.execute(part_stmt)
    part_map = {p.user_id: p for p in part_res.scalars().all()}

    items: list[UserDetailResponse] = []
    for u in users:
        p = part_map.get(u.id)
        items.append(
            UserDetailResponse(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role.value if hasattr(u.role, "value") else str(u.role),
                is_active=u.is_active,
                must_change_password=u.must_change_password,
                last_login_at=u.last_login_at,
                created_at=u.created_at,
                participant_id=p.participant_id if p else None,
                participant_code=p.research_code if p else None,
                study_group=p.study_group.value if p and hasattr(p.study_group, "value") else (p.study_group if p else None),
            )
        )

    return PaginatedUsersResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: CreateUserRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_roles(UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER))],
) -> UserDetailResponse:
    """Create a new user account with role-appropriate profiles."""
    # Check email duplicate
    existing = await db.execute(select(User).where(User.email == req.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{req.email}' already exists.",
        )

    # Determine password
    raw_password = req.password or f"SyntaxLens@{generate_secure_token(6)}!"
    valid, reason = validate_password_strength(raw_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason or "Password complexity requirement not met.",
        )

    hashed_pw = get_password_hash(raw_password)
    user_id = uuid.uuid4()

    new_user = User(
        id=user_id,
        email=req.email.lower(),
        full_name=req.full_name,
        hashed_password=hashed_pw,
        role=req.role,
        is_active=True,
        must_change_password=req.must_change_password,
        created_at=datetime.utcnow(),
    )
    db.add(new_user)
    await db.flush()

    participant: Participant | None = None
    if req.role in {UserRole.PARTICIPANT, UserRole.STUDENT}:
        # Generate pseudonymous research code if not supplied
        code = req.research_code or f"SL-{datetime.utcnow().year}-{str(uuid.uuid4())[:6].upper()}"
        participant = Participant(
            participant_id=uuid.uuid4(),
            research_code=code,
            user_id=new_user.id,
            age=req.age,
            mother_tongue=req.mother_tongue,
            school_medium=req.school_medium,
            country="India",
            study_group=req.study_group,
            is_withdrawn=False,
            created_at=datetime.utcnow(),
        )
        db.add(participant)
        await db.flush()

    await db.commit()
    await db.refresh(new_user)

    # Audit log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await AuditService.log(
        db=db,
        action="user_created",
        record_type="user",
        record_id=str(new_user.id),
        actor_id=current_admin.id,
        role=current_admin.role.value if hasattr(current_admin.role, "value") else str(current_admin.role),
        outcome="success",
        ip_address=client_ip,
        user_agent=user_agent,
        details={"email": new_user.email, "role": str(new_user.role)},
    )

    return UserDetailResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role.value if hasattr(new_user.role, "value") else str(new_user.role),
        is_active=new_user.is_active,
        must_change_password=new_user.must_change_password,
        last_login_at=None,
        created_at=new_user.created_at,
        participant_id=participant.participant_id if participant else None,
        participant_code=participant.research_code if participant else None,
        study_group=participant.study_group.value if participant and hasattr(participant.study_group, "value") else (participant.study_group if participant else None),
    )


@router.patch("/{user_id}/status", response_model=UserDetailResponse)
async def toggle_user_status(
    user_id: uuid.UUID,
    req: ToggleStatusRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_roles(UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER))],
) -> UserDetailResponse:
    """Activate or deactivate a user account."""
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account.",
        )

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_active = req.is_active
    await db.commit()

    # Invalidate all active sessions if deactivated
    if not req.is_active:
        await session_store.delete_user_sessions(user.id)

    # Audit log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await AuditService.log(
        db=db,
        action="user_deactivated" if not req.is_active else "user_activated",
        record_type="user",
        record_id=str(user.id),
        actor_id=current_admin.id,
        role=current_admin.role.value if hasattr(current_admin.role, "value") else str(current_admin.role),
        outcome="success",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    p_res = await db.execute(select(Participant).where(Participant.user_id == user.id))
    participant = p_res.scalar_one_or_none()

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        participant_id=participant.participant_id if participant else None,
        participant_code=participant.research_code if participant else None,
        study_group=participant.study_group.value if participant and hasattr(participant.study_group, "value") else (participant.study_group if participant else None),
    )


@router.post("/assign-reviewer")
async def assign_reviewer_to_assessment(
    req: AssignReviewerRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_roles(UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER))],
) -> dict[str, str]:
    """Assign an assessment to a reviewer to grant row-level review permission."""
    # Validate reviewer
    u_res = await db.execute(select(User).where(User.id == req.reviewer_id))
    reviewer = u_res.scalar_one_or_none()
    if not reviewer or reviewer.role != UserRole.REVIEWER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target user is not an active reviewer.")

    # Validate assessment
    a_res = await db.execute(select(Assessment).where(Assessment.assessment_id == req.assessment_id))
    assessment = a_res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    assignment = ReviewerAssignment(
        assignment_id=uuid.uuid4(),
        reviewer_id=req.reviewer_id,
        assessment_id=req.assessment_id,
        assigned_by=current_admin.id,
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(assignment)
    await db.commit()

    # Audit log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await AuditService.log(
        db=db,
        action="reviewer_assigned",
        record_type="assessment",
        record_id=str(req.assessment_id),
        actor_id=current_admin.id,
        role=current_admin.role.value if hasattr(current_admin.role, "value") else str(current_admin.role),
        outcome="success",
        ip_address=client_ip,
        user_agent=user_agent,
        details={"reviewer_id": str(req.reviewer_id)},
    )

    return {"message": "Reviewer successfully assigned to assessment."}
