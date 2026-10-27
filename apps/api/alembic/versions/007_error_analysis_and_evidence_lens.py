"""Error Analysis Engine, Participant Visibility, and Annotation Version Stamping (Phase P8).

Revision ID: 007_error_analysis_and_evidence_lens
Revises: 006_stt_pipeline_and_metrics
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '007_error_analysis_and_evidence_lens'
down_revision = '006_stt_pipeline_and_metrics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enrich research.assessments with prompt version, visibility flag, and model notes
    op.add_column(
        'assessments',
        sa.Column('prompt_version', sa.String(50), nullable=True),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('is_visible_to_participant', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        schema='research'
    )
    op.add_column(
        'assessments',
        sa.Column('model_notes', sa.Text(), nullable=True),
        schema='research'
    )

    # 2. Enrich research.error_annotations with flag, versions, and raw model output reference
    op.add_column(
        'error_annotations',
        sa.Column('flag', sa.String(50), server_default=sa.text("'candidate_error'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'error_annotations',
        sa.Column('rubric_version', sa.String(50), server_default=sa.text("'v1.0-jam-phd'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'error_annotations',
        sa.Column('prompt_version', sa.String(50), server_default=sa.text("'v1.0-assessor'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'error_annotations',
        sa.Column('raw_model_output_ref', sa.String(500), nullable=True),
        schema='research'
    )


def downgrade() -> None:
    op.drop_column('error_annotations', 'raw_model_output_ref', schema='research')
    op.drop_column('error_annotations', 'prompt_version', schema='research')
    op.drop_column('error_annotations', 'rubric_version', schema='research')
    op.drop_column('error_annotations', 'flag', schema='research')
    op.drop_column('assessments', 'model_notes', schema='research')
    op.drop_column('assessments', 'is_visible_to_participant', schema='research')
    op.drop_column('assessments', 'prompt_version', schema='research')
