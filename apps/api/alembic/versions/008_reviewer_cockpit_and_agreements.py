"""Reviewer Cockpit, Decisions Immutability, and Inter-Rater Agreements (Phase P9).

Revision ID: 008_reviewer_cockpit_and_agreements
Revises: 007_error_analysis_and_evidence_lens
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '008_reviewer_cockpit_and_agreements'
down_revision = '007_error_analysis_and_evidence_lens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enrich research.assessments with verification sign-off and review status
    op.add_column(
        'assessments',
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('verified_by', sa.UUID(), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('review_status', sa.String(50), server_default=sa.text("'unreviewed'"), nullable=False),
        schema='research'
    )

    # 2. Enrich research.error_annotations with origin and reviewer creator
    op.add_column(
        'error_annotations',
        sa.Column('origin', sa.String(20), server_default=sa.text("'ai'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'error_annotations',
        sa.Column('created_by_reviewer_id', sa.UUID(), nullable=True),
        schema='research'
    )

    # 3. Enrich research.reviewer_decisions
    op.add_column(
        'reviewer_decisions',
        sa.Column('assessment_id', sa.UUID(), nullable=True),
        schema='research'
    )
    op.add_column(
        'reviewer_decisions',
        sa.Column('edited_span', sa.String(255), nullable=True),
        schema='research'
    )
    op.add_column(
        'reviewer_decisions',
        sa.Column('edited_start_char', sa.Integer(), nullable=True),
        schema='research'
    )
    op.add_column(
        'reviewer_decisions',
        sa.Column('edited_end_char', sa.Integer(), nullable=True),
        schema='research'
    )
    op.add_column(
        'reviewer_decisions',
        sa.Column('edited_explanation', sa.Text(), nullable=True),
        schema='research'
    )
    op.add_column(
        'reviewer_decisions',
        sa.Column('reason', sa.Text(), nullable=True),
        schema='research'
    )
    op.add_column(
        'reviewer_decisions',
        sa.Column('before_state', sa.Text(), nullable=True),
        schema='research'
    )
    op.add_column(
        'reviewer_decisions',
        sa.Column('after_state', sa.Text(), nullable=True),
        schema='research'
    )
    op.add_column(
        'reviewer_decisions',
        sa.Column('is_reviewer_originated', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        schema='research'
    )

    # 4. Enrich research.reviewer_assignments with review round
    op.add_column(
        'reviewer_assignments',
        sa.Column('review_round', sa.Integer(), server_default=sa.text('1'), nullable=False),
        schema='research'
    )

    # 5. Expand PostgreSQL enum review_decision_type if on PostgreSQL
    try:
        op.execute("ALTER TYPE research.review_decision_type ADD VALUE IF NOT EXISTS 'recategorized';")
        op.execute("ALTER TYPE research.review_decision_type ADD VALUE IF NOT EXISTS 'transcription_related';")
        op.execute("ALTER TYPE research.review_decision_type ADD VALUE IF NOT EXISTS 'acceptable_variation';")
        op.execute("ALTER TYPE research.review_decision_type ADD VALUE IF NOT EXISTS 'added';")
    except Exception:
        pass


def downgrade() -> None:
    op.drop_column('reviewer_assignments', 'review_round', schema='research')
    op.drop_column('reviewer_decisions', 'is_reviewer_originated', schema='research')
    op.drop_column('reviewer_decisions', 'after_state', schema='research')
    op.drop_column('reviewer_decisions', 'before_state', schema='research')
    op.drop_column('reviewer_decisions', 'reason', schema='research')
    op.drop_column('reviewer_decisions', 'edited_explanation', schema='research')
    op.drop_column('reviewer_decisions', 'edited_end_char', schema='research')
    op.drop_column('reviewer_decisions', 'edited_start_char', schema='research')
    op.drop_column('reviewer_decisions', 'edited_span', schema='research')
    op.drop_column('reviewer_decisions', 'assessment_id', schema='research')
    op.drop_column('error_annotations', 'created_by_reviewer_id', schema='research')
    op.drop_column('error_annotations', 'origin', schema='research')
    op.drop_column('assessments', 'review_status', schema='research')
    op.drop_column('assessments', 'verified_by', schema='research')
    op.drop_column('assessments', 'verified_at', schema='research')
    op.drop_column('assessments', 'is_verified', schema='research')
