"""
Logging middleware — structured request/response logging via structlog.

Logs: method, path, status_code, latency_ms, client IP.
"""
from __future__ import annotations

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("http")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.monotonic()
        method = request.method
        path = request.url.path

        # Skip noisy paths
        if path in ("/api/v1/health", "/api/v1/metrics", "/favicon.ico"):
            return await call_next(request)

        try:
            response = await call_next(request)
            elapsed_ms = (time.monotonic() - start) * 1000

            logger.info(
                "http.request",
                method=method,
                path=path,
                status=response.status_code,
                latency_ms=round(elapsed_ms, 2),
                client=request.client.host if request.client else "unknown",
            )
            return response

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error(
                "http.error",
                method=method,
                path=path,
                latency_ms=round(elapsed_ms, 2),
                error=str(exc)[:300],
            )
            raise
