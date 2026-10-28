"""Research Settings, Versioned Config, and Frozen Immutability.

Revision ID: 004_research_settings
Revises: 003_participant_consent
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '004_research_settings'
down_revision = '003_participant_consent'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update research.assessment_tasks
    op.add_column(
        'assessment_tasks',
        sa.Column('equivalence_group', sa.String(100), server_default=sa.text("'pair_daily_routine'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'assessment_tasks',
        sa.Column('task_type', sa.String(50), server_default=sa.text("'any'"), nullable=False),
        schema='research'
    )

    # 2. Update research.rubric_versions
    op.add_column(
        'rubric_versions',
        sa.Column('categories_json', sa.Text(), server_default=sa.text("'[]'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'rubric_versions',
        sa.Column('counting_rules', sa.Text(), server_default=sa.text("''"), nullable=False),
        schema='research'
    )
    op.add_column(
        'rubric_versions',
        sa.Column('word_counting_rules', sa.Text(), server_default=sa.text("''"), nullable=False),
        schema='research'
    )
    op.add_column(
        'rubric_versions',
        sa.Column('status', sa.String(50), server_default=sa.text("'frozen'"), nullable=False),
        schema='research'
    )
    op.add_column('rubric_versions', sa.Column('change_notes', sa.Text(), nullable=True), schema='research')
    op.add_column('rubric_versions', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True), schema='research')
    op.add_column('rubric_versions', sa.Column('frozen_at', sa.DateTime(timezone=True), nullable=True), schema='research')
    op.add_column('rubric_versions', sa.Column('created_by', sa.UUID(), nullable=True), schema='research')

    # 3. Update research.prompt_versions
    op.add_column(
        'prompt_versions',
        sa.Column('prompt_role', sa.String(50), server_default=sa.text("'pre_test_assessor'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'prompt_versions',
        sa.Column('name', sa.String(200), server_default=sa.text("'Prompt'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'prompt_versions',
        sa.Column('output_schema_version', sa.String(50), server_default=sa.text("'json-schema-v1.0'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'prompt_versions',
        sa.Column('output_schema_json', sa.Text(), server_default=sa.text("'{}'"), nullable=False),
        schema='research'
    )
    op.add_column(
        'prompt_versions',
        sa.Column('status', sa.String(50), server_default=sa.text("'frozen'"), nullable=False),
        schema='research'
    )
    op.add_column('prompt_versions', sa.Column('change_notes', sa.Text(), nullable=True), schema='research')
    op.add_column('prompt_versions', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True), schema='research')
    op.add_column('prompt_versions', sa.Column('frozen_at', sa.DateTime(timezone=True), nullable=True), schema='research')
    op.add_column('prompt_versions', sa.Column('created_by', sa.UUID(), nullable=True), schema='research')

    # 4. Create research.assessment_periods table
    op.create_table(
        'assessment_periods',
        sa.Column('period_id', sa.UUID(), primary_key=True),
        sa.Column('period_code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rubric_version_code', sa.String(50), nullable=False),
        sa.Column('pre_prompt_version_code', sa.String(50), nullable=False),
        sa.Column('tutor_prompt_version_code', sa.String(50), nullable=False),
        sa.Column('post_prompt_version_code', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), server_default=sa.text("'frozen'"), nullable=False),
        sa.Column('is_frozen', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('change_notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        schema='research'
    )

    # 5. Database Triggers for Frozen Immutability on Postgres
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION research.fn_block_frozen_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                IF (OLD.is_frozen = true OR OLD.status = 'frozen') THEN
                    RAISE EXCEPTION 'RESEARCH INTEGRITY VIOLATION: Record is FROZEN and immutable. It cannot be updated or deleted. Supersede with a new version.';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        for tbl in ['rubric_versions', 'prompt_versions', 'assessment_periods']:
            op.execute(f"""
                DROP TRIGGER IF EXISTS trg_{tbl}_frozen_check ON research.{tbl};
                CREATE TRIGGER trg_{tbl}_frozen_check
                BEFORE UPDATE OR DELETE ON research.{tbl}
                FOR EACH ROW EXECUTE FUNCTION research.fn_block_frozen_mutation();
            """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for tbl in ['rubric_versions', 'prompt_versions', 'assessment_periods']:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_frozen_check ON research.{tbl};")

    op.drop_table('assessment_periods', schema='research')

    op.drop_column('prompt_versions', 'created_by', schema='research')
    op.drop_column('prompt_versions', 'frozen_at', schema='research')
    op.drop_column('prompt_versions', 'approved_at', schema='research')
    op.drop_column('prompt_versions', 'change_notes', schema='research')
    op.drop_column('prompt_versions', 'status', schema='research')
    op.drop_column('prompt_versions', 'output_schema_json', schema='research')
    op.drop_column('prompt_versions', 'output_schema_version', schema='research')
    op.drop_column('prompt_versions', 'name', schema='research')
    op.drop_column('prompt_versions', 'prompt_role', schema='research')

    op.drop_column('rubric_versions', 'created_by', schema='research')
    op.drop_column('rubric_versions', 'frozen_at', schema='research')
    op.drop_column('rubric_versions', 'approved_at', schema='research')
    op.drop_column('rubric_versions', 'change_notes', schema='research')
    op.drop_column('rubric_versions', 'status', schema='research')
    op.drop_column('rubric_versions', 'word_counting_rules', schema='research')
    op.drop_column('rubric_versions', 'counting_rules', schema='research')
    op.drop_column('rubric_versions', 'categories_json', schema='research')

    op.drop_column('assessment_tasks', 'task_type', schema='research')
    op.drop_column('assessment_tasks', 'equivalence_group', schema='research')
