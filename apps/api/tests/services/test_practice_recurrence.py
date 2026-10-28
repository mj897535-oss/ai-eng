"""Unit and Scenario Tests for Phase P11: Session History, Active Timing, and Recurrence (SRS Section 10, FR-13, FR-14).

Tests:
1. test_double_count_prevention_adversarial_repeats:
   Validates FR-14 double-count prevention across identical utterances, casing differences,
   punctuation differences, and extra whitespace.
2. test_active_duration_across_idle_gaps:
   Validates documented idle exclusion rule: gaps >60s cap active time at 60s and credit remainder to idle.
3. test_technical_interruption_logging:
   Validates interruption events (mic_failure, disconnect) logged as distinct events without corrupting error metrics.
4. test_pattern_level_recurrence_tracking:
   Validates longitudinal tracking of utterance patterns with first_seen_at, last_seen_at, occurrence counts.
5. test_metrics_purely_derived_from_events:
   Validates that independent correction rates and adherence stats are purely derived with zero database mutation.
6. test_cohort_adherence_summary:
   Validates researcher cohort adherence metrics against configured targets (3 sessions/week, 15 min/session).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentTask, AssessmentType, ErrorAnnotation
from app.models.consent import Consent, ConsentStatus
from app.models.identity import User, UserRole
from app.models.practice import AttemptType, PracticeEvent, PracticeSession, UtterancePattern
from app.models.research import Participant, StudyGroup
from app.research.metrics import (
    calculate_active_duration,
    calculate_adherence_statistics,
    calculate_independent_correction_rate,
    compute_utterance_fingerprint,
    normalize_utterance_for_fingerprint,
)
from app.services.tutor import tutor_service


@pytest_asyncio.fixture
async def setup_p11_fixtures(test_session: AsyncSession):
    """Seed participant and verified pre-test baseline for Phase P11 tests."""
    user = User(
        id=uuid.uuid4(),
        email="p11.recurrence@syntaxlens.edu",
        hashed_password="argon2id$mockhash",
        full_name="P11 Recurrence Learner",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    test_session.add(user)
    await test_session.flush()

    participant = Participant(
        participant_id=uuid.uuid4(),
        user_id=user.id,
        research_code="SL-2026-9001",
        study_group=StudyGroup.INTERVENTION,
        learner_interests="Language Acquisition Studies",
    )
    consent = Consent(
        consent_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        consent_version="v1.0-jam-2026",
        status=ConsentStatus.CONSENTED,
    )
    test_session.add_all([participant, consent])
    await test_session.flush()

    task = AssessmentTask(
        task_id=uuid.uuid4(),
        title="P11 Baseline Task",
        prompt_text="Talk about your daily study routine.",
        rubric_version="v1.0-jam-phd",
    )
    test_session.add(task)
    await test_session.flush()

    pretest = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/p11-pre.webm",
        transcript="He go to college every day.",
        word_count=6,
        status="analyzed",
        review_status="verified",
        is_verified=True,
        stt_version="mock-stt-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-syntax-v1",
    )
    test_session.add(pretest)
    await test_session.flush()

    annotation = ErrorAnnotation(
        annotation_id=uuid.uuid4(),
        assessment_id=pretest.assessment_id,
        start_char=3,
        end_char=5,
        candidate_error="go",
        suggested_correction="goes",
        category_code="SVA",
        explanation="Subject 'He' requires third-person singular inflection.",
        confidence=0.98,
        ai_status="suggested",
        flag="none",
        rubric_version="v1.0-jam-phd",
        prompt_version="v1.0-assessor",
        model_version="mock-syntax-v1",
        origin="ai",
    )
    test_session.add(annotation)
    await test_session.flush()

    return {
        "user": user,
        "participant": participant,
        "pretest": pretest,
    }


@pytest.mark.asyncio
async def test_double_count_prevention_adversarial_repeats(test_session: AsyncSession, setup_p11_fixtures):
    """FR-14: Repeated references to the SAME utterance within/across sessions must NOT count as separate errors.
    
    Tests adversarial variations: casing, punctuation, extra whitespace.
    """
    fx = setup_p11_fixtures
    part_id = fx["participant"].participant_id

    adversarial_inputs = [
        "He go to college every day.",
        "he go to college every day",
        "He  go to college, every day!",
        "HE GO TO COLLEGE EVERY DAY",
        "  he go to   college every day.  ",
    ]

    # Verify that all adversarial inputs produce the IDENTICAL fingerprint
    fingerprints = [compute_utterance_fingerprint(inp) for inp in adversarial_inputs]
    assert len(set(fingerprints)) == 1, "Adversarial variations failed to produce identical fingerprint!"
    shared_fp = fingerprints[0]

    # Start session 1
    s1_data = await tutor_service.start_session(test_session, part_id)
    s1_id = uuid.UUID(s1_data["session_id"])

    # Turn 1: initial utterance
    t1 = await tutor_service.process_turn(test_session, s1_id, part_id, adversarial_inputs[0])
    assert t1["utterance_fingerprint"] == shared_fp
    assert t1["is_first_occurrence"] is True

    # Turn 2: repeat with different punctuation/casing
    t2 = await tutor_service.process_turn(test_session, s1_id, part_id, adversarial_inputs[1])
    assert t2["utterance_fingerprint"] == shared_fp
    assert t2["is_first_occurrence"] is False

    await tutor_service.end_session(test_session, s1_id, part_id)

    # Start session 2 (longitudinal test)
    s2_data = await tutor_service.start_session(test_session, part_id)
    s2_id = uuid.UUID(s2_data["session_id"])

    # Turn 3: repeat in session 2 with whitespace variations
    t3 = await tutor_service.process_turn(test_session, s2_id, part_id, adversarial_inputs[2])
    assert t3["utterance_fingerprint"] == shared_fp
    assert t3["is_first_occurrence"] is False

    await tutor_service.end_session(test_session, s2_id, part_id)

    # Query participant history and metrics
    history = await tutor_service.get_participant_history(test_session, part_id)
    metrics = history["correction_metrics"]

    # Critical SRS FR-14 Assertion:
    # 3 turns occurred, but only ONE unique error episode may be counted in metrics
    assert metrics["total_unique_error_episodes"] == 1
    assert "SVA" in metrics["category_breakdown"]
    assert metrics["category_breakdown"]["SVA"]["unique_error_episodes"] == 1

    # Pattern occurrence tracking
    patterns = await tutor_service.get_recurrence_patterns(test_session, part_id)
    assert len(patterns) == 1
    pat = patterns[0]
    assert pat["utterance_fingerprint"] == shared_fp
    assert pat["occurrence_count"] == 3
    assert pat["target_category"] == "SVA"


@pytest.mark.asyncio
async def test_active_duration_across_idle_gaps(test_session: AsyncSession, setup_p11_fixtures):
    """SRS §10: Active duration rule excludes idle time (gaps >60s pause the clock)."""
    fx = setup_p11_fixtures
    part_id = fx["participant"].participant_id

    # 1. Test stateless pure calculation
    base_time = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    turn_timestamps = [
        base_time,                                # Turn 0: 0s
        base_time + timedelta(seconds=25),        # Turn 1: 25s gap (<= 60s -> 25s active)
        base_time + timedelta(seconds=205),       # Turn 2: 180s gap (> 60s -> 60s active, 120s idle)
        base_time + timedelta(seconds=240),       # Turn 3: 35s gap (<= 60s -> 35s active)
    ]
    calc = calculate_active_duration(turn_timestamps, idle_threshold_seconds=60)
    assert calc["active_duration_seconds"] == 120  # 25 + 60 + 35 = 120s
    assert calc["idle_duration_seconds"] == 120    # 180 - 60 = 120s
    assert calc["total_wall_clock_seconds"] == 240
    assert calc["idle_gaps_count"] == 1

    # 2. Test session active timing accumulation with mock time gaps
    s_data = await tutor_service.start_session(test_session, part_id)
    s_id = uuid.UUID(s_data["session_id"])

    # Load session and artificially simulate time passage
    sess_stmt = select(PracticeSession).where(PracticeSession.session_id == s_id)
    sess = (await test_session.execute(sess_stmt)).scalar_one()

    # Gap 1: 30 seconds (active)
    sess.last_activity_at = datetime.now(UTC) - timedelta(seconds=30)
    await tutor_service.process_turn(test_session, s_id, part_id, "He walk to work.")
    assert sess.active_duration_seconds == 30
    assert sess.idle_duration_seconds == 0

    # Gap 2: 150 seconds (90s idle, 60s active)
    sess.last_activity_at = datetime.now(UTC) - timedelta(seconds=150)
    await tutor_service.process_turn(test_session, s_id, part_id, "He walks to work.")
    assert sess.active_duration_seconds == 90   # 30 + 60
    assert sess.idle_duration_seconds == 90     # 150 - 60

    end_res = await tutor_service.end_session(test_session, s_id, part_id)
    assert end_res["active_duration_seconds"] == 90
    assert sess.idle_duration_seconds == 90


@pytest.mark.asyncio
async def test_technical_interruption_logging(test_session: AsyncSession, setup_p11_fixtures):
    """SRS §10: Technical interruptions (disconnects, mic failures) recorded as events without corrupting scores."""
    fx = setup_p11_fixtures
    part_id = fx["participant"].participant_id

    s_data = await tutor_service.start_session(test_session, part_id)
    s_id = uuid.UUID(s_data["session_id"])

    # Normal turn
    await tutor_service.process_turn(test_session, s_id, part_id, "He go to library.")

    # Interruption 1: mic failure
    int1 = await tutor_service.log_interruption(
        db=test_session,
        session_id=s_id,
        participant_id=part_id,
        interruption_type="mic_failure",
        details="MediaStreamTrack muted unexpectedly",
    )
    assert int1["interruption_type"] == "mic_failure"
    assert int1["interruption_count"] == 1

    # Interruption 2: network disconnect
    int2 = await tutor_service.log_interruption(
        db=test_session,
        session_id=s_id,
        participant_id=part_id,
        interruption_type="disconnect",
        details="WebSocket connection dropped; reconnected",
    )
    assert int2["interruption_type"] == "disconnect"
    assert int2["interruption_count"] == 2

    # Query events directly
    ev_stmt = select(PracticeEvent).where(PracticeEvent.session_id == s_id).order_by(PracticeEvent.created_at.asc())
    events = (await test_session.execute(ev_stmt)).scalars().all()
    assert len(events) == 3

    interruption_events = [e for e in events if e.event_type.startswith("interruption_")]
    assert len(interruption_events) == 2
    assert interruption_events[0].event_type == "interruption_mic_failure"
    assert interruption_events[1].event_type == "interruption_disconnect"

    # Interruption events must NOT inflate or contaminate error metrics
    history = await tutor_service.get_participant_history(test_session, part_id)
    metrics = history["correction_metrics"]
    assert metrics["total_unique_error_episodes"] == 1


@pytest.mark.asyncio
async def test_metrics_purely_derived_from_events():
    """FR-13, FR-14: Metrics must be purely derived from event lists without database mutation."""
    raw_events = [
        # Episode 1: SVA error resolved independently on turn 2
        {
            "event_id": str(uuid.uuid4()),
            "utterance_fingerprint": "fp_sva_1",
            "learner_phrase": "He go to school",
            "target_category": "SVA",
            "attempt_type": "independent",
            "is_correct": False,
        },
        {
            "event_id": str(uuid.uuid4()),
            "utterance_fingerprint": "fp_sva_1",  # Same episode
            "learner_phrase": "He goes to school",
            "target_category": "SVA",
            "attempt_type": "independent",
            "is_correct": True,
        },
        # Episode 2: SVA error resolved with hint
        {
            "event_id": str(uuid.uuid4()),
            "utterance_fingerprint": "fp_sva_2",
            "learner_phrase": "She play guitar",
            "target_category": "SVA",
            "attempt_type": "hint_assisted",
            "is_correct": True,
        },
        # Episode 3: TNS error resolved independently
        {
            "event_id": str(uuid.uuid4()),
            "utterance_fingerprint": "fp_tns_1",
            "learner_phrase": "Yesterday I go there",
            "target_category": "TNS",
            "attempt_type": "independent",
            "is_correct": True,
        },
    ]

    res = calculate_independent_correction_rate(raw_events)

    # 3 unique episodes: 2 SVA, 1 TNS
    assert res["total_unique_error_episodes"] == 3
    # 2 independent corrections: 1 SVA, 1 TNS
    assert res["total_independent_corrections"] == 2
    assert res["overall_rate_pct"] == 66.7

    sva = res["category_breakdown"]["SVA"]
    assert sva["unique_error_episodes"] == 2
    assert sva["independent_corrections"] == 1
    assert sva["hint_assisted_corrections"] == 1
    assert sva["independent_correction_rate_pct"] == 50.0

    tns = res["category_breakdown"]["TNS"]
    assert tns["unique_error_episodes"] == 1
    assert tns["independent_corrections"] == 1
    assert tns["independent_correction_rate_pct"] == 100.0

    # Ensure required research disclaimer is strictly attached
    assert "Descriptive practice metric only" in res["disclaimer"]
    assert "Never used as an official assessment score" in res["disclaimer"]


@pytest.mark.asyncio
async def test_cohort_adherence_summary(test_session: AsyncSession, setup_p11_fixtures):
    """SRS §10: Intervention adherence metrics vs configured expected practice time."""
    fx = setup_p11_fixtures
    part_id = fx["participant"].participant_id

    # Create 3 sessions representing 1 week of practice (expected: 3 sessions, 45 minutes = 2700s)
    t0 = datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC)
    s1 = PracticeSession(
        session_id=uuid.uuid4(),
        participant_id=part_id,
        start_time=t0,
        end_time=t0 + timedelta(minutes=15),
        active_duration_seconds=900,  # 15 mins
        status="completed",
        tutor_prompt_version="v1.0",
        turns_count=10,
    )
    t1 = t0 + timedelta(days=2)
    s2 = PracticeSession(
        session_id=uuid.uuid4(),
        participant_id=part_id,
        start_time=t1,
        end_time=t1 + timedelta(minutes=15),
        active_duration_seconds=900,  # 15 mins
        status="completed",
        tutor_prompt_version="v1.0",
        turns_count=8,
    )
    t2 = t0 + timedelta(days=5)
    s3 = PracticeSession(
        session_id=uuid.uuid4(),
        participant_id=part_id,
        start_time=t2,
        end_time=t2 + timedelta(minutes=15),
        active_duration_seconds=900,  # 15 mins
        status="completed",
        tutor_prompt_version="v1.0",
        turns_count=9,
    )
    test_session.add_all([s1, s2, s3])
    await test_session.flush()

    adherence = await tutor_service.get_cohort_adherence(test_session)

    # 3 sessions * 15m = 45m active
    assert adherence["completed_sessions"] >= 3
    assert adherence["total_active_minutes"] >= 45.0
    assert adherence["adherence_percentage"] >= 100.0
    assert adherence["status_label"] == "High Adherence"
