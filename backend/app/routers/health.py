"""
Health & metrics routes — observability endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.models.health import (
    CircuitState,
    ExternalServiceStatus,
    HealthResponse,
    ServiceHealth,
)
from app.utils.circuit_breaker import get_all_breaker_states
from app.utils.monitoring import metrics

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    GET /api/v1/health — Aggregate health of all external services.

    Returns circuit breaker states, last known latencies, and overall status.
    Used by Docker health checks, load balancers, and the frontend
    FallbackState component.
    """
    settings = request.app.state.settings
    breaker_states = get_all_breaker_states()
    metrics_data = metrics.to_dict()

    services = {}

    # Map each known service
    service_defs = {
        "fashn_tryon": "fashn_vto",
        "fashn_video": "fashn_video",
        "replicate_idm_vton": "replicate_vto",
        "replicate_flux_vton": "replicate_vto_fallback",
        "replicate_trellis": "replicate_3d",
        "replicate_wan_video": "replicate_video",
        "hmr_body_estimation": "huggingface_hmr",
    }

    for breaker_name, display_name in service_defs.items():
        state_str = breaker_states.get(breaker_name, "closed")
        circuit = _map_circuit_state(state_str)

        metric_key = f"pipeline.{breaker_name}"
        m = metrics_data.get(metric_key, {})

        services[display_name] = ExternalServiceStatus(
            status=(
                ServiceHealth.UNHEALTHY if circuit == CircuitState.OPEN
                else ServiceHealth.DEGRADED if circuit == CircuitState.HALF_OPEN
                else ServiceHealth.HEALTHY
            ),
            latency_ms=m.get("avg_ms"),
            circuit=circuit,
            last_error=m.get("last_error") or None,
        )

    # Supabase health (always healthy in stubs)
    services["supabase"] = ExternalServiceStatus(
        status=ServiceHealth.HEALTHY,
        circuit=CircuitState.CLOSED,
    )

    # Redis health
    redis_pool = request.app.state.redis_pool
    redis_ok = redis_pool is not None
    services["redis"] = ExternalServiceStatus(
        status=ServiceHealth.HEALTHY if redis_ok else ServiceHealth.UNHEALTHY,
        circuit=CircuitState.CLOSED if redis_ok else CircuitState.OPEN,
    )

    # Aggregate
    all_statuses = [s.status for s in services.values()]
    if ServiceHealth.UNHEALTHY in all_statuses:
        overall = ServiceHealth.DEGRADED
    elif ServiceHealth.DEGRADED in all_statuses:
        overall = ServiceHealth.DEGRADED
    else:
        overall = ServiceHealth.HEALTHY

    return HealthResponse(
        status=overall,
        environment=settings.environment.value,
        services=services,
    )


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    GET /api/v1/metrics — Prometheus-compatible text exposition.

    Metrics tracked:
      - vto_request_duration_seconds{step}
      - vto_request_total{status}
      - circuit_breaker_state{service}
      - storage_upload_duration_seconds
    """
    return metrics.to_prometheus()


def _map_circuit_state(state_str: str) -> CircuitState:
    state_lower = state_str.lower()
    if "open" in state_lower and "half" not in state_lower:
        return CircuitState.OPEN
    elif "half" in state_lower:
        return CircuitState.HALF_OPEN
    return CircuitState.CLOSED
