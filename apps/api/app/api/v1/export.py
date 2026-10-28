"""Research Data Export API (P14).

Endpoints
---------
POST /export/dataset          — Create a new de-identified export snapshot
GET  /export/history          — List export snapshots for the current user
GET  /export/snapshots/{id}/download      — Re-download frozen CSV
GET  /export/snapshots/{id}/download/dict — Re-download data dictionary

Access control
--------------
Default export: RESEARCHER_ADMIN or ADMIN role required.
Elevated export (include_identifiers=True): RESEARCHER_ADMIN/ADMIN + reason field
  + X-Confirm-Elevated: true header → separate audit log entry with "elevated_export".
PARTICIPANT role → 403 on all endpoints.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.assessment import Assessment
from app.models.export import ExportSnapshot
from app.models.identity import User, UserRole
from app.models.research import Participant
from app.research.exporter import (
    ELEVATED_COLUMNS,
    SAFE_COLUMNS,
    build_export_rows,
    compute_k_anonymity_warnings,
    compute_sha256,
    generate_csv_bytes,
    generate_data_dictionary_csv,
    generate_xlsx_bytes,
)
from app.services.audit import audit_service

router = APIRouter(prefix="/export", tags=["Export"])

# Roles permitted to run any export
_EXPORT_ROLES: set[str] = {UserRole.ADMIN.value, UserRole.RESEARCHER_ADMIN.value}


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    format: str = Field("csv", pattern="^(csv|xlsx)$")
    group_filter: str = Field("all", pattern="^(all|intervention|control)$")
    hash_participant_ids: bool = False
    include_identifiers: bool = False
    reason: str | None = None


class ExportSnapshotOut(BaseModel):
    snapshot_id: str
    export_type: str
    filters_json: str | None
    row_count: int
    file_checksum_sha256: str
    format: str
    reason: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_export_role(current_user: User) -> None:
    if current_user.role.value not in _EXPORT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Export requires RESEARCHER_ADMIN or ADMIN role.")


async def _fetch_assessments(
    db: AsyncSession,
    group_filter: str,
) -> list[dict[str, Any]]:
    """Fetch completed assessments joined with participant pseudonyms."""
    stmt = (
        select(
            Assessment.assessment_id,
            Assessment.assessment_type,
            Assessment.status,
            Assessment.word_count,
            Assessment.audio_duration_seconds,
            Assessment.rubric_version,
            Assessment.stt_version,
            Assessment.prompt_version,
            Assessment.model_version,
            Assessment.is_verified,
            Assessment.is_official,
            Assessment.created_at,
            Participant.research_code,
            Participant.study_group,
        )
        .join(Participant, Assessment.participant_id == Participant.participant_id)
        .where(Assessment.status == "completed")
    )
    if group_filter != "all":
        stmt = stmt.where(Participant.study_group == group_filter)

    result = await db.execute(stmt)
    rows = result.all()

    out: list[dict[str, Any]] = []
    for row in rows:
        out.append({
            "assessment_id": row.assessment_id,
            "assessment_type": row.assessment_type.value if hasattr(row.assessment_type, "value") else str(row.assessment_type),
            "status": row.status,
            "word_count": row.word_count or 0,
            "audio_duration_seconds": float(row.audio_duration_seconds or 0.0),
            "rubric_version": row.rubric_version or "",
            "stt_version": row.stt_version or "",
            "prompt_version": row.prompt_version or "",
            "model_version": row.model_version or "",
            "is_verified": bool(row.is_verified),
            "is_official": bool(row.is_official),
            "assessment_date": row.created_at,
            "research_code": row.research_code or "",
            "study_group": row.study_group.value if hasattr(row.study_group, "value") else str(row.study_group),
        })
    return out


async def _fetch_effective_category_counts(
    db: AsyncSession,
    assessment_ids: list[str],
) -> dict[str, dict[str, int]]:
    """Return {assessment_id: {category_code: count}} using the effective annotation set.

    Effective set = reviewer decision if present, else AI candidate.
    Excludes: rejected, uncertain, transcription_related, acceptable_variation.
    """
    if not assessment_ids:
        return {}

    from app.models.assessment import ErrorAnnotation, ReviewerDecision

    # Fetch all annotations for these assessments
    stmt = select(
        ErrorAnnotation.annotation_id,
        ErrorAnnotation.assessment_id,
        ErrorAnnotation.category_code,
        ErrorAnnotation.flag,
    ).where(
        ErrorAnnotation.assessment_id.in_([uuid.UUID(aid) for aid in assessment_ids])
    )
    ann_result = await db.execute(stmt)
    annotations = {str(row.annotation_id): row for row in ann_result.all()}

    # Fetch latest reviewer decisions per annotation
    dec_stmt = select(
        ReviewerDecision.annotation_id,
        ReviewerDecision.decision,
        ReviewerDecision.edited_category,
    ).where(
        ReviewerDecision.annotation_id.in_([uuid.UUID(aid) for aid in annotations.keys()])
    )
    dec_result = await db.execute(dec_stmt)
    latest_decisions: dict[str, Any] = {}
    for row in dec_result.all():
        latest_decisions[str(row.annotation_id)] = row

    _excluded_flags = {"uncertain", "transcription_related", "acceptable_variation"}
    _excluded_decisions = {"rejected", "uncertain", "transcription_related", "acceptable_variation"}

    counts: dict[str, dict[str, int]] = {}

    for ann_id, ann in annotations.items():
        aid = str(ann.assessment_id)
        if aid not in counts:
            counts[aid] = {}

        # Determine effective category and whether assessable
        dec = latest_decisions.get(ann_id)
        if dec:
            dec_val = dec.decision.value if hasattr(dec.decision, "value") else str(dec.decision)
            if dec_val in _excluded_decisions:
                continue
            eff_cat = dec.edited_category or ann.category_code
        else:
            # AI annotation only — check flag
            if ann.flag and ann.flag.lower() in _excluded_flags:
                continue
            eff_cat = ann.category_code

        cat_key = str(eff_cat).upper() if eff_cat else "OTH"
        counts[aid][cat_key] = counts[aid].get(cat_key, 0) + 1

    return counts


# ---------------------------------------------------------------------------
# POST /export/dataset
# ---------------------------------------------------------------------------

@router.post("/dataset", status_code=status.HTTP_201_CREATED)
async def create_export(
    body: ExportRequest,
    x_confirm_elevated: str | None = Header(None, alias="X-Confirm-Elevated"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a de-identified export snapshot and return snapshot metadata + k-anonymity warnings."""
    _require_export_role(current_user)

    # Elevated export gate
    if body.include_identifiers:
        if current_user.role.value not in _EXPORT_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Elevated exports require RESEARCHER_ADMIN or ADMIN role.")
        if not body.reason:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="reason is required for elevated exports.")
        if (x_confirm_elevated or "").lower() != "true":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Header X-Confirm-Elevated: true is required for elevated exports.",
            )

    # Fetch data
    assessments = await _fetch_assessments(db, body.group_filter)
    assessment_ids = [str(a["assessment_id"]) for a in assessments]
    cat_counts = await _fetch_effective_category_counts(db, assessment_ids)

    # Build rows
    salt = str(current_user.id) if body.hash_participant_ids else None
    rows = build_export_rows(
        assessments=assessments,
        category_counts_by_assessment=cat_counts,
        include_identifiers=body.include_identifiers,
        salt=salt,
    )

    columns = ELEVATED_COLUMNS if body.include_identifiers else SAFE_COLUMNS

    # Serialise
    csv_bytes = generate_csv_bytes(rows, columns)
    dict_bytes = generate_data_dictionary_csv(columns)
    checksum = compute_sha256(csv_bytes)

    export_type = "elevated" if body.include_identifiers else "default"
    filters = {
        "group_filter": body.group_filter,
        "hash_participant_ids": body.hash_participant_ids,
        "include_identifiers": body.include_identifiers,
        "format": body.format,
    }

    # Store snapshot
    snapshot = ExportSnapshot(
        snapshot_id=uuid.uuid4(),
        exported_by=current_user.id,
        export_type=export_type,
        filters_json=json.dumps(filters),
        row_count=len(rows),
        file_checksum_sha256=checksum,
        frozen_csv_bytes=csv_bytes,
        frozen_dict_bytes=dict_bytes,
        reason=body.reason,
        format=body.format,
        created_at=datetime.utcnow(),
    )
    db.add(snapshot)
    await db.flush()
    await db.commit()

    # Audit log — action depends on export type
    action = "elevated_export" if body.include_identifiers else "export"
    await audit_service.log_event(
        db,
        actor_id=current_user.id,
        role=current_user.role.value,
        action=action,
        record_type="export_snapshot",
        record_id=str(snapshot.snapshot_id),
        outcome="success",
        details={
            "row_count": len(rows),
            "checksum_sha256": checksum,
            "export_type": export_type,
            "group_filter": body.group_filter,
            "reason": body.reason,
        },
    )

    # k-anonymity check
    qi = ["study_group", "assessment_type"]
    k_warnings = compute_k_anonymity_warnings(rows, qi, k_threshold=5)

    # For XLSX, return bytes directly; for CSV use streaming
    if body.format == "xlsx":
        generate_xlsx_bytes(rows, columns)
        return {
            "snapshot_id": str(snapshot.snapshot_id),
            "row_count": len(rows),
            "checksum_sha256": checksum,
            "export_type": export_type,
            "k_anonymity_warnings": k_warnings,
            "download_url": f"/api/v1/export/snapshots/{snapshot.snapshot_id}/download",
            "dictionary_url": f"/api/v1/export/snapshots/{snapshot.snapshot_id}/download/dict",
        }

    return {
        "snapshot_id": str(snapshot.snapshot_id),
        "row_count": len(rows),
        "checksum_sha256": checksum,
        "export_type": export_type,
        "k_anonymity_warnings": k_warnings,
        "download_url": f"/api/v1/export/snapshots/{snapshot.snapshot_id}/download",
        "dictionary_url": f"/api/v1/export/snapshots/{snapshot.snapshot_id}/download/dict",
    }


# ---------------------------------------------------------------------------
# GET /export/history
# ---------------------------------------------------------------------------

@router.get("/history")
async def list_export_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """List export snapshots visible to the current user (admin: all; else: own)."""
    _require_export_role(current_user)

    if current_user.role == UserRole.ADMIN:
        stmt = (
            select(ExportSnapshot)
            .order_by(ExportSnapshot.created_at.desc())
            .limit(limit)
        )
    else:
        stmt = (
            select(ExportSnapshot)
            .where(ExportSnapshot.exported_by == current_user.id)
            .order_by(ExportSnapshot.created_at.desc())
            .limit(limit)
        )

    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        {
            "snapshot_id": str(s.snapshot_id),
            "export_type": s.export_type,
            "filters_json": s.filters_json,
            "row_count": s.row_count,
            "file_checksum_sha256": s.file_checksum_sha256,
            "format": s.format,
            "reason": s.reason,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in snapshots
    ]


# ---------------------------------------------------------------------------
# GET /export/snapshots/{snapshot_id}/download
# ---------------------------------------------------------------------------

@router.get("/snapshots/{snapshot_id}/download")
async def download_snapshot_csv(
    snapshot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Re-download the frozen CSV bytes for a snapshot."""
    _require_export_role(current_user)

    result = await db.execute(
        select(ExportSnapshot).where(ExportSnapshot.snapshot_id == snapshot_id)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found.")

    # Researchers can only re-download their own; admins can download any
    if current_user.role != UserRole.ADMIN and snapshot.exported_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised to download this snapshot.")

    content = snapshot.frozen_csv_bytes or b""
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="syntaxlens_export_{snapshot_id}.csv"',
            "X-Checksum-SHA256": snapshot.file_checksum_sha256,
        },
    )


# ---------------------------------------------------------------------------
# GET /export/snapshots/{snapshot_id}/download/dict
# ---------------------------------------------------------------------------

@router.get("/snapshots/{snapshot_id}/download/dict")
async def download_snapshot_dict(
    snapshot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Re-download the frozen data dictionary CSV for a snapshot."""
    _require_export_role(current_user)

    result = await db.execute(
        select(ExportSnapshot).where(ExportSnapshot.snapshot_id == snapshot_id)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found.")

    if current_user.role != UserRole.ADMIN and snapshot.exported_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised to download this snapshot.")

    content = snapshot.frozen_dict_bytes or b""
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="syntaxlens_data_dictionary_{snapshot_id}.csv"',
        },
    )
