# Multi-Provider Model Router + Fallback + RAG + Observability

This guide covers the complete implementation of multi-provider support in Open WebUI, including intelligent routing, automatic fallback, RAG transparency, and comprehensive observability.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup & Configuration](#setup--configuration)
4. [Components](#components)
5. [Usage](#usage)
6. [Observability Dashboard](#observability-dashboard)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### Features Implemented

✅ **Multi-Provider Support**
- OpenAI (GPT models)
- DeepSeek (DeepSeek Chat, DeepSeek Reasoner)
- Extensible adapter layer for adding more providers

✅ **Intelligent Model Routing**
- Content-based routing (code, RAG, tools, reasoning)
- Capability matching (tools, vision, JSON schema)
- Configurable routing rules in YAML

✅ **Automatic Fallback**
- Cross-provider fallback chains
- Circuit breaker pattern to prevent cascading failures
- Per-model timeout configuration

✅ **RAG Transparency + Reranking**
- Lexical reranking (BM25-style) improves chunk relevance
- Full transparency: see what chunks were retrieved and selected
- Sources panel in UI with scores

✅ **Observability Dashboard**
- Request logs with full routing trace
- Metrics: latency (P50/P95), error rate, fallback rate
- Circuit breaker status monitoring
- RAG hit rate tracking

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chat Completion Request                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Completion Handler                       │
│  • Analyzes request content                                 │
│  • Handles RAG if enabled                                   │
│  • Routes to best model                                     │
│  • Executes with fallback                                   │
│  • Logs to observability                                    │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Model Router  │  │  RAG Reranker  │  │   Fallback     │
│                │  │                │  │   Handler      │
│ • Routes based │  │ • BM25 scoring │  │ • Try primary  │
│   on content   │  │ • Chunk        │  │ • Fallback on  │
│ • Matches      │  │   selection    │  │   error        │
│   capabilities │  │ • Transparency │  │ • Circuit      │
│                │  │                │  │   breaker      │
└────────────────┘  └────────────────┘  └────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ OpenAI Adapter │  │DeepSeek Adapter│  │  More...       │
│                │  │                │  │                │
│ • Normalizes   │  │ • Normalizes   │  │                │
│   requests     │  │   requests     │  │                │
│ • Filters      │  │ • Filters      │  │                │
│   unsupported  │  │   unsupported  │  │                │
│   params       │  │   params       │  │                │
└────────────────┘  └────────────────┘  └────────────────┘
```

---

## Setup & Configuration

### 1. API Keys

**OpenAI:** Configure via Open WebUI Settings UI
- Go to Admin Panel → Settings → Connections
- Find "OpenAI API" section
- Enter your API key and base URL
- Save settings

**DeepSeek and others:** Set environment variables
```bash
export DEEPSEEK_API_KEY="sk-..."
```

The system automatically reads OpenAI keys from the UI settings and other providers from environment variables.

### 2. Model Registry Configuration

Edit `backend/open_webui/config/model_registry.yaml`:

```yaml
providers:
  openai:
    base_url: "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"
    timeout: 60

  deepseek:
    base_url: "https://api.deepseek.com/v1"
    api_key_env: "DEEPSEEK_API_KEY"
    timeout: 60

models:
  - id: "gpt-4"
    provider: "openai"
    supports_tools: true
    supports_vision: true
    supports_json_schema: true
    max_context_tokens: 128000
    max_output_tokens: 4096
    reliability_tier: 3
    cost_tier: 3
    speed_tier: 2
    tags: ["general", "rag", "reliable", "tools"]

  - id: "deepseek-chat"
    provider: "deepseek"
    supports_tools: true
    supports_vision: false
    supports_json_schema: true
    max_context_tokens: 64000
    max_output_tokens: 4000
    reliability_tier: 2
    cost_tier: 1
    speed_tier: 3
    tags: ["fast", "cheap", "general", "tools"]

routes:
  - name: "coding"
    when:
      any:
        - has_code_block: true
        - contains_regex: "\\b(python|javascript|docker|npm)\\b"
    use_model: "deepseek-chat"
    fallback_models: ["gpt-4"]
    timeout_ms: 45000

  - name: "default"
    when:
      always: true
    use_model: "deepseek-chat"
    fallback_models: ["gpt-4"]
    timeout_ms: 30000
```

### 3. Database Migration

The observability tables need to be created:

```bash
# Run migration (automatically creates tables on startup)
python -m open_webui.models.observability
```

---

## Components

### 1. Model Registry

**File:** `backend/open_webui/services/model_registry.py`

**Purpose:** Single source of truth for model configurations

**Key Classes:**
- `ModelSpec`: Model metadata (capabilities, tiers, tags)
- `RouteSpec`: Routing rule configuration
- `ModelRegistry`: Global registry singleton

**Usage:**
```python
from open_webui.services.model_registry import get_model_registry

registry = get_model_registry()
model = registry.get_model("gpt-4")
print(model.supports_tools)  # True
```

### 2. Provider Adapters

**File:** `backend/open_webui/services/provider_adapters.py`

**Purpose:** Normalize requests/responses across providers

**Key Classes:**
- `ProviderAdapter`: Base adapter interface
- `OpenAIAdapter`: OpenAI-specific adapter
- `DeepSeekAdapter`: DeepSeek-specific adapter
- `AdapterFactory`: Creates adapters by provider name

**Adding a New Provider:**
```python
class MyProviderAdapter(ProviderAdapter):
    def prepare_request(self, request: ProviderRequest) -> Dict[str, Any]:
        # Only include supported fields
        return {
            "model": request.model,
            "messages": request.messages,
            # ... add provider-specific fields
        }

    def parse_response(self, response: Dict[str, Any]) -> ProviderResponse:
        # Convert provider response to normalized format
        return ProviderResponse(
            content=response['choices'][0]['message']['content'],
            # ...
        )

# Register it
AdapterFactory.register_adapter("myprovider", MyProviderAdapter)
```

### 3. Model Router

**File:** `backend/open_webui/services/model_router.py`

**Purpose:** Select best model based on content and capabilities

**Key Classes:**
- `RoutingContext`: Input context for routing
- `RoutingDecision`: Output routing decision
- `ModelRouter`: Main routing logic

**Routing Logic:**
1. Analyze message content (code blocks, attachments, etc.)
2. Check for explicit user model selection
3. Match against route conditions in order
4. Validate model capabilities
5. Return primary model + fallback chain

**Example:**
```python
from open_webui.services.model_router import get_router, ModelRouter

router = get_router()

# Analyze messages
context = ModelRouter.analyze_message_content(
    messages=[{"role": "user", "content": "```python\nprint('hello')\n```"}],
    tools=None
)

# Route
decision = router.route(context)
print(decision.route_name)  # "coding"
print(decision.primary_model_id)  # "deepseek-chat"
print(decision.fallback_model_ids)  # ["gpt-4"]
```

### 4. Fallback Handler

**File:** `backend/open_webui/services/fallback_handler.py`

**Purpose:** Execute requests with automatic fallback

**Key Classes:**
- `FallbackHandler`: Orchestrates fallback logic
- `CircuitBreaker`: Prevents cascading failures
- `CircuitBreakerState`: Per-provider circuit state

**Circuit Breaker States:**
- `closed`: Normal operation
- `open`: Provider is failing, skip it
- `half_open`: Testing if provider recovered

**Example:**
```python
from open_webui.services.fallback_handler import get_fallback_handler
from open_webui.services.provider_adapters import ProviderRequest

handler = get_fallback_handler()

request = ProviderRequest(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    stream=False
)

response, attempts = await handler.execute_with_fallback(
    request=request,
    primary_model_id="gpt-4",
    fallback_model_ids=["deepseek-chat"],
    timeout_ms=30000
)

print(f"Succeeded with {len(attempts)} fallback attempts")
```

### 5. RAG Reranker

**File:** `backend/open_webui/services/rag_reranker.py`

**Purpose:** Rerank retrieved chunks for better relevance

**Key Classes:**
- `LexicalReranker`: BM25-style lexical scoring
- `RAGTransparency`: Wrapper for transparency logging
- `RAGChunk`: Input chunk format
- `RankedChunk`: Output with scores

**Reranking Algorithm:**
1. Calculate BM25 scores for lexical relevance
2. Combine with vector scores (weighted average)
3. Sort by final score
4. Select top K chunks

**Example:**
```python
from open_webui.services.rag_reranker import get_rag_transparency, RAGChunk

rag = get_rag_transparency()

chunks = [
    RAGChunk(
        doc_id="doc1",
        chunk_id="chunk1",
        content="Python is a programming language...",
        vector_score=0.85
    ),
    # ... more chunks
]

selected, result = rag.retrieve_and_rerank(
    query="What is Python?",
    retrieved_chunks=chunks,
    top_k=5
)

print(f"Reranked in {result.rerank_latency_ms}ms")
for ranked in selected:
    print(f"{ranked.chunk.doc_id}: {ranked.final_score:.3f}")
```

### 6. Observability

**Files:**
- `backend/open_webui/models/observability.py` - Database models
- `backend/open_webui/routers/observability.py` - API endpoints
- `src/lib/components/admin/Observability.svelte` - Dashboard UI

**Database Tables:**
- `request_logs`: Every chat completion request
- `rag_logs`: RAG retrieval details
- `circuit_breaker_states`: Circuit breaker state (optional)

**Metrics Captured:**
- Latency (total, provider, RAG, rerank)
- Tokens (input, output)
- Routing (route name, model used)
- Fallback (attempts, errors)
- RAG (attempted, used, top N/K)

---

## Usage

### Using the Completion Handler

**File:** `backend/open_webui/services/completion_handler.py`

This is the main entry point that orchestrates everything:

```python
from open_webui.services.completion_handler import get_completion_handler, CompletionRequest

handler = get_completion_handler()

request = CompletionRequest(
    messages=[
        {"role": "user", "content": "Explain async/await in Python"}
    ],
    user_id="user123",
    chat_id="chat456",
    model=None,  # Let router decide
    rag_enabled=True,
    rag_chunks=[
        {
            "doc_id": "doc1",
            "chunk_id": "chunk1",
            "content": "Async/await is...",
            "score": 0.9
        }
    ],
    knowledge_base_id="kb1"
)

response = await handler.complete(request)

print(response.content)
print(response.raw_response.get('rag_sources'))  # RAG sources for UI
```

### Integrating with Existing OpenAI Router

To integrate with the existing `/openai/chat/completions` endpoint:

```python
# In backend/open_webui/routers/openai.py

from open_webui.services.completion_handler import get_completion_handler, CompletionRequest

@router.post("/chat/completions")
async def generate_chat_completion(request: Request, form_data: dict, user=Depends(get_verified_user)):
    # ... existing code ...

    # Use completion handler instead of direct provider call
    handler = get_completion_handler()

    completion_request = CompletionRequest(
        messages=payload['messages'],
        model=payload.get('model'),
        temperature=payload.get('temperature'),
        max_tokens=payload.get('max_tokens'),
        tools=payload.get('tools'),
        response_format=payload.get('response_format'),
        stream=payload.get('stream', False),
        user_id=user.id,
        chat_id=metadata.get('chat_id'),
        rag_enabled=False,  # Set based on your RAG logic
        rag_chunks=None
    )

    response = await handler.complete(completion_request)

    return JSONResponse(content={
        "id": str(uuid.uuid4()),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": payload['model'],
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response.content
            },
            "finish_reason": response.finish_reason
        }],
        "usage": response.usage
    })
```

---

## Observability Dashboard

### Accessing the Dashboard

1. Navigate to Admin Panel
2. Click "Observability" in sidebar
3. View metrics, logs, and circuit breaker status

### Dashboard Features

**Metrics Overview:**
- Total requests
- Error rate
- Fallback rate
- P95 latency
- Provider distribution
- RAG hit rate

**Request Logs Table:**
- Timestamp
- Provider & Model
- Route name
- Latency
- Tokens (in/out)
- Status (success/error)
- Flags (fallback, RAG)

**Circuit Breakers:**
- Current state (closed/open/half-open)
- Failure count
- Reset button (admin only)

**Filters:**
- Provider
- Model
- Route name
- Errors only
- RAG used only
- Time range

### API Endpoints

```bash
# Get logs
GET /api/v1/observability/logs?provider=openai&limit=50

# Get metrics
GET /api/v1/observability/metrics?start_time=2025-01-01T00:00:00Z

# Get circuit breaker status
GET /api/v1/observability/circuit-breakers

# Reset circuit breaker
POST /api/v1/observability/circuit-breakers/openai/reset

# Get request details
GET /api/v1/observability/logs/{log_id}

# Get RAG details
GET /api/v1/observability/rag/logs/{request_id}

# Health check
GET /api/v1/observability/health
```

---

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest backend/tests/test_model_router.py
pytest backend/tests/test_rag_reranker.py
pytest backend/tests/test_fallback_handler.py

# Run with coverage
pytest --cov=backend/open_webui/services backend/tests/
```

### Test Coverage

✅ **Model Router Tests:**
- Content analysis (code blocks, tokens, tools)
- Route matching (coding, tools, RAG, default)
- Capability validation
- Fallback chain filtering

✅ **RAG Reranker Tests:**
- Lexical scoring (BM25)
- Reranking improves relevance
- Top-K selection
- Preview generation
- Chunk injection strategies

✅ **Fallback Handler Tests:**
- Success on first attempt
- Fallback on error
- All attempts fail
- Timeout handling
- Circuit breaker (open/close/half-open)

### Manual Testing Scenarios

**Scenario 1: Simulate OpenAI Outage**
1. Stop OpenAI provider (set invalid API key)
2. Send request with GPT-4 as primary
3. Verify fallback to DeepSeek succeeds
4. Check observability logs show fallback

**Scenario 2: Coding Prompt Routing**
1. Send message with Python code block
2. Verify routed to "coding" route
3. Verify DeepSeek selected (cheap, fast)
4. Check observability shows route name

**Scenario 3: RAG with Reranking**
1. Enable RAG
2. Send query with retrieved chunks
3. Verify reranking changes order
4. Check RAG sources in response
5. View RAG log in observability

**Scenario 4: Circuit Breaker**
1. Cause 5+ failures on a provider
2. Verify circuit breaker opens
3. Verify next requests skip that provider
4. Wait for timeout, verify half-open
5. Successful request closes circuit

---

## Troubleshooting

### Common Issues

**1. Models not loading**

```
Error: Model registry config not found
```

**Solution:** Ensure `backend/open_webui/config/model_registry.yaml` exists and is valid YAML.

```bash
python -c "import yaml; yaml.safe_load(open('backend/open_webui/config/model_registry.yaml'))"
```

**2. Circuit breaker stuck open**

**Solution:** Reset via API or wait for timeout:

```bash
curl -X POST http://localhost:8080/api/v1/observability/circuit-breakers/openai/reset \
  -H "Authorization: Bearer $TOKEN"
```

**3. RAG chunks not being reranked**

**Solution:** Verify chunks have `content` field and `vector_score`:

```python
chunks = [
    {
        "doc_id": "doc1",
        "chunk_id": "chunk1",
        "content": "...",  # Required
        "score": 0.85      # Required (renamed to vector_score internally)
    }
]
```

**4. Observability logs not appearing**

**Solution:** Check database tables were created:

```python
from open_webui.internal.db import engine
from sqlalchemy import inspect

inspector = inspect(engine)
print(inspector.get_table_names())
# Should include: request_logs, rag_logs, circuit_breaker_states
```

**5. Provider adapter errors**

```
Error: Provider deepseek not configured
```

**Solution:** Verify provider config in YAML and API key environment variable:

```bash
echo $DEEPSEEK_API_KEY
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:

```bash
export LOG_LEVEL=DEBUG
```

### Performance Tips

1. **Adjust reranker weights** for your use case:
   - More lexical overlap importance: increase `lexical_weight`
   - Trust vector scores more: increase `vector_weight`

2. **Tune circuit breaker thresholds**:
   ```python
   CircuitBreakerState(
       failure_threshold=10,  # More failures before opening
       timeout_seconds=120,   # Longer timeout before retry
   )
   ```

3. **Optimize routing rules**:
   - Put most common routes first
   - Use specific regexes to avoid overhead

4. **Cache registry**:
   - Registry loads once at startup
   - Reload only when config changes

---

## Summary

This implementation provides:

✅ **Multi-provider resilience**: Automatic fallback across OpenAI and DeepSeek
✅ **Intelligent routing**: Content-aware model selection
✅ **RAG transparency**: Full visibility into retrieval and reranking
✅ **Production observability**: Comprehensive metrics and logging
✅ **Extensibility**: Easy to add new providers and models

**Next Steps:**
1. Configure your providers in `model_registry.yaml`
2. Set API keys as environment variables
3. Integrate `CompletionHandler` into your chat endpoint
4. Monitor via Observability Dashboard
5. Tune routing rules and reranker weights for your use case

For questions or issues, refer to the test files for usage examples.
