"""Unit Tests for Deterministic Topic Assignment (SRS FR-05, FR-20).

Verifies:
- Equivalence topic pairs are reproducible from seed.
- Same participant identifier or explicit seed always yields identical pre and post tasks.
- Pre and post tasks belong to the same equivalence group and match difficulty.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.config import config_service


@pytest.mark.asyncio
async def test_topic_seed_assignment_reproducible(test_session: AsyncSession, seeded_data: dict) -> None:
    """Verify that given an explicit seed, topic pair assignment is 100% deterministic."""
    seed_val = 42

    result1 = await config_service.assign_topic_pair(
        db=test_session,
        participant_identifier="any_participant",
        seed=seed_val,
    )

    result2 = await config_service.assign_topic_pair(
        db=test_session,
        participant_identifier="different_participant",
        seed=seed_val,
    )

    assert result1["seed"] == seed_val
    assert result2["seed"] == seed_val
    assert result1["equivalence_group"] == result2["equivalence_group"]
    assert result1["pre_task"]["task_id"] == result2["pre_task"]["task_id"]
    assert result1["post_task"]["task_id"] == result2["post_task"]["task_id"]
    assert result1["pre_task"]["title"] == result2["pre_task"]["title"]
    assert result1["post_task"]["title"] == result2["post_task"]["title"]


@pytest.mark.asyncio
async def test_participant_id_reproducible_without_explicit_seed(test_session: AsyncSession, seeded_data: dict) -> None:
    """Verify that using the same participant ID generates a consistent deterministic seed and assignment."""
    pid = "SL-2026-0099"

    first_call = await config_service.assign_topic_pair(
        db=test_session,
        participant_identifier=pid,
    )

    second_call = await config_service.assign_topic_pair(
        db=test_session,
        participant_identifier=pid,
    )

    assert first_call["seed"] == second_call["seed"]
    assert first_call["equivalence_group"] == second_call["equivalence_group"]
    assert first_call["pre_task"]["title"] == second_call["pre_task"]["title"]
    assert first_call["post_task"]["title"] == second_call["post_task"]["title"]


@pytest.mark.asyncio
async def test_pre_post_matched_difficulty_and_distinct(test_session: AsyncSession, seeded_data: dict) -> None:
    """Verify pre and post tasks are distinct but matched in equivalence group and duration."""
    res = await config_service.assign_topic_pair(
        db=test_session,
        participant_identifier="SL-2026-TEST",
        seed=101,
    )

    pre = res["pre_task"]
    post = res["post_task"]

    # Pre and Post must be different tasks
    assert pre["task_id"] != post["task_id"]
    assert pre["title"] != post["title"]

    # Both must match research duration & prep time
    assert pre["prep_time_seconds"] == 30
    assert post["prep_time_seconds"] == 30
    assert pre["duration_seconds"] == 60
    assert post["duration_seconds"] == 60
    assert pre["difficulty_level"] == post["difficulty_level"]
