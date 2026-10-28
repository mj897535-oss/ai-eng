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
from app.models.assessment import Assessment, AssessmentType, ErrorAnnotation, ReviewDecisionType, ReviewerDecision
from app.models.identity import User
from app.models.practice import AttemptType, PracticeEvent, PracticeSession
from app.models.research import Participant, StudyGroup
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
        primary_cat = target_cats[0]

        # 5. Create PracticeSession
        session = PracticeSession(
            session_id=uuid.uuid4(),
            participant_id=participant_id,
            start_time=datetime.now(UTC),
            tutor_prompt_version=settings.DEFAULT_TUTOR_PROMPT_VERSION,
            status="active",
            topic=learner_topic,
            target_categories_json=json.dumps(target_cats),
            turns_count=0,
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

        # 2. Check previous events in this session to determine current episode & ladder level
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

        # 3. Detect Syntactic State / Self-Correction
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

        # 4. Handle Transfer Check Completion
        if is_transfer_success and last_unresolved_event:
            last_unresolved_event.transfer_phrase = clean_text
            last_unresolved_event.transfer_correct = True
            session.turns_count += 1
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
            }

        # 5. Handle Successful Self-Correction
        if is_correction:
            attempt_type = AttemptType.INDEPENDENT if current_level == 0 else AttemptType.HINT_ASSISTED
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
            }

        # 6. Generate Next Hint Ladder Step via Decoupled LLMProvider
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
        }

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

        # Calculate active duration in seconds
        if session.start_time:
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
