"""Audio Recording, Upload Ingestion, and Idempotency (Phase P6).

Revision ID: 005_audio_recording
Revises: 004_research_settings
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '005_audio_recording'
down_revision = '004_research_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new tracking and idempotency columns to research.assessments
    op.add_column(
        'assessments',
        sa.Column('status', sa.String(50), server_default=sa.text("'queued_for_transcription'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('audio_duration_seconds', sa.Float(), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('audio_checksum', sa.String(128), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('idempotency_key', sa.String(100), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('is_official', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('retake_authorized_by', postgresql.UUID(as_uuid=True), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('retake_authorized_at', sa.DateTime(timezone=True), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('retake_reason', sa.Text(), nullable=True),
        schema='research'
    )

    # Alter transcript to nullable
    op.alter_column('assessments', 'transcript', nullable=True, schema='research')

    # Create indexes
    op.create_index(
        'ix_research_assessments_idempotency_key',
        'assessments',
        ['idempotency_key'],
        unique=True,
        schema='research'
    )
    op.create_index(
        'ix_research_assessments_status',
        'assessments',
        ['status'],
        unique=False,
        schema='research'
    )


def downgrade() -> None:
    op.drop_index('ix_research_assessments_status', table_name='assessments', schema='research')
    op.drop_index('ix_research_assessments_idempotency_key', table_name='assessments', schema='research')
    op.drop_column('assessments', 'retake_reason', schema='research')
    op.drop_column('assessments', 'retake_authorized_at', schema='research')
    op.drop_column('assessments', 'retake_authorized_by', schema='research')
    op.drop_column('assessments', 'is_official', schema='research')
    op.drop_column('assessments', 'idempotency_key', schema='research')
    op.drop_column('assessments', 'audio_checksum', schema='research')
    op.drop_column('assessments', 'audio_duration_seconds', schema='research')
    op.drop_column('assessments', 'status', schema='research')
