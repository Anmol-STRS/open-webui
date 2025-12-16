"""
Unit tests for fallback handler
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from open_webui.services.fallback_handler import (
    FallbackHandler,
    CircuitBreaker,
    CircuitBreakerState
)
from open_webui.services.provider_adapters import ProviderRequest, ProviderResponse, ProviderError
from open_webui.services.model_registry import ModelSpec


@pytest.fixture
def circuit_breaker():
    """Create circuit breaker"""
    return CircuitBreaker()


@pytest.fixture
def mock_registry():
    """Mock model registry"""
    registry = MagicMock()
    registry.get_model.side_effect = lambda model_id: {
        'model1': ModelSpec(
            id='model1',
            provider='provider1',
            supports_tools=True,
            max_context_tokens=4096,
            max_output_tokens=2048,
            reliability_tier=2,
            cost_tier=2,
            speed_tier=2,
            tags=['general']
        ),
        'model2': ModelSpec(
            id='model2',
            provider='provider2',
            supports_tools=True,
            max_context_tokens=4096,
            max_output_tokens=2048,
            reliability_tier=2,
            cost_tier=2,
            speed_tier=2,
            tags=['general']
        )
    }.get(model_id)

    registry.get_provider_config.side_effect = lambda provider: MagicMock(
        base_url=f'https://api.{provider}.com/v1',
        api_key_env=f'{provider.upper()}_API_KEY',
        timeout=60
    )

    registry.get_api_key.return_value = 'test-api-key'

    return registry


def test_circuit_breaker_initial_state():
    """Test circuit breaker initial state"""
    breaker = CircuitBreakerState()
    assert breaker.state == 'closed'
    assert breaker.failure_count == 0
    assert breaker.can_attempt() is True


def test_circuit_breaker_opens_after_threshold():
    """Test circuit breaker opens after failure threshold"""
    breaker = CircuitBreakerState(failure_threshold=3)

    # Record failures
    for _ in range(3):
        breaker.record_failure()

    assert breaker.state == 'open'
    assert breaker.can_attempt() is False


def test_circuit_breaker_half_open_after_timeout():
    """Test circuit breaker transitions to half-open after timeout"""
    breaker = CircuitBreakerState(failure_threshold=2, timeout_seconds=0)

    # Open the breaker
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == 'open'

    # Wait (simulated by 0 timeout) and check if half-open
    import time
    time.sleep(0.1)
    assert breaker.can_attempt() is True
    assert breaker.state == 'half_open'


def test_circuit_breaker_closes_on_success():
    """Test circuit breaker closes on success from half-open"""
    breaker = CircuitBreakerState()

    # Transition to half-open
    breaker.state = 'half_open'

    # Record success
    breaker.record_success()

    assert breaker.state == 'closed'
    assert breaker.failure_count == 0


def test_circuit_breaker_manager():
    """Test circuit breaker manager"""
    cb = CircuitBreaker()

    # Initially all providers can attempt
    assert cb.can_attempt('provider1') is True

    # Record failures for provider1
    for _ in range(5):
        cb.record_failure('provider1')

    # provider1 should be open
    assert cb.can_attempt('provider1') is False

    # provider2 should still be closed
    assert cb.can_attempt('provider2') is True


@pytest.mark.asyncio
async def test_fallback_handler_success_on_first_attempt(mock_registry):
    """Test successful completion on first attempt"""
    handler = FallbackHandler()
    handler.registry = mock_registry
    handler.circuit_breaker = CircuitBreaker()

    # Mock adapter
    mock_adapter = AsyncMock()
    mock_adapter.complete.return_value = ProviderResponse(
        content='Success',
        finish_reason='stop',
        usage={'prompt_tokens': 10, 'completion_tokens': 20}
    )

    handler.adapters['provider1'] = mock_adapter

    request = ProviderRequest(
        model='model1',
        messages=[{'role': 'user', 'content': 'test'}],
        stream=False
    )

    response, attempts = await handler.execute_with_fallback(
        request=request,
        primary_model_id='model1',
        fallback_model_ids=['model2'],
        timeout_ms=30000
    )

    assert response.content == 'Success'
    assert len(attempts) == 0  # No fallback attempts
    mock_adapter.complete.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_handler_fallback_on_error(mock_registry):
    """Test fallback to second model on error"""
    handler = FallbackHandler()
    handler.registry = mock_registry
    handler.circuit_breaker = CircuitBreaker()

    # Mock adapters
    mock_adapter1 = AsyncMock()
    mock_adapter1.complete.side_effect = ProviderError(
        message='Provider error',
        status_code=500,
        error_type='server_error'
    )

    mock_adapter2 = AsyncMock()
    mock_adapter2.complete.return_value = ProviderResponse(
        content='Success from fallback',
        finish_reason='stop'
    )

    handler.adapters['provider1'] = mock_adapter1
    handler.adapters['provider2'] = mock_adapter2

    request = ProviderRequest(
        model='model1',
        messages=[{'role': 'user', 'content': 'test'}],
        stream=False
    )

    response, attempts = await handler.execute_with_fallback(
        request=request,
        primary_model_id='model1',
        fallback_model_ids=['model2'],
        timeout_ms=30000
    )

    assert response.content == 'Success from fallback'
    assert len(attempts) == 1
    assert attempts[0].model_id == 'model1'
    assert attempts[0].error_type == 'server_error'


@pytest.mark.asyncio
async def test_fallback_handler_all_attempts_fail(mock_registry):
    """Test all attempts failing"""
    handler = FallbackHandler()
    handler.registry = mock_registry
    handler.circuit_breaker = CircuitBreaker()

    # Mock adapters - all fail
    mock_adapter1 = AsyncMock()
    mock_adapter1.complete.side_effect = ProviderError(
        message='Error 1',
        status_code=500,
        error_type='server_error'
    )

    mock_adapter2 = AsyncMock()
    mock_adapter2.complete.side_effect = ProviderError(
        message='Error 2',
        status_code=429,
        error_type='rate_limit'
    )

    handler.adapters['provider1'] = mock_adapter1
    handler.adapters['provider2'] = mock_adapter2

    request = ProviderRequest(
        model='model1',
        messages=[{'role': 'user', 'content': 'test'}],
        stream=False
    )

    with pytest.raises(ProviderError) as exc_info:
        await handler.execute_with_fallback(
            request=request,
            primary_model_id='model1',
            fallback_model_ids=['model2'],
            timeout_ms=30000
        )

    assert 'All models in fallback chain failed' in str(exc_info.value)


@pytest.mark.asyncio
async def test_fallback_handler_timeout(mock_registry):
    """Test timeout handling"""
    handler = FallbackHandler()
    handler.registry = mock_registry
    handler.circuit_breaker = CircuitBreaker()

    # Mock adapter that takes too long
    async def slow_complete(request):
        await asyncio.sleep(2)  # Longer than timeout
        return ProviderResponse(content='Too slow')

    mock_adapter = AsyncMock()
    mock_adapter.complete = slow_complete

    handler.adapters['provider1'] = mock_adapter

    request = ProviderRequest(
        model='model1',
        messages=[{'role': 'user', 'content': 'test'}],
        stream=False
    )

    with pytest.raises(ProviderError):
        await handler.execute_with_fallback(
            request=request,
            primary_model_id='model1',
            fallback_model_ids=[],
            timeout_ms=100  # Very short timeout
        )


@pytest.mark.asyncio
async def test_fallback_handler_skips_circuit_breaker_open(mock_registry):
    """Test that open circuit breakers are skipped"""
    handler = FallbackHandler()
    handler.registry = mock_registry
    handler.circuit_breaker = CircuitBreaker()

    # Open circuit for provider1
    for _ in range(5):
        handler.circuit_breaker.record_failure('provider1')

    # Mock adapter for provider2
    mock_adapter2 = AsyncMock()
    mock_adapter2.complete.return_value = ProviderResponse(
        content='Success from provider2'
    )

    handler.adapters['provider2'] = mock_adapter2

    request = ProviderRequest(
        model='model1',
        messages=[{'role': 'user', 'content': 'test'}],
        stream=False
    )

    response, attempts = await handler.execute_with_fallback(
        request=request,
        primary_model_id='model1',
        fallback_model_ids=['model2'],
        timeout_ms=30000
    )

    # Should succeed with model2
    assert response.content == 'Success from provider2'

    # Should have recorded that provider1 was skipped
    assert len(attempts) == 2  # Skip attempt + success attempt
    assert attempts[0].error_type == 'circuit_breaker_open'


def test_circuit_breaker_different_providers(circuit_breaker):
    """Test circuit breaker tracks providers independently"""
    # Fail provider1
    for _ in range(5):
        circuit_breaker.record_failure('provider1')

    # provider1 should be open
    assert circuit_breaker.can_attempt('provider1') is False

    # provider2 should still be closed
    assert circuit_breaker.can_attempt('provider2') is True

    # Success on provider2 shouldn't affect provider1
    circuit_breaker.record_success('provider2')
    assert circuit_breaker.can_attempt('provider1') is False
