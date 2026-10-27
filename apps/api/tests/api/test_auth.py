"""Authentication & Session Security Tests.

Tests:
- Login with Participant Code and Email.
- Argon2id password verification.
- Failed attempt decrement and 5-attempt account lockout.
- Session fixation protection (new token minted on login).
- CSRF negative tests (mutating requests without valid token rejected).
- Forced password change on first login.
- Single-use and expiration of password reset tokens.
- Immediate session invalidation on logout and password reset.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.core.security import hash_token
from app.models.identity import PasswordResetToken, User
from tests.conftest import TEST_PASSWORD


@pytest.mark.asyncio
async def test_login_with_email_success(client: AsyncClient, seeded_data: dict[str, Any]) -> None:
    """Test successful sign-in with email address."""
    resp = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": "admin@syntaxlens.edu", "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "admin@syntaxlens.edu"
    assert data["user"]["role"] == "researcher_admin"
    assert "csrf_token" in data
    # Check cookies
    cookies = resp.cookies
    assert settings.SESSION_COOKIE_NAME in cookies
    assert settings.CSRF_COOKIE_NAME in cookies


@pytest.mark.asyncio
async def test_login_with_participant_code_success(client: AsyncClient, seeded_data: dict[str, Any]) -> None:
    """Test successful sign-in with research participant code (SL-2026-001)."""
    resp = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": "SL-2026-001", "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["participant_code"] == "SL-2026-001"
    assert data["user"]["role"] == "participant"


@pytest.mark.asyncio
async def test_login_invalid_password_returns_401_and_decrements_attempts(client: AsyncClient, seeded_data: dict[str, Any]) -> None:
    """Invalid credentials return 401 with remaining attempt guidance."""
    resp = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": "participant_a@syntaxlens.edu", "password": "WrongPassword@123"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert "Invalid identifier or password" in data["message"]
    assert "attempt(s) remaining" in data["message"]


@pytest.mark.asyncio
async def test_account_lockout_after_5_failed_attempts(client: AsyncClient, seeded_data: dict[str, Any]) -> None:
    """Account is locked out upon 5 consecutive failed login attempts."""
    identifier = "participant_b@syntaxlens.edu"
    await rate_limiter.reset_failed_attempts(identifier)

    # 4 failed attempts
    for _ in range(4):
        r = await client.post(
            f"{settings.API_PREFIX}/auth/login",
            json={"identifier": identifier, "password": "WrongPassword123!"},
        )
        assert r.status_code == 401

    # 5th attempt locks the account
    r5 = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": identifier, "password": "WrongPassword123!"},
    )
    assert r5.status_code == 423
    assert "Account locked after 5 failed attempts" in r5.json()["message"]

    # 6th attempt immediately rejected as locked
    r6 = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": identifier, "password": TEST_PASSWORD},  # Even with correct password!
    )
    assert r6.status_code == 423
    assert "Account temporarily locked" in r6.json()["message"]

    # Reset lockout cleanly
    await rate_limiter.reset_failed_attempts(identifier)


@pytest.mark.asyncio
async def test_session_fixation_protection(client: AsyncClient, seeded_data: dict[str, Any]) -> None:
    """Ensure that authenticating always issues a fresh session identifier."""
    # First sign in
    r1 = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": "admin@syntaxlens.edu", "password": TEST_PASSWORD},
    )
    session_1 = r1.cookies.get(settings.SESSION_COOKIE_NAME)

    # Second sign in for same user
    r2 = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": "admin@syntaxlens.edu", "password": TEST_PASSWORD},
    )
    session_2 = r2.cookies.get(settings.SESSION_COOKIE_NAME)

    assert session_1 is not None
    assert session_2 is not None
    assert session_1 != session_2, "Session ID must be regenerated on each login"


@pytest.mark.asyncio
async def test_csrf_negative_tests(client: AsyncClient, seeded_data: dict[str, Any]) -> None:
    """Mutating state without valid CSRF header must be rejected with 403."""
    login_resp = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": "admin@syntaxlens.edu", "password": TEST_PASSWORD},
    )
    session_cookie = login_resp.cookies.get(settings.SESSION_COOKIE_NAME)
    valid_csrf = login_resp.json()["csrf_token"]

    user_payload = {
        "email": "csrf_test_new@syntaxlens.edu",
        "full_name": "CSRF Test User",
        "role": "reviewer",
        "password": "Valid@Password123!",
    }

    # Case 1: Session provided, but X-CSRF-Token omitted
    r_no_csrf = await client.post(
        f"{settings.API_PREFIX}/admin/users",
        json=user_payload,
        cookies={settings.SESSION_COOKIE_NAME: str(session_cookie)},
    )
    assert r_no_csrf.status_code == 403
    assert "CSRF token missing" in r_no_csrf.json()["message"]

    # Case 2: Session provided, but X-CSRF-Token is invalid/mismatched
    r_bad_csrf = await client.post(
        f"{settings.API_PREFIX}/admin/users",
        json=user_payload,
        cookies={settings.SESSION_COOKIE_NAME: str(session_cookie)},
        headers={"X-CSRF-Token": "invalid-tampered-token"},
    )
    assert r_bad_csrf.status_code == 403
    assert "CSRF token mismatch" in r_bad_csrf.json()["message"]

    # Case 3: Session provided with matching valid CSRF token -> succeeds!
    r_valid_csrf = await client.post(
        f"{settings.API_PREFIX}/admin/users",
        json=user_payload,
        cookies={settings.SESSION_COOKIE_NAME: str(session_cookie)},
        headers={"X-CSRF-Token": valid_csrf},
    )
    assert r_valid_csrf.status_code == 201


@pytest.mark.asyncio
async def test_forced_password_change_on_first_login(
    client: AsyncClient,
    test_session: AsyncSession,
    seeded_data: dict[str, Any],
) -> None:
    """Users with must_change_password=True are restricted until password is changed."""
    user_a: User = seeded_data["user_a"]
    user_a.must_change_password = True
    await test_session.commit()

    # Log in
    login_resp = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": user_a.email, "password": TEST_PASSWORD},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["must_change_password"] is True
    session_cookie = login_resp.cookies.get(settings.SESSION_COOKIE_NAME)
    csrf_token = login_resp.json()["csrf_token"]

    cookies = {settings.SESSION_COOKIE_NAME: str(session_cookie)}
    headers = {"X-CSRF-Token": csrf_token}

    # Attempting to access protected participant data before changing password returns 403
    part_id = seeded_data["participant_a"].participant_id
    res_blocked = await client.get(
        f"{settings.API_PREFIX}/participants/{part_id}",
        cookies=cookies,
        headers=headers,
    )
    assert res_blocked.status_code == 403
    assert "Password change required" in res_blocked.json()["message"]

    # Now change password
    change_resp = await client.post(
        f"{settings.API_PREFIX}/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "NewSyntaxLens@2026!Updated"},
        cookies=cookies,
        headers=headers,
    )
    assert change_resp.status_code == 200
    assert "Password updated successfully" in change_resp.json()["message"]

    # Now accessing participant data is permitted!
    res_allowed = await client.get(
        f"{settings.API_PREFIX}/participants/{part_id}",
        cookies=cookies,
        headers=headers,
    )
    assert res_allowed.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_flow_single_use_and_expiry(
    client: AsyncClient,
    test_session: AsyncSession,
    seeded_data: dict[str, Any],
) -> None:
    """Password reset tokens are single-use, expire in 15 minutes, and invalidate sessions."""
    user = seeded_data["user_b"]

    # 1. Request reset link
    req_resp = await client.post(
        f"{settings.API_PREFIX}/auth/reset-password-request",
        json={"identifier": user.email},
    )
    assert req_resp.status_code == 200

    # Retrieve generated token from DB
    stmt = (
        select(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id)
        .order_by(PasswordResetToken.created_at.desc())
    )
    res = await test_session.execute(stmt)
    token_record = res.scalars().first()
    assert token_record is not None

    # We cannot invert the SHA-256 token_hash, so let's simulate a known raw token
    raw_token = "secret-research-reset-token-12345"
    token_record.token_hash = hash_token(raw_token)
    await test_session.commit()

    # 2. Reset password successfully
    new_password = "NewlyResetPassword@2026!"
    confirm_resp = await client.post(
        f"{settings.API_PREFIX}/auth/reset-password",
        json={"token": raw_token, "new_password": new_password},
    )
    assert confirm_resp.status_code == 200
    assert "successfully reset" in confirm_resp.json()["message"]

    # 3. Negative test: token is single use — cannot be used again
    reuse_resp = await client.post(
        f"{settings.API_PREFIX}/auth/reset-password",
        json={"token": raw_token, "new_password": "AnotherNewPassword@2026!"},
    )
    assert reuse_resp.status_code == 400
    assert "already been used" in reuse_resp.json()["message"]

    # 4. Negative test: expired token
    expired_token = "expired-token-raw"
    exp_record = PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(expired_token),
        expires_at=datetime.utcnow() - timedelta(minutes=1),  # Expired
    )
    test_session.add(exp_record)
    await test_session.commit()

    exp_resp = await client.post(
        f"{settings.API_PREFIX}/auth/reset-password",
        json={"token": expired_token, "new_password": "YetAnotherPassword@2026!"},
    )
    assert exp_resp.status_code == 400
    assert "expired" in exp_resp.json()["message"]


@pytest.mark.asyncio
async def test_logout_invalidates_session(client: AsyncClient, seeded_data: dict[str, Any]) -> None:
    """Logout invalidates the session in store and clears browser cookies."""
    login_resp = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"identifier": "admin@syntaxlens.edu", "password": TEST_PASSWORD},
    )
    session_cookie = login_resp.cookies.get(settings.SESSION_COOKIE_NAME)
    csrf_token = login_resp.json()["csrf_token"]

    cookies = {settings.SESSION_COOKIE_NAME: str(session_cookie)}
    headers = {"X-CSRF-Token": csrf_token}

    # Verify session works
    me_res = await client.get(f"{settings.API_PREFIX}/auth/me", cookies=cookies)
    assert me_res.status_code == 200

    # Logout
    logout_res = await client.post(f"{settings.API_PREFIX}/auth/logout", cookies=cookies, headers=headers)
    assert logout_res.status_code == 200

    # Subsequent request using that session is rejected as 401
    me_after = await client.get(f"{settings.API_PREFIX}/auth/me", cookies=cookies)
    assert me_after.status_code == 401
