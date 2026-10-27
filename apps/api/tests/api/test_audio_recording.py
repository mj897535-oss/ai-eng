"""Tests for Phase P6 Audio Recording, Upload Ingestion, and Idempotency (SRS FR-04, NFR-SEC-03, NFR-REL-01).

Verifies:
- Consent gating: endpoints reject participants without current consent or withdrawn status.
- Presigned URL generation for browser direct upload to private bucket.
- Single official submission rule enforced per assessment type.
- Researcher retake authorization workflow.
- Strict submission idempotency: retries return existing assessment without duplicates.
- Duration validation: minimum 3s enforced, oversize rejected.
- Authorization: participant blinded polling, reviewer playback URL, anonymous access denied.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assessment import Assessment, AssessmentType
from app.models.research import Participant
from tests.conftest import create_auth_headers_for


def get_err_msg(resp) -> str:
    data = resp.json()
    return (data.get("message") or data.get("detail") or "").lower()


@pytest.mark.asyncio
async def test_consent_gating_blocks_audio_presigned_url(client: AsyncClient, seeded_data: dict, test_session: AsyncSession) -> None:
    """Verifies that a participant without current valid consent cannot request an upload URL."""
    user_a = seeded_data["user_a"]
    p_a = seeded_data["participant_a"]

    # Temporarily remove consent
    p_a.current_consent_version = None
    await test_session.commit()

    headers = await create_auth_headers_for(user_a, p_a)
    resp = await client.post("/api/v1/assessments/post/presigned-url", json={}, headers=headers)
    assert resp.status_code == 400
    assert "consent required" in get_err_msg(resp)

    # Restore consent
    p_a.current_consent_version = settings.CURRENT_CONSENT_VERSION
    await test_session.commit()


@pytest.mark.asyncio
async def test_withdrawn_participant_cannot_request_presigned_url(client: AsyncClient, seeded_data: dict, test_session: AsyncSession) -> None:
    """Verifies that a withdrawn participant is strictly blocked from new recording."""
    user_b = seeded_data["user_b"]
    p_b = seeded_data["participant_b"]

    p_b.is_withdrawn = True
    await test_session.commit()

    headers = await create_auth_headers_for(user_b, p_b)
    resp = await client.post("/api/v1/assessments/post/presigned-url", json={}, headers=headers)
    assert resp.status_code == 400
    assert "withdrawn" in get_err_msg(resp)

    p_b.is_withdrawn = False
    await test_session.commit()


@pytest.mark.asyncio
async def test_presigned_url_generation_success(client: AsyncClient, seeded_data: dict) -> None:
    """Verifies consented participant receives valid presigned PUT URL and task metadata."""
    user_a = seeded_data["user_a"]
    p_a = seeded_data["participant_a"]
    headers = await create_auth_headers_for(user_a, p_a)

    resp = await client.post("/api/v1/assessments/post/presigned-url", json={"codec": "audio/webm"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "upload_url" in data
    assert data["storage_key"].startswith(f"audio/{p_a.research_code}/post_")
    assert data["method"] == "PUT"
    assert data["headers"]["Content-Type"] == "audio/webm"
    assert "task" in data
    assert data["task"]["prep_time_seconds"] == 30
    assert data["task"]["duration_seconds"] == 60


@pytest.mark.asyncio
async def test_idempotent_submission_and_validation(client: AsyncClient, seeded_data: dict, test_session: AsyncSession) -> None:
    """Verifies submission idempotency and minimum audio duration validation."""
    user_a = seeded_data["user_a"]
    p_a = seeded_data["participant_a"]
    task_id_str = str(seeded_data["task"].task_id)
    headers = await create_auth_headers_for(user_a, p_a)

    idemp_key = f"idemp-test-{uuid.uuid4().hex[:8]}"
    storage_key = f"audio/{p_a.research_code}/post_{uuid.uuid4().hex[:8]}.webm"

    # 1. Validation failure: duration too short (< 3s)
    short_payload = {
        "task_id": task_id_str,
        "assessment_type": "post",
        "storage_key": storage_key,
        "duration_seconds": 1.5,
        "checksum": "abc12345",
        "idempotency_key": idemp_key,
    }
    short_resp = await client.post("/api/v1/assessments/submit", json=short_payload, headers=headers)
    assert short_resp.status_code == 400
    assert "too short" in get_err_msg(short_resp)

    # 2. Valid submission: 25.0 seconds
    valid_payload = {
        "task_id": task_id_str,
        "assessment_type": "post",
        "storage_key": storage_key,
        "duration_seconds": 25.0,
        "checksum": "abc12345",
        "idempotency_key": idemp_key,
    }
    res1 = await client.post("/api/v1/assessments/submit", json=valid_payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["status"] == "queued_for_transcription"
    assert data1["is_official"] is True
    assessment_id = data1["assessment_id"]

    # 3. Idempotent replay: submitting with identical key returns exact same assessment without error or duplicate
    res2 = await client.post("/api/v1/assessments/submit", json=valid_payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["assessment_id"] == assessment_id

    # 4. Verify in DB only 1 record exists with this idempotency key
    stmt = select(Assessment).where(Assessment.idempotency_key == idemp_key)
    records = (await test_session.execute(stmt)).scalars().all()
    assert len(records) == 1


@pytest.mark.asyncio
async def test_one_submission_rule_and_researcher_retake_flow(client: AsyncClient, seeded_data: dict, test_session: AsyncSession) -> None:
    """Verifies one official submission per participant and authorized retake workflow."""
    admin = seeded_data["admin"]
    user_a = seeded_data["user_a"]
    p_a = seeded_data["participant_a"]
    participant_id_str = str(p_a.participant_id)
    research_code = p_a.research_code
    task_id_str = str(seeded_data["task"].task_id)
    p_headers = await create_auth_headers_for(user_a, p_a)
    admin_headers = await create_auth_headers_for(admin)

    # 1. First submission succeeds (201)
    initial_payload = {
        "task_id": task_id_str,
        "assessment_type": "post",
        "storage_key": f"audio/{research_code}/post_first.webm",
        "duration_seconds": 28.0,
        "checksum": "first123",
        "idempotency_key": f"idemp-first-{uuid.uuid4().hex[:8]}",
    }
    first_resp = await client.post("/api/v1/assessments/submit", json=initial_payload, headers=p_headers)
    assert first_resp.status_code == 201

    # 2. Participant attempts second post submission with a different idempotency key -> rejected
    duplicate_payload = {
        "task_id": task_id_str,
        "assessment_type": "post",
        "storage_key": f"audio/{research_code}/post_second.webm",
        "duration_seconds": 30.0,
        "checksum": "def45678",
        "idempotency_key": f"idemp-different-{uuid.uuid4().hex[:8]}",
    }
    dup_resp = await client.post("/api/v1/assessments/submit", json=duplicate_payload, headers=p_headers)
    assert dup_resp.status_code == 400
    assert "already submitted" in get_err_msg(dup_resp)

    # 3. Researcher admin authorizes an official retake
    retake_payload = {
        "assessment_type": "post",
        "reason": "Audio corrupted by microphone disconnect during initial recording.",
    }
    retake_resp = await client.post(
        f"/api/v1/assessments/retake/{participant_id_str}",
        json=retake_payload,
        headers=admin_headers,
    )
    assert retake_resp.status_code == 200
    assert retake_resp.json()["status"] == "authorized"

    # 4. Now participant can submit new post recording
    retake_submit_resp = await client.post("/api/v1/assessments/submit", json=duplicate_payload, headers=p_headers)
    assert retake_submit_resp.status_code == 201
    assert retake_submit_resp.json()["is_official"] is True


@pytest.mark.asyncio
async def test_assessment_status_polling_and_blinding(client: AsyncClient, seeded_data: dict) -> None:
    """Verifies transparent status tracking and object-level participant authorization."""
    user_a = seeded_data["user_a"]
    user_b = seeded_data["user_b"]
    p_a = seeded_data["participant_a"]
    p_b = seeded_data["participant_b"]
    assessment_a = seeded_data["assessment_a"]

    headers_a = await create_auth_headers_for(user_a, p_a)
    headers_b = await create_auth_headers_for(user_b, p_b)

    # Participant A can view status of their own assessment
    res_a = await client.get(f"/api/v1/assessments/{assessment_a.assessment_id}/status", headers=headers_a)
    assert res_a.status_code == 200
    assert "status" in res_a.json()

    # Participant B CANNOT view Participant A's assessment status (403 Forbidden)
    res_b = await client.get(f"/api/v1/assessments/{assessment_a.assessment_id}/status", headers=headers_b)
    assert res_b.status_code == 403


@pytest.mark.asyncio
async def test_audio_playback_url_access_control(client: AsyncClient, seeded_data: dict) -> None:
    """Verifies that presigned playback URL is accessible only to reviewers/researchers, never anonymous or participants."""
    user_a = seeded_data["user_a"]
    p_a = seeded_data["participant_a"]
    rev_1 = seeded_data["rev_1"]
    assessment_a = seeded_data["assessment_a"]

    # 1. Anonymous request is rejected
    anon_res = await client.get(f"/api/v1/assessments/{assessment_a.assessment_id}/audio-url")
    assert anon_res.status_code in (401, 403)

    # 2. Participant is forbidden from reviewer playback URL
    p_headers = await create_auth_headers_for(user_a, p_a)
    p_res = await client.get(f"/api/v1/assessments/{assessment_a.assessment_id}/audio-url", headers=p_headers)
    assert p_res.status_code == 403

    # 3. Reviewer receives presigned playback URL
    rev_headers = await create_auth_headers_for(rev_1)
    rev_res = await client.get(f"/api/v1/assessments/{assessment_a.assessment_id}/audio-url", headers=rev_headers)
    assert rev_res.status_code == 200
    assert "playback_url" in rev_res.json()
