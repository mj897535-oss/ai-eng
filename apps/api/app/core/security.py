"""Security and Cryptography Utilities.

Enforces:
- Argon2id password hashing per OWASP ASVS L2.
- SHA-256 hashing for single-use reset tokens and pseudonymized IP addresses.
- Cryptographically secure token generation.
- Password complexity validation.
"""

import hashlib
import re
import secrets

from passlib.context import CryptContext  # type: ignore[import-untyped]

from app.core.config import settings

# Argon2id context configuration
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__type="ID",  # Argon2id hybrid
)

PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_\-+=\[\]{}|:;<>,./~`])[A-Za-z\d@$!%*?&#^()_\-+=\[\]{}|:;<>,./~`]{8,}$"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored Argon2id hash."""
    try:
        return bool(pwd_context.verify(plain_password, hashed_password))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash password using Argon2id."""
    return str(pwd_context.hash(password))


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """Validate that password meets minimum academic research security standards:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special symbol
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not PASSWORD_REGEX.match(password):
        return False, (
            "Password must contain at least one uppercase letter, one lowercase letter, "
            "one digit, and one special character."
        )
    return True, None


def hash_token(token: str) -> str:
    """SHA-256 hash for reset tokens so raw tokens are never persisted in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_ip(ip: str | None) -> str | None:
    """Pseudonymize IP address via salted SHA-256 hash.
    
    RESEARCH INTEGRITY & PRIVACY RULE:
    Direct client IPs are never stored in research logs to prevent participant re-identification.
    """
    if not ip:
        return None
    salt = settings.APP_SECRET_KEY[:32]
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:32]


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate cryptographically secure URL-safe random string."""
    return secrets.token_urlsafe(nbytes)
