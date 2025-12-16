"""
Pricing Management API Routes

This module provides endpoints for managing model pricing data.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from open_webui.models.pricing import (
    Pricings,
    PricingForm,
    PricingModel,
    PricingUpdateForm,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.pricing_data import (
    initialize_pricing_database,
    get_all_pricing_data,
    get_providers,
)

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Pricing Endpoints
############################


@router.get("/", response_model=list[PricingModel])
async def get_all_pricing(
    active_only: bool = True,
    user=Depends(get_verified_user),
):
    """
    Get all pricing entries

    Args:
        active_only: Only return active pricing (default: True)
    """
    return Pricings.get_all_pricing(active_only=active_only)


@router.get("/providers", response_model=list[str])
async def get_pricing_providers(user=Depends(get_verified_user)):
    """Get list of all providers with pricing data"""
    return get_providers()


@router.get("/provider/{provider}", response_model=list[PricingModel])
async def get_pricing_by_provider(
    provider: str,
    active_only: bool = True,
    user=Depends(get_verified_user),
):
    """
    Get all pricing for a specific provider

    Args:
        provider: Provider name (e.g., "openai", "anthropic")
        active_only: Only return active pricing (default: True)
    """
    return Pricings.get_pricing_by_provider(provider, active_only=active_only)


@router.get("/{pricing_id}", response_model=PricingModel)
async def get_pricing(
    pricing_id: str,
    user=Depends(get_verified_user),
):
    """
    Get pricing by ID

    Args:
        pricing_id: Pricing ID (e.g., "openai/gpt-4o")
    """
    pricing = Pricings.get_pricing_by_id(pricing_id)
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found",
        )
    return pricing


class CalculateCostRequest(BaseModel):
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@router.post("/calculate")
async def calculate_cost(
    request: CalculateCostRequest,
    user=Depends(get_verified_user),
):
    """
    Calculate cost for given token usage

    Args:
        model_id: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_read_tokens: Number of cached tokens read
        cache_write_tokens: Number of tokens written to cache
    """
    result = Pricings.calculate_cost(
        provider="",
        model_name=request.model_id,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
        cache_read_tokens=request.cache_read_tokens,
        cache_write_tokens=request.cache_write_tokens,
    )
    return result


@router.post("/", response_model=PricingModel)
async def create_pricing(
    form_data: PricingForm,
    user=Depends(get_admin_user),
):
    """
    Create new pricing entry (Admin only)

    Args:
        form_data: Pricing data
    """
    pricing = Pricings.insert_new_pricing(form_data)
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pricing already exists or failed to create",
        )
    return pricing


@router.post("/upsert", response_model=PricingModel)
async def upsert_pricing(
    form_data: PricingForm,
    user=Depends(get_admin_user),
):
    """
    Create or update pricing entry (Admin only)

    Args:
        form_data: Pricing data
    """
    pricing = Pricings.upsert_pricing(form_data)
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create or update pricing",
        )
    return pricing


@router.patch("/{pricing_id}", response_model=PricingModel)
async def update_pricing(
    pricing_id: str,
    form_data: PricingUpdateForm,
    user=Depends(get_admin_user),
):
    """
    Update pricing entry (Admin only)

    Args:
        pricing_id: Pricing ID
        form_data: Updated pricing data
    """
    pricing = Pricings.update_pricing_by_id(pricing_id, form_data)
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found or failed to update",
        )
    return pricing


@router.delete("/{pricing_id}")
async def delete_pricing(
    pricing_id: str,
    user=Depends(get_admin_user),
):
    """
    Delete pricing entry (Admin only)

    Args:
        pricing_id: Pricing ID
    """
    success = Pricings.delete_pricing_by_id(pricing_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found or failed to delete",
        )
    return {"success": True}


@router.post("/initialize")
async def initialize_pricing(
    user=Depends(get_admin_user),
):
    """
    Initialize pricing database with current pricing data (Admin only)

    This loads all known pricing data into the database.
    """
    try:
        result = initialize_pricing_database()
        return {
            "success": True,
            "message": "Pricing database initialized",
            **result,
        }
    except Exception as e:
        log.error(f"Error initializing pricing database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize pricing database",
        )


@router.get("/data/builtin")
async def get_builtin_pricing_data(
    user=Depends(get_admin_user),
):
    """
    Get built-in pricing data (Admin only)

    Returns all pricing data from the pricing_data module.
    """
    return {"pricing_data": get_all_pricing_data()}
