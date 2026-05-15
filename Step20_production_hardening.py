"""
TRID Production Hardening — Step 20
Logging, rate limiting, security middleware,
exception handling, performance, deployment readiness

FILES TO CREATE / UPDATE:
- app/core/logging_config.py
- app/core/middleware.py
- app/core/exceptions.py
- app/core/rate_limiter.py
- app/main.py  (final production version)
- .env.example
- Dockerfile   (production)
- docker-compose.yml (production)
"""

# ─────────────────────────────────────────────
# app/core/logging_config.py
# ─────────────────────────────────────────────

LOGGING_CONFIG = '''
import logging, sys, os
from logging.handlers import RotatingFileHandler

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR   = "logs"


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # Rotating file handler — 10MB × 5 backups
    file_handler = RotatingFileHandler(
        f"{LOG_DIR}/trid.log", maxBytes=10_000_000, backupCount=5
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # Silence noisy libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info("TRID logging initialized")
'''

# ─────────────────────────────────────────────
# app/core/exceptions.py
# ─────────────────────────────────────────────

EXCEPTIONS = '''
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


class TRIDException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message     = message
        self.status_code = status_code
        super().__init__(message)


async def trid_exception_handler(request: Request, exc: TRIDException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "path": str(request.url)},
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "path": str(request.url)},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(x) for x in e["loc"]), "msg": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "details": errors},
    )


async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc} | path={request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Our team has been notified."},
    )
'''

# ─────────────────────────────────────────────
# app/core/middleware.py
# ─────────────────────────────────────────────

MIDDLEWARE = '''
import time, logging, uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://trid.in",           # production domain
    "https://www.trid.in",
]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start      = time.time()

        # Attach request ID
        request.state.request_id = request_id

        response = await call_next(request)

        duration = round((time.time() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration}ms)"
        )
        response.headers["X-Request-ID"]    = request_id
        response.headers["X-Response-Time"] = f"{duration}ms"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]            = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"]  = "max-age=31536000; includeSubDomains"
        return response
'''

# ─────────────────────────────────────────────
# app/core/rate_limiter.py
# ─────────────────────────────────────────────

RATE_LIMITER = '''
import time, logging
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# In-memory store (use Redis in production for multi-instance)
_request_counts: dict = defaultdict(list)

RATE_LIMITS = {
    "/api/v1/auth/send-otp": (5,  300),   # 5 requests per 5 min
    "/api/v1/auth/verify-otp": (10, 300), # 10 per 5 min
    "default": (100, 60),                  # 100 requests per minute
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        path      = request.url.path

        limit, window = RATE_LIMITS.get(path, RATE_LIMITS["default"])
        key = f"{client_ip}:{path}"
        now = time.time()

        # Remove expired entries
        _request_counts[key] = [t for t in _request_counts[key] if now - t < window]

        if len(_request_counts[key]) >= limit:
            logger.warning(f"Rate limit hit: {client_ip} → {path}")
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again after {window} seconds.",
                headers={"Retry-After": str(window)},
            )

        _request_counts[key].append(now)
        return await call_next(request)
'''

# ─────────────────────────────────────────────
# app/main.py — FINAL PRODUCTION VERSION
# ─────────────────────────────────────────────

MAIN_PY = '''
import os, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.logging_config import setup_logging
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware, ALLOWED_ORIGINS
from app.core.rate_limiter import RateLimiterMiddleware
from app.core.exceptions import (
    TRIDException, trid_exception_handler,
    http_exception_handler, validation_exception_handler,
    global_exception_handler,
)
from app.database.session import engine
from app.database.base import Base

# Setup logging before everything
setup_logging()
logger = logging.getLogger(__name__)

ENV = os.getenv("ENV", "development")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"TRID Backend starting | env={ENV}")
    # DB health check on startup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: c.execute(__import__("sqlalchemy").text("SELECT 1")))
        logger.info("Database connection OK")
    except Exception as e:
        logger.critical(f"Database connection FAILED: {e}")
    yield
    logger.info("TRID Backend shutting down")
    await engine.dispose()


app = FastAPI(
    title       = "TRID API",
    description = "Intelligent 3D Printing Manufacturing Platform",
    version     = "1.0.0",
    docs_url    = "/docs" if ENV != "production" else None,
    redoc_url   = "/redoc" if ENV != "production" else None,
    lifespan    = lifespan,
)

# ── Middleware (order matters) ────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers     = ["*"],
)

# ── Exception handlers ────────────────────────
app.add_exception_handler(TRIDException,           trid_exception_handler)
app.add_exception_handler(HTTPException,            http_exception_handler)
app.add_exception_handler(RequestValidationError,   validation_exception_handler)
app.add_exception_handler(Exception,                global_exception_handler)

# ── Routers ───────────────────────────────────
from app.api.v1.endpoints import (
    upload, geometry, orientation, support,
    segments, materials, usecases, recommendations,
    infill, effective_material, pricing, auth,
    orders, payments,
)

PREFIX = "/api/v1"

app.include_router(upload.router,            prefix=PREFIX)
app.include_router(geometry.router,          prefix=PREFIX)
app.include_router(orientation.router,       prefix=PREFIX)
app.include_router(support.router,           prefix=PREFIX)
app.include_router(segments.router,          prefix=PREFIX)
app.include_router(materials.router,         prefix=PREFIX)
app.include_router(usecases.router,          prefix=PREFIX)
app.include_router(recommendations.router,   prefix=PREFIX)
app.include_router(infill.router,            prefix=PREFIX)
app.include_router(effective_material.router,prefix=PREFIX)
app.include_router(pricing.router,           prefix=PREFIX)
app.include_router(auth.router,              prefix=PREFIX)
app.include_router(orders.router,            prefix=PREFIX)
app.include_router(payments.router,          prefix=PREFIX)


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status"  : "ok",
        "service" : "TRID API",
        "version" : "1.0.0",
        "env"     : ENV,
    }
'''

# ─────────────────────────────────────────────
# .env.example
# ─────────────────────────────────────────────

ENV_EXAMPLE = '''
# ── App ──────────────────────────────────────
ENV=production
SECRET_KEY=your-super-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
LOG_LEVEL=INFO

# ── Database ─────────────────────────────────
DATABASE_URL=postgresql+asyncpg://trid_user:password@db:5432/trid_db

# ── Razorpay ─────────────────────────────────
RAZORPAY_KEY_ID=rzp_live_XXXXXXXXXX
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# ── SMS Provider (MSG91 / Fast2SMS) ──────────
SMS_API_KEY=your_sms_api_key
SMS_TEMPLATE_ID=your_template_id
'''

# ─────────────────────────────────────────────
# Dockerfile (production)
# ─────────────────────────────────────────────

DOCKERFILE = '''
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create logs + storage dirs
RUN mkdir -p logs storage/models

# Non-root user for security
RUN adduser --disabled-password --gecos "" triduser
RUN chown -R triduser:triduser /app
USER triduser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
'''

# ─────────────────────────────────────────────
# docker-compose.yml (production)
# ─────────────────────────────────────────────

DOCKER_COMPOSE = '''
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: trid_user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: trid_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trid_user -d trid_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
'''

# ─────────────────────────────────────────────
# FINAL ARCHITECTURE SUMMARY
# ─────────────────────────────────────────────

ARCHITECTURE_SUMMARY = """
╔══════════════════════════════════════════════════════════════╗
║              TRID BACKEND — COMPLETE ARCHITECTURE            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  STEP  │ MODULE                    │ STATUS                  ║
║────────┼───────────────────────────┼─────────────────────── ║
║  01    │ Project Foundation         │ ✅ Done                 ║
║  02    │ Database Foundation        │ ✅ Done                 ║
║  03    │ File Upload System         │ ✅ Done                 ║
║  04    │ Model Database             │ ✅ Done                 ║
║  05    │ 3D Geometry Analysis       │ ✅ Done                 ║
║  06    │ Orientation Engine         │ ✅ Done                 ║
║  07    │ Support Volume Estimation  │ ✅ Done                 ║
║  08    │ Support Density Engine     │ ✅ Done                 ║
║  09    │ Segment Management         │ ✅ Done                 ║
║  10    │ Material Family System     │ ✅ Done                 ║
║  11    │ Material Library           │ ✅ Done                 ║
║  12    │ Use Case Management        │ ✅ Done                 ║
║  13    │ Recommendation Engine      │ ✅ Done                 ║
║  14    │ Infill Engine              │ ✅ Done                 ║
║  15    │ Effective Material Calc    │ ✅ Done                 ║
║  16    │ Smart Pricing Engine       │ ✅ Done                 ║
║  17    │ OTP + JWT Auth             │ ✅ Done                 ║
║  18    │ Order Management           │ ✅ Done                 ║
║  19    │ Razorpay Payment           │ ✅ Done                 ║
║  20    │ Production Hardening       │ ✅ Done                 ║
║                                                              ║
║  DB TABLES: 19 total                                         ║
║  API ROUTES: 55+ endpoints                                   ║
║  ALEMBIC MIGRATIONS: 0001 → 0019                             ║
╚══════════════════════════════════════════════════════════════╝
"""
