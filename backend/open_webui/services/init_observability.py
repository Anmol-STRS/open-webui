"""
Initialize observability database tables

This module creates the observability tables if they don't exist.
Call init_observability_tables() on application startup.
"""

import logging
from sqlalchemy import text
from open_webui.internal.db import engine, Base
from open_webui.models.observability import RequestLog, RAGLog, CircuitBreakerState

logger = logging.getLogger(__name__)


def init_observability_tables():
    """
    Initialize observability tables.
    Creates tables if they don't exist.
    """
    try:
        # Use SQLAlchemy's create_all to create tables
        # This is idempotent - only creates if tables don't exist
        Base.metadata.create_all(
            bind=engine,
            tables=[
                RequestLog.__table__,
                RAGLog.__table__,
                CircuitBreakerState.__table__
            ],
            checkfirst=True
        )
        logger.info("Observability tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize observability tables: {e}")
        logger.exception(e)


def check_observability_tables():
    """
    Check if observability tables exist.

    Returns:
        bool: True if all tables exist, False otherwise
    """
    try:
        with engine.connect() as conn:
            # Check if request_logs table exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='request_logs'"
            ))
            has_request_logs = result.fetchone() is not None

            # Check if rag_logs table exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rag_logs'"
            ))
            has_rag_logs = result.fetchone() is not None

            # Check if circuit_breaker_states table exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='circuit_breaker_states'"
            ))
            has_circuit_breaker = result.fetchone() is not None

            all_exist = has_request_logs and has_rag_logs and has_circuit_breaker

            if not all_exist:
                logger.warning(
                    f"Observability tables status: "
                    f"request_logs={has_request_logs}, "
                    f"rag_logs={has_rag_logs}, "
                    f"circuit_breaker_states={has_circuit_breaker}"
                )

            return all_exist
    except Exception as e:
        logger.error(f"Failed to check observability tables: {e}")
        return False
