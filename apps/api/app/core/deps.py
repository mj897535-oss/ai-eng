"""FastAPI Reusable Dependencies & Authentication Middleware.

Enforces:
- Cookie-based session extraction (with Authorization Bearer fallback).
- Session existence and validity against Redis/store.
- Automatic CSRF header validation on state-mutating requests.
- Single reusable role policy enforcement via `require_roles(...)`.
- Forced password change enforcement for imported accounts.
"""

import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.csrf import verify_csrf_token
from app.core.database import get_db
from app.core.session import session_store
from app.models.identity import User, UserRole


async def get_current_session(
    request: Request,
    cookie_session_id: Annotated[str | None, Cookie(alias=settings.SESSION_COOKIE_NAME)] = None,
    auth_header: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, Any]:
    """Extract and validate the active session."""
    session_id: str | None = cookie_session_id

    # Fallback to Bearer token header if cookie is omitted (for programmatic testing/API tools)
    if not session_id and auth_header and auth_header.startswith("Bearer "):
        session_id = auth_header.split(" ", 1)[1].strip()

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
        )

    session_data = await session_store.get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please sign in again.",
        )

    # Validate CSRF token for state-mutating HTTP methods
    verify_csrf_token(request, session_data.get("csrf_token"))

    return session_data


async def get_current_user(
    session_data: Annotated[dict[str, Any], Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Retrieve database User model for active session."""
    user_id_str = session_data.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session user reference.",
        )

    user_id = uuid.UUID(user_id_str)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this session no longer exists.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact the research administrator.",
        )

    return user


async def require_active_user(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Verify account is active and password change is not pending.
    
    If must_change_password is true, only allow access to password change endpoints.
    """
    if current_user.must_change_password:
        allowed_paths = {"/api/v1/auth/change-password", "/api/v1/auth/me", "/api/v1/auth/logout"}
        if request.url.path not in allowed_paths:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required on first login before accessing research data.",
            )
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Reusable dependency generating role verification guard."""
    async def role_checker(
        user: Annotated[User, Depends(require_active_user)],
    ) -> User:
        # Check direct role value or compatible alias
        if user.role not in allowed_roles:
            role_names = ", ".join(r.value for r in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of the following roles: {role_names}.",
            )
        return user

    return role_checker
