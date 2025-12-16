"""
Database models for observability and request logging
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, JSON, Text, DateTime, Index
)
from sqlalchemy.sql import func
from open_webui.internal.db import Base, get_db
import time
import uuid


####################
# DB Models
####################

class RequestLog(Base):
    """Request log for observability"""
    __tablename__ = "request_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=func.now(), index=True)

    # User and chat context
    user_id = Column(String, index=True)
    chat_id = Column(String, index=True)

    # Routing information
    provider = Column(String, index=True)
    model_id = Column(String, index=True)
    route_name = Column(String, index=True)
    route_reason = Column(Text)

    # Fallback tracking
    fallback_used = Column(Boolean, default=False, index=True)
    fallback_chain_json = Column(JSON)  # List of fallback attempts

    # Performance metrics
    total_latency_ms = Column(Float)
    provider_latency_ms = Column(Float)
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)

    # Error tracking
    error_type = Column(String, index=True)
    error_short = Column(Text)

    # RAG metrics
    rag_attempted = Column(Boolean, default=False, index=True)
    rag_used = Column(Boolean, default=False, index=True)
    rag_latency_ms = Column(Float)
    rag_topN = Column(Integer)
    rag_topK = Column(Integer)
    reranker_type = Column(String)
    rerank_latency_ms = Column(Float)

    # Additional metadata
    extra_metadata = Column(JSON)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_timestamp_provider', 'timestamp', 'provider'),
        Index('idx_timestamp_error', 'timestamp', 'error_type'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )


class RAGLog(Base):
    """RAG retrieval log for transparency"""
    __tablename__ = "rag_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String, index=True)  # Links to RequestLog
    timestamp = Column(DateTime, default=func.now(), index=True)

    # Query information
    query = Column(Text)
    knowledge_base_id = Column(String, index=True)

    # Retrieval candidates
    candidates_json = Column(JSON)  # List of retrieved chunks

    # Reranking
    reranker_type = Column(String)
    reranker_scores_json = Column(JSON)  # Reranked scores

    # Final selection
    selected_chunks_json = Column(JSON)  # Final selected chunks for prompt


class CircuitBreakerState(Base):
    """Circuit breaker state for providers"""
    __tablename__ = "circuit_breaker_states"

    provider = Column(String, primary_key=True)
    state = Column(String, default="closed")  # closed, open, half_open
    failure_count = Column(Integer, default=0)
    last_failure_time = Column(DateTime)
    last_success_time = Column(DateTime)
    opened_at = Column(DateTime)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


####################
# Pydantic Models
####################

class FallbackAttempt(BaseModel):
    """Single fallback attempt"""
    attempt_n: int
    model_id: str
    provider: str
    status_code: Optional[int] = None
    error_type: Optional[str] = None
    error_short: Optional[str] = None
    latency_ms: float


class RAGCandidate(BaseModel):
    """RAG retrieval candidate"""
    doc_id: str
    doc_title: Optional[str] = None
    doc_path: Optional[str] = None
    chunk_id: str
    vector_score: float
    preview: str  # First 200-500 chars
    rerank_score: Optional[float] = None


class RequestLogCreate(BaseModel):
    """Request log creation model"""
    user_id: str
    chat_id: Optional[str] = None
    provider: str
    model_id: str
    route_name: str
    route_reason: Optional[str] = None
    fallback_used: bool = False
    fallback_chain: Optional[List[FallbackAttempt]] = None
    total_latency_ms: float
    provider_latency_ms: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    error_type: Optional[str] = None
    error_short: Optional[str] = None
    rag_attempted: bool = False
    rag_used: bool = False
    rag_latency_ms: Optional[float] = None
    rag_topN: Optional[int] = None
    rag_topK: Optional[int] = None
    reranker_type: Optional[str] = None
    rerank_latency_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class RAGLogCreate(BaseModel):
    """RAG log creation model"""
    request_id: str
    query: str
    knowledge_base_id: Optional[str] = None
    candidates: List[RAGCandidate]
    reranker_type: Optional[str] = None
    selected_chunks: List[RAGCandidate]


class RequestLogResponse(BaseModel):
    """Request log response model"""
    id: str
    timestamp: str
    user_id: str
    chat_id: Optional[str]
    provider: str
    model_id: str
    route_name: str
    fallback_used: bool
    total_latency_ms: float
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    error_type: Optional[str]
    rag_used: bool


class ObservabilityMetrics(BaseModel):
    """Aggregated observability metrics"""
    total_requests: int
    error_rate: float
    fallback_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    rag_hit_rate: float
    provider_breakdown: Dict[str, int]
    error_breakdown: Dict[str, int]


####################
# Database Operations
####################

class RequestLogs:
    """Request log database operations"""

    def insert_log(self, log: RequestLogCreate) -> RequestLog:
        """Insert a new request log"""
        with get_db() as db:
            db_log = RequestLog(
                user_id=log.user_id,
                chat_id=log.chat_id,
                provider=log.provider,
                model_id=log.model_id,
                route_name=log.route_name,
                route_reason=log.route_reason,
                fallback_used=log.fallback_used,
                fallback_chain_json=[attempt.dict() for attempt in log.fallback_chain] if log.fallback_chain else None,
                total_latency_ms=log.total_latency_ms,
                provider_latency_ms=log.provider_latency_ms,
                tokens_in=log.tokens_in,
                tokens_out=log.tokens_out,
                error_type=log.error_type,
                error_short=log.error_short,
                rag_attempted=log.rag_attempted,
                rag_used=log.rag_used,
                rag_latency_ms=log.rag_latency_ms,
                rag_topN=log.rag_topN,
                rag_topK=log.rag_topK,
                reranker_type=log.reranker_type,
                rerank_latency_ms=log.rerank_latency_ms,
                metadata=log.metadata
            )
            db.add(db_log)
            db.commit()
            db.refresh(db_log)
            return db_log

    def get_logs(
        self,
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
        route_name: Optional[str] = None,
        errors_only: bool = False,
        rag_used_only: bool = False,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[RequestLog]:
        """Query request logs with filters"""
        with get_db() as db:
            query = db.query(RequestLog)

            if user_id:
                query = query.filter(RequestLog.user_id == user_id)
            if provider:
                query = query.filter(RequestLog.provider == provider)
            if model_id:
                query = query.filter(RequestLog.model_id == model_id)
            if route_name:
                query = query.filter(RequestLog.route_name == route_name)
            if errors_only:
                query = query.filter(RequestLog.error_type.isnot(None))
            if rag_used_only:
                query = query.filter(RequestLog.rag_used == True)
            if start_time:
                query = query.filter(RequestLog.timestamp >= start_time)
            if end_time:
                query = query.filter(RequestLog.timestamp <= end_time)

            query = query.order_by(RequestLog.timestamp.desc())
            query = query.limit(limit).offset(offset)

            return query.all()

    def get_metrics(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        provider: Optional[str] = None
    ) -> ObservabilityMetrics:
        """Get aggregated metrics"""
        with get_db() as db:
            query = db.query(RequestLog)

            if start_time:
                query = query.filter(RequestLog.timestamp >= start_time)
            if end_time:
                query = query.filter(RequestLog.timestamp <= end_time)
            if provider:
                query = query.filter(RequestLog.provider == provider)

            logs = query.all()

            if not logs:
                return ObservabilityMetrics(
                    total_requests=0,
                    error_rate=0.0,
                    fallback_rate=0.0,
                    avg_latency_ms=0.0,
                    p50_latency_ms=0.0,
                    p95_latency_ms=0.0,
                    rag_hit_rate=0.0,
                    provider_breakdown={},
                    error_breakdown={}
                )

            total = len(logs)
            errors = sum(1 for log in logs if log.error_type)
            fallbacks = sum(1 for log in logs if log.fallback_used)
            rag_attempted = sum(1 for log in logs if log.rag_attempted)
            rag_used = sum(1 for log in logs if log.rag_used)

            latencies = [log.total_latency_ms for log in logs if log.total_latency_ms]
            latencies.sort()

            provider_breakdown = {}
            for log in logs:
                provider_breakdown[log.provider] = provider_breakdown.get(log.provider, 0) + 1

            error_breakdown = {}
            for log in logs:
                if log.error_type:
                    error_breakdown[log.error_type] = error_breakdown.get(log.error_type, 0) + 1

            return ObservabilityMetrics(
                total_requests=total,
                error_rate=errors / total if total > 0 else 0.0,
                fallback_rate=fallbacks / total if total > 0 else 0.0,
                avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
                p50_latency_ms=latencies[len(latencies) // 2] if latencies else 0.0,
                p95_latency_ms=latencies[int(len(latencies) * 0.95)] if latencies else 0.0,
                rag_hit_rate=rag_used / rag_attempted if rag_attempted > 0 else 0.0,
                provider_breakdown=provider_breakdown,
                error_breakdown=error_breakdown
            )


class RAGLogs:
    """RAG log database operations"""

    def insert_log(self, log: RAGLogCreate) -> RAGLog:
        """Insert a new RAG log"""
        with get_db() as db:
            db_log = RAGLog(
                request_id=log.request_id,
                query=log.query,
                knowledge_base_id=log.knowledge_base_id,
                candidates_json=[c.dict() for c in log.candidates],
                reranker_type=log.reranker_type,
                selected_chunks_json=[c.dict() for c in log.selected_chunks]
            )
            db.add(db_log)
            db.commit()
            db.refresh(db_log)
            return db_log

    def get_log_by_request_id(self, request_id: str) -> Optional[RAGLog]:
        """Get RAG log by request ID"""
        with get_db() as db:
            return db.query(RAGLog).filter(RAGLog.request_id == request_id).first()


# Global instances
Logs = RequestLogs()
RAGLogOps = RAGLogs()
