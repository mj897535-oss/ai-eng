"""Research Integrity Test Suite: Database-Enforced Immutability.

NON-NEGOTIABLE RULE 3:
Original AI outputs, transcripts, baseline assessments, consents, and audit logs
are APPEND-ONLY. Enforced with database triggers, plus automated tests that prove
updates and deletes fail.
"""

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError, OperationalError
from sqlalchemy.orm import sessionmaker


# Setup in-memory SQLite with schema translation and native immutability triggers
@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)

    with engine.begin() as conn:
        # Create tables without schema prefixes for SQLite compatibility
        conn.execute(text("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                last_login_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE participants (
                participant_id TEXT PRIMARY KEY,
                research_code TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(id),
                age INTEGER,
                mother_tongue TEXT NOT NULL,
                school_medium TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT 'India',
                state TEXT,
                city TEXT,
                study_group TEXT NOT NULL,
                is_withdrawn INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE consents (
                consent_id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL REFERENCES participants(participant_id),
                consent_version TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE assessment_tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                prep_time_seconds INTEGER NOT NULL,
                difficulty_level TEXT NOT NULL,
                rubric_version TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE assessments (
                assessment_id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL REFERENCES participants(participant_id),
                task_id TEXT NOT NULL REFERENCES assessment_tasks(task_id),
                assessment_type TEXT NOT NULL,
                audio_key TEXT NOT NULL,
                transcript TEXT NOT NULL,
                word_count INTEGER NOT NULL,
                stt_version TEXT NOT NULL,
                rubric_version TEXT NOT NULL,
                model_version TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE error_annotations (
                annotation_id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL REFERENCES assessments(assessment_id),
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                start_time_ms INTEGER,
                end_time_ms INTEGER,
                candidate_error TEXT NOT NULL,
                suggested_correction TEXT NOT NULL,
                category_code TEXT NOT NULL,
                explanation TEXT NOT NULL,
                confidence REAL NOT NULL,
                ai_status TEXT NOT NULL,
                model_version TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE reviewer_decisions (
                decision_id TEXT PRIMARY KEY,
                annotation_id TEXT NOT NULL REFERENCES error_annotations(annotation_id),
                reviewer_id TEXT NOT NULL REFERENCES users(id),
                decision TEXT NOT NULL,
                edited_category TEXT,
                edited_correction TEXT,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE audit_logs (
                log_id TEXT PRIMARY KEY,
                actor_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Attach Immutability Triggers to Append-Only tables
        append_only_tables = ["consents", "assessments", "error_annotations", "audit_logs"]
        for tbl in append_only_tables:
            conn.execute(text(f"""
                CREATE TRIGGER trg_{tbl}_no_update
                BEFORE UPDATE ON {tbl}
                BEGIN
                    SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Records in {tbl} are strictly append-only and cannot be updated.');
                END;
            """))
            conn.execute(text(f"""
                CREATE TRIGGER trg_{tbl}_no_delete
                BEFORE DELETE ON {tbl}
                BEGIN
                    SELECT RAISE(FAIL, 'RESEARCH INTEGRITY VIOLATION: Records in {tbl} are strictly append-only and cannot be deleted.');
                END;
            """))

    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed baseline user & participant
    u_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    t_id = str(uuid.uuid4())
    session.execute(text(f"""
        INSERT INTO users (id, email, full_name, hashed_password, role)
        VALUES ('{u_id}', 'student1@example.com', 'Student One', 'hash', 'student');
    """))
    session.execute(text(f"""
        INSERT INTO participants (participant_id, research_code, user_id, mother_tongue, school_medium, study_group)
        VALUES ('{p_id}', 'SL-TEST-001', '{u_id}', 'Marathi', 'English', 'intervention');
    """))
    session.execute(text(f"""
        INSERT INTO assessment_tasks (task_id, title, prompt_text, duration_seconds, prep_time_seconds, difficulty_level, rubric_version)
        VALUES ('{t_id}', 'Daily Routine', 'Talk about your daily routine.', 60, 30, 'standard', 'v1.0');
    """))
    session.commit()

    session.u_id = u_id
    session.p_id = p_id
    session.t_id = t_id

    yield session
    session.close()


def test_consent_immutability(db_session):
    """Prove consents cannot be updated or deleted."""
    c_id = str(uuid.uuid4())
    db_session.execute(text(f"""
        INSERT INTO consents (consent_id, participant_id, consent_version, status)
        VALUES ('{c_id}', '{db_session.p_id}', 'v1.0', 'consented');
    """))
    db_session.commit()

    # Attempt UPDATE -> MUST FAIL
    with pytest.raises((DatabaseError, OperationalError)) as exc_info:
        db_session.execute(text(f"UPDATE consents SET status = 'withdrawn' WHERE consent_id = '{c_id}';"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_info.value)

    # Attempt DELETE -> MUST FAIL
    with pytest.raises((DatabaseError, OperationalError)) as exc_info:
        db_session.execute(text(f"DELETE FROM consents WHERE consent_id = '{c_id}';"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_info.value)


def test_assessment_immutability(db_session):
    """Prove assessments (transcripts, word count) cannot be updated or deleted."""
    a_id = str(uuid.uuid4())
    db_session.execute(text(f"""
        INSERT INTO assessments (assessment_id, participant_id, task_id, assessment_type, audio_key, transcript, word_count, stt_version, rubric_version, model_version)
        VALUES ('{a_id}', '{db_session.p_id}', '{db_session.t_id}', 'pre', 'audio/pre_01.wav', 'He go to college', 4, 'mock-stt', 'v1.0', 'mock-v1');
    """))
    db_session.commit()

    # Attempt UPDATE transcript -> MUST FAIL
    with pytest.raises((DatabaseError, OperationalError)) as exc_info:
        db_session.execute(text(f"UPDATE assessments SET transcript = 'He goes to college' WHERE assessment_id = '{a_id}';"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_info.value)

    # Attempt DELETE -> MUST FAIL
    with pytest.raises((DatabaseError, OperationalError)) as exc_info:
        db_session.execute(text(f"DELETE FROM assessments WHERE assessment_id = '{a_id}';"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_info.value)


def test_error_annotation_immutability_and_separate_review(db_session):
    """Prove AI candidate errors are immutable and reviewer decisions are separate rows."""
    a_id = str(uuid.uuid4())
    ann_id = str(uuid.uuid4())
    db_session.execute(text(f"""
        INSERT INTO assessments (assessment_id, participant_id, task_id, assessment_type, audio_key, transcript, word_count, stt_version, rubric_version, model_version)
        VALUES ('{a_id}', '{db_session.p_id}', '{db_session.t_id}', 'pre', 'audio/pre_02.wav', 'He go to college', 4, 'mock-stt', 'v1.0', 'mock-v1');
    """))
    db_session.execute(text(f"""
        INSERT INTO error_annotations (annotation_id, assessment_id, start_char, end_char, candidate_error, suggested_correction, category_code, explanation, confidence, ai_status, model_version)
        VALUES ('{ann_id}', '{a_id}', 3, 5, 'go', 'goes', 'SVA', 'Subject-verb agreement error', 0.95, 'candidate', 'mock-v1');
    """))
    db_session.commit()

    # Attempt UPDATE error annotation -> MUST FAIL
    with pytest.raises((DatabaseError, OperationalError)) as exc_info:
        db_session.execute(text(f"UPDATE error_annotations SET category_code = 'TNS' WHERE annotation_id = '{ann_id}';"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_info.value)

    # Attempt DELETE error annotation -> MUST FAIL
    with pytest.raises((DatabaseError, OperationalError)) as exc_info:
        db_session.execute(text(f"DELETE FROM error_annotations WHERE annotation_id = '{ann_id}';"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_info.value)

    # Add Reviewer Decision in separate row -> MUST SUCCEED
    dec_id = str(uuid.uuid4())
    db_session.execute(text(f"""
        INSERT INTO reviewer_decisions (decision_id, annotation_id, reviewer_id, decision, notes)
        VALUES ('{dec_id}', '{ann_id}', '{db_session.u_id}', 'accepted', 'Verified SVA error.');
    """))
    db_session.commit()

    # Verify original AI annotation is preserved intact
    row = db_session.execute(text(f"SELECT category_code, candidate_error FROM error_annotations WHERE annotation_id = '{ann_id}';")).fetchone()
    assert row[0] == "SVA"
    assert row[1] == "go"


def test_audit_log_immutability(db_session):
    """Prove research audit logs cannot be updated or deleted."""
    log_id = str(uuid.uuid4())
    db_session.execute(text(f"""
        INSERT INTO audit_logs (log_id, actor_id, action, resource_type, resource_id, details)
        VALUES ('{log_id}', '{db_session.u_id}', 'AUDIO_UPLOAD', 'assessment', 'test-123', 'Audio uploaded');
    """))
    db_session.commit()

    # Attempt UPDATE -> MUST FAIL
    with pytest.raises((DatabaseError, OperationalError)) as exc_info:
        db_session.execute(text(f"UPDATE audit_logs SET details = 'tampered' WHERE log_id = '{log_id}';"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_info.value)

    # Attempt DELETE -> MUST FAIL
    with pytest.raises((DatabaseError, OperationalError)) as exc_info:
        db_session.execute(text(f"DELETE FROM audit_logs WHERE log_id = '{log_id}';"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_info.value)
