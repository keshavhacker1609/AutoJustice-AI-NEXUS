"""
AutoJustice AI NEXUS - IP-Based Rate Limiter Middleware
Prevents submission spam and API abuse.
Uses in-memory sliding window (use Redis in production for multi-process).
"""
import time
import logging
from collections import defaultdict, deque
from typing import Dict, Deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import settings

logger = logging.getLogger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter for the submission endpoint.
    Rate-limited paths: POST /api/reports/submit

    Limits:
      - Max N submissions per IP per window (configurable in settings)
      - Logs suspicious patterns for forensic review
    """

    # Protected endpoints and their per-window limits
    RATE_LIMITED_PATHS: Dict[str, tuple] = {
        "/api/reports/submit": ("submissions", 5),    # 5 per hour
        "/api/auth/login": ("login_attempts", 10),    # 10 per 15 min
    }

    # Window durations in seconds per endpoint type
    WINDOW_DURATIONS: Dict[str, int] = {
        "submissions": 3600,     # 1 hour
        "login_attempts": 900,   # 15 minutes
    }

    def __init__(self, app):
        super().__init__(app)
        # {ip: {bucket: deque of timestamps}}
        self._windows: Dict[str, Dict[str, Deque[float]]] = defaultdict(
            lambda: defaultdict(deque)
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Only rate-limit POST methods on specific paths
        if request.method != "POST":
            return await call_next(request)

        path = request.url.path
        if path not in self.RATE_LIMITED_PATHS:
            return await call_next(request)

        ip = self._get_client_ip(request)
        bucket, max_requests = self.RATE_LIMITED_PATHS[path]
        window_seconds = self.WINDOW_DURATIONS.get(bucket, 3600)

        # Sliding window check
        now = time.time()
        window = self._windows[ip][bucket]

        # Remove expired timestamps
        cutoff = now - window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= max_requests:
            wait_secs = int(window[0] + window_seconds - now) + 1
            logger.warning(
                f"Rate limit exceeded: IP={ip} path={path} "
                f"bucket={bucket} count={len(window)}/{max_requests}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests. Please wait before submitting again.",
                    "retry_after_seconds": wait_secs,
                    "limit": max_requests,
                    "window_seconds": window_seconds,
                },
                headers={
                    "Retry-After": str(wait_secs),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(window[0] + window_seconds)),
                },
            )

        window.append(now)
        remaining = max_requests - len(window)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
