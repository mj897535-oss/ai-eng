"""Audio Assessment Ingestion and Upload Orchestration (Phase P6).

NON-NEGOTIABLE RESEARCH INTEGRITY & SECURITY RULES:
- Participant must have active, current consent before ANY audio endpoint is callable (FR-03).
- Only the storage key is saved in the database, NEVER a public URL (NFR-SEC-03).
- Strict idempotency key guarantees duplicate network submissions create exactly ONE assessment (NFR-REL-01).
- One official submission per participant per assessment type unless a researcher explicitly authorizes a retake (audited).
- Minimum duration (>= 3s) and maximum duration limits enforced; corrupt / empty files rejected.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.assessment import Assessment, AssessmentTask, AssessmentType
from app.models.research import Participant
from app.services.audit import audit_service
from app.services.config import config_service
from app.services.storage import storage_provider


class PresignedUploadRequest(BaseModel):
    task_id: uuid.UUID | None = None
    codec: str = "audio/webm"


class PresignedUploadResponse(BaseModel):
    upload_url: str
    storage_key: str
    method: str
    headers: dict[str, str]
    expires_at: int
    task: dict[str, Any]
    rubric_version: str


class AssessmentSubmitInput(BaseModel):
    task_id: uuid.UUID
    assessment_type: AssessmentType
    storage_key: str
    duration_seconds: float
    checksum: str | None = None
    idempotency_key: str = Field(..., min_length=1, max_length=100)


class RetakeAuthInput(BaseModel):
    assessment_type: AssessmentType
    reason: str


class AudioAssessmentService:
    async def get_or_verify_participant(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
    ) -> Participant:
        """Verify participant exists, has active consent, and is not withdrawn."""
        stmt = select(Participant).where(Participant.participant_id == participant_id)
        participant = (await db.execute(stmt)).scalar_one_or_none()
        if not participant:
            raise ValueError(f"Participant '{participant_id}' not found.")

        if participant.is_withdrawn:
            raise ValueError("Research participation has been withdrawn. No further data collection is permitted.")

        if not participant.current_consent_version or participant.current_consent_version != settings.CURRENT_CONSENT_VERSION:
            raise ValueError("Valid research consent required before recording audio.")

        return participant

    async def prepare_upload(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
        assessment_type: AssessmentType,
        codec: str = "audio/webm",
        task_id: uuid.UUID | None = None,
    ) -> PresignedUploadResponse:
        """Verify consent, check retake authorization, and mint short-lived presigned upload URL."""
        participant = await self.get_or_verify_participant(db, participant_id)

        # Enforce one official submission rule unless authorized retake exists
        existing_stmt = select(Assessment).where(
            Assessment.participant_id == participant_id,
            Assessment.assessment_type == assessment_type,
            Assessment.is_official == True,  # noqa: E712
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()

        if existing:
            # Check if researcher has authorized a retake that has not yet been consumed
            retake_authorized = existing.retake_authorized_at is not None and existing.retake_reason is not None
            if not retake_authorized:
                raise ValueError(
                    f"Official {assessment_type.value} assessment already completed for this participant. "
                    "A researcher must authorize a retake before a new recording can be submitted."
                )

        # Reproducibly assign topic task if not explicitly passed
        if task_id:
            t_stmt = select(AssessmentTask).where(AssessmentTask.task_id == task_id)
            task = (await db.execute(t_stmt)).scalar_one_or_none()
            if not task:
                raise ValueError(f"Task '{task_id}' not found.")
            assigned_task_info = {
                "task_id": str(task.task_id),
                "title": task.title,
                "prompt_text": task.prompt_text,
                "prep_time_seconds": task.prep_time_seconds,
                "duration_seconds": task.duration_seconds,
                "difficulty_level": task.difficulty_level,
                "rubric_version": task.rubric_version,
            }
        else:
            topic_assignment = await config_service.assign_topic_pair(db, participant.research_code)
            if assessment_type == AssessmentType.PRE:
                assigned_task_info = topic_assignment["pre_task"]
            else:
                assigned_task_info = topic_assignment["post_task"]

        # Generate unique storage key
        random_suffix = uuid.uuid4().hex[:12]
        file_ext = "mp4" if "mp4" in codec else "webm"
        storage_key = f"audio/{participant.research_code}/{assessment_type.value}_{random_suffix}.{file_ext}"

        # Mint presigned upload URL with private S3/MinIO bucket
        presigned = storage_provider.generate_presigned_upload_url(
            key=storage_key,
            content_type=codec,
            expires_in=settings.S3_PRESIGNED_EXPIRATION_SECONDS,
        )

        return PresignedUploadResponse(
            upload_url=presigned["upload_url"],
            storage_key=storage_key,
            method=presigned["method"],
            headers=presigned["headers"],
            expires_at=presigned["expires_at"],
            task=assigned_task_info,
            rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        )

    async def submit_assessment(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
        payload: AssessmentSubmitInput,
        actor_id: uuid.UUID | None = None,
    ) -> Assessment:
        """Finalize assessment ingestion with strict server-side validation and idempotency."""
        participant = await self.get_or_verify_participant(db, participant_id)

        # 1. IDEMPOTENCY CHECK (NFR-REL-01): Return existing record if already processed with this key
        idemp_stmt = select(Assessment).where(Assessment.idempotency_key == payload.idempotency_key)
        existing_idemp = (await db.execute(idemp_stmt)).scalar_one_or_none()
        if existing_idemp:
            logger.info("Idempotent submission replay detected for key: %s", payload.idempotency_key)
            return existing_idemp

        # 2. AUDIO INTEGRITY & DURATION VALIDATION
        if payload.duration_seconds < 3.0:
            raise ValueError("Recording is too short (minimum 3 seconds required). Please re-record your answer.")
        if payload.duration_seconds > 90.0:
            raise ValueError("Recording exceeds maximum permitted assessment duration.")

        # 3. Check for previous official attempt
        prev_stmt = select(Assessment).where(
            Assessment.participant_id == participant_id,
            Assessment.assessment_type == payload.assessment_type,
            Assessment.is_official == True,  # noqa: E712
        )
        prev_assessment = (await db.execute(prev_stmt)).scalar_one_or_none()
        if prev_assessment:
            if not prev_assessment.retake_authorized_at:
                raise ValueError(
                    f"Official {payload.assessment_type.value} assessment already submitted for this participant."
                )
            # Demote previous attempt as this is an authorized retake
            prev_assessment.is_official = False

        # 4. Create new Assessment (APPEND-ONLY)
        new_assessment = Assessment(
            assessment_id=uuid.uuid4(),
            participant_id=participant_id,
            task_id=payload.task_id,
            assessment_type=payload.assessment_type,
            audio_key=payload.storage_key,
            status="queued_for_transcription",
            audio_duration_seconds=payload.duration_seconds,
            audio_checksum=payload.checksum,
            idempotency_key=payload.idempotency_key,
            is_official=True,
            transcript=None,
            word_count=0,
            stt_version=settings.STT_PROVIDER,
            rubric_version=settings.DEFAULT_RUBRIC_VERSION,
            model_version=settings.LLM_PROVIDER,
        )
        db.add(new_assessment)
        await db.flush()

        # 5. Log audit trail
        await audit_service.log_event(
            db=db,
            action="audio_submission",
            actor_id=actor_id or participant.user_id,
            role="participant",
            record_type="assessment",
            record_id=str(new_assessment.assessment_id),
            outcome="success",
            details={
                "assessment_type": payload.assessment_type.value,
                "duration_seconds": payload.duration_seconds,
                "storage_key": payload.storage_key,
                "idempotency_key": payload.idempotency_key,
                "task_id": str(payload.task_id),
            },
        )

        return new_assessment

    async def authorize_retake(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
        assessment_type: AssessmentType,
        reason: str,
        researcher_id: uuid.UUID,
    ) -> Assessment:
        """Allow a researcher to authorize an official retake (SRS FR-04)."""
        stmt = select(Assessment).where(
            Assessment.participant_id == participant_id,
            Assessment.assessment_type == assessment_type,
            Assessment.is_official == True,  # noqa: E712
        )
        assessment = (await db.execute(stmt)).scalar_one_or_none()
        if not assessment:
            raise ValueError(f"No completed official {assessment_type.value} assessment found to retake.")

        now = datetime.now(UTC)
        assessment.retake_authorized_by = researcher_id
        assessment.retake_authorized_at = now
        assessment.retake_reason = reason
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="retake_authorized",
            actor_id=researcher_id,
            role="researcher_admin",
            record_type="assessment",
            record_id=str(assessment.assessment_id),
            outcome="success",
            details={
                "participant_id": str(participant_id),
                "assessment_type": assessment_type.value,
                "reason": reason,
            },
        )
        return assessment


audio_service = AudioAssessmentService()
