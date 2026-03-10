"""
Monitoring — lightweight metrics collection for API latencies & error rates.

Exposes Prometheus-compatible text format at GET /api/v1/metrics.
Uses an in-memory collector (no external dependency needed).
"""
from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List

import structlog

logger = structlog.get_logger("monitoring")


@dataclass
class _Bucket:
    """Accumulator for a single metric key."""
    count: int = 0
    total_ms: float = 0.0
    errors: int = 0
    last_error: str = ""
    _recent_ms: List[float] = field(default_factory=list)

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0.0

    @property
    def error_rate(self) -> float:
        return self.errors / self.count if self.count else 0.0

    def record(self, duration_ms: float, error: str | None = None):
        self.count += 1
        self.total_ms += duration_ms
        self._recent_ms.append(duration_ms)
        if len(self._recent_ms) > 100:
            self._recent_ms.pop(0)
        if error:
            self.errors += 1
            self.last_error = error


class MetricsCollector:
    """Singleton-style in-memory metrics collector."""

    def __init__(self):
        self._buckets: Dict[str, _Bucket] = defaultdict(_Bucket)

    # ── Record a metric ──────────────────────────────────────────────
    def record(self, key: str, duration_ms: float, error: str | None = None):
        self._buckets[key].record(duration_ms, error)

    @asynccontextmanager
    async def track(self, key: str):
        """Async context manager to auto-time an operation."""
        start = time.monotonic()
        error = None
        try:
            yield
        except Exception as exc:
            error = str(exc)[:200]
            raise
        finally:
            elapsed = (time.monotonic() - start) * 1000
            self.record(key, elapsed, error)

    # ── Prometheus text exposition ───────────────────────────────────
    def to_prometheus(self) -> str:
        lines: List[str] = []
        for key, b in sorted(self._buckets.items()):
            safe_key = key.replace(".", "_").replace("-", "_")
            lines.append(f"# HELP {safe_key}_total Total requests")
            lines.append(f"# TYPE {safe_key}_total counter")
            lines.append(f'{safe_key}_total {b.count}')

            lines.append(f"# HELP {safe_key}_errors_total Total errors")
            lines.append(f"# TYPE {safe_key}_errors_total counter")
            lines.append(f'{safe_key}_errors_total {b.errors}')

            lines.append(f"# HELP {safe_key}_duration_ms_avg Average latency")
            lines.append(f"# TYPE {safe_key}_duration_ms_avg gauge")
            lines.append(f'{safe_key}_duration_ms_avg {b.avg_ms:.2f}')

            lines.append("")
        return "\n".join(lines)

    # ── JSON summary ─────────────────────────────────────────────────
    def to_dict(self) -> Dict[str, dict]:
        return {
            key: {
                "count": b.count,
                "avg_ms": round(b.avg_ms, 2),
                "errors": b.errors,
                "error_rate": round(b.error_rate, 4),
                "last_error": b.last_error,
            }
            for key, b in sorted(self._buckets.items())
        }


# Module-level singleton
metrics = MetricsCollector()
