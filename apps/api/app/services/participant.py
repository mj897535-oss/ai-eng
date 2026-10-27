"""Participant Management and Bulk CSV Import Service.

NON-NEGOTIABLE RESEARCH INTEGRITY & PRIVACY RULES:
- Participant IDs are pseudonymous, collision-safe, and never reused.
- Duplicate IDs are rejected with a clear, descriptive message.
- Identity fields (real name, email) are kept strictly separate from research fields.
"""

import csv
import io
import re
import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.services.audit import audit_service


class ParticipantCreateInput(BaseModel):
    research_code: str | None = None
    study_group: StudyGroup = StudyGroup.INTERVENTION
    age: int | None = None
    age_band: str | None = None
    mother_tongue: str | None = None
    school_medium: str | None = None
    country: str | None = "India"
    state: str | None = None
    city: str | None = None
    email: str | None = None
    full_name: str | None = None


class CSVRowValidation(BaseModel):
    row_number: int
    research_code: str
    study_group: str
    email: str | None = None
    age: int | None = None
    age_band: str | None = None
    mother_tongue: str | None = None
    school_medium: str | None = None
    country: str | None = "India"
    state: str | None = None
    city: str | None = None
    is_valid: bool = True
    error_reason: str | None = None


class CSVImportResult(BaseModel):
    dry_run: bool
    total_rows: int
    valid_count: int
    rejected_count: int
    duplicate_count: int
    valid_rows: list[CSVRowValidation]
    rejected_rows: list[CSVRowValidation]
    duplicates_found: list[dict[str, Any]]
    can_commit: bool


class ParticipantService:
    async def generate_next_research_code(
        self,
        db: AsyncSession,
        prefix: str | None = None,
    ) -> str:
        """Generate a sequential, collision-safe pseudonymous participant research code.

        Format: e.g. "SL-2026-0001".
        """
        code_prefix = prefix or settings.RESEARCH_CODE_PREFIX

        stmt = select(Participant.research_code).where(
            Participant.research_code.like(f"{code_prefix}%")
        )
        result = await db.execute(stmt)
        existing_codes = result.scalars().all()

        max_num = 0
        pattern = re.compile(rf"^{re.escape(code_prefix)}(\d+)$")
        for code in existing_codes:
            match = pattern.match(code)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

        next_num = max_num + 1
        candidate_code = f"{code_prefix}{next_num:04d}"

        # Invariant check: ensure candidate does not exist
        while candidate_code in existing_codes:
            next_num += 1
            candidate_code = f"{code_prefix}{next_num:04d}"

        return candidate_code

    async def check_code_exists(self, db: AsyncSession, research_code: str) -> bool:
        stmt = select(func.count(Participant.participant_id)).where(
            func.lower(Participant.research_code) == research_code.strip().lower()
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def create_participant(
        self,
        db: AsyncSession,
        input_data: ParticipantCreateInput,
        actor_id: uuid.UUID | None = None,
        actor_role: str = "researcher_admin",
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> Participant:
        """Create a single participant record with collision detection."""
        # 1. Resolve research code
        if input_data.research_code and input_data.research_code.strip():
            code = input_data.research_code.strip()
            if await self.check_code_exists(db, code):
                raise ValueError(
                    f"Participant ID '{code}' is already registered in this study."
                )
        else:
            code = await self.generate_next_research_code(db)

        # 2. Optionally create linked user account if email provided
        user_id: uuid.UUID | None = None
        if input_data.email and input_data.email.strip():
            email = input_data.email.strip().lower()
            # Check user existence
            stmt = select(User).where(func.lower(User.email) == email)
            existing_user = (await db.execute(stmt)).scalar_one_or_none()
            if existing_user:
                user_id = existing_user.id
            else:
                user = User(
                    id=uuid.uuid4(),
                    email=email,
                    full_name=input_data.full_name or f"Participant {code}",
                    hashed_password=get_password_hash("SyntaxLens@Temp2026!"),
                    role=UserRole.PARTICIPANT,
                    is_active=True,
                    must_change_password=True,
                )
                db.add(user)
                await db.flush()
                user_id = user.id

        # 3. Create participant record
        participant = Participant(
            participant_id=uuid.uuid4(),
            research_code=code,
            user_id=user_id,
            age=input_data.age,
            age_band=input_data.age_band,
            mother_tongue=input_data.mother_tongue,
            school_medium=input_data.school_medium,
            country=input_data.country or "India",
            state=input_data.state,
            city=input_data.city,
            study_group=input_data.study_group,
            is_group_blinded=settings.BLIND_STUDY_GROUP_FROM_PARTICIPANTS,
            is_active=True,
            is_withdrawn=False,
            onboarding_completed=False,
            onboarding_step="consent",
        )
        db.add(participant)
        await db.flush()

        # 4. Audit Log
        await audit_service.log_event(
            db=db,
            action="participant_created",
            actor_id=actor_id,
            role=actor_role,
            record_type="participant",
            record_id=str(participant.participant_id),
            outcome="success",
            ip_hash=ip_hash,
            user_agent=user_agent,
            details={"research_code": code, "study_group": input_data.study_group.value},
        )

        return participant

    async def parse_and_process_csv(
        self,
        db: AsyncSession,
        csv_text: str,
        dry_run: bool = True,
        actor_id: uuid.UUID | None = None,
        actor_role: str = "researcher_admin",
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> CSVImportResult:
        """Parse bulk CSV import with dry-run preview and duplicate detection."""
        f = io.StringIO(csv_text.strip())
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            return CSVImportResult(
                dry_run=dry_run,
                total_rows=0,
                valid_count=0,
                rejected_count=0,
                duplicate_count=0,
                valid_rows=[],
                rejected_rows=[],
                duplicates_found=[],
                can_commit=False,
            )

        # Standardize headers to lowercase stripped
        normalized_headers = {k.strip().lower(): k for k in reader.fieldnames if k}

        # Gather existing research codes and emails to detect DB duplicates
        all_codes_res = await db.execute(select(func.lower(Participant.research_code)))
        existing_codes_set = set(all_codes_res.scalars().all())

        all_emails_res = await db.execute(select(func.lower(User.email)))
        existing_emails_set = set(all_emails_res.scalars().all())

        seen_codes_in_batch: set[str] = set()
        seen_emails_in_batch: set[str] = set()

        valid_rows: list[CSVRowValidation] = []
        rejected_rows: list[CSVRowValidation] = []
        duplicates_found: list[dict[str, Any]] = []

        row_idx = 1
        generated_counter = 0

        for raw_row in reader:
            row_idx += 1
            # Extract fields flexibly
            def get_val(row_data: dict[str, Any], *keys: str) -> str | None:
                for k in keys:
                    actual_key = normalized_headers.get(k)
                    if actual_key and row_data.get(actual_key):
                        val = str(row_data[actual_key]).strip()
                        if val:
                            return val
                return None

            code_raw = get_val(raw_row, "research_code", "participant_id", "code", "id")
            group_raw = get_val(raw_row, "study_group", "group") or "intervention"
            email_raw = get_val(raw_row, "email")
            age_raw = get_val(raw_row, "age")
            age_band_raw = get_val(raw_row, "age_band", "age_group")
            mt_raw = get_val(raw_row, "mother_tongue", "first_language")
            med_raw = get_val(raw_row, "school_medium", "medium")
            country_raw = get_val(raw_row, "country") or "India"
            state_raw = get_val(raw_row, "state")
            city_raw = get_val(raw_row, "city")

            # Validate study group
            group_val = group_raw.lower()
            if group_val not in ("intervention", "control"):
                rejected_rows.append(
                    CSVRowValidation(
                        row_number=row_idx,
                        research_code=code_raw or f"ROW-{row_idx}",
                        study_group=group_raw,
                        is_valid=False,
                        error_reason=f"Invalid study group '{group_raw}'. Must be 'control' or 'intervention'.",
                    )
                )
                continue

            # Validate research code
            if code_raw:
                code_clean = code_raw.strip()
                code_lower = code_clean.lower()

                # Duplicate in batch
                if code_lower in seen_codes_in_batch:
                    duplicate_entry = {
                        "row_number": row_idx,
                        "research_code": code_clean,
                        "reason": "Duplicate participant ID within this CSV file.",
                    }
                    duplicates_found.append(duplicate_entry)
                    rejected_rows.append(
                        CSVRowValidation(
                            row_number=row_idx,
                            research_code=code_clean,
                            study_group=group_val,
                            is_valid=False,
                            error_reason=str(duplicate_entry["reason"]),
                        )
                    )
                    continue

                # Duplicate in database
                if code_lower in existing_codes_set:
                    duplicate_entry = {
                        "row_number": row_idx,
                        "research_code": code_clean,
                        "reason": f"Participant ID '{code_clean}' is already registered in the study.",
                    }
                    duplicates_found.append(duplicate_entry)
                    rejected_rows.append(
                        CSVRowValidation(
                            row_number=row_idx,
                            research_code=code_clean,
                            study_group=group_val,
                            is_valid=False,
                            error_reason=str(duplicate_entry["reason"]),
                        )
                    )
                    continue

                seen_codes_in_batch.add(code_lower)
                resolved_code = code_clean
            else:
                # Auto-generate sequentially for dry run preview
                generated_counter += 1
                resolved_code = f"{settings.RESEARCH_CODE_PREFIX}AUTO-{generated_counter:04d}"

            # Validate age if present
            age_val: int | None = None
            if age_raw:
                try:
                    age_val = int(age_raw)
                    if age_val < 15 or age_val > 100:
                        rejected_rows.append(
                            CSVRowValidation(
                                row_number=row_idx,
                                research_code=resolved_code,
                                study_group=group_val,
                                is_valid=False,
                                error_reason=f"Age '{age_raw}' is out of reasonable research bounds (15-100).",
                            )
                        )
                        continue
                except ValueError:
                    rejected_rows.append(
                        CSVRowValidation(
                            row_number=row_idx,
                            research_code=resolved_code,
                            study_group=group_val,
                            is_valid=False,
                            error_reason=f"Invalid age integer format '{age_raw}'.",
                        )
                    )
                    continue

            # Validate email uniqueness if present
            if email_raw:
                email_lower = email_raw.lower()
                if email_lower in seen_emails_in_batch:
                    rejected_rows.append(
                        CSVRowValidation(
                            row_number=row_idx,
                            research_code=resolved_code,
                            study_group=group_val,
                            email=email_raw,
                            is_valid=False,
                            error_reason=f"Duplicate email '{email_raw}' within this CSV file.",
                        )
                    )
                    continue

                if email_lower in existing_emails_set:
                    rejected_rows.append(
                        CSVRowValidation(
                            row_number=row_idx,
                            research_code=resolved_code,
                            study_group=group_val,
                            email=email_raw,
                            is_valid=False,
                            error_reason=f"Email '{email_raw}' is already registered to an existing account.",
                        )
                    )
                    continue

                seen_emails_in_batch.add(email_lower)

            # Row is valid!
            valid_rows.append(
                CSVRowValidation(
                    row_number=row_idx,
                    research_code=resolved_code,
                    study_group=group_val,
                    email=email_raw,
                    age=age_val,
                    age_band=age_band_raw,
                    mother_tongue=mt_raw,
                    school_medium=med_raw,
                    country=country_raw,
                    state=state_raw,
                    city=city_raw,
                    is_valid=True,
                )
            )

        total_rows = len(valid_rows) + len(rejected_rows)
        can_commit = len(valid_rows) > 0 and len(rejected_rows) == 0

        # If not dry run and we can commit, insert records!
        if not dry_run and len(valid_rows) > 0:
            for item in valid_rows:
                # If code was auto-generated placeholder, resolve real sequential ID
                if item.research_code.startswith(f"{settings.RESEARCH_CODE_PREFIX}AUTO-"):
                    item_code = await self.generate_next_research_code(db)
                else:
                    item_code = item.research_code

                user_id: uuid.UUID | None = None
                if item.email:
                    user = User(
                        id=uuid.uuid4(),
                        email=item.email.lower(),
                        full_name=f"Participant {item_code}",
                        hashed_password=get_password_hash("SyntaxLens@Temp2026!"),
                        role=UserRole.PARTICIPANT,
                        is_active=True,
                        must_change_password=True,
                    )
                    db.add(user)
                    await db.flush()
                    user_id = user.id

                p = Participant(
                    participant_id=uuid.uuid4(),
                    research_code=item_code,
                    user_id=user_id,
                    age=item.age,
                    age_band=item.age_band,
                    mother_tongue=item.mother_tongue,
                    school_medium=item.school_medium,
                    country=item.country,
                    state=item.state,
                    city=item.city,
                    study_group=StudyGroup(item.study_group),
                    is_group_blinded=settings.BLIND_STUDY_GROUP_FROM_PARTICIPANTS,
                    is_active=True,
                    is_withdrawn=False,
                    onboarding_completed=False,
                    onboarding_step="consent",
                )
                db.add(p)

            await db.flush()

            # Audit Log
            await audit_service.log_event(
                db=db,
                action="participant_bulk_import",
                actor_id=actor_id,
                role=actor_role,
                record_type="cohort",
                record_id="bulk_import",
                outcome="success",
                ip_hash=ip_hash,
                user_agent=user_agent,
                details={
                    "imported_count": len(valid_rows),
                    "rejected_count": len(rejected_rows),
                },
            )

        return CSVImportResult(
            dry_run=dry_run,
            total_rows=total_rows,
            valid_count=len(valid_rows),
            rejected_count=len(rejected_rows),
            duplicate_count=len(duplicates_found),
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
            duplicates_found=duplicates_found,
            can_commit=can_commit,
        )

    async def update_status(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
        is_active: bool,
        actor_id: uuid.UUID | None = None,
        actor_role: str = "researcher_admin",
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> Participant:
        stmt = select(Participant).where(Participant.participant_id == participant_id)
        participant = (await db.execute(stmt)).scalar_one_or_none()
        if not participant:
            raise ValueError(f"Participant with ID {participant_id} not found.")

        participant.is_active = is_active
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="participant_status_changed",
            actor_id=actor_id,
            role=actor_role,
            record_type="participant",
            record_id=str(participant_id),
            outcome="success",
            ip_hash=ip_hash,
            user_agent=user_agent,
            details={"is_active": is_active, "research_code": participant.research_code},
        )
        return participant

    async def assign_group(
        self,
        db: AsyncSession,
        participant_id: uuid.UUID,
        study_group: StudyGroup,
        actor_id: uuid.UUID | None = None,
        actor_role: str = "researcher_admin",
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> Participant:
        stmt = select(Participant).where(Participant.participant_id == participant_id)
        participant = (await db.execute(stmt)).scalar_one_or_none()
        if not participant:
            raise ValueError(f"Participant with ID {participant_id} not found.")

        old_group = participant.study_group
        participant.study_group = study_group
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="participant_group_assigned",
            actor_id=actor_id,
            role=actor_role,
            record_type="participant",
            record_id=str(participant_id),
            outcome="success",
            ip_hash=ip_hash,
            user_agent=user_agent,
            details={
                "previous_group": old_group.value,
                "assigned_group": study_group.value,
                "research_code": participant.research_code,
            },
        )
        return participant


participant_service = ParticipantService()
