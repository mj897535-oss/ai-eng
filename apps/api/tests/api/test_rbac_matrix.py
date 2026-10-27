"""Object-Level Authorisation Matrix Test Suite.

NON-NEGOTIABLE RULES:
- Participant A cannot fetch Participant B's data via any endpoint.
- Reviewers cannot access unassigned assessment records.
- Parametrised matrix enumerating all endpoints across all security roles.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import create_auth_headers_for

# Define the comprehensive authorization matrix
# (endpoint_key, actor_role, expected_status, description)
AUTHORIZATION_MATRIX = [
    # --- Participant Profile Access (GET /participants/{id}) ---
    ("participant_b", "unauthenticated", 401, "Unauthenticated user cannot view participant B"),
    ("participant_b", "participant_a", 403, "Participant A CANNOT view Participant B's profile"),
    ("participant_b", "participant_b", 200, "Participant B CAN view own profile"),
    ("participant_b", "reviewer_1", 403, "Reviewer CANNOT view participant demographic profile"),
    ("participant_b", "reviewer_2", 403, "Reviewer CANNOT view participant demographic profile"),
    ("participant_b", "researcher_admin", 200, "Lead Researcher CAN view participant B profile"),

    # --- Assessment B1 Access (GET /assessments/{id}) ---
    ("assessment_b", "unauthenticated", 401, "Unauthenticated user cannot view assessment B"),
    ("assessment_b", "participant_a", 403, "Participant A CANNOT view Participant B's assessment"),
    ("assessment_b", "participant_b", 200, "Participant B CAN view own assessment B"),
    ("assessment_b", "reviewer_1", 403, "Reviewer 1 CANNOT view unassigned assessment B"),
    ("assessment_b", "reviewer_2", 403, "Reviewer 2 CANNOT view unassigned assessment B"),
    ("assessment_b", "researcher_admin", 200, "Lead Researcher CAN view assessment B"),

    # --- Assessment A1 Access (Assigned to Reviewer 1) ---
    ("assessment_a", "unauthenticated", 401, "Unauthenticated user cannot view assessment A"),
    ("assessment_a", "participant_a", 200, "Participant A CAN view own assessment A"),
    ("assessment_a", "participant_b", 403, "Participant B CANNOT view Participant A's assessment"),
    ("assessment_a", "reviewer_1", 200, "Reviewer 1 CAN view explicitly assigned assessment A"),
    ("assessment_a", "reviewer_2", 403, "Reviewer 2 CANNOT view unassigned assessment A"),
    ("assessment_a", "researcher_admin", 200, "Lead Researcher CAN view assessment A"),

    # --- Recording Audio Access (GET /assessments/{id}/audio) ---
    ("audio_a", "unauthenticated", 401, "Unauthenticated user cannot access audio A"),
    ("audio_a", "participant_a", 200, "Participant A CAN access own audio A"),
    ("audio_a", "participant_b", 403, "Participant B CANNOT access Participant A's audio"),
    ("audio_a", "reviewer_1", 200, "Assigned Reviewer 1 CAN access audio A"),
    ("audio_a", "reviewer_2", 403, "Unassigned Reviewer 2 CANNOT access audio A"),
    ("audio_a", "researcher_admin", 200, "Lead Researcher CAN access audio A"),

    # --- Admin Users Management (GET /admin/users) ---
    ("admin_users", "unauthenticated", 401, "Unauthenticated user cannot access admin users list"),
    ("admin_users", "participant_a", 403, "Participant CANNOT access admin users list"),
    ("admin_users", "reviewer_1", 403, "Reviewer CANNOT access admin users list"),
    ("admin_users", "researcher_admin", 200, "Lead Researcher CAN access admin users list"),

    # --- Admin Audit Log Access (GET /admin/audit-logs) ---
    ("admin_audit", "unauthenticated", 401, "Unauthenticated user cannot access research audit logs"),
    ("admin_audit", "participant_a", 403, "Participant CANNOT access research audit logs"),
    ("admin_audit", "reviewer_1", 403, "Reviewer CANNOT access research audit logs"),
    ("admin_audit", "researcher_admin", 200, "Lead Researcher CAN access research audit logs"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("resource_key,actor_key,expected_status,description", AUTHORIZATION_MATRIX)
async def test_authorization_matrix(
    client: AsyncClient,
    seeded_data: dict[str, Any],
    resource_key: str,
    actor_key: str,
    expected_status: int,
    description: str,
) -> None:
    """Parametrised test executing the object-level authorisation matrix."""
    # 1. Resolve endpoint path
    if resource_key == "participant_b":
        part_id = seeded_data["participant_b"].participant_id
        path = f"{settings.API_PREFIX}/participants/{part_id}"
    elif resource_key == "assessment_b":
        ass_id = seeded_data["assessment_b"].assessment_id
        path = f"{settings.API_PREFIX}/assessments/{ass_id}"
    elif resource_key == "assessment_a":
        ass_id = seeded_data["assessment_a"].assessment_id
        path = f"{settings.API_PREFIX}/assessments/{ass_id}"
    elif resource_key == "audio_a":
        ass_id = seeded_data["assessment_a"].assessment_id
        path = f"{settings.API_PREFIX}/assessments/{ass_id}/audio"
    elif resource_key == "admin_users":
        path = f"{settings.API_PREFIX}/admin/users"
    elif resource_key == "admin_audit":
        path = f"{settings.API_PREFIX}/admin/audit-logs"
    else:
        raise ValueError(f"Unknown resource key: {resource_key}")

    # 2. Resolve actor headers
    headers: dict[str, str] = {}
    if actor_key == "unauthenticated":
        headers = {}
    elif actor_key == "participant_a":
        headers = await create_auth_headers_for(seeded_data["user_a"], seeded_data["participant_a"])
    elif actor_key == "participant_b":
        headers = await create_auth_headers_for(seeded_data["user_b"], seeded_data["participant_b"])
    elif actor_key == "reviewer_1":
        headers = await create_auth_headers_for(seeded_data["rev_1"])
    elif actor_key == "reviewer_2":
        headers = await create_auth_headers_for(seeded_data["rev_2"])
    elif actor_key == "researcher_admin":
        headers = await create_auth_headers_for(seeded_data["admin"])
    else:
        raise ValueError(f"Unknown actor key: {actor_key}")

    # 3. Execute request
    response = await client.get(path, headers=headers)

    # 4. Assert expected status
    assert response.status_code == expected_status, (
        f"Failed assertion: {description}. "
        f"Path: {path}, Actor: {actor_key}. "
        f"Expected {expected_status}, got {response.status_code}. Response: {response.text}"
    )
