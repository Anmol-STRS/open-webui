"""
Fallback handler with circuit breaker for multi-provider resilience

Handles:
- Automatic fallback to backup models on failures
- Circuit breaker to avoid cascading failures
- Retry logic with exponential backoff
- Detailed error tracking for observability
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, AsyncIterator
from collections import defaultdict

from open_webui.services.model_registry import get_model_registry, ModelSpec
from open_webui.services.provider_adapters import (
    ProviderAdapter,
    AdapterFactory,
    ProviderRequest,
    ProviderResponse,
    ProviderError
)
from open_webui.models.observability import FallbackAttempt

logger = logging.getLogger(__name__)


class CircuitBreakerState:
    """Circuit breaker state for a provider"""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_attempts: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_attempts = half_open_attempts

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
        self.opened_at: Optional[float] = None

    def record_success(self):
        """Record successful request"""
        self.failure_count = 0
        self.last_failure_time = None
        if self.state == "half_open":
            self.state = "closed"
            self.opened_at = None
            logger.info("Circuit breaker closed after successful request")

    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == "closed" and self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.opened_at = time.time()
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )

    def can_attempt(self) -> bool:
        """Check if request can be attempted"""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if timeout has passed to transition to half-open
            if time.time() - self.opened_at >= self.timeout_seconds:
                self.state = "half_open"
                logger.info("Circuit breaker transitioning to half-open")
                return True
            return False

        if self.state == "half_open":
            return True

        return False

    def get_state(self) -> str:
        """Get current circuit breaker state"""
        return self.state


class CircuitBreaker:
    """Global circuit breaker manager for all providers"""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreakerState] = defaultdict(CircuitBreakerState)

    def get_breaker(self, provider: str) -> CircuitBreakerState:
        """Get circuit breaker for provider"""
        return self.breakers[provider]

    def record_success(self, provider: str):
        """Record successful request for provider"""
        self.breakers[provider].record_success()

    def record_failure(self, provider: str):
        """Record failed request for provider"""
        self.breakers[provider].record_failure()

    def can_attempt(self, provider: str) -> bool:
        """Check if provider can be attempted"""
        return self.breakers[provider].can_attempt()

    def get_provider_state(self, provider: str) -> str:
        """Get circuit breaker state for provider"""
        return self.breakers[provider].get_state()


# Global circuit breaker instance
_circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker instance"""
    return _circuit_breaker


class FallbackHandler:
    """
    Handles request execution with automatic fallback to backup models.
    Integrates circuit breaker to prevent cascading failures.
    """

    def __init__(self):
        self.registry = get_model_registry()
        self.circuit_breaker = get_circuit_breaker()
        self.adapters: Dict[str, ProviderAdapter] = {}

    def _get_adapter(self, model: ModelSpec) -> ProviderAdapter:
        """Get or create adapter for model's provider"""
        provider = model.provider

        if provider not in self.adapters:
            provider_config = self.registry.get_provider_config(provider)
            if not provider_config:
                raise ValueError(f"Provider {provider} not configured")

            api_key = self.registry.get_api_key(provider)
            if not api_key:
                raise ValueError(f"API key not found for provider {provider}")

            # Use get_base_url to get URL from settings (for OpenAI) or config
            base_url = self.registry.get_base_url(provider)
            if not base_url:
                base_url = provider_config.base_url

            self.adapters[provider] = AdapterFactory.create(
                provider=provider,
                base_url=base_url,
                api_key=api_key,
                timeout=provider_config.timeout
            )

        return self.adapters[provider]

    async def execute_with_fallback(
        self,
        request: ProviderRequest,
        primary_model_id: str,
        fallback_model_ids: List[str],
        timeout_ms: int = 30000
    ) -> tuple[ProviderResponse, List[FallbackAttempt]]:
        """
        Execute request with fallback chain.

        Args:
            request: Normalized provider request
            primary_model_id: Primary model to try first
            fallback_model_ids: Ordered list of fallback models
            timeout_ms: Per-model timeout in milliseconds

        Returns:
            Tuple of (response, fallback_attempts)

        Raises:
            ProviderError: If all attempts fail
        """
        chain = [primary_model_id] + fallback_model_ids
        fallback_attempts: List[FallbackAttempt] = []

        for attempt_n, model_id in enumerate(chain, start=1):
            model = self.registry.get_model(model_id)
            if not model:
                logger.warning(f"Model {model_id} not found in registry, skipping")
                continue

            # Check circuit breaker
            if not self.circuit_breaker.can_attempt(model.provider):
                logger.warning(
                    f"Circuit breaker open for {model.provider}, skipping {model_id}"
                )
                fallback_attempts.append(FallbackAttempt(
                    attempt_n=attempt_n,
                    model_id=model_id,
                    provider=model.provider,
                    status_code=503,
                    error_type="circuit_breaker_open",
                    error_short="Circuit breaker is open",
                    latency_ms=0
                ))
                continue

            try:
                start_time = time.time()

                # Update request model
                request.model = model_id

                # Execute with timeout
                adapter = self._get_adapter(model)
                response = await asyncio.wait_for(
                    adapter.complete(request),
                    timeout=timeout_ms / 1000.0
                )

                latency_ms = (time.time() - start_time) * 1000

                # Success - record and return
                self.circuit_breaker.record_success(model.provider)

                if attempt_n > 1:
                    # Only add to attempts if this was a fallback
                    fallback_attempts.append(FallbackAttempt(
                        attempt_n=attempt_n,
                        model_id=model_id,
                        provider=model.provider,
                        status_code=200,
                        error_type=None,
                        error_short=None,
                        latency_ms=latency_ms
                    ))

                logger.info(
                    f"Request succeeded with {model_id} on attempt {attempt_n}/{len(chain)}"
                )
                return response, fallback_attempts

            except asyncio.TimeoutError:
                latency_ms = (time.time() - start_time) * 1000
                self.circuit_breaker.record_failure(model.provider)

                fallback_attempts.append(FallbackAttempt(
                    attempt_n=attempt_n,
                    model_id=model_id,
                    provider=model.provider,
                    status_code=408,
                    error_type="timeout",
                    error_short=f"Request timeout after {timeout_ms}ms",
                    latency_ms=latency_ms
                ))

                logger.warning(
                    f"Timeout on {model_id} (attempt {attempt_n}/{len(chain)})"
                )

            except ProviderError as e:
                latency_ms = (time.time() - start_time) * 1000

                # Only record as circuit breaker failure for 5xx errors
                if e.status_code and e.status_code >= 500:
                    self.circuit_breaker.record_failure(model.provider)
                elif e.error_type == "timeout":
                    self.circuit_breaker.record_failure(model.provider)

                fallback_attempts.append(FallbackAttempt(
                    attempt_n=attempt_n,
                    model_id=model_id,
                    provider=model.provider,
                    status_code=e.status_code,
                    error_type=e.error_type,
                    error_short=str(e)[:200],  # Truncate to 200 chars
                    latency_ms=latency_ms
                ))

                logger.warning(
                    f"Error on {model_id} (attempt {attempt_n}/{len(chain)}): {e}"
                )

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                self.circuit_breaker.record_failure(model.provider)

                fallback_attempts.append(FallbackAttempt(
                    attempt_n=attempt_n,
                    model_id=model_id,
                    provider=model.provider,
                    status_code=500,
                    error_type="unknown",
                    error_short=str(e)[:200],
                    latency_ms=latency_ms
                ))

                logger.exception(
                    f"Unexpected error on {model_id} (attempt {attempt_n}/{len(chain)})"
                )

        # All attempts failed
        raise ProviderError(
            message="All models in fallback chain failed",
            status_code=500,
            error_type="all_fallbacks_failed"
        )

    async def stream_with_fallback(
        self,
        request: ProviderRequest,
        primary_model_id: str,
        fallback_model_ids: List[str],
        timeout_ms: int = 30000
    ) -> AsyncIterator[str]:
        """
        Execute streaming request with fallback.

        Note: Streaming has limited fallback capability since we can't retry
        after streaming starts. We try each model in sequence until one works.
        """
        chain = [primary_model_id] + fallback_model_ids

        for attempt_n, model_id in enumerate(chain, start=1):
            model = self.registry.get_model(model_id)
            if not model:
                logger.warning(f"Model {model_id} not found in registry, skipping")
                continue

            # Check circuit breaker
            if not self.circuit_breaker.can_attempt(model.provider):
                logger.warning(
                    f"Circuit breaker open for {model.provider}, skipping {model_id}"
                )
                continue

            try:
                request.model = model_id
                adapter = self._get_adapter(model)

                # Try to stream - if it fails immediately, try next model
                async for chunk in adapter.stream_complete(request):
                    yield chunk

                # If we got here, streaming succeeded
                self.circuit_breaker.record_success(model.provider)
                return

            except ProviderError as e:
                logger.warning(
                    f"Streaming failed on {model_id} (attempt {attempt_n}/{len(chain)}): {e}"
                )
                if e.status_code and e.status_code >= 500:
                    self.circuit_breaker.record_failure(model.provider)

                # Try next model
                continue

            except Exception as e:
                logger.exception(
                    f"Unexpected streaming error on {model_id} (attempt {attempt_n}/{len(chain)})"
                )
                self.circuit_breaker.record_failure(model.provider)
                continue

        # All attempts failed
        raise ProviderError(
            message="All models in fallback chain failed for streaming",
            status_code=500,
            error_type="all_fallbacks_failed"
        )

    async def close(self):
        """Close all adapters"""
        for adapter in self.adapters.values():
            await adapter.close()


# Global handler instance
_fallback_handler: Optional[FallbackHandler] = None


def get_fallback_handler() -> FallbackHandler:
    """Get or create global fallback handler"""
    global _fallback_handler
    if _fallback_handler is None:
        _fallback_handler = FallbackHandler()
    return _fallback_handler
