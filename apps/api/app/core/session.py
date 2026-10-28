"""Session Management with Redis and Memory Fallback.

Enforces:
- Cryptographically secure session IDs stored in httpOnly cookies.
- CSRF token binding per session.
- Immediate invalidation on logout.
- Session fixation prevention (new session minted upon authentication).
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.security import generate_secure_token

logger = logging.getLogger("syntaxlens.session")


class SessionStore:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._redis_failed: bool = False
        self._memory_store: dict[str, dict[str, Any]] = {}
        self._user_sessions: dict[str, set[str]] = {}

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
                logger.warning("Redis unavailable (%s); falling back to in-memory session store.", e)
                self._redis = None
                self._redis_failed = True
        return self._redis

    async def create_session(
        self,
        user_id: uuid.UUID,
        email: str,
        role: str,
        must_change_password: bool,
        participant_id: uuid.UUID | None = None,
        participant_code: str | None = None,
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        """Create a new session, returning (session_id, csrf_token)."""
        session_id = generate_secure_token(32)
        csrf_token = generate_secure_token(32)
        now = time.time()

        payload = {
            "session_id": session_id,
            "user_id": str(user_id),
            "email": email,
            "role": role,
            "must_change_password": must_change_password,
            "participant_id": str(participant_id) if participant_id else None,
            "participant_code": participant_code,
            "csrf_token": csrf_token,
            "ip_hash": ip_hash,
            "user_agent": user_agent,
            "created_at": now,
            "last_active_at": now,
        }

        r = await self._get_redis()
        if r is not None:
            try:
                pipe = r.pipeline()
                pipe.setex(
                    f"session:{session_id}",
                    settings.SESSION_EXPIRE_SECONDS,
                    json.dumps(payload),
                )
                pipe.sadd(f"user_sessions:{user_id}", session_id)
                pipe.expire(f"user_sessions:{user_id}", settings.SESSION_EXPIRE_SECONDS)
                await pipe.execute()
                return session_id, csrf_token
            except Exception as e:
                logger.error("Redis error creating session: %s; using memory fallback", e)

        # In-memory fallback
        self._memory_store[session_id] = payload
        user_key = str(user_id)
        if user_key not in self._user_sessions:
            self._user_sessions[user_key] = set()
        self._user_sessions[user_key].add(session_id)
        return session_id, csrf_token

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve active session by session_id."""
        if not session_id:
            return None

        r = await self._get_redis()
        if r is not None:
            try:
                data = await r.get(f"session:{session_id}")
                if data:
                    parsed: dict[str, Any] = json.loads(data)
                    return parsed
                return None
            except Exception as e:
                logger.error("Redis error getting session: %s; checking memory store", e)

        # In-memory fallback
        sess = self._memory_store.get(session_id)
        if sess is None:
            return None
        # Check expiry
        if time.time() - sess["created_at"] > settings.SESSION_EXPIRE_SECONDS:
            await self.delete_session(session_id)
            return None
        return sess

    async def update_session_data(self, session_id: str, updates: dict[str, Any]) -> None:
        """Update fields in an existing session."""
        sess = await self.get_session(session_id)
        if not sess:
            return
        sess.update(updates)
        sess["last_active_at"] = time.time()

        r = await self._get_redis()
        if r is not None:
            try:
                ttl = await r.ttl(f"session:{session_id}")
                if ttl > 0:
                    await r.setex(f"session:{session_id}", ttl, json.dumps(sess))
                    return
            except Exception as e:
                logger.error("Redis update error: %s", e)

        self._memory_store[session_id] = sess

    async def delete_session(self, session_id: str) -> None:
        """Invalidate a specific session."""
        r = await self._get_redis()
        if r is not None:
            try:
                data = await r.get(f"session:{session_id}")
                if data:
                    sess = json.loads(data)
                    user_id = sess.get("user_id")
                    if user_id:
                        await r.srem(f"user_sessions:{user_id}", session_id)
                await r.delete(f"session:{session_id}")
            except Exception as e:
                logger.error("Redis delete error: %s", e)

        if session_id in self._memory_store:
            sess = self._memory_store.pop(session_id)
            user_id = sess.get("user_id")
            if user_id and user_id in self._user_sessions:
                self._user_sessions[user_id].discard(session_id)

    async def delete_user_sessions(self, user_id: uuid.UUID | str) -> None:
        """Invalidate all active sessions for a user (e.g. after password reset)."""
        uid = str(user_id)
        r = await self._get_redis()
        if r is not None:
            try:
                sessions = await r.smembers(f"user_sessions:{uid}")
                if sessions:
                    pipe = r.pipeline()
                    for sid in sessions:
                        sid_str = sid.decode("utf-8") if isinstance(sid, bytes) else str(sid)
                        pipe.delete(f"session:{sid_str}")
                    pipe.delete(f"user_sessions:{uid}")
                    await pipe.execute()
            except Exception as e:
                logger.error("Redis delete user sessions error: %s", e)

        if uid in self._user_sessions:
            for sid in list(self._user_sessions[uid]):
                self._memory_store.pop(sid, None)
            self._user_sessions.pop(uid, None)


session_store = SessionStore()
