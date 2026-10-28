"""Rate Limiting and Account Lockout Infrastructure.

Enforces:
- Account lockout after 5 consecutive failed login attempts.
- 15-minute lockout cooldown.
- Sliding-window IP rate limiting on authentication and sensitive endpoints.
- In-memory fallback for test and local development when Redis is offline.
"""

import asyncio
import logging
import time
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("syntaxlens.ratelimit")


class RateLimiter:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._redis_failed: bool = False
        self._memory_limits: dict[str, list[float]] = {}
        self._memory_lockouts: dict[str, dict[str, Any]] = {}

    async def _get_redis(self) -> aioredis.Redis | None:
        if settings.ENVIRONMENT in ("testing", "test"):
            return None
        if self._redis is None and not self._redis_failed:
            try:
                client = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=0.2,
                    socket_timeout=0.2,
                )
                await asyncio.wait_for(client.ping(), timeout=0.2)
                self._redis = client
            except Exception as e:
                logger.debug("Redis unavailable (%s); using in-memory rate limiter.", e)
                self._redis = None
                self._redis_failed = True
        return self._redis

    async def is_account_locked(self, identifier: str) -> tuple[bool, int]:
        """Check if an identifier (email or participant code) is locked.
        Returns (is_locked, seconds_remaining).
        """
        key = f"lockout:{identifier.lower()}"
        now = time.time()

        r = await self._get_redis()
        if r is not None:
            try:
                ttl = await r.ttl(key)
                if ttl > 0:
                    return True, ttl
                return False, 0
            except Exception as e:
                logger.error("Redis lockout check error: %s", e)

        # In-memory check
        info = self._memory_lockouts.get(identifier.lower())
        if info:
            locked_until = info.get("locked_until", 0)
            if locked_until > 0:
                if now < locked_until:
                    return True, int(locked_until - now)
                # Lockout Expired
                self._memory_lockouts.pop(identifier.lower(), None)
        return False, 0

    async def record_failed_attempt(self, identifier: str) -> tuple[int, bool, int]:
        """Record a failed login attempt.
        Returns (current_attempts, is_now_locked, lockout_seconds).
        """
        ident = identifier.lower()
        now = time.time()
        lockout_secs = settings.LOCKOUT_DURATION_MINUTES * 60
        window_secs = 900  # 15 minutes window

        r = await self._get_redis()
        if r is not None:
            try:
                fail_key = f"failed_attempts:{ident}"
                count = await r.incr(fail_key)
                if count == 1:
                    await r.expire(fail_key, window_secs)
                if count >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                    lock_key = f"lockout:{ident}"
                    await r.setex(lock_key, lockout_secs, "locked")
                    await r.delete(fail_key)
                    return count, True, lockout_secs
                return count, False, 0
            except Exception as e:
                logger.error("Redis record failed attempt error: %s", e)

        # In-memory
        info = self._memory_lockouts.get(ident, {"attempts": 0, "first_fail": now, "locked_until": 0})
        if now - info["first_fail"] > window_secs:
            info["attempts"] = 0
            info["first_fail"] = now

        info["attempts"] += 1
        if info["attempts"] >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            info["locked_until"] = now + lockout_secs
            self._memory_lockouts[ident] = info
            return info["attempts"], True, lockout_secs

        self._memory_lockouts[ident] = info
        return info["attempts"], False, 0

    async def reset_failed_attempts(self, identifier: str) -> None:
        """Reset failed attempts on successful login."""
        ident = identifier.lower()
        r = await self._get_redis()
        if r is not None:
            try:
                await r.delete(f"failed_attempts:{ident}")
                await r.delete(f"lockout:{ident}")
            except Exception as e:
                logger.error("Redis reset failed attempts error: %s", e)

        self._memory_lockouts.pop(ident, None)

    async def check_rate_limit(self, key: str, max_requests: int = 30, window_seconds: int = 60) -> tuple[bool, int]:
        """Sliding window rate limit.
        Returns (is_allowed, remaining_requests).
        """
        now = time.time()
        r = await self._get_redis()
        if r is not None:
            try:
                redis_key = f"ratelimit:{key}"
                pipe = r.pipeline()
                pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
                pipe.zadd(redis_key, {str(now): now})
                pipe.zcard(redis_key)
                pipe.expire(redis_key, window_seconds)
                results = await pipe.execute()
                current_count = results[2]
                if current_count > max_requests:
                    return False, 0
                return True, max_requests - current_count
            except Exception as e:
                logger.error("Redis rate limit error: %s", e)

        # In-memory sliding window
        window_start = now - window_seconds
        timestamps = self._memory_limits.get(key, [])
        valid_timestamps = [t for t in timestamps if t > window_start]
        if len(valid_timestamps) >= max_requests:
            self._memory_limits[key] = valid_timestamps
            return False, 0
        valid_timestamps.append(now)
        self._memory_limits[key] = valid_timestamps
        return True, max_requests - len(valid_timestamps)


rate_limiter = RateLimiter()
