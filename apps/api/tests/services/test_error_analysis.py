"""Tests for Error Analysis Engine, Post-Validation, Immutability, and Golden Sets (Phase P8).

Tests:
1. Golden-file tests for each of the 8 categories (TNS, SVA, WO, AUX, ART, PREP, PRO, OTH)
   including the SRS Appendix A example ('He go to college every day.' -> SVA, 'goes').
2. Scientific edge cases: Indian English acceptable variation ('I am knowing').
3. Non-LLM Post-Validation: hallucinated span rejection and deduplication.
4. Retry state machine on invalid JSON / parse failure up to max retries -> needs_attention.
5. Immutability: ErrorAnnotation rows cannot be updated or deleted after persistence.
6. Auto-routing: low confidence, non-candidate flag, or OTH routed to needs_human_review.
7. Participant visibility gating and researcher release workflow.
"""

import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assessment import (
    Assessment,
    AssessmentTask,
    AssessmentType,
    ErrorAnnotation,
)
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.services.analysis import error_analysis_service
from app.services.llm.base import AnnotationItem, AssessorOutput, LLMProvider
from app.services.llm.mock import GOLDEN_FIXTURES, MockLLMProvider
from app.services.validator import post_validator
from tests.conftest import create_auth_headers_for


@pytest.fixture
async def analysis_seeded_data(test_session: AsyncSession) -> dict:
    """Fixture providing participant, task, researcher, and participant users."""
    researcher = User(
        email=f"res_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Principal Investigator",
        hashed_password="pw",
        role=UserRole.RESEARCHER_ADMIN,
        is_active=True,
    )
    p_user = User(
        email=f"p_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Study Participant",
        hashed_password="pw",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    p_user_b = User(
        email=f"pb_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Other Participant",
        hashed_password="pw",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    test_session.add_all([researcher, p_user, p_user_b])
    await test_session.flush()

    participant = Participant(
        user_id=p_user.id,
        research_code=f"SL-2026-P8-{uuid.uuid4().hex[:4]}",
        study_group=StudyGroup.INTERVENTION,
        is_active=True,
    )
    participant_b = Participant(
        user_id=p_user_b.id,
        research_code=f"SL-2026-P8B-{uuid.uuid4().hex[:4]}",
        study_group=StudyGroup.CONTROL,
        is_active=True,
    )
    task = AssessmentTask(
        title="Spoken Baseline Task",
        prompt_text="Describe your college routine.",
        duration_seconds=60,
        prep_time_seconds=30,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        is_active=True,
    )
    test_session.add_all([participant, participant_b, task])
    await test_session.commit()

    return {
        "researcher": researcher,
        "p_user": p_user,
        "p_user_b": p_user_b,
        "participant": participant,
        "participant_b": participant_b,
        "task": task,
    }


# ============================================================================
# 1. GOLDEN-FILE TESTS FOR 8 CATEGORIES (INCLUDING APPENDIX A SVA EXAMPLE)
# ============================================================================

@pytest.mark.asyncio
async def test_golden_sva_appendix_a_example() -> None:
    """Verifies Appendix A: 'He go to college every day.' -> SVA, correction 'goes'."""
    provider = MockLLMProvider()
    transcript = "He go to college every day."
    output = await provider.analyze_syntax(
        transcript=transcript,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        prompt_version=settings.DEFAULT_ASSESSOR_PROMPT_VERSION,
    )

    assert len(output.annotations) == 1
    ann = output.annotations[0]
    assert ann.category_code == "SVA"
    assert ann.span_text == "go"
    assert ann.proposed_correction == "goes"
    assert ann.char_start == 3
    assert ann.char_end == 5
    assert transcript[ann.char_start:ann.char_end] == ann.span_text
    assert ann.flag == "candidate_error"
    assert ann.confidence >= 0.95


@pytest.mark.parametrize(
    "transcript,expected_category,expected_span,expected_correction",
    [
        ("Yesterday I have seen him at the station.", "TNS", "have seen", "saw"),
        ("Always he is coming late to class.", "WO", "Always he is coming", "He is always coming"),
        ("She can to solve this problem.", "AUX", "can to solve", "can solve"),
        ("He is studying in the engineering college.", "ART", "the engineering college", "an engineering college"),
        ("We will discuss about this topic.", "PREP", "discuss about", "discuss"),
        ("My friend he told me about the exam.", "PRO", "he", ""),
        ("This machine is more better than old one.", "OTH", "more better", "better"),
    ],
)
@pytest.mark.asyncio
async def test_golden_categories_coverage(
    transcript: str,
    expected_category: str,
    expected_span: str,
    expected_correction: str,
) -> None:
    """Verifies golden detection for TNS, WO, AUX, ART, PREP, PRO, and OTH."""
    provider = MockLLMProvider()
    output = await provider.analyze_syntax(
        transcript=transcript,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        prompt_version=settings.DEFAULT_ASSESSOR_PROMPT_VERSION,
    )

    assert len(output.annotations) >= 1
    matching = [a for a in output.annotations if a.category_code == expected_category]
    assert len(matching) == 1
    ann = matching[0]
    assert ann.span_text == expected_span
    assert ann.proposed_correction == expected_correction
    assert transcript[ann.char_start:ann.char_end] == ann.span_text


@pytest.mark.asyncio
async def test_acceptable_indian_english_variation_flagging() -> None:
    """Acceptable regional syntax ('I am knowing') is flagged as acceptable_variation."""
    provider = MockLLMProvider()
    transcript = "I am knowing this subject very well."
    output = await provider.analyze_syntax(
        transcript=transcript,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        prompt_version=settings.DEFAULT_ASSESSOR_PROMPT_VERSION,
    )

    assert len(output.annotations) == 1
    ann = output.annotations[0]
    assert ann.flag == "acceptable_variation"
    assert ann.span_text == "am knowing"
    assert ann.category_code == "TNS"


# ============================================================================
# 2. NON-LLM POST-VALIDATION LAYER TESTS
# ============================================================================

def test_hallucinated_span_rejection() -> None:
    """Non-LLM layer must reject spans that do not exist in transcript text."""
    transcript = "He goes to college every day."
    # Annotation where span_text is hallucinated / nonexistent
    hallucinated_ann = AnnotationItem(
        span_text="went to",
        char_start=3,
        char_end=10,
        category_code="TNS",
        proposed_correction="goes to",
        explanation="Tense consistency.",
        confidence=0.90,
        flag="candidate_error",
    )

    validated = post_validator.validate_and_align_annotations(transcript, [hallucinated_ann])
    assert len(validated) == 0, "Hallucinated span must be rejected by post-validation."


def test_post_validation_correction_identical_to_span_rejected() -> None:
    """If proposed correction is identical to span text, reject as invalid error."""
    transcript = "We attended the meeting."
    identical_ann = AnnotationItem(
        span_text="attended",
        char_start=3,
        char_end=11,
        category_code="TNS",
        proposed_correction="attended",
        explanation="No change.",
        confidence=0.90,
        flag="candidate_error",
    )
    validated = post_validator.validate_and_align_annotations(transcript, [identical_ann])
    assert len(validated) == 0


def test_post_validation_deduplicates_overlapping_spans() -> None:
    """Deduplicates overlapping annotations in the same category, keeping higher confidence."""
    transcript = "He go to college every day."
    ann1 = AnnotationItem(
        span_text="go",
        char_start=3,
        char_end=5,
        category_code="SVA",
        proposed_correction="goes",
        explanation="SVA rule 1.",
        confidence=0.85,
        flag="candidate_error",
    )
    ann2 = AnnotationItem(
        span_text="go",
        char_start=3,
        char_end=5,
        category_code="SVA",
        proposed_correction="goes",
        explanation="SVA rule 2.",
        confidence=0.98,  # Higher confidence
        flag="candidate_error",
    )
    validated = post_validator.validate_and_align_annotations(transcript, [ann1, ann2])
    assert len(validated) == 1
    assert validated[0].confidence == 0.98


# ============================================================================
# 3. RETRY STATE MACHINE & INVALID JSON HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_json_retries_and_dead_letters(
    test_session: AsyncSession,
    analysis_seeded_data: dict,
) -> None:
    """Service retries on invalid output up to max retries, then marks needs_attention."""
    participant = analysis_seeded_data["participant"]
    task = analysis_seeded_data["task"]

    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/invalid_json_test.webm",
        transcript="He go to college every day.",
        word_count=6,
        status="transcribed",
        stt_version=settings.DEFAULT_STT_VERSION,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
    )
    test_session.add(assessment)
    await test_session.commit()

    # Provider that consistently fails with malformed JSON
    class MalformedJSONProvider(MockLLMProvider):
        async def analyze_syntax(self, *args, **kwargs):
            raise ValueError("Malformed JSON string from upstream LLM.")

    broken_service = error_analysis_service.__class__(provider=MalformedJSONProvider())

    with pytest.raises(ValueError, match="needs_attention|failed after"):
        await broken_service.analyze_assessment(
            db=test_session,
            assessment_id=assessment.assessment_id,
        )

    stmt = select(Assessment).where(Assessment.assessment_id == assessment.assessment_id)
    failed_assessment = (await test_session.execute(stmt)).scalar_one()
    assert failed_assessment.status == "needs_attention"
    assert "Malformed JSON" in failed_assessment.last_error


# ============================================================================
# 4. IMMUTABILITY OF ERROR ANNOTATIONS
# ============================================================================

@pytest.mark.asyncio
async def test_error_annotation_immutability(
    test_session: AsyncSession,
    analysis_seeded_data: dict,
) -> None:
    """ErrorAnnotation records are append-only research artefacts and cannot be updated or deleted."""
    participant = analysis_seeded_data["participant"]
    task = analysis_seeded_data["task"]

    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/immutability_test.webm",
        transcript="He go to college every day.",
        word_count=6,
        status="transcribed",
        stt_version=settings.DEFAULT_STT_VERSION,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
    )
    test_session.add(assessment)
    await test_session.commit()

    annotation = ErrorAnnotation(
        annotation_id=uuid.uuid4(),
        assessment_id=assessment.assessment_id,
        start_char=3,
        end_char=5,
        candidate_error="go",
        suggested_correction="goes",
        category_code="SVA",
        explanation="SVA rule.",
        confidence=0.98,
        ai_status="candidate",
        flag="candidate_error",
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        prompt_version=settings.DEFAULT_ASSESSOR_PROMPT_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
    )
    test_session.add(annotation)
    await test_session.commit()

    ann_id = annotation.annotation_id

    # 1. Attempt UPDATE -> must raise ValueError
    annotation.suggested_correction = "went"
    with pytest.raises(ValueError, match="cannot be updated"):
        await test_session.flush()

    await test_session.rollback()

    # 2. Attempt DELETE -> must raise ValueError
    stmt = select(ErrorAnnotation).where(ErrorAnnotation.annotation_id == ann_id)
    fresh_ann = (await test_session.execute(stmt)).scalar_one_or_none()
    assert fresh_ann is not None
    await test_session.delete(fresh_ann)
    with pytest.raises(ValueError, match="cannot be deleted"):
        await test_session.flush()

    await test_session.rollback()


# ============================================================================
# 5. AUTO-ROUTING & VERSION STAMPING
# ============================================================================

@pytest.mark.asyncio
async def test_auto_routing_and_version_stamping(
    test_session: AsyncSession,
    analysis_seeded_data: dict,
) -> None:
    """Annotations are version-stamped, and non-candidate flags are routed to needs_human_review."""
    participant = analysis_seeded_data["participant"]
    task = analysis_seeded_data["task"]

    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/autoroute_test.webm",
        transcript="I am knowing this subject very well.",
        word_count=7,
        status="transcribed",
        stt_version=settings.DEFAULT_STT_VERSION,
        rubric_version="v1.0-jam-phd",
        model_version="mock-syntax-v1",
    )
    test_session.add(assessment)
    await test_session.commit()

    annotations = await error_analysis_service.analyze_assessment(
        db=test_session,
        assessment_id=assessment.assessment_id,
    )

    assert len(annotations) == 1
    ann = annotations[0]

    # Version stamping verification
    assert ann.rubric_version == "v1.0-jam-phd"
    assert ann.prompt_version == settings.DEFAULT_ASSESSOR_PROMPT_VERSION
    assert ann.model_version is not None
    assert ann.raw_model_output_ref is not None

    # Auto-routing: because flag is 'acceptable_variation', ai_status is routed to 'needs_human_review'
    assert ann.flag == "acceptable_variation"
    assert ann.ai_status == "needs_human_review"


# ============================================================================
# 6. PARTICIPANT VISIBILITY GATING & RESEARCHER RELEASE
# ============================================================================

@pytest.mark.asyncio
async def test_participant_visibility_gating_and_release(
    client: AsyncClient,
    test_session: AsyncSession,
    analysis_seeded_data: dict,
) -> None:
    """Participant cannot view annotations until released by researcher."""
    researcher = analysis_seeded_data["researcher"]
    p_user = analysis_seeded_data["p_user"]
    participant = analysis_seeded_data["participant"]
    task = analysis_seeded_data["task"]

    headers_part = await create_auth_headers_for(p_user, participant)
    headers_res = await create_auth_headers_for(researcher)

    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/vis_test.webm",
        transcript="He go to college every day.",
        word_count=6,
        status="transcribed",
        is_visible_to_participant=False,  # Hidden by default
        stt_version=settings.DEFAULT_STT_VERSION,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
    )
    test_session.add(assessment)
    await test_session.commit()

    # 1. Researcher triggers analysis
    analyze_resp = await client.post(
        f"/api/v1/assessments/{assessment.assessment_id}/analyze",
        headers=headers_res,
    )
    assert analyze_resp.status_code == 200

    # 2. Participant views report before release -> annotations REDACTED (empty)
    part_resp = await client.get(
        f"/api/v1/assessments/{assessment.assessment_id}/report",
        headers=headers_part,
    )
    assert part_resp.status_code == 200
    part_data = part_resp.json()
    assert part_data["is_visible_to_participant"] is False
    assert len(part_data["annotations"]) == 0
    assert "being evaluated" in part_data["banner_notice"].lower()

    # 3. Researcher views report -> sees all annotations
    res_resp = await client.get(
        f"/api/v1/assessments/{assessment.assessment_id}/report",
        headers=headers_res,
    )
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert len(res_data["annotations"]) == 1
    assert res_data["annotations"][0]["category_code"] == "SVA"

    # 4. Researcher releases results
    rel_resp = await client.post(
        f"/api/v1/assessments/{assessment.assessment_id}/release",
        headers=headers_res,
    )
    assert rel_resp.status_code == 200
    assert rel_resp.json()["is_visible_to_participant"] is True

    # 5. Participant views report after release -> annotations now VISIBLE
    part_after = await client.get(
        f"/api/v1/assessments/{assessment.assessment_id}/report",
        headers=headers_part,
    )
    assert part_after.status_code == 200
    after_data = part_after.json()
    assert after_data["is_visible_to_participant"] is True
    assert len(after_data["annotations"]) == 1
    assert after_data["annotations"][0]["candidate_error"] == "go"
    assert after_data["annotations"][0]["suggested_correction"] == "goes"
