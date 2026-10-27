"""Consent Gating and Audio Access Authorization Tests.

NON-NEGOTIABLE RULE 3:
Participants must read and agree to the current consent document before ANY recording is possible.
The API must refuse audio endpoints without valid current consent.
Consent withdrawal halts all further collection.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import create_auth_headers_for


@pytest.mark.asyncio
async def test_audio_endpoint_blocks_participant_without_consent(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Participant with no recorded consent must receive 403 Forbidden on audio access."""
    user = seeded_data["user_b"]
    participant = seeded_data["participant_b"]
    assessment = seeded_data["assessment_b"]

    # Ensure participant has no consent version recorded
    participant.current_consent_version = None
    participant.is_withdrawn = False

    headers = await create_auth_headers_for(user, participant)
    response = await client.get(
        f"{settings.API_PREFIX}/assessments/{assessment.assessment_id}/audio",
        headers=headers,
    )

    assert response.status_code == 403
    assert "Consent required" in response.json()["message"] or "consent" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_audio_endpoint_blocks_participant_with_outdated_consent_version(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Participant with outdated consent version (e.g. v0.9-draft) must receive 403 Forbidden."""
    user = seeded_data["user_b"]
    participant = seeded_data["participant_b"]
    assessment = seeded_data["assessment_b"]

    # Outdated consent version
    participant.current_consent_version = "v0.9-pilot-expired"
    participant.is_withdrawn = False

    headers = await create_auth_headers_for(user, participant)
    response = await client.get(
        f"{settings.API_PREFIX}/assessments/{assessment.assessment_id}/audio",
        headers=headers,
    )

    assert response.status_code == 403
    assert "Consent required" in response.json()["message"] or settings.CURRENT_CONSENT_VERSION in response.json()["message"]


@pytest.mark.asyncio
async def test_audio_endpoint_allows_participant_with_current_active_consent(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Participant with valid current consent version must successfully access audio URL."""
    user = seeded_data["user_a"]
    participant = seeded_data["participant_a"]
    assessment = seeded_data["assessment_a"]

    # Active consent
    participant.current_consent_version = settings.CURRENT_CONSENT_VERSION
    participant.is_withdrawn = False
    participant.is_active = True

    headers = await create_auth_headers_for(user, participant)
    response = await client.get(
        f"{settings.API_PREFIX}/assessments/{assessment.assessment_id}/audio",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["assessment_id"] == str(assessment.assessment_id)
    assert "presigned_url" in data
    assert data["audio_key"] == assessment.audio_key


@pytest.mark.asyncio
async def test_audio_endpoint_blocks_withdrawn_participant(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Participant who has withdrawn consent must receive 403 Forbidden on audio access."""
    user = seeded_data["user_a"]
    participant = seeded_data["participant_a"]
    assessment = seeded_data["assessment_a"]

    # Flag as withdrawn
    participant.current_consent_version = settings.CURRENT_CONSENT_VERSION
    participant.is_withdrawn = True

    headers = await create_auth_headers_for(user, participant)
    response = await client.get(
        f"{settings.API_PREFIX}/assessments/{assessment.assessment_id}/audio",
        headers=headers,
    )

    assert response.status_code == 403
    assert "withdrawn" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_audio_endpoint_blocks_deactivated_participant(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Participant deactivated by researcher must receive 403 Forbidden on audio access."""
    user = seeded_data["user_a"]
    participant = seeded_data["participant_a"]
    assessment = seeded_data["assessment_a"]

    participant.current_consent_version = settings.CURRENT_CONSENT_VERSION
    participant.is_withdrawn = False
    participant.is_active = False

    headers = await create_auth_headers_for(user, participant)
    response = await client.get(
        f"{settings.API_PREFIX}/assessments/{assessment.assessment_id}/audio",
        headers=headers,
    )

    assert response.status_code == 403
    assert "inactive" in response.json()["message"].lower()
