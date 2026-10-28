"""SyntaxLens FastAPI Application Entry Point.

Provides structured JSON logging, request IDs, consistent error schemas,
health/readiness probes, and core security routers.
"""

import time
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.analysis import router as analysis_router
from app.api.v1.audio import router as audio_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.config import router as config_router
from app.api.v1.consent import router as consent_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.export import router as export_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.participants import router as participants_router
from app.api.v1.resources import router as resources_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.tutor import router as tutor_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.database import async_engine
from app.core.logging import logger


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
    detail: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting SyntaxLens API Service...")
    yield
    logger.info("Shutting down SyntaxLens API Service...")


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


# Request ID & Structured Logging Middleware
@app.middleware("http")
async def request_id_and_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Any],
) -> Response:
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id
    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id

        # Log request summary
        extra_fields = {
            "request_id": req_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} in {duration_ms}ms",
            extra=extra_fields,
        )
        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}",
            extra={"request_id": req_id, "duration_ms": duration_ms},
            exc_info=True,
        )
        raise exc


# Security Headers Middleware (OWASP ASVS L2 baseline + HSTS)
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
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';"
    )
    return response


# Include Core Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(audit_logs_router, prefix=settings.API_PREFIX)
app.include_router(resources_router, prefix=settings.API_PREFIX)
app.include_router(participants_router, prefix=settings.API_PREFIX)
app.include_router(consent_router, prefix=settings.API_PREFIX)
app.include_router(onboarding_router, prefix=settings.API_PREFIX)
app.include_router(config_router, prefix=settings.API_PREFIX)
app.include_router(audio_router, prefix=settings.API_PREFIX)
app.include_router(analysis_router, prefix=settings.API_PREFIX)
app.include_router(reviews_router, prefix=settings.API_PREFIX)
app.include_router(tutor_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)
app.include_router(export_router, prefix=settings.API_PREFIX)


# Health & Readiness Probes
@app.get(f"{settings.API_PREFIX}/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Liveness probe verifying service availability and frozen versions."""
    return {
        "status": "healthy",
        "service": "SyntaxLens Backend API",
        "environment": settings.ENVIRONMENT,
        "rubric_version": settings.DEFAULT_RUBRIC_VERSION,
        "prompt_version": settings.DEFAULT_PROMPT_VERSION,
        "stt_provider": settings.STT_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
    }


@app.get(f"{settings.API_PREFIX}/ready", tags=["System"])
async def readiness_check() -> dict[str, Any]:
    """Readiness probe checking database connectivity and system health."""
    db_ok = False
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.warning(f"Readiness DB probe failed: {e}")
        db_ok = False

    return {
        "status": "ready" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "storage": "configured",
    }


# Global Exception Handlers Returning Consistent Error Schema
@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        423: "ACCOUNT_LOCKED",
        429: "TOO_MANY_REQUESTS",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": code,
            "message": str(exc.detail),
            "request_id": req_id,
            "detail": None,
        },
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return await starlette_http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Input validation failed. Please check your request parameters.",
            "request_id": req_id,
            "detail": str(exc.errors()),
        },
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred while processing your request.",
            "request_id": req_id,
            "detail": str(exc) if settings.DEBUG else "Please contact the research administrator.",
        },
        headers={"X-Request-ID": req_id},
    )
