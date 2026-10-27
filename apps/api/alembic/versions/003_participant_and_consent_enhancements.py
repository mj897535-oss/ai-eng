"""Participant Management, Consent Tracking, and Onboarding Enhancements.

Revision ID: 003_participant_consent
Revises: 002_auth_and_audit
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '003_participant_consent'
down_revision = '002_auth_and_audit'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update research.participants columns
    op.add_column(
        'participants',
        sa.Column('age_band', sa.String(50), nullable=True),
        schema='research'
    )
    op.add_column(
        'participants',
        sa.Column('is_group_blinded', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        schema='research'
    )
    op.add_column(
        'participants',
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        schema='research'
    )
    op.add_column(
        'participants',
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        schema='research'
    )
    op.add_column(
        'participants',
        sa.Column('withdrawal_reason', sa.String(500), nullable=True),
        schema='research'
    )
    op.add_column(
        'participants',
        sa.Column('current_consent_version', sa.String(50), nullable=True),
        schema='research'
    )
    op.add_column(
        'participants',
        sa.Column('consented_at', sa.DateTime(timezone=True), nullable=True),
        schema='research'
    )
    op.add_column(
        'participants',
        sa.Column('onboarding_completed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        schema='research'
    )
    op.add_column(
        'participants',
        sa.Column('onboarding_step', sa.String(50), server_default=sa.text("'consent'"), nullable=False),
        schema='research'
    )

    # Allow nullable user_id, mother_tongue, school_medium during pre-registration
    op.alter_column('participants', 'user_id', nullable=True, schema='research')
    op.alter_column('participants', 'mother_tongue', nullable=True, schema='research')
    op.alter_column('participants', 'school_medium', nullable=True, schema='research')
    op.alter_column('participants', 'country', nullable=True, schema='research')

    # 2. Update research.consents columns
    op.add_column(
        'consents',
        sa.Column('ip_hash', sa.String(64), nullable=True),
        schema='research'
    )
    op.add_column(
        'consents',
        sa.Column('user_agent', sa.String(500), nullable=True),
        schema='research'
    )

    # 3. Add immutability triggers for research.consents on Postgres
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION research.fn_block_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'RESEARCH INTEGRITY VIOLATION: Records in %.% are strictly append-only and cannot be modified or deleted.',
                    TG_TABLE_SCHEMA, TG_TABLE_NAME;
            END;
            $$ LANGUAGE plpgsql;
        """)

        op.execute("""
            DROP TRIGGER IF EXISTS trg_consents_no_update ON research.consents;
            CREATE TRIGGER trg_consents_no_update
            BEFORE UPDATE ON research.consents
            FOR EACH ROW EXECUTE FUNCTION research.fn_block_mutation();
        """)

        op.execute("""
            DROP TRIGGER IF EXISTS trg_consents_no_delete ON research.consents;
            CREATE TRIGGER trg_consents_no_delete
            BEFORE DELETE ON research.consents
            FOR EACH ROW EXECUTE FUNCTION research.fn_block_mutation();
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_consents_no_update ON research.consents;")
        op.execute("DROP TRIGGER IF EXISTS trg_consents_no_delete ON research.consents;")

    op.drop_column('consents', 'user_agent', schema='research')
    op.drop_column('consents', 'ip_hash', schema='research')

    op.drop_column('participants', 'onboarding_step', schema='research')
    op.drop_column('participants', 'onboarding_completed', schema='research')
    op.drop_column('participants', 'consented_at', schema='research')
    op.drop_column('participants', 'current_consent_version', schema='research')
    op.drop_column('participants', 'withdrawal_reason', schema='research')
    op.drop_column('participants', 'withdrawn_at', schema='research')
    op.drop_column('participants', 'is_active', schema='research')
    op.drop_column('participants', 'is_group_blinded', schema='research')
    op.drop_column('participants', 'age_band', schema='research')
