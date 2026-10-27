"""Research Configuration, Versioning, and Freezing Engine (SRS FR-05, FR-08, FR-20).

NON-NEGOTIABLE RESEARCH INTEGRITY RULES:
- Rubrics, prompts, scoring rules and topic banks are versioned and FROZEN per assessment period.
- Assessments always record the exact versions used.
- Once frozen, records are strictly immutable.
- Topic assignment is reproducible from its seed.
"""

import difflib
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assessment import AssessmentTask
from app.models.config import (
    AssessmentPeriod,
    LifecycleState,
    PromptRole,
    PromptVersion,
    RubricVersion,
)
from app.services.audit import audit_service


# --- DTOs ---

class RubricCategoryDef(BaseModel):
    code: str
    name: str
    definition: str
    assessable_criteria: str
    variation_rules: str
    examples: list[dict[str, str]]
    is_expanded: bool = False


class RubricInput(BaseModel):
    version_code: str
    name: str
    description: str | None = None
    categories: list[RubricCategoryDef]
    counting_rules: str
    word_counting_rules: str
    change_notes: str | None = None


class PromptInput(BaseModel):
    prompt_role: PromptRole
    version_code: str
    name: str
    prompt_template: str
    output_schema_version: str = "json-schema-v1.0"
    output_schema_json: str
    change_notes: str | None = None


class PeriodInput(BaseModel):
    period_code: str
    name: str
    description: str | None = None
    rubric_version_code: str
    pre_prompt_version_code: str
    tutor_prompt_version_code: str
    post_prompt_version_code: str
    start_date: datetime
    end_date: datetime | None = None
    change_notes: str | None = None


class TaskInput(BaseModel):
    title: str
    prompt_text: str
    equivalence_group: str
    task_type: str = "any"  # pre, post, any
    difficulty_level: str = "standard_b1"
    prep_time_seconds: int = 30
    duration_seconds: int = 60
    rubric_version: str = "v1.0-jam-phd"


# --- Default Mock-Friendly Research Seed Data ---

DEFAULT_8_CATEGORIES: list[dict[str, Any]] = [
    {
        "code": "TNS",
        "name": "Tense and Aspect",
        "definition": "Incorrect verb inflection, auxiliary-verb mismatch in progressive/perfective aspect, or past/present inconsistency in narrative context.",
        "assessable_criteria": "Deviations where finite verb morphology does not match temporal frame or standard aspectual semantics.",
        "variation_rules": "Statistically common Indian English habitual progressives (e.g. 'I am knowing') are tagged as acceptable regional variation unless causing severe semantic ambiguity.",
        "examples": [
            {"phrase": "Yesterday he go to market", "correction": "Yesterday he went to market", "explanation": "Simple past required."},
            {"phrase": "She has saw the movie", "correction": "She has seen the movie", "explanation": "Past participle 'seen' required with 'has'."}
        ],
        "is_expanded": False
    },
    {
        "code": "SVA",
        "name": "Subject-Verb Agreement",
        "definition": "Mismatch between the grammatical number/person of the subject noun phrase and the finite verb form.",
        "assessable_criteria": "Third-person singular -s omission or erroneous plural inflection on singular subjects.",
        "variation_rules": "Agreement with collective nouns (e.g. 'the staff is/are') follows standard variation rules.",
        "examples": [
            {"phrase": "She know the answer", "correction": "She knows the answer", "explanation": "Third-person singular subject requires -s."},
            {"phrase": "The students is studying", "correction": "The students are studying", "explanation": "Plural subject requires 'are'."}
        ],
        "is_expanded": False
    },
    {
        "code": "WO",
        "name": "Word Order",
        "definition": "Non-standard constituent placement, incorrect inversion in wh- and polar questions, or misplaced adverbs.",
        "assessable_criteria": "Syntactic positioning deviations departing from Canonical SVO or inversion rules.",
        "variation_rules": "Topicalization common in Indian English ('Tomorrow only we will go') evaluated with variation tag.",
        "examples": [
            {"phrase": "Why you are late?", "correction": "Why are you late?", "explanation": "Subject-auxiliary inversion required in interrogatives."},
            {"phrase": "Always she is working", "correction": "She is always working", "explanation": "Frequency adverb belongs between auxiliary and main verb."}
        ],
        "is_expanded": False
    },
    {
        "code": "AUX",
        "name": "Auxiliary Usage",
        "definition": "Omission, redundancy, or incorrect selection of modal, aspectual, or passive auxiliaries.",
        "assessable_criteria": "Missing copula 'be', double modals, or incorrect do-support.",
        "variation_rules": "Standard do-support omissions in colloquial speed tagged under standard confidence thresholds.",
        "examples": [
            {"phrase": "She very happy today", "correction": "She is very happy today", "explanation": "Copular 'is' is required."},
            {"phrase": "He must can do it", "correction": "He must be able to do it", "explanation": "Double modals prohibited in standard syntax."}
        ],
        "is_expanded": False
    },
    {
        "code": "ART",
        "name": "Articles and Determiners",
        "definition": "Omission, redundant insertion, or incorrect substitution of definite (the), indefinite (a/an), or zero articles.",
        "assessable_criteria": "Deviations in countability and reference specification.",
        "variation_rules": "Subtle generic reference variations in Indian English are labeled as acceptable regional variation.",
        "examples": [
            {"phrase": "I bought car yesterday", "correction": "I bought a car yesterday", "explanation": "Singular countable noun requires determiner."},
            {"phrase": "She is studying the mathematics", "correction": "She is studying mathematics", "explanation": "Uncountable academic field takes zero article."}
        ],
        "is_expanded": False
    },
    {
        "code": "PREP",
        "name": "Prepositions",
        "definition": "Incorrect selection, insertion, or omission of dependent or spatial/temporal prepositions.",
        "assessable_criteria": "Phrasal verb particle errors and prepositional complementation deviations.",
        "variation_rules": "Indian English prepositional extensions (e.g. 'discuss about', 'order for') are flagged as regional usage.",
        "examples": [
            {"phrase": "He is good in mathematics", "correction": "He is good at mathematics", "explanation": "Adjective 'good' takes 'at' for skills."},
            {"phrase": "We arrived to the station", "correction": "We arrived at the station", "explanation": "Point of arrival takes 'at'."}
        ],
        "is_expanded": False
    },
    {
        "code": "PRO",
        "name": "Pronoun Usage",
        "definition": "Errors in pronoun case, number, gender agreement, relative pronoun selection, or redundant resumptive pronouns.",
        "assessable_criteria": "Subject vs object case confusion, reflexive errors, or relative clause mismatch.",
        "variation_rules": "Gender neutralization in fast speech checked against acoustic transcript confidence.",
        "examples": [
            {"phrase": "Me and him went there", "correction": "He and I went there", "explanation": "Subject pronouns required in compound subject position."},
            {"phrase": "The girl which helped me", "correction": "The girl who helped me", "explanation": "Personal relative pronoun 'who' required for human antecedent."}
        ],
        "is_expanded": False
    },
    {
        "code": "OTH",
        "name": "Other Syntactic Deviations",
        "definition": "Uncertain syntactic structures, multiple overlapping deviations, or idiosyncratic clause-level formations.",
        "assessable_criteria": "Catch-all category for structural irregularities not mapped to standard 7 classes.",
        "variation_rules": "Always triggers human reviewer verification in assessment pipeline.",
        "examples": [
            {"phrase": "Because of he was tired so he slept", "correction": "Because he was tired, he slept", "explanation": "Double conjunction 'because...so' creates comma splice."}
        ],
        "is_expanded": False
    }
]

DEFAULT_COUNTING_RULES = """### Syntactic Deviation Counting Rules (Frozen v1.0)
1. **Sentence Unit Scope**: Each candidate error is anchored to an exact token span. If a single clause contains multiple distinct syntactic errors (e.g., SVA and Tense), each is counted as a separate candidate error instance.
2. **Assessable Speech**: Only completed syntactic clauses spoken in English are counted in the denominator. Verbatim repetitions (stutters) and isolated discourse markers ('um', 'uh', 'you know') are excluded from syntactic error calculations.
3. **Acceptable Regional Variation**: Indian English standard syntactic variations (such as habitual progressive 'I am knowing' or phrasal extension 'discuss about') are recorded with the `acceptable_variation=True` flag and are NOT counted as syntactic deviations in research error rate formulas."""

DEFAULT_WORD_COUNTING_RULES = """### Word-Counting Rules (Pure Module v1.0)
1. **Word Definition**: A whitespace-separated sequence of alphabetic characters.
2. **Punctuation**: Stripped before tokenisation.
3. **Contractions**: Expanded or counted as single token according to transcript convention (standard: 'don\'t' = 1 word).
4. **Hyphenated Compounds**: Counted as a single compound word ('state-of-the-art' = 1 word).
5. **Speech Fillers**: Excluded from total word denominator ('um', 'uh', 'ah', 'mm')."""

DEFAULT_TOPIC_PAIRS = [
    {
        "pair_id": "pair_daily_routine",
        "difficulty": "standard_b1",
        "pre": {
            "title": "Daily Routine & College Life",
            "prompt_text": "Describe your daily routine on a typical college day, from morning until evening. Explain what activities you usually do and what you enjoy most about your schedule."
        },
        "post": {
            "title": "Weekend & Free Time Activities",
            "prompt_text": "Describe how you spend your typical weekend or holiday, from morning to evening. Explain the activities you enjoy doing with friends or family and how it differs from weekdays."
        }
    },
    {
        "pair_id": "pair_campus_memories",
        "difficulty": "standard_b1",
        "pre": {
            "title": "My College Campus & Favorite Places",
            "prompt_text": "Describe your college campus and your favorite places to study, relax, or meet friends. Explain why these spots are important to you."
        },
        "post": {
            "title": "My School Memories & Teachers",
            "prompt_text": "Describe your school days and the teachers or subjects that made a lasting impression on you. Explain why those memories stand out in your education."
        }
    },
    {
        "pair_id": "pair_interests_celebration",
        "difficulty": "standard_b1",
        "pre": {
            "title": "Favorite Hobby or Skill",
            "prompt_text": "Talk about a hobby, sport, or skill you enjoy practicing in your free time. Explain how you learned it and why you find it fulfilling."
        },
        "post": {
            "title": "Favorite Festival or Celebration",
            "prompt_text": "Talk about a festival or cultural celebration you enjoy attending. Explain how people prepare for it and why this celebration is meaningful to you."
        }
    }
]


class ResearchConfigService:
    # --- Rubrics ---

    async def get_rubrics(
        self,
        db: AsyncSession,
        status: LifecycleState | None = None,
    ) -> list[RubricVersion]:
        stmt = select(RubricVersion)
        if status:
            stmt = stmt.where(RubricVersion.status == status)
        result = await db.execute(stmt.order_by(RubricVersion.created_at.desc()))
        return list(result.scalars().all())

    async def get_rubric(self, db: AsyncSession, version_code: str) -> RubricVersion | None:
        result = await db.execute(select(RubricVersion).where(RubricVersion.version_code == version_code))
        return result.scalar_one_or_none()

    async def create_rubric(
        self,
        db: AsyncSession,
        input_data: RubricInput,
        created_by: uuid.UUID | None = None,
    ) -> RubricVersion:
        existing = await self.get_rubric(db, input_data.version_code)
        if existing:
            raise ValueError(f"Rubric version '{input_data.version_code}' already exists.")

        categories_json = json.dumps([c.model_dump() for c in input_data.categories])
        rubric = RubricVersion(
            rubric_id=uuid.uuid4(),
            version_code=input_data.version_code,
            name=input_data.name,
            description=input_data.description,
            categories_json=categories_json,
            counting_rules=input_data.counting_rules,
            word_counting_rules=input_data.word_counting_rules,
            status=LifecycleState.DRAFT,
            is_frozen=False,
            change_notes=input_data.change_notes,
            created_by=created_by,
        )
        db.add(rubric)
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="rubric_created",
            actor_id=created_by,
            role="researcher_admin",
            record_type="rubric_version",
            record_id=input_data.version_code,
            outcome="success",
            details={"version_code": input_data.version_code, "status": "draft"},
        )
        return rubric

    async def freeze_rubric(
        self,
        db: AsyncSession,
        version_code: str,
        actor_id: uuid.UUID | None = None,
    ) -> RubricVersion:
        rubric = await self.get_rubric(db, version_code)
        if not rubric:
            raise ValueError(f"Rubric version '{version_code}' not found.")
        if rubric.is_frozen or rubric.status == LifecycleState.FROZEN:
            raise ValueError(f"Rubric version '{version_code}' is already frozen and immutable.")

        now = datetime.now(timezone.utc)
        rubric.status = LifecycleState.FROZEN
        rubric.is_frozen = True
        rubric.frozen_at = now
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="rubric_frozen",
            actor_id=actor_id,
            role="researcher_admin",
            record_type="rubric_version",
            record_id=version_code,
            outcome="success",
            details={"version_code": version_code, "frozen_at": now.isoformat()},
        )
        return rubric

    # --- Prompts ---

    async def get_prompts(
        self,
        db: AsyncSession,
        role: PromptRole | None = None,
        prompt_role: PromptRole | None = None,
    ) -> list[PromptVersion]:
        stmt = select(PromptVersion)
        filter_role = role or prompt_role
        if filter_role:
            stmt = stmt.where(PromptVersion.prompt_role == filter_role)
        result = await db.execute(stmt.order_by(PromptVersion.created_at.desc()))
        return list(result.scalars().all())

    async def get_prompt(self, db: AsyncSession, version_code: str) -> PromptVersion | None:
        result = await db.execute(select(PromptVersion).where(PromptVersion.version_code == version_code))
        return result.scalar_one_or_none()

    async def create_prompt(
        self,
        db: AsyncSession,
        input_data: PromptInput,
        created_by: uuid.UUID | None = None,
    ) -> PromptVersion:
        existing = await self.get_prompt(db, input_data.version_code)
        if existing:
            raise ValueError(f"Prompt version '{input_data.version_code}' already exists.")

        prompt = PromptVersion(
            prompt_id=uuid.uuid4(),
            prompt_role=input_data.prompt_role,
            version_code=input_data.version_code,
            name=input_data.name,
            prompt_template=input_data.prompt_template,
            output_schema_version=input_data.output_schema_version,
            output_schema_json=input_data.output_schema_json,
            status=LifecycleState.DRAFT,
            is_frozen=False,
            change_notes=input_data.change_notes,
            created_by=created_by,
        )
        db.add(prompt)
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="prompt_created",
            actor_id=created_by,
            role="researcher_admin",
            record_type="prompt_version",
            record_id=input_data.version_code,
            outcome="success",
            details={"version_code": input_data.version_code, "role": input_data.prompt_role.value},
        )
        return prompt

    async def freeze_prompt(
        self,
        db: AsyncSession,
        version_code: str,
        actor_id: uuid.UUID | None = None,
    ) -> PromptVersion:
        prompt = await self.get_prompt(db, version_code)
        if not prompt:
            raise ValueError(f"Prompt version '{version_code}' not found.")
        if prompt.is_frozen or prompt.status == LifecycleState.FROZEN:
            raise ValueError(f"Prompt version '{version_code}' is already frozen and immutable.")

        now = datetime.now(timezone.utc)
        prompt.status = LifecycleState.FROZEN
        prompt.is_frozen = True
        prompt.frozen_at = now
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="prompt_frozen",
            actor_id=actor_id,
            role="researcher_admin",
            record_type="prompt_version",
            record_id=version_code,
            outcome="success",
            details={"version_code": version_code, "frozen_at": now.isoformat()},
        )
        return prompt

    # --- Topic Bank & Reproducible Assignment ---

    async def get_tasks(
        self,
        db: AsyncSession,
        equivalence_group: str | None = None,
        is_active: bool | None = None,
    ) -> list[AssessmentTask]:
        stmt = select(AssessmentTask)
        if equivalence_group:
            stmt = stmt.where(AssessmentTask.equivalence_group == equivalence_group)
        if is_active is not None:
            stmt = stmt.where(AssessmentTask.is_active == is_active)
        result = await db.execute(stmt.order_by(AssessmentTask.created_at.asc()))
        return list(result.scalars().all())

    async def assign_topic_pair(
        self,
        db: AsyncSession,
        participant_identifier: str,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Reproducibly assign pre and post tasks of equivalent difficulty from a recorded seed.

        Deterministic: Same participant identifier or explicit seed always assigns the exact same topic pair.
        """
        # Resolve deterministic integer seed
        if seed is None:
            # Deterministic SHA-256 hash of participant research code / UUID
            digest = hashlib.sha256(participant_identifier.encode("utf-8")).hexdigest()
            resolved_seed = int(digest[:8], 16)
        else:
            resolved_seed = seed

        # Fetch all distinct active equivalence groups
        stmt = (
            select(AssessmentTask.equivalence_group)
            .where(AssessmentTask.is_active == True)  # noqa: E712
            .distinct()
        )
        result = await db.execute(stmt)
        groups = sorted(result.scalars().all())

        if not groups:
            raise ValueError("No active assessment topic pairs found in topic bank.")

        # Deterministically select group using resolved seed
        selected_group = groups[resolved_seed % len(groups)]

        # Fetch tasks in that group
        tasks_stmt = select(AssessmentTask).where(
            AssessmentTask.equivalence_group == selected_group,
            AssessmentTask.is_active == True,  # noqa: E712
        ).order_by(AssessmentTask.created_at.asc())
        tasks = (await db.execute(tasks_stmt)).scalars().all()

        if len(tasks) < 2:
            raise ValueError(
                f"Equivalence group '{selected_group}' requires at least 2 paired tasks (found {len(tasks)})."
            )

        # First task = Pre, Second task = Post
        pre_task = tasks[0]
        post_task = tasks[1]

        return {
            "seed": resolved_seed,
            "equivalence_group": selected_group,
            "pre_task": {
                "task_id": str(pre_task.task_id),
                "title": pre_task.title,
                "prompt_text": pre_task.prompt_text,
                "prep_time_seconds": pre_task.prep_time_seconds,
                "duration_seconds": pre_task.duration_seconds,
                "difficulty_level": pre_task.difficulty_level,
                "rubric_version": pre_task.rubric_version,
            },
            "post_task": {
                "task_id": str(post_task.task_id),
                "title": post_task.title,
                "prompt_text": post_task.prompt_text,
                "prep_time_seconds": post_task.prep_time_seconds,
                "duration_seconds": post_task.duration_seconds,
                "difficulty_level": post_task.difficulty_level,
                "rubric_version": post_task.rubric_version,
            },
        }

    # --- Diff Viewer Engine ---

    def compute_diff(
        self,
        base_text: str,
        target_text: str,
        base_label: str = "Base Version",
        target_label: str = "Target Version",
    ) -> dict[str, Any]:
        """Compute structured line diff between two versions."""
        base_lines = base_text.splitlines(keepends=True)
        target_lines = target_text.splitlines(keepends=True)

        diff_gen = difflib.unified_diff(
            base_lines,
            target_lines,
            fromfile=base_label,
            tofile=target_label,
        )
        unified_diff_str = "".join(diff_gen)

        additions = 0
        deletions = 0
        line_records = []

        diff_lines = unified_diff_str.splitlines()
        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
                line_records.append({"type": "add", "text": line[1:]})
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1
                line_records.append({"type": "delete", "text": line[1:]})
            elif line.startswith("@"):
                line_records.append({"type": "header", "text": line})
            else:
                line_records.append({"type": "context", "text": line})

        return {
            "unified_diff": unified_diff_str,
            "additions": additions,
            "deletions": deletions,
            "has_changes": additions > 0 or deletions > 0,
            "lines": line_records,
        }

    # --- Seed Mock-Friendly Baseline Defaults ---

    async def seed_defaults(self, db: AsyncSession) -> None:
        """Seed frozen v1.0 baseline rubric, prompt versions, and topic pairs."""
        now = datetime.now(timezone.utc)

        # 1. Rubric Version v1.0-jam-phd
        rubric_stmt = select(RubricVersion).where(RubricVersion.version_code == settings.DEFAULT_RUBRIC_VERSION)
        existing_rubric = (await db.execute(rubric_stmt)).scalar_one_or_none()
        if not existing_rubric:
            rubric = RubricVersion(
                rubric_id=uuid.uuid4(),
                version_code=settings.DEFAULT_RUBRIC_VERSION,
                name="Doctoral Baseline Spoken English Syntactic Rubric",
                description="8 core syntactic categories with counting rules and Indian English variation handling.",
                categories_json=json.dumps(DEFAULT_8_CATEGORIES),
                counting_rules=DEFAULT_COUNTING_RULES,
                word_counting_rules=DEFAULT_WORD_COUNTING_RULES,
                status=LifecycleState.FROZEN,
                is_frozen=True,
                change_notes="Initial baseline approved for doctoral research protocol.",
                approved_at=now,
                frozen_at=now,
            )
            db.add(rubric)

        # 2. Prompts for Three Roles (SRS §8)
        # Pre-test Prompt
        pre_stmt = select(PromptVersion).where(PromptVersion.version_code == "v1.0-pre-assessor")
        if not (await db.execute(pre_stmt)).scalar_one_or_none():
            p_pre = PromptVersion(
                prompt_id=uuid.uuid4(),
                prompt_role=PromptRole.PRE_TEST_ASSESSOR,
                version_code="v1.0-pre-assessor",
                name="Pre-Test Baseline Syntactic Assessor",
                prompt_template="Role: Neutral spoken-English syntax assessor. Transcribe faithfully and label candidate deviations with category, evidence, confidence, and review status.",
                output_schema_version="json-schema-v1.0",
                output_schema_json=json.dumps({"type": "object", "properties": {"deviations": {"type": "array"}}}),
                status=LifecycleState.FROZEN,
                is_frozen=True,
                change_notes="Baseline pre-test assessor prompt.",
                approved_at=now,
                frozen_at=now,
            )
            db.add(p_pre)

        # Tutor Prompt
        tutor_stmt = select(PromptVersion).where(PromptVersion.version_code == settings.DEFAULT_PROMPT_VERSION)
        if not (await db.execute(tutor_stmt)).scalar_one_or_none():
            p_tutor = PromptVersion(
                prompt_id=uuid.uuid4(),
                prompt_role=PromptRole.TUTOR,
                version_code=settings.DEFAULT_PROMPT_VERSION,
                name="AI Tutor Hint Ladder Progression",
                prompt_template="Role: Supportive conversational tutor. Use hint ladder: L0 quote, L1 hint, L2 rule cue, L3 reveal and new transfer check.",
                output_schema_version="json-schema-v1.0",
                output_schema_json=json.dumps({"type": "object", "properties": {"hint_level": {"type": "integer"}}}),
                status=LifecycleState.FROZEN,
                is_frozen=True,
                change_notes="Baseline tutor prompt enforcing hint ladder.",
                approved_at=now,
                frozen_at=now,
            )
            db.add(p_tutor)

        # Post-test Prompt
        post_stmt = select(PromptVersion).where(PromptVersion.version_code == "v1.0-post-assessor")
        if not (await db.execute(post_stmt)).scalar_one_or_none():
            p_post = PromptVersion(
                prompt_id=uuid.uuid4(),
                prompt_role=PromptRole.POST_TEST_ASSESSOR,
                version_code="v1.0-post-assessor",
                name="Post-Test Comparative Assessor",
                prompt_template="Role: Neutral post-test assessor. Assess independently using identical rubric conventions. Compare error rates against verified baseline.",
                output_schema_version="json-schema-v1.0",
                output_schema_json=json.dumps({"type": "object", "properties": {"comparison": {"type": "object"}}}),
                status=LifecycleState.FROZEN,
                is_frozen=True,
                change_notes="Baseline post-test assessor prompt.",
                approved_at=now,
                frozen_at=now,
            )
            db.add(p_post)

        # 3. Assessment Tasks (3 Equivalence Pairs)
        for pair in DEFAULT_TOPIC_PAIRS:
            pair_id = pair["pair_id"]
            # Pre task
            pre_t = pair["pre"]
            t_pre_stmt = select(AssessmentTask).where(AssessmentTask.title == pre_t["title"])
            if not (await db.execute(t_pre_stmt)).scalar_one_or_none():
                task_pre = AssessmentTask(
                    task_id=uuid.uuid4(),
                    title=pre_t["title"],
                    prompt_text=pre_t["prompt_text"],
                    equivalence_group=pair_id,
                    task_type="pre",
                    difficulty_level=pair["difficulty"],
                    rubric_version=settings.DEFAULT_RUBRIC_VERSION,
                    prep_time_seconds=30,
                    duration_seconds=60,
                    is_active=True,
                )
                db.add(task_pre)

            # Post task
            post_t = pair["post"]
            t_post_stmt = select(AssessmentTask).where(AssessmentTask.title == post_t["title"])
            if not (await db.execute(t_post_stmt)).scalar_one_or_none():
                task_post = AssessmentTask(
                    task_id=uuid.uuid4(),
                    title=post_t["title"],
                    prompt_text=post_t["prompt_text"],
                    equivalence_group=pair_id,
                    task_type="post",
                    difficulty_level=pair["difficulty"],
                    rubric_version=settings.DEFAULT_RUBRIC_VERSION,
                    prep_time_seconds=30,
                    duration_seconds=60,
                    is_active=True,
                )
                db.add(task_post)

        # 4. Assessment Period
        period_stmt = select(AssessmentPeriod).where(AssessmentPeriod.period_code == "period-2026-spring")
        if not (await db.execute(period_stmt)).scalar_one_or_none():
            period = AssessmentPeriod(
                period_id=uuid.uuid4(),
                period_code="period-2026-spring",
                name="Spring 2026 Doctoral Research Cohort",
                description="Active frozen assessment period with frozen v1.0 rubrics and prompts.",
                rubric_version_code=settings.DEFAULT_RUBRIC_VERSION,
                pre_prompt_version_code="v1.0-pre-assessor",
                tutor_prompt_version_code=settings.DEFAULT_PROMPT_VERSION,
                post_prompt_version_code="v1.0-post-assessor",
                status=LifecycleState.FROZEN,
                is_frozen=True,
                is_active=True,
                start_date=now,
                change_notes="Initial frozen study period.",
            )
            db.add(period)

        await db.flush()


config_service = ResearchConfigService()
