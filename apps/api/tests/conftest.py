"""Test Fixtures and Async SQLite Database Setup.

NON-NEGOTIABLE RULE 2:
Zero external API keys required.
Zero live external database required for test execution.
Uses schema_translate_map to dynamically map identity/research schemas to isolated in-memory test databases.
"""

import sys
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure apps/api is in sys.path
API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limiter
from app.core.security import get_password_hash
from app.core.session import session_store
from app.main import app

# Ensure tests use fast in-memory stores without waiting on Redis timeouts
settings.ENVIRONMENT = "testing"
session_store._redis_failed = True
rate_limiter._redis_failed = True
from app.models.assessment import (
    Assessment,
    AssessmentTask,
    AssessmentType,
    ReviewerAssignment,
)
from app.models.base import Base
from app.models.identity import User, UserRole
from app.models.practice import PracticeSession
from app.models.research import Participant, StudyGroup
from app.services.config import config_service

TEST_PASSWORD = "SyntaxLens@2026!Secure"
CACHED_HASHED_PASSWORD: str | None = None


def get_cached_test_password() -> str:
    global CACHED_HASHED_PASSWORD
    if CACHED_HASHED_PASSWORD is None:
        CACHED_HASHED_PASSWORD = get_password_hash(TEST_PASSWORD)
    return CACHED_HASHED_PASSWORD


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def test_engine() -> AsyncGenerator[Any, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        execution_options={"schema_translate_map": {"identity": None, "research": None}},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Attach append-only triggers to audit_logs and consents for in-memory SQLite
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_audit_no_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Records in audit_logs are strictly append-only.');
            END;
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_audit_no_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Records in audit_logs are strictly append-only.');
            END;
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_consents_no_update
            BEFORE UPDATE ON consents
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Records in consents are strictly append-only.');
            END;
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_consents_no_delete
            BEFORE DELETE ON consents
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Records in consents are strictly append-only.');
            END;
        """))

        # Attach frozen immutability triggers on rubric_versions, prompt_versions, assessment_periods
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_rubric_frozen_update
            BEFORE UPDATE ON rubric_versions
            WHEN OLD.is_frozen = 1 OR OLD.status = 'frozen'
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Frozen rubric versions are strictly immutable.');
            END;
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_rubric_frozen_delete
            BEFORE DELETE ON rubric_versions
            WHEN OLD.is_frozen = 1 OR OLD.status = 'frozen'
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Frozen rubric versions cannot be deleted.');
            END;
        """))

        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_prompt_frozen_update
            BEFORE UPDATE ON prompt_versions
            WHEN OLD.is_frozen = 1 OR OLD.status = 'frozen'
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Frozen prompt versions are strictly immutable.');
            END;
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_prompt_frozen_delete
            BEFORE DELETE ON prompt_versions
            WHEN OLD.is_frozen = 1 OR OLD.status = 'frozen'
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Frozen prompt versions cannot be deleted.');
            END;
        """))

        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_period_frozen_update
            BEFORE UPDATE ON assessment_periods
            WHEN OLD.is_frozen = 1 OR OLD.status = 'frozen'
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Frozen assessment periods are strictly immutable.');
            END;
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trg_period_frozen_delete
            BEFORE DELETE ON assessment_periods
            WHEN OLD.is_frozen = 1 OR OLD.status = 'frozen'
            BEGIN
                SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Frozen assessment periods cannot be deleted.');
            END;
        """))

    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client overriding the get_db dependency with test_session."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def seeded_data(test_session: AsyncSession) -> dict[str, Any]:
    """Seed test users, participants, tasks, and assessments for RBAC verification."""
    hashed_pw = get_cached_test_password()

    # 1. Researcher Admin
    admin = User(
        id=uuid.uuid4(),
        email="admin@syntaxlens.edu",
        full_name="Lead Researcher Admin",
        hashed_password=hashed_pw,
        role=UserRole.RESEARCHER_ADMIN,
        is_active=True,
        must_change_password=False,
    )

    # 2. Participant A
    user_a = User(
        id=uuid.uuid4(),
        email="participant_a@syntaxlens.edu",
        full_name="Participant Alpha",
        hashed_password=hashed_pw,
        role=UserRole.PARTICIPANT,
        is_active=True,
        must_change_password=False,
    )
    participant_a = Participant(
        participant_id=uuid.uuid4(),
        research_code="SL-2026-001",
        user_id=user_a.id,
        mother_tongue="Marathi",
        school_medium="English",
        country="India",
        study_group=StudyGroup.INTERVENTION,
        current_consent_version=settings.CURRENT_CONSENT_VERSION,
        is_active=True,
        is_withdrawn=False,
    )

    # 3. Participant B
    user_b = User(
        id=uuid.uuid4(),
        email="participant_b@syntaxlens.edu",
        full_name="Participant Beta",
        hashed_password=hashed_pw,
        role=UserRole.PARTICIPANT,
        is_active=True,
        must_change_password=False,
    )
    participant_b = Participant(
        participant_id=uuid.uuid4(),
        research_code="SL-2026-002",
        user_id=user_b.id,
        mother_tongue="Hindi",
        school_medium="English",
        country="India",
        study_group=StudyGroup.CONTROL,
        current_consent_version=settings.CURRENT_CONSENT_VERSION,
        is_active=True,
        is_withdrawn=False,
    )

    # 4. Reviewer 1 (Will be assigned Assessment A1)
    rev_1 = User(
        id=uuid.uuid4(),
        email="reviewer_1@syntaxlens.edu",
        full_name="Reviewer One",
        hashed_password=hashed_pw,
        role=UserRole.REVIEWER,
        is_active=True,
        must_change_password=False,
    )

    # 5. Reviewer 2 (Unassigned to any assessment)
    rev_2 = User(
        id=uuid.uuid4(),
        email="reviewer_2@syntaxlens.edu",
        full_name="Reviewer Two",
        hashed_password=hashed_pw,
        role=UserRole.REVIEWER,
        is_active=True,
        must_change_password=False,
    )

    # 6. Task
    task = AssessmentTask(
        task_id=uuid.uuid4(),
        title="College Day Routine",
        prompt_text="Describe your college routine.",
        rubric_version="v1.0-jam-phd",
    )

    # 7. Assessment A1 (Belongs to Participant A)
    assessment_a = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant_a.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/p_a/assessment_1.wav",
        transcript="I am go to college everyday.",
        word_count=6,
        stt_version="mock-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-v1",
    )

    # 8. Assessment B1 (Belongs to Participant B)
    assessment_b = Assessment(
        assessment_id=uuid.uuid4(),
        participant_id=participant_b.participant_id,
        task_id=task.task_id,
        assessment_type=AssessmentType.PRE,
        audio_key="audio/p_b/assessment_1.wav",
        transcript="She do not know the answer.",
        word_count=6,
        stt_version="mock-v1",
        rubric_version="v1.0-jam-phd",
        model_version="mock-v1",
    )

    # 9. Reviewer Assignment: Assign Assessment A1 to Reviewer 1
    assignment = ReviewerAssignment(
        assignment_id=uuid.uuid4(),
        reviewer_id=rev_1.id,
        assessment_id=assessment_a.assessment_id,
        assigned_by=admin.id,
        status="active",
    )

    # 10. Practice Session for Participant A
    practice_session = PracticeSession(
        session_id=uuid.uuid4(),
        participant_id=participant_a.participant_id,
        tutor_prompt_version="v1.0-tutor",
        status="completed",
        active_duration_seconds=300,
    )

    test_session.add_all([
        admin, user_a, participant_a, user_b, participant_b,
        rev_1, rev_2, task, assessment_a, assessment_b, assignment,
        practice_session
    ])
    await test_session.commit()
    await config_service.seed_defaults(test_session)
    await test_session.commit()

    return {
        "admin": admin,
        "user_a": user_a,
        "participant_a": participant_a,
        "user_b": user_b,
        "participant_b": participant_b,
        "rev_1": rev_1,
        "rev_2": rev_2,
        "task": task,
        "assessment_a": assessment_a,
        "assessment_b": assessment_b,
        "assignment": assignment,
        "practice_session": practice_session,
    }


async def create_auth_headers_for(
    user: User,
    participant: Participant | None = None,
    must_change_password: bool = False,
) -> dict[str, str]:
    """Helper creating a valid session and returning auth headers (Cookie and X-CSRF-Token)."""
    session_id, csrf_token = await session_store.create_session(
        user_id=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        must_change_password=must_change_password,
        participant_id=participant.participant_id if participant else None,
        participant_code=participant.research_code if participant else None,
    )
    return {
        "Cookie": f"syntaxlens_session={session_id}; syntaxlens_csrf={csrf_token}",
        "X-CSRF-Token": csrf_token,
    }
