"""API Integration Tests for STT Endpoints (Phase P7).

Tests:
1. POST /assessments/{id}/transcribe: trigger STT background job and fetch result.
2. GET /assessments/{id}/transcript: retrieve transcript, word timestamps, and revisions.
3. POST /assessments/{id}/revisions: reviewer adds revision with diff (participant forbidden).
4. GET /assessments/metrics/stt: researcher queries pilot kit telemetry.
5. Row-level access control: participant A cannot view participant B's transcript.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assessment import Assessment, AssessmentTask, AssessmentType
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from tests.conftest import create_auth_headers_for


@pytest.fixture
async def stt_api_seeded(test_session: AsyncSession) -> dict:
    # 1. Reviewer & Researcher
    reviewer = User(
        email=f"rev_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Dr. Reviewer",
        hashed_password="pw",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    researcher = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Chief Researcher",
        hashed_password="pw",
        role=UserRole.RESEARCHER_ADMIN,
        is_active=True,
    )
    # 2. Participant A & B
    user_a = User(
        email=f"pa_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Participant Alpha",
        hashed_password="pw",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    user_b = User(
        email=f"pb_{uuid.uuid4().hex[:6]}@syntaxlens.test",
        full_name="Participant Beta",
        hashed_password="pw",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    test_session.add_all([reviewer, researcher, user_a, user_b])
    await test_session.flush()

    p_a = Participant(
        user_id=user_a.id,
        research_code=f"SL-2026-A{uuid.uuid4().hex[:4]}",
        study_group=StudyGroup.INTERVENTION,
        is_active=True,
    )
    p_b = Participant(
        user_id=user_b.id,
        research_code=f"SL-2026-B{uuid.uuid4().hex[:4]}",
        study_group=StudyGroup.CONTROL,
        is_active=True,
    )
    task = AssessmentTask(
        title="Spoken Task 1",
        prompt_text="Describe your typical weekend.",
        duration_seconds=60,
        prep_time_seconds=30,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        is_active=True,
    )
    test_session.add_all([p_a, p_b, task])
    await test_session.commit()

    # Create an assessment for Participant A
    assessment_a = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=p_a.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key=f"audio/{p_a.research_code}/pre_001.webm",
        audio_checksum="mock_audio_hash_a",
        audio_duration_seconds=50.0,
        status="queued_for_transcription",
        stt_version=settings.DEFAULT_STT_VERSION,
        rubric_version=settings.DEFAULT_RUBRIC_VERSION,
        model_version=settings.DEFAULT_MODEL_VERSION,
    )
    test_session.add(assessment_a)
    await test_session.commit()

    return {
        "reviewer": reviewer,
        "researcher": researcher,
        "user_a": user_a,
        "user_b": user_b,
        "p_a": p_a,
        "p_b": p_b,
        "task": task,
        "assessment_a": assessment_a,
    }


@pytest.mark.asyncio
async def test_trigger_transcription_and_fetch_transcript(
    client: AsyncClient,
    stt_api_seeded: dict,
) -> None:
    """Participant triggers transcription for their recording and retrieves verbatim words."""
    user_a = stt_api_seeded["user_a"]
    p_a = stt_api_seeded["p_a"]
    assessment_a = stt_api_seeded["assessment_a"]
    headers_a = await create_auth_headers_for(user_a, p_a)

    # 1. Trigger transcription
    resp = await client.post(
        f"/api/v1/assessments/{assessment_a.assessment_id}/transcribe",
        headers=headers_a,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "transcribed"
    assert data["transcript"] is not None
    assert data["word_count"] > 0
    assert len(data["words"]) > 0
    assert data["words"][0]["word"] is not None

    # 2. Query transcript endpoint
    get_resp = await client.get(
        f"/api/v1/assessments/{assessment_a.assessment_id}/transcript",
        headers=headers_a,
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["transcript"] == data["transcript"]
    assert get_data["word_count"] == data["word_count"]


@pytest.mark.asyncio
async def test_row_level_access_control_transcript(
    client: AsyncClient,
    stt_api_seeded: dict,
) -> None:
    """Participant B cannot access Participant A's transcript or trigger their transcription."""
    user_b = stt_api_seeded["user_b"]
    p_b = stt_api_seeded["p_b"]
    assessment_a = stt_api_seeded["assessment_a"]
    headers_b = await create_auth_headers_for(user_b, p_b)

    # Participant B attempts to trigger A's transcription -> 403 Forbidden
    resp = await client.post(
        f"/api/v1/assessments/{assessment_a.assessment_id}/transcribe",
        headers=headers_b,
    )
    assert resp.status_code == 403

    # Participant B attempts to read A's transcript -> 403 Forbidden
    resp_get = await client.get(
        f"/api/v1/assessments/{assessment_a.assessment_id}/transcript",
        headers=headers_b,
    )
    assert resp_get.status_code == 403


@pytest.mark.asyncio
async def test_human_revision_role_authorization_and_workflow(
    client: AsyncClient,
    stt_api_seeded: dict,
) -> None:
    """Reviewers can add revisions; participants cannot; revisions appear in transcript response."""
    user_a = stt_api_seeded["user_a"]
    p_a = stt_api_seeded["p_a"]
    reviewer = stt_api_seeded["reviewer"]
    assessment_a = stt_api_seeded["assessment_a"]

    headers_a = await create_auth_headers_for(user_a, p_a)
    headers_rev = await create_auth_headers_for(reviewer)

    # 1. Transcribe assessment first
    await client.post(
        f"/api/v1/assessments/{assessment_a.assessment_id}/transcribe",
        headers=headers_a,
    )

    # 2. Participant tries to submit revision -> 403 Forbidden
    payload = {
        "revised_transcript": "He go to lectures every morning.",
        "reason": "Participant self-correction attempt (unauthorized)",
    }
    p_resp = await client.post(
        f"/api/v1/assessments/{assessment_a.assessment_id}/revisions",
        json=payload,
        headers=headers_a,
    )
    assert p_resp.status_code == 403

    # 3. Reviewer submits authorized revision -> 200 OK
    rev_payload = {
        "revised_transcript": "He go to lectures every morning.",
        "reason": "Acoustic review confirmed token 'lectures' uttered rather than 'college'.",
    }
    rev_resp = await client.post(
        f"/api/v1/assessments/{assessment_a.assessment_id}/revisions",
        json=rev_payload,
        headers=headers_rev,
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["revised_transcript"] == rev_payload["revised_transcript"]
    assert rev_data["reason"] == rev_payload["reason"]
    assert rev_data["reviewer_id"] == str(reviewer.id)

    # 4. GET transcript now lists the revision
    fresh_resp = await client.get(
        f"/api/v1/assessments/{assessment_a.assessment_id}/transcript",
        headers=headers_a,
    )
    assert fresh_resp.status_code == 200
    fresh_data = fresh_resp.json()
    assert len(fresh_data["revisions"]) == 1
    assert fresh_data["revisions"][0]["revision_id"] == rev_data["revision_id"]


@pytest.mark.asyncio
async def test_pilot_kit_stt_metrics_endpoint(
    client: AsyncClient,
    stt_api_seeded: dict,
) -> None:
    """Researcher admin can query aggregate STT metrics and recent job runs."""
    user_a = stt_api_seeded["user_a"]
    p_a = stt_api_seeded["p_a"]
    researcher = stt_api_seeded["researcher"]
    assessment_a = stt_api_seeded["assessment_a"]

    headers_a = await create_auth_headers_for(user_a, p_a)
    headers_res = await create_auth_headers_for(researcher)

    # 1. Transcribe to create metrics
    await client.post(
        f"/api/v1/assessments/{assessment_a.assessment_id}/transcribe",
        headers=headers_a,
    )

    # 2. Participant tries to query metrics -> 403 Forbidden
    part_resp = await client.get("/api/v1/assessments/metrics/stt", headers=headers_a)
    assert part_resp.status_code == 403

    # 3. Researcher queries metrics -> 200 OK
    res_resp = await client.get("/api/v1/assessments/metrics/stt", headers=headers_res)
    assert res_resp.status_code == 200
    metrics_data = res_resp.json()
    assert metrics_data["total_runs"] >= 1
    assert metrics_data["total_audio_seconds"] >= 45.0
    assert len(metrics_data["recent_jobs"]) >= 1
    assert metrics_data["recent_jobs"][0]["provider"] == "mock"
