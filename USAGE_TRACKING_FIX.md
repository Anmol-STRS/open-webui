# Usage Tracking Fix

## Problem

The `/api/usage/details` endpoint was returning empty usage data (0 tokens, 0 cost) despite having chat conversations. This was because the AI model responses were not including usage information in the message metadata.

## Root Cause

When using OpenAI-compatible APIs with **streaming enabled** (which is the default in Open WebUI), the usage data is NOT included in the response unless you explicitly request it by adding `stream_options: { include_usage: true }` to the request payload.

### Investigation Results

1. **Messages without usage data**: Debug script revealed that messages in the database had no `usage` or `info` fields containing token counts
2. **Model type**: You're using `gpt-5.2`, which is an OpenAI-compatible model
3. **Missing parameter**: The OpenAI router wasn't adding `stream_options` to enable usage tracking

## The Fix

Modified [backend/open_webui/routers/openai.py:893-896](backend/open_webui/routers/openai.py#L893-L896) to automatically add `stream_options` when streaming is enabled:

```python
# Enable usage tracking for streaming responses
# This ensures usage data is included in the response so it can be tracked
if payload.get("stream", False) and "stream_options" not in payload:
    payload["stream_options"] = {"include_usage": True}
```

This change:
- ✅ Automatically enables usage tracking for all streaming OpenAI-compatible requests
- ✅ Respects existing `stream_options` if already set (doesn't override)
- ✅ Works with Azure OpenAI (filtered by API version in `convert_to_azure_payload`)
- ✅ Compatible with all OpenAI-compatible providers that support this parameter

## How to Test

### 1. Restart the Backend Server

```bash
# If using start.py/start.bat/start.sh, stop and restart
# Or manually restart the backend:
cd backend
python -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload
```

### 2. Create a New Chat

After restarting, create a **new chat conversation** and send a few messages. The fix only applies to new messages created after the backend restart.

### 3. Check Usage Data

**Option A: Via User Menu (UI)**
1. Click your profile icon in the sidebar
2. You should see a usage statistics panel with:
   - Total tokens used
   - Breakdown by type (prompt, completion, cached)
   - Estimated cost
   - Number of tracked responses

**Option B: Via API**
```bash
# Get usage details via API
curl -X GET "http://localhost:8080/api/usage/details" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Option C: Via Debug Script**
```bash
# Run the debug script to see raw data
python debug_usage.py
```

Expected output should show:
```
Message X/Y:
  Role: assistant
  Has usage: YES
  Usage keys: ['prompt_tokens', 'completion_tokens', 'total_tokens']
```

### 4. What to Look For

✅ **Working correctly:**
- UserMenu shows token counts and costs
- Debug script shows `Has usage: YES` for assistant messages
- Messages have `usage` field with token counts

❌ **Still not working:**
- All zeros in usage display
- Debug script shows `Has usage: NO`
- Messages missing `usage` field

## If Usage is Still Not Working

If usage tracking still doesn't work after the fix, check these:

### 1. Check Your OpenAI Provider Compatibility

Not all OpenAI-compatible providers support `stream_options`. Test if your provider supports it:

```bash
# Test with your actual API endpoint
curl -X POST "YOUR_OPENAI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5.2",
    "messages": [{"role": "user", "content": "Hi"}],
    "stream": true,
    "stream_options": {"include_usage": true}
  }'
```

If you get an error about `stream_options` not being recognized, your provider doesn't support this parameter yet.

### 2. Disable Streaming (Workaround)

If your provider doesn't support `stream_options`, you can disable streaming in the model settings:

1. Go to Settings → Models
2. Find your model (gpt-5.2)
3. Edit model parameters
4. Set `stream: false`

Note: This will make responses appear all at once instead of word-by-word.

### 3. Check Non-Streaming Usage Data

The middleware also checks for usage data in non-streaming responses. If streaming is disabled, usage should automatically be included by most providers.

## Technical Details

### How Usage Data Flows

1. **Request**: Open WebUI sends chat completion request with `stream_options: { include_usage: true }`
2. **Response**: OpenAI-compatible API returns streaming chunks, with usage data in the final chunk
3. **Middleware**: [backend/open_webui/utils/middleware.py:2523-2543](backend/open_webui/utils/middleware.py#L2523-L2543) extracts usage from response
4. **Storage**: Usage is saved to message via `Chats.upsert_message_to_chat_by_id_and_message_id()`
5. **Extraction**: `/api/usage/details` endpoint uses `_extract_usage_payload()` to find usage in messages
6. **Display**: Frontend shows aggregated usage in UserMenu via UsagePreview component

### Usage Data Structure

The usage data can be in several formats, all supported:

```json
// OpenAI format
{
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  }
}

// Nested in info
{
  "info": {
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 50
    }
  }
}

// Ollama format (llama.cpp)
{
  "usage": {
    "prompt_eval_count": 10,
    "eval_count": 50
  }
}
```

The `_normalize_usage_payload()` function handles all these formats automatically.

## Files Modified

- [backend/open_webui/routers/openai.py](backend/open_webui/routers/openai.py) - Added `stream_options` for usage tracking

## Files Created (for debugging)

- [debug_usage.py](debug_usage.py) - Script to check usage data in database
- [check_models.py](check_models.py) - Script to check configured models

## Related Code

- **Usage extraction**: [backend/open_webui/main.py:2043-2151](backend/open_webui/main.py#L2043-L2151)
- **Usage endpoint**: [backend/open_webui/main.py:2206-2278](backend/open_webui/main.py#L2206-L2278)
- **Frontend API**: [src/lib/apis/index.ts:1351](src/lib/apis/index.ts#L1351)
- **UI Component**: [src/lib/components/layout/Sidebar/UsagePreview.svelte](src/lib/components/layout/Sidebar/UsagePreview.svelte)
- **Middleware capture**: [backend/open_webui/utils/middleware.py:2521-2543](backend/open_webui/utils/middleware.py#L2521-L2543)

## Additional Notes

### Azure OpenAI Support

For Azure OpenAI, `stream_options` is only supported in API version `2024-09-01-preview` or later. The code automatically filters this parameter out for older API versions via the `get_azure_allowed_params()` function.

### Cost Estimation

Usage tracking includes cost estimation when the AI provider returns cost information. This is automatically extracted and normalized from various formats:
- `total_cost`, `cost`, `estimated_cost`
- `prompt_cost`, `completion_cost`, `cached_cost`
- Currency information from `currency`, `cost_currency`, or `total_cost_currency`

### Performance Impact

Enabling usage tracking has minimal performance impact:
- Adds ~100 bytes to each request payload
- Adds ~200 bytes to streaming response (one final chunk)
- Database storage: ~100 bytes per message for usage metadata
