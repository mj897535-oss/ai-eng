"""Initial Schema and Research Immutability Triggers.

Revision ID: 001_initial
Revises: None
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Ensure schemas exist
    op.execute("CREATE SCHEMA IF NOT EXISTS identity;")
    op.execute("CREATE SCHEMA IF NOT EXISTS research;")

    # 2. Trigger function for append-only tables
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_row_mutation_or_deletion()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'RESEARCH INTEGRITY VIOLATION: Records in table %.% are strictly append-only and cannot be updated or deleted.', TG_TABLE_SCHEMA, TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 3. Identity Schema Tables
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('student', 'researcher', 'reviewer', 'admin', name='user_role', schema='identity'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='identity'
    )
    op.create_index('ix_identity_users_email', 'users', ['email'], unique=True, schema='identity')

    op.create_table(
        'identity_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('details', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='identity'
    )

    # 4. Research Schema Tables
    op.create_table(
        'participants',
        sa.Column('participant_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('research_code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identity.users.id', ondelete='RESTRICT'), nullable=False, unique=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('mother_tongue', sa.String(length=100), nullable=False),
        sa.Column('school_medium', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False, server_default='India'),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('study_group', sa.Enum('intervention', 'control', name='study_group', schema='research'), nullable=False),
        sa.Column('is_withdrawn', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )
    op.create_index('ix_research_participants_code', 'participants', ['research_code'], unique=True, schema='research')

    op.create_table(
        'consents',
        sa.Column('consent_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research.participants.participant_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('consent_version', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('consented', 'withdrawn', name='consent_status', schema='research'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'assessment_tasks',
        sa.Column('task_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('prep_time_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('difficulty_level', sa.String(length=50), nullable=False, server_default='standard'),
        sa.Column('rubric_version', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'assessments',
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research.participants.participant_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research.assessment_tasks.task_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('assessment_type', sa.Enum('pre', 'post', name='assessment_type', schema='research'), nullable=False),
        sa.Column('audio_key', sa.String(length=500), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('stt_version', sa.String(length=50), nullable=False),
        sa.Column('rubric_version', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'error_annotations',
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research.assessments.assessment_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=False),
        sa.Column('end_char', sa.Integer(), nullable=False),
        sa.Column('start_time_ms', sa.Integer(), nullable=True),
        sa.Column('end_time_ms', sa.Integer(), nullable=True),
        sa.Column('candidate_error', sa.String(length=255), nullable=False),
        sa.Column('suggested_correction', sa.String(length=255), nullable=False),
        sa.Column('category_code', sa.String(length=10), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('ai_status', sa.String(length=50), nullable=False, server_default='candidate'),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'reviewer_decisions',
        sa.Column('decision_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research.error_annotations.annotation_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identity.users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('decision', sa.Enum('accepted', 'rejected', 'edited', 'uncertain', name='review_decision_type', schema='research'), nullable=False),
        sa.Column('edited_category', sa.String(length=10), nullable=True),
        sa.Column('edited_correction', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'practice_sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research.participants.participant_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('active_duration_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tutor_prompt_version', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'practice_events',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research.practice_sessions.session_id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_category', sa.String(length=10), nullable=False),
        sa.Column('learner_phrase', sa.Text(), nullable=False),
        sa.Column('feedback_level', sa.Integer(), nullable=False),
        sa.Column('hint_text', sa.Text(), nullable=True),
        sa.Column('attempt_type', sa.Enum('independent', 'hint_assisted', 'revealed', name='attempt_type', schema='research'), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('transfer_phrase', sa.Text(), nullable=True),
        sa.Column('transfer_correct', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'audit_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'rubric_versions',
        sa.Column('rubric_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version_code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('taxonomy_json', sa.Text(), nullable=False),
        sa.Column('is_frozen', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    op.create_table(
        'prompt_versions',
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('prompt_type', sa.String(length=50), nullable=False),
        sa.Column('version_code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('prompt_template', sa.Text(), nullable=False),
        sa.Column('is_frozen', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='research'
    )

    # 5. Attach Append-Only Triggers
    op.execute("""
        CREATE TRIGGER trg_consents_immutability
        BEFORE UPDATE OR DELETE ON research.consents
        FOR EACH ROW EXECUTE FUNCTION prevent_row_mutation_or_deletion();
    """)

    op.execute("""
        CREATE TRIGGER trg_assessments_immutability
        BEFORE UPDATE OR DELETE ON research.assessments
        FOR EACH ROW EXECUTE FUNCTION prevent_row_mutation_or_deletion();
    """)

    op.execute("""
        CREATE TRIGGER trg_error_annotations_immutability
        BEFORE UPDATE OR DELETE ON research.error_annotations
        FOR EACH ROW EXECUTE FUNCTION prevent_row_mutation_or_deletion();
    """)

    op.execute("""
        CREATE TRIGGER trg_audit_logs_immutability
        BEFORE UPDATE OR DELETE ON research.audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_row_mutation_or_deletion();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutability ON research.audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS trg_error_annotations_immutability ON research.error_annotations;")
    op.execute("DROP TRIGGER IF EXISTS trg_assessments_immutability ON research.assessments;")
    op.execute("DROP TRIGGER IF EXISTS trg_consents_immutability ON research.consents;")

    op.execute("DROP FUNCTION IF EXISTS prevent_row_mutation_or_deletion();")

    # Drop research tables
    op.drop_table('prompt_versions', schema='research')
    op.drop_table('rubric_versions', schema='research')
    op.drop_table('audit_logs', schema='research')
    op.drop_table('practice_events', schema='research')
    op.drop_table('practice_sessions', schema='research')
    op.drop_table('reviewer_decisions', schema='research')
    op.drop_table('error_annotations', schema='research')
    op.drop_table('assessments', schema='research')
    op.drop_table('assessment_tasks', schema='research')
    op.drop_table('consents', schema='research')
    op.drop_table('participants', schema='research')

    # Drop identity tables
    op.drop_table('identity_audit_logs', schema='identity')
    op.drop_table('users', schema='identity')

    # Drop types
    op.execute("DROP TYPE IF EXISTS research.attempt_type;")
    op.execute("DROP TYPE IF EXISTS research.review_decision_type;")
    op.execute("DROP TYPE IF EXISTS research.assessment_type;")
    op.execute("DROP TYPE IF EXISTS research.consent_status;")
    op.execute("DROP TYPE IF EXISTS research.study_group;")
    op.execute("DROP TYPE IF EXISTS identity.user_role;")
