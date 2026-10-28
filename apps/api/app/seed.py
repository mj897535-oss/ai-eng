"""SyntaxLens Database Seeding Module.

Seeds initial frozen research rubrics, prompt versions, topic bank, and baseline research accounts.
Can be executed as a module (`python -m app.seed`) or imported into startup scripts.
"""

import json
import uuid

from passlib.context import CryptContext
from sqlalchemy import text

from app.core.database import sync_engine

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def seed():
    print("Starting SyntaxLens seed procedure...")

    with sync_engine.begin() as conn:
        # 1. Seed Frozen Rubric Version
        rubric_id = str(uuid.uuid4())
        taxonomy = {
            "categories": [
                {"code": "TNS", "name": "Tense and Aspect", "description": "Deviations in verb tense or aspectual markers."},
                {"code": "SVA", "name": "Subject-Verb Agreement", "description": "Agreement between subject person/number and verb form."},
                {"code": "WO", "name": "Word Order", "description": "Syntactic positioning of clausal or phrasal elements."},
                {"code": "AUX", "name": "Auxiliary Usage", "description": "Omission, substitution, or redundant insertion of auxiliary verbs."},
                {"code": "ART", "name": "Article Usage", "description": "Definite, indefinite, or zero article deviations."},
                {"code": "PREP", "name": "Preposition Choice", "description": "Non-standard preposition selection or omission."},
                {"code": "PRO", "name": "Pronoun Reference", "description": "Case, gender, number, or relative pronoun mismatch."},
                {"code": "OTH", "name": "Other / Uncertain", "description": "Syntactic deviations requiring specialist review or acceptable regional variation."}
            ]
        }
        conn.execute(text("""
            INSERT INTO research.rubric_versions (rubric_id, version_code, name, description, taxonomy_json, is_frozen)
            VALUES (:id, 'v1.0-jam-phd', 'PhD Spoken English Syntax Rubric v1.0', 'Standardized 8-category syntactic taxonomy for Indian speakers of English.', :tax, true)
            ON CONFLICT (version_code) DO NOTHING;
        """), {"id": rubric_id, "tax": json.dumps(taxonomy)})

        # 2. Seed Prompt Versions
        conn.execute(text("""
            INSERT INTO research.prompt_versions (prompt_id, prompt_type, version_code, prompt_template, is_frozen)
            VALUES
            (:id1, 'pre_test', 'v1.0-jam-pre', 'Neutral assessor. Transcribe faithfully and label syntactic candidate errors.', true),
            (:id2, 'tutor', 'v1.0-tutor-ladder', 'Supportive conversational tutor. Implement 4-step hint ladder (L0 quote, L1 hint, L2 rule, L3 reveal + transfer).', true),
            (:id3, 'post_test', 'v1.0-jam-post', 'Neutral assessor. Independent post-test evaluation using identical rubric version.', true)
            ON CONFLICT (version_code) DO NOTHING;
        """), {"id1": str(uuid.uuid4()), "id2": str(uuid.uuid4()), "id3": str(uuid.uuid4())})

        # 3. Seed Assessment Task Bank
        tasks = [
            ("A Memorable Journey", "Describe a memorable journey you took recently. Talk about where you went, how you travelled, and why it was special to you.", 60, 30),
            ("My Typical College Day", "Describe your daily routine at college or work from morning until evening. Include your classes, activities, and interactions with peers.", 60, 30),
            ("Role of Technology in Everyday Life", "Share your thoughts on how smartphones and technology impact daily communication in modern life.", 60, 30),
        ]
        for title, prompt, duration, prep in tasks:
            conn.execute(text("""
                INSERT INTO research.assessment_tasks (task_id, title, prompt_text, duration_seconds, prep_time_seconds, difficulty_level, rubric_version)
                VALUES (:id, :title, :prompt, :dur, :prep, 'standard', 'v1.0-jam-phd')
                ON CONFLICT DO NOTHING;
            """), {"id": str(uuid.uuid4()), "title": title, "prompt": prompt, "dur": duration, "prep": prep})

        # 4. Seed Research Accounts
        # Password for all initial seed accounts: SyntaxLens@2026!
        hashed_pw = hash_password("SyntaxLens@2026!")

        researcher_id = str(uuid.uuid4())
        reviewer_id = str(uuid.uuid4())
        student_id = str(uuid.uuid4())

        conn.execute(text("""
            INSERT INTO identity.users (id, email, full_name, hashed_password, role, is_active)
            VALUES
            (:r_id, 'researcher@syntaxlens.edu', 'Lead Researcher', :pw, 'researcher', true),
            (:rev_id, 'reviewer@syntaxlens.edu', 'Independent Reviewer', :pw, 'reviewer', true),
            (:s_id, 'student1@syntaxlens.edu', 'Student Participant 001', :pw, 'student', true)
            ON CONFLICT (email) DO NOTHING;
        """), {"r_id": researcher_id, "rev_id": reviewer_id, "s_id": student_id, "pw": hashed_pw})

        # Seed Participant Profile for student1
        participant_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO research.participants (participant_id, research_code, user_id, age, mother_tongue, school_medium, country, state, city, study_group)
            SELECT :p_id, 'SL-2026-001', id, 21, 'Marathi', 'English', 'India', 'Maharashtra', 'Pune', 'intervention'
            FROM identity.users WHERE email = 'student1@syntaxlens.edu'
            ON CONFLICT (research_code) DO NOTHING;
        """), {"p_id": participant_id})

    print("Seeding completed successfully.")


if __name__ == "__main__":
    seed()
