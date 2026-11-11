import logging
import os
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from backend.src.api.router import api_router
from backend.src.core.config import settings
from backend.src.core.database import engine
from backend.src.core.errors import register_error_handlers
from backend.src.core.logging import setup_logging

# Initialize structured logging
setup_logging()
logger = logging.getLogger("smart_inventory.startup")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup connectivity tests and clean shutdown."""
    current_env = (os.getenv("ENVIRONMENT") or settings.ENVIRONMENT).lower()
    is_testing = current_env in ("testing", "test") or bool(os.getenv("PYTEST_CURRENT_TEST"))
    if is_testing:
        yield
        return

    logger.info("Initializing Smart Inventory FastAPI application [%s]...", settings.ENVIRONMENT)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connectivity verified: connected successfully via asyncpg.")
    except Exception as exc:
        logger.error(
            "CRITICAL: Failed to connect to database at startup: %s. "
            "Please verify DATABASE_URL in your environment variables.",
            exc,
        )
        if settings.is_production:
            raise
    yield
    # Graceful shutdown: close connection pool
    await engine.dispose()
    logger.info("Database connection pool disposed cleanly.")


def create_application() -> FastAPI:
    """FastAPI application factory with security hardening."""
    # Temporarily enable FastAPI Swagger documentation in production for deployment verification
    docs_url = f"{settings.API_V1_PREFIX}/docs"
    redoc_url = f"{settings.API_V1_PREFIX}/redoc"
    openapi_url = f"{settings.API_V1_PREFIX}/openapi.json"

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan,
    )

    # Attach OWASP Security Headers Middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    # Register CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Standard Error Handlers (API.md format)
    register_error_handlers(app)

    # Root health check endpoint
    @app.get("/health", tags=["System"])
    async def root_health() -> dict[str, str]:
        """Root health check endpoint returning application status."""
        return {
            "status": "healthy",
            "service": "smart-inventory-api",
        }

    # Convenience redirects to API v1 documentation and schema
    @app.get("/docs", include_in_schema=False)
    async def redirect_docs() -> RedirectResponse:
        return RedirectResponse(url=f"{settings.API_V1_PREFIX}/docs")

    @app.get("/openapi.json", include_in_schema=False)
    async def redirect_openapi() -> RedirectResponse:
        return RedirectResponse(url=f"{settings.API_V1_PREFIX}/openapi.json")

    @app.get("/", include_in_schema=False)
    async def redirect_root() -> RedirectResponse:
        return RedirectResponse(url=f"{settings.API_V1_PREFIX}/docs")

    # Mount Base API Router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
