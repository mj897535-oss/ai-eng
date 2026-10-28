"""Unit, Table-Driven, Invariant, and Integration Tests for Phase P12: Post-Test & Metrics Engine.

Tests:
1. Table-driven comparative calculations:
   - Zero pre-rate (N/A relative reduction)
   - Zero post-rate (100% relative reduction)
   - Equal rates (0.0 change)
   - Negative change (post-rate > pre-rate)
   - Tiny word counts
   - Multi-error sentences under frozen counting rules (count_all vs count_one_per_sentence)
   - Provisional vs verified status determination
   - Exclusion of rejected, uncertain, transcription_related, and acceptable_variation items
2. Property-based invariant tests:
   - Absolute reduction mathematical identity: abs_red == pre_rate - post_rate
   - Relative reduction defined if and only if pre_rate > 0
   - Zero post count strictly labelled 'not observed in this sample', NEVER 'mastered'
   - Standard caution text invariance
3. API / Dashboard zero-drift test:
   - Asserts API endpoint output equals direct pure metrics module output for identical inputs.
"""

from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_auth_headers_for
from app.main import app
from app.models.assessment import (
    Assessment,
    AssessmentTask,
    AssessmentType,
    ErrorAnnotation,
    ReviewDecisionType,
    ReviewerDecision,
)
from app.models.consent import Consent, ConsentStatus
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.research.metrics import (
    STANDARD_CAUTION_TEXT,
    apply_sentence_counting_rule,
    calculate_absolute_reduction,
    calculate_error_rate,
    calculate_relative_reduction,
    compute_comparative_report,
    filter_assessable_annotations,
)


# --- 1. Table-Driven Unit Tests ---

TABLE_DRIVEN_TEST_CASES = [
    # (name, pre_err, pre_words, post_err, post_words, expected_pre_rate, expected_post_rate, expected_abs, expected_rel, expected_rel_status)
    (
        "zero_pre_rate_undefined_baseline",
        0, 100, 2, 100,
        0.0, 2.0, -2.0, None, "undefined_zero_baseline"
    ),
    (
        "zero_post_rate_100pct_reduction",
        5, 100, 0, 100,
        5.0, 0.0, 5.0, 100.0, "defined"
    ),
    (
        "equal_rates_zero_change",
        4, 100, 4, 100,
        4.0, 4.0, 0.0, 0.0, "defined"
    ),
    (
        "negative_change_regression",
        3, 100, 6, 100,
        3.0, 6.0, -3.0, -100.0, "defined"
    ),
    (
        "tiny_word_counts",
        1, 5, 0, 4,
        20.0, 0.0, 20.0, 100.0, "defined"
    ),
    (
        "standard_phd_sample",
        8, 120, 3, 120,
        6.67, 2.5, 4.17, 62.52, "defined"
    ),
]


@pytest.mark.parametrize(
    "name,pre_err,pre_words,post_err,post_words,exp_pre_rate,exp_post_rate,exp_abs,exp_rel,exp_rel_status",
    TABLE_DRIVEN_TEST_CASES,
)
def test_table_driven_comparative_calculations(
    name: str,
    pre_err: int,
    pre_words: int,
    post_err: int,
    post_words: int,
    exp_pre_rate: float,
    exp_post_rate: float,
    exp_abs: float,
    exp_rel: float | None,
    exp_rel_status: str,
):
    """Verify table-driven reductions against exact mathematical formulas."""
    pre_rate = calculate_error_rate(pre_err, pre_words)
    post_rate = calculate_error_rate(post_err, post_words)
    assert pre_rate == exp_pre_rate
    assert post_rate == exp_post_rate

    abs_red = calculate_absolute_reduction(pre_rate, post_rate)
    assert abs_red == exp_abs

    rel_red, rel_status = calculate_relative_reduction(pre_rate, post_rate)
    assert rel_status == exp_rel_status
    assert rel_red == exp_rel


def test_multi_error_sentence_counting_rules():
    """Verify frozen rubric counting rules for multiple errors in a single sentence."""
    transcript = "He go to college and he walk every day. She studies at home."
    # Sentence 1: "He go to college and he walk every day." has 2 errors at chars 3 and 24
    # Sentence 2: "She studies at home." has 0 errors
    annotations = [
        {"start_char": 3, "category_code": "SVA", "candidate_error": "go"},
        {"start_char": 24, "category_code": "SVA", "candidate_error": "walk"},
    ]

    # Rule A: count_all (default) -> both errors count
    all_counted = apply_sentence_counting_rule(annotations, transcript, counting_rule="count_all")
    assert len(all_counted) == 2

    # Rule B: count_one_per_sentence -> only first error in sentence 1 counts
    one_counted = apply_sentence_counting_rule(annotations, transcript, counting_rule="count_one_per_sentence")
    assert len(one_counted) == 1
    assert one_counted[0]["candidate_error"] == "go"


def test_effective_annotation_exclusion_filters():
    """Verify that uncertain, transcription-related, and acceptable-variation items are strictly excluded."""
    annotations = [
        {"annotation_id": "1", "category_code": "SVA", "review_status": "accepted", "flag": "candidate_error", "is_active_for_metrics": True},
        {"annotation_id": "2", "category_code": "TNS", "review_status": "rejected", "flag": "candidate_error", "is_active_for_metrics": False},
        {"annotation_id": "3", "category_code": "PREP", "review_status": "uncertain", "flag": "uncertain", "is_active_for_metrics": True},
        {"annotation_id": "4", "category_code": "ART", "review_status": "transcription_related", "flag": "transcription_related", "is_active_for_metrics": True},
        {"annotation_id": "5", "category_code": "WO", "review_status": "acceptable_variation", "flag": "acceptable_variation", "is_active_for_metrics": True},
        {"annotation_id": "6", "category_code": "AUX", "review_status": "unreviewed", "flag": "candidate_error", "is_active_for_metrics": True},
    ]

    assessable, excluded_count = filter_assessable_annotations(annotations)

    # Out of 6 annotations, only 1 (accepted) and 6 (unreviewed valid candidate) are assessable
    assert len(assessable) == 2
    assert excluded_count == 4
    categories = {a["category_code"] for a in assessable}
    assert categories == {"SVA", "AUX"}


def test_zero_post_count_labelled_not_observed_never_mastered():
    """Research Rule: Zero count at post-test is labelled 'not observed in this sample', NEVER 'mastered'."""
    pre_ann = [
        {"category_code": "SVA", "candidate_error": "go", "is_active_for_metrics": True, "review_status": "accepted"},
        {"category_code": "TNS", "candidate_error": "saw", "is_active_for_metrics": True, "review_status": "accepted"},
    ]
    post_ann = []  # 0 errors at post-test

    report = compute_comparative_report(
        pre_annotations=pre_ann,
        pre_word_count=50,
        post_annotations=post_ann,
        post_word_count=50,
        rubric_version="v1.0-jam-phd",
        is_pre_verified=True,
        is_post_verified=True,
    )

    sva = report["category_comparisons"]["SVA"]
    assert sva["post_count"] == 0
    assert sva["post_status_label"] == "not observed in this sample"
    assert "mastered" not in str(report).lower()


def test_provisional_vs_verified_status():
    """Assessments with pending human review must be marked provisional in every output."""
    # 1. Unverified baseline -> provisional
    rep1 = compute_comparative_report(
        pre_annotations=[], pre_word_count=50,
        post_annotations=[], post_word_count=50,
        rubric_version="v1.0",
        is_pre_verified=False, is_post_verified=True,
    )
    assert rep1["is_provisional"] is True
    assert rep1["status_label"] == "provisional"
    assert "Provisional analysis" in rep1["provisional_warning"]

    # 2. Both verified -> verified
    rep2 = compute_comparative_report(
        pre_annotations=[], pre_word_count=50,
        post_annotations=[], post_word_count=50,
        rubric_version="v1.0",
        is_pre_verified=True, is_post_verified=True,
    )
    assert rep2["is_provisional"] is False
    assert rep2["status_label"] == "verified"
    assert rep2["provisional_warning"] is None


def test_reproducibility_panel_and_caution_metadata():
    """Signature Feature E: Reproducibility Panel must include formulas, denominators, and caution text."""
    report = compute_comparative_report(
        pre_annotations=[{"category_code": "SVA", "is_active_for_metrics": True}],
        pre_word_count=100,
        post_annotations=[],
        post_word_count=100,
        rubric_version="v1.0-jam-phd",
        pre_prompt_version="v1.0-assessor",
        post_prompt_version="v1.0-assessor",
        model_version="mock-syntax-v1",
        stt_version="mock-stt-v1",
        is_pre_verified=True,
        is_post_verified=True,
    )

    # Standard Caution exact match
    assert report["standard_caution"] == STANDARD_CAUTION_TEXT
    assert report["standard_caution"] == "This is a descriptive comparison and does not by itself show that AI caused the change."

    # Reproducibility Panel formulas and inputs
    rp = report["reproducibility_panel"]
    assert "error_rate_per_100_words" in rp["formulas"]
    assert "absolute_reduction" in rp["formulas"]
    assert "relative_reduction_pct" in rp["formulas"]
    assert rp["pre_inputs"]["total_words"] == 100
    assert rp["pre_inputs"]["rubric_version"] == "v1.0-jam-phd"
    assert rp["pre_inputs"]["annotation_set_used"] == "effective"


# --- 2. Property-Based Invariant Tests ---

def test_property_invariants_across_ranges():
    """Property test validating mathematical invariants across 1,000 synthetic rate combinations."""
    for pre_c in range(0, 15):
        for post_c in range(0, 15):
            for words in (20, 50, 100, 200):
                pre_rate = calculate_error_rate(pre_c, words)
                post_rate = calculate_error_rate(post_c, words)

                # Invariant 1: rates must be non-negative
                assert pre_rate >= 0.0
                assert post_rate >= 0.0

                # Invariant 2: absolute reduction identity
                abs_red = calculate_absolute_reduction(pre_rate, post_rate)
                expected_abs = round(pre_rate - post_rate, 2)
                assert abs_red == expected_abs

                # Invariant 3: relative reduction status
                rel_red, rel_status = calculate_relative_reduction(pre_rate, post_rate)
                if pre_rate == 0.0:
                    assert rel_red is None
                    assert rel_status == "undefined_zero_baseline"
                else:
                    assert rel_status == "defined"
                    assert rel_red is not None
                    if post_rate == 0.0:
                        assert rel_red == 100.0


# --- 3. API / Dashboard Zero-Drift Test ---

@pytest_asyncio.fixture
async def setup_p12_paired_assessments(test_session: AsyncSession):
    """Seed user, participant, and paired pre/post assessments sharing an equivalence group."""
    user = User(
        id=uuid.uuid4(),
        email="learner.p12@syntaxlens.edu",
        hashed_password="argon2id$mockhash",
        full_name="P12 Paired Learner",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    test_session.add(user)
    await test_session.flush()

    participant = Participant(
        participant_id=uuid.uuid4(),
        user_id=user.id,
        research_code="SL-2026-9501",
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

    # Pre-task and Post-task from same equivalence group
    task_pre = AssessmentTask(
        task_id=uuid.uuid4(),
        title="Pre Task - Daily Routine",
        prompt_text="Talk about your morning commute.",
        equivalence_group="pair_commute_work",
        rubric_version="v1.0-jam-phd",
    )
    task_post = AssessmentTask(
        task_id=uuid.uuid4(),
        title="Post Task - Workplace",
        prompt_text="Talk about your workspace.",
        equivalence_group="pair_commute_work",
        rubric_version="v1.0-jam-phd",
    )
    test_session.add_all([task_pre, task_post])
    await test_session.flush()

    # Pre-test assessment
    pre_ass = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task_pre.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/p12-pre.webm",
        transcript="He go to college every day and he walk.",
        word_count=9,
        status="completed",
        is_official=True,
        is_verified=True,
        is_visible_to_participant=True,
        stt_version="mock-stt-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-syntax-v1",
        prompt_version="v1.0-assessor",
    )
    post_ass = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task_post.task_id,
        assessment_type=AssessmentType.POST,
        audio_key="audio/p12-post.webm",
        transcript="He goes to college every day by train.",
        word_count=8,
        status="completed",
        is_official=True,
        is_verified=True,
        is_visible_to_participant=True,
        stt_version="mock-stt-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-syntax-v1",
        prompt_version="v1.0-assessor",
    )
    test_session.add_all([pre_ass, post_ass])
    await test_session.flush()

    # Annotations on pre-test: 2 SVA errors
    ann1 = ErrorAnnotation(
        annotation_id=uuid.uuid4(),
        assessment_id=pre_ass.assessment_id,
        start_char=3, end_char=5,
        candidate_error="go", suggested_correction="goes",
        category_code="SVA", explanation="SVA deviation",
        confidence=0.98, ai_status="suggested", flag="candidate_error",
        model_version="mock-syntax-v1", origin="ai",
    )
    ann2 = ErrorAnnotation(
        annotation_id=uuid.uuid4(),
        assessment_id=pre_ass.assessment_id,
        start_char=29, end_char=33,
        candidate_error="walk", suggested_correction="walks",
        category_code="SVA", explanation="SVA deviation",
        confidence=0.95, ai_status="suggested", flag="candidate_error",
        model_version="mock-syntax-v1", origin="ai",
    )
    test_session.add_all([ann1, ann2])
    await test_session.flush()

    # Reviewer accepts ann1, marks ann2 as accepted
    dec1 = ReviewerDecision(
        decision_id=uuid.uuid4(),
        annotation_id=ann1.annotation_id,
        assessment_id=pre_ass.assessment_id,
        reviewer_id=user.id,
        decision=ReviewDecisionType.ACCEPTED,
    )
    test_session.add(dec1)
    await test_session.flush()

    return {
        "user": user,
        "participant": participant,
        "pre_ass": pre_ass,
        "post_ass": post_ass,
    }


@pytest.mark.asyncio
async def test_api_number_equals_metrics_module_output(client: AsyncClient, setup_p12_paired_assessments):
    """Zero-Drift Guarantee: Assert API comparative endpoint matches pure metrics module output exactly."""
    fx = setup_p12_paired_assessments
    user = fx["user"]
    participant = fx["participant"]
    post_id = fx["post_ass"].assessment_id

    headers = await create_auth_headers_for(user, participant)

    # Call API endpoint
    response = await client.get(f"/api/v1/assessments/{post_id}/comparative-report", headers=headers)
    assert response.status_code == 200, response.text
    api_data = response.json()

    # Call pure module directly with same inputs
    pre_eff = [
        {"start_char": 3, "category_code": "SVA", "candidate_error": "go", "review_status": "accepted", "flag": "candidate_error", "is_active_for_metrics": True},
        {"start_char": 29, "category_code": "SVA", "candidate_error": "walk", "review_status": "unreviewed", "flag": "candidate_error", "is_active_for_metrics": True},
    ]
    post_eff = []

    direct_report = compute_comparative_report(
        pre_annotations=pre_eff,
        pre_word_count=9,
        post_annotations=post_eff,
        post_word_count=8,
        rubric_version="v1.0-jam-phd",
        is_pre_verified=True,
        is_post_verified=True,
    )

    # Assert exact equality between API endpoint numbers and direct metrics module
    assert api_data["overall_comparison"]["pre_rate_per_100"] == direct_report["overall_comparison"]["pre_rate_per_100"]
    assert api_data["overall_comparison"]["post_rate_per_100"] == direct_report["overall_comparison"]["post_rate_per_100"]
    assert api_data["overall_comparison"]["absolute_reduction"] == direct_report["overall_comparison"]["absolute_reduction"]
    assert api_data["overall_comparison"]["relative_reduction_pct"] == direct_report["overall_comparison"]["relative_reduction_pct"]
    assert api_data["standard_caution"] == direct_report["standard_caution"]
    assert api_data["category_comparisons"]["SVA"]["post_status_label"] == "not observed in this sample"
