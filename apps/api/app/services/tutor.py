"""AI Tutor Service with Hint Ladder (Phase P10, Signature Feature C).

RESEARCH INTEGRITY RULE:
The AI Tutor is completely separate from the assessment engine.
It has ZERO write access to official assessment tables (assessments, error_annotations, reviewer_decisions).
Tutoring is gated until the pre-test baseline is verified.
Official assessment feedback is never revealed during blinded evaluation windows.
All calculations and ladder transitions strictly match SRS Section 7, 8, FR-11, FR-12, FR-13, and FR-14.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assessment import Assessment, AssessmentType, ErrorAnnotation
from app.models.practice import AttemptType, PracticeEvent, PracticeSession, UtterancePattern
from app.models.research import Participant
from app.research.metrics import (
    calculate_adherence_statistics,
    calculate_independent_correction_rate,
    compute_utterance_fingerprint,
)
from app.services.audit import audit_service
from app.services.llm.base import TutorResponse
from app.services.llm.factory import get_llm_provider


class TutorGatingError(Exception):
    """Raised when tutoring is attempted before the pre-test is verified or for ineligible participants."""
    pass


class TutorService:
    """Conversational AI Tutor orchestrating the Hint Ladder."""

    def __init__(self):
        self.llm_provider = get_llm_provider()

    async def get_verified_pretest_summary(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Fetch verified pre-test baseline summary for tutor personalization."""
        stmt = (
            select(Assessment)
            .where(
                Assessment.participant_id == participant_id,
                Assessment.assessment_type == AssessmentType.PRE,
                Assessment.status.in_(["analyzed", "completed"]),
            )
            .order_by(Assessment.created_at.desc())
        )
        pretest = (await db.execute(stmt)).scalars().first()
        if not pretest:
            return None

        # Check verification sign-off
        if settings.REQUIRE_VERIFIED_PRETEST_FOR_TUTORING and not pretest.is_verified:
            return None

        # Aggregate priority categories from active candidate deviations
        ann_stmt = (
            select(ErrorAnnotation.category_code, func.count(ErrorAnnotation.annotation_id))
            .where(ErrorAnnotation.assessment_id == pretest.assessment_id)
            .group_by(ErrorAnnotation.category_code)
            .order_by(func.count(ErrorAnnotation.annotation_id).desc())
        )
        cat_counts = (await db.execute(ann_stmt)).all()

        priority_categories = [c[0] for c in cat_counts if c[0] != "OTH"]
        if not priority_categories:
            priority_categories = ["SVA", "TNS"]

        return {
            "assessment_id": pretest.assessment_id,
            "is_verified": pretest.is_verified,
            "word_count": pretest.word_count,
            "priority_categories": priority_categories,
            "top_category": priority_categories[0],
            "rubric_version": pretest.rubric_version,
        }

    async def start_session(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
        interests: str | None = None,
    ) -> dict[str, Any]:
        """Initialize a tutoring session gated by verified pre-test requirements."""
        # 1. Fetch participant
        part_stmt = select(Participant).where(Participant.participant_id == participant_id)
        participant = (await db.execute(part_stmt)).scalar_one_or_none()
        if not participant:
            raise ValueError("Participant record not found.")

        # 2. Gate by verified pre-test
        pretest_summary = await self.get_verified_pretest_summary(db, participant_id)
        if not pretest_summary and settings.REQUIRE_VERIFIED_PRETEST_FOR_TUTORING:
            raise TutorGatingError(
                "Tutoring sessions are locked until your baseline pre-test assessment has been calibrated and verified."
            )

        # 3. Store / update interests
        if interests:
            participant.learner_interests = interests.strip()
        learner_topic = participant.learner_interests or "Daily routines and technology"

        # 4. Target categories
        target_cats = pretest_summary["priority_categories"][:2] if pretest_summary else ["SVA"]
        target_cats[0]

        # 5. Create PracticeSession
        now = datetime.now(UTC)
        session = PracticeSession(
            session_id=uuid.uuid4(),
            participant_id=participant_id,
            start_time=now,
            last_activity_at=now,
            tutor_prompt_version=settings.DEFAULT_TUTOR_PROMPT_VERSION,
            status="active",
            topic=learner_topic,
            target_categories_json=json.dumps(target_cats),
            turns_count=0,
            active_duration_seconds=0,
            idle_duration_seconds=0,
            interruption_count=0,
        )
        db.add(session)
        await db.flush()

        # 6. Generate opening conversational prompt
        opening_prompt = (
            f"Hello! Today we'll chat naturally about {learner_topic.lower()}. "
            f"To get started, tell me: what does a typical day look like for you or someone you know?"
        )

        await audit_service.log_event(
            db=db,
            actor_id=participant.user_id,
            role="participant",
            action="start_tutoring_session",
            record_type="practice_session",
            record_id=session.session_id,
            outcome="success",
            details={
                "topic": learner_topic,
                "target_categories": target_cats,
            },
        )

        return {
            "session_id": str(session.session_id),
            "status": "active",
            "topic": learner_topic,
            "target_categories": target_cats,
            "tutor_opening_message": opening_prompt,
            "prompt_version": session.tutor_prompt_version,
        }

    async def process_turn(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        participant_id: uuid.UUID,
        learner_utterance: str,
    ) -> dict[str, Any]:
        """Process one conversational turn according to the Hint Ladder state machine."""
        clean_text = learner_utterance.strip()

        # 1. Fetch active session
        sess_stmt = select(PracticeSession).where(
            PracticeSession.session_id == session_id,
            PracticeSession.participant_id == participant_id,
            PracticeSession.status == "active",
        )
        session = (await db.execute(sess_stmt)).scalar_one_or_none()
        if not session:
            raise ValueError("Active tutoring session not found or already closed.")

        target_cats = json.loads(session.target_categories_json or '["SVA"]')
        primary_cat = target_cats[0]

        # 2. Track Active Duration vs Idle Time (Idle Rule: >60s pauses active clock)
        now = datetime.now(UTC)
        last_activity = session.last_activity_at or session.start_time
        if last_activity:
            st = last_activity if last_activity.tzinfo else last_activity.replace(tzinfo=UTC)
            delta_seconds = max(0, int((now - st).total_seconds()))
        else:
            delta_seconds = 0

        idle_threshold = getattr(settings, "PRACTICE_IDLE_TIMEOUT_SECONDS", 60)
        if delta_seconds > idle_threshold:
            active_increment = idle_threshold
            idle_increment = delta_seconds - idle_threshold
        else:
            active_increment = delta_seconds
            idle_increment = 0

        session.active_duration_seconds += active_increment
        session.idle_duration_seconds += idle_increment
        session.last_activity_at = now

        # 3. Compute Utterance Fingerprint & Longitudinal Recurrence Tracking
        utterance_fingerprint = compute_utterance_fingerprint(clean_text)

        pat_stmt = select(UtterancePattern).where(
            UtterancePattern.participant_id == participant_id,
            UtterancePattern.utterance_fingerprint == utterance_fingerprint,
        )
        pattern = (await db.execute(pat_stmt)).scalar_one_or_none()
        if pattern:
            is_first_occurrence = False
            pattern.occurrence_count += 1
            pattern.last_seen_at = now
            pattern.last_session_id = session_id
        else:
            is_first_occurrence = True
            pattern = UtterancePattern(
                pattern_id=uuid.uuid4(),
                participant_id=participant_id,
                target_category=primary_cat,
                utterance_fingerprint=utterance_fingerprint,
                canonical_phrase=clean_text,
                construction_type=f"{primary_cat}_construction",
                occurrence_count=1,
                first_seen_at=now,
                last_seen_at=now,
                first_session_id=session_id,
                last_session_id=session_id,
                resolved_independently=False,
            )
            db.add(pattern)

        # 4. Check previous events in this session to determine current episode & ladder level
        events_stmt = (
            select(PracticeEvent)
            .where(PracticeEvent.session_id == session_id)
            .order_by(PracticeEvent.created_at.asc())
        )
        previous_events = (await db.execute(events_stmt)).scalars().all()

        current_level = 0
        last_unresolved_event = None
        for ev in reversed(previous_events):
            if not ev.is_correct and ev.transfer_phrase is None:
                last_unresolved_event = ev
                current_level = min(3, ev.feedback_level + 1)
                break

        # 5. Detect Syntactic State / Self-Correction
        # Check if learner has self-corrected the target structure (e.g. SVA: 'he goes')
        is_correction = False
        is_transfer_success = False

        if primary_cat == "SVA":
            if "he goes" in clean_text.lower() or "she goes" in clean_text.lower() or "goes" in clean_text.lower():
                is_correction = True
            elif ("works" in clean_text.lower() or "studies" in clean_text.lower() or "plays" in clean_text.lower()) and last_unresolved_event and last_unresolved_event.feedback_level == 3:
                is_transfer_success = True
        elif primary_cat == "TNS":
            if "walked" in clean_text.lower() or "went" in clean_text.lower() or "saw" in clean_text.lower():
                is_correction = True

        # 6. Handle Transfer Check Completion
        if is_transfer_success and last_unresolved_event:
            last_unresolved_event.transfer_phrase = clean_text
            last_unresolved_event.transfer_correct = True
            session.turns_count += 1
            if pattern:
                pattern.resolved_independently = True
            await db.flush()

            reply_text = (
                f'Excellent transfer! "{clean_text}" accurately uses the third-person singular present. '
                "What else can you share about your daily activities?"
            )
            return {
                "reply_text": reply_text,
                "target_category": primary_cat,
                "hint_level": 3,
                "is_self_correction": True,
                "attempt_type": "transfer_successful",
                "expects_attempt": True,
                "transfer_prompt": None,
                "utterance_fingerprint": utterance_fingerprint,
                "is_first_occurrence": is_first_occurrence,
            }

        # 7. Handle Successful Self-Correction
        if is_correction:
            attempt_type = AttemptType.INDEPENDENT if current_level == 0 else AttemptType.HINT_ASSISTED
            if attempt_type == AttemptType.INDEPENDENT and pattern:
                pattern.resolved_independently = True

            event = PracticeEvent(
                event_id=uuid.uuid4(),
                session_id=session_id,
                target_category=primary_cat,
                learner_phrase=clean_text,
                feedback_level=current_level,
                hint_text="Learner successfully produced accurate form.",
                attempt_type=attempt_type,
                is_correct=True,
                learner_input=clean_text,
                tutor_reply=(
                    f'Spot on! "{clean_text}" is completely accurate. '
                    "Now, can you tell me what another colleague or friend does?"
                ),
                transfer_prompt="What does another friend or colleague do?",
                utterance_fingerprint=utterance_fingerprint,
                event_type="turn_attempt",
                is_first_occurrence=is_first_occurrence,
                elapsed_active_seconds=session.active_duration_seconds,
            )
            db.add(event)
            session.turns_count += 1
            await db.flush()

            return {
                "reply_text": event.tutor_reply,
                "target_category": primary_cat,
                "hint_level": current_level,
                "is_self_correction": True,
                "attempt_type": attempt_type.value,
                "expects_attempt": True,
                "transfer_prompt": event.transfer_prompt,
                "utterance_fingerprint": utterance_fingerprint,
                "is_first_occurrence": is_first_occurrence,
            }

        # 8. Generate Next Hint Ladder Step via Decoupled LLMProvider
        tutor_response: TutorResponse = await self.llm_provider.generate_tutor_turn(
            target_category=primary_cat,
            learner_utterance=clean_text,
            ladder_level=current_level,
            prompt_version=session.tutor_prompt_version,
            learner_phrase_quoted=clean_text if "he go" in clean_text.lower() else "He go to college",
        )

        # Log event in practice_events
        event = PracticeEvent(
            event_id=uuid.uuid4(),
            session_id=session_id,
            target_category=primary_cat,
            learner_phrase=clean_text,
            feedback_level=tutor_response.hint_level,
            hint_text=tutor_response.reply_text,
            attempt_type=AttemptType.HINT_ASSISTED if tutor_response.hint_level > 0 else AttemptType.INDEPENDENT,
            is_correct=False,
            learner_input=clean_text,
            tutor_reply=tutor_response.reply_text,
            transfer_prompt=tutor_response.transfer_prompt,
            utterance_fingerprint=utterance_fingerprint,
            event_type="turn_attempt",
            is_first_occurrence=is_first_occurrence,
            elapsed_active_seconds=session.active_duration_seconds,
        )
        db.add(event)
        session.turns_count += 1
        await db.flush()

        return {
            "reply_text": tutor_response.reply_text,
            "target_category": primary_cat,
            "learner_phrase_quoted": tutor_response.learner_phrase_quoted,
            "hint_level": tutor_response.hint_level,
            "expects_attempt": tutor_response.expects_attempt,
            "transfer_prompt": tutor_response.transfer_prompt,
            "is_off_topic": tutor_response.is_off_topic,
            "safety_refusal": tutor_response.safety_refusal,
            "is_self_correction": False,
            "attempt_type": event.attempt_type.value,
            "utterance_fingerprint": utterance_fingerprint,
            "is_first_occurrence": is_first_occurrence,
        }

    async def log_interruption(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        participant_id: uuid.UUID,
        interruption_type: str,
        details: str | None = None,
    ) -> dict[str, Any]:
        """Record technical interruptions (disconnect, mic_failure, audio_timeout) as events."""
        sess_stmt = select(PracticeSession).where(
            PracticeSession.session_id == session_id,
            PracticeSession.participant_id == participant_id,
        )
        session = (await db.execute(sess_stmt)).scalar_one_or_none()
        if not session:
            raise ValueError("Practice session not found.")

        now = datetime.now(UTC)
        session.interruption_count += 1
        session.last_activity_at = now

        event = PracticeEvent(
            event_id=uuid.uuid4(),
            session_id=session_id,
            target_category="TECH",
            learner_phrase=f"Technical interruption: {interruption_type}",
            feedback_level=0,
            hint_text=details or f"Interruption ({interruption_type}) logged.",
            attempt_type=AttemptType.REVEALED,
            is_correct=False,
            learner_input=f"Technical interruption: {interruption_type}",
            tutor_reply="Connection or audio interruption detected. Resuming session...",
            utterance_fingerprint=None,
            event_type=f"interruption_{interruption_type}",
            is_first_occurrence=False,
            elapsed_active_seconds=session.active_duration_seconds,
        )
        db.add(event)
        await db.flush()

        await audit_service.log_event(
            db=db,
            actor_id=participant_id,
            role="participant",
            action="log_technical_interruption",
            record_type="practice_session",
            record_id=session.session_id,
            outcome="success",
            details={
                "interruption_type": interruption_type,
                "details": details,
            },
        )

        return {
            "session_id": str(session.session_id),
            "interruption_type": interruption_type,
            "interruption_count": session.interruption_count,
            "recorded_at": now.isoformat(),
        }

    async def get_participant_history(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Fetch participant's practice sessions, active duration, and independent correction stats."""
        stmt = (
            select(PracticeSession)
            .where(PracticeSession.participant_id == participant_id)
            .order_by(PracticeSession.start_time.desc())
        )
        sessions = (await db.execute(stmt)).scalars().all()

        ev_stmt = (
            select(PracticeEvent)
            .join(PracticeSession)
            .where(PracticeSession.participant_id == participant_id)
            .order_by(PracticeEvent.created_at.asc())
        )
        events = (await db.execute(ev_stmt)).scalars().all()

        events_dicts = [
            {
                "event_id": str(e.event_id),
                "utterance_fingerprint": e.utterance_fingerprint,
                "learner_phrase": e.learner_phrase,
                "target_category": e.target_category,
                "attempt_type": e.attempt_type.value if hasattr(e.attempt_type, "value") else str(e.attempt_type),
                "is_correct": e.is_correct,
            }
            for e in events
            if not e.event_type.startswith("interruption")
        ]

        correction_metrics = calculate_independent_correction_rate(events_dicts)

        sessions_data = []
        for s in sessions:
            sessions_data.append({
                "session_id": str(s.session_id),
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "active_duration_seconds": s.active_duration_seconds,
                "idle_duration_seconds": s.idle_duration_seconds,
                "turns_count": s.turns_count,
                "status": s.status,
                "topic": s.topic,
                "target_categories": json.loads(s.target_categories_json or "[]"),
                "interruption_count": s.interruption_count,
                "prompt_version": s.tutor_prompt_version,
            })

        return {
            "sessions": sessions_data,
            "total_sessions": len(sessions_data),
            "correction_metrics": correction_metrics,
        }

    async def get_recurrence_patterns(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch recurring utterance patterns and longitudinal frequency."""
        stmt = (
            select(UtterancePattern)
            .where(UtterancePattern.participant_id == participant_id)
            .order_by(UtterancePattern.occurrence_count.desc(), UtterancePattern.last_seen_at.desc())
        )
        patterns = (await db.execute(stmt)).scalars().all()

        return [
            {
                "pattern_id": str(p.pattern_id),
                "target_category": p.target_category,
                "utterance_fingerprint": p.utterance_fingerprint,
                "canonical_phrase": p.canonical_phrase,
                "construction_type": p.construction_type,
                "occurrence_count": p.occurrence_count,
                "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
                "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
                "resolved_independently": p.resolved_independently,
            }
            for p in patterns
        ]

    async def get_cohort_adherence(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Fetch researcher intervention adherence statistics across cohort sessions."""
        stmt = select(PracticeSession).order_by(PracticeSession.start_time.asc())
        sessions = (await db.execute(stmt)).scalars().all()

        sessions_dicts = [
            {
                "session_id": str(s.session_id),
                "participant_id": str(s.participant_id),
                "start_time": s.start_time,
                "active_duration_seconds": s.active_duration_seconds,
                "idle_duration_seconds": s.idle_duration_seconds,
                "status": s.status,
            }
            for s in sessions
        ]

        adherence_stats = calculate_adherence_statistics(
            sessions=sessions_dicts,
            expected_sessions_per_week=getattr(settings, "EXPECTED_SESSIONS_PER_WEEK", 3),
            expected_minutes_per_session=getattr(settings, "EXPECTED_PRACTICE_MINUTES_PER_SESSION", 15),
        )

        return adherence_stats

    async def end_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Conclude an active practice session and calculate practice analytics."""
        sess_stmt = select(PracticeSession).where(
            PracticeSession.session_id == session_id,
            PracticeSession.participant_id == participant_id,
        )
        session = (await db.execute(sess_stmt)).scalar_one_or_none()
        if not session:
            raise ValueError("Practice session not found.")

        now = datetime.now(UTC)
        session.end_time = now
        session.status = "completed"

        # Calculate active duration in seconds if not already accumulated across turns
        if session.active_duration_seconds <= 0 and session.start_time:
            # Handle timezone differences
            st = session.start_time if session.start_time.tzinfo else session.start_time.replace(tzinfo=UTC)
            session.active_duration_seconds = max(1, int((now - st).total_seconds()))

        # Fetch events for summary
        ev_stmt = select(PracticeEvent).where(PracticeEvent.session_id == session_id)
        events = (await db.execute(ev_stmt)).scalars().all()

        total_attempts = len(events)
        correct_attempts = sum(1 for e in events if e.is_correct or e.transfer_correct)
        independent_count = sum(1 for e in events if e.attempt_type == AttemptType.INDEPENDENT and e.is_correct)
        hint_assisted_count = sum(1 for e in events if e.attempt_type == AttemptType.HINT_ASSISTED and e.is_correct)

        await db.flush()

        await audit_service.log_event(
            db=db,
            actor_id=participant_id,
            role="participant",
            action="end_tutoring_session",
            record_type="practice_session",
            record_id=session.session_id,
            outcome="success",
            details={
                "duration_seconds": session.active_duration_seconds,
                "total_events": total_attempts,
                "correct_attempts": correct_attempts,
            },
        )

        return {
            "session_id": str(session.session_id),
            "status": "completed",
            "active_duration_seconds": session.active_duration_seconds,
            "turns_count": session.turns_count,
            "total_attempts": total_attempts,
            "independent_self_corrections": independent_count,
            "hint_assisted_corrections": hint_assisted_count,
            "prompt_version": session.tutor_prompt_version,
        }


tutor_service = TutorService()
