"""API Tests for Research Configuration and Freezing (SRS FR-05, FR-08, FR-20).

Verifies:
- Rubric and prompt listing, creation, and freezing workflows.
- Immutability enforcement via API error responses on already-frozen records.
- Reproducible topic assignment endpoint.
- Unified diff viewer calculation.
- RBAC enforcement (participants/reviewers cannot create or freeze research config).
"""

import pytest
from httpx import AsyncClient

from apps.api.tests.conftest import TEST_PASSWORD, create_auth_headers_for


@pytest.mark.asyncio
async def test_admin_list_rubrics_and_baseline_exists(client: AsyncClient, seeded_data: dict) -> None:
    """Verify admin can list rubrics and baseline frozen rubric is present."""
    admin = seeded_data["admin"]
    headers = await create_auth_headers_for(admin)

    res = await client.get("/api/v1/admin/config/rubrics", headers=headers)
    assert res.status_code == 200
    rubrics = res.json()
    assert len(rubrics) >= 1

    baseline = next((r for r in rubrics if r["version_code"] == "v1.0-jam-phd"), None)
    assert baseline is not None
    assert baseline["is_frozen"] is True
    assert baseline["status"] == "frozen"
    assert baseline["category_count"] == 8


@pytest.mark.asyncio
async def test_admin_rubric_detail_and_categories(client: AsyncClient, seeded_data: dict) -> None:
    """Verify getting full rubric details returns definitions and counting rules."""
    admin = seeded_data["admin"]
    headers = await create_auth_headers_for(admin)

    res = await client.get("/api/v1/admin/config/rubrics/v1.0-jam-phd", headers=headers)
    assert res.status_code == 200
    detail = res.json()
    assert detail["version_code"] == "v1.0-jam-phd"
    assert "counting_rules" in detail
    assert "word_counting_rules" in detail
    assert len(detail["categories"]) == 8

    # Verify categories taxonomy
    codes = [c["code"] for c in detail["categories"]]
    for expected in ["TNS", "SVA", "WO", "AUX", "ART", "PREP", "PRO", "OTH"]:
        assert expected in codes


@pytest.mark.asyncio
async def test_rubric_draft_and_freeze_lifecycle(client: AsyncClient, seeded_data: dict) -> None:
    """Verify creating a draft rubric and subsequently freezing it."""
    admin = seeded_data["admin"]
    headers = await create_auth_headers_for(admin)

    payload = {
        "version_code": "v2.0-draft-test",
        "name": "Phase 2 Experimental Rubric",
        "description": "Expanded taxonomy for advanced clauses.",
        "categories": [
            {
                "code": "REL",
                "name": "Relative Clause Misattachment",
                "definition": "Ambiguous or ungrammatical relative clause attachment.",
                "assessable_criteria": "Sentence boundaries violated.",
                "variation_rules": "Contact clauses allowed.",
                "examples": [{"phrase": "The car that he drove it", "correction": "The car that he drove"}],
                "is_expanded": True,
            }
        ],
        "counting_rules": "Count up to 3 errors per complex clause.",
        "word_counting_rules": "Include contracted auxiliaries.",
        "change_notes": "Added REL category.",
    }

    # 1. Create draft
    create_res = await client.post("/api/v1/admin/config/rubrics", json=payload, headers=headers)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["version_code"] == "v2.0-draft-test"
    assert created["status"] == "draft"
    assert created["is_frozen"] is False

    # 2. Freeze rubric
    freeze_res = await client.post("/api/v1/admin/config/rubrics/v2.0-draft-test/freeze", headers=headers)
    assert freeze_res.status_code == 200
    frozen = freeze_res.json()
    assert frozen["status"] == "frozen"
    assert frozen["is_frozen"] is True
    assert frozen["frozen_at"] is not None

    # 3. Attempting to freeze again fails
    refreeze_res = await client.post("/api/v1/admin/config/rubrics/v2.0-draft-test/freeze", headers=headers)
    assert refreeze_res.status_code == 400


@pytest.mark.asyncio
async def test_prompt_versions_for_three_roles(client: AsyncClient, seeded_data: dict) -> None:
    """Verify prompts exist for all three AI roles: pre-test assessor, tutor, post-test assessor."""
    admin = seeded_data["admin"]
    headers = await create_auth_headers_for(admin)

    res = await client.get("/api/v1/admin/config/prompts", headers=headers)
    assert res.status_code == 200
    prompts = res.json()

    roles = {p["prompt_role"] for p in prompts}
    assert "pre_test_assessor" in roles
    assert "tutor" in roles
    assert "post_test_assessor" in roles


@pytest.mark.asyncio
async def test_reproducible_topic_assignment_endpoint(client: AsyncClient, seeded_data: dict) -> None:
    """Verify /admin/config/tasks/assign endpoint reproducibly assigns equivalent pre/post tasks."""
    admin = seeded_data["admin"]
    headers = await create_auth_headers_for(admin)

    res1 = await client.get("/api/v1/admin/config/tasks/assign?participant_id=SL-2026-TEST&seed=99", headers=headers)
    assert res1.status_code == 200
    d1 = res1.json()

    res2 = await client.get("/api/v1/admin/config/tasks/assign?participant_id=SL-2026-TEST&seed=99", headers=headers)
    assert res2.status_code == 200
    d2 = res2.json()

    assert d1["equivalence_group"] == d2["equivalence_group"]
    assert d1["pre_task"]["task_id"] == d2["pre_task"]["task_id"]
    assert d1["post_task"]["task_id"] == d2["post_task"]["task_id"]


@pytest.mark.asyncio
async def test_diff_viewer_endpoint(client: AsyncClient, seeded_data: dict) -> None:
    """Verify unified diff calculation between two versions."""
    admin = seeded_data["admin"]
    headers = await create_auth_headers_for(admin)

    # Create a draft prompt to compare against v1.0-pre-assessor
    p_payload = {
        "prompt_role": "pre_test_assessor",
        "version_code": "v1.1-pre-experimental",
        "name": "Experimental Pre-Assessor",
        "prompt_template": "Role: Neutral spoken-English syntax assessor with strict clause boundaries.\nTranscribe faithfully.",
        "output_schema_version": "json-schema-v1.1",
        "output_schema_json": '{"type": "object", "properties": {"deviations": {"type": "array"}}}',
        "change_notes": "Added strict clause boundaries.",
    }
    await client.post("/api/v1/admin/config/prompts", json=p_payload, headers=headers)

    diff_res = await client.get(
        "/api/v1/admin/config/diff?type=prompt&base_code=v1.0-pre-assessor&target_code=v1.1-pre-experimental",
        headers=headers,
    )
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert diff_data["has_changes"] is True
    assert diff_data["additions"] > 0
    assert diff_data["deletions"] > 0
    assert len(diff_data["lines"]) > 0


@pytest.mark.asyncio
async def test_participant_forbidden_from_config_endpoints(client: AsyncClient, seeded_data: dict) -> None:
    """Verify participants cannot create or freeze research rubrics or prompts."""
    user_a = seeded_data["user_a"]
    p_a = seeded_data["participant_a"]
    headers = await create_auth_headers_for(user_a, p_a)

    res = await client.post(
        "/api/v1/admin/config/rubrics",
        json={"version_code": "hacked", "name": "hacked", "categories": [], "counting_rules": "", "word_counting_rules": ""},
        headers=headers,
    )
    assert res.status_code == 403
