"""
Circuit Breaker factory — wraps pybreaker with structured logging.

Each external service gets its own breaker instance so one flaky API
doesn't take down the whole pipeline.

States:
  CLOSED   → Normal operation; failures are counted.
  OPEN     → Tripped after fail_max; all calls rejected instantly.
  HALF-OPEN → After reset_timeout, one trial call is allowed through.
"""
from __future__ import annotations

from typing import Dict

import pybreaker
import structlog

logger = structlog.get_logger("circuit_breaker")

# Global registry so we can inspect all breakers from the health endpoint.
_registry: Dict[str, pybreaker.CircuitBreaker] = {}


class _LogListener(pybreaker.CircuitBreakerListener):
    """Logs every state transition for observability."""

    def __init__(self, name: str):
        self._name = name

    def state_change(self, cb: pybreaker.CircuitBreaker, old_state, new_state):
        logger.warning(
            "circuit_breaker.state_change",
            breaker=self._name,
            old=str(old_state),
            new=str(new_state),
        )

    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception):
        logger.info(
            "circuit_breaker.failure",
            breaker=self._name,
            error=str(exc)[:200],
            fail_count=cb.fail_counter,
        )

    def success(self, cb: pybreaker.CircuitBreaker):
        logger.debug("circuit_breaker.success", breaker=self._name)


def create_breaker(
    name: str,
    fail_max: int = 5,
    reset_timeout: int = 60,
) -> pybreaker.CircuitBreaker:
    """
    Create (or return existing) named circuit breaker.

    Args:
        name:          Unique identifier (e.g. "replicate_idm_vton")
        fail_max:      Consecutive failures before opening the circuit.
        reset_timeout: Seconds before trying a single request again (half-open).
    """
    if name in _registry:
        return _registry[name]

    breaker = pybreaker.CircuitBreaker(
        fail_max=fail_max,
        reset_timeout=reset_timeout,
        listeners=[_LogListener(name)],
        name=name,
    )
    _registry[name] = breaker
    logger.info(
        "circuit_breaker.created",
        name=name,
        fail_max=fail_max,
        reset_timeout=reset_timeout,
    )
    return breaker


def get_all_breaker_states() -> Dict[str, str]:
    """Return current state of every registered circuit breaker."""
    return {name: str(cb.current_state) for name, cb in _registry.items()}


def get_breaker(name: str) -> pybreaker.CircuitBreaker | None:
    return _registry.get(name)
