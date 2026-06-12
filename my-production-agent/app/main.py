import json
import logging
import os
import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, cost_guard
from app.rate_limiter import check_rate_limit, rate_limiter
from utils.mock_llm import ask

logging.basicConfig(
    level=getattr(
        logging, settings.LOG_LEVEL.upper()
    ) if hasattr(settings, "LOG_LEVEL") else logging.INFO,
    format=(
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    ),
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(settings.APP_NAME)

start_time = time.time()
_graceful_shutdown = False


class AskRequest(BaseModel):
    user_id: str = Field(default="default", description="User identifier for session")
    question: str = Field(
        ..., min_length=1, max_length=2000, description="Question to ask"
    )


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str
    instance_id: str
    usage: dict = {}


def get_instance_id():
    return os.getenv("INSTANCE_ID", str(uuid.uuid4())[:8])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "instance": get_instance_id(),
    }))
    yield
    logger.info(
        json.dumps({"event": "shutdown", "message": "Shutting down gracefully"})
    )


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        settings.ALLOWED_ORIGINS.split(",")
        if settings.ALLOWED_ORIGINS != "*" else ["*"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


def handle_sigterm(signum, frame):
    global _graceful_shutdown
    _graceful_shutdown = True
    logger.info(json.dumps({
        "event": "signal_received",
        "signal": "SIGTERM",
        "message": "Stopping new requests, finishing in-flight...",
    }))


signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "instance": get_instance_id(),
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "ask": "/ask (POST)",
            "metrics": "/metrics",
        },
    }


@app.get("/health")
def health():
    uptime_seconds = time.time() - start_time
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "instance": get_instance_id(),
        "uptime_seconds": uptime_seconds,
        "uptime_human": f"{uptime_seconds / 3600:.2f} hours",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    if _graceful_shutdown:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": "graceful shutdown in progress"},
        )
    return {
        "status": "ready",
        "instance": get_instance_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/ask")
async def ask_endpoint(
    body: AskRequest,
    user_id: str = Depends(verify_api_key),
    _: None = Depends(check_rate_limit),
    __: None = Depends(check_budget),
):
    if _graceful_shutdown:
        raise HTTPException(
            status_code=503, detail="Server is shutting down, try again later"
        )

    answer = ask(body.question)
    usage = cost_guard.record_usage(user_id=body.user_id)

    logger.info(json.dumps({
        "event": "ask",
        "user_id": body.user_id,
        "question_length": len(body.question),
        "instance": get_instance_id(),
    }))

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.LLM_MODEL,
        timestamp=datetime.now(timezone.utc).isoformat(),
        instance_id=get_instance_id(),
        usage=usage,
    )


@app.get("/metrics")
def metrics(user_id: str = Depends(verify_api_key)):
    rate_stats = rate_limiter.get_stats(user_id)
    usage_stats = cost_guard.get_usage(user_id)
    return {
        "instance": get_instance_id(),
        "uptime_seconds": time.time() - start_time,
        "rate_limiting": rate_stats,
        "cost_guard": usage_stats,
    }


def main():
    import uvicorn
    logger.info(json.dumps({
        "event": "starting",
        "host": settings.HOST,
        "port": settings.PORT,
        "environment": settings.ENVIRONMENT,
    }))
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.ENVIRONMENT == "production" else "debug",
        timeout_graceful_shutdown=30,
    )


if __name__ == "__main__":
    main()
