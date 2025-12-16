"""
Pricing Data Utilities

This module provides current pricing data for popular AI models
and utilities for fetching/updating pricing information.
"""

from typing import Dict, List
import logging

log = logging.getLogger(__name__)


# Current pricing data as of January 2025
# Prices are in USD per million tokens
PRICING_DATA = {
    # OpenAI Models
    "openai/gpt-4o": {
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
        "notes": "Latest GPT-4o model with vision capabilities",
    },
    "openai/gpt-4o-mini": {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "input_cost_per_million": 0.150,
        "output_cost_per_million": 0.600,
        "cache_read_cost_per_million": 0.075,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://openai.com/api/pricing/",
        "notes": "Affordable small model",
    },
    "openai/gpt-4-turbo": {
        "provider": "openai",
        "model_name": "gpt-4-turbo",
        "display_name": "GPT-4 Turbo",
        "input_cost_per_million": 10.00,
        "output_cost_per_million": 30.00,
        "cache_read_cost_per_million": 5.00,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://openai.com/api/pricing/",
    },
    "openai/gpt-3.5-turbo": {
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
        "display_name": "GPT-3.5 Turbo",
        "input_cost_per_million": 0.50,
        "output_cost_per_million": 1.50,
        "cache_read_cost_per_million": 0.0,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://openai.com/api/pricing/",
    },
    "openai/o1": {
        "provider": "openai",
        "model_name": "o1",
        "display_name": "o1",
        "input_cost_per_million": 15.00,
        "output_cost_per_million": 60.00,
        "cache_read_cost_per_million": 7.50,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://openai.com/api/pricing/",
        "notes": "Reasoning model",
    },
    "openai/o1-mini": {
        "provider": "openai",
        "model_name": "o1-mini",
        "display_name": "o1-mini",
        "input_cost_per_million": 3.00,
        "output_cost_per_million": 12.00,
        "cache_read_cost_per_million": 1.50,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://openai.com/api/pricing/",
        "notes": "Smaller reasoning model",
    },
    # Anthropic (Claude) Models
    "anthropic/claude-3-5-sonnet-20241022": {
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "display_name": "Claude 3.5 Sonnet",
        "input_cost_per_million": 3.00,
        "output_cost_per_million": 15.00,
        "cache_read_cost_per_million": 0.30,
        "cache_write_cost_per_million": 3.75,
        "currency": "USD",
        "source": "official",
        "source_url": "https://www.anthropic.com/pricing",
        "notes": "Latest Sonnet with prompt caching",
    },
    "anthropic/claude-3-5-haiku-20241022": {
        "provider": "anthropic",
        "model_name": "claude-3-5-haiku-20241022",
        "display_name": "Claude 3.5 Haiku",
        "input_cost_per_million": 0.80,
        "output_cost_per_million": 4.00,
        "cache_read_cost_per_million": 0.08,
        "cache_write_cost_per_million": 1.00,
        "currency": "USD",
        "source": "official",
        "source_url": "https://www.anthropic.com/pricing",
        "notes": "Fast and affordable",
    },
    "anthropic/claude-3-opus-20240229": {
        "provider": "anthropic",
        "model_name": "claude-3-opus-20240229",
        "display_name": "Claude 3 Opus",
        "input_cost_per_million": 15.00,
        "output_cost_per_million": 75.00,
        "cache_read_cost_per_million": 1.50,
        "cache_write_cost_per_million": 18.75,
        "currency": "USD",
        "source": "official",
        "source_url": "https://www.anthropic.com/pricing",
        "notes": "Most capable Claude model",
    },
    # DeepSeek Models
    "deepseek/deepseek-chat": {
        "provider": "deepseek",
        "model_name": "deepseek-chat",
        "display_name": "DeepSeek Chat",
        "input_cost_per_million": 0.14,
        "output_cost_per_million": 0.28,
        "cache_read_cost_per_million": 0.014,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://platform.deepseek.com/api-docs/pricing/",
        "notes": "Very affordable general chat model",
    },
    "deepseek/deepseek-coder": {
        "provider": "deepseek",
        "model_name": "deepseek-coder",
        "display_name": "DeepSeek Coder",
        "input_cost_per_million": 0.14,
        "output_cost_per_million": 0.28,
        "cache_read_cost_per_million": 0.014,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://platform.deepseek.com/api-docs/pricing/",
        "notes": "Code-focused model",
    },
    "deepseek/deepseek-reasoner": {
        "provider": "deepseek",
        "model_name": "deepseek-reasoner",
        "display_name": "DeepSeek Reasoner",
        "input_cost_per_million": 0.55,
        "output_cost_per_million": 2.19,
        "cache_read_cost_per_million": 0.055,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://platform.deepseek.com/api-docs/pricing/",
        "notes": "Reasoning-focused model",
    },
    # Google Gemini Models
    "google/gemini-2.0-flash-exp": {
        "provider": "google",
        "model_name": "gemini-2.0-flash-exp",
        "display_name": "Gemini 2.0 Flash (Experimental)",
        "input_cost_per_million": 0.0,
        "output_cost_per_million": 0.0,
        "cache_read_cost_per_million": 0.0,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://ai.google.dev/pricing",
        "notes": "Free during experimental phase",
    },
    "google/gemini-1.5-pro": {
        "provider": "google",
        "model_name": "gemini-1.5-pro",
        "display_name": "Gemini 1.5 Pro",
        "input_cost_per_million": 1.25,
        "output_cost_per_million": 5.00,
        "cache_read_cost_per_million": 0.3125,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://ai.google.dev/pricing",
        "notes": "Long context window",
    },
    "google/gemini-1.5-flash": {
        "provider": "google",
        "model_name": "gemini-1.5-flash",
        "display_name": "Gemini 1.5 Flash",
        "input_cost_per_million": 0.075,
        "output_cost_per_million": 0.30,
        "cache_read_cost_per_million": 0.01875,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://ai.google.dev/pricing",
        "notes": "Fast and affordable",
    },
    "google/gemini-1.5-flash-8b": {
        "provider": "google",
        "model_name": "gemini-1.5-flash-8b",
        "display_name": "Gemini 1.5 Flash 8B",
        "input_cost_per_million": 0.0375,
        "output_cost_per_million": 0.15,
        "cache_read_cost_per_million": 0.009375,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://ai.google.dev/pricing",
        "notes": "Smallest flash model",
    },
    # Add common model aliases
    "gpt-4o": {
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
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "input_cost_per_million": 0.150,
        "output_cost_per_million": 0.600,
        "cache_read_cost_per_million": 0.075,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://openai.com/api/pricing/",
    },
    "claude-3-5-sonnet-20241022": {
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "display_name": "Claude 3.5 Sonnet",
        "input_cost_per_million": 3.00,
        "output_cost_per_million": 15.00,
        "cache_read_cost_per_million": 0.30,
        "cache_write_cost_per_million": 3.75,
        "currency": "USD",
        "source": "official",
        "source_url": "https://www.anthropic.com/pricing",
    },
    "deepseek-chat": {
        "provider": "deepseek",
        "model_name": "deepseek-chat",
        "display_name": "DeepSeek Chat",
        "input_cost_per_million": 0.14,
        "output_cost_per_million": 0.28,
        "cache_read_cost_per_million": 0.014,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://platform.deepseek.com/api-docs/pricing/",
    },
    "gemini-2.0-flash-exp": {
        "provider": "google",
        "model_name": "gemini-2.0-flash-exp",
        "display_name": "Gemini 2.0 Flash (Experimental)",
        "input_cost_per_million": 0.0,
        "output_cost_per_million": 0.0,
        "cache_read_cost_per_million": 0.0,
        "cache_write_cost_per_million": 0.0,
        "currency": "USD",
        "source": "official",
        "source_url": "https://ai.google.dev/pricing",
        "notes": "Free during experimental phase",
    },
}


def get_all_pricing_data() -> Dict[str, dict]:
    """Get all pricing data"""
    return PRICING_DATA


def get_pricing_for_model(model_id: str) -> dict:
    """
    Get pricing data for a specific model

    Args:
        model_id: Model identifier (e.g., "gpt-4o", "openai/gpt-4o", "claude-3-5-sonnet-20241022")

    Returns:
        dict with pricing data or None if not found
    """
    # Try direct lookup
    if model_id in PRICING_DATA:
        return PRICING_DATA[model_id]

    # Try with common prefixes
    for prefix in ["openai/", "anthropic/", "deepseek/", "google/"]:
        prefixed_id = f"{prefix}{model_id}"
        if prefixed_id in PRICING_DATA:
            return PRICING_DATA[prefixed_id]

    # Try without prefix
    for key, data in PRICING_DATA.items():
        if "/" in key and key.split("/")[1] == model_id:
            return data

    return None


def initialize_pricing_database():
    """
    Initialize the pricing database with current pricing data

    This should be called on first run or when updating pricing data
    """
    from open_webui.models.pricing import Pricings, PricingForm

    log.info("Initializing pricing database...")

    initialized_count = 0
    updated_count = 0
    skipped_count = 0

    for model_id, data in PRICING_DATA.items():
        try:
            form = PricingForm(**data)
            result = Pricings.upsert_pricing(form)

            if result:
                existing = Pricings.get_pricing_by_id(f"{data['provider']}/{data['model_name']}")
                if existing and existing.created_at < existing.last_updated:
                    updated_count += 1
                else:
                    initialized_count += 1
            else:
                skipped_count += 1

        except Exception as e:
            log.error(f"Error initializing pricing for {model_id}: {e}")
            skipped_count += 1

    log.info(
        f"Pricing database initialized: {initialized_count} new, {updated_count} updated, {skipped_count} skipped"
    )

    return {
        "initialized": initialized_count,
        "updated": updated_count,
        "skipped": skipped_count,
    }


def get_providers() -> List[str]:
    """Get list of all providers with pricing data"""
    providers = set()
    for data in PRICING_DATA.values():
        providers.add(data["provider"])
    return sorted(list(providers))


def get_models_by_provider(provider: str) -> List[dict]:
    """Get all models for a specific provider"""
    models = []
    for model_id, data in PRICING_DATA.items():
        if data["provider"] == provider and "/" in model_id:
            models.append(data)
    return models
