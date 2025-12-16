"""
Model router with intelligent routing and capability matching

Routes requests to the best model based on:
- Content analysis (code blocks, long context, etc.)
- Required capabilities (tools, vision, JSON schema)
- Model specifications (reliability, cost, speed tiers)
"""

import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel

from open_webui.services.model_registry import (
    get_model_registry,
    ModelSpec,
    RouteSpec
)

logger = logging.getLogger(__name__)


class RoutingContext(BaseModel):
    """Context information for routing decisions"""
    last_user_message: str
    messages: List[Dict[str, Any]]
    has_code_block: bool = False
    has_attachments: bool = False
    rag_enabled: bool = False
    estimated_context_tokens: int = 0
    tools_enabled: bool = False
    response_format_required: Optional[str] = None  # "json_schema" or None


class RoutingDecision(BaseModel):
    """Router decision output"""
    primary_model_id: str
    fallback_model_ids: List[str]
    route_name: str
    route_reason: str
    timeout_ms: int


class ModelRouter:
    """
    Model router that selects the best model for each request
    based on content analysis and capability requirements.
    """

    def __init__(self):
        self.registry = get_model_registry()

    def route(self, context: RoutingContext, user_model_override: Optional[str] = None) -> RoutingDecision:
        """
        Route a request to the best model.

        Args:
            context: Routing context with request information
            user_model_override: If provided, user explicitly selected a model

        Returns:
            RoutingDecision with primary and fallback models
        """
        # If user explicitly selected a model, honor it
        if user_model_override:
            model = self.registry.get_model(user_model_override)
            if model:
                # Validate capabilities if strict requirements
                if self._validate_capabilities(model, context):
                    fallbacks = self._get_fallback_models(model, context)
                    return RoutingDecision(
                        primary_model_id=user_model_override,
                        fallback_model_ids=fallbacks,
                        route_name="user_override",
                        route_reason=f"User selected {user_model_override}",
                        timeout_ms=60000
                    )
                else:
                    logger.warning(
                        f"User selected model {user_model_override} doesn't meet capability requirements, "
                        f"falling back to router"
                    )

        # Try matching against configured routes
        for route in self.registry.get_routes():
            if self._matches_route(route, context):
                primary_model = self.registry.get_model(route.use_model)
                if primary_model and self._validate_capabilities(primary_model, context):
                    fallbacks = self._resolve_fallback_chain(
                        route.fallback_models,
                        context
                    )
                    return RoutingDecision(
                        primary_model_id=route.use_model,
                        fallback_model_ids=fallbacks,
                        route_name=route.name,
                        route_reason=self._build_route_reason(route, context),
                        timeout_ms=route.timeout_ms
                    )

        # Fallback to default best model
        return self._get_default_route(context)

    def _matches_route(self, route: RouteSpec, context: RoutingContext) -> bool:
        """Check if context matches a route's conditions"""
        condition = route.when

        # Always matches
        if condition.always:
            return True

        # Check 'any' conditions (OR)
        if condition.any:
            return any(self._evaluate_condition(cond, context) for cond in condition.any)

        # Check 'all' conditions (AND)
        if condition.all:
            return all(self._evaluate_condition(cond, context) for cond in condition.all)

        return False

    def _evaluate_condition(self, condition: Dict[str, Any], context: RoutingContext) -> bool:
        """Evaluate a single condition against context"""
        if "has_code_block" in condition:
            return context.has_code_block == condition["has_code_block"]

        if "has_attachments" in condition:
            return context.has_attachments == condition["has_attachments"]

        if "rag_enabled" in condition:
            return context.rag_enabled == condition["rag_enabled"]

        if "tools_enabled" in condition:
            return context.tools_enabled == condition["tools_enabled"]

        if "response_format_required" in condition:
            return context.response_format_required == condition["response_format_required"]

        if "context_est_tokens_gt" in condition:
            return context.estimated_context_tokens > condition["context_est_tokens_gt"]

        if "contains_regex" in condition:
            pattern = condition["contains_regex"]
            try:
                return bool(re.search(pattern, context.last_user_message, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")
                return False

        return False

    def _validate_capabilities(self, model: ModelSpec, context: RoutingContext) -> bool:
        """Validate that model meets capability requirements"""
        if context.tools_enabled and not model.supports_tools:
            return False

        if context.response_format_required == "json_schema" and not model.supports_json_schema:
            return False

        # Vision check would require analyzing attachments (future enhancement)
        # if context.has_vision_attachments and not model.supports_vision:
        #     return False

        if context.estimated_context_tokens > model.max_context_tokens:
            return False

        return True

    def _resolve_fallback_chain(
        self,
        fallback_model_ids: List[str],
        context: RoutingContext
    ) -> List[str]:
        """Resolve and filter fallback models by capabilities"""
        valid_fallbacks = []
        for model_id in fallback_model_ids:
            model = self.registry.get_model(model_id)
            if model and self._validate_capabilities(model, context):
                valid_fallbacks.append(model_id)
        return valid_fallbacks

    def _get_fallback_models(
        self,
        primary_model: ModelSpec,
        context: RoutingContext
    ) -> List[str]:
        """Get smart fallback models when not explicitly configured"""
        # Get all models that meet capability requirements
        candidates = [
            model for model in self.registry.config.models
            if model.id != primary_model.id and self._validate_capabilities(model, context)
        ]

        # Sort by reliability, then speed, then cost
        candidates.sort(
            key=lambda m: (-m.reliability_tier, -m.speed_tier, m.cost_tier)
        )

        # Return top 3 as fallbacks
        return [model.id for model in candidates[:3]]

    def _get_default_route(self, context: RoutingContext) -> RoutingDecision:
        """Get default routing when no route matches"""
        # Find models that meet capability requirements
        candidates = [
            model for model in self.registry.config.models
            if self._validate_capabilities(model, context)
        ]

        if not candidates:
            # No models meet requirements - return first available
            logger.warning("No models meet capability requirements, using first available")
            first_model = self.registry.config.models[0]
            return RoutingDecision(
                primary_model_id=first_model.id,
                fallback_model_ids=[],
                route_name="fallback_no_match",
                route_reason="No models meet all requirements",
                timeout_ms=30000
            )

        # For default, prefer fast + cheap models
        candidates.sort(
            key=lambda m: (-m.speed_tier, m.cost_tier, -m.reliability_tier)
        )

        primary = candidates[0]
        fallbacks = [m.id for m in candidates[1:4]]

        return RoutingDecision(
            primary_model_id=primary.id,
            fallback_model_ids=fallbacks,
            route_name="default",
            route_reason="Default routing: fast and cost-effective",
            timeout_ms=30000
        )

    def _build_route_reason(self, route: RouteSpec, context: RoutingContext) -> str:
        """Build human-readable reason for route selection"""
        reasons = []

        if context.has_code_block:
            reasons.append("code blocks detected")
        if context.rag_enabled:
            reasons.append("RAG enabled")
        if context.tools_enabled:
            reasons.append("tools required")
        if context.response_format_required:
            reasons.append(f"{context.response_format_required} format required")
        if context.estimated_context_tokens > 12000:
            reasons.append(f"long context ({context.estimated_context_tokens} tokens)")

        if reasons:
            return f"Route '{route.name}': {', '.join(reasons)}"
        else:
            return f"Route '{route.name}' matched"

    @staticmethod
    def analyze_message_content(
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> RoutingContext:
        """
        Analyze message content to build routing context.

        Args:
            messages: List of chat messages
            tools: Optional tool definitions
            response_format: Optional response format specification

        Returns:
            RoutingContext with analyzed information
        """
        if not messages:
            return RoutingContext(
                last_user_message="",
                messages=[]
            )

        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        # Detect code blocks
        has_code_block = bool(re.search(r'```[\w]*\n', last_user_message))

        # Estimate context tokens (rough approximation: 4 chars = 1 token)
        total_content = " ".join(msg.get("content", "") for msg in messages if isinstance(msg.get("content"), str))
        estimated_tokens = len(total_content) // 4

        # Check for attachments (images, files)
        has_attachments = any(
            isinstance(msg.get("content"), list) for msg in messages
        )

        # Tools enabled
        tools_enabled = tools is not None and len(tools) > 0

        # Response format
        response_format_required = None
        if response_format:
            if response_format.get("type") == "json_schema":
                response_format_required = "json_schema"
            elif response_format.get("type") == "json_object":
                response_format_required = "json_object"

        return RoutingContext(
            last_user_message=last_user_message,
            messages=messages,
            has_code_block=has_code_block,
            has_attachments=has_attachments,
            rag_enabled=False,  # Will be set externally based on RAG system
            estimated_context_tokens=estimated_tokens,
            tools_enabled=tools_enabled,
            response_format_required=response_format_required
        )


# Global router instance
_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get or create the global router instance"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
