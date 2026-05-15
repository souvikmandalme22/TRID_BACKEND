import time, logging, uuid
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://trid-2q3h.onrender.com",   # production frontend
    "https://trid.in",
    "https://www.trid.in",
]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start      = time.time()
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
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]   = "nosniff"
        response.headers["X-Frame-Options"]          = "DENY"
        response.headers["X-XSS-Protection"]         = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
