from __future__ import annotations

import asyncio
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


async def _batch_flush_loop(redis: aioredis.Redis) -> None:
    """
    Background task that wakes up every BATCH_FLUSH_INTERVAL seconds and
    dispatches whatever is sitting in the Redis buffer as a single Celery
    batch job.  Runs for the lifetime of the FastAPI process.
    """
    # Late import to avoid circular imports at module load time.
    from app.queue.tasks import process_batch_task
    from app.services.batch_buffer import BatchBuffer

    buffer = BatchBuffer(redis)
    interval = buffer.flush_interval

    logger.info(
        "batch_flush_loop_started",
        flush_interval_seconds=interval,
        max_batch_size=buffer.max_batch_size,
    )

    while True:
        await asyncio.sleep(interval)

        try:
            size = await buffer.size()

            if size == 0:
                continue

            batch = await buffer.pop_batch()

            if not batch:
                continue

            logger.info(
                "periodic_batch_flush_dispatching_tasks",
                batch_size=len(batch),
                flush_interval_seconds=interval,
            )

            from app.core.orchestrator import orchestrator
            for item in batch:
                orchestrator.dispatch(item["task_id"], item["user_request"])

        except asyncio.CancelledError:
            logger.info("batch_flush_loop_cancelled")
            raise

        except Exception as exc:
            # Log and keep the loop alive — a transient Redis hiccup should
            # not kill the flush background task permanently.
            logger.warning(
                "batch_flush_loop_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_application")

    flush_task: asyncio.Task | None = None

    # ------------------------------------------------------------------ Redis
    try:
        app.state.redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )

        await app.state.redis.ping()
        logger.info("redis_connected")

        # Batch loop disabled - using immediate dispatch instead
        logger.info("batch_loop_disabled_demo_mode")

    except Exception as exc:
        app.state.redis = None
        logger.warning("redis_connection_failed", error=str(exc))

    # ----------------------------------------------------------------- yield
    yield

    # --------------------------------------------------------------- shutdown
    # Batch loop disabled - no cleanup needed

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
        allow_origins=[
            "https://pulseops-multi-agent-ai.vercel.app",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002"
        ],
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
            "status": "healthy"
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