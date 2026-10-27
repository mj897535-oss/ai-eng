"""Tests for Speech-to-Text Pipeline, Word Counting, Immutability, and Telemetry (Phase P7).

Tests enforce:
1. Determinism: Same audio hash always yields identical mock transcript.
2. Faithful Transcription: Disfluencies and ungrammatical utterances are NOT normalised or corrected.
3. Word-Counting Rules: Contractions, hyphenated compounds, and fillers counted per rubric spec.
4. Database Immutability: Assessments transcript cannot be updated once written.
5. Human Revisions: Revisions stored in separate table without mutating candidate transcript.
6. State Machine & Dead-Letter: queued -> transcribing -> transcribed | failed -> retrying -> needs_attention.
7. Pilot Kit Telemetry: Cost, latency, confidence, and duration accurately tracked.
"""

import hashlib
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
    STTJobMetric,
    TranscriptRevision,
)
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.services.stt import (
    MockSTTProvider,
    count_words,
    get_stt_provider,
    tokenize_words,
)
from app.services.stt.mock import (
    FIXTURE_COMPOUND_CONTRACTIONS,
    FIXTURE_DISFLUENCY,
    FIXTURE_UNGRAMMATICAL,
)
from app.services.stt_pipeline import MAX_STT_RETRIES, stt_pipeline_service


@pytest.fixture
async def stt_seeded_data(test_session: AsyncSession) -> dict:
    """Fixture providing participant, task, and users for STT tests."""
    # Create reviewer and researcher
    reviewer = User(
        email=f"reviewer_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Reviewer User",
        hashed_password="hashed_pw",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    researcher = User(
        email=f"researcher_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Researcher Admin",
        hashed_password="hashed_pw",
        role=UserRole.RESEARCHER_ADMIN,
        is_active=True,
    )
    p_user = User(
        email=f"part_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Participant User",
        hashed_password="hashed_pw",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    test_session.add_all([reviewer, researcher, p_user])
    await test_session.flush()

    participant = Participant(
        user_id=p_user.id,
        research_code=f"SL-2026-{uuid.uuid4().hex[:4]}",
        study_group=StudyGroup.INTERVENTION,
        is_active=True,
    )
    task = AssessmentTask(
        title="College Routine Spoken Task",
        prompt_text="Describe your typical schedule at college.",
        duration_seconds=60,
        prep_time_seconds=30,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        is_active=True,
    )
    test_session.add_all([participant, task])
    await test_session.commit()

    return {
        "reviewer": reviewer,
        "researcher": researcher,
        "p_user": p_user,
        "participant": participant,
        "task": task,
    }


# ============================================================================
# 1. FAITHFUL TRANSCRIPTION & MOCK DETERMINISM TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_mock_stt_same_audio_same_transcript() -> None:
    """Verifies same audio reference/hash ALWAYS returns the identical transcript."""
    provider = MockSTTProvider()
    audio_ref_1 = "audio/SL-2026-0001/pre_sample_test.webm"
    checksum_1 = hashlib.sha256(b"sample_audio_123").hexdigest()

    res_1 = await provider.transcribe(audio_ref_1, options={"checksum": checksum_1})
    res_2 = await provider.transcribe(audio_ref_1, options={"checksum": checksum_1})

    assert res_1.text == res_2.text
    assert len(res_1.words) == len(res_2.words)
    assert res_1.overall_confidence == res_2.overall_confidence
    assert res_1.model_version == res_2.model_version


@pytest.mark.asyncio
async def test_disfluency_fixture_never_normalised() -> None:
    """Disfluency fixture ('um... I think that, that he go') is NOT normalised or corrected."""
    provider = MockSTTProvider()
    res = await provider.transcribe("audio/test.webm", options={"fixture": "disfluency"})

    # Verbatim checks:
    # 1. Preserves filler / hesitation
    assert "um" in res.text.lower()
    # 2. Preserves stutter / repetition
    assert "that, that" in res.text
    # 3. Preserves ungrammatical third-person singular "he go" (NEVER corrected to "he goes")
    assert "he go" in res.text
    assert "he goes" not in res.text
    assert res.text == FIXTURE_DISFLUENCY


@pytest.mark.asyncio
async def test_ungrammatical_fixture_preserved_verbatim() -> None:
    """Verifies 'He go to college every day.' is preserved verbatim without SVA correction."""
    provider = MockSTTProvider()
    res = await provider.transcribe("audio/test.webm", options={"fixture": "ungrammatical"})
    assert res.text == FIXTURE_UNGRAMMATICAL
    assert "He goes" not in res.text


# ============================================================================
# 2. FROZEN WORD-COUNTING RULES
# ============================================================================

def test_word_counting_rules_hyphenation_and_contractions() -> None:
    """Word-counting rule must handle hyphenation, contractions, and fillers per rubric spec."""
    # 1. Contraction is 1 word
    assert count_words("don't") == 1
    assert count_words("it's") == 1
    assert count_words("they'll") == 1

    # 2. Hyphenated compound is 1 word
    assert count_words("state-of-the-art") == 1
    assert count_words("well-known") == 1
    assert count_words("mother-in-law") == 1

    # 3. Speech fillers are excluded from count
    assert count_words("um") == 0
    assert count_words("uh") == 0
    assert count_words("ah") == 0
    assert count_words("um uh ah") == 0

    # 4. Complex sentence with compounds, contractions, and fillers:
    # "I don't think it's a state-of-the-art laboratory, um... but we attend daily."
    # Tokens: I (1), don't (1), think (1), it's (1), a (1), state-of-the-art (1), laboratory (1),
    #         um... (0, filler), but (1), we (1), attend (1), daily (1)
    # Total = 11 words
    text = FIXTURE_COMPOUND_CONTRACTIONS
    assert count_words(text) == 11

    # 5. Tokenizer test
    tokens = tokenize_words(text)
    assert "don't" in tokens
    assert "it's" in tokens
    assert "state-of-the-art" in tokens
    assert "um" not in tokens


# ============================================================================
# 3. DATABASE IMMUTABILITY AND REVISIONS
# ============================================================================

@pytest.mark.asyncio
async def test_transcript_row_cannot_be_updated_after_write(
    test_session: AsyncSession,
    stt_seeded_data: dict,
) -> None:
    """Once written, direct UPDATE to assessments.transcript MUST fail."""
    participant = stt_seeded_data["participant"]
    task = stt_seeded_data["task"]

    # Create assessment and write transcript
    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/immutable_test.webm",
        transcript="He go to college every day.",
        word_count=6,
        status="transcribed",
        stt_version="mock-stt-v1.0",
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
    )
    test_session.add(assessment)
    await test_session.commit()

    # Attempt to directly mutate the transcript
    assessment.transcript = "He goes to college every day."  # Attempted grammar correction
    with pytest.raises(ValueError, match="immutable once written"):
        await test_session.flush()

    await test_session.rollback()


@pytest.mark.asyncio
async def test_human_transcript_revision_creates_separate_row(
    test_session: AsyncSession,
    stt_seeded_data: dict,
) -> None:
    """Reviewer correction creates a separate transcript_revisions row while preserving candidate transcript."""
    participant = stt_seeded_data["participant"]
    task = stt_seeded_data["task"]
    reviewer = stt_seeded_data["reviewer"]

    original_text = "He go to college every day."
    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/rev_test.webm",
        transcript=original_text,
        word_count=6,
        status="transcribed",
        stt_version="mock-stt-v1.0",
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
    )
    test_session.add(assessment)
    await test_session.commit()

    # Reviewer documents acoustic hearing correction
    revised_text = "He go to classes every day."
    revision = await stt_pipeline_service.create_transcript_revision(
        db=test_session,
        assessment_id=assessment.assessment_id,
        revised_transcript=revised_text,
        reason="Acoustic clarity check confirms speaker said 'classes', not 'college'.",
        reviewer=reviewer,
    )

    # 1. Revision is persisted with diff and word count
    assert revision.revised_transcript == revised_text
    assert revision.revised_word_count == 6
    assert revision.reviewer_id == reviewer.id
    assert "diff_tokens" in revision.diff_json

    # 2. Original assessment transcript is completely UNTOUCHED
    stmt = select(Assessment).where(Assessment.assessment_id == assessment.assessment_id)
    fresh_assessment = (await test_session.execute(stmt)).scalar_one()
    assert fresh_assessment.transcript == original_text


# ============================================================================
# 4. STATE MACHINE, RETRIES, AND TELEMETRY METRICS
# ============================================================================

@pytest.mark.asyncio
async def test_stt_pipeline_job_state_machine_and_metrics(
    test_session: AsyncSession,
    stt_seeded_data: dict,
) -> None:
    """Verifies queued -> transcribing -> transcribed and metrics entry."""
    participant = stt_seeded_data["participant"]
    task = stt_seeded_data["task"]

    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/job_test.webm",
        audio_checksum=hashlib.sha256(b"disfluency").hexdigest(),
        audio_duration_seconds=45.0,
        status="queued_for_transcription",
        stt_version=settings.DEFAULT_STT_VERSION,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
    )
    test_session.add(assessment)
    await test_session.commit()

    # Run STT job
    completed = await stt_pipeline_service.process_transcription_job(
        db=test_session,
        assessment_id=assessment.assessment_id,
    )

    assert completed.status == "transcribed"
    assert completed.transcript == FIXTURE_DISFLUENCY
    assert completed.words_json is not None
    assert completed.raw_stt_response_key is not None
    assert completed.stt_confidence is not None

    # Verify telemetry in stt_job_metrics
    stmt = select(STTJobMetric).where(STTJobMetric.assessment_id == assessment.assessment_id)
    metric = (await test_session.execute(stmt)).scalar_one_or_none()
    assert metric is not None
    assert metric.provider == "mock"
    assert metric.audio_duration_seconds == 45.0
    assert metric.word_count > 0
    assert metric.latency_ms >= 0


@pytest.mark.asyncio
async def test_stt_dead_letter_handling_after_max_retries(
    test_session: AsyncSession,
    stt_seeded_data: dict,
) -> None:
    """Verifies failed STT transitions to 'retrying' and dead-letters to 'needs_attention'."""
    participant = stt_seeded_data["participant"]
    task = stt_seeded_data["task"]

    assessment = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/failing_test.webm",
        status="queued_for_transcription",
        stt_version=settings.DEFAULT_STT_VERSION,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
        retry_count=MAX_STT_RETRIES - 1,  # 1 attempt left before dead-letter
    )
    test_session.add(assessment)
    await test_session.commit()

    # Create a broken provider that raises an exception
    class FailingSTTProvider(MockSTTProvider):
        async def transcribe(self, *args, **kwargs):
            raise ConnectionError("Upstream STT service timeout.")

    failing_service = stt_pipeline_service.__class__(provider=FailingSTTProvider())

    with pytest.raises(ConnectionError):
        await failing_service.process_transcription_job(
            db=test_session,
            assessment_id=assessment.assessment_id,
        )

    # Reload assessment and verify dead-letter status
    stmt = select(Assessment).where(Assessment.assessment_id == assessment.assessment_id)
    failed_assessment = (await test_session.execute(stmt)).scalar_one()
    assert failed_assessment.status == "needs_attention"
    assert failed_assessment.retry_count == MAX_STT_RETRIES
    assert "timeout" in failed_assessment.last_error.lower()
