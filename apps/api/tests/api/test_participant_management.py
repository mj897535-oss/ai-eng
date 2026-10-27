"""Participant Management and Duplicate Rejection Test Suite.

NON-NEGOTIABLE RULE 1 & 2:
- Unique pseudonymous participant_id generator (e.g. SL-2026-0001 style).
- Duplicate IDs rejected with a clear message.
- Researchers can view, deactivate, and assign study group.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import create_auth_headers_for


@pytest.mark.asyncio
async def test_create_participant_auto_generates_sequential_code(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Omitting research_code must auto-generate next sequential pseudonymous code."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])

    payload = {
        "study_group": "intervention",
        "mother_tongue": "Kannada",
        "school_medium": "English",
        "country": "India",
    }
    response = await client.post(
        f"{settings.API_PREFIX}/admin/participants",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()
    assert "participant_id" in data
    assert data["research_code"].startswith(settings.RESEARCH_CODE_PREFIX)
    assert data["study_group"] == "intervention"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_duplicate_participant_id_rejected_with_clear_message(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Submitting an already registered research_code must return 409 Conflict with descriptive reason."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])
    existing_code = seeded_data["participant_a"].research_code

    payload = {
        "research_code": existing_code,
        "study_group": "control",
        "mother_tongue": "Hindi",
        "school_medium": "English",
    }
    response = await client.post(
        f"{settings.API_PREFIX}/admin/participants",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 409
    error_msg = response.json()["message"]
    assert f"Participant ID '{existing_code}' is already registered in this study." in error_msg


@pytest.mark.asyncio
async def test_researcher_can_filter_and_list_participants(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Researcher can search and filter participants by study group and active status."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])

    response = await client.get(
        f"{settings.API_PREFIX}/admin/participants?study_group=intervention",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["study_group"] == "intervention"


@pytest.mark.asyncio
async def test_deactivate_and_reactivate_participant(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Researcher can deactivate and reactivate a participant record."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])
    part_id = seeded_data["participant_a"].participant_id

    # 1. Deactivate
    resp_deact = await client.patch(
        f"{settings.API_PREFIX}/admin/participants/{part_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert resp_deact.status_code == 200
    assert resp_deact.json()["is_active"] is False

    # 2. Reactivate
    resp_act = await client.patch(
        f"{settings.API_PREFIX}/admin/participants/{part_id}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert resp_act.status_code == 200
    assert resp_act.json()["is_active"] is True


@pytest.mark.asyncio
async def test_assign_study_group_by_researcher(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Researcher can change participant's study group allocation."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])
    part_id = seeded_data["participant_b"].participant_id

    response = await client.patch(
        f"{settings.API_PREFIX}/admin/participants/{part_id}/group",
        headers=admin_headers,
        json={"study_group": "intervention"},
    )
    assert response.status_code == 200
    assert response.json()["study_group"] == "intervention"


@pytest.mark.asyncio
async def test_participant_cannot_access_researcher_participant_endpoints(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Participants attempting to call researcher admin endpoints receive 403 Forbidden."""
    part_headers = await create_auth_headers_for(seeded_data["user_a"], seeded_data["participant_a"])

    response = await client.get(
        f"{settings.API_PREFIX}/admin/participants",
        headers=part_headers,
    )
    assert response.status_code == 403
