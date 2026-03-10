"""
Health / monitoring schemas.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ServiceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


class ExternalServiceStatus(BaseModel):
    status: ServiceHealth = ServiceHealth.HEALTHY
    latency_ms: Optional[float] = None
    circuit: CircuitState = CircuitState.CLOSED
    last_error: Optional[str] = None


class HealthResponse(BaseModel):
    """GET /api/v1/health"""

    status: ServiceHealth = ServiceHealth.HEALTHY
    environment: str = "development"
    services: Dict[str, ExternalServiceStatus] = Field(default_factory=dict)
