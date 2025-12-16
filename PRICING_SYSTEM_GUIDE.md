# Model Pricing System Guide

## Overview

The pricing system automatically calculates costs for AI model usage based on token consumption. It fetches and stores pricing data for popular AI models and uses it to provide accurate cost estimates in the usage tracking system.

## Problem Solved

**Before:** Usage tracking showed "No pricing data detected" because API providers don't always include cost information in their responses.

**After:** Pricing system automatically calculates costs based on:
- Token usage (input, output, cached tokens)
- Current model pricing stored in database
- Automatic fallback when API doesn't provide cost data

## Features

✅ **Automatic Cost Calculation** - Calculates costs even when API doesn't provide them
✅ **Multi-Provider Support** - OpenAI, Claude/Anthropic, DeepSeek, Google Gemini
✅ **Database Storage** - Persistent pricing data with easy updates
✅ **Admin Management** - Full CRUD API for pricing management
✅ **Flexible Lookup** - Smart model matching with multiple fallback strategies
✅ **Cache Support** - Separate pricing for cached vs fresh tokens
✅ **Auto-Initialize** - Pre-loads current pricing on first startup

## Architecture

### Components

1. **Database Model** (`backend/open_webui/models/pricing.py`)
   - `Pricing` - SQLAlchemy model for storing pricing data
   - `PricingTable` - CRUD operations and cost calculation
   - Stores: input cost, output cost, cache costs, currency, metadata

2. **Pricing Data** (`backend/open_webui/utils/pricing_data.py`)
   - Current pricing for 20+ popular models
   - Helper functions for data access
   - Auto-initialization logic

3. **API Routes** (`backend/open_webui/routers/pricing.py`)
   - REST API for pricing management
   - Endpoints for CRUD operations
   - Cost calculation endpoint

4. **Integration** (`backend/open_webui/main.py`)
   - Enhanced `get_usage_details` endpoint
   - Automatic pricing fallback
   - Startup initialization

### Data Flow

```
User sends message → AI responds with tokens → Usage data captured
                                                        ↓
                                           API provides cost?
                                          ↙                  ↘
                                       YES                  NO
                                         ↓                    ↓
                                   Use API cost      Look up in pricing DB
                                         ↓                    ↓
                                         Calculate using:
                                         - input_tokens × input_cost_per_million
                                         - output_tokens × output_cost_per_million
                                         - cached_tokens × cache_cost_per_million
                                                ↓
                                         Store in message metadata
                                                ↓
                                         Display in Usage UI
```

## Database Schema

```sql
CREATE TABLE pricing (
    id VARCHAR PRIMARY KEY,              -- e.g., "openai/gpt-4o"
    provider VARCHAR,                    -- e.g., "openai"
    model_name VARCHAR,                  -- e.g., "gpt-4o"
    display_name VARCHAR,                -- e.g., "GPT-4o"

    input_cost_per_million FLOAT,       -- Cost per 1M input tokens
    output_cost_per_million FLOAT,      -- Cost per 1M output tokens
    cache_read_cost_per_million FLOAT,  -- Cost per 1M cached tokens read
    cache_write_cost_per_million FLOAT, -- Cost per 1M cache write tokens

    currency VARCHAR DEFAULT 'USD',

    source VARCHAR,                      -- "official", "manual", "scraped"
    source_url TEXT,                     -- URL to pricing page
    notes TEXT,                          -- Additional info

    is_active BOOLEAN DEFAULT TRUE,
    last_updated BIGINT,
    created_at BIGINT
);
```

## API Endpoints

### Get All Pricing
```http
GET /api/v1/pricing?active_only=true
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": "openai/gpt-4o",
    "provider": "openai",
    "model_name": "gpt-4o",
    "display_name": "GPT-4o",
    "input_cost_per_million": 2.50,
    "output_cost_per_million": 10.00,
    "cache_read_cost_per_million": 1.25,
    "cache_write_cost_per_million": 0.0,
    "currency": "USD",
    "source": "official",
    "source_url": "https://openai.com/api/pricing/",
    "is_active": true,
    "last_updated": 1705000000,
    "created_at": 1705000000
  }
]
```

### Get Pricing by Provider
```http
GET /api/v1/pricing/provider/{provider}?active_only=true
Authorization: Bearer {token}
```

### Calculate Cost
```http
POST /api/v1/pricing/calculate
Authorization: Bearer {token}
Content-Type: application/json

{
  "model_id": "gpt-4o",
  "input_tokens": 1000,
  "output_tokens": 500,
  "cache_read_tokens": 100,
  "cache_write_tokens": 0
}
```

**Response:**
```json
{
  "input_cost": 0.0025,
  "output_cost": 0.005,
  "cache_read_cost": 0.000125,
  "cache_write_cost": 0.0,
  "total_cost": 0.007625,
  "currency": "USD",
  "pricing_available": true
}
```

### Create/Update Pricing (Admin Only)
```http
POST /api/v1/pricing/upsert
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "provider": "openai",
  "model_name": "gpt-4o",
  "display_name": "GPT-4o",
  "input_cost_per_million": 2.50,
  "output_cost_per_million": 10.00,
  "cache_read_cost_per_million": 1.25,
  "cache_write_cost_per_million": 0.0,
  "currency": "USD",
  "source": "official",
  "source_url": "https://openai.com/api/pricing/"
}
```

### Initialize Pricing Database (Admin Only)
```http
POST /api/v1/pricing/initialize
Authorization: Bearer {admin_token}
```

Loads all built-in pricing data into the database.

## Pre-Loaded Models

### OpenAI
- **gpt-4o**: $2.50 / $10.00 per 1M tokens
- **gpt-4o-mini**: $0.15 / $0.60 per 1M tokens
- **gpt-4-turbo**: $10.00 / $30.00 per 1M tokens
- **gpt-3.5-turbo**: $0.50 / $1.50 per 1M tokens
- **o1**: $15.00 / $60.00 per 1M tokens (reasoning)
- **o1-mini**: $3.00 / $12.00 per 1M tokens

### Anthropic (Claude)
- **claude-3-5-sonnet-20241022**: $3.00 / $15.00 per 1M tokens
- **claude-3-5-haiku-20241022**: $0.80 / $4.00 per 1M tokens
- **claude-3-opus-20240229**: $15.00 / $75.00 per 1M tokens

### DeepSeek
- **deepseek-chat**: $0.14 / $0.28 per 1M tokens
- **deepseek-coder**: $0.14 / $0.28 per 1M tokens
- **deepseek-reasoner**: $0.55 / $2.19 per 1M tokens

### Google Gemini
- **gemini-2.0-flash-exp**: Free (experimental)
- **gemini-1.5-pro**: $1.25 / $5.00 per 1M tokens
- **gemini-1.5-flash**: $0.075 / $0.30 per 1M tokens
- **gemini-1.5-flash-8b**: $0.0375 / $0.15 per 1M tokens

Format: Input cost / Output cost per 1M tokens

## Usage in Code

### Calculate Cost Manually

```python
from open_webui.models.pricing import Pricings

# Calculate cost for a model
cost_data = Pricings.calculate_cost(
    provider="openai",
    model_name="gpt-4o",
    input_tokens=1000,
    output_tokens=500,
    cache_read_tokens=100,
    cache_write_tokens=0
)

print(f"Total cost: ${cost_data['total_cost']:.4f} {cost_data['currency']}")
# Output: Total cost: $0.0076 USD
```

### Add Custom Pricing

```python
from open_webui.models.pricing import Pricings, PricingForm

# Add pricing for a custom model
form = PricingForm(
    provider="custom",
    model_name="my-model",
    display_name="My Custom Model",
    input_cost_per_million=1.00,
    output_cost_per_million=2.00,
    cache_read_cost_per_million=0.10,
    cache_write_cost_per_million=0.0,
    currency="USD",
    source="manual",
    notes="Custom pricing for internal model"
)

pricing = Pricings.upsert_pricing(form)
```

### Query Pricing

```python
# Get all pricing
all_pricing = Pricings.get_all_pricing(active_only=True)

# Get pricing for specific provider
openai_pricing = Pricings.get_pricing_by_provider("openai")

# Get pricing for specific model
gpt4_pricing = Pricings.get_pricing_by_model("openai", "gpt-4o")
```

## How It Works

### Model Lookup Strategy

The system uses multiple strategies to find pricing:

1. **Direct lookup**: `provider/model_name` (e.g., `openai/gpt-4o`)
2. **Full ID**: Model name with slash (e.g., `openai/gpt-4o`)
3. **Model name only**: Just the model part (e.g., `gpt-4o`)
4. **Common providers**: Try with common provider prefixes
5. **Fuzzy match**: Match by model name across all providers

This ensures pricing is found even if the model ID format varies.

### Cost Calculation

```
Input Cost = (input_tokens / 1,000,000) × input_cost_per_million
Output Cost = (output_tokens / 1,000,000) × output_cost_per_million
Cache Read Cost = (cache_tokens / 1,000,000) × cache_read_cost_per_million
Cache Write Cost = (cache_write_tokens / 1,000,000) × cache_write_cost_per_million

Total Cost = Input Cost + Output Cost + Cache Read Cost + Cache Write Cost
```

### Integration with Usage Tracking

When `/api/usage/details` is called:

1. Extract usage data from messages
2. Check if API provided cost data
3. If no cost data:
   - Get model ID from message
   - Look up pricing in database
   - Calculate cost using token counts
   - Add to usage summary
4. Return aggregated usage with costs

## Testing

### Test Pricing Calculation

```bash
# Using curl
curl -X POST http://localhost:8080/api/v1/pricing/calculate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "gpt-4o",
    "input_tokens": 1000,
    "output_tokens": 500
  }'
```

### Test Usage with Pricing

1. Create a new chat after restart
2. Send a few messages
3. Check usage: Profile Icon → User Menu
4. Should now show cost estimates with currency

### Debug Pricing Lookup

```python
# Run in Python shell
from open_webui.models.pricing import Pricings

# Test different model IDs
test_ids = ["gpt-4o", "openai/gpt-4o", "claude-3-5-sonnet-20241022", "deepseek-chat"]

for model_id in test_ids:
    result = Pricings.calculate_cost("", model_id, 1000, 500)
    print(f"{model_id}: ${result['total_cost']:.4f} (available: {result['pricing_available']})")
```

## Updating Pricing

### Via API (Admin)

```http
PATCH /api/v1/pricing/openai%2Fgpt-4o
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "input_cost_per_million": 3.00,
  "output_cost_per_million": 12.00,
  "notes": "Price increase January 2025"
}
```

### Via Code

```python
from open_webui.models.pricing import Pricings, PricingUpdateForm

form = PricingUpdateForm(
    input_cost_per_million=3.00,
    output_cost_per_million=12.00,
    notes="Price increase January 2025"
)

Pricings.update_pricing_by_id("openai/gpt-4o", form)
```

### Via Python Module

Edit `backend/open_webui/utils/pricing_data.py` and add/update the PRICING_DATA dictionary, then run:

```http
POST /api/v1/pricing/initialize
```

## Admin Features

### View All Pricing

Admin Panel → (Coming soon: Pricing Management UI)

Or via API:
```bash
curl http://localhost:8080/api/v1/pricing \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Add New Model Pricing

```bash
curl -X POST http://localhost:8080/api/v1/pricing/upsert \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model_name": "gpt-5",
    "display_name": "GPT-5",
    "input_cost_per_million": 5.00,
    "output_cost_per_million": 20.00,
    "cache_read_cost_per_million": 2.50,
    "cache_write_cost_per_million": 0.0,
    "currency": "USD",
    "source": "official",
    "source_url": "https://openai.com/pricing/"
  }'
```

### Deactivate Model Pricing

```bash
curl -X PATCH http://localhost:8080/api/v1/pricing/openai%2Fgpt-3.5-turbo \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

## Troubleshooting

### Cost Still Showing $0.00

**Check 1: Is pricing initialized?**
```bash
curl http://localhost:8080/api/v1/pricing | jq '. | length'
# Should return > 0
```

If 0, initialize:
```bash
curl -X POST http://localhost:8080/api/v1/pricing/initialize \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Check 2: Does your model have pricing?**
```bash
curl http://localhost:8080/api/v1/pricing/calculate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_id": "YOUR_MODEL_ID", "input_tokens": 1000, "output_tokens": 500}'
```

If `pricing_available: false`, add pricing for your model.

**Check 3: Are you looking at old chats?**
- Pricing only applies to NEW messages after the fix
- Create a new chat to see costs

### Model Not Found in Pricing DB

Add it manually:
```python
from open_webui.models.pricing import Pricings, PricingForm

form = PricingForm(
    provider="your-provider",
    model_name="your-model",
    display_name="Your Model Name",
    input_cost_per_million=1.00,
    output_cost_per_million=2.00,
    currency="USD",
    source="manual"
)

Pricings.upsert_pricing(form)
```

### Pricing Lookup Failing

Check what model ID is being used:
```bash
# Look at a message in debug_usage.py output
python debug_usage.py | grep "Model ID"
```

Then test lookup:
```python
from open_webui.models.pricing import Pricings
result = Pricings.calculate_cost("", "YOUR_MODEL_ID_HERE", 1000, 500)
print(result)
```

## Best Practices

1. **Keep Pricing Updated** - Check provider pricing pages monthly for changes
2. **Use Official Sources** - Always set `source_url` when adding pricing
3. **Document Changes** - Use the `notes` field to track price changes
4. **Test After Updates** - Use `/pricing/calculate` to verify pricing works
5. **Monitor Costs** - Regularly check usage to ensure accurate tracking

## Future Enhancements

- **Auto-Update** - Scheduled scraping of official pricing pages
- **Price History** - Track pricing changes over time
- **Budget Alerts** - Notify when costs exceed thresholds
- **Cost Forecasting** - Predict monthly costs based on usage patterns
- **Multi-Currency** - Support for non-USD currencies
- **Bulk Import** - CSV/JSON import for batch pricing updates

## Related Files

- **Models**: `backend/open_webui/models/pricing.py`
- **Pricing Data**: `backend/open_webui/utils/pricing_data.py`
- **API Routes**: `backend/open_webui/routers/pricing.py`
- **Integration**: `backend/open_webui/main.py` (lines 603-616, 2239-2262)
- **Usage Tracking**: `backend/open_webui/main.py` (lines 2206-2278)

## See Also

- [USAGE_TRACKING_FIX.md](USAGE_TRACKING_FIX.md) - Usage tracking system
- [ADD_AI_MODELS_GUIDE.md](ADD_AI_MODELS_GUIDE.md) - Adding AI models
- [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) - Complete feature guide
