"""
Observability API endpoints

Provides access to request logs, metrics, and RAG transparency data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta

from open_webui.models.observability import (
    RequestLogs,
    RAGLogs,
    RequestLogResponse,
    ObservabilityMetrics,
    RAGLog,
    FallbackAttempt
)
from open_webui.utils.auth import get_verified_user
from open_webui.models.users import Users

router = APIRouter()


@router.get("/logs", response_model=List[RequestLogResponse])
async def get_request_logs(
    user=Depends(get_verified_user),
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
    route_name: Optional[str] = None,
    errors_only: bool = False,
    rag_used_only: bool = False,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0
):
    """
    Get request logs with optional filters.

    Requires admin role for seeing all users' logs.
    Regular users can only see their own logs.
    """
    request_logs = RequestLogs()

    # Check if user is admin
    is_admin = user.role == "admin"

    # Regular users can only see their own logs
    user_id = None if is_admin else user.id

    logs = request_logs.get_logs(
        user_id=user_id,
        provider=provider,
        model_id=model_id,
        route_name=route_name,
        errors_only=errors_only,
        rag_used_only=rag_used_only,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )

    return [
        RequestLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            user_id=log.user_id,
            chat_id=log.chat_id,
            provider=log.provider,
            model_id=log.model_id,
            route_name=log.route_name,
            fallback_used=log.fallback_used,
            total_latency_ms=log.total_latency_ms,
            tokens_in=log.tokens_in,
            tokens_out=log.tokens_out,
            error_type=log.error_type,
            rag_used=log.rag_used
        )
        for log in logs
    ]


@router.get("/logs/{log_id}")
async def get_request_log_detail(
    log_id: str,
    user=Depends(get_verified_user)
):
    """Get detailed information for a specific request log"""
    request_logs = RequestLogs()

    logs = request_logs.get_logs(limit=1, offset=0)
    log = next((l for l in logs if l.id == log_id), None)

    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    # Check permissions
    if user.role != "admin" and log.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get associated RAG log if exists
    rag_log = None
    if log.rag_used:
        rag_logs = RAGLogs()
        rag_log = rag_logs.get_log_by_request_id(log_id)

    return {
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "user_id": log.user_id,
        "chat_id": log.chat_id,
        "provider": log.provider,
        "model_id": log.model_id,
        "route_name": log.route_name,
        "route_reason": log.route_reason,
        "fallback_used": log.fallback_used,
        "fallback_chain": log.fallback_chain_json,
        "total_latency_ms": log.total_latency_ms,
        "provider_latency_ms": log.provider_latency_ms,
        "tokens_in": log.tokens_in,
        "tokens_out": log.tokens_out,
        "error_type": log.error_type,
        "error_short": log.error_short,
        "rag_attempted": log.rag_attempted,
        "rag_used": log.rag_used,
        "rag_latency_ms": log.rag_latency_ms,
        "rag_topN": log.rag_topN,
        "rag_topK": log.rag_topK,
        "reranker_type": log.reranker_type,
        "rerank_latency_ms": log.rerank_latency_ms,
        "metadata": log.metadata,
        "rag_details": {
            "query": rag_log.query if rag_log else None,
            "knowledge_base_id": rag_log.knowledge_base_id if rag_log else None,
            "candidates": rag_log.candidates_json if rag_log else None,
            "selected_chunks": rag_log.selected_chunks_json if rag_log else None
        } if rag_log else None
    }


@router.get("/metrics", response_model=ObservabilityMetrics)
async def get_metrics(
    user=Depends(get_verified_user),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    provider: Optional[str] = None
):
    """
    Get aggregated metrics.

    Returns metrics like error rate, latency percentiles, fallback rate, etc.
    Admin only.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    request_logs = RequestLogs()

    # Default to last 24 hours if no time range specified
    if not start_time:
        start_time = (datetime.utcnow() - timedelta(days=1)).isoformat()

    metrics = request_logs.get_metrics(
        start_time=start_time,
        end_time=end_time,
        provider=provider
    )

    return metrics


@router.get("/metrics/timeseries")
async def get_timeseries_metrics(
    user=Depends(get_verified_user),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    interval: str = "1h",
    metric: str = "latency"
):
    """
    Get time-series metrics for charting.

    Supports metrics: latency, error_rate, tokens, fallback_rate
    Intervals: 5m, 15m, 1h, 6h, 1d
    Admin only.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # TODO: Implement time-series aggregation
    # This would require more complex SQL queries or time-series DB
    # For MVP, return placeholder

    return {
        "metric": metric,
        "interval": interval,
        "data_points": [
            # {"timestamp": "2025-01-01T00:00:00Z", "value": 123.45}
        ]
    }


@router.get("/circuit-breakers")
async def get_circuit_breaker_states(
    user=Depends(get_verified_user)
):
    """
    Get current circuit breaker states for all providers.
    Admin only.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from open_webui.services.fallback_handler import get_circuit_breaker

    circuit_breaker = get_circuit_breaker()

    states = {}
    for provider in circuit_breaker.breakers.keys():
        breaker = circuit_breaker.get_breaker(provider)
        states[provider] = {
            "state": breaker.get_state(),
            "failure_count": breaker.failure_count,
            "last_failure_time": breaker.last_failure_time,
            "opened_at": breaker.opened_at
        }

    return states


@router.post("/circuit-breakers/{provider}/reset")
async def reset_circuit_breaker(
    provider: str,
    user=Depends(get_verified_user)
):
    """
    Manually reset a circuit breaker for a provider.
    Admin only.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from open_webui.services.fallback_handler import get_circuit_breaker

    circuit_breaker = get_circuit_breaker()
    circuit_breaker.record_success(provider)

    return {"message": f"Circuit breaker reset for {provider}"}


@router.get("/rag/logs/{request_id}")
async def get_rag_log(
    request_id: str,
    user=Depends(get_verified_user)
):
    """Get RAG log for a specific request"""
    rag_logs = RAGLogs()
    log = rag_logs.get_log_by_request_id(request_id)

    if not log:
        raise HTTPException(status_code=404, detail="RAG log not found")

    # TODO: Check permissions against request_id's user_id

    return {
        "request_id": log.request_id,
        "query": log.query,
        "knowledge_base_id": log.knowledge_base_id,
        "candidates": log.candidates_json,
        "reranker_type": log.reranker_type,
        "selected_chunks": log.selected_chunks_json,
        "timestamp": log.timestamp.isoformat()
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    from open_webui.services.model_registry import get_model_registry
    from open_webui.services.fallback_handler import get_circuit_breaker

    registry = get_model_registry()
    circuit_breaker = get_circuit_breaker()

    return {
        "status": "healthy",
        "models_loaded": len(registry.models_by_id),
        "providers_configured": len(registry.config.providers) if registry.config else 0,
        "circuit_breaker_states": {
            provider: circuit_breaker.get_provider_state(provider)
            for provider in circuit_breaker.breakers.keys()
        }
    }
