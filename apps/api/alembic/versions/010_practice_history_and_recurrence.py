"""Practice History, Utterance Recurrence, and Interruption Tracking (Phase P11).

Revision ID: 010_practice_history_and_recurrence
Revises: 009_tutor_and_hint_ladder
Create Date: 2026-10-28
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '010_practice_history_and_recurrence'
down_revision = '009_tutor_and_hint_ladder'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enrich research.practice_sessions with idle duration, interruptions, and activity tracking
    op.add_column(
        'practice_sessions',
        sa.Column('idle_duration_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
        schema='research'
    )
    op.add_column(
        'practice_sessions',
        sa.Column('interruption_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        schema='research'
    )
    op.add_column(
        'practice_sessions',
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        schema='research'
    )

    # 2. Enrich research.practice_events with fingerprint, event_type, occurrence flag, and active timing
    op.add_column(
        'practice_events',
        sa.Column('utterance_fingerprint', sa.String(64), nullable=True),
        schema='research'
    )
    op.add_column(
        'practice_events',
        sa.Column('event_type', sa.String(50), server_default=sa.text("'turn_attempt'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'practice_events',
        sa.Column('is_first_occurrence', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        schema='research'
    )
    op.add_column(
        'practice_events',
        sa.Column('elapsed_active_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
        schema='research'
    )
    op.create_index(
        'ix_research_event_fingerprint',
        'practice_events',
        ['utterance_fingerprint'],
        schema='research'
    )

    # 3. Create research.utterance_patterns table for recurrence tracking (SRS FR-14)
    op.create_table(
        'utterance_patterns',
        sa.Column('pattern_id', sa.UUID(), primary_key=True),
        sa.Column('participant_id', sa.UUID(), sa.ForeignKey('research.participants.participant_id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_category', sa.String(10), nullable=False),
        sa.Column('utterance_fingerprint', sa.String(64), nullable=False),
        sa.Column('canonical_phrase', sa.Text(), nullable=False),
        sa.Column('construction_type', sa.String(100), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('first_session_id', sa.UUID(), nullable=False),
        sa.Column('last_session_id', sa.UUID(), nullable=False),
        sa.Column('resolved_independently', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='research'
    )
    op.create_index(
        'ix_research_pattern_fingerprint',
        'utterance_patterns',
        ['participant_id', 'utterance_fingerprint'],
        schema='research'
    )
    op.create_index(
        'ix_research_pattern_category',
        'utterance_patterns',
        ['target_category'],
        schema='research'
    )


def downgrade() -> None:
    op.drop_table('utterance_patterns', schema='research')
    op.drop_index('ix_research_event_fingerprint', table_name='practice_events', schema='research')
    op.drop_column('practice_events', 'elapsed_active_seconds', schema='research')
    op.drop_column('practice_events', 'is_first_occurrence', schema='research')
    op.drop_column('practice_events', 'event_type', schema='research')
    op.drop_column('practice_events', 'utterance_fingerprint', schema='research')
    op.drop_column('practice_sessions', 'last_activity_at', schema='research')
    op.drop_column('practice_sessions', 'interruption_count', schema='research')
    op.drop_column('practice_sessions', 'idle_duration_seconds', schema='research')
