"""Tutor Service, Hint Ladder Sessions, and Learner Interests (Phase P10).

Revision ID: 009_tutor_and_hint_ladder
Revises: 008_reviewer_cockpit_and_agreements
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '009_tutor_and_hint_ladder'
down_revision = '008_reviewer_cockpit_and_agreements'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add learner_interests to research.participants
    op.add_column(
        'participants',
        sa.Column('learner_interests', sa.String(500), nullable=True),
        schema='research'
    )

    # 2. Enrich research.practice_sessions with topic, target categories, and turns count
    op.add_column(
        'practice_sessions',
        sa.Column('topic', sa.String(200), nullable=True),
        schema='research'
    )
    op.add_column(
        'practice_sessions',
        sa.Column('target_categories_json', sa.Text(), nullable=True),
        schema='research'
    )
    op.add_column(
        'practice_sessions',
        sa.Column('turns_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        schema='research'
    )

    # 3. Enrich research.practice_events with learner input, tutor reply, and transfer prompt
    op.add_column(
        'practice_events',
        sa.Column('learner_input', sa.Text(), nullable=True),
        schema='research'
    )
    op.add_column(
        'practice_events',
        sa.Column('tutor_reply', sa.Text(), nullable=True),
        schema='research'
    )
    op.add_column(
        'practice_events',
        sa.Column('transfer_prompt', sa.Text(), nullable=True),
        schema='research'
    )


def downgrade() -> None:
    op.drop_column('practice_events', 'transfer_prompt', schema='research')
    op.drop_column('practice_events', 'tutor_reply', schema='research')
    op.drop_column('practice_events', 'learner_input', schema='research')
    op.drop_column('practice_sessions', 'turns_count', schema='research')
    op.drop_column('practice_sessions', 'target_categories_json', schema='research')
    op.drop_column('practice_sessions', 'topic', schema='research')
    op.drop_column('participants', 'learner_interests', schema='research')
