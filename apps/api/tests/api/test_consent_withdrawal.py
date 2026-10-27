"""Consent Agreement, Withdrawal Workflow, and Append-Only Immutability Tests.

NON-NEGOTIABLE RULE 3:
- Original consents are APPEND-ONLY.
- Database triggers prohibit UPDATE and DELETE.
- Withdrawal halts all further data collection.
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, update
from sqlalchemy.exc import DatabaseError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.consent import Consent, ConsentStatus
from tests.conftest import create_auth_headers_for


@pytest.mark.asyncio
async def test_get_current_consent_document(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Participants can fetch the current versioned consent document and withdrawal terms."""
    headers = await create_auth_headers_for(seeded_data["user_a"], seeded_data["participant_a"])

    response = await client.get(f"{settings.API_PREFIX}/consent/current", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == settings.CURRENT_CONSENT_VERSION
    assert "Informed Consent" in data["title"]
    assert "Right to Withdraw" in data["withdrawal_policy"]
    assert "already_consented" in data


@pytest.mark.asyncio
async def test_participant_consent_agreement_flow(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Agreeing to consent writes an append-only row and updates participant state."""
    user = seeded_data["user_b"]
    participant = seeded_data["participant_b"]
    participant.current_consent_version = None
    participant.is_withdrawn = False

    headers = await create_auth_headers_for(user, participant)
    payload = {"consent_version": settings.CURRENT_CONSENT_VERSION}

    response = await client.post(
        f"{settings.API_PREFIX}/consent/agree",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "consented"
    assert data["consent_version"] == settings.CURRENT_CONSENT_VERSION
    assert "consent_id" in data


@pytest.mark.asyncio
async def test_participant_consent_withdrawal_flow(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Withdrawing consent creates an immutable row, halts collection, and blocks audio."""
    user = seeded_data["user_a"]
    participant = seeded_data["participant_a"]
    participant.current_consent_version = settings.CURRENT_CONSENT_VERSION
    participant.is_withdrawn = False

    headers = await create_auth_headers_for(user, participant)
    payload = {"reason": "Personal time constraints"}

    # 1. Execute withdrawal
    response = await client.post(
        f"{settings.API_PREFIX}/consent/withdraw",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "withdrawn"
    assert data["is_withdrawn"] is True

    # 2. Verify subsequent audio access is rejected
    ass_id = seeded_data["assessment_a"].assessment_id
    audio_resp = await client.get(
        f"{settings.API_PREFIX}/assessments/{ass_id}/audio",
        headers=headers,
    )
    assert audio_resp.status_code == 403
    assert "withdrawn" in audio_resp.json()["message"].lower()

    # 3. Verify attempting to agree again is rejected
    agree_resp = await client.post(
        f"{settings.API_PREFIX}/consent/agree",
        headers=headers,
        json={"consent_version": settings.CURRENT_CONSENT_VERSION},
    )
    assert agree_resp.status_code == 400


@pytest.mark.asyncio
async def test_consent_records_are_strictly_append_only(
    test_session: AsyncSession,
    seeded_data: dict[str, Any],
) -> None:
    """Updating or deleting any consent row must trigger a database integrity exception."""
    part_id = seeded_data["participant_a"].participant_id

    entry = Consent(
        participant_id=part_id,
        consent_version=settings.CURRENT_CONSENT_VERSION,
        status=ConsentStatus.CONSENTED,
    )
    test_session.add(entry)
    await test_session.commit()
    entry_id = entry.consent_id

    # Attempt UPDATE
    update_stmt = update(Consent).where(Consent.consent_id == entry_id).values(status=ConsentStatus.WITHDRAWN)
    with pytest.raises((OperationalError, DatabaseError)) as exc_update:
        await test_session.execute(update_stmt)
        await test_session.commit()

    await test_session.rollback()
    assert "RESEARCH INTEGRITY VIOLATION" in str(exc_update.value) or "append-only" in str(exc_update.value).lower()

    # Attempt DELETE
    delete_stmt = delete(Consent).where(Consent.consent_id == entry_id)
    with pytest.raises((OperationalError, DatabaseError)) as exc_delete:
        await test_session.execute(delete_stmt)
        await test_session.commit()

    await test_session.rollback()
    assert "RESEARCH INTEGRITY VIOLATION" in str(exc_delete.value) or "append-only" in str(exc_delete.value).lower()
