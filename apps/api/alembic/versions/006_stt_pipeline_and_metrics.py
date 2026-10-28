"""STT Pipeline, Transcript Immutability, and Pilot Metrics (Phase P7).

Revision ID: 006_stt_pipeline_and_metrics
Revises: 005_audio_recording
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '006_stt_pipeline_and_metrics'
down_revision = '005_audio_recording'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add STT enrichment columns to research.assessments
    op.add_column(
        'assessments',
        sa.Column('raw_stt_response_key', sa.String(500), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('words_json', sa.Text(), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('stt_confidence', sa.Float(), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('low_confidence_flag', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('retry_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('last_error', sa.Text(), nullable=True),
        schema='research'
    )

    # 2. Create research.transcript_revisions (Immutable human revisions)
    op.create_table(
        'transcript_revisions',
        sa.Column('revision_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'assessment_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('research.assessments.assessment_id', ondelete='CASCADE'),
            nullable=False,
            index=True
        ),
        sa.Column('revised_transcript', sa.Text(), nullable=False),
        sa.Column('revised_word_count', sa.Integer(), nullable=False),
        sa.Column(
            'reviewer_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('identity.users.id', ondelete='RESTRICT'),
            nullable=False,
            index=True
        ),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('diff_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='research'
    )

    # 3. Create research.stt_job_metrics (Pilot Kit telemetry)
    op.create_table(
        'stt_job_metrics',
        sa.Column('metric_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'assessment_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('research.assessments.assessment_id', ondelete='CASCADE'),
            nullable=False,
            index=True
        ),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('audio_duration_seconds', sa.Float(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('estimated_cost_usd', sa.Float(), server_default=sa.text('0.0'), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('average_confidence', sa.Float(), nullable=False),
        sa.Column('low_confidence_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('retry_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='research'
    )

    # 4. Enforce DB trigger on PostgreSQL to block transcript updates once written
    op.execute(
        """
        CREATE OR REPLACE FUNCTION research.fn_block_transcript_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.transcript IS NOT NULL AND NEW.transcript IS DISTINCT FROM OLD.transcript THEN
                RAISE EXCEPTION 'Assessments transcript is immutable once written and cannot be modified. Record a transcript_revision instead.';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_block_transcript_mutation ON research.assessments;
        CREATE TRIGGER trg_block_transcript_mutation
        BEFORE UPDATE OF transcript ON research.assessments
        FOR EACH ROW
        EXECUTE FUNCTION research.fn_block_transcript_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_transcript_mutation ON research.assessments;")
    op.execute("DROP FUNCTION IF EXISTS research.fn_block_transcript_mutation();")
    op.drop_table('stt_job_metrics', schema='research')
    op.drop_table('transcript_revisions', schema='research')
    op.drop_column('assessments', 'last_error', schema='research')
    op.drop_column('assessments', 'retry_count', schema='research')
    op.drop_column('assessments', 'low_confidence_flag', schema='research')
    op.drop_column('assessments', 'stt_confidence', schema='research')
    op.drop_column('assessments', 'words_json', schema='research')
    op.drop_column('assessments', 'raw_stt_response_key', schema='research')
