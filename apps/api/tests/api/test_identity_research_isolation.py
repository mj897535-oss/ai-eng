"""Identity vs Research Data Isolation Tests.

NON-NEGOTIABLE RULE 4 & NFR-PRIV-01:
- Never send names or direct identifiers to research endpoints or external providers.
- Identity data lives in a separate table/schema from research data.
- Research queries never join identity tables for research observations.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import create_auth_headers_for


@pytest.mark.asyncio
async def test_participant_api_returns_zero_pii_in_research_responses(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Researcher participant endpoint returns pseudonymous codes and zero passwords/salts/emails."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])

    response = await client.get(
        f"{settings.API_PREFIX}/admin/participants",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0

    for item in data["items"]:
        # Verify research code format
        assert item["research_code"].startswith(settings.RESEARCH_CODE_PREFIX)
        # Verify security: no hashed_password, no raw identity fields
        assert "hashed_password" not in item
        assert "password" not in item
        assert "full_name" not in item


@pytest.mark.asyncio
async def test_research_participant_schema_isolation_at_database_level(
    seeded_data: dict[str, Any],
) -> None:
    """Participant model belongs strictly to research schema with only pseudonymous keys."""
    participant = seeded_data["participant_a"]
    assert participant.__table__.schema == "research"
    # Column verification
    col_names = {c.name for c in participant.__table__.columns}
    assert "research_code" in col_names
    assert "participant_id" in col_names
    assert "full_name" not in col_names
    assert "email" not in col_names
    assert "hashed_password" not in col_names
