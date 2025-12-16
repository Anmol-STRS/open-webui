"""
Model Pricing Database Models

This module handles storage and retrieval of AI model pricing information
for accurate cost tracking and calculation.
"""

import time
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import BigInteger, Column, String, Float, Text, Boolean

from open_webui.internal.db import Base, get_db


####################
# Pricing Models
####################


class Pricing(Base):
    __tablename__ = "pricing"

    id = Column(String, primary_key=True)  # e.g., "openai/gpt-4o", "deepseek/deepseek-chat"
    provider = Column(String)  # e.g., "openai", "anthropic", "deepseek"
    model_name = Column(String)  # e.g., "gpt-4o", "claude-3-5-sonnet"
    display_name = Column(String)  # Human-readable name

    # Pricing per million tokens (input)
    input_cost_per_million = Column(Float, default=0.0)
    # Pricing per million tokens (output)
    output_cost_per_million = Column(Float, default=0.0)
    # Pricing per million tokens (cached/prompt cache)
    cache_read_cost_per_million = Column(Float, default=0.0)
    # Pricing per million tokens (cache write)
    cache_write_cost_per_million = Column(Float, default=0.0)

    currency = Column(String, default="USD")  # Currency code

    # Metadata
    source = Column(String)  # Where pricing data came from (e.g., "official", "manual", "scraped")
    source_url = Column(Text, nullable=True)  # URL to pricing page
    notes = Column(Text, nullable=True)  # Additional notes

    # Status
    is_active = Column(Boolean, default=True)
    last_updated = Column(BigInteger, default=lambda: int(time.time()))
    created_at = Column(BigInteger, default=lambda: int(time.time()))


class PricingModel(BaseModel):
    id: str
    provider: str
    model_name: str
    display_name: str
    input_cost_per_million: float
    output_cost_per_million: float
    cache_read_cost_per_million: float = 0.0
    cache_write_cost_per_million: float = 0.0
    currency: str = "USD"
    source: str = "manual"
    source_url: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    last_updated: int
    created_at: int

    model_config = {"from_attributes": True}


class PricingForm(BaseModel):
    provider: str
    model_name: str
    display_name: str
    input_cost_per_million: float
    output_cost_per_million: float
    cache_read_cost_per_million: float = 0.0
    cache_write_cost_per_million: float = 0.0
    currency: str = "USD"
    source: str = "manual"
    source_url: Optional[str] = None
    notes: Optional[str] = None


class PricingUpdateForm(BaseModel):
    display_name: Optional[str] = None
    input_cost_per_million: Optional[float] = None
    output_cost_per_million: Optional[float] = None
    cache_read_cost_per_million: Optional[float] = None
    cache_write_cost_per_million: Optional[float] = None
    currency: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


####################
# Pricing Table
####################


class PricingTable:
    def insert_new_pricing(self, form_data: PricingForm) -> Optional[PricingModel]:
        """Insert new pricing entry"""
        with get_db() as db:
            pricing_id = f"{form_data.provider}/{form_data.model_name}"

            pricing = Pricing(
                **{
                    "id": pricing_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "last_updated": int(time.time()),
                }
            )

            try:
                result = db.query(Pricing).filter_by(id=pricing_id).first()
                if result:
                    return None
                db.add(pricing)
                db.commit()
                db.refresh(pricing)
                return PricingModel.model_validate(pricing)
            except Exception as e:
                db.rollback()
                print(f"Error inserting pricing: {e}")
                return None

    def get_pricing_by_id(self, pricing_id: str) -> Optional[PricingModel]:
        """Get pricing by ID"""
        with get_db() as db:
            pricing = db.query(Pricing).filter_by(id=pricing_id).first()
            return PricingModel.model_validate(pricing) if pricing else None

    def get_pricing_by_model(self, provider: str, model_name: str) -> Optional[PricingModel]:
        """Get pricing by provider and model name"""
        pricing_id = f"{provider}/{model_name}"
        return self.get_pricing_by_id(pricing_id)

    def get_all_pricing(self, active_only: bool = True) -> list[PricingModel]:
        """Get all pricing entries"""
        with get_db() as db:
            query = db.query(Pricing)
            if active_only:
                query = query.filter_by(is_active=True)
            pricing_list = query.order_by(Pricing.provider, Pricing.model_name).all()
            return [PricingModel.model_validate(p) for p in pricing_list]

    def get_pricing_by_provider(self, provider: str, active_only: bool = True) -> list[PricingModel]:
        """Get all pricing for a provider"""
        with get_db() as db:
            query = db.query(Pricing).filter_by(provider=provider)
            if active_only:
                query = query.filter_by(is_active=True)
            pricing_list = query.order_by(Pricing.model_name).all()
            return [PricingModel.model_validate(p) for p in pricing_list]

    def update_pricing_by_id(
        self, pricing_id: str, form_data: PricingUpdateForm
    ) -> Optional[PricingModel]:
        """Update pricing entry"""
        with get_db() as db:
            try:
                db.query(Pricing).filter_by(id=pricing_id).update(
                    {
                        **form_data.model_dump(exclude_none=True),
                        "last_updated": int(time.time()),
                    }
                )
                db.commit()

                pricing = db.query(Pricing).filter_by(id=pricing_id).first()
                return PricingModel.model_validate(pricing) if pricing else None
            except Exception as e:
                db.rollback()
                print(f"Error updating pricing: {e}")
                return None

    def upsert_pricing(self, form_data: PricingForm) -> Optional[PricingModel]:
        """Insert or update pricing entry"""
        pricing_id = f"{form_data.provider}/{form_data.model_name}"
        existing = self.get_pricing_by_id(pricing_id)

        if existing:
            update_form = PricingUpdateForm(**form_data.model_dump())
            return self.update_pricing_by_id(pricing_id, update_form)
        else:
            return self.insert_new_pricing(form_data)

    def delete_pricing_by_id(self, pricing_id: str) -> bool:
        """Delete pricing entry"""
        with get_db() as db:
            try:
                result = db.query(Pricing).filter_by(id=pricing_id).first()
                if result:
                    db.delete(result)
                    db.commit()
                    return True
                return False
            except Exception as e:
                db.rollback()
                print(f"Error deleting pricing: {e}")
                return False

    def calculate_cost(
        self,
        provider: str,
        model_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> dict:
        """
        Calculate cost for given token usage

        Args:
            provider: Provider name (can be empty, will try to infer)
            model_name: Model name or full model ID
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
            cache_read_tokens: Number of cached tokens read
            cache_write_tokens: Number of tokens written to cache

        Returns:
            dict with:
                - input_cost: float
                - output_cost: float
                - cache_read_cost: float
                - cache_write_cost: float
                - total_cost: float
                - currency: str
                - pricing_available: bool
        """
        # Try to get pricing with various lookup strategies
        pricing = None

        # Strategy 1: Direct lookup with provider and model_name
        if provider:
            pricing = self.get_pricing_by_model(provider, model_name)

        # Strategy 2: Try model_name as full ID (provider/model)
        if not pricing and "/" in model_name:
            pricing = self.get_pricing_by_id(model_name)

        # Strategy 3: Try model_name directly as ID
        if not pricing:
            pricing = self.get_pricing_by_id(model_name)

        # Strategy 4: Try common providers
        if not pricing:
            for common_provider in ["openai", "anthropic", "google", "deepseek"]:
                test_id = f"{common_provider}/{model_name}"
                pricing = self.get_pricing_by_id(test_id)
                if pricing:
                    break

        # Strategy 5: Try to match by model_name alone
        if not pricing:
            all_pricing = self.get_all_pricing(active_only=True)
            for p in all_pricing:
                if p.model_name == model_name or model_name.endswith(p.model_name):
                    pricing = p
                    break

        if not pricing or not pricing.is_active:
            return {
                "input_cost": 0.0,
                "output_cost": 0.0,
                "cache_read_cost": 0.0,
                "cache_write_cost": 0.0,
                "total_cost": 0.0,
                "currency": "USD",
                "pricing_available": False,
            }

        # Calculate costs (pricing is per million tokens)
        input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_million
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing.cache_read_cost_per_million
        cache_write_cost = (cache_write_tokens / 1_000_000) * pricing.cache_write_cost_per_million

        total_cost = input_cost + output_cost + cache_read_cost + cache_write_cost

        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "cache_read_cost": round(cache_read_cost, 6),
            "cache_write_cost": round(cache_write_cost, 6),
            "total_cost": round(total_cost, 6),
            "currency": pricing.currency,
            "pricing_available": True,
        }


# Global instance
Pricings = PricingTable()
