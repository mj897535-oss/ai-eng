"""Participant and Researcher Dashboard Endpoints (Phase P13, SRS Section 9, FR-16, FR-17).

Implements:
- GET /dashboard/participant: Student Home data with progress ring and gentle next-best-action.
- GET /dashboard/progress: Student Progress data with category trends, repeated patterns, and plain-language explainer.
- GET /dashboard/researcher: Cohort overview with enrolment funnel, adherence, capacity/cost panel, and pure metrics group aggregates.
- GET /dashboard/researcher/participants: Cohort participant table.
- GET /dashboard/researcher/participants/{id}: Detailed per-participant drill-down.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.assessment import (
    Assessment,
    AssessmentType,
    ErrorAnnotation,
    STTJobMetric,
)
from app.models.consent import Consent, ConsentStatus
from app.models.identity import User, UserRole
from app.models.practice import PracticeEvent, PracticeSession, UtterancePattern
from app.models.research import Participant, StudyGroup
from app.research.metrics import (
    STANDARD_CAUTION_TEXT,
    compute_cohort_distribution,
    compute_group_comparative_aggregates,
)
from app.services.review import review_service
from app.services.tutor import tutor_service

router = APIRouter(prefix="/dashboard", tags=["Participant & Researcher Dashboards"])


async def get_participant_record(user: User, db: AsyncSession) -> Participant:
    stmt = select(Participant).where(Participant.user_id == user.id)
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current user is not registered as a research participant.",
        )
    return participant


# ----------------------------------------------------
# 1. Participant (Student) Home & Progress Endpoints
# ----------------------------------------------------

@router.get("/participant", response_model=dict[str, Any])
async def get_participant_home_dashboard(
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve Student Home screen data with stage progress ring and next-best-action."""
    participant = await get_participant_record(current_user, db)
    part_id = participant.participant_id

    # Check Consent
    consent_stmt = (
        select(Consent)
        .where(Consent.participant_id == part_id, Consent.status == ConsentStatus.CONSENTED)
        .order_by(Consent.created_at.desc())
    )
    consent = (await db.execute(consent_stmt)).scalars().first()
    has_consented = consent is not None

    # Check Pre-Test
    pre_stmt = (
        select(Assessment)
        .where(
            Assessment.participant_id == part_id,
            Assessment.assessment_type == AssessmentType.PRE,
            Assessment.is_official == True,
        )
        .order_by(Assessment.created_at.desc())
    )
    pre_ass = (await db.execute(pre_stmt)).scalars().first()

    # Check Post-Test
    post_stmt = (
        select(Assessment)
        .where(
            Assessment.participant_id == part_id,
            Assessment.assessment_type == AssessmentType.POST,
            Assessment.is_official == True,
        )
        .order_by(Assessment.created_at.desc())
    )
    post_ass = (await db.execute(post_stmt)).scalars().first()

    # Check Practice Sessions
    sess_stmt = select(PracticeSession).where(PracticeSession.participant_id == part_id)
    practice_sessions = (await db.execute(sess_stmt)).scalars().all()
    completed_practice_count = sum(1 for s in practice_sessions if s.status == "completed")
    total_active_seconds = sum(s.active_duration_seconds for s in practice_sessions)

    # Determine Study Stage & Progress Ring
    if not has_consented:
        stage = "consent"
        progress_pct = 10
        next_action = {
            "title": "Review & Sign Study Consent",
            "action_text": "Sign Consent",
            "route": "/onboarding",
            "description": "Please review the study information and provide your consent to begin.",
            "urgency": "high",
        }
    elif not pre_ass or pre_ass.status != "completed":
        stage = "pre_test"
        progress_pct = 25
        next_action = {
            "title": "Record Baseline Pre-Test",
            "action_text": "Start Pre-Test",
            "route": "/assessment/pre",
            "description": "Speak for one minute on your assigned daily routine topic.",
            "urgency": "high",
        }
    elif completed_practice_count < 3 and participant.study_group == StudyGroup.INTERVENTION:
        stage = "practising"
        progress_pct = 50 + int((completed_practice_count / 3.0) * 25)
        next_action = {
            "title": f"Practice Session {completed_practice_count + 1} of 3 Ready",
            "action_text": "Start Practice Turn",
            "route": "/tutor",
            "description": "Engage in a 15-minute conversational practice session with the Hint Ladder tutor.",
            "urgency": "medium",
        }
    elif not post_ass or post_ass.status != "completed":
        stage = "post_test"
        progress_pct = 75
        next_action = {
            "title": "Complete Final Post-Test",
            "action_text": "Start Post-Test",
            "route": "/assessment/post",
            "description": "Speak for one minute on your paired topic to evaluate your progress.",
            "urgency": "high",
        }
    else:
        stage = "completed"
        progress_pct = 100
        next_action = {
            "title": "Study Protocol Completed",
            "action_text": "View Progress Report",
            "route": "/dashboard/progress",
            "description": "Thank you! All study milestones have been successfully completed.",
            "urgency": "low",
        }

    # Recent Activity items
    activity_items = []
    if post_ass and post_ass.status == "completed":
        activity_items.append({
            "title": "Completed Post-Test Assessment",
            "timestamp": post_ass.created_at.isoformat(),
            "status": "completed",
        })
    for s in practice_sessions[-2:]:
        activity_items.append({
            "title": f"Tutoring Session ({s.topic or 'Grammar'})",
            "timestamp": s.start_time.isoformat() if s.start_time else None,
            "status": s.status,
            "active_minutes": round(s.active_duration_seconds / 60.0, 1),
        })
    if pre_ass and pre_ass.status == "completed":
        activity_items.append({
            "title": "Completed Baseline Pre-Test Assessment",
            "timestamp": pre_ass.created_at.isoformat(),
            "status": "completed",
        })

    # Blinding Check: pre/post assessment visibility
    is_pre_visible = pre_ass.is_visible_to_participant if pre_ass else False
    is_post_visible = post_ass.is_visible_to_participant if post_ass else False

    return {
        "participant_code": participant.research_code,
        "study_group": participant.study_group.value if hasattr(participant.study_group, "value") else str(participant.study_group),
        "stage": stage,
        "progress_percentage": progress_pct,
        "next_best_action": next_action,
        "pre_test_status": pre_ass.status if pre_ass else "not_started",
        "post_test_status": post_ass.status if post_ass else "not_started",
        "practice_sessions_completed": completed_practice_count,
        "total_active_minutes": round(total_active_seconds / 60.0, 1),
        "recent_activity": activity_items,
        "is_blinded": not (is_pre_visible and is_post_visible),
    }


@router.get("/progress", response_model=dict[str, Any])
async def get_participant_progress_screen(
    current_user: User = Depends(require_roles([UserRole.PARTICIPANT])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve Student Progress screen data with trends, repeated patterns, and plain-language explainer."""
    participant = await get_participant_record(current_user, db)
    part_id = participant.participant_id

    # 1. Practice history & recurrence patterns
    practice_history = await tutor_service.get_participant_history(db, part_id)
    patterns = await tutor_service.get_recurrence_patterns(db, part_id)

    # 2. Check assessments and unblinding status
    pre_stmt = (
        select(Assessment)
        .where(
            Assessment.participant_id == part_id,
            Assessment.assessment_type == AssessmentType.PRE,
            Assessment.is_official == True,
        )
        .order_by(Assessment.created_at.desc())
    )
    pre_ass = (await db.execute(pre_stmt)).scalars().first()

    post_stmt = (
        select(Assessment)
        .where(
            Assessment.participant_id == part_id,
            Assessment.assessment_type == AssessmentType.POST,
            Assessment.is_official == True,
        )
        .order_by(Assessment.created_at.desc())
    )
    post_ass = (await db.execute(post_stmt)).scalars().first()

    # Determine if comparative evaluation is released to learner
    is_released = bool(
        pre_ass and post_ass and
        pre_ass.status == "completed" and post_ass.status == "completed" and
        pre_ass.is_visible_to_participant and post_ass.is_visible_to_participant
    )

    comparative_summary = None
    if is_released and pre_ass and post_ass:
        from app.research.metrics import compute_comparative_report
        pre_eff = await review_service.get_effective_annotations(db, pre_ass.assessment_id)
        post_eff = await review_service.get_effective_annotations(db, post_ass.assessment_id)
        rep = compute_comparative_report(
            pre_annotations=pre_eff,
            pre_word_count=pre_ass.word_count,
            post_annotations=post_eff,
            post_word_count=post_ass.word_count,
            rubric_version=post_ass.rubric_version or pre_ass.rubric_version,
            is_pre_verified=pre_ass.is_verified,
            is_post_verified=post_ass.is_verified,
        )
        comparative_summary = {
            "pre_rate_per_100": rep["overall_comparison"]["pre_rate_per_100"],
            "post_rate_per_100": rep["overall_comparison"]["post_rate_per_100"],
            "absolute_reduction": rep["overall_comparison"]["absolute_reduction"],
            "relative_reduction_pct": rep["overall_comparison"]["relative_reduction_pct"],
            "is_provisional": rep["is_provisional"],
            "status_label": rep["status_label"],
            "post_assessment_id": str(post_ass.assessment_id),
            "category_comparisons": rep["category_comparisons"],
        }

    # Plain-language educational explainer (SRS Section 9)
    plain_language_explainer = {
        "title": "What do these numbers mean?",
        "intro": "SyntaxLens evaluates your spoken English syntax during spontaneous speaking tasks.",
        "sections": [
            {
                "term": "Error Rate per 100 Words",
                "explanation": "Instead of counting raw mistakes, we divide your errors by the total number of words you spoke and multiply by 100. This makes speaking samples of different lengths fair to compare.",
            },
            {
                "term": "Observed vs Not Observed",
                "explanation": "If a grammar structure (like Subject-Verb Agreement) had 0 errors in your post-test, we label it 'not observed in this sample'. In academic research, we never say 'mastered' because one speech sample does not prove permanent perfection.",
            },
            {
                "term": "Provisional vs Verified",
                "explanation": "AI first analyzes your audio, but a human research linguist reviews candidate deviations. While review is in progress, numbers are marked 'Provisional'.",
            },
            {
                "term": "Descriptive Practice Metrics",
                "explanation": "Practice sessions and self-correction rates describe your learning journey during tutoring. They are not official scores.",
            },
        ],
        "standard_caution": STANDARD_CAUTION_TEXT,
    }

    return {
        "participant_code": participant.research_code,
        "is_results_released": is_released,
        "total_practice_minutes": round(
            sum(s["active_duration_seconds"] for s in practice_history["sessions"]) / 60.0, 1
        ),
        "total_completed_sessions": practice_history["total_sessions"],
        "independent_correction_rate_pct": practice_history["correction_metrics"]["overall_rate_pct"],
        "repeated_error_patterns": patterns[:5],
        "category_breakdown": practice_history["correction_metrics"]["category_breakdown"],
        "comparative_summary": comparative_summary,
        "plain_language_explainer": plain_language_explainer,
    }


# ----------------------------------------------------
# 2. Researcher Dashboard Endpoints
# ----------------------------------------------------

@router.get("/researcher", response_model=dict[str, Any])
async def get_researcher_cohort_dashboard(
    group: str = Query(default="all", description="Group filter: all, intervention, or control"),
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve comprehensive Researcher Cohort Overview, aggregate pre/post distributions, and capacity panel."""
    # 1. Cohort Enrolment Funnel
    parts_stmt = select(Participant).where(Participant.is_active == True)
    participants = (await db.execute(parts_stmt)).scalars().all()
    total_enrolled = len(participants)

    # Consented count
    cons_stmt = select(func.count(func.distinct(Consent.participant_id))).where(Consent.status == ConsentStatus.CONSENTED)
    consented_count = (await db.execute(cons_stmt)).scalar() or 0

    # Assessments
    ass_stmt = select(Assessment).where(Assessment.is_official == True)
    assessments = (await db.execute(ass_stmt)).scalars().all()

    pre_completed_ids = {a.participant_id for a in assessments if a.assessment_type == AssessmentType.PRE and a.status == "completed"}
    post_completed_ids = {a.participant_id for a in assessments if a.assessment_type == AssessmentType.POST and a.status == "completed"}

    # Practice sessions
    sess_stmt = select(PracticeSession)
    practice_sessions = (await db.execute(sess_stmt)).scalars().all()
    practising_ids = {s.participant_id for s in practice_sessions if s.turns_count > 0}

    funnel = {
        "enrolled": total_enrolled,
        "consented": consented_count,
        "pre_test_completed": len(pre_completed_ids),
        "practising": len(practising_ids),
        "post_test_completed": len(post_completed_ids),
    }

    # Group Allocation
    intervention_count = sum(1 for p in participants if p.study_group == StudyGroup.INTERVENTION)
    control_count = sum(1 for p in participants if p.study_group == StudyGroup.CONTROL)

    # Missing Data & Drop-off warnings
    dropped_off = [p.research_code for p in participants if p.is_withdrawn]
    missing_pre = [p.research_code for p in participants if p.participant_id not in pre_completed_ids and not p.is_withdrawn]
    missing_post = [p.research_code for p in participants if p.participant_id in pre_completed_ids and p.participant_id not in post_completed_ids and not p.is_withdrawn]

    # Review queue size (annotations needing review)
    ann_unreviewed_stmt = select(func.count(ErrorAnnotation.annotation_id)).where(ErrorAnnotation.ai_status == "needs_human_review")
    review_queue_size = (await db.execute(ann_unreviewed_stmt)).scalar() or 0

    # Pipeline failures (retry_count > 0 or status == 'failed')
    failed_ass_stmt = select(func.count(Assessment.assessment_id)).where(Assessment.status.in_(["failed", "retrying"]))
    pipeline_failures = (await db.execute(failed_ass_stmt)).scalar() or 0

    # 2. Paired Aggregate Pre/Post Comparisons via Pure Metrics Module
    paired_data = []
    for p in participants:
        # Group filter
        p_grp = p.study_group.value if hasattr(p.study_group, "value") else str(p.study_group)
        if group != "all" and p_grp != group:
            continue

        p_pre = next((a for a in assessments if a.participant_id == p.participant_id and a.assessment_type == AssessmentType.PRE and a.status == "completed"), None)
        p_post = next((a for a in assessments if a.participant_id == p.participant_id and a.assessment_type == AssessmentType.POST and a.status == "completed"), None)

        if p_pre and p_post and p_pre.word_count > 0 and p_post.word_count > 0:
            pre_eff = await review_service.get_effective_annotations(db, p_pre.assessment_id)
            post_eff = await review_service.get_effective_annotations(db, p_post.assessment_id)

            pre_err = len([a for a in pre_eff if a.get("is_active_for_metrics", True) and a.get("review_status") not in ("rejected", "uncertain", "transcription_related", "acceptable_variation")])
            post_err = len([a for a in post_eff if a.get("is_active_for_metrics", True) and a.get("review_status") not in ("rejected", "uncertain", "transcription_related", "acceptable_variation")])

            pre_rate = round((pre_err / p_pre.word_count) * 100.0, 2)
            post_rate = round((post_err / p_post.word_count) * 100.0, 2)

            paired_data.append({
                "participant_id": str(p.participant_id),
                "research_code": p.research_code,
                "group": p_grp,
                "pre_rate": pre_rate,
                "post_rate": post_rate,
                "pre_error_count": pre_err,
                "post_error_count": post_err,
                "pre_word_count": p_pre.word_count,
                "post_word_count": p_post.word_count,
                "is_provisional": not (p_pre.is_verified and p_post.is_verified),
            })

    aggregates = compute_group_comparative_aggregates(paired_data)

    # 3. Capacity and Cost Panel (Design Target: 120 Participants)
    total_audio_seconds = sum(a.audio_duration_seconds or 60.0 for a in assessments)
    total_storage_mb = round((total_audio_seconds * 32_000) / (1024 * 1024), 2)  # ~32KB/s opus
    total_stt_minutes = round(total_audio_seconds / 60.0, 1)

    # STT & LLM calls
    stt_runs = len(assessments)
    llm_runs = len(assessments) + len(practice_sessions)

    # Cost model: STT ~ $0.006 / min, LLM ~ $0.015 / assessment or turn
    stt_cost = round(total_stt_minutes * 0.006, 2)
    llm_cost = round(llm_runs * 0.015, 2)
    total_cost_usd = round(stt_cost + llm_cost, 2)
    cost_per_participant = round(total_cost_usd / max(1, total_enrolled), 2)

    capacity_and_cost = {
        "design_target_participants": 120,
        "enrolled_participants": total_enrolled,
        "capacity_utilization_pct": round((total_enrolled / 120.0) * 100.0, 1),
        "total_storage_mb": total_storage_mb,
        "total_stt_calls": stt_runs,
        "total_llm_calls": llm_runs,
        "estimated_total_cost_usd": total_cost_usd,
        "estimated_cost_per_participant_usd": cost_per_participant,
        "headroom_participants": max(0, 120 - total_enrolled),
    }

    return {
        "filter_group": group,
        "funnel": funnel,
        "group_allocation": {
            "intervention": intervention_count,
            "control": control_count,
        },
        "missing_data": {
            "withdrawn_count": len(dropped_off),
            "missing_pre_count": len(missing_pre),
            "missing_post_count": len(missing_post),
            "withdrawn_participants": dropped_off,
        },
        "review_queue_size": review_queue_size,
        "pipeline_failures": pipeline_failures,
        "aggregates": {
            **aggregates,
            "standard_caution": STANDARD_CAUTION_TEXT,
        },
        "capacity_and_cost": capacity_and_cost,
    }


@router.get("/researcher/participants", response_model=list[dict[str, Any]])
async def list_cohort_participants(
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve cohort participant table with study status, practice minutes, and verification state."""
    stmt = select(Participant).where(Participant.is_active == True).order_by(Participant.research_code.asc())
    participants = (await db.execute(stmt)).scalars().all()

    # Preload assessments and practice sessions
    ass_stmt = select(Assessment).where(Assessment.is_official == True)
    assessments = (await db.execute(ass_stmt)).scalars().all()

    sess_stmt = select(PracticeSession)
    sessions = (await db.execute(sess_stmt)).scalars().all()

    rows = []
    for p in participants:
        p_pre = next((a for a in assessments if a.participant_id == p.participant_id and a.assessment_type == AssessmentType.PRE), None)
        p_post = next((a for a in assessments if a.participant_id == p.participant_id and a.assessment_type == AssessmentType.POST), None)
        p_sessions = [s for s in sessions if s.participant_id == p.participant_id]
        active_mins = round(sum(s.active_duration_seconds for s in p_sessions) / 60.0, 1)

        rows.append({
            "participant_id": str(p.participant_id),
            "research_code": p.research_code,
            "study_group": p.study_group.value if hasattr(p.study_group, "value") else str(p.study_group),
            "pre_test_status": p_pre.status if p_pre else "not_started",
            "pre_test_verified": p_pre.is_verified if p_pre else False,
            "post_test_status": p_post.status if p_post else "not_started",
            "post_test_verified": p_post.is_verified if p_post else False,
            "practice_sessions_count": len(p_sessions),
            "active_practice_minutes": active_mins,
            "is_withdrawn": p.is_withdrawn,
            "enrolled_at": p.created_at.isoformat() if p.created_at else None,
        })

    return rows


@router.get("/researcher/participants/{participant_id}", response_model=dict[str, Any])
async def get_participant_drilldown(
    participant_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.RESEARCHER_ADMIN, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve deep per-participant drilldown: timeline of events, assessments, verification state, practice minutes."""
    p_stmt = select(Participant).where(Participant.participant_id == participant_id)
    participant = (await db.execute(p_stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found.")

    # Assessments
    ass_stmt = (
        select(Assessment)
        .where(Assessment.participant_id == participant_id)
        .order_by(Assessment.created_at.desc())
    )
    assessments = (await db.execute(ass_stmt)).scalars().all()

    # Practice sessions & events
    practice_history = await tutor_service.get_participant_history(db, participant_id)
    patterns = await tutor_service.get_recurrence_patterns(db, participant_id)

    # Build timeline
    timeline = []
    for a in assessments:
        timeline.append({
            "event_type": f"assessment_{a.assessment_type.value}",
            "title": f"Submitted {a.assessment_type.value.capitalize()}-Test Recording",
            "timestamp": a.created_at.isoformat(),
            "status": a.status,
            "is_verified": a.is_verified,
            "word_count": a.word_count,
        })
    for s in practice_history["sessions"]:
        timeline.append({
            "event_type": "practice_session",
            "title": f"Tutoring Turn ({s.get('topic') or 'Grammar'})",
            "timestamp": s.get("start_time"),
            "status": s.get("status"),
            "active_minutes": round(s.get("active_duration_seconds", 0) / 60.0, 1),
            "turns_count": s.get("turns_count"),
        })

    timeline.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    return {
        "participant_id": str(participant.participant_id),
        "research_code": participant.research_code,
        "study_group": participant.study_group.value if hasattr(participant.study_group, "value") else str(participant.study_group),
        "is_withdrawn": participant.is_withdrawn,
        "enrolled_at": participant.created_at.isoformat() if participant.created_at else None,
        "timeline": timeline,
        "assessments": [
            {
                "assessment_id": str(a.assessment_id),
                "assessment_type": a.assessment_type.value,
                "status": a.status,
                "is_verified": a.is_verified,
                "word_count": a.word_count,
                "created_at": a.created_at.isoformat(),
            }
            for a in assessments
        ],
        "practice_history": practice_history,
        "patterns": patterns,
    }
