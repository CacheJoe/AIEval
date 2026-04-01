"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.db.session import init_db
from app.utils.config import get_settings
from app.utils.exceptions import AppException
from app.utils.logging import configure_logging

# NEW — import seed function
from app.seed_data import main as seed_data


settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize runtime resources."""
    settings.ensure_directories()

    if settings.auto_create_tables:

        # Create tables
        init_db()

        logger.info(
            "Database tables ensured for environment %s",
            settings.environment,
        )

        # NEW — seed default users safely
        try:

            seed_data()

            logger.info(
                "Seed data ensured (admin and faculty accounts ready)."
            )

        except Exception as exc:

            logger.exception(
                "Seed data initialization failed: %s",
                exc,
            )

    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Academic Integrity & Automated Lab Evaluation System backend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    """Simple root endpoint."""
    return {
        "message": settings.app_name,
        "docs": "/docs",
    }


@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """Return application-level errors in a consistent envelope."""
    logger.warning(
        "Application error on %s: %s",
        request.url.path,
        exc.message,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return request validation errors."""
    logger.warning(
        "Validation error on %s: %s",
        request.url.path,
        exc.errors(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Request validation failed.",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch and log unexpected failures."""
    logger.exception(
        "Unhandled error on %s",
        request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "An unexpected internal server error occurred.",
            "details": None,
        },
    )
