"""Speech-To-Text Pipeline & Job State Machine.

RESEARCH & ARCHITECTURE RULES:
1. Status machine: queued -> transcribing -> transcribed | failed -> retrying -> needs_attention.
2. Max 3 retries before dead-lettering to needs_attention.
3. Faithful transcription: preserve all spoken ungrammaticalities and disfluencies verbatim.
4. Word-counting uses the frozen rubric rules.
5. All STT telemetry, latency, and costs logged to stt_job_metrics for the Pilot Kit.
6. Transcript rows in assessments are strictly immutable once written.
"""

import difflib
import json
import logging
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assessment import Assessment, STTJobMetric, TranscriptRevision
from app.models.identity import User
from app.services.audit import audit_service
from app.services.storage import storage_provider
from app.services.stt.base import STTProvider, STTResponse
from app.services.stt.factory import get_stt_provider
from app.services.stt.word_counter import count_words

logger = logging.getLogger(__name__)

MAX_STT_RETRIES = 3
WHISPER_COST_PER_SECOND_USD = 0.006 / 60.0  # $0.006 per minute standard pricing


class STTPipelineService:
    """Manages asynchronous transcription processing, retry state machine, and Pilot Kit metrics."""

    def __init__(self, provider: STTProvider | None = None):
        self._provider = provider

    def get_provider(self) -> STTProvider:
        if self._provider:
            return self._provider
        return get_stt_provider()

    async def process_transcription_job(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        force_retry: bool = False,
    ) -> Assessment:
        """Run STT job following the status state machine with dead-letter retries."""
        # 1. Fetch Assessment
        stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
        assessment = (await db.execute(stmt)).scalar_one_or_none()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found.")

        # Check terminal success
        if assessment.status == "transcribed" and not force_retry:
            logger.info("Assessment %s already successfully transcribed.", assessment_id)
            return assessment

        # Check terminal dead-letter unless explicitly forced
        if assessment.status == "needs_attention" and not force_retry:
            raise ValueError(
                f"Assessment {assessment_id} has exceeded maximum retries and requires researcher attention."
            )

        # 2. Transition state: -> 'transcribing'
        assessment.status = "transcribing"
        await db.commit()
        await db.refresh(assessment)

        start_time = time.perf_counter()
        provider = self.get_provider()

        try:
            # 3. Prepare audio reference and options
            options: dict[str, Any] = {
                "checksum": assessment.audio_checksum,
                "audio_duration": assessment.audio_duration_seconds or 60.0,
            }

            # If using real Whisper adapter or needed, retrieve audio bytes
            audio_ref: str | bytes = assessment.audio_key
            if settings.STT_PROVIDER.lower() in {"whisper", "openai"}:
                audio_bytes = storage_provider.get_file(assessment.audio_key)
                options["audio_bytes"] = audio_bytes

            # 4. Execute transcription via decoupled interface
            stt_result: STTResponse = await provider.transcribe(
                audio_ref=audio_ref,
                language_hint="en",
                options=options,
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # 5. Calculate faithful word count using frozen rubric rule
            word_count = count_words(stt_result.text)

            # 6. Format words json and assess confidence
            words_dict_list = [
                {
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "confidence": w.confidence,
                }
                for w in stt_result.words
            ]
            words_json = json.dumps(words_dict_list)

            low_conf_words = sum(1 for w in stt_result.words if w.confidence < 0.70)
            low_conf_flag = low_conf_words > 0 or stt_result.overall_confidence < 0.80

            # 7. Persist raw response payload into private object storage
            raw_payload_key = f"transcripts/raw/{assessment.assessment_id}.json"
            raw_payload_content = (
                stt_result.raw_response_ref
                if isinstance(stt_result.raw_response_ref, str)
                else json.dumps(stt_result.raw_response_ref or {})
            )
            storage_provider.upload_file(
                key=raw_payload_key,
                data=raw_payload_content.encode("utf-8"),
                content_type="application/json",
            )

            # 8. Record telemetry in research.stt_job_metrics (Pilot Kit)
            duration_sec = assessment.audio_duration_seconds or (
                stt_result.words[-1].end if stt_result.words else 60.0
            )
            estimated_cost = (
                round(duration_sec * WHISPER_COST_PER_SECOND_USD, 5)
                if stt_result.provider == "whisper"
                else 0.0
            )

            metric = STTJobMetric(
                metric_id=uuid.uuid4(),
                assessment_id=assessment.assessment_id,
                provider=stt_result.provider,
                model_version=stt_result.model_version,
                audio_duration_seconds=round(duration_sec, 2),
                latency_ms=latency_ms,
                estimated_cost_usd=estimated_cost,
                word_count=word_count,
                average_confidence=stt_result.overall_confidence,
                low_confidence_count=low_conf_words,
                retry_count=assessment.retry_count,
            )
            db.add(metric)

            # 9. Update Assessment with immutable transcript and transition to 'transcribed'
            assessment.transcript = stt_result.text
            assessment.word_count = word_count
            assessment.words_json = words_json
            assessment.raw_stt_response_key = raw_payload_key
            assessment.stt_confidence = stt_result.overall_confidence
            assessment.low_confidence_flag = low_conf_flag
            assessment.stt_version = stt_result.model_version
            assessment.status = "transcribed"
            assessment.last_error = None

            await audit_service.log_event(
                db=db,
                action="assessment_transcribed",
                record_type="assessment",
                record_id=str(assessment.assessment_id),
                outcome="success",
            )

            await db.commit()
            await db.refresh(assessment)
            logger.info("Successfully transcribed assessment %s (word_count=%d)", assessment_id, word_count)
            return assessment

        except Exception as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("STT transcription error for assessment %s: %s", assessment_id, exc)

            assessment.retry_count += 1
            assessment.last_error = str(exc)

            if assessment.retry_count >= MAX_STT_RETRIES:
                assessment.status = "needs_attention"
            else:
                assessment.status = "retrying"

            await audit_service.log_event(
                db=db,
                action="assessment_transcription_failed",
                record_type="assessment",
                record_id=str(assessment.assessment_id),
                outcome="failure",
            )
            await db.commit()
            await db.refresh(assessment)
            raise exc

    async def create_transcript_revision(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        revised_transcript: str,
        reason: str,
        reviewer: User,
    ) -> TranscriptRevision:
        """Create a human review revision without mutating the original transcript row."""
        stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
        assessment = (await db.execute(stmt)).scalar_one_or_none()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found.")

        if not assessment.transcript:
            raise ValueError("Cannot revise an assessment that has not yet been transcribed.")

        if not revised_transcript or not revised_transcript.strip():
            raise ValueError("Revised transcript cannot be empty.")

        if not reason or not reason.strip():
            raise ValueError("A reason must be documented for any research transcript revision.")

        # Compute word count of revised transcript
        revised_word_count = count_words(revised_transcript)

        # Generate readable token-level diff
        orig_tokens = assessment.transcript.split()
        rev_tokens = revised_transcript.split()
        diff_lines = list(difflib.ndiff(orig_tokens, rev_tokens))
        diff_json = json.dumps({"diff_tokens": diff_lines})

        revision = TranscriptRevision(
            revision_id=uuid.uuid4(),
            assessment_id=assessment.assessment_id,
            revised_transcript=revised_transcript.strip(),
            revised_word_count=revised_word_count,
            reviewer_id=reviewer.id,
            reason=reason.strip(),
            diff_json=diff_json,
        )
        db.add(revision)

        await audit_service.log_event(
            db=db,
            action="transcript_revision_created",
            record_type="assessment",
            record_id=str(assessment.assessment_id),
            outcome="success",
            actor_id=reviewer.id,
        )

        await db.commit()
        await db.refresh(revision)
        return revision


stt_pipeline_service = STTPipelineService()
