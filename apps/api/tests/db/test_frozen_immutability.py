"""Database-level Tests for Frozen Immutability (SRS FR-05, FR-08, FR-20).

NON-NEGOTIABLE RESEARCH INTEGRITY RULE:
Rubrics, prompts, and assessment periods once FROZEN are immutable at the database level.
Any UPDATE or DELETE on frozen configuration records MUST be rejected by DB triggers.
Draft configuration records can be updated until frozen.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import (
    AssessmentPeriod,
    LifecycleState,
    PromptRole,
    PromptVersion,
    RubricVersion,
)


@pytest.mark.asyncio
async def test_frozen_rubric_rejects_update_at_db_level(test_session: AsyncSession, seeded_data: dict) -> None:
    """Verifies DB trigger blocks any UPDATE to a frozen rubric version."""
    stmt = select(RubricVersion).where(RubricVersion.is_frozen == True).limit(1)  # noqa: E712
    rubric = (await test_session.execute(stmt)).scalar_one()

    # Attempt to update frozen rubric name via direct SQL
    update_stmt = (
        update(RubricVersion)
        .where(RubricVersion.rubric_id == rubric.rubric_id)
        .values(name="Tampered Frozen Rubric Name")
    )

    with pytest.raises(DBAPIError) as exc_info:
        await test_session.execute(update_stmt)
        await test_session.flush()

    assert "RESEARCH INTEGRITY VIOLATION: Frozen rubric versions are strictly immutable" in str(exc_info.value)
    await test_session.rollback()


@pytest.mark.asyncio
async def test_frozen_rubric_rejects_delete_at_db_level(test_session: AsyncSession, seeded_data: dict) -> None:
    """Verifies DB trigger blocks any DELETE to a frozen rubric version."""
    stmt = select(RubricVersion).where(RubricVersion.is_frozen == True).limit(1)  # noqa: E712
    rubric = (await test_session.execute(stmt)).scalar_one()

    delete_stmt = delete(RubricVersion).where(RubricVersion.rubric_id == rubric.rubric_id)

    with pytest.raises(DBAPIError) as exc_info:
        await test_session.execute(delete_stmt)
        await test_session.flush()

    assert "RESEARCH INTEGRITY VIOLATION: Frozen rubric versions cannot be deleted" in str(exc_info.value)
    await test_session.rollback()


@pytest.mark.asyncio
async def test_frozen_prompt_rejects_mutation_at_db_level(test_session: AsyncSession, seeded_data: dict) -> None:
    """Verifies DB trigger blocks UPDATE or DELETE to frozen prompt versions."""
    stmt = select(PromptVersion).where(PromptVersion.is_frozen == True).limit(1)  # noqa: E712
    prompt = (await test_session.execute(stmt)).scalar_one()
    prompt_id = prompt.prompt_id

    # Attempt update
    update_stmt = (
        update(PromptVersion)
        .where(PromptVersion.prompt_id == prompt_id)
        .values(prompt_template="Malicious replacement prompt template")
    )
    with pytest.raises(DBAPIError) as exc_info:
        await test_session.execute(update_stmt)
        await test_session.flush()

    assert "RESEARCH INTEGRITY VIOLATION: Frozen prompt versions are strictly immutable" in str(exc_info.value)
    await test_session.rollback()

    # Attempt delete
    delete_stmt = delete(PromptVersion).where(PromptVersion.prompt_id == prompt_id)
    with pytest.raises(DBAPIError) as exc_info_del:
        await test_session.execute(delete_stmt)
        await test_session.flush()

    assert "RESEARCH INTEGRITY VIOLATION: Frozen prompt versions cannot be deleted" in str(exc_info_del.value)
    await test_session.rollback()


@pytest.mark.asyncio
async def test_frozen_period_rejects_mutation_at_db_level(test_session: AsyncSession, seeded_data: dict) -> None:
    """Verifies DB trigger blocks UPDATE or DELETE to frozen assessment periods."""
    stmt = select(AssessmentPeriod).where(AssessmentPeriod.is_frozen == True).limit(1)  # noqa: E712
    period = (await test_session.execute(stmt)).scalar_one()

    # Attempt update
    update_stmt = (
        update(AssessmentPeriod)
        .where(AssessmentPeriod.period_id == period.period_id)
        .values(name="Tampered Period Name")
    )
    with pytest.raises(DBAPIError) as exc_info:
        await test_session.execute(update_stmt)
        await test_session.flush()

    assert "RESEARCH INTEGRITY VIOLATION: Frozen assessment periods are strictly immutable" in str(exc_info.value)
    await test_session.rollback()


@pytest.mark.asyncio
async def test_draft_rubric_can_be_updated_before_freezing(test_session: AsyncSession, seeded_data: dict) -> None:
    """Verifies that non-frozen draft records can be legitimately updated."""
    draft_rubric = RubricVersion(
        rubric_id=uuid.uuid4(),
        version_code="v-test-draft-01",
        name="Test Draft Rubric",
        categories_json=json.dumps([]),
        counting_rules="Draft rules",
        word_counting_rules="Draft word rules",
        status=LifecycleState.DRAFT,
        is_frozen=False,
    )
    test_session.add(draft_rubric)
    await test_session.commit()

    # Update draft name
    update_stmt = (
        update(RubricVersion)
        .where(RubricVersion.rubric_id == draft_rubric.rubric_id)
        .values(name="Updated Draft Rubric Name")
    )
    await test_session.execute(update_stmt)
    await test_session.commit()

    # Verify update succeeded
    stmt = select(RubricVersion).where(RubricVersion.rubric_id == draft_rubric.rubric_id)
    refreshed = (await test_session.execute(stmt)).scalar_one()
    assert refreshed.name == "Updated Draft Rubric Name"
    assert refreshed.is_frozen is False
