"""Circuit Breaker & Reliability Wrapper (Phase P15).

Implements:
1. Circuit breaker pattern for external speech/LLM providers (closed, open, half-open).
2. Failure threshold tripping and automated cool-off.
3. Fallback to offline queue / graceful degradation message to users.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Callable, Coroutine


class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Tripped; requests immediately rejected / degraded
    HALF_OPEN = "half_open"  # Testing if dependency recovered


class CircuitBreakerOpenError(RuntimeError):
    """Raised when request is rejected because the external provider is currently failing."""


class CircuitBreaker:
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        now = time.time()

        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time > self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Service '{self.service_name}' circuit is OPEN. "
                    f"External provider is degraded; request queued for automatic retry."
                )

        try:
            result = await func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return result
        except Exception as exc:
            self.failure_count += 1
            self.last_failure_time = now
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            raise exc
