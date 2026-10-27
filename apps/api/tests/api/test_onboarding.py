"""Participant Onboarding Wizard Test Suite.

NON-NEGOTIABLE RULE 6:
- Resumable onboarding: consent -> profile -> mic check -> orientation.
- Mobile-first, friendly plain language.
- Config-driven demographic validation (age vs age band).
"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import create_auth_headers_for


@pytest.mark.asyncio
async def test_onboarding_state_progression(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Participant can fetch onboarding state, submit profile, and advance steps."""
    user = seeded_data["user_b"]
    participant = seeded_data["participant_b"]
    participant.onboarding_completed = False
    participant.onboarding_step = "consent"

    headers = await create_auth_headers_for(user, participant)

    # 1. Fetch initial state
    res_state = await client.get(f"{settings.API_PREFIX}/onboarding/state", headers=headers)
    assert res_state.status_code == 200
    state_data = res_state.json()
    assert state_data["research_code"] == participant.research_code
    assert state_data["onboarding_completed"] is False
    assert "config" in state_data

    # 2. Submit demographic profile
    profile_payload = {
        "age_band": "21-24",
        "mother_tongue": "Marathi",
        "school_medium": "English",
        "country": "India",
        "state": "Maharashtra",
        "city": "Pune",
    }
    res_prof = await client.post(
        f"{settings.API_PREFIX}/onboarding/profile",
        headers=headers,
        json=profile_payload,
    )
    assert res_prof.status_code == 200
    assert res_prof.json()["next_step"] == "mic_check"

    # 3. Complete mic check step
    res_mic = await client.post(
        f"{settings.API_PREFIX}/onboarding/complete-step",
        headers=headers,
        json={"step": "mic_check"},
    )
    assert res_mic.status_code == 200
    assert res_mic.json()["current_step"] == "what_next"

    # 4. Complete final orientation step
    res_finish = await client.post(
        f"{settings.API_PREFIX}/onboarding/complete-step",
        headers=headers,
        json={"step": "completed"},
    )
    assert res_finish.status_code == 200
    assert res_finish.json()["onboarding_completed"] is True
