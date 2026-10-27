"""CSRF Protection Infrastructure.

Enforces:
- Header-based and session-bound CSRF token validation on all state-mutating requests.
- Safe methods (GET, HEAD, OPTIONS) are exempt.
- Public authentication bootstrap endpoints (login, password reset request) are exempt.
"""

from fastapi import HTTPException, Request, status

EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/reset-password-request",
    "/api/v1/auth/reset-password",
    "/docs",
    "/openapi.json",
    "/health",
    "/ready",
}


def verify_csrf_token(request: Request, session_csrf_token: str | None) -> None:
    """Validate incoming X-CSRF-Token against session CSRF token."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return

    path = request.url.path
    if path in EXEMPT_PATHS:
        return

    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing in X-CSRF-Token header.",
        )

    if not session_csrf_token or csrf_header != session_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch or session expired.",
        )
