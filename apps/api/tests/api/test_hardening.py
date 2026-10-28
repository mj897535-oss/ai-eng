"""Phase P15: Comprehensive Security, Hardening & Reliability Tests.

Test Matrix:
1. test_security_headers_hsts_and_csp
2. test_provider_privacy_gate_blocks_unapproved
3. test_provider_privacy_gate_allows_approved
4. test_canary_pii_detection_blocks_leaks
5. test_participant_data_purge_removes_audio_and_anonymizes
6. test_circuit_breaker_trips_on_failures
7. test_circuit_breaker_recovers_after_timeout
8. test_backup_and_restore_drill
9. test_idempotent_submissions_prevent_duplicates
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_auth_headers_for
from app.models.assessment import Assessment, AssessmentTask, AssessmentType
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.services.backup import generate_backup_archive, verify_and_restore_backup
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from app.services.privacy_gate import (
    ProviderPrivacyGateError,
    inspect_payload_for_canaries,
    verify_provider_compliance,
)
from app.services.retention import data_retention_service


# ---------------------------------------------------------------------------
# Security Headers & HSTS Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_security_headers_hsts_and_csp(client: AsyncClient):
    """Verify HSTS, CSP, and secure framing headers on live API responses."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == status.HTTP_200_OK

    headers = resp.headers
    assert "Strict-Transport-Security" in headers
    assert "max-age=63072000" in headers["Strict-Transport-Security"]
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"


# ---------------------------------------------------------------------------
# Provider Privacy Gate Tests
# ---------------------------------------------------------------------------

def test_provider_privacy_gate_blocks_unapproved():
    """Unapproved or consumer-tier AI providers are strictly refused at runtime."""
    with pytest.raises(ProviderPrivacyGateError) as exc_info:
        verify_provider_compliance("unapproved_third_party")
    assert "not approved" in str(exc_info.value).lower()

    with pytest.raises(ProviderPrivacyGateError) as exc_info2:
        verify_provider_compliance("completely_unknown_llm")
    assert "institutional privacy registry" in str(exc_info2.value).lower()


def test_provider_privacy_gate_allows_approved():
    """Approved enterprise providers with confirmed zero-training pass the gate."""
    profile = verify_provider_compliance("mock")
    assert profile.approval_status.value == "approved"
    assert profile.training_opt_out_confirmed is True

    profile_gemini = verify_provider_compliance("gemini")
    assert profile_gemini.approval_status.value == "approved"


def test_canary_pii_detection_blocks_leaks():
    """Outgoing payloads are inspected for direct PII and canary participant names."""
    clean_text = "The participant said: 'I go to school yesterday and I sees my teacher.'"
    assert inspect_payload_for_canaries(clean_text) == []

    dirty_email = "Transcript from user student.alex@univ.edu: I go to store."
    violations = inspect_payload_for_canaries(dirty_email)
    assert len(violations) >= 1
    assert "PII pattern detected" in violations[0]

    canary_leak = "Participant Aarav Sharma recorded this sentence."
    canary_violations = inspect_payload_for_canaries(canary_leak, canary_tokens=["Aarav Sharma", "SL-2026-999"])
    assert len(canary_violations) >= 1
    assert "Aarav Sharma" in canary_violations[0]


# ---------------------------------------------------------------------------
# Retention & Right-to-be-Forgotten Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_participant_data_purge_removes_audio_and_anonymizes(
    test_session: AsyncSession,
):
    """Purge operation scrubs direct identifiers and raw speech audio keys."""
    # Create test participant and assessment
    user = User(
        id=uuid.uuid4(),
        email="purge_me@syntaxlens.edu",
        full_name="Purge Candidate",
        hashed_password="pw",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    part = Participant(
        participant_id=uuid.uuid4(),
        user_id=user.id,
        research_code="SL-PURGE-01",
        study_group=StudyGroup.INTERVENTION,
        is_active=True,
    )
    task = AssessmentTask(
        task_id=uuid.uuid4(),
        title="Purge Task",
        prompt_text="Describe something.",
        equivalence_group="G1",
        rubric_version="v1",
    )
    asmt = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=part.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        status="completed",
        audio_key="audio/SL-PURGE-01/pre_audio.webm",
        transcript="I had two sister.",
        word_count=4,
        stt_version="mock-stt-v1",
        rubric_version="v1.0-jam-phd",
        prompt_version="v1.0-assessor",
        model_version="mock-llm-v1",
        is_verified=True,
    )
    test_session.add_all([user, part, task, asmt])
    await test_session.commit()

    # Execute purge
    summary = await data_retention_service.execute_participant_purge(
        db=test_session,
        participant_id=part.participant_id,
        actor_id=uuid.uuid4(),
        actor_role="admin",
        preserve_deidentified_metrics=True,
    )

    assert summary.status == "completed"
    assert summary.audio_files_deleted == 1

    # Reload records
    await test_session.refresh(user)
    await test_session.refresh(part)
    await test_session.refresh(asmt)

    assert user.is_active is False
    assert "Withdrawn Participant" in user.full_name
    assert "redacted" in user.email
    assert part.is_withdrawn is True
    assert "tombstone/purged" in asmt.audio_key
    # De-identified transcript preserved for publication stats
    assert asmt.transcript == "I had two sister."


# ---------------------------------------------------------------------------
# Circuit Breaker & Reliability Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_circuit_breaker_trips_on_failures():
    """Circuit breaker transitions to OPEN after 3 consecutive failures."""
    cb = CircuitBreaker("mock_stt", failure_threshold=3, recovery_timeout_seconds=0.1)

    fail_mock = AsyncMock(side_effect=ConnectionError("Upstream STT timeout"))

    # Failures 1 & 2
    for _ in range(2):
        with pytest.raises(ConnectionError):
            await cb.call(fail_mock)
        assert cb.state == CircuitState.CLOSED

    # Failure 3 -> Trips to OPEN
    with pytest.raises(ConnectionError):
        await cb.call(fail_mock)
    assert cb.state == CircuitState.OPEN

    # 4th call is immediately rejected with CircuitBreakerOpenError without calling upstream
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(fail_mock)


@pytest.mark.asyncio
async def test_circuit_breaker_recovers_after_timeout():
    """Circuit breaker transitions to HALF_OPEN and resets on recovery."""
    import asyncio
    cb = CircuitBreaker("mock_llm", failure_threshold=2, recovery_timeout_seconds=0.05)

    fail_mock = AsyncMock(side_effect=ConnectionError("Downstream LLM unavailable"))
    for _ in range(2):
        with pytest.raises(ConnectionError):
            await cb.call(fail_mock)
    assert cb.state == CircuitState.OPEN

    # Wait out recovery timeout
    await asyncio.sleep(0.06)

    success_mock = AsyncMock(return_value={"result": "recovered"})
    res = await cb.call(success_mock)
    assert res == {"result": "recovered"}
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# Backup & Disaster Recovery Tests
# ---------------------------------------------------------------------------

def test_backup_and_restore_drill():
    """Backup manifest generation and automated cryptographic restore drill."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        mock_data = {
            "participants": [{"id": "p1", "code": "SL-001"}],
            "assessments": [{"id": "a1", "words": 120}],
        }

        manifest = generate_backup_archive(tmp_dir, mock_data)
        assert manifest.status == "completed"
        assert len(manifest.archive_checksum_sha256) == 64

        backup_path = Path(tmp_dir) / f"{manifest.backup_id}.json"
        restored = verify_and_restore_backup(backup_path)

        assert restored["restore_status"] == "success"
        assert restored["backup_id"] == manifest.backup_id
        assert set(restored["recovered_tables"]) == {"participants", "assessments"}
        assert restored["verified_checksum"] == manifest.archive_checksum_sha256
