"""Unit and Integration Tests for Phase P9 Reviewer Cockpit & Adjudication (Signature Feature D).

Tests:
1. AI row unchanged after any reviewer action (database immutability).
2. ReviewerDecision row immutability (decisions are append-only).
3. Derived view correctness (Effective Annotation Set reflects AI, accepted, edited, rejected, and added).
4. Assessment-level sign-off: assessment is verified ONLY when all candidates are resolved.
5. Row-level access control: reviewer access strictly limited to assigned records.
6. Double-review Cohen's Kappa calculation against a known worked example.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import (
    Assessment,
    AssessmentTask,
    AssessmentType,
    ErrorAnnotation,
    ReviewDecisionType,
)
from app.models.consent import Consent, ConsentStatus
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.research.metrics import calculate_cohens_kappa
from app.services.review import review_service


@pytest_asyncio.fixture
async def setup_review_fixtures(test_session: AsyncSession):
    """Seed test data for reviewer cockpit testing."""
    # 1. Users
    researcher = User(
        id=uuid.uuid4(),
        email="researcher.cockpit@syntaxlens.edu",
        hashed_password="argon2id$mockhash",
        full_name="Dr. Eleanor Vance",
        role=UserRole.RESEARCHER_ADMIN,
        is_active=True,
    )
    reviewer_1 = User(
        id=uuid.uuid4(),
        email="rev1@syntaxlens.edu",
        hashed_password="argon2id$mockhash",
        full_name="Calibrated Reviewer 1",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    reviewer_2 = User(
        id=uuid.uuid4(),
        email="rev2@syntaxlens.edu",
        hashed_password="argon2id$mockhash",
        full_name="Calibrated Reviewer 2",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    participant_user = User(
        id=uuid.uuid4(),
        email="p1.cockpit@syntaxlens.edu",
        hashed_password="argon2id$mockhash",
        full_name="Research Participant P1",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    test_session.add_all([researcher, reviewer_1, reviewer_2, participant_user])
    await test_session.flush()

    # 2. Participant & Consent
    participant = Participant(
        participant_id=uuid.uuid4(),
        user_id=participant_user.id,
        research_code="SL-2026-9001",
        study_group=StudyGroup.INTERVENTION,
    )
    consent = Consent(
        consent_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        consent_version="v1.0-jam-2026",
        status=ConsentStatus.CONSENTED,
    )
    test_session.add_all([participant, consent])
    await test_session.flush()

    # 3. Assessment Task & Assessment
    task = AssessmentTask(
        task_id=uuid.uuid4(),
        title="Cockpit Daily Routine Task",
        prompt_text="Describe your daily routine.",
        rubric_version="v1.0-jam-phd",
    )
    test_session.add(task)
    await test_session.flush()

    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/cockpit-test.webm",
        transcript="He go to college every day by bus, but yesterday he walk.",
        word_count=12,
        status="analyzed",
        review_status="unreviewed",
        is_verified=False,
        stt_version="mock-stt-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-syntax-v1",
    )
    test_session.add(assessment)
    await test_session.flush()

    # 4. Error Annotations (2 AI candidates)
    ann_sva = ErrorAnnotation(
        annotation_id=uuid.uuid4(),
        assessment_id=assessment.assessment_id,
        start_char=3,
        end_char=5,
        candidate_error="go",
        suggested_correction="goes",
        category_code="SVA",
        explanation="Subject 'He' requires third person singular.",
        confidence=0.96,
        ai_status="suggested",
        flag="none",
        rubric_version="v1.0-jam-phd",
        prompt_version="v1.0-assessor",
        model_version="mock-syntax-v1",
        origin="ai",
    )
    ann_tns = ErrorAnnotation(
        annotation_id=uuid.uuid4(),
        assessment_id=assessment.assessment_id,
        start_char=51,
        end_char=55,
        candidate_error="walk",
        suggested_correction="walked",
        category_code="TNS",
        explanation="Past tense marker 'yesterday' requires simple past.",
        confidence=0.94,
        ai_status="suggested",
        flag="none",
        rubric_version="v1.0-jam-phd",
        prompt_version="v1.0-assessor",
        model_version="mock-syntax-v1",
        origin="ai",
    )
    test_session.add_all([ann_sva, ann_tns])
    await test_session.flush()

    return {
        "researcher": researcher,
        "reviewer_1": reviewer_1,
        "reviewer_2": reviewer_2,
        "assessment": assessment,
        "ann_sva": ann_sva,
        "ann_tns": ann_tns,
    }


@pytest.mark.asyncio
async def test_ai_annotation_unchanged_after_review(test_session: AsyncSession, setup_review_fixtures):
    """Data Rule: AI candidate rows are NEVER mutated by any reviewer action."""
    fx = setup_review_fixtures
    ann_sva = fx["ann_sva"]
    rev1 = fx["reviewer_1"]

    orig_span = ann_sva.candidate_error
    orig_corr = ann_sva.suggested_correction
    orig_cat = ann_sva.category_code
    orig_conf = ann_sva.confidence

    # Reviewer accepts SVA
    dec = await review_service.record_decision(
        db=test_session,
        assessment_id=fx["assessment"].assessment_id,
        annotation_id=ann_sva.annotation_id,
        reviewer=rev1,
        decision=ReviewDecisionType.ACCEPTED,
        reason="Verified against rubric.",
    )
    assert dec.decision == ReviewDecisionType.ACCEPTED

    # Re-fetch annotation from DB
    stmt = select(ErrorAnnotation).where(ErrorAnnotation.annotation_id == ann_sva.annotation_id)
    refreshed = (await test_session.execute(stmt)).scalar_one()

    # Assert 100% byte-for-byte fidelity of original AI row
    assert refreshed.candidate_error == orig_span
    assert refreshed.suggested_correction == orig_corr
    assert refreshed.category_code == orig_cat
    assert refreshed.confidence == orig_conf
    assert refreshed.origin == "ai"

    # Verify event listener prevents direct mutation
    refreshed.candidate_error = "tampered"
    with pytest.raises(ValueError, match="ErrorAnnotation records are append-only"):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_reviewer_decision_immutability(test_session: AsyncSession, setup_review_fixtures):
    """Data Rule: Every reviewer decision is an append-only NEW row."""
    fx = setup_review_fixtures
    rev1 = fx["reviewer_1"]
    ann_sva = fx["ann_sva"]

    # Record first decision
    d1 = await review_service.record_decision(
        db=test_session,
        assessment_id=fx["assessment"].assessment_id,
        annotation_id=ann_sva.annotation_id,
        reviewer=rev1,
        decision=ReviewDecisionType.ACCEPTED,
        reason="Initial accept",
    )
    d1_id = d1.decision_id

    # Reviewer later re-evaluates and edits: must append NEW row, not mutate d1
    d2 = await review_service.record_decision(
        db=test_session,
        assessment_id=fx["assessment"].assessment_id,
        annotation_id=ann_sva.annotation_id,
        reviewer=rev1,
        decision=ReviewDecisionType.EDITED,
        edited_correction="goes to",
        reason="Extended span",
    )
    assert d2.decision_id != d1_id

    # Attempting to mutate d1 directly raises ValueError
    d1.notes = "Direct mutation attempt"
    with pytest.raises(ValueError, match="ReviewerDecision records are append-only"):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_derived_view_correctness(test_session: AsyncSession, setup_review_fixtures):
    """The 'effective annotation set' correctly derives values without touching AI data."""
    fx = setup_review_fixtures
    rev1 = fx["reviewer_1"]
    ass_id = fx["assessment"].assessment_id
    ann_sva = fx["ann_sva"]
    ann_tns = fx["ann_tns"]

    # 1. State: 0 decisions -> Both annotations unreviewed
    eff = await review_service.get_effective_annotations(test_session, ass_id)
    assert len(eff) == 2
    assert all(item["review_status"] == "unreviewed" for item in eff)
    assert all(item["origin"] == "ai" for item in eff)

    # 2. Accept SVA
    await review_service.record_decision(
        db=test_session,
        assessment_id=ass_id,
        annotation_id=ann_sva.annotation_id,
        reviewer=rev1,
        decision=ReviewDecisionType.ACCEPTED,
    )

    # 3. Reject TNS
    await review_service.record_decision(
        db=test_session,
        assessment_id=ass_id,
        annotation_id=ann_tns.annotation_id,
        reviewer=rev1,
        decision=ReviewDecisionType.REJECTED,
        reason="Speaker self-corrected",
    )

    # 4. Add missed error (reviewer-originated)
    added_ann = await review_service.add_reviewer_annotation(
        db=test_session,
        assessment_id=ass_id,
        reviewer=rev1,
        span_text="by bus",
        start_char=24,
        end_char=30,
        category_code="PREP",
        suggested_correction="on the bus",
        explanation="Prepositional choice inquiry",
        reason="AI missed preposition error",
    )

    # 5. Verify effective annotation set derived view
    eff_updated = await review_service.get_effective_annotations(test_session, ass_id)
    assert len(eff_updated) == 3

    # Map by annotation_id
    sva_eff = next(e for e in eff_updated if e["annotation_id"] == str(ann_sva.annotation_id))
    tns_eff = next(e for e in eff_updated if e["annotation_id"] == str(ann_tns.annotation_id))
    added_eff = next(e for e in eff_updated if e["annotation_id"] == str(added_ann.annotation_id))

    assert sva_eff["review_status"] == "accepted"
    assert sva_eff["is_active_for_metrics"] is True
    assert sva_eff["origin"] == "ai"

    assert tns_eff["review_status"] == "rejected"
    assert tns_eff["is_active_for_metrics"] is False  # Excluded from official error counts

    assert added_eff["review_status"] == "added"
    assert added_eff["is_active_for_metrics"] is True
    assert added_eff["origin"] == "reviewer"
    assert added_eff["category_code"] == "PREP"


@pytest.mark.asyncio
async def test_assessment_verification_signoff(test_session: AsyncSession, setup_review_fixtures):
    """An assessment is 'verified' ONLY when ALL candidate errors are resolved."""
    fx = setup_review_fixtures
    rev1 = fx["reviewer_1"]
    ass = fx["assessment"]
    ann_sva = fx["ann_sva"]
    ann_tns = fx["ann_tns"]

    # Initially unreviewed
    assert ass.review_status == "unreviewed"
    assert ass.is_verified is False

    # Review first candidate (1 of 2) -> partially_reviewed
    await review_service.record_decision(
        db=test_session,
        assessment_id=ass.assessment_id,
        annotation_id=ann_sva.annotation_id,
        reviewer=rev1,
        decision=ReviewDecisionType.ACCEPTED,
    )
    stmt = select(Assessment).where(Assessment.assessment_id == ass.assessment_id)
    ass_mid = (await test_session.execute(stmt)).scalar_one()
    assert ass_mid.review_status == "partially_reviewed"
    assert ass_mid.is_verified is False

    # Review second candidate (2 of 2) -> verified
    await review_service.record_decision(
        db=test_session,
        assessment_id=ass.assessment_id,
        annotation_id=ann_tns.annotation_id,
        reviewer=rev1,
        decision=ReviewDecisionType.EDITED,
        edited_correction="walked",
        reason="Past tense confirmed",
    )
    ass_final = (await test_session.execute(stmt)).scalar_one()
    assert ass_final.review_status == "verified"
    assert ass_final.is_verified is True
    assert ass_final.verified_by == rev1.id
    assert ass_final.verified_at is not None


@pytest.mark.asyncio
async def test_reviewer_row_level_access_control(test_session: AsyncSession, setup_review_fixtures):
    """Reviewers can only access records assigned to them; Researcher Admins access all."""
    fx = setup_review_fixtures
    ass_id = fx["assessment"].assessment_id
    rev1 = fx["reviewer_1"]
    rev2 = fx["reviewer_2"]
    admin = fx["researcher"]

    # Before assignment, rev1 has NO access
    assert await review_service.check_reviewer_access(test_session, ass_id, rev1) is False

    # Assign rev1 to assessment
    await review_service.assign_reviewer(
        db=test_session,
        assessment_id=ass_id,
        reviewer_id=rev1.id,
        assigned_by=admin.id,
    )

    # Now rev1 has access; rev2 does NOT
    assert await review_service.check_reviewer_access(test_session, ass_id, rev1) is True
    assert await review_service.check_reviewer_access(test_session, ass_id, rev2) is False

    # Researcher admin always has access
    assert await review_service.check_reviewer_access(test_session, ass_id, admin) is True


def test_double_review_cohens_kappa_worked_example():
    """Double-review Cohen's Kappa calculation against a known worked example."""
    # Worked Example from Landis & Koch (1977) and standard inter-rater reliability text:
    # 20 binary decisions between 2 calibrated raters
    # Rater 1: 14 'accepted', 6 'rejected'
    # Rater 2: 13 'accepted', 7 'rejected'
    # Concordance: 12 both accepted, 5 both rejected -> 17/20 concordant (85% Po)
    rater1 = ["accepted"] * 12 + ["accepted"] * 2 + ["rejected"] * 1 + ["rejected"] * 5
    rater2 = ["accepted"] * 12 + ["rejected"] * 2 + ["accepted"] * 1 + ["rejected"] * 5

    res = calculate_cohens_kappa(rater1, rater2)

    assert res.total_items == 20
    assert res.concordant_items == 17
    assert res.percent_agreement == 85.0
    # Expected Pe: (14/20)*(13/20) + (6/20)*(7/20) = (0.7*0.65) + (0.3*0.35) = 0.455 + 0.105 = 0.56
    # Kappa: (0.85 - 0.56) / (1 - 0.56) = 0.29 / 0.44 = 0.659
    assert res.cohens_kappa == pytest.approx(0.659, abs=0.01)
    assert res.interpretation == "Substantial Agreement"
