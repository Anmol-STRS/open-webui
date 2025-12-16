"""
Unit tests for model router
"""

import pytest
from open_webui.services.model_router import ModelRouter, RoutingContext
from open_webui.services.model_registry import ModelRegistry, ModelSpec, ProviderConfig, RouteSpec, RouteCondition


@pytest.fixture
def test_registry():
    """Create test model registry"""
    registry = ModelRegistry()
    registry.config = type('Config', (), {
        'providers': {
            'openai': ProviderConfig(
                base_url='https://api.openai.com/v1',
                api_key_env='OPENAI_API_KEY'
            ),
            'deepseek': ProviderConfig(
                base_url='https://api.deepseek.com/v1',
                api_key_env='DEEPSEEK_API_KEY'
            )
        },
        'models': [
            ModelSpec(
                id='gpt-4',
                provider='openai',
                supports_tools=True,
                supports_vision=True,
                supports_json_schema=True,
                max_context_tokens=128000,
                max_output_tokens=4096,
                reliability_tier=3,
                cost_tier=3,
                speed_tier=2,
                tags=['general', 'rag', 'reliable', 'tools']
            ),
            ModelSpec(
                id='gpt-3.5-turbo',
                provider='openai',
                supports_tools=True,
                supports_vision=False,
                supports_json_schema=True,
                max_context_tokens=16385,
                max_output_tokens=4096,
                reliability_tier=3,
                cost_tier=1,
                speed_tier=3,
                tags=['fast', 'cheap', 'general']
            ),
            ModelSpec(
                id='deepseek-chat',
                provider='deepseek',
                supports_tools=True,
                supports_vision=False,
                supports_json_schema=True,
                max_context_tokens=64000,
                max_output_tokens=4000,
                reliability_tier=2,
                cost_tier=1,
                speed_tier=3,
                tags=['fast', 'cheap', 'general', 'tools']
            ),
            ModelSpec(
                id='deepseek-coder',
                provider='deepseek',
                supports_tools=False,
                supports_vision=False,
                supports_json_schema=False,
                max_context_tokens=16000,
                max_output_tokens=8192,
                reliability_tier=2,
                cost_tier=1,
                speed_tier=2,
                tags=['coding']
            )
        ],
        'routes': [
            RouteSpec(
                name='coding',
                when=RouteCondition(any=[{'has_code_block': True}]),
                use_model='deepseek-coder',
                fallback_models=['deepseek-chat', 'gpt-3.5-turbo'],
                timeout_ms=45000
            ),
            RouteSpec(
                name='tools',
                when=RouteCondition(any=[{'tools_enabled': True}]),
                use_model='gpt-4',
                fallback_models=['deepseek-chat'],
                timeout_ms=60000
            ),
            RouteSpec(
                name='default',
                when=RouteCondition(always=True),
                use_model='deepseek-chat',
                fallback_models=['gpt-3.5-turbo'],
                timeout_ms=30000
            )
        ]
    })()

    registry.models_by_id = {model.id: model for model in registry.config.models}
    registry.models_by_provider = {}
    for model in registry.config.models:
        if model.provider not in registry.models_by_provider:
            registry.models_by_provider[model.provider] = []
        registry.models_by_provider[model.provider].append(model)

    return registry


@pytest.fixture
def router(test_registry, monkeypatch):
    """Create router with test registry"""
    # Patch the global registry getter
    monkeypatch.setattr('open_webui.services.model_router.get_model_registry', lambda: test_registry)
    return ModelRouter()


def test_analyze_message_content_detects_code_blocks():
    """Test code block detection"""
    messages = [
        {'role': 'user', 'content': 'Here is some code:\n```python\nprint("hello")\n```'}
    ]
    context = ModelRouter.analyze_message_content(messages)
    assert context.has_code_block is True


def test_analyze_message_content_no_code_blocks():
    """Test no code blocks"""
    messages = [
        {'role': 'user', 'content': 'Just a regular message'}
    ]
    context = ModelRouter.analyze_message_content(messages)
    assert context.has_code_block is False


def test_analyze_message_content_tools_enabled():
    """Test tools detection"""
    messages = [{'role': 'user', 'content': 'test'}]
    tools = [{'type': 'function', 'function': {'name': 'test'}}]
    context = ModelRouter.analyze_message_content(messages, tools=tools)
    assert context.tools_enabled is True


def test_analyze_message_content_estimates_tokens():
    """Test token estimation"""
    messages = [
        {'role': 'user', 'content': 'a' * 4000}  # 4000 chars = ~1000 tokens
    ]
    context = ModelRouter.analyze_message_content(messages)
    assert context.estimated_context_tokens > 900
    assert context.estimated_context_tokens < 1100


def test_route_coding_prompt(router):
    """Test routing for coding prompts"""
    context = RoutingContext(
        last_user_message='```python\nprint("test")\n```',
        messages=[],
        has_code_block=True,
        estimated_context_tokens=100
    )

    decision = router.route(context)
    assert decision.route_name == 'coding'
    assert decision.primary_model_id == 'deepseek-coder'
    assert 'deepseek-chat' in decision.fallback_model_ids


def test_route_tools_required(router):
    """Test routing when tools are required"""
    context = RoutingContext(
        last_user_message='Call a function',
        messages=[],
        tools_enabled=True,
        estimated_context_tokens=100
    )

    decision = router.route(context)
    assert decision.route_name == 'tools'
    assert decision.primary_model_id == 'gpt-4'


def test_route_default(router):
    """Test default routing"""
    context = RoutingContext(
        last_user_message='Hello, how are you?',
        messages=[],
        estimated_context_tokens=50
    )

    decision = router.route(context)
    assert decision.route_name == 'default'
    assert decision.primary_model_id == 'deepseek-chat'


def test_route_user_override(router):
    """Test user model override"""
    context = RoutingContext(
        last_user_message='Test message',
        messages=[],
        estimated_context_tokens=50
    )

    decision = router.route(context, user_model_override='gpt-4')
    assert decision.route_name == 'user_override'
    assert decision.primary_model_id == 'gpt-4'


def test_validate_capabilities_tools(router):
    """Test capability validation for tools"""
    model = router.registry.get_model('deepseek-coder')
    context = RoutingContext(
        last_user_message='test',
        messages=[],
        tools_enabled=True,
        estimated_context_tokens=100
    )

    # deepseek-coder doesn't support tools
    assert router._validate_capabilities(model, context) is False


def test_validate_capabilities_json_schema(router):
    """Test capability validation for JSON schema"""
    model = router.registry.get_model('deepseek-coder')
    context = RoutingContext(
        last_user_message='test',
        messages=[],
        response_format_required='json_schema',
        estimated_context_tokens=100
    )

    # deepseek-coder doesn't support JSON schema
    assert router._validate_capabilities(model, context) is False


def test_validate_capabilities_context_length(router):
    """Test capability validation for context length"""
    model = router.registry.get_model('gpt-3.5-turbo')
    context = RoutingContext(
        last_user_message='test',
        messages=[],
        estimated_context_tokens=20000,  # Exceeds gpt-3.5-turbo limit
    )

    assert router._validate_capabilities(model, context) is False


def test_fallback_chain_filtered_by_capabilities(router):
    """Test that fallback chain only includes capable models"""
    context = RoutingContext(
        last_user_message='test',
        messages=[],
        tools_enabled=True,
        estimated_context_tokens=100
    )

    # Manually resolve fallbacks with tool requirement
    fallbacks = router._resolve_fallback_chain(
        ['deepseek-coder', 'deepseek-chat', 'gpt-4'],
        context
    )

    # deepseek-coder doesn't support tools, should be excluded
    assert 'deepseek-coder' not in fallbacks
    assert 'deepseek-chat' in fallbacks
    assert 'gpt-4' in fallbacks
