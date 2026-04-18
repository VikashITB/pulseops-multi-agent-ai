from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.routes import router as main_router
from app.core.config import settings
from app.core.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_application")

    try:
        app.state.redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )

        await app.state.redis.ping()

        logger.info("redis_connected")

    except Exception as exc:
        app.state.redis = None

        logger.warning(
            "redis_connection_failed",
            error=str(exc),
        )

    yield

    if app.state.redis:
        try:
            await app.state.redis.aclose()
        except Exception:
            pass

    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="PulseOps AI",
        version="1.0.0",
        description="Agentic AI system for multi-step task execution",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,
    )

    app.include_router(
        main_router,
        prefix="/api/v1",
    )

    app.include_router(
        auth_router,
        prefix="/api/v1/auth",
    )

    @app.get("/", tags=["system"])
    async def root():
        return {
            "message": "PulseOps AI running"
        }

    @app.get("/health", tags=["system"])
    async def health():
        return {
            "status": "ok",
            "redis": app.state.redis is not None,
            "version": "1.0.0",
        }

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.exception(
            "unhandled_exception",
            path=str(request.url.path),
            error=str(exc),
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error"
            },
        )

    return app


app = create_app()