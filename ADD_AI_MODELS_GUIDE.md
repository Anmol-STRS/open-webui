# Adding DeepSeek, Claude, and Gemini Models to Open WebUI

This guide shows you how to add popular AI models (DeepSeek, Claude/Anthropic, and Google Gemini) to your Open WebUI instance.

## Overview

Open WebUI supports multiple AI providers through its OpenAI-compatible API configuration. You can add multiple providers and switch between them in the UI.

## Method 1: Via Admin Settings (Recommended)

### Step 1: Access Admin Panel

1. Open your Open WebUI instance (http://localhost:3000)
2. Click on your profile icon in the sidebar
3. Go to **Admin Panel** → **Settings** → **Connections**

### Step 2: Add API Keys and Base URLs

#### For DeepSeek

1. Get your API key from https://platform.deepseek.com/api_keys
2. In the **OpenAI API** section:
   - **API Base URL**: `https://api.deepseek.com`
   - **API Key**: Your DeepSeek API key (starts with `sk-...`)
3. Click **Save**

**Available Models:**
- `deepseek-chat` - Latest chat model
- `deepseek-coder` - Code-focused model
- `deepseek-reasoner` - Reasoning model

#### For Claude (Anthropic)

1. Get your API key from https://console.anthropic.com/settings/keys
2. In the **OpenAI API** section:
   - **API Base URL**: `https://api.anthropic.com/v1` (Note: Need a compatibility layer - see below)
   - **API Key**: Your Anthropic API key (starts with `sk-ant-...`)

**Note:** Claude uses a different API format. You have two options:

**Option A: Use LiteLLM Proxy (Recommended)**
```bash
# Install LiteLLM
pip install litellm[proxy]

# Start proxy
litellm --model claude-3-5-sonnet-20241022

# Then in Open WebUI:
# API Base URL: http://localhost:4000
# API Key: anything (litellm doesn't require it by default)
```

**Option B: Use OpenAI-compatible wrapper**
Use a service like https://anthropic-proxy.example.com or run your own wrapper.

**Available Models (via LiteLLM):**
- `claude-3-5-sonnet-20241022` - Latest Sonnet
- `claude-3-5-haiku-20241022` - Latest Haiku
- `claude-3-opus-20240229` - Opus (most capable)

#### For Google Gemini

1. Get your API key from https://aistudio.google.com/app/apikey
2. In the **OpenAI API** section:
   - **API Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai/`
   - **API Key**: Your Google AI Studio API key
3. Click **Save**

**Available Models:**
- `gemini-2.0-flash-exp` - Latest experimental Flash
- `gemini-1.5-pro` - Pro model
- `gemini-1.5-flash` - Fast model

### Step 3: Verify Models Are Available

1. Go to **Admin Panel** → **Settings** → **Models**
2. You should see your models listed
3. If not, click **Refresh Models** or restart the backend

## Method 2: Via Environment Variables

### Using `.env` file

Create or edit `.env` file in the root directory:

```bash
# DeepSeek
OPENAI_API_BASE_URLS=https://api.deepseek.com
OPENAI_API_KEYS=sk-your-deepseek-key

# Multiple providers (comma-separated)
OPENAI_API_BASE_URLS=https://api.deepseek.com,https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_API_KEYS=sk-your-deepseek-key,your-google-ai-key

# Enable OpenAI API
ENABLE_OPENAI_API=true
```

### Using Docker Compose

Edit your `docker-compose.yml`:

```yaml
version: '3'
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      - ENABLE_OPENAI_API=true
      - OPENAI_API_BASE_URLS=https://api.deepseek.com,https://generativelanguage.googleapis.com/v1beta/openai/
      - OPENAI_API_KEYS=sk-your-deepseek-key,your-google-ai-key
    volumes:
      - open-webui:/app/backend/data
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Method 3: Via Database (Advanced)

If you're running without Docker, you can add them directly through the admin UI or by modifying settings in the database.

## Adding Multiple Providers at Once

You can configure multiple providers by separating them with commas:

```bash
# In .env or environment variables
OPENAI_API_BASE_URLS=https://api.openai.com/v1,https://api.deepseek.com,https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_API_KEYS=sk-openai-key,sk-deepseek-key,google-ai-key
```

Each URL corresponds to the key at the same index (first URL with first key, etc.)

## Using LiteLLM for Multiple Providers (Recommended for Claude)

LiteLLM acts as a proxy that converts different API formats to OpenAI-compatible format.

### Step 1: Install LiteLLM

```bash
pip install litellm[proxy]
```

### Step 2: Create `litellm_config.yaml`

```yaml
model_list:
  - model_name: deepseek-chat
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: sk-your-deepseek-key
      api_base: https://api.deepseek.com

  - model_name: claude-3-5-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: sk-ant-your-claude-key

  - model_name: gemini-2.0-flash
    litellm_params:
      model: gemini/gemini-2.0-flash-exp
      api_key: your-google-ai-key

  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: sk-your-openai-key
```

### Step 3: Start LiteLLM Proxy

```bash
litellm --config litellm_config.yaml --port 4000
```

### Step 4: Configure Open WebUI

In Open WebUI Admin Settings:
- **API Base URL**: `http://localhost:4000`
- **API Key**: `anything` (or leave blank)

Now all your models will be available through the single LiteLLM endpoint!

## Verification

### Test Models in Chat

1. Create a new chat
2. Click the model selector (top of chat)
3. You should see all available models:
   - DeepSeek models (`deepseek-chat`, `deepseek-coder`)
   - Claude models (if using LiteLLM)
   - Gemini models (`gemini-2.0-flash-exp`, etc.)
4. Select a model and send a test message

### Check Model List via API

```bash
# Check what models are available
curl http://localhost:8080/api/models

# Should return a list including your configured models
```

## Troubleshooting

### Models Not Showing Up

1. **Refresh models**: Go to Admin Panel → Settings → Models → Click "Refresh Models"
2. **Check API keys**: Ensure your API keys are valid and have credits
3. **Check base URLs**: Make sure the URLs are correct (no trailing slashes for most providers)
4. **Restart backend**: Sometimes requires a restart to pick up new settings
   ```bash
   # If using start.py/start.bat
   # Stop and restart

   # If using Docker
   docker-compose restart
   ```

### Authentication Errors

- **DeepSeek**: Ensure key starts with `sk-` and has credits
- **Gemini**: Make sure you're using Google AI Studio key (not Vertex AI)
- **Claude**: Requires LiteLLM or compatible proxy

### API Format Issues

Some providers have slight differences:
- **Gemini**: Must use the `/v1beta/openai/` endpoint for OpenAI compatibility
- **Claude**: Requires conversion proxy (LiteLLM recommended)
- **DeepSeek**: Fully OpenAI-compatible, should work directly

## Cost Comparison (as of 2024)

| Provider | Model | Input | Output |
|----------|-------|-------|--------|
| DeepSeek | deepseek-chat | $0.14/M tokens | $0.28/M tokens |
| DeepSeek | deepseek-coder | $0.14/M tokens | $0.28/M tokens |
| Claude | claude-3-5-sonnet | $3/M tokens | $15/M tokens |
| Claude | claude-3-5-haiku | $0.80/M tokens | $4/M tokens |
| Gemini | gemini-2.0-flash | $0.075/M tokens | $0.30/M tokens |
| Gemini | gemini-1.5-pro | $1.25/M tokens | $5/M tokens |

## Advanced: Per-Model Configuration

You can also configure individual models with custom parameters:

1. Go to **Admin Panel** → **Settings** → **Models**
2. Click on a model to edit
3. Set custom parameters:
   - Temperature
   - Max tokens
   - Top P
   - System prompt
   - API-specific options

## Creating Model Presets

You can create custom model configurations:

1. Admin Panel → Settings → Models
2. Click **+ Add Model**
3. Configure:
   - **ID**: Custom identifier (e.g., `deepseek-creative`)
   - **Base Model**: Select base model
   - **Name**: Display name
   - **Parameters**: Custom temperature, max tokens, etc.

## Quick Setup Script

Here's a quick setup for all three providers:

```bash
# Set environment variables (Linux/Mac)
export ENABLE_OPENAI_API=true
export OPENAI_API_BASE_URLS="https://api.deepseek.com,https://generativelanguage.googleapis.com/v1beta/openai/"
export OPENAI_API_KEYS="your-deepseek-key,your-google-key"

# Or for Windows PowerShell
$env:ENABLE_OPENAI_API="true"
$env:OPENAI_API_BASE_URLS="https://api.deepseek.com,https://generativelanguage.googleapis.com/v1beta/openai/"
$env:OPENAI_API_KEYS="your-deepseek-key,your-google-key"

# Then start your backend
cd backend
python -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload
```

## Recommended Setup

For the best experience with all three providers:

1. **Use LiteLLM** - It handles all API differences automatically
2. **Configure via Admin UI** - Easier to manage and test
3. **Enable usage tracking** - The recent fix ensures token usage is tracked properly
4. **Set up model presets** - Create optimized configurations for different use cases

## Related Documentation

- [USAGE_TRACKING_FIX.md](USAGE_TRACKING_FIX.md) - How usage tracking works
- [REACT_PREVIEW_GUIDE.md](REACT_PREVIEW_GUIDE.md) - Using React preview feature
- [QUICK_START.md](QUICK_START.md) - Quick start guide

## Getting API Keys

- **DeepSeek**: https://platform.deepseek.com/api_keys
- **Claude (Anthropic)**: https://console.anthropic.com/settings/keys
- **Google Gemini**: https://aistudio.google.com/app/apikey
- **OpenAI** (for comparison): https://platform.openai.com/api-keys
