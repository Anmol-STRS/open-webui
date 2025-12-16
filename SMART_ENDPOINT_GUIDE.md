# Smart Chat Completion Endpoint Guide

## Overview

The Smart Chat Completion endpoint (`/api/chat/completions/smart`) is an enhanced version of the standard OpenAI chat completions endpoint that adds:

- **Intelligent Multi-Provider Routing**: Automatically selects the best model based on content
- **Cross-Provider Fallback**: Seamlessly falls back to alternative providers if primary fails
- **RAG Reranking**: Enhances retrieval-augmented generation with BM25 lexical scoring
- **Full Observability**: Logs all requests for metrics, debugging, and optimization

## Endpoint Details

**URL**: `POST /openai/chat/completions/smart`

**Authentication**: Required (Bearer token or session cookie)

**Content-Type**: `application/json`

## Request Format

The request format is OpenAI-compatible with additional optional fields:

```json
{
  "messages": [
    {"role": "user", "content": "Your message here"}
  ],
  "model": "gpt-4",           // Optional: override automatic routing
  "stream": false,            // Optional: enable streaming
  "temperature": 0.7,         // Optional: OpenAI parameters
  "max_tokens": 2000,
  "metadata": {               // Optional: additional context
    "chat_id": "uuid",
    "rag_enabled": true,
    "rag_chunks": [...]       // RAG context chunks
  }
}
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `messages` | array | Yes | Array of chat messages with `role` and `content` |
| `model` | string | No | Override automatic routing with specific model |
| `stream` | boolean | No | Enable SSE streaming (default: false) |
| `temperature` | float | No | Sampling temperature (0-2) |
| `max_tokens` | integer | No | Maximum tokens to generate |
| `top_p` | float | No | Nucleus sampling parameter |
| `frequency_penalty` | float | No | Frequency penalty (-2.0 to 2.0) |
| `presence_penalty` | float | No | Presence penalty (-2.0 to 2.0) |
| `stop` | string/array | No | Stop sequences |
| `tools` | array | No | Function calling tools |
| `tool_choice` | string/object | No | Tool selection strategy |
| `metadata` | object | No | Additional context (chat_id, RAG, etc.) |

## Response Format

### Non-Streaming Response

```json
{
  "id": "req_abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response text here"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  },
  "rag_sources": [          // Only present if RAG was used
    {
      "chunk_id": "chunk1",
      "score": 0.95,
      "content": "...",
      "source": "document.pdf"
    }
  ]
}
```

### Streaming Response

Server-Sent Events (SSE) format:

```
data: {"id":"req_abc123","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"req_abc123","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{"content":" there"},"finish_reason":null}]}

data: [DONE]
```

## How It Works

### 1. Content Analysis

The router analyzes your request to determine the best model:

```
User message: "Write a Python function..."
→ Detects: code block, programming language
→ Routes to: deepseek-chat (coding model)
```

### 2. Automatic Routing

Routes are evaluated in order from most specific to most general:

| Route | Triggers | Model | Fallbacks |
|-------|----------|-------|-----------|
| **coding** | Code blocks, programming terms | deepseek-chat | gpt-3.5-turbo, gpt-4 |
| **tools** | Function/tool calling enabled | gpt-4 | deepseek-chat |
| **rag** | RAG context provided | gpt-4 | gpt-3.5-turbo |
| **reasoning** | Complex analytical queries | gpt-4 | deepseek-chat |
| **default** | Everything else | deepseek-chat | gpt-3.5-turbo |

### 3. Fallback Execution

If the primary model fails, the system automatically tries fallbacks:

```
1. Try deepseek-chat → 503 Service Unavailable
2. Try gpt-3.5-turbo → 429 Rate Limited
3. Try gpt-4 → ✅ Success

Response includes fallback_chain for observability
```

### 4. Circuit Breaker

Protects against cascading failures:

- After 5 consecutive failures, provider is marked as "open"
- Requests skip open providers for 60 seconds
- After timeout, transitions to "half-open" for testing
- One successful request closes the circuit

## Usage Examples

### Example 1: Simple Chat

```python
import requests

response = requests.post(
    "http://localhost:8080/openai/chat/completions/smart",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "messages": [
            {"role": "user", "content": "What's the capital of France?"}
        ]
    }
)

data = response.json()
print(data["choices"][0]["message"]["content"])
```

### Example 2: Code Generation (Automatic Routing)

```python
# This will automatically route to the coding model
response = requests.post(
    "http://localhost:8080/openai/chat/completions/smart",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "messages": [
            {"role": "user", "content": """Write a Python function:
```python
def factorial(n):
    # implement here
```"""}
        ]
    }
)
```

### Example 3: Streaming with RAG

```python
response = requests.post(
    "http://localhost:8080/openai/chat/completions/smart",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "messages": [
            {"role": "user", "content": "Explain quantum computing"}
        ],
        "stream": True,
        "metadata": {
            "rag_enabled": True,
            "rag_chunks": [
                {
                    "content": "Quantum computing uses qubits...",
                    "score": 0.85,
                    "metadata": {"source": "quantum_intro.pdf"}
                }
            ]
        }
    },
    stream=True
)

for line in response.iter_lines():
    if line and line.startswith(b'data: '):
        data = line[6:]  # Remove 'data: ' prefix
        if data != b'[DONE]':
            chunk = json.loads(data)
            content = chunk["choices"][0]["delta"].get("content", "")
            print(content, end="", flush=True)
```

### Example 4: Model Override

```python
# Force use of a specific model (bypass routing)
response = requests.post(
    "http://localhost:8080/openai/chat/completions/smart",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "model": "gpt-4",  # Force GPT-4
        "messages": [
            {"role": "user", "content": "Complex reasoning task..."}
        ]
    }
)
```

### Example 5: Function Calling

```python
response = requests.post(
    "http://localhost:8080/openai/chat/completions/smart",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?"}
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        },
                        "required": ["location"]
                    }
                }
            }
        ]
    }
)
```

## Observability

All requests are logged to the observability system. Access the dashboard at:

```
http://localhost:8080/admin/observability
```

### Metrics Available

- **Request logs**: Full trace of each request
- **Routing decisions**: Which route matched and why
- **Fallback chains**: Which models were tried
- **Latency**: Total time and per-provider time
- **Token usage**: Prompt/completion tokens per request
- **Error rates**: Failures by provider and error type
- **RAG transparency**: Which chunks were selected and why
- **Circuit breaker status**: Provider health

## Configuration

Edit `backend/open_webui/config/model_registry.yaml` to:

- Add/remove providers
- Configure models
- Adjust routing rules
- Tune fallback chains
- Set timeouts and thresholds

See [SETUP_MULTI_PROVIDER.md](SETUP_MULTI_PROVIDER.md) for configuration details.

## Comparison: Standard vs Smart Endpoint

| Feature | `/chat/completions` | `/chat/completions/smart` |
|---------|---------------------|---------------------------|
| Model selection | Manual | Automatic based on content |
| Fallback | None | Cross-provider fallback chains |
| RAG reranking | Basic | BM25 lexical + vector hybrid |
| Observability | Basic | Full metrics + tracing |
| Circuit breaker | No | Yes (failure protection) |
| RAG transparency | No | Full source attribution |
| Performance | Direct pass-through | Intelligent routing overhead |

## When to Use Each Endpoint

### Use Standard `/chat/completions` when:
- You want direct pass-through to OpenAI/providers
- You have existing integrations that can't change
- You need minimal latency overhead
- You want to test a specific provider without routing

### Use Smart `/chat/completions/smart` when:
- You want automatic model selection
- You need resilience with fallback chains
- You want RAG transparency and reranking
- You need detailed observability metrics
- You want to optimize costs with smart routing
- You're building new features

## Testing

Run the test script to verify the endpoint:

```bash
python test_smart_completion.py
```

The script tests:
1. Simple completion
2. Coding completion (routing verification)
3. Streaming responses
4. Observability health check

## Troubleshooting

### 401 Unauthorized
- Ensure you're sending a valid Bearer token
- Get token from browser: `localStorage.getItem('token')`

### 500 Internal Server Error
- Check backend logs for stack trace
- Verify model_registry.yaml is valid
- Ensure API keys are configured

### "Model not found" Error
- Check that models are configured in model_registry.yaml
- Verify API keys are set (OpenAI via UI, others via env)

### No Routing (Always Uses Default)
- Check route conditions in model_registry.yaml
- Verify content matches routing patterns
- Check logs for routing decisions

### Circuit Breaker Stuck Open
- Wait 60 seconds for automatic reset
- Or manually reset via API:
  ```bash
  curl -X POST http://localhost:8080/api/v1/observability/circuit-breakers/{provider}/reset \
    -H "Authorization: Bearer $TOKEN"
  ```

## Migration from Standard Endpoint

To migrate existing code:

1. **Change the URL**:
   ```python
   # Old
   url = "/api/chat/completions"

   # New
   url = "/api/chat/completions/smart"
   ```

2. **No other changes required** - the API is backward compatible!

3. **Optionally add metadata** for RAG and chat tracking:
   ```python
   json={
       "messages": [...],
       "metadata": {
           "chat_id": chat_id,
           "rag_enabled": True,
           "rag_chunks": chunks
       }
   }
   ```

4. **Review observability metrics** to optimize routing

## Next Steps

- Configure additional providers in [model_registry.yaml](backend/open_webui/config/model_registry.yaml)
- Customize routing rules for your use cases
- Set up monitoring alerts based on observability metrics
- Tune circuit breaker thresholds for your traffic patterns
- Explore RAG reranking with different weight configurations

## API Reference

For complete API details, see:
- [MULTI_PROVIDER_GUIDE.md](MULTI_PROVIDER_GUIDE.md) - Architecture and internals
- [SETUP_MULTI_PROVIDER.md](SETUP_MULTI_PROVIDER.md) - Setup and configuration
- [model_registry.yaml](backend/open_webui/config/model_registry.yaml) - Configuration reference
