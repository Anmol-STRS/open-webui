"""add observability tables

Revision ID: e1b2c3d4e5f6
Revises: 3e0e00844bb0
Create Date: 2025-01-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'e1b2c3d4e5f6'
down_revision = '3e0e00844bb0'
branch_labels = None
depends_on = None


def upgrade():
    # Create request_logs table
    op.create_table(
        'request_logs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('chat_id', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('model_id', sa.String(), nullable=True),
        sa.Column('route_name', sa.String(), nullable=True),
        sa.Column('route_reason', sa.Text(), nullable=True),
        sa.Column('fallback_used', sa.Boolean(), default=False),
        sa.Column('fallback_chain_json', sa.JSON(), nullable=True),
        sa.Column('total_latency_ms', sa.Float(), nullable=True),
        sa.Column('provider_latency_ms', sa.Float(), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('error_type', sa.String(), nullable=True),
        sa.Column('error_short', sa.Text(), nullable=True),
        sa.Column('rag_attempted', sa.Boolean(), default=False),
        sa.Column('rag_used', sa.Boolean(), default=False),
        sa.Column('rag_latency_ms', sa.Float(), nullable=True),
        sa.Column('rag_topN', sa.Integer(), nullable=True),
        sa.Column('rag_topK', sa.Integer(), nullable=True),
        sa.Column('reranker_type', sa.String(), nullable=True),
        sa.Column('rerank_latency_ms', sa.Float(), nullable=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
    )

    # Create indexes for request_logs
    op.create_index('idx_request_logs_timestamp', 'request_logs', ['timestamp'])
    op.create_index('idx_request_logs_user_id', 'request_logs', ['user_id'])
    op.create_index('idx_request_logs_chat_id', 'request_logs', ['chat_id'])
    op.create_index('idx_request_logs_provider', 'request_logs', ['provider'])
    op.create_index('idx_request_logs_model_id', 'request_logs', ['model_id'])
    op.create_index('idx_request_logs_route_name', 'request_logs', ['route_name'])
    op.create_index('idx_request_logs_error_type', 'request_logs', ['error_type'])
    op.create_index('idx_request_logs_fallback_used', 'request_logs', ['fallback_used'])
    op.create_index('idx_request_logs_rag_attempted', 'request_logs', ['rag_attempted'])
    op.create_index('idx_request_logs_rag_used', 'request_logs', ['rag_used'])
    op.create_index('idx_timestamp_provider', 'request_logs', ['timestamp', 'provider'])
    op.create_index('idx_timestamp_error', 'request_logs', ['timestamp', 'error_type'])
    op.create_index('idx_user_timestamp', 'request_logs', ['user_id', 'timestamp'])

    # Create rag_logs table
    op.create_table(
        'rag_logs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('knowledge_base_id', sa.String(), nullable=True),
        sa.Column('candidates_json', sa.JSON(), nullable=True),
        sa.Column('reranker_type', sa.String(), nullable=True),
        sa.Column('reranker_scores_json', sa.JSON(), nullable=True),
        sa.Column('selected_chunks_json', sa.JSON(), nullable=True),
    )

    # Create indexes for rag_logs
    op.create_index('idx_rag_logs_request_id', 'rag_logs', ['request_id'])
    op.create_index('idx_rag_logs_timestamp', 'rag_logs', ['timestamp'])
    op.create_index('idx_rag_logs_knowledge_base_id', 'rag_logs', ['knowledge_base_id'])

    # Create circuit_breaker_states table
    op.create_table(
        'circuit_breaker_states',
        sa.Column('provider', sa.String(), primary_key=True),
        sa.Column('state', sa.String(), default='closed'),
        sa.Column('failure_count', sa.Integer(), default=0),
        sa.Column('last_failure_time', sa.DateTime(), nullable=True),
        sa.Column('last_success_time', sa.DateTime(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade():
    # Drop tables
    op.drop_table('circuit_breaker_states')
    op.drop_table('rag_logs')
    op.drop_table('request_logs')
