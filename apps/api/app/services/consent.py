"""Consent Management and Right to Withdraw Service.

NON-NEGOTIABLE RESEARCH INTEGRITY RULES:
- Consent records are strictly APPEND-ONLY.
- Database triggers reject UPDATE and DELETE queries on research.consents.
- Consent must be active before any audio recording is permitted.
- Withdrawal halts all further data collection and tags records accordingly.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.consent import Consent, ConsentStatus
from app.models.research import Participant
from app.services.audit import audit_service


class ConsentService:
    def get_current_consent_metadata(
        self,
        participant: Participant | None = None,
    ) -> dict[str, Any]:
        """Return the current frozen research consent document metadata."""
        is_consented = False
        consented_version = None
        is_withdrawn = False

        if participant:
            is_withdrawn = participant.is_withdrawn
            consented_version = participant.current_consent_version
            if (
                consented_version == settings.CURRENT_CONSENT_VERSION
                and not is_withdrawn
            ):
                is_consented = True

        return {
            "version": settings.CURRENT_CONSENT_VERSION,
            "effective_date": settings.CONSENT_EFFECTIVE_DATE,
            "title": settings.CONSENT_DOCUMENT_TITLE,
            "text": settings.CONSENT_DOCUMENT_TEXT,
            "withdrawal_policy": settings.WITHDRAWAL_POLICY_TEXT,
            "already_consented": is_consented,
            "consented_version": consented_version,
            "is_withdrawn": is_withdrawn,
        }

    async def agree_to_consent(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
        version: str,
        actor_id: uuid.UUID | None = None,
        actor_role: str = "participant",
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> Consent:
        """Record participant agreement to the research consent document.

        Append-only row in research.consents + updates participant profile state.
        """
        stmt = select(Participant).where(Participant.participant_id == participant_id)
        participant = (await db.execute(stmt)).scalar_one_or_none()
        if not participant:
            raise ValueError(f"Participant {participant_id} not found.")

        if participant.is_withdrawn:
            raise ValueError("Participant has withdrawn consent from this study.")

        now = datetime.now(UTC)

        # 1. Append-only Consent record
        consent_record = Consent(
            consent_id=uuid.uuid4(),
            participant_id=participant_id,
            consent_version=version,
            status=ConsentStatus.CONSENTED,
            ip_hash=ip_hash,
            user_agent=user_agent,
            created_at=now,
        )
        db.add(consent_record)

        # 2. Update participant active consent status
        participant.current_consent_version = version
        participant.consented_at = now
        if participant.onboarding_step == "consent":
            participant.onboarding_step = "profile"

        await db.flush()

        # 3. Append-only Audit Trail
        await audit_service.log_event(
            db=db,
            action="consent_agreed",
            actor_id=actor_id,
            role=actor_role,
            record_type="participant",
            record_id=str(participant_id),
            outcome="success",
            ip_hash=ip_hash,
            user_agent=user_agent,
            details={
                "consent_version": version,
                "research_code": participant.research_code,
            },
        )

        return consent_record

    async def withdraw_consent(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
        reason: str | None = None,
        actor_id: uuid.UUID | None = None,
        actor_role: str = "participant",
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> Consent:
        """Execute protocol-defined consent withdrawal workflow.

        - Creates immutable append-only record with status=WITHDRAWN.
        - Sets is_withdrawn=True and records withdrawal timestamp and reason.
        - Blocks any further audio or assessment data collection.
        """
        stmt = select(Participant).where(Participant.participant_id == participant_id)
        participant = (await db.execute(stmt)).scalar_one_or_none()
        if not participant:
            raise ValueError(f"Participant {participant_id} not found.")

        if participant.is_withdrawn:
            raise ValueError("Consent has already been withdrawn.")

        now = datetime.now(UTC)

        # 1. Append-only Consent record
        consent_record = Consent(
            consent_id=uuid.uuid4(),
            participant_id=participant_id,
            consent_version=participant.current_consent_version or settings.CURRENT_CONSENT_VERSION,
            status=ConsentStatus.WITHDRAWN,
            ip_hash=ip_hash,
            user_agent=user_agent,
            created_at=now,
        )
        db.add(consent_record)

        # 2. Update participant withdrawal state
        participant.is_withdrawn = True
        participant.withdrawn_at = now
        participant.withdrawal_reason = reason
        participant.is_active = False

        await db.flush()

        # 3. Append-only Audit Trail
        await audit_service.log_event(
            db=db,
            action="consent_withdrawn",
            actor_id=actor_id,
            role=actor_role,
            record_type="participant",
            record_id=str(participant_id),
            outcome="success",
            ip_hash=ip_hash,
            user_agent=user_agent,
            details={
                "reason": reason,
                "research_code": participant.research_code,
            },
        )

        return consent_record

    async def get_participant_consent_history(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
    ) -> list[Consent]:
        stmt = (
            select(Consent)
            .where(Consent.participant_id == participant_id)
            .order_by(Consent.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


consent_service = ConsentService()
