"""Reviewer Cockpit Service (Phase P9, Signature Feature D).

Implements:
- Review queue management with multi-criteria filtering and reviewer workload tracking.
- Row-level access control enforcing reviewer assignment restrictions.
- Append-only reviewer decision logging (decisions are always NEW rows, AI outputs untouched).
- Derived "effective annotation set" consolidating AI candidates, reviewer decisions, and additions.
- Assessment verification sign-off rules (all candidates resolved -> verified).
- Inter-rater agreement statistics and Cohen's Kappa calculation via pure research metrics module.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assessment import (
    Assessment,
    ErrorAnnotation,
    ReviewDecisionType,
    ReviewerAssignment,
    ReviewerDecision,
)
from app.models.identity import User, UserRole
from app.research.metrics import (
    AgreementMetrics,
    ErrorCategory,
    _round_metric,
    calculate_cohens_kappa,
)
from app.services.audit import audit_service


class ReviewService:
    """Service orchestrating Reviewer Cockpit operations."""

    async def check_reviewer_access(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        user: User,
    ) -> bool:
        """Enforce row-level ownership: Reviewers only access assigned records; Admins access all."""
        if user.role in (UserRole.RESEARCHER_ADMIN, UserRole.ADMIN):
            return True

        stmt = (
            select(ReviewerAssignment)
            .where(
                ReviewerAssignment.assessment_id == assessment_id,
                ReviewerAssignment.reviewer_id == user.id,
                ReviewerAssignment.status == "active",
            )
        )
        assignment = (await db.execute(stmt)).scalar_one_or_none()
        return assignment is not None

    async def assign_reviewer(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        assigned_by: uuid.UUID,
        review_round: int = 1,
    ) -> ReviewerAssignment:
        """Assign an assessment to a reviewer."""
        # Check if active assignment already exists
        stmt = (
            select(ReviewerAssignment)
            .where(
                ReviewerAssignment.assessment_id == assessment_id,
                ReviewerAssignment.reviewer_id == reviewer_id,
                ReviewerAssignment.review_round == review_round,
            )
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.status = "active"
            await db.flush()
            return existing

        assignment = ReviewerAssignment(
            assignment_id=uuid.uuid4(),
            assessment_id=assessment_id,
            reviewer_id=reviewer_id,
            assigned_by=assigned_by,
            review_round=review_round,
            status="active",
        )
        db.add(assignment)
        await db.flush()

        await audit_service.log_event(
            db=db,
            actor_id=assigned_by,
            role="researcher_admin",
            action="assign_reviewer",
            record_type="reviewer_assignment",
            record_id=assignment.assignment_id,
            outcome="success",
            details={
                "assessment_id": str(assessment_id),
                "reviewer_id": str(reviewer_id),
                "review_round": review_round,
            },
        )
        return assignment

    async def get_workload_counts(
        self,
        db: AsyncSession,
        user: User,
    ) -> dict[str, Any]:
        """Compute reviewer workload summary counts."""
        # Total assessments analyzed or completed
        total_stmt = select(func.count(Assessment.assessment_id)).where(
            Assessment.status.in_(["analyzed", "completed"])
        )
        total_in_system = (await db.execute(total_stmt)).scalar() or 0

        # Unreviewed vs Partially Reviewed vs Verified
        unreviewed_stmt = select(func.count(Assessment.assessment_id)).where(
            Assessment.status.in_(["analyzed", "completed"]),
            Assessment.review_status == "unreviewed",
        )
        total_unreviewed = (await db.execute(unreviewed_stmt)).scalar() or 0

        verified_stmt = select(func.count(Assessment.assessment_id)).where(
            Assessment.status.in_(["analyzed", "completed"]),
            Assessment.review_status == "verified",
        )
        total_verified = (await db.execute(verified_stmt)).scalar() or 0

        # Assigned to current user
        assigned_to_me = 0
        if user.role == UserRole.REVIEWER:
            assigned_stmt = select(func.count(ReviewerAssignment.assignment_id)).where(
                ReviewerAssignment.reviewer_id == user.id,
                ReviewerAssignment.status == "active",
            )
            assigned_to_me = (await db.execute(assigned_stmt)).scalar() or 0

        return {
            "total_system_assessments": total_in_system,
            "total_unreviewed": total_unreviewed,
            "total_partially_reviewed": total_in_system - total_unreviewed - total_verified,
            "total_verified": total_verified,
            "assigned_to_current_reviewer": assigned_to_me,
            "double_review_mode_enabled": settings.DOUBLE_REVIEW_MODE,
        }

    async def get_effective_annotations(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        target_reviewer_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Compute the derived Effective Annotation Set.
        
        Data Rule:
        The original AI annotation is NEVER modified.
        Effective value = latest reviewed decision if present, else original AI value.
        Reviewer-added errors are included with origin='reviewer'.
        """
        # 1. Fetch all annotations (both AI and reviewer-added)
        ann_stmt = (
            select(ErrorAnnotation)
            .where(ErrorAnnotation.assessment_id == assessment_id)
            .order_by(ErrorAnnotation.start_char.asc(), ErrorAnnotation.created_at.asc())
        )
        annotations = (await db.execute(ann_stmt)).scalars().all()

        effective_list: list[dict[str, Any]] = []

        for ann in annotations:
            # Fetch latest decision for this annotation
            dec_query = (
                select(ReviewerDecision)
                .where(ReviewerDecision.annotation_id == ann.annotation_id)
                .order_by(ReviewerDecision.created_at.desc())
            )
            if target_reviewer_id:
                dec_query = dec_query.where(ReviewerDecision.reviewer_id == target_reviewer_id)

            latest_dec = (await db.execute(dec_query)).scalars().first()

            if not latest_dec:
                # Unreviewed original AI annotation
                effective_list.append({
                    "annotation_id": str(ann.annotation_id),
                    "start_char": ann.start_char,
                    "end_char": ann.end_char,
                    "start_time_ms": ann.start_time_ms,
                    "end_time_ms": ann.end_time_ms,
                    "span_text": ann.candidate_error,
                    "category_code": ann.category_code,
                    "suggested_correction": ann.suggested_correction,
                    "explanation": ann.explanation,
                    "confidence": ann.confidence,
                    "origin": ann.origin,
                    "review_status": "unreviewed",
                    "decision_id": None,
                    "reviewer_id": None,
                    "reason": None,
                    "is_active_for_metrics": True,
                    "flag": ann.flag,
                })
            else:
                # Decision exists
                d_type = latest_dec.decision.value if hasattr(latest_dec.decision, "value") else str(latest_dec.decision)
                is_active = d_type != "rejected"

                eff_span = latest_dec.edited_span or ann.candidate_error
                eff_start = latest_dec.edited_start_char if latest_dec.edited_start_char is not None else ann.start_char
                eff_end = latest_dec.edited_end_char if latest_dec.edited_end_char is not None else ann.end_char
                eff_cat = latest_dec.edited_category or ann.category_code
                eff_corr = latest_dec.edited_correction or ann.suggested_correction
                eff_expl = latest_dec.edited_explanation or ann.explanation

                effective_list.append({
                    "annotation_id": str(ann.annotation_id),
                    "start_char": eff_start,
                    "end_char": eff_end,
                    "start_time_ms": ann.start_time_ms,
                    "end_time_ms": ann.end_time_ms,
                    "span_text": eff_span,
                    "category_code": eff_cat,
                    "suggested_correction": eff_corr,
                    "explanation": eff_expl,
                    "confidence": ann.confidence,
                    "origin": ann.origin,
                    "review_status": d_type,
                    "decision_id": str(latest_dec.decision_id),
                    "reviewer_id": str(latest_dec.reviewer_id),
                    "reason": latest_dec.reason,
                    "is_active_for_metrics": is_active,
                    "flag": ann.flag,
                    "decision_timestamp": latest_dec.created_at.isoformat(),
                })

        return effective_list

    async def record_decision(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        annotation_id: uuid.UUID,
        reviewer: User,
        decision: ReviewDecisionType,
        edited_span: str | None = None,
        edited_start_char: int | None = None,
        edited_end_char: int | None = None,
        edited_category: str | None = None,
        edited_correction: str | None = None,
        edited_explanation: str | None = None,
        reason: str | None = None,
        notes: str | None = None,
    ) -> ReviewerDecision:
        """Record a NEW reviewer decision row without mutating original AI records."""
        # 1. Fetch annotation and ensure it exists and belongs to assessment
        ann_stmt = select(ErrorAnnotation).where(
            ErrorAnnotation.annotation_id == annotation_id,
            ErrorAnnotation.assessment_id == assessment_id,
        )
        annotation = (await db.execute(ann_stmt)).scalar_one_or_none()
        if not annotation:
            raise ValueError(f"Annotation {annotation_id} not found on assessment {assessment_id}")

        # 2. Capture snapshot before decision
        before_state = json.dumps({
            "span_text": annotation.candidate_error,
            "category_code": annotation.category_code,
            "suggested_correction": annotation.suggested_correction,
            "explanation": annotation.explanation,
            "confidence": annotation.confidence,
            "ai_status": annotation.ai_status,
            "origin": annotation.origin,
        })

        after_state = json.dumps({
            "decision": decision.value,
            "edited_span": edited_span or annotation.candidate_error,
            "edited_category": edited_category or annotation.category_code,
            "edited_correction": edited_correction or annotation.suggested_correction,
            "edited_explanation": edited_explanation or annotation.explanation,
            "reason": reason,
        })

        # 3. Create NEW decision row (Append-only)
        new_decision = ReviewerDecision(
            decision_id=uuid.uuid4(),
            annotation_id=annotation.annotation_id,
            assessment_id=assessment_id,
            reviewer_id=reviewer.id,
            decision=decision,
            edited_span=edited_span,
            edited_start_char=edited_start_char,
            edited_end_char=edited_end_char,
            edited_category=edited_category,
            edited_correction=edited_correction,
            edited_explanation=edited_explanation,
            reason=reason,
            before_state=before_state,
            after_state=after_state,
            is_reviewer_originated=False,
            notes=notes,
        )
        db.add(new_decision)
        await db.flush()

        # 4. Check assessment-level sign-off:
        # An assessment is "verified" only when ALL its candidate annotations have been resolved
        ass_stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
        assessment = (await db.execute(ass_stmt)).scalar_one()

        all_anns_stmt = select(ErrorAnnotation.annotation_id).where(
            ErrorAnnotation.assessment_id == assessment_id
        )
        all_ann_ids = (await db.execute(all_anns_stmt)).scalars().all()

        decided_anns_stmt = (
            select(func.count(func.distinct(ReviewerDecision.annotation_id)))
            .where(
                ReviewerDecision.assessment_id == assessment_id,
                ReviewerDecision.annotation_id.in_(all_ann_ids),
            )
        )
        decided_count = (await db.execute(decided_anns_stmt)).scalar() or 0

        total_anns = len(all_ann_ids)
        if total_anns > 0 and decided_count >= total_anns:
            assessment.review_status = "verified"
            assessment.is_verified = True
            assessment.verified_at = datetime.now(UTC)
            assessment.verified_by = reviewer.id
        elif decided_count > 0:
            assessment.review_status = "partially_reviewed"
            assessment.is_verified = False

        await db.flush()

        # Audit trail logging
        await audit_service.log_event(
            db=db,
            actor_id=reviewer.id,
            role=reviewer.role.value if hasattr(reviewer.role, "value") else str(reviewer.role),
            action="reviewer_decision",
            record_type="reviewer_decision",
            record_id=new_decision.decision_id,
            outcome="success",
            details={
                "assessment_id": str(assessment_id),
                "annotation_id": str(annotation_id),
                "decision": decision.value,
                "review_status": assessment.review_status,
                "is_verified": assessment.is_verified,
            },
        )
        return new_decision

    async def add_reviewer_annotation(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        reviewer: User,
        span_text: str,
        start_char: int,
        end_char: int,
        category_code: str,
        suggested_correction: str,
        explanation: str,
        reason: str | None = None,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> ErrorAnnotation:
        """Add a candidate error missed by AI, stored as reviewer-originated."""
        ass_stmt = select(Assessment).where(Assessment.assessment_id == assessment_id)
        assessment = (await db.execute(ass_stmt)).scalar_one_or_none()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found.")

        # Create reviewer-originated ErrorAnnotation
        new_ann = ErrorAnnotation(
            annotation_id=uuid.uuid4(),
            assessment_id=assessment_id,
            start_char=start_char,
            end_char=end_char,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            candidate_error=span_text,
            suggested_correction=suggested_correction,
            category_code=category_code,
            explanation=explanation,
            confidence=1.0,
            ai_status="reviewer_added",
            flag="none",
            rubric_version=assessment.rubric_version,
            prompt_version="manual-reviewer",
            model_version="human-reviewer",
            origin="reviewer",
            created_by_reviewer_id=reviewer.id,
        )
        db.add(new_ann)
        await db.flush()

        # Record decision as ADDED
        decision = ReviewerDecision(
            decision_id=uuid.uuid4(),
            annotation_id=new_ann.annotation_id,
            assessment_id=assessment_id,
            reviewer_id=reviewer.id,
            decision=ReviewDecisionType.ADDED,
            edited_span=span_text,
            edited_start_char=start_char,
            edited_end_char=end_char,
            edited_category=category_code,
            edited_correction=suggested_correction,
            edited_explanation=explanation,
            reason=reason or "Reviewer identified syntactic error missed by AI.",
            is_reviewer_originated=True,
            before_state=None,
            after_state=json.dumps({
                "origin": "reviewer",
                "span_text": span_text,
                "category_code": category_code,
                "suggested_correction": suggested_correction,
            }),
        )
        db.add(decision)
        await db.flush()

        # Audit trail
        await audit_service.log_event(
            db=db,
            actor_id=reviewer.id,
            role=reviewer.role.value if hasattr(reviewer.role, "value") else str(reviewer.role),
            action="reviewer_add_annotation",
            record_type="error_annotation",
            record_id=new_ann.annotation_id,
            outcome="success",
            details={
                "assessment_id": str(assessment_id),
                "category_code": category_code,
                "span_text": span_text,
            },
        )
        return new_ann

    async def calculate_agreement_stats(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Compute Reviewer-vs-AI agreement rates and Inter-Reviewer Cohen's Kappa."""
        # 1. Reviewer-vs-AI Agreement
        base_query = (
            select(ErrorAnnotation, ReviewerDecision)
            .join(ReviewerDecision, ErrorAnnotation.annotation_id == ReviewerDecision.annotation_id)
            .where(ErrorAnnotation.origin == "ai")
        )
        if assessment_id:
            base_query = base_query.where(ErrorAnnotation.assessment_id == assessment_id)

        rows = (await db.execute(base_query)).all()

        total_ai_reviewed = len(rows)
        concordant_count = 0
        cat_stats: dict[str, dict[str, int]] = {
            cat.value: {"total": 0, "accepted": 0, "edited": 0, "rejected": 0, "recategorized": 0}
            for cat in ErrorCategory
        }

        for ann, dec in rows:
            cat = ann.category_code
            if cat not in cat_stats:
                cat_stats[cat] = {"total": 0, "accepted": 0, "edited": 0, "rejected": 0, "recategorized": 0}

            cat_stats[cat]["total"] += 1
            d_val = dec.decision.value if hasattr(dec.decision, "value") else str(dec.decision)

            if d_val == "accepted":
                concordant_count += 1
                cat_stats[cat]["accepted"] += 1
            elif d_val == "rejected":
                cat_stats[cat]["rejected"] += 1
            elif d_val == "edited":
                cat_stats[cat]["edited"] += 1
            elif d_val == "recategorized":
                cat_stats[cat]["recategorized"] += 1

        overall_pct = (concordant_count / total_ai_reviewed * 100.0) if total_ai_reviewed > 0 else 100.0

        # Formatted category breakdowns
        category_breakdown = {}
        for cat, counts in cat_stats.items():
            tot = counts["total"]
            acc = counts["accepted"]
            rate = _round_metric((acc / tot * 100.0), 1) if tot > 0 else 0.0
            category_breakdown[cat] = {
                "total_reviewed": tot,
                "accepted": acc,
                "rejected": counts["rejected"],
                "edited": counts["edited"],
                "recategorized": counts["recategorized"],
                "agreement_rate_pct": rate,
            }

        # 2. Inter-Reviewer Cohen's Kappa for double-reviewed items
        # Find assessments reviewed by at least two distinct reviewers
        kappa_result: AgreementMetrics | None = None
        rater1_labels: list[str] = []
        rater2_labels: list[str] = []

        double_rev_stmt = (
            select(
                ReviewerDecision.annotation_id,
                func.array_agg(ReviewerDecision.reviewer_id).label("reviewers"),
                func.array_agg(ReviewerDecision.decision).label("decisions"),
            )
            .group_by(ReviewerDecision.annotation_id)
            .having(func.count(func.distinct(ReviewerDecision.reviewer_id)) >= 2)
        )
        if assessment_id:
            double_rev_stmt = double_rev_stmt.where(ReviewerDecision.assessment_id == assessment_id)

        try:
            double_rev_rows = (await db.execute(double_rev_stmt)).all()
            for r in double_rev_rows:
                decs = r.decisions
                if len(decs) >= 2:
                    d1 = decs[0].value if hasattr(decs[0], "value") else str(decs[0])
                    d2 = decs[1].value if hasattr(decs[1], "value") else str(decs[1])
                    rater1_labels.append(d1)
                    rater2_labels.append(d2)
        except Exception:
            # Fallback if array_agg not supported on dialect (e.g. basic SQLite)
            pass

        if len(rater1_labels) > 0:
            kappa_result = calculate_cohens_kappa(rater1_labels, rater2_labels)
        else:
            kappa_result = AgreementMetrics(
                total_items=0,
                concordant_items=0,
                percent_agreement=100.0,
                cohens_kappa=1.0,
                interpretation="Single review baseline",
            )

        return {
            "ai_vs_reviewer": {
                "total_items": total_ai_reviewed,
                "accepted_count": concordant_count,
                "percent_agreement": _round_metric(overall_pct, 2),
                "category_breakdown": category_breakdown,
            },
            "inter_reviewer_kappa": {
                "total_double_reviewed": kappa_result.total_items,
                "concordant_items": kappa_result.concordant_items,
                "percent_agreement": kappa_result.percent_agreement,
                "cohens_kappa": kappa_result.cohens_kappa,
                "interpretation": kappa_result.interpretation,
            },
        }


review_service = ReviewService()
