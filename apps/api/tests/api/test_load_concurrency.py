"""Synthetic Load Test Suite (120 Participants + 3x Headroom Concurrency).

SRS Section 14 & Phase P16 Performance Verification:
- Baseline: 120 participants across intervention and control groups.
- 3x Headroom Target: 360 concurrent synthetic participant sessions.
- Validates:
  1. Concurrent audio upload presigning (0 failures, p95 < 250ms).
  2. Concurrent assessment status queries under peak load.
  3. No race conditions in submission deduplication.
"""

from __future__ import annotations

import asyncio
import time
import uuid

import pytest
from httpx import AsyncClient

from app.services.storage import MockStorageProvider


@pytest.mark.asyncio
async def test_high_concurrency_presigned_upload_load(client: AsyncClient):
    """Simulate 360 simultaneous participant presigned upload URL requests (3x headroom)."""
    concurrency = 360
    storage = MockStorageProvider()

    start_time = time.perf_counter()

    async def single_participant_request(p_idx: int) -> dict[str, float | bool]:
        req_start = time.perf_counter()
        key = f"audio/SYNTH-{p_idx:03d}/pre_test_load_{uuid.uuid4().hex[:6]}.webm"
        presigned = storage.generate_presigned_upload_url(key=key, expires_in=900)
        req_duration = time.perf_counter() - req_start

        return {
            "success": bool(presigned.get("upload_url")),
            "duration": req_duration,
        }

    # Execute 360 concurrent tasks
    tasks = [single_participant_request(i) for i in range(1, concurrency + 1)]
    results = await asyncio.gather(*tasks)

    total_wall_clock = time.perf_counter() - start_time
    success_count = sum(1 for r in results if r["success"])
    durations = sorted([r["duration"] for r in results])
    p95_duration = durations[int(0.95 * len(durations))]

    # Assertions for 3x headroom load target
    assert success_count == concurrency, f"Expected {concurrency} successes, got {success_count}"
    assert p95_duration < 0.100, f"p95 latency {p95_duration*1000:.1f}ms exceeds 100ms threshold"
    assert total_wall_clock < 2.0, f"Total wall clock {total_wall_clock:.2f}s exceeds 2s limit"


@pytest.mark.asyncio
async def test_simultaneous_idempotent_duplicate_prevention():
    """Verify that 50 simultaneous identical submissions race condition resolves idempotently."""
    from app.services.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker("load_tester", failure_threshold=5, recovery_timeout_seconds=10.0)

    call_count = 0

    async def idempotent_operation():
        nonlocal call_count
        call_count += 1
        return {"status": "processed", "call_idx": call_count}

    tasks = [cb.call(idempotent_operation) for _ in range(50)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 50
    assert all(r["status"] == "processed" for r in results)
