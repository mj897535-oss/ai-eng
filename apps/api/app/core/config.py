"""Application Settings and Configuration."""

from typing import Any, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_SECRET_KEY: str = "dev-secret-key-must-be-replaced-in-production-environments-64-bytes"
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database
    POSTGRES_USER: str = "syntaxlens_user"
    POSTGRES_PASSWORD: str = "syntaxlens_dev_password_only"
    POSTGRES_DB: str = "syntaxlens"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = (
        "postgresql+asyncpg://syntaxlens_user:syntaxlens_dev_password_only@localhost:5432/syntaxlens"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg2://syntaxlens_user:syntaxlens_dev_password_only@localhost:5432/syntaxlens"
    )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage (S3 / MinIO)
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "syntaxlens_minio_admin"
    S3_SECRET_KEY: str = "syntaxlens_minio_secret_key_123"
    S3_BUCKET_NAME: str = "syntaxlens-audio"
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False
    S3_PRESIGNED_EXPIRATION_SECONDS: int = 900

    # SMTP (Mailpit in dev)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str = "no-reply@syntaxlens.edu"
    EMAILS_FROM_NAME: str = "SyntaxLens Research Platform"

    # Providers
    STT_PROVIDER: str = "mock"
    LLM_PROVIDER: str = "mock"

    # Security & Auth (SRS §12-13, ASVS L2)
    JWT_ALGORITHM: str = "HS256"
    SESSION_EXPIRE_SECONDS: int = 28800  # 8 hours
    RESET_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes single-use
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    RATE_LIMIT_PER_MINUTE: int = 30
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    SESSION_COOKIE_NAME: str = "syntaxlens_session"
    CSRF_COOKIE_NAME: str = "syntaxlens_csrf"

    # Research Protocol Defaults
    DEFAULT_RUBRIC_VERSION: str = "v1.0-jam-phd"
    DEFAULT_PROMPT_VERSION: str = "v1.0-tutor-ladder"
    DEFAULT_ASSESSOR_PROMPT_VERSION: str = "v1.0-assessor"
    DEFAULT_MODEL_VERSION: str = "mock-syntax-v1"
    DEFAULT_STT_VERSION: str = "mock-stt-v1"
    MAX_COHORT_SIZE: int = 120

    # Google OAuth / SSO Configuration
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # Phase P8 Error Analysis & Evidence Lens Configuration
    ANNOTATION_CONFIDENCE_THRESHOLD: float = 0.85
    REVIEW_ALL_MODE: bool = False
    MAX_ANALYSIS_RETRIES: int = 3
    PARTICIPANT_VISIBILITY_DEFAULT: bool = False
    GEMINI_API_KEY: str | None = None
    LLM_MODEL: str = "gemini-1.5-pro"

    # Phase P9 Reviewer Cockpit Configuration
    DOUBLE_REVIEW_MODE: bool = False
    REQUIRE_ALL_RESOLVED_FOR_VERIFIED: bool = True

    # Phase P10 AI Tutor & Hint Ladder Configuration
    REQUIRE_VERIFIED_PRETEST_FOR_TUTORING: bool = True
    DEFAULT_TUTOR_PROMPT_VERSION: str = "v1.0-tutor-ladder"
    TUTOR_MAX_HINT_LEVEL: int = 3

    # Phase P11 Session History & Recurrence Configuration
    PRACTICE_IDLE_TIMEOUT_SECONDS: int = 60
    EXPECTED_SESSIONS_PER_WEEK: int = 3
    EXPECTED_PRACTICE_MINUTES_PER_SESSION: int = 15

    # Phase P4 Protocol & Onboarding Configuration
    COLLECT_NAME: bool = False
    AGE_COLLECTION_MODE: Literal["exact", "band"] = "band"
    COLLECT_GEOGRAPHY: bool = True
    RESEARCH_CODE_PREFIX: str = "SL-2026-"
    BLIND_STUDY_GROUP_FROM_PARTICIPANTS: bool = True
    CURRENT_CONSENT_VERSION: str = "v1.0-jam-2026"
    CONSENT_EFFECTIVE_DATE: str = "2026-01-15"
    CONSENT_DOCUMENT_TITLE: str = "Informed Consent for Syntactic Assessment & Personalized Tutoring Study"
    CONSENT_DOCUMENT_TEXT: str = """# Research Participant Informed Consent

**Study Title:** Longitudinal Evaluation of Form-Focused AI Conversational Tutoring on Spoken English Syntactic Accuracy
**Principal Investigator:** Research Team, Department of Linguistics and Language Technology
**Protocol Version:** v1.0-jam-2026 (Effective: January 15, 2026)

### 1. Purpose of the Study
You are invited to participate in a doctoral research study examining spoken English grammatical development in engineering college students. The purpose is to evaluate whether short, personalized conversational interactions with an AI tutor targeting specific syntactic structures assist learners in noticing and self-correcting grammar patterns in spontaneous speech.

### 2. Procedures
If you agree to participate, you will:
1. Complete a brief demographic profile (mother tongue, schooling medium).
2. Record an initial 1-minute spontaneous speaking response on a familiar daily topic (pre-test).
3. If allocated to the tutoring group, participate in short speaking practice sessions over a 3-week study period.
4. Record a 1-minute post-test speaking sample on a comparable topic.

### 3. Audio & Data Handling
- **Pseudonymity:** You are assigned a unique, random research code (e.g., `SL-2026-0001`). Your real name and email are kept in a separate secure authentication store and are never attached to research recordings or analysis files.
- **Recordings:** Spoken audio is stored in private, encrypted object storage. Audio is used solely for speech-to-text transcription and grammatical analysis. No audio will ever be published publicly.
- **No Evaluation Grading:** This study is strictly non-evaluative. Your performance has no connection to academic grading, college marks, or formal English certification.

### 4. Voluntary Participation and Right to Withdraw
Participation is entirely voluntary. You may choose to withdraw from this study at any time without giving a reason and without any negative consequences. Upon withdrawal, further data collection ceases immediately, and your records are handled in accordance with the study retention protocol."""
    WITHDRAWAL_POLICY_TEXT: str = """### Right to Withdraw
You may withdraw from this research study at any time. When you click 'Withdraw Consent':
1. All future audio collection, assessments, and tutoring sessions are immediately stopped.
2. Your account is flagged as withdrawn and quarantined from future study periods.
3. Your data will not be included in subsequent research publications or aggregate models."""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def assemble_db_urls(self) -> "Settings":
        db_url = str(self.DATABASE_URL)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
            self.DATABASE_URL = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not db_url.startswith("postgresql+asyncpg://") and not db_url.startswith("sqlite"):
            self.DATABASE_URL = db_url

        if "localhost:5432" not in self.DATABASE_URL and ("localhost:5432" in self.DATABASE_URL_SYNC or self.DATABASE_URL_SYNC.startswith("postgres")):
            sync_url = self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
            if sync_url.startswith("postgres://"):
                sync_url = sync_url.replace("postgres://", "postgresql+psycopg2://", 1)
            self.DATABASE_URL_SYNC = sync_url

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
