"""CSV Bulk Import and Dry-Run Preview Test Suite.

NON-NEGOTIABLE RULE 1 & 2:
- Bulk CSV import with a dry-run preview (valid rows, rejected rows with reasons, duplicates).
- Duplicate IDs rejected cleanly.
- Strict data validation before committing.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import create_auth_headers_for


@pytest.mark.asyncio
async def test_csv_import_dry_run_with_valid_rows(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Dry run on clean CSV reports all valid rows and does not mutate database."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])

    csv_content = """research_code,study_group,email,age,mother_tongue,school_medium
SL-2026-9001,intervention,batch_p1@syntaxlens.edu,21,Marathi,English
SL-2026-9002,control,batch_p2@syntaxlens.edu,22,Hindi,English
"""
    response = await client.post(
        f"{settings.API_PREFIX}/admin/participants/import?dry_run=true",
        headers=admin_headers,
        json={"csv_content": csv_content},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True
    assert data["total_rows"] == 2
    assert data["valid_count"] == 2
    assert data["rejected_count"] == 0
    assert data["can_commit"] is True

    # Verify database was NOT mutated
    check_resp = await client.get(
        f"{settings.API_PREFIX}/admin/participants?search=SL-2026-9001",
        headers=admin_headers,
    )
    assert check_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_csv_import_detects_batch_and_db_duplicates(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Dry run detects collisions against DB records and within the CSV itself."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])
    existing_code = seeded_data["participant_a"].research_code

    csv_content = f"""research_code,study_group,email
{existing_code},intervention,p_dup_db@syntaxlens.edu
SL-2026-9010,control,p_new_1@syntaxlens.edu
SL-2026-9010,intervention,p_dup_file@syntaxlens.edu
"""
    response = await client.post(
        f"{settings.API_PREFIX}/admin/participants/import?dry_run=true",
        headers=admin_headers,
        json={"csv_content": csv_content},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True
    assert data["valid_count"] == 1
    assert data["rejected_count"] == 2
    assert data["duplicate_count"] == 2
    assert data["can_commit"] is False

    reasons = [r["error_reason"] for r in data["rejected_rows"]]
    assert any("already registered" in r for r in reasons)
    assert any("Duplicate participant ID within this CSV" in r for r in reasons)


@pytest.mark.asyncio
async def test_csv_import_rejects_invalid_groups_and_ages(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """Dry run rejects invalid study group names and invalid age ranges with exact reasons."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])

    csv_content = """research_code,study_group,age
SL-2026-9020,invalid_group,21
SL-2026-9021,control,5
SL-2026-9022,intervention,not_a_number
"""
    response = await client.post(
        f"{settings.API_PREFIX}/admin/participants/import?dry_run=true",
        headers=admin_headers,
        json={"csv_content": csv_content},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid_count"] == 0
    assert data["rejected_count"] == 3
    assert data["can_commit"] is False


@pytest.mark.asyncio
async def test_csv_import_commit_creates_participants_and_audit_log(
    client: AsyncClient,
    seeded_data: dict[str, Any],
) -> None:
    """When dry_run=False, valid rows are persisted and an audit log is emitted."""
    admin_headers = await create_auth_headers_for(seeded_data["admin"])

    csv_content = """research_code,study_group,email,age,mother_tongue,school_medium
SL-2026-8801,intervention,batch_c1@syntaxlens.edu,20,Telugu,English
SL-2026-8802,control,batch_c2@syntaxlens.edu,22,Tamil,English
"""
    response = await client.post(
        f"{settings.API_PREFIX}/admin/participants/import?dry_run=false",
        headers=admin_headers,
        json={"csv_content": csv_content},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is False
    assert data["valid_count"] == 2
    assert data["can_commit"] is True

    # Verify records exist in database
    p1 = await client.get(
        f"{settings.API_PREFIX}/admin/participants?search=SL-2026-8801",
        headers=admin_headers,
    )
    assert p1.json()["total"] == 1
    assert p1.json()["items"][0]["research_code"] == "SL-2026-8801"
    assert p1.json()["items"][0]["study_group"] == "intervention"
