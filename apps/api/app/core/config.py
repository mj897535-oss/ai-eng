"""Application Settings and Configuration."""


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

    # Security
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # Research Protocol Defaults
    DEFAULT_RUBRIC_VERSION: str = "v1.0-jam-phd"
    DEFAULT_PROMPT_VERSION: str = "v1.0-tutor-ladder"
    DEFAULT_MODEL_VERSION: str = "mock-syntax-v1"
    DEFAULT_STT_VERSION: str = "mock-stt-v1"
    MAX_COHORT_SIZE: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
