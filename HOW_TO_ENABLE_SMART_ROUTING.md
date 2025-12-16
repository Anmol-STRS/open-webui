# How to Enable Smart Routing - Step by Step

## Quick Answer

You have **2 options** to enable the multi-provider smart routing:

### Option 1: Add as New Constant (Recommended - Easy to Test)

This creates a NEW constant so you can test smart routing without breaking existing functionality.

**File**: `src/lib/constants.ts`

**Add this line** after line 11:

```typescript
export const OPENAI_API_BASE_URL = `${WEBUI_BASE_URL}/openai`;
export const OPENAI_SMART_API_BASE_URL = `${WEBUI_BASE_URL}/openai/chat/completions/smart`;  // ADD THIS LINE
```

Then in your code, when you want smart routing, use:
```typescript
fetch(OPENAI_SMART_API_BASE_URL, {
  method: 'POST',
  body: JSON.stringify({messages: [...]})
})
```

### Option 2: Change the Default OpenAI Endpoint (System-Wide Change)

This makes ALL OpenAI chat completions use smart routing automatically.

**⚠️ WARNING**: This changes the behavior system-wide!

#### Step 1: Modify the Backend Router Mapping

**File**: `backend/open_webui/main.py`

**Find line 1392**:
```python
app.include_router(openai.router, prefix="/openai", tags=["openai"])
```

**No change needed** - the `/openai` prefix is correct.

#### Step 2: Create a Redirect in the OpenAI Router

**File**: `backend/open_webui/routers/openai.py`

**Find the existing endpoint** (around line 796):
```python
@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
```

**Replace the entire function** with a redirect to the smart endpoint:

```python
@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    """
    Redirect to smart chat completion endpoint for intelligent routing
    """
    # Just forward to the smart endpoint
    return await generate_smart_chat_completion(request, form_data, user)
```

This will make ALL `/openai/chat/completions` requests use the smart routing!

---

## Recommended Approach: Test First, Then Replace

### Phase 1: Test Smart Endpoint (No Code Changes Needed!)

The smart endpoint is **already working** at:
```
POST /openai/chat/completions/smart
```

Test it now:

1. **Get your auth token**:
   - Open browser DevTools (F12)
   - Console tab
   - Run: `localStorage.getItem('token')`
   - Copy the token

2. **Run the test script**:
   ```bash
   # Edit test_smart_completion.py and set AUTH_TOKEN
   python test_smart_completion.py
   ```

3. **Check the observability dashboard**:
   ```
   http://localhost:8080/admin/observability
   ```

   You should see:
   - Request logs with routing decisions
   - "coding" route for code queries
   - "default" route for general chat
   - Token usage and latency

### Phase 2: Use Smart Endpoint in Specific Places

After testing, use the smart endpoint where you want intelligent routing:

**Example in Svelte component**:

```typescript
// Before (standard OpenAI)
const response = await fetch(`${OPENAI_API_BASE_URL}/chat/completions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.token}`
  },
  body: JSON.stringify({
    model: 'gpt-4',  // Manual model selection
    messages: messages
  })
});

// After (smart routing)
const response = await fetch(`${OPENAI_API_BASE_URL}/chat/completions/smart`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.token}`
  },
  body: JSON.stringify({
    // No model needed - automatic routing!
    messages: messages
  })
});
```

### Phase 3: Replace System-Wide (Optional)

Once you're confident, make the redirect change in Option 2 above.

---

## Configuration: What Models/Providers to Use

The smart endpoint uses the configuration in:
```
backend/open_webui/config/model_registry.yaml
```

### Current Default Configuration

```yaml
providers:
  openai:
    base_url: "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"  # Reads from UI settings
    timeout: 60

  deepseek:
    base_url: "https://api.deepseek.com/v1"
    api_key_env: "DEEPSEEK_API_KEY"  # Reads from environment
    timeout: 60

models:
  - id: "gpt-4"
    provider: "openai"
    supports_tools: true
    supports_vision: true

  - id: "deepseek-chat"
    provider: "deepseek"
    supports_tools: true

routes:
  - name: "coding"
    when:
      any:
        - has_code_block: true
    use_model: "deepseek-chat"
    fallback_models: ["gpt-3.5-turbo", "gpt-4"]

  - name: "default"
    when:
      always: true
    use_model: "deepseek-chat"
    fallback_models: ["gpt-3.5-turbo"]
```

### To Change Which Models Are Used

**Edit**: `backend/open_webui/config/model_registry.yaml`

**Example - Use GPT-4 by default**:

```yaml
routes:
  - name: "default"
    when:
      always: true
    use_model: "gpt-4"  # Change this
    fallback_models: ["gpt-3.5-turbo", "deepseek-chat"]
```

**Example - Add GPT-4-Turbo**:

```yaml
models:
  - id: "gpt-4-turbo"  # Add this model
    provider: "openai"
    supports_tools: true
    supports_vision: true
    max_context_tokens: 128000

routes:
  - name: "coding"
    use_model: "gpt-4-turbo"  # Use it in routing
    fallback_models: ["deepseek-chat", "gpt-4"]
```

**After editing**, restart the backend server:
```bash
# Stop the backend (Ctrl+C in backend window)
# Then restart it
cd backend
python -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload
```

---

## API Keys Configuration

### OpenAI API Key (Set via UI)

1. Log in to Open WebUI as admin
2. Go to **Admin Panel** → **Settings** → **Connections**
3. Find "OpenAI API"
4. Enter your API key
5. Save

The smart endpoint automatically reads this!

### DeepSeek API Key (Set via Environment)

**Option A**: Environment variable
```bash
export DEEPSEEK_API_KEY="sk-..."
```

**Option B**: `.env` file
```bash
echo "DEEPSEEK_API_KEY=sk-..." >> .env
```

Then restart the server.

---

## Verification

### Check Everything is Working

1. **Health check**:
   ```bash
   curl http://localhost:8080/api/v1/observability/health
   ```

   Should return:
   ```json
   {
     "status": "healthy",
     "models_loaded": 4,
     "providers_configured": 2,
     "circuit_breaker_states": {
       "openai": "closed",
       "deepseek": "closed"
     }
   }
   ```

2. **Test smart endpoint**:
   ```bash
   curl -X POST http://localhost:8080/openai/chat/completions/smart \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
       "messages": [
         {"role": "user", "content": "Hello!"}
       ]
     }'
   ```

3. **Check dashboard**:
   ```
   http://localhost:8080/admin/observability
   ```

   You should see the request logged with:
   - Route name (e.g., "default")
   - Model used (e.g., "deepseek-chat")
   - Latency and token usage

---

## Summary: Where to Change

| What to Change | File | Line | What to Do |
|----------------|------|------|------------|
| **Test only** | None | - | Use `/openai/chat/completions/smart` URL directly |
| **Add constant** | `src/lib/constants.ts` | After 11 | Add `OPENAI_SMART_API_BASE_URL` |
| **System-wide redirect** | `backend/open_webui/routers/openai.py` | 796 | Redirect `/chat/completions` to smart |
| **Change routing logic** | `backend/open_webui/config/model_registry.yaml` | - | Edit routes and models |
| **Change default model** | `backend/open_webui/config/model_registry.yaml` | - | Change `use_model` in default route |
| **Add new provider** | `backend/open_webui/config/model_registry.yaml` | - | Add to `providers` section |

---

## Need Help?

- **Smart endpoint not found**: Check that backend restarted after adding the endpoint
- **"Not authenticated"**: Get token from `localStorage.getItem('token')`
- **No routing happening**: Check `model_registry.yaml` syntax
- **API keys not working**: OpenAI via UI settings, others via environment
- **Want to see what's happening**: Check `/admin/observability` dashboard

See [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) for full documentation!
