"""Research Configuration, Freezing, and Diff API Endpoints (SRS FR-05, FR-08, FR-20).

Allows researcher_admin to:
- List and create versioned Rubrics, Prompts, Topic Pools, and Assessment Periods.
- Transition lifecycle from Draft -> Approved -> Frozen (strictly immutable).
- Test reproducible topic pair assignment from seeds.
- Compute unified side-by-side diffs between any two versions.
"""

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.config import (
    LifecycleState,
    PromptRole,
    PromptVersion,
    RubricVersion,
)
from app.models.identity import User, UserRole
from app.services.config import (
    PeriodInput,
    PromptInput,
    RubricInput,
    config_service,
)

router = APIRouter(prefix="/admin/config", tags=["Research Configuration & Freezing"])


# --- Schemas ---

class RubricCategorySchema(BaseModel):
    code: str
    name: str
    definition: str
    assessable_criteria: str
    variation_rules: str
    examples: list[dict[str, str]]
    is_expanded: bool = False


class RubricSummaryResponse(BaseModel):
    rubric_id: uuid.UUID
    version_code: str
    name: str
    description: str | None = None
    status: str
    is_frozen: bool
    approved_at: datetime | None = None
    frozen_at: datetime | None = None
    category_count: int
    created_at: datetime


class RubricDetailResponse(RubricSummaryResponse):
    categories: list[RubricCategorySchema]
    counting_rules: str
    word_counting_rules: str
    change_notes: str | None = None


class PromptSummaryResponse(BaseModel):
    prompt_id: uuid.UUID
    prompt_role: str
    version_code: str
    name: str
    status: str
    is_frozen: bool
    approved_at: datetime | None = None
    frozen_at: datetime | None = None
    output_schema_version: str
    created_at: datetime


class PromptDetailResponse(PromptSummaryResponse):
    prompt_template: str
    output_schema_json: str
    change_notes: str | None = None


class AssessmentPeriodResponse(BaseModel):
    period_id: uuid.UUID
    period_code: str
    name: str
    description: str | None = None
    rubric_version_code: str
    pre_prompt_version_code: str
    tutor_prompt_version_code: str
    post_prompt_version_code: str
    status: str
    is_frozen: bool
    is_active: bool
    start_date: datetime
    end_date: datetime | None = None
    frozen_at: datetime | None = None
    change_notes: str | None = None
    created_at: datetime


class TaskResponse(BaseModel):
    task_id: uuid.UUID
    title: str
    prompt_text: str
    equivalence_group: str
    task_type: str
    difficulty_level: str
    prep_time_seconds: int
    duration_seconds: int
    rubric_version: str
    is_active: bool
    created_at: datetime


# --- Rubric Endpoints ---

@router.get("/rubrics", response_model=list[RubricSummaryResponse])
async def list_rubrics(
    status_filter: LifecycleState | None = Query(None, alias="status"),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all rubric versions with their frozen state."""
    rubrics = await config_service.get_rubrics(db, status=status_filter)
    out = []
    for r in rubrics:
        try:
            cats = json.loads(r.categories_json)
        except Exception:
            cats = []
        out.append({
            "rubric_id": r.rubric_id,
            "version_code": r.version_code,
            "name": r.name,
            "description": r.description,
            "status": r.status.value,
            "is_frozen": r.is_frozen,
            "approved_at": r.approved_at,
            "frozen_at": r.frozen_at,
            "category_count": len(cats),
            "created_at": r.created_at,
        })
    return out


@router.get("/rubrics/{version_code}", response_model=RubricDetailResponse)
async def get_rubric(
    version_code: str,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get full rubric version details including taxonomy and counting rules."""
    rubric = await config_service.get_rubric(db, version_code)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rubric '{version_code}' not found.")

    try:
        cats = json.loads(rubric.categories_json)
    except Exception:
        cats = []

    return {
        "rubric_id": rubric.rubric_id,
        "version_code": rubric.version_code,
        "name": rubric.name,
        "description": rubric.description,
        "status": rubric.status.value,
        "is_frozen": rubric.is_frozen,
        "approved_at": rubric.approved_at,
        "frozen_at": rubric.frozen_at,
        "category_count": len(cats),
        "categories": cats,
        "counting_rules": rubric.counting_rules,
        "word_counting_rules": rubric.word_counting_rules,
        "change_notes": rubric.change_notes,
        "created_at": rubric.created_at,
    }


@router.post("/rubrics", response_model=RubricDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_rubric(
    payload: RubricInput,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new rubric in draft lifecycle state."""
    try:
        rubric = await config_service.create_rubric(
            db=db,
            input_data=payload,
            created_by=current_user.id,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    cats = json.loads(rubric.categories_json)
    return {
        "rubric_id": rubric.rubric_id,
        "version_code": rubric.version_code,
        "name": rubric.name,
        "description": rubric.description,
        "status": rubric.status.value,
        "is_frozen": rubric.is_frozen,
        "approved_at": rubric.approved_at,
        "frozen_at": rubric.frozen_at,
        "category_count": len(cats),
        "categories": cats,
        "counting_rules": rubric.counting_rules,
        "word_counting_rules": rubric.word_counting_rules,
        "change_notes": rubric.change_notes,
        "created_at": rubric.created_at,
    }


@router.post("/rubrics/{version_code}/freeze", response_model=RubricDetailResponse)
async def freeze_rubric(
    version_code: str,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Permanently freeze a rubric version. After freezing, it cannot be modified or deleted."""
    try:
        rubric = await config_service.freeze_rubric(
            db=db,
            version_code=version_code,
            actor_id=current_user.id,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    cats = json.loads(rubric.categories_json)
    return {
        "rubric_id": rubric.rubric_id,
        "version_code": rubric.version_code,
        "name": rubric.name,
        "description": rubric.description,
        "status": rubric.status.value,
        "is_frozen": rubric.is_frozen,
        "approved_at": rubric.approved_at,
        "frozen_at": rubric.frozen_at,
        "category_count": len(cats),
        "categories": cats,
        "counting_rules": rubric.counting_rules,
        "word_counting_rules": rubric.word_counting_rules,
        "change_notes": rubric.change_notes,
        "created_at": rubric.created_at,
    }


# --- Prompt Endpoints ---

@router.get("/prompts", response_model=list[PromptSummaryResponse])
async def list_prompts(
    role: PromptRole | None = Query(None, description="Filter by AI role"),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all prompt versions across roles (pre-test, tutor, post-test)."""
    prompts = await config_service.get_prompts(db, prompt_role=role)
    return [
        {
            "prompt_id": p.prompt_id,
            "prompt_role": p.prompt_role.value,
            "version_code": p.version_code,
            "name": p.name,
            "status": p.status.value,
            "is_frozen": p.is_frozen,
            "approved_at": p.approved_at,
            "frozen_at": p.frozen_at,
            "output_schema_version": p.output_schema_version,
            "created_at": p.created_at,
        }
        for p in prompts
    ]


@router.get("/prompts/{version_code}", response_model=PromptDetailResponse)
async def get_prompt(
    version_code: str,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get full prompt details including template and output JSON schema."""
    prompt = await config_service.get_prompt(db, version_code)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prompt '{version_code}' not found.")

    return {
        "prompt_id": prompt.prompt_id,
        "prompt_role": prompt.prompt_role.value,
        "version_code": prompt.version_code,
        "name": prompt.name,
        "status": prompt.status.value,
        "is_frozen": prompt.is_frozen,
        "approved_at": prompt.approved_at,
        "frozen_at": prompt.frozen_at,
        "output_schema_version": prompt.output_schema_version,
        "prompt_template": prompt.prompt_template,
        "output_schema_json": prompt.output_schema_json,
        "change_notes": prompt.change_notes,
        "created_at": prompt.created_at,
    }


@router.post("/prompts", response_model=PromptDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptInput,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new prompt version in draft status."""
    try:
        prompt = await config_service.create_prompt(
            db=db,
            input_data=payload,
            created_by=current_user.id,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return {
        "prompt_id": prompt.prompt_id,
        "prompt_role": prompt.prompt_role.value,
        "version_code": prompt.version_code,
        "name": prompt.name,
        "status": prompt.status.value,
        "is_frozen": prompt.is_frozen,
        "approved_at": prompt.approved_at,
        "frozen_at": prompt.frozen_at,
        "output_schema_version": prompt.output_schema_version,
        "prompt_template": prompt.prompt_template,
        "output_schema_json": prompt.output_schema_json,
        "change_notes": prompt.change_notes,
        "created_at": prompt.created_at,
    }


@router.post("/prompts/{version_code}/freeze", response_model=PromptDetailResponse)
async def freeze_prompt(
    version_code: str,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Freeze a prompt version permanently."""
    try:
        prompt = await config_service.freeze_prompt(
            db=db,
            version_code=version_code,
            actor_id=current_user.id,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "prompt_id": prompt.prompt_id,
        "prompt_role": prompt.prompt_role.value,
        "version_code": prompt.version_code,
        "name": prompt.name,
        "status": prompt.status.value,
        "is_frozen": prompt.is_frozen,
        "approved_at": prompt.approved_at,
        "frozen_at": prompt.frozen_at,
        "output_schema_version": prompt.output_schema_version,
        "prompt_template": prompt.prompt_template,
        "output_schema_json": prompt.output_schema_json,
        "change_notes": prompt.change_notes,
        "created_at": prompt.created_at,
    }


# --- Topic Bank & Assignment Endpoints ---

@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    equivalence_group: str | None = Query(None, description="Filter by equivalence group"),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List topics / assessment tasks from the bank."""
    tasks = await config_service.get_tasks(db, equivalence_group=equivalence_group, is_active=True)
    return [
        {
            "task_id": t.task_id,
            "title": t.title,
            "prompt_text": t.prompt_text,
            "equivalence_group": t.equivalence_group or "unassigned",
            "task_type": t.task_type or "any",
            "difficulty_level": t.difficulty_level,
            "prep_time_seconds": t.prep_time_seconds,
            "duration_seconds": t.duration_seconds,
            "rubric_version": t.rubric_version,
            "is_active": t.is_active,
            "created_at": t.created_at,
        }
        for t in tasks
    ]


@router.get("/tasks/assign")
async def assign_topic_pair(
    participant_id: str = Query(..., description="Participant identifier or research code"),
    seed: int | None = Query(None, description="Optional deterministic seed integer override"),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Test and verify reproducible topic pair assignment from seed or participant ID."""
    try:
        assignment = await config_service.assign_topic_pair(
            db=db,
            participant_identifier=participant_id,
            seed=seed,
        )
        return assignment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Assessment Period Endpoints ---

@router.get("/periods", response_model=list[AssessmentPeriodResponse])
async def list_periods(
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all assessment periods."""
    periods = await config_service.get_periods(db)
    return [
        {
            "period_id": p.period_id,
            "period_code": p.period_code,
            "name": p.name,
            "description": p.description,
            "rubric_version_code": p.rubric_version_code,
            "pre_prompt_version_code": p.pre_prompt_version_code,
            "tutor_prompt_version_code": p.tutor_prompt_version_code,
            "post_prompt_version_code": p.post_prompt_version_code,
            "status": p.status.value,
            "is_frozen": p.is_frozen,
            "is_active": p.is_active,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "frozen_at": p.frozen_at,
            "change_notes": p.change_notes,
            "created_at": p.created_at,
        }
        for p in periods
    ]


@router.post("/periods", response_model=AssessmentPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_period(
    payload: PeriodInput,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new assessment study period in draft state."""
    try:
        period = await config_service.create_period(
            db=db,
            input_data=payload,
            created_by=current_user.id,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "period_id": period.period_id,
        "period_code": period.period_code,
        "name": period.name,
        "description": period.description,
        "rubric_version_code": period.rubric_version_code,
        "pre_prompt_version_code": period.pre_prompt_version_code,
        "tutor_prompt_version_code": period.tutor_prompt_version_code,
        "post_prompt_version_code": period.post_prompt_version_code,
        "status": period.status.value,
        "is_frozen": period.is_frozen,
        "is_active": period.is_active,
        "start_date": period.start_date,
        "end_date": period.end_date,
        "frozen_at": period.frozen_at,
        "change_notes": period.change_notes,
        "created_at": period.created_at,
    }


@router.post("/periods/{period_code}/freeze", response_model=AssessmentPeriodResponse)
async def freeze_period(
    period_code: str,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Freeze an assessment period."""
    try:
        period = await config_service.freeze_period(
            db=db,
            period_code=period_code,
            actor_id=current_user.id,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "period_id": period.period_id,
        "period_code": period.period_code,
        "name": period.name,
        "description": period.description,
        "rubric_version_code": period.rubric_version_code,
        "pre_prompt_version_code": period.pre_prompt_version_code,
        "tutor_prompt_version_code": period.tutor_prompt_version_code,
        "post_prompt_version_code": period.post_prompt_version_code,
        "status": period.status.value,
        "is_frozen": period.is_frozen,
        "is_active": period.is_active,
        "start_date": period.start_date,
        "end_date": period.end_date,
        "frozen_at": period.frozen_at,
        "change_notes": period.change_notes,
        "created_at": period.created_at,
    }


# --- Unified Diff Viewer ---

@router.get("/diff")
async def compare_versions(
    type: str = Query(..., description="'rubric' or 'prompt'"),
    base_code: str = Query(..., description="Base version code"),
    target_code: str = Query(..., description="Target version code to compare against base"),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Compute line-by-line diff between two rubric or prompt versions."""
    if type == "rubric":
        r_base = await config_service.get_rubric(db, base_code)
        r_target = await config_service.get_rubric(db, target_code)
        if not r_base:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Base rubric '{base_code}' not found.")
        if not r_target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target rubric '{target_code}' not found.")

        # Format comparison text for rubrics
        def format_rubric(r: RubricVersion) -> str:
            lines = [
                f"Rubric: {r.name} ({r.version_code})",
                f"Status: {r.status.value} (Frozen: {r.is_frozen})",
                "",
                "=== COUNTING RULES ===",
                r.counting_rules,
                "",
                "=== WORD COUNTING RULES ===",
                r.word_counting_rules,
                "",
                "=== CATEGORY TAXONOMY ===",
            ]
            try:
                cats = json.loads(r.categories_json)
                for c in cats:
                    lines.append(f"[{c.get('code')}] {c.get('name')}")
                    lines.append(f"  Definition: {c.get('definition')}")
                    lines.append(f"  Criteria: {c.get('assessable_criteria')}")
                    lines.append(f"  Variation: {c.get('variation_rules')}")
                    lines.append(f"  Expanded: {c.get('is_expanded', False)}")
                    lines.append("")
            except Exception:
                lines.append(r.categories_json)
            return "\n".join(lines)

        base_str = format_rubric(r_base)
        target_str = format_rubric(r_target)
        diff_res = config_service.compute_diff(base_str, target_str, base_code, target_code)
        return {
            "type": "rubric",
            "base_code": base_code,
            "target_code": target_code,
            **diff_res,
        }

    elif type == "prompt":
        p_base = await config_service.get_prompt(db, base_code)
        p_target = await config_service.get_prompt(db, target_code)
        if not p_base:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Base prompt '{base_code}' not found.")
        if not p_target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target prompt '{target_code}' not found.")

        def format_prompt(p: PromptVersion) -> str:
            return (
                f"Prompt: {p.name} ({p.version_code})\n"
                f"Role: {p.prompt_role.value}\n"
                f"Output Schema: {p.output_schema_version}\n\n"
                f"=== TEMPLATE ===\n{p.prompt_template}\n\n"
                f"=== OUTPUT SCHEMA JSON ===\n{p.output_schema_json}\n"
            )

        base_str = format_prompt(p_base)
        target_str = format_prompt(p_target)
        diff_res = config_service.compute_diff(base_str, target_str, base_code, target_code)
        return {
            "type": "prompt",
            "base_code": base_code,
            "target_code": target_code,
            **diff_res,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comparison type must be 'rubric' or 'prompt'.",
        )
