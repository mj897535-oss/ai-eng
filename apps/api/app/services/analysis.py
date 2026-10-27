"""Error Analysis Engine & Syntactic Deviation Orchestration.

SCIENTIFIC CORE & RESEARCH RULES:
1. Fully separated from the AI tutor.
2. Assessor role: neutral spoken-English syntax evaluator.
3. Post-validation: exact span match, taxonomy category verification, deduplication.
4. Auto-routing: confidence < threshold, non-candidate flag, or OTH routed to review queue.
5. Participant visibility controlled by research protocol flag (default hidden).
6. Annotations are strictly APPEND-ONLY research artefacts.
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assessment import Assessment, ErrorAnnotation
from app.models.identity import User
from app.services.audit import audit_service
from app.services.llm.base import AssessorOutput, LLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.storage import storage_provider
from app.services.validator import post_validator

logger = logging.getLogger(__name__)


class ErrorAnalysisService:
    """Orchestrates candidate syntactic deviation detection, validation, and auto-routing."""

    def __init__(self, provider: LLMProvider | None = None):
        self._provider = provider

    def get_provider(self) -> LLMProvider:
        if self._provider:
            return self._provider
        return get_llm_provider()

    async def analyze_assessment(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        force_retry: bool = False,
    ) -> list[ErrorAnnotation]:
        """Run candidate error detection with Pydantic validation, retries, and post-validation."""
        # 1. Fetch assessment
        stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
        assessment = (await db.execute(stmt)).scalar_one_or_none()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found.")

        if not assessment.transcript:
            raise ValueError(
                f"Assessment {assessment_id} has no transcript. Speech-to-text must complete before error analysis."
            )

        # Idempotency check: if already analyzed and not forcing retry, return existing annotations
        if assessment.status in {"analyzed", "completed"} and not force_retry:
            ann_stmt = select(ErrorAnnotation).where(ErrorAnnotation.assessment_id == assessment_id)
            existing = (await db.execute(ann_stmt)).scalars().all()
            if existing:
                logger.info("Assessment %s already analyzed (%d annotations).", assessment_id, len(existing))
                return list(existing)

        rubric_version = assessment.rubric_version or settings.DEFAULT_RUBRIC_VERSION
        prompt_version = assessment.prompt_version or settings.DEFAULT_ASSESSOR_PROMPT_VERSION

        provider = self.get_provider()
        assessor_output: AssessorOutput | None = None
        last_exception: Exception | None = None

        # 2. Execution with Retries for JSON / Validation Failures
        max_retries = settings.MAX_ANALYSIS_RETRIES
        for attempt in range(1, max_retries + 1):
            try:
                assessor_output = await provider.analyze_syntax(
                    transcript=assessment.transcript,
                    rubric_version=rubric_version,
                    prompt_version=prompt_version,
                    words_json=assessment.words_json,
                )
                break
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Assessor attempt %d/%d failed for assessment %s: %s",
                    attempt,
                    max_retries,
                    assessment_id,
                    exc,
                )

        if not assessor_output:
            assessment.status = "needs_attention"
            assessment.last_error = f"Error analysis failed after {max_retries} attempts: {last_exception}"
            await audit_service.log_event(
                db=db,
                action="assessment_analysis_failed",
                record_type="assessment",
                record_id=str(assessment.assessment_id),
                outcome="failure",
            )
            await db.commit()
            raise ValueError(assessment.last_error)

        # 3. Non-LLM Post-Validation Layer
        validated_items = post_validator.validate_and_align_annotations(
            transcript=assessment.transcript,
            annotations=assessor_output.annotations,
            words_json=assessment.words_json,
        )

        # 4. Store raw LLM output in private object storage
        raw_storage_key = f"analysis/raw/{assessment.assessment_id}.json"
        storage_provider.upload_file(
            key=raw_storage_key,
            data=assessor_output.raw_response.encode("utf-8"),
            content_type="application/json",
        )

        # 5. Persist Annotations with Auto-Routing to Review Queue
        annotations_created: list[ErrorAnnotation] = []

        for ann in validated_items:
            # Auto-routing conditions:
            # 1. Confidence < threshold (default 0.85)
            # 2. Non-candidate flag (uncertain, transcription_related, acceptable_variation)
            # 3. Category is OTH
            # 4. Protocol review_all_mode enabled
            needs_review = (
                ann.confidence < settings.ANNOTATION_CONFIDENCE_THRESHOLD
                or ann.flag != "candidate_error"
                or ann.category_code == "OTH"
                or settings.REVIEW_ALL_MODE
            )

            ai_status = "needs_human_review" if needs_review else "candidate"

            start_ms = int(ann.time_start * 1000) if ann.time_start is not None else None
            end_ms = int(ann.time_end * 1000) if ann.time_end is not None else None

            annotation = ErrorAnnotation(
                annotation_id=uuid.uuid4(),
                assessment_id=assessment.assessment_id,
                start_char=ann.char_start,
                end_char=ann.char_end,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                candidate_error=ann.span_text,
                suggested_correction=ann.proposed_correction,
                category_code=ann.category_code,
                explanation=ann.explanation,
                confidence=ann.confidence,
                ai_status=ai_status,
                flag=ann.flag,
                rubric_version=rubric_version,
                prompt_version=prompt_version,
                model_version=assessor_output.model_version,
                raw_model_output_ref=raw_storage_key,
            )
            db.add(annotation)
            annotations_created.append(annotation)

        # 6. Update assessment state
        assessment.status = "analyzed"
        assessment.prompt_version = prompt_version
        assessment.model_version = assessor_output.model_version
        assessment.model_notes = assessor_output.model_notes
        assessment.is_visible_to_participant = settings.PARTICIPANT_VISIBILITY_DEFAULT

        await audit_service.log_event(
            db=db,
            action="assessment_analyzed",
            record_type="assessment",
            record_id=str(assessment.assessment_id),
            outcome="success",
        )

        await db.commit()
        for a in annotations_created:
            await db.refresh(a)

        logger.info(
            "Completed error analysis for assessment %s: %d candidate annotations created.",
            assessment_id,
            len(annotations_created),
        )
        return annotations_created

    async def release_results(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        researcher: User,
    ) -> Assessment:
        """Release analyzed assessment results for participant viewing."""
        stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
        assessment = (await db.execute(stmt)).scalar_one_or_none()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found.")

        assessment.is_visible_to_participant = True

        await audit_service.log_event(
            db=db,
            action="assessment_results_released",
            record_type="assessment",
            record_id=str(assessment.assessment_id),
            outcome="success",
            actor_id=researcher.id,
        )

        await db.commit()
        await db.refresh(assessment)
        return assessment


error_analysis_service = ErrorAnalysisService()
