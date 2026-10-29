"""SyntaxLens Database Seeding Module.

Seeds initial frozen research rubrics, prompt versions, topic bank, and baseline research accounts.
Uses SQLAlchemy sync session to ensure cross-database compatibility (PostgreSQL & SQLite).
"""

import json
import uuid
from datetime import UTC, datetime

from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import SyncSessionLocal
from app.models.assessment import AssessmentTask
from app.models.config import (
    AssessmentPeriod,
    LifecycleState,
    PromptRole,
    PromptVersion,
    RubricVersion,
)
from app.models.identity import User, UserRole
from app.models.research import Participant, StudyGroup
from app.services.config import (
    DEFAULT_8_CATEGORIES,
    DEFAULT_COUNTING_RULES,
    DEFAULT_TOPIC_PAIRS,
    DEFAULT_WORD_COUNTING_RULES,
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def seed() -> None:
    print("Starting SyntaxLens seed procedure...")
    session = SyncSessionLocal()
    try:
        now = datetime.now(UTC)

        # 1. Rubric Version v1.0-jam-phd
        existing_rubric = (
            session.query(RubricVersion)
            .filter(RubricVersion.version_code == settings.DEFAULT_RUBRIC_VERSION)
            .first()
        )
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
            session.add(rubric)

        # 2. Prompts
        pre_prompt = (
            session.query(PromptVersion)
            .filter(PromptVersion.version_code == "v1.0-pre-assessor")
            .first()
        )
        if not pre_prompt:
            session.add(
                PromptVersion(
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
            )

        tutor_prompt = (
            session.query(PromptVersion)
            .filter(PromptVersion.version_code == settings.DEFAULT_PROMPT_VERSION)
            .first()
        )
        if not tutor_prompt:
            session.add(
                PromptVersion(
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
            )

        # 3. Assessment Tasks (Topic Bank Pairs)
        for pair in DEFAULT_TOPIC_PAIRS:
            pair_id = pair["pair_id"]
            pre_t = pair["pre"]
            if not session.query(AssessmentTask).filter(AssessmentTask.title == pre_t["title"]).first():
                session.add(
                    AssessmentTask(
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
                )

            post_t = pair["post"]
            if not session.query(AssessmentTask).filter(AssessmentTask.title == post_t["title"]).first():
                session.add(
                    AssessmentTask(
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
                )

        # 4. Assessment Period
        if not session.query(AssessmentPeriod).filter(AssessmentPeriod.period_code == "period-2026-spring").first():
            session.add(
                AssessmentPeriod(
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
            )

        session.commit()

        # 5. Seed Users
        hashed_pw = pwd_context.hash("SyntaxLens@2026!")

        users_data = [
            ("researcher@syntaxlens.edu", "Lead Researcher", UserRole.RESEARCHER_ADMIN),
            ("reviewer@syntaxlens.edu", "Independent Reviewer", UserRole.REVIEWER),
            ("student1@syntaxlens.edu", "Student Participant 001", UserRole.PARTICIPANT),
        ]

        for email, full_name, role in users_data:
            existing = session.query(User).filter(User.email == email).first()
            if not existing:
                u = User(
                    id=uuid.uuid4(),
                    email=email,
                    full_name=full_name,
                    hashed_password=hashed_pw,
                    role=role,
                    is_active=True,
                    must_change_password=False,
                )
                session.add(u)
                session.commit()

                if role == UserRole.PARTICIPANT:
                    if not session.query(Participant).filter(Participant.user_id == u.id).first():
                        session.add(
                            Participant(
                                participant_id=uuid.uuid4(),
                                user_id=u.id,
                                research_code="SL-2026-001",
                                study_group=StudyGroup.INTERVENTION,
                                age=21,
                                mother_tongue="Marathi",
                                school_medium="English",
                                country="India",
                                state="Maharashtra",
                                city="Pune",
                                is_active=True,
                            )
                        )
                        session.commit()

        print("Seeding completed successfully.")
    except Exception as e:
        session.rollback()
        print(f"Seed encountered notice: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
