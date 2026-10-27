"""SyntaxLens FastAPI Application Entry Point."""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: Initialize resources / verify configs
    yield
    # Shutdown: Clean up connections


app = FastAPI(
    title="SyntaxLens Research Platform API",
    description="Research-grade spoken English syntactic assessment and personalized tutoring API.",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Security Headers Middleware (OWASP ASVS L2 baseline)
@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Any],
) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; frame-ancestors 'none'; object-src 'none';"
    )
    return response


@app.get(f"{settings.API_PREFIX}/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """System health check endpoint verifying service status and versions."""
    return {
        "status": "healthy",
        "service": "SyntaxLens Backend",
        "environment": settings.ENVIRONMENT,
        "rubric_version": settings.DEFAULT_RUBRIC_VERSION,
        "prompt_version": settings.DEFAULT_PROMPT_VERSION,
        "stt_provider": settings.STT_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ensure no swallowed exceptions and plain-language error reporting."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred while processing your request.",
            "detail": str(exc) if settings.DEBUG else "Please contact the research administrator.",
        },
    )
