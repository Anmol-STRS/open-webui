# Multi-Provider Quick Reference

## 🚀 Quick Start

```bash
# 1. Set DeepSeek API key (OpenAI via UI)
export DEEPSEEK_API_KEY="sk-..."

# 2. Verify installation
python verify_multi_provider.py

# 3. Start server
# Database tables auto-created on first run

# 4. Configure OpenAI via UI
# Admin Panel → Settings → Connections → OpenAI API
```

## 🔑 API Key Sources

| Provider | Source | Path |
|----------|--------|------|
| OpenAI | **UI Settings** | Admin → Settings → Connections |
| DeepSeek | Environment | `DEEPSEEK_API_KEY` |
| Others | Environment | `{PROVIDER}_API_KEY` |

## 📁 Key Files

| File | Purpose |
|------|---------|
| `backend/open_webui/config/model_registry.yaml` | **Config**: Providers, models, routes |
| `backend/open_webui/services/completion_handler.py` | **Entry point**: Main orchestration |
| `src/lib/components/admin/Observability.svelte` | **Dashboard**: Metrics & logs UI |
| `verify_multi_provider.py` | **Verification**: Check installation |

## 🎯 Routing Logic

```
User Message
    ↓
Content Analysis
    ↓
Route Matching (in order):
  1. coding (has code blocks?)
  2. tools (tools_enabled?)
  3. rag_or_long (RAG or >12K tokens?)
  4. reasoning (complex analysis?)
  5. default (catch-all)
    ↓
Capability Check
    ↓
Select Model + Fallbacks
    ↓
Execute with Fallback
    ↓
Log to Observability
```

## 📊 Observability API

```bash
# Logs
GET /api/v1/observability/logs?provider=openai&limit=50

# Metrics
GET /api/v1/observability/metrics

# Circuit breakers
GET /api/v1/observability/circuit-breakers
POST /api/v1/observability/circuit-breakers/{provider}/reset

# Health
GET /api/v1/observability/health
```

## 🔧 Common Config Patterns

### Basic (OpenAI only)
```yaml
providers:
  openai: { base_url: "...", api_key_env: "OPENAI_API_KEY" }
models:
  - { id: "gpt-4", provider: "openai", ... }
routes:
  - { name: "default", when: { always: true }, use_model: "gpt-4" }
```

### Multi-Provider
```yaml
providers:
  openai: { ... }
  deepseek: { base_url: "https://api.deepseek.com/v1", ... }
models:
  - { id: "gpt-4", provider: "openai", ... }
  - { id: "deepseek-chat", provider: "deepseek", ... }
routes:
  - { name: "coding", use_model: "deepseek-chat", fallback_models: ["gpt-4"] }
  - { name: "default", use_model: "deepseek-chat", fallback_models: ["gpt-4"] }
```

## 🧪 Test Commands

```bash
# Unit tests
pytest backend/tests/test_model_router.py
pytest backend/tests/test_rag_reranker.py
pytest backend/tests/test_fallback_handler.py

# All tests with coverage
pytest --cov=backend/open_webui/services backend/tests/

# Verification
python verify_multi_provider.py
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| OpenAI key not found | Set via Admin Panel → Settings → Connections |
| DeepSeek key not found | `export DEEPSEEK_API_KEY="..."` |
| Config not loading | Check `backend/open_webui/config/model_registry.yaml` exists |
| Circuit breaker stuck | POST to `/api/v1/observability/circuit-breakers/{provider}/reset` |
| Routes not matching | Check route order (specific first, default last) |

## 💡 Usage Example

```python
from open_webui.services.completion_handler import (
    get_completion_handler,
    CompletionRequest
)

handler = get_completion_handler()

request = CompletionRequest(
    messages=[{"role": "user", "content": "```python\nprint('hi')\n```"}],
    user_id="user123",
    chat_id="chat456",
    model=None,  # Let router decide
    rag_enabled=False
)

response = await handler.complete(request)
print(response.content)
```

## 📈 Metrics Captured

- **Latency**: Total, provider, RAG, rerank (ms)
- **Tokens**: Input, output
- **Routing**: Route name, model used, fallbacks
- **Errors**: Type, short description, status code
- **RAG**: Attempted, used, topN, topK, hit rate
- **Circuit Breaker**: State, failure count

## 🎨 Dashboard URL

```
http://localhost:8080/admin/observability
```

## 📚 Documentation

- **Complete Guide**: [MULTI_PROVIDER_GUIDE.md](MULTI_PROVIDER_GUIDE.md)
- **Setup Guide**: [SETUP_MULTI_PROVIDER.md](SETUP_MULTI_PROVIDER.md)
- **Summary**: [MULTI_PROVIDER_SUMMARY.md](MULTI_PROVIDER_SUMMARY.md)

## ✅ Implementation Status

- ✅ Model registry with YAML config
- ✅ Provider adapters (OpenAI, DeepSeek)
- ✅ Intelligent routing with capability matching
- ✅ Automatic fallback with circuit breaker
- ✅ RAG transparency + BM25 reranking
- ✅ Observability dashboard with metrics
- ✅ Comprehensive unit tests
- ✅ Integration with Open WebUI settings (API keys)
- ✅ Documentation + verification script

**Status: Production Ready** 🎉
