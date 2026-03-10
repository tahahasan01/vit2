"""
Rate limiter middleware — simple in-memory sliding window.

Production: Replace with Redis-backed limiter or use Nginx rate limiting.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.

    Limits are per-IP per-path-prefix:
      /api/v1/auth/*  : 10 requests / 60 seconds
      /api/v1/tryon   : 5  requests / 60 seconds  (VTO is expensive)
      default         : 60 requests / 60 seconds
    """

    LIMITS: Dict[str, Tuple[int, int]] = {
        "/api/v1/auth": (10, 60),
        "/api/v1/tryon": (5, 60),
    }
    DEFAULT_LIMIT = (60, 60)  # requests, window_seconds

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self._hits: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "0.0.0.0"
        path = request.url.path

        # Find matching limit
        max_requests, window = self.DEFAULT_LIMIT
        for prefix, (limit, win) in self.LIMITS.items():
            if path.startswith(prefix):
                max_requests, window = limit, win
                break

        parts = path.split('/')
        key = f"{client_ip}:{parts[3] if len(parts) > 3 else path}"
        now = time.monotonic()

        # Clean old entries
        self._hits[key] = [t for t in self._hits[key] if now - t < window]

        if len(self._hits[key]) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": window,
                },
                headers={"Retry-After": str(window)},
            )

        self._hits[key].append(now)
        return await call_next(request)
