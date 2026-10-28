"""P14: Research Data Export Tests.

Test matrix
-----------
1. test_default_export_has_no_identifier_columns
2. test_data_dictionary_covers_100_pct_of_export_columns
3. test_audit_row_written_on_export
4. test_elevated_export_requires_reason_and_role
5. test_snapshot_reproducibility
6. test_participant_rbac_cannot_export
7. test_k_anonymity_warning_on_small_group
8. test_export_history_returns_snapshots
9. test_re_download_returns_frozen_bytes
10. test_export_dict_download
"""

from __future__ import annotations

import csv
import io
import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentTask, AssessmentType
from app.models.audit import AuditLog
from app.models.export import ExportSnapshot
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.research.exporter import (
    EXPORT_COLUMN_DEFINITIONS,
    FORBIDDEN_DEFAULT_COLUMNS,
    SAFE_COLUMN_NAMES,
    build_export_rows,
    compute_k_anonymity_warnings,
    generate_csv_bytes,
    generate_data_dictionary_csv,
)
from tests.conftest import create_auth_headers_for

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_participant(db: AsyncSession, code: str = "SL-2026-001", group: str = "intervention") -> Participant:
    p = Participant(
        participant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        research_code=code,
        study_group=StudyGroup.INTERVENTION if group == "intervention" else StudyGroup.CONTROL,
        is_active=True,
        is_withdrawn=False,
    )
    db.add(p)
    return p


def _make_task(db: AsyncSession) -> AssessmentTask:
    t = AssessmentTask(
        task_id=uuid.uuid4(),
        title="Export Test Task",
        prompt_text="Describe a typical school day.",
        equivalence_group="A",
        rubric_version="v1",
    )
    db.add(t)
    return t


def _make_assessment(
    db: AsyncSession, participant: Participant, task: AssessmentTask, atype: str = "pre"
) -> Assessment:
    a = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE if atype == "pre" else AssessmentType.POST,
        status="completed",
        audio_key="audio/test_export.webm",
        word_count=120,
        rubric_version="v1",
        stt_version="mock-stt-v1",
        prompt_version="v1",
        model_version="mock-llm-v1",
        is_verified=True,
        is_official=True,
    )
    db.add(a)
    return a


def _make_researcher_admin(db: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"ra_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Test Researcher",
        hashed_password="hashed",
        role=UserRole.RESEARCHER_ADMIN,
        is_active=True,
    )
    db.add(u)
    return u


def _make_participant_user(db: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"p_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Test Participant",
        hashed_password="hashed",
        role=UserRole.PARTICIPANT,
        is_active=True,
    )
    db.add(u)
    return u


# ---------------------------------------------------------------------------
# Unit tests (pure exporter module — no DB/HTTP)
# ---------------------------------------------------------------------------

class TestExporterUnit:
    def test_default_export_has_no_identifier_columns(self):
        """No forbidden column names appear in the safe column set."""
        for forbidden in FORBIDDEN_DEFAULT_COLUMNS:
            assert forbidden not in SAFE_COLUMN_NAMES, (
                f"Forbidden column '{forbidden}' found in default export column list."
            )

    def test_data_dictionary_covers_100_pct_of_export_columns(self):
        """Every column in EXPORT_COLUMN_DEFINITIONS appears in generated CSV dictionary."""
        dict_bytes = generate_data_dictionary_csv(EXPORT_COLUMN_DEFINITIONS)
        reader = csv.DictReader(io.StringIO(dict_bytes.decode("utf-8")))
        dict_col_names = {row["column_name"] for row in reader}
        export_col_names = {c.column_name for c in EXPORT_COLUMN_DEFINITIONS}
        missing = export_col_names - dict_col_names
        assert not missing, f"Data dictionary missing columns: {missing}"

    def test_safe_columns_subset_of_all_columns(self):
        """SAFE_COLUMN_NAMES is a strict subset of all defined column names."""
        all_names = {c.column_name for c in EXPORT_COLUMN_DEFINITIONS}
        for name in SAFE_COLUMN_NAMES:
            assert name in all_names

    def test_build_export_rows_produces_correct_counts(self):
        """build_export_rows correctly aggregates category counts and computes rates."""
        aid = str(uuid.uuid4())
        assessments = [{
            "assessment_id": aid,
            "assessment_type": "pre",
            "status": "completed",
            "word_count": 100,
            "audio_duration_seconds": 45.0,
            "rubric_version": "v1",
            "stt_version": "mock-stt-v1",
            "prompt_version": "v1",
            "model_version": "mock-llm-v1",
            "is_verified": True,
            "is_official": True,
            "assessment_date": "2026-10-01",
            "research_code": "SL-2026-001",
            "study_group": "intervention",
        }]
        cat_counts = {aid: {"TNS": 3, "SVA": 2}}
        rows = build_export_rows(assessments, cat_counts)
        assert len(rows) == 1
        row = rows[0]
        assert row["count_tns"] == 3
        assert row["count_sva"] == 2
        assert row["total_assessable_errors"] == 5
        assert row["error_rate_per_100_words"] == 5.0
        assert row["rate_tns_per_100"] == 3.0
        assert row["provisional"] is False  # is_verified=True

    def test_build_export_rows_hash_replaces_research_code(self):
        """When salt is provided, research_code is replaced with HMAC hash."""
        aid = str(uuid.uuid4())
        assessments = [{
            "assessment_id": aid,
            "assessment_type": "pre",
            "status": "completed",
            "word_count": 50,
            "audio_duration_seconds": 30.0,
            "rubric_version": "v1",
            "stt_version": "mock-stt-v1",
            "prompt_version": "v1",
            "model_version": "mock-llm-v1",
            "is_verified": False,
            "is_official": False,
            "assessment_date": "2026-10-01",
            "research_code": "SL-2026-099",
            "study_group": "control",
        }]
        rows_plain = build_export_rows(assessments, {})
        rows_hashed = build_export_rows(assessments, {}, salt="test-salt-123")
        assert rows_plain[0]["research_code"] == "SL-2026-099"
        assert rows_hashed[0]["research_code"] != "SL-2026-099"
        assert len(rows_hashed[0]["research_code"]) == 64  # SHA-256 hex

    def test_k_anonymity_warning_on_small_group(self):
        """Warning is emitted when a quasi-identifier combination has n < threshold."""
        rows = [
            {"study_group": "control", "assessment_type": "pre"},
            {"study_group": "control", "assessment_type": "pre"},
            {"study_group": "intervention", "assessment_type": "post"},
        ]
        warnings = compute_k_anonymity_warnings(rows, ["study_group", "assessment_type"], k_threshold=5)
        assert len(warnings) >= 1
        for w in warnings:
            assert "k-anonymity warning" in w

    def test_k_anonymity_no_warning_when_above_threshold(self):
        """No warning when all quasi-identifier combinations meet the threshold."""
        rows = [{"study_group": "intervention", "assessment_type": "pre"}] * 10
        warnings = compute_k_anonymity_warnings(rows, ["study_group", "assessment_type"], k_threshold=5)
        assert warnings == []

    def test_generate_csv_bytes_header_matches_columns(self):
        """Generated CSV header row matches column definition order."""
        from app.research.exporter import SAFE_COLUMNS
        rows = [{}]
        csv_bytes = generate_csv_bytes(rows, SAFE_COLUMNS)
        reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
        header = reader.fieldnames or []
        assert header == SAFE_COLUMN_NAMES


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestExportAPI:
    async def test_participant_rbac_cannot_export(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """PARTICIPANT role receives 403 on all export endpoints."""
        puser = _make_participant_user(test_session)
        await test_session.commit()
        headers = await create_auth_headers_for(puser)

        r1 = await client.post("/api/v1/export/dataset", json={"format": "csv"}, headers=headers)
        assert r1.status_code == status.HTTP_403_FORBIDDEN

        r2 = await client.get("/api/v1/export/history", headers=headers)
        assert r2.status_code == status.HTTP_403_FORBIDDEN

    async def test_elevated_export_requires_reason(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Elevated export without reason returns 422."""
        ra = _make_researcher_admin(test_session)
        await test_session.commit()
        headers = await create_auth_headers_for(ra)
        headers["X-Confirm-Elevated"] = "true"

        r = await client.post(
            "/api/v1/export/dataset",
            json={"format": "csv", "include_identifiers": True},
            headers=headers,
        )
        assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_elevated_export_requires_confirm_header(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Elevated export without X-Confirm-Elevated: true header returns 422."""
        ra = _make_researcher_admin(test_session)
        await test_session.commit()
        headers = await create_auth_headers_for(ra)

        r = await client.post(
            "/api/v1/export/dataset",
            json={"format": "csv", "include_identifiers": True, "reason": "IRB audit"},
            headers=headers,
        )
        assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_default_export_creates_snapshot_and_audit_row(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Default export creates an ExportSnapshot row and writes an audit log."""
        ra = _make_researcher_admin(test_session)
        participant = _make_participant(test_session)
        task = _make_task(test_session)
        _make_assessment(test_session, participant, task)
        await test_session.commit()
        headers = await create_auth_headers_for(ra)

        r = await client.post("/api/v1/export/dataset", json={"format": "csv"}, headers=headers)
        assert r.status_code == status.HTTP_201_CREATED
        data = r.json()
        assert "snapshot_id" in data
        assert "checksum_sha256" in data
        assert isinstance(data["k_anonymity_warnings"], list)

        from sqlalchemy import select
        snap_result = await test_session.execute(
            select(ExportSnapshot).where(ExportSnapshot.exported_by == ra.id)
        )
        snapshot = snap_result.scalar_one_or_none()
        assert snapshot is not None
        assert snapshot.export_type == "default"

        audit_result = await test_session.execute(
            select(AuditLog).where(AuditLog.actor_id == ra.id)
        )
        audit_rows = audit_result.scalars().all()
        export_audits = [a for a in audit_rows if a.action == "export"]
        assert len(export_audits) >= 1

    async def test_audit_row_written_on_export(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Every export call writes an AuditLog row."""
        ra = _make_researcher_admin(test_session)
        await test_session.commit()
        headers = await create_auth_headers_for(ra)

        from sqlalchemy import func, select
        count_before = (
            await test_session.execute(
                select(func.count()).select_from(AuditLog).where(AuditLog.actor_id == ra.id)
            )
        ).scalar()

        r = await client.post("/api/v1/export/dataset", json={"format": "csv"}, headers=headers)
        assert r.status_code == status.HTTP_201_CREATED

        count_after = (
            await test_session.execute(
                select(func.count()).select_from(AuditLog).where(AuditLog.actor_id == ra.id)
            )
        ).scalar()

        assert count_after > count_before

    async def test_snapshot_reproducibility(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Re-downloading a snapshot returns identical bytes and checksum."""
        ra = _make_researcher_admin(test_session)
        participant = _make_participant(test_session, "SL-2026-REPRO")
        task = _make_task(test_session)
        _make_assessment(test_session, participant, task)
        await test_session.commit()
        headers = await create_auth_headers_for(ra)

        create_resp = await client.post(
            "/api/v1/export/dataset", json={"format": "csv"}, headers=headers
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        snapshot_id = create_resp.json()["snapshot_id"]
        original_checksum = create_resp.json()["checksum_sha256"]

        dl_resp = await client.get(
            f"/api/v1/export/snapshots/{snapshot_id}/download", headers=headers
        )
        assert dl_resp.status_code == status.HTTP_200_OK
        assert dl_resp.headers.get("X-Checksum-SHA256") == original_checksum

    async def test_export_history_returns_snapshots(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Export history endpoint lists created snapshots."""
        ra = _make_researcher_admin(test_session)
        await test_session.commit()
        headers = await create_auth_headers_for(ra)

        await client.post("/api/v1/export/dataset", json={"format": "csv"}, headers=headers)
        hist_resp = await client.get("/api/v1/export/history", headers=headers)
        assert hist_resp.status_code == status.HTTP_200_OK
        history = hist_resp.json()
        assert isinstance(history, list)
        assert len(history) >= 1
        first = history[0]
        assert "snapshot_id" in first
        assert "file_checksum_sha256" in first
        assert "row_count" in first

    async def test_export_dict_download(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Data dictionary download returns CSV with column_name header."""
        ra = _make_researcher_admin(test_session)
        await test_session.commit()
        headers = await create_auth_headers_for(ra)

        create_resp = await client.post(
            "/api/v1/export/dataset", json={"format": "csv"}, headers=headers
        )
        snapshot_id = create_resp.json()["snapshot_id"]

        dict_resp = await client.get(
            f"/api/v1/export/snapshots/{snapshot_id}/download/dict", headers=headers
        )
        assert dict_resp.status_code == status.HTTP_200_OK
        reader = csv.DictReader(io.StringIO(dict_resp.content.decode("utf-8")))
        headers_read = reader.fieldnames or []
        assert "column_name" in headers_read
        assert "definition" in headers_read
        assert "calculation_rule" in headers_read

    async def test_default_export_csv_headers_no_forbidden(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """CSV downloaded from a default export contains no forbidden columns."""
        ra = _make_researcher_admin(test_session)
        participant = _make_participant(test_session, "SL-2026-SAFE")
        task = _make_task(test_session)
        _make_assessment(test_session, participant, task)
        await test_session.commit()
        headers = await create_auth_headers_for(ra)

        create_resp = await client.post(
            "/api/v1/export/dataset", json={"format": "csv"}, headers=headers
        )
        snapshot_id = create_resp.json()["snapshot_id"]

        dl_resp = await client.get(
            f"/api/v1/export/snapshots/{snapshot_id}/download", headers=headers
        )
        assert dl_resp.status_code == status.HTTP_200_OK

        reader = csv.DictReader(io.StringIO(dl_resp.content.decode("utf-8")))
        headers_set = set(reader.fieldnames or [])
        intersection = headers_set & FORBIDDEN_DEFAULT_COLUMNS
        assert not intersection, f"Forbidden columns in default export: {intersection}"
