# Multi-Provider Setup Guide

This guide explains how to configure the multi-provider system in your Open WebUI fork.

## API Key Configuration

### OpenAI API Keys

OpenAI API keys are configured through **Open WebUI's Settings UI**, not environment variables.

**Steps:**
1. Log in to Open WebUI as admin
2. Go to **Admin Panel** → **Settings** → **Connections**
3. Find the **OpenAI API** section
4. Enter your OpenAI API key(s)
5. Enter the base URL (default: `https://api.openai.com/v1`)
6. Save settings

The multi-provider system automatically reads these settings from the database.

### DeepSeek API Keys

For DeepSeek and other non-OpenAI providers, set environment variables:

```bash
export DEEPSEEK_API_KEY="sk-..."
```

Or add to your `.env` file:
```
DEEPSEEK_API_KEY=sk-...
```

### Adding Additional Providers

To add more providers (e.g., Anthropic, local models):

1. Add to `model_registry.yaml`:
```yaml
providers:
  anthropic:
    base_url: "https://api.anthropic.com/v1"
    api_key_env: "ANTHROPIC_API_KEY"
    timeout: 60
```

2. Set the environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

3. Add models for that provider:
```yaml
models:
  - id: "claude-3-opus"
    provider: "anthropic"
    supports_tools: true
    # ... other fields
```

## Model Registry Configuration

Edit `backend/open_webui/config/model_registry.yaml`:

### Minimum Configuration

```yaml
providers:
  openai:
    base_url: "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"  # Reads from UI settings
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
    tags: ["general", "reliable"]

routes:
  - name: "default"
    when:
      always: true
    use_model: "gpt-4"
    fallback_models: []
    timeout_ms: 30000
```

### Production Configuration

See [model_registry.yaml](backend/open_webui/config/model_registry.yaml) for a complete example with:
- Multiple providers (OpenAI, DeepSeek)
- Multiple models per provider
- Intelligent routing rules (coding, RAG, tools, reasoning)
- Fallback chains

## Database Setup

The observability tables are **automatically created** on server startup. No manual migration needed!

When you start the Open WebUI server, you'll see:
```
INFO: Initializing observability tables...
INFO: Observability tables initialized
```

This creates three tables:
- `request_logs` - All chat completion requests
- `rag_logs` - RAG retrieval details
- `circuit_breaker_states` - Circuit breaker status

## Verification

Run the verification script:

```bash
python verify_multi_provider.py
```

This checks:
- ✓ All files are present
- ✓ Modules can be imported
- ✓ Config file is valid YAML
- ✓ API keys are configured (OpenAI from UI, others from env)
- ✓ Database models are ready
- ✓ Functional tests pass

## Quick Test

Test the system without modifying existing code:

```python
# In Python shell or script
from open_webui.services.model_registry import get_model_registry
from open_webui.services.model_router import get_router, RoutingContext

# 1. Check registry loaded
registry = get_model_registry()
print(f"Loaded {len(registry.models_by_id)} models")

# 2. Test API key retrieval
openai_key = registry.get_api_key('openai')
print(f"OpenAI key configured: {bool(openai_key)}")

# 3. Test routing
router = get_router()
context = RoutingContext(
    last_user_message="```python\nprint('hello')\n```",
    messages=[],
    has_code_block=True,
    estimated_context_tokens=100
)
decision = router.route(context)
print(f"Routed to: {decision.route_name} -> {decision.primary_model_id}")
```

## Integration with Existing Code

The multi-provider system is **ready to use** but not yet integrated into the main chat flow.

### Option 1: Gradual Integration (Recommended)

Add multi-provider support to specific routes first:

```python
# In a new route, e.g., /api/v1/chat/smart
from open_webui.services.completion_handler import get_completion_handler, CompletionRequest

@router.post("/chat/smart")
async def smart_completion(request: dict, user=Depends(get_verified_user)):
    handler = get_completion_handler()

    completion_request = CompletionRequest(
        messages=request['messages'],
        user_id=user.id,
        chat_id=request.get('chat_id'),
        rag_enabled=request.get('rag_enabled', False),
        rag_chunks=request.get('rag_chunks'),
    )

    response = await handler.complete(completion_request)

    return {
        "content": response.content,
        "rag_sources": response.raw_response.get('rag_sources', [])
    }
```

### Option 2: Full Integration

Replace the existing OpenAI router logic with the completion handler. See [MULTI_PROVIDER_GUIDE.md](MULTI_PROVIDER_GUIDE.md) for detailed integration steps.

## Observability Dashboard

Access the dashboard at:
```
http://localhost:8080/admin/observability
```

Features:
- Real-time metrics (error rate, latency, fallback rate)
- Request logs with full routing trace
- Circuit breaker status
- RAG hit rate and transparency
- Filters: provider, model, route, errors, RAG used

## Configuration Tips

### 1. Route Priority

Routes are evaluated in order. Put most specific routes first:

```yaml
routes:
  - name: "coding"           # Specific: code blocks
  - name: "tools"            # Specific: tools enabled
  - name: "rag"              # Specific: RAG enabled
  - name: "default"          # Catch-all: always matches
```

### 2. Fallback Chains

Design fallback chains for resilience:

```yaml
# Good: Cross-provider fallback
use_model: "deepseek-chat"
fallback_models: ["gpt-3.5-turbo", "gpt-4"]

# Better: Capability-aware fallback
use_model: "gpt-4"              # High reliability, expensive
fallback_models: ["gpt-3.5-turbo", "deepseek-chat"]  # Cheaper alternatives
```

### 3. Model Tiers

Use tiers to influence routing:

```yaml
# Fast, cheap model for casual chat
- id: "deepseek-chat"
  reliability_tier: 2
  cost_tier: 1       # Cheapest
  speed_tier: 3      # Fastest
  tags: ["fast", "cheap", "general"]

# Reliable, expensive model for critical tasks
- id: "gpt-4"
  reliability_tier: 3  # Most reliable
  cost_tier: 3         # Most expensive
  speed_tier: 2        # Medium speed
  tags: ["reliable", "tools", "rag"]
```

### 4. Circuit Breaker Tuning

Adjust thresholds in code if needed:

```python
# In fallback_handler.py
CircuitBreakerState(
    failure_threshold=5,   # Open after 5 failures
    timeout_seconds=60,    # Wait 60s before retry
    half_open_attempts=1   # Test with 1 request
)
```

## Troubleshooting

### OpenAI Key Not Found

**Symptom:** `ValueError: API key not found for provider openai`

**Solution:**
1. Check that you've set the OpenAI API key in Open WebUI settings
2. Verify the key is saved in the database:
   ```python
   from open_webui.config import OPENAI_API_KEYS
   print(OPENAI_API_KEYS)
   ```
3. If empty, go to Admin Panel → Settings → Connections and save the key again

### DeepSeek Key Not Found

**Symptom:** `ValueError: API key not found for provider deepseek`

**Solution:**
```bash
# Set environment variable
export DEEPSEEK_API_KEY="sk-..."

# Or add to .env file
echo "DEEPSEEK_API_KEY=sk-..." >> .env

# Restart the server
```

### Config File Not Loading

**Symptom:** `Model registry config not found at ...`

**Solution:**
1. Ensure the file exists: `backend/open_webui/config/model_registry.yaml`
2. Check YAML syntax: `python -c "import yaml; yaml.safe_load(open('backend/open_webui/config/model_registry.yaml'))"`
3. Set custom path: `export MODEL_REGISTRY_CONFIG=/path/to/config.yaml`

### Circuit Breaker Stuck Open

**Symptom:** All requests to a provider are skipped

**Solution:**
Reset via API:
```bash
curl -X POST http://localhost:8080/api/v1/observability/circuit-breakers/openai/reset \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Or wait for the timeout (default: 60 seconds) and the circuit will transition to half-open.

## Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | Set via UI instead (Admin → Settings → Connections) |
| `DEEPSEEK_API_KEY` | Yes* | Required if using DeepSeek models |
| `MODEL_REGISTRY_CONFIG` | No | Path to custom config (default: `backend/open_webui/config/model_registry.yaml`) |

*Required only if DeepSeek models are configured in your registry

## Next Steps

1. ✅ Set API keys (OpenAI via UI, DeepSeek via env)
2. ✅ Customize `model_registry.yaml` for your use case
3. ✅ Run `python verify_multi_provider.py`
4. ✅ Access observability dashboard to verify it works
5. ✅ Integrate `CompletionHandler` into your chat endpoint
6. ✅ Monitor metrics and tune routing rules

For detailed API usage and architecture, see [MULTI_PROVIDER_GUIDE.md](MULTI_PROVIDER_GUIDE.md).
