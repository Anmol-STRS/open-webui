"""
Unified completion handler with routing, fallback, and observability

This service wraps the chat completion logic with:
- Model routing based on content analysis
- Automatic fallback on failures
- RAG transparency and reranking
- Comprehensive observability logging
"""

import time
import uuid
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from open_webui.services.model_router import get_router, RoutingContext, ModelRouter
from open_webui.services.fallback_handler import get_fallback_handler
from open_webui.services.provider_adapters import ProviderRequest, ProviderResponse, ProviderError
from open_webui.services.rag_reranker import get_rag_transparency, RAGChunk
from open_webui.models.observability import (
    Logs,
    RAGLogOps,
    RequestLogCreate,
    RAGLogCreate,
    RAGCandidate as ObsRAGCandidate
)

logger = logging.getLogger(__name__)


class CompletionRequest(BaseModel):
    """Unified completion request"""
    messages: List[Dict[str, Any]]
    model: Optional[str] = None  # User-selected model (optional)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    response_format: Optional[Dict[str, Any]] = None
    stream: bool = False
    user_id: str
    chat_id: Optional[str] = None

    # RAG context
    rag_enabled: bool = False
    rag_chunks: Optional[List[Dict[str, Any]]] = None
    knowledge_base_id: Optional[str] = None


class CompletionHandler:
    """
    Handles chat completion requests with routing, fallback, RAG, and observability.
    """

    def __init__(self):
        self.router = get_router()
        self.fallback_handler = get_fallback_handler()
        self.rag_transparency = get_rag_transparency()

    async def complete(self, request: CompletionRequest) -> ProviderResponse:
        """
        Execute completion with full routing, fallback, RAG, and observability.

        Args:
            request: Unified completion request

        Returns:
            Provider response

        Raises:
            ProviderError: If all attempts fail
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())

        # Step 1: Analyze message content and build routing context
        routing_context = ModelRouter.analyze_message_content(
            messages=request.messages,
            tools=request.tools,
            response_format=request.response_format
        )

        # Step 2: Handle RAG if enabled
        rag_latency_ms = None
        rerank_latency_ms = None
        reranker_type = None
        selected_chunks = []
        rag_sources = []

        if request.rag_enabled and request.rag_chunks:
            rag_start_time = time.time()

            # Convert to RAGChunk format
            chunks = [
                RAGChunk(
                    doc_id=chunk.get('doc_id', ''),
                    doc_title=chunk.get('doc_title'),
                    doc_path=chunk.get('doc_path'),
                    chunk_id=chunk.get('chunk_id', ''),
                    content=chunk.get('content', ''),
                    vector_score=chunk.get('score', 0.0),
                    metadata=chunk.get('metadata')
                )
                for chunk in request.rag_chunks
            ]

            # Get last user message for query
            query = routing_context.last_user_message

            # Rerank and select chunks
            selected_ranked, rerank_result = self.rag_transparency.retrieve_and_rerank(
                query=query,
                retrieved_chunks=chunks,
                top_k=5,  # Select top 5
                knowledge_base_id=request.knowledge_base_id
            )

            selected_chunks = selected_ranked
            rerank_latency_ms = rerank_result.rerank_latency_ms
            reranker_type = rerank_result.reranker_type

            # Inject chunks into messages
            request.messages = self.rag_transparency.inject_chunks_into_prompt(
                messages=request.messages,
                ranked_chunks=selected_ranked,
                injection_strategy="system"
            )

            # Prepare sources for UI
            rag_sources = self.rag_transparency.format_sources_for_ui(selected_ranked)

            routing_context.rag_enabled = True
            rag_latency_ms = (time.time() - rag_start_time) * 1000

            logger.info(f"RAG: Selected {len(selected_chunks)} chunks in {rag_latency_ms:.1f}ms")

        # Step 3: Route to best model
        routing_decision = self.router.route(
            context=routing_context,
            user_model_override=request.model
        )

        logger.info(
            f"Routing: {routing_decision.route_name} -> {routing_decision.primary_model_id}, "
            f"fallbacks: {routing_decision.fallback_model_ids}"
        )

        # Step 4: Build provider request
        provider_request = ProviderRequest(
            model=routing_decision.primary_model_id,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            tools=request.tools,
            tool_choice=request.tool_choice,
            response_format=request.response_format,
            stream=request.stream,
            metadata={"request_id": request_id}
        )

        # Step 5: Execute with fallback
        try:
            response, fallback_attempts = await self.fallback_handler.execute_with_fallback(
                request=provider_request,
                primary_model_id=routing_decision.primary_model_id,
                fallback_model_ids=routing_decision.fallback_model_ids,
                timeout_ms=routing_decision.timeout_ms
            )

            total_latency_ms = (time.time() - start_time) * 1000
            fallback_used = len(fallback_attempts) > 0

            # Extract final model info
            final_model_id = routing_decision.primary_model_id
            if fallback_attempts:
                # Last successful attempt
                final_model_id = fallback_attempts[-1].model_id

            final_model = self.router.registry.get_model(final_model_id)
            provider = final_model.provider if final_model else "unknown"

            # Extract usage
            usage = response.usage or {}
            tokens_in = usage.get('prompt_tokens')
            tokens_out = usage.get('completion_tokens')

            # Step 6: Log to observability
            await self._log_request(
                request_id=request_id,
                user_id=request.user_id,
                chat_id=request.chat_id,
                provider=provider,
                model_id=final_model_id,
                route_name=routing_decision.route_name,
                route_reason=routing_decision.route_reason,
                fallback_used=fallback_used,
                fallback_chain=fallback_attempts,
                total_latency_ms=total_latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                rag_attempted=request.rag_enabled,
                rag_used=len(selected_chunks) > 0,
                rag_latency_ms=rag_latency_ms,
                rag_topN=len(request.rag_chunks) if request.rag_chunks else None,
                rag_topK=len(selected_chunks),
                reranker_type=reranker_type,
                rerank_latency_ms=rerank_latency_ms
            )

            # Log RAG details if used
            if request.rag_enabled and selected_chunks:
                await self._log_rag(
                    request_id=request_id,
                    query=routing_context.last_user_message,
                    knowledge_base_id=request.knowledge_base_id,
                    chunks=chunks,
                    selected_chunks=selected_chunks,
                    reranker_type=reranker_type
                )

            # Attach RAG sources to response metadata
            if rag_sources:
                if not response.raw_response:
                    response.raw_response = {}
                response.raw_response['rag_sources'] = rag_sources

            return response

        except ProviderError as e:
            total_latency_ms = (time.time() - start_time) * 1000

            # Log failure
            await self._log_request(
                request_id=request_id,
                user_id=request.user_id,
                chat_id=request.chat_id,
                provider="unknown",
                model_id=routing_decision.primary_model_id,
                route_name=routing_decision.route_name,
                route_reason=routing_decision.route_reason,
                fallback_used=True,
                fallback_chain=[],
                total_latency_ms=total_latency_ms,
                error_type=e.error_type,
                error_short=str(e)[:200],
                rag_attempted=request.rag_enabled,
                rag_used=False
            )

            raise

    async def _log_request(
        self,
        request_id: str,
        user_id: str,
        chat_id: Optional[str],
        provider: str,
        model_id: str,
        route_name: str,
        route_reason: str,
        fallback_used: bool,
        fallback_chain: List,
        total_latency_ms: float,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        error_type: Optional[str] = None,
        error_short: Optional[str] = None,
        rag_attempted: bool = False,
        rag_used: bool = False,
        rag_latency_ms: Optional[float] = None,
        rag_topN: Optional[int] = None,
        rag_topK: Optional[int] = None,
        reranker_type: Optional[str] = None,
        rerank_latency_ms: Optional[float] = None
    ):
        """Log request to observability"""
        try:
            log = RequestLogCreate(
                user_id=user_id,
                chat_id=chat_id,
                provider=provider,
                model_id=model_id,
                route_name=route_name,
                route_reason=route_reason,
                fallback_used=fallback_used,
                fallback_chain=fallback_chain,
                total_latency_ms=total_latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                error_type=error_type,
                error_short=error_short,
                rag_attempted=rag_attempted,
                rag_used=rag_used,
                rag_latency_ms=rag_latency_ms,
                rag_topN=rag_topN,
                rag_topK=rag_topK,
                reranker_type=reranker_type,
                rerank_latency_ms=rerank_latency_ms
            )
            Logs.insert_log(log)
        except Exception as e:
            logger.exception(f"Failed to log request: {e}")

    async def _log_rag(
        self,
        request_id: str,
        query: str,
        knowledge_base_id: Optional[str],
        chunks: List[RAGChunk],
        selected_chunks: List,
        reranker_type: Optional[str]
    ):
        """Log RAG details"""
        try:
            # Convert to observability format
            candidates = [
                ObsRAGCandidate(
                    doc_id=chunk.doc_id,
                    doc_title=chunk.doc_title,
                    doc_path=chunk.doc_path,
                    chunk_id=chunk.chunk_id,
                    vector_score=chunk.vector_score,
                    preview=chunk.content[:400]
                )
                for chunk in chunks
            ]

            selected = [
                ObsRAGCandidate(
                    doc_id=ranked.chunk.doc_id,
                    doc_title=ranked.chunk.doc_title,
                    doc_path=ranked.chunk.doc_path,
                    chunk_id=ranked.chunk.chunk_id,
                    vector_score=ranked.vector_score,
                    preview=ranked.preview,
                    rerank_score=ranked.rerank_score
                )
                for ranked in selected_chunks
            ]

            log = RAGLogCreate(
                request_id=request_id,
                query=query,
                knowledge_base_id=knowledge_base_id,
                candidates=candidates,
                reranker_type=reranker_type,
                selected_chunks=selected
            )
            RAGLogOps.insert_log(log)
        except Exception as e:
            logger.exception(f"Failed to log RAG: {e}")


# Global handler instance
_completion_handler: Optional[CompletionHandler] = None


def get_completion_handler() -> CompletionHandler:
    """Get or create global completion handler"""
    global _completion_handler
    if _completion_handler is None:
        _completion_handler = CompletionHandler()
    return _completion_handler
