"""Authentication API Router.

Enforces:
- Login with Participant Code (e.g. SL-2026-001) or Email + Password.
- Argon2id password verification.
- HTTP-only, secure, SameSite session cookies.
- CSRF double-submit protection.
- Sliding-window rate limiting and 5-attempt account lockout.
- Password reset via single-use, 15-minute expiring tokens.
- Forced password change on first login.
- Append-only audit logging on all security events.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_session, get_current_user
from app.core.rate_limit import rate_limiter
from app.core.security import (
    generate_secure_token,
    get_password_hash,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.core.session import session_store
from app.models.identity import PasswordResetToken, User, UserRole
from app.models.research import Participant
from app.services.audit import AuditService
from app.services.email import email_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# --- Schemas ---

class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Participant research code (e.g. SL-2026-001) or email address")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    participant_id: uuid.UUID | None = None
    participant_code: str | None = None


class LoginResponse(BaseModel):
    user: UserResponse
    csrf_token: str
    message: str = "Authentication successful"


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New secure password meeting complexity policy")


class ResetPasswordRequest(BaseModel):
    identifier: str = Field(..., description="Participant research code or email address")


class ResetPasswordConfirm(BaseModel):
    token: str = Field(..., description="Single-use reset token from email")
    new_password: str = Field(..., description="New secure password")


# --- Endpoints ---

@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """Authenticate via email or participant ID."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent")

    # 1. Check IP rate limit (max 30 requests/min)
    allowed, _ = await rate_limiter.check_rate_limit(f"ip_login:{client_ip}", max_requests=settings.RATE_LIMIT_PER_MINUTE)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts from this address. Please wait a moment before retrying.",
        )

    # 2. Check if account identifier is locked out
    is_locked, remaining_seconds = await rate_limiter.is_account_locked(req.identifier)
    if is_locked:
        minutes = max(1, remaining_seconds // 60)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account temporarily locked due to multiple failed attempts. Please try again in {minutes} minute(s).",
        )

    # 3. Lookup User (by email or via research participant_code)
    user: User | None = None
    participant: Participant | None = None

    if "@" in req.identifier:
        result = await db.execute(select(User).where(User.email == req.identifier.strip().lower()))
        user = result.scalar_one_or_none()
    else:
        # Lookup by research code
        p_res = await db.execute(
            select(Participant).where(Participant.research_code == req.identifier.strip().upper())
        )
        participant = p_res.scalar_one_or_none()
        if participant:
            u_res = await db.execute(select(User).where(User.id == participant.user_id))
            user = u_res.scalar_one_or_none()

    # 4. Verify Password
    if not user or not verify_password(req.password, user.hashed_password):
        # Record failure and trigger lockout if 5 attempts reached
        attempts, now_locked, lockout_secs = await rate_limiter.record_failed_attempt(req.identifier)
        await AuditService.log_login_failure(
            db=db,
            identifier=req.identifier,
            reason="Invalid credentials",
            ip_address=client_ip,
            user_agent=user_agent,
        )

        if now_locked:
            minutes = max(1, lockout_secs // 60)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked after {attempts} failed attempts. Please try again in {minutes} minutes.",
            )

        remaining_attempts = max(0, settings.MAX_FAILED_LOGIN_ATTEMPTS - attempts)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid identifier or password. {remaining_attempts} attempt(s) remaining before lockout.",
        )

    # 5. Check if user is active
    if not user.is_active:
        await AuditService.log_login_failure(
            db=db,
            identifier=req.identifier,
            reason="Account deactivated",
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact the research team.",
        )

    # 6. Reset failed attempts upon successful authentication
    await rate_limiter.reset_failed_attempts(req.identifier)

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # If participant wasn't loaded earlier, look it up for participant users
    if not participant and user.role in {UserRole.PARTICIPANT, UserRole.STUDENT}:
        p_res = await db.execute(select(Participant).where(Participant.user_id == user.id))
        participant = p_res.scalar_one_or_none()

    # 7. Mint session (Session Fixation Prevention: mint fresh token on auth)
    session_id, csrf_token = await session_store.create_session(
        user_id=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        must_change_password=user.must_change_password,
        participant_id=participant.participant_id if participant else None,
        participant_code=participant.research_code if participant else None,
        ip_hash=client_ip,
        user_agent=user_agent,
    )

    # 8. Set secure HTTP-only cookies
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_EXPIRE_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    # Set double-submit CSRF cookie (readable by frontend client)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.SESSION_EXPIRE_SECONDS,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )

    # 9. Log successful login
    await AuditService.log_login_success(
        db=db,
        user_id=user.id,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return LoginResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            participant_id=participant.participant_id if participant else None,
            participant_code=participant.research_code if participant else None,
        ),
        csrf_token=csrf_token,
        message="Sign-in successful",
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: Annotated[dict[str, Any], Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Terminate the current session."""
    session_id = session["session_id"]
    await session_store.delete_session(session_id)

    # Clear cookies
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")

    # Audit log
    user_id = uuid.UUID(session["user_id"])
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await AuditService.log_logout(
        db=db,
        user_id=user_id,
        role=session.get("role", "unknown"),
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {"message": "You have been securely signed out."}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    session: Annotated[dict[str, Any], Depends(get_current_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Return profile of the currently signed-in user."""
    participant_id: uuid.UUID | None = None
    participant_code: str | None = None

    if current_user.role in {UserRole.PARTICIPANT, UserRole.STUDENT}:
        p_res = await db.execute(select(Participant).where(Participant.user_id == current_user.id))
        participant = p_res.scalar_one_or_none()
        if participant:
            participant_id = participant.participant_id
            participant_code = participant.research_code

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        is_active=current_user.is_active,
        must_change_password=current_user.must_change_password,
        participant_id=participant_id,
        participant_code=participant_code,
    )


@router.get("/csrf")
async def get_csrf_token(
    session: Annotated[dict[str, Any], Depends(get_current_session)],
) -> dict[str, str]:
    """Retrieve CSRF token for the authenticated session."""
    return {"csrf_token": session.get("csrf_token", "")}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[dict[str, Any], Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Change user password. Required on first login for imported accounts."""
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed.",
        )

    valid, reason = validate_password_strength(req.new_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason or "Password does not meet research security criteria.",
        )

    current_user.hashed_password = get_password_hash(req.new_password)
    current_user.must_change_password = False
    await db.commit()

    # Update session state
    await session_store.update_session_data(session["session_id"], {"must_change_password": False})

    # Log password change
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await AuditService.log_password_change(
        db=db,
        user_id=current_user.id,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {"message": "Password updated successfully."}


@router.post("/reset-password-request")
async def request_password_reset(
    req: ResetPasswordRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Request a single-use password reset link.
    
    Protects user enumeration: returns identical success message whether email exists or not.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent")

    # Rate limit password reset requests per IP (max 5 per hour)
    allowed, _ = await rate_limiter.check_rate_limit(f"ip_reset:{client_ip}", max_requests=5, window_seconds=3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please check your inbox or try again in an hour.",
        )

    # Find user by email or research code
    user: User | None = None
    if "@" in req.identifier:
        result = await db.execute(select(User).where(User.email == req.identifier.strip().lower()))
        user = result.scalar_one_or_none()
    else:
        p_res = await db.execute(
            select(Participant).where(Participant.research_code == req.identifier.strip().upper())
        )
        participant = p_res.scalar_one_or_none()
        if participant:
            u_res = await db.execute(select(User).where(User.id == participant.user_id))
            user = u_res.scalar_one_or_none()

    if user and user.is_active:
        # Generate single-use random token
        raw_token = generate_secure_token(32)
        token_hashed = hash_token(raw_token)
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

        reset_record = PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hashed,
            expires_at=expires_at,
            created_at=now,
        )
        db.add(reset_record)
        await db.commit()

        # Send email (Mailpit in dev)
        email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=raw_token,
            recipient_name=user.full_name,
        )

    await AuditService.log_password_reset_request(
        db=db,
        user_id=user.id if user else None,
        identifier=req.identifier,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {
        "message": (
            "If an active account was found matching that identifier, a secure reset link "
            "has been sent to the associated email address. The link expires in 15 minutes."
        )
    }


@router.post("/reset-password")
async def confirm_password_reset(
    req: ResetPasswordConfirm,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Complete password reset using the emailed single-use token."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    # Validate password complexity
    valid, reason = validate_password_strength(req.new_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason or "Password does not meet research security criteria.",
        )

    # Hash incoming token and find match
    token_hashed = hash_token(req.token)
    stmt = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hashed,
        PasswordResetToken.used_at.is_(None),
    )
    result = await db.execute(stmt)
    reset_record = result.scalar_one_or_none()

    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid or has already been used.",
        )

    now = datetime.now(UTC)
    exp = reset_record.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)

    if now > exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired. Please request a new link.",
        )

    # Mark token used
    reset_record.used_at = now

    # Update user password and clear lockout
    user_stmt = select(User).where(User.id == reset_record.user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one()

    user.hashed_password = get_password_hash(req.new_password)
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    # Reset Redis failed attempts
    await rate_limiter.reset_failed_attempts(user.email)

    # Invalidate all existing sessions across devices
    await session_store.delete_user_sessions(user.id)

    # Audit log
    await AuditService.log_password_reset_complete(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {"message": "Your password has been successfully reset. You may now sign in."}
