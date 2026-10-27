"""Auth, RBAC, Reviewer Assignments, and Enhanced Audit Log.

Revision ID: 002_auth_and_audit
Revises: 001_initial
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '002_auth_and_audit'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update identity.user_role enum if on Postgres
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE identity.user_role ADD VALUE IF NOT EXISTS 'participant';")
        op.execute("ALTER TYPE identity.user_role ADD VALUE IF NOT EXISTS 'researcher_admin';")

    # 2. Add columns to identity.users
    op.add_column(
        'users',
        sa.Column('must_change_password', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        schema='identity'
    )
    op.add_column(
        'users',
        sa.Column('failed_login_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        schema='identity'
    )
    op.add_column(
        'users',
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        schema='identity'
    )

    # 3. Create identity.password_reset_tokens
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identity.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='identity'
    )
    op.create_index('ix_identity_reset_token_hash', 'password_reset_tokens', ['token_hash'], schema='identity')
    op.create_index('ix_identity_reset_user_id', 'password_reset_tokens', ['user_id'], schema='identity')

    # 4. Create research.reviewer_assignments
    op.create_table(
        'reviewer_assignments',
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identity.users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research.assessments.assessment_id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('identity.users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='research'
    )
    op.create_index('ix_research_reviewer_id', 'reviewer_assignments', ['reviewer_id'], schema='research')
    op.create_index('ix_research_assigned_assessment_id', 'reviewer_assignments', ['assessment_id'], schema='research')

    # 5. Enhance research.audit_logs
    op.add_column(
        'audit_logs',
        sa.Column('role', sa.String(length=50), nullable=True),
        schema='research'
    )
    op.add_column(
        'audit_logs',
        sa.Column('record_type', sa.String(length=50), nullable=True),
        schema='research'
    )
    op.add_column(
        'audit_logs',
        sa.Column('record_id', sa.String(length=100), nullable=True),
        schema='research'
    )
    op.add_column(
        'audit_logs',
        sa.Column('outcome', sa.String(length=20), server_default='success', nullable=False),
        schema='research'
    )
    op.add_column(
        'audit_logs',
        sa.Column('ip_hash', sa.String(length=64), nullable=True),
        schema='research'
    )
    op.add_column(
        'audit_logs',
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        schema='research'
    )
    op.add_column(
        'audit_logs',
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='research'
    )

    # Populate record_type and record_id from old columns if exist
    op.execute("""
        UPDATE research.audit_logs
        SET record_type = COALESCE(record_type, resource_type, 'unknown'),
            record_id = COALESCE(record_id, resource_id, 'unknown')
        WHERE record_type IS NULL;
    """)

    # Alter columns to NOT NULL if needed
    op.alter_column('audit_logs', 'record_type', nullable=False, schema='research')
    op.alter_column('audit_logs', 'record_id', nullable=False, schema='research')

    op.create_index('ix_research_audit_actor', 'audit_logs', ['actor_id'], schema='research')
    op.create_index('ix_research_audit_action', 'audit_logs', ['action'], schema='research')
    op.create_index('ix_research_audit_timestamp', 'audit_logs', ['timestamp'], schema='research')


def downgrade() -> None:
    op.drop_table('reviewer_assignments', schema='research')
    op.drop_table('password_reset_tokens', schema='identity')
    
    op.drop_column('users', 'locked_until', schema='identity')
    op.drop_column('users', 'failed_login_attempts', schema='identity')
    op.drop_column('users', 'must_change_password', schema='identity')
    
    op.drop_column('audit_logs', 'timestamp', schema='research')
    op.drop_column('audit_logs', 'user_agent', schema='research')
    op.drop_column('audit_logs', 'ip_hash', schema='research')
    op.drop_column('audit_logs', 'outcome', schema='research')
    op.drop_column('audit_logs', 'record_id', schema='research')
    op.drop_column('audit_logs', 'record_type', schema='research')
    op.drop_column('audit_logs', 'role', schema='research')
