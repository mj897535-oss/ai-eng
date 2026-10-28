"""Tests for Phase P13: Participant and Researcher Dashboards (SRS Section 9, FR-16, FR-17).

Verifies:
1. Dashboard numbers equal metrics module output (zero drift guarantee).
2. Participants cannot see other participants' or aggregate-with-identity data (RBAC + row-level isolation).
3. Empty/partial cohort data renders cleanly without crashing.
4. Student Home & Progress blinding protocol respected.
5. Researcher participant drilldown endpoint returns correct longitudinal timeline and recurrence patterns.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import (
    Assessment,
    AssessmentTask,
    AssessmentType,
    ErrorAnnotation,
)
from app.models.consent import Consent, ConsentStatus
from app.models.identity import User, UserRole
from app.models.practice import PracticeSession, UtterancePattern
from app.models.research import Participant, StudyGroup
from app.research.metrics import (
    compute_group_comparative_aggregates,
)
from tests.conftest import create_auth_headers_for


@pytest.mark.asyncio
async def test_dashboard_numbers_equal_metrics_module_output(
    client: AsyncClient,
    test_session: AsyncSession,
    seeded_data: dict[str, Any],
) -> None:
    """Guarantee zero drift: Researcher dashboard aggregates must equal pure metrics module output."""
    admin_user = seeded_data["admin"]

    # Create a fresh isolated participant to avoid unique constraints from seeded_data
    user_x = User(
        id=uuid.uuid4(),
        email="part_x@syntaxlens.edu",
        full_name="Participant X",
        hashed_password="pw_test_hash",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    part_x = Participant(
        participant_id=uuid.uuid4(),
        user_id=user_x.id,
        research_code="SL-2026-X01",
        study_group=StudyGroup.INTERVENTION,
        is_active=True,
    )
    consent_x = Consent(
        consent_id=uuid.uuid4(),
        participant_id=part_x.participant_id,
        consent_version="v1.0-jam-2026",
        status=ConsentStatus.CONSENTED,
    )
    test_session.add_all([user_x, part_x, consent_x])
    await test_session.flush()

    # 1. Create Pre & Post assessments for Participant X
    task_pre = AssessmentTask(
        task_id=uuid.uuid4(),
        title="Daily Commute Pre",
        prompt_text="Describe your daily commute.",
        equivalence_group="pair_commute_work",
        rubric_version="v1.0-jam-phd",
    )
    task_post = AssessmentTask(
        task_id=uuid.uuid4(),
        title="Work Routine Post",
        prompt_text="Describe your work routine.",
        equivalence_group="pair_commute_work",
        rubric_version="v1.0-jam-phd",
    )
    test_session.add_all([task_pre, task_post])
    await test_session.flush()

    pre_ass_x = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=part_x.participant_id,
        task_id=task_pre.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/pre_x.webm",
        status="completed",
        is_official=True,
        is_verified=True,
        word_count=100,
        audio_duration_seconds=55.0,
        is_visible_to_participant=True,
        stt_version="mock-stt-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-syntax-v1",
        prompt_version="v1.0-assessor",
    )
    post_ass_x = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=part_x.participant_id,
        task_id=task_post.task_id,
        assessment_type=AssessmentType.POST,
        audio_key="audio/post_x.webm",
        status="completed",
        is_official=True,
        is_verified=True,
        word_count=100,
        audio_duration_seconds=58.0,
        is_visible_to_participant=True,
        stt_version="mock-stt-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-syntax-v1",
        prompt_version="v1.0-assessor",
    )
    test_session.add_all([pre_ass_x, post_ass_x])
    await test_session.flush()

    # Add 6 pre errors and 2 post errors for Participant X
    for i in range(6):
        ann = ErrorAnnotation(
            annotation_id=uuid.uuid4(),
            assessment_id=pre_ass_x.assessment_id,
            start_char=i * 10,
            end_char=i * 10 + 5,
            candidate_error=f"error_{i}",
            suggested_correction=f"correct_{i}",
            category_code="TNS",
            explanation="Tense deviation",
            confidence=0.95,
            ai_status="suggested",
            flag="candidate_error",
            model_version="mock-syntax-v1",
            origin="ai",
        )
        test_session.add(ann)

    for i in range(2):
        ann = ErrorAnnotation(
            annotation_id=uuid.uuid4(),
            assessment_id=post_ass_x.assessment_id,
            start_char=i * 10,
            end_char=i * 10 + 5,
            candidate_error=f"error_{i}",
            suggested_correction=f"correct_{i}",
            category_code="TNS",
            explanation="Tense deviation",
            confidence=0.95,
            ai_status="suggested",
            flag="candidate_error",
            model_version="mock-syntax-v1",
            origin="ai",
        )
        test_session.add(ann)

    await test_session.flush()

    # 2. Call Researcher Dashboard Endpoint for intervention group
    headers = await create_auth_headers_for(admin_user)
    res = await client.get("/api/v1/dashboard/researcher?group=intervention", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    # 3. Calculate directly via pure metrics module
    paired_sample = [
        {
            "participant_id": str(part_x.participant_id),
            "research_code": part_x.research_code,
            "group": "intervention",
            "pre_rate": 6.0,  # 6 / 100 * 100
            "post_rate": 2.0,  # 2 / 100 * 100
            "pre_error_count": 6,
            "post_error_count": 2,
            "pre_word_count": 100,
            "post_word_count": 100,
            "is_provisional": False,
        }
    ]
    expected_aggregates = compute_group_comparative_aggregates(paired_sample)

    # 4. Zero Drift Assertions
    api_aggs = data["aggregates"]
    assert api_aggs["n"] == expected_aggregates["n"] == 1
    assert api_aggs["total_pre_errors"] == expected_aggregates["total_pre_errors"] == 6
    assert api_aggs["total_post_errors"] == expected_aggregates["total_post_errors"] == 2
    assert api_aggs["pre_distribution"]["mean"] == expected_aggregates["pre_distribution"]["mean"] == 6.0
    assert api_aggs["post_distribution"]["mean"] == expected_aggregates["post_distribution"]["mean"] == 2.0
    assert api_aggs["absolute_reduction_distribution"]["mean"] == expected_aggregates["absolute_reduction_distribution"]["mean"] == 4.0
    assert api_aggs["mean_relative_reduction_pct"] == expected_aggregates["mean_relative_reduction_pct"] == 66.7


@pytest.mark.asyncio
async def test_cross_participant_isolation_enforced(
    client: AsyncClient,
    test_session: AsyncSession,
    seeded_data: dict[str, Any],
) -> None:
    """RBAC & Row-level isolation: participants cannot access researcher data or other participants."""
    user_a = seeded_data["user_a"]
    part_b = seeded_data["participant_b"]

    headers_a = await create_auth_headers_for(user_a)

    # 1. Participant A cannot access researcher cohort overview
    res_cohort = await client.get("/api/v1/dashboard/researcher", headers=headers_a)
    assert res_cohort.status_code == 403

    # 2. Participant A cannot access researcher cohort participant list
    res_roster = await client.get("/api/v1/dashboard/researcher/participants", headers=headers_a)
    assert res_roster.status_code == 403

    # 3. Participant A cannot access participant drilldown endpoint
    res_drill = await client.get(
        f"/api/v1/dashboard/researcher/participants/{part_b.participant_id}",
        headers=headers_a,
    )
    assert res_drill.status_code == 403


@pytest.mark.asyncio
async def test_empty_cohort_dashboard_renders_cleanly(
    client: AsyncClient,
    test_session: AsyncSession,
) -> None:
    """Empty database: researcher dashboard returns valid zero distributions without dividing by zero."""
    admin = User(
        id=uuid.uuid4(),
        email="solo_admin@syntaxlens.edu",
        full_name="Solo Admin",
        hashed_password="hashed_pw_test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_session.add(admin)
    await test_session.flush()

    headers = await create_auth_headers_for(admin)
    res = await client.get("/api/v1/dashboard/researcher?group=all", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["funnel"]["enrolled"] == 0
    assert data["aggregates"]["n"] == 0
    assert data["aggregates"]["pre_distribution"]["mean"] == 0.0
    assert data["aggregates"]["pre_distribution"]["std_dev"] == 0.0
    assert data["capacity_and_cost"]["design_target_participants"] == 120
    assert data["capacity_and_cost"]["enrolled_participants"] == 0


@pytest.mark.asyncio
async def test_student_home_and_progress_blinding_respected(
    client: AsyncClient,
    test_session: AsyncSession,
    seeded_data: dict[str, Any],
) -> None:
    """Blinding protocol: results are masked from student when assessments are not flagged visible."""
    # Create fresh participant Y
    user_y = User(
        id=uuid.uuid4(),
        email="part_y@syntaxlens.edu",
        full_name="Participant Y",
        hashed_password="pw_test_hash",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    part_y = Participant(
        participant_id=uuid.uuid4(),
        user_id=user_y.id,
        research_code="SL-2026-Y01",
        study_group=StudyGroup.CONTROL,
        is_active=True,
    )
    consent_y = Consent(
        consent_id=uuid.uuid4(),
        participant_id=part_y.participant_id,
        consent_version="v1.0-jam-2026",
        status=ConsentStatus.CONSENTED,
    )
    test_session.add_all([user_y, part_y, consent_y])
    await test_session.flush()

    # Pre-test marked completed but NOT visible
    task = AssessmentTask(
        task_id=uuid.uuid4(),
        title="Blinded Task",
        prompt_text="Speak freely.",
        equivalence_group="grp_test",
        rubric_version="v1.0-jam-phd",
    )
    test_session.add(task)
    await test_session.flush()

    pre_ass = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=part_y.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/blinded.webm",
        status="completed",
        is_official=True,
        is_verified=False,
        word_count=120,
        is_visible_to_participant=False,  # BLINDED
        stt_version="mock-stt-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-syntax-v1",
        prompt_version="v1.0-assessor",
    )
    test_session.add(pre_ass)
    await test_session.flush()

    headers = await create_auth_headers_for(user_y, part_y)

    # 1. Student Home
    res_home = await client.get("/api/v1/dashboard/participant", headers=headers)
    assert res_home.status_code == 200
    home_data = res_home.json()
    assert home_data["is_blinded"] is True

    # 2. Student Progress
    res_prog = await client.get("/api/v1/dashboard/progress", headers=headers)
    assert res_prog.status_code == 200
    prog_data = res_prog.json()
    assert prog_data["is_results_released"] is False
    assert prog_data["comparative_summary"] is None


@pytest.mark.asyncio
async def test_researcher_participant_drilldown(
    client: AsyncClient,
    test_session: AsyncSession,
    seeded_data: dict[str, Any],
) -> None:
    """Researcher drilldown returns longitudinal timeline, assessment items, and recurrence patterns."""
    admin_user = seeded_data["admin"]
    part_a = seeded_data["participant_a"]

    # Add practice session and pattern
    sess = PracticeSession(
        session_id=uuid.uuid4(),
        participant_id=part_a.participant_id,
        tutor_prompt_version="v1.0-tutor",
        status="completed",
        active_duration_seconds=600,
        turns_count=4,
    )
    test_session.add(sess)
    await test_session.flush()

    pattern = UtterancePattern(
        pattern_id=uuid.uuid4(),
        participant_id=part_a.participant_id,
        target_category="SVA",
        utterance_fingerprint="she_play_tennis",
        canonical_phrase="she play tennis every sunday",
        occurrence_count=3,
        first_session_id=sess.session_id,
        last_session_id=sess.session_id,
    )
    test_session.add(pattern)
    await test_session.flush()

    headers = await create_auth_headers_for(admin_user)
    res = await client.get(
        f"/api/v1/dashboard/researcher/participants/{part_a.participant_id}",
        headers=headers,
    )
    assert res.status_code == 200
    drill_data = res.json()

    assert drill_data["research_code"] == part_a.research_code
    assert drill_data["study_group"] == "intervention"
    assert len(drill_data["timeline"]) >= 1
    assert len(drill_data["patterns"]) >= 1
    assert drill_data["patterns"][0]["utterance_fingerprint"] == "she_play_tennis"
    assert drill_data["patterns"][0]["occurrence_count"] == 3
