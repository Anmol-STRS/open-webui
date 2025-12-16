"""
Model Registry for Multi-Provider Support

Loads and manages model configurations from YAML, providing the single source
of truth for routing decisions.
"""

import os
import yaml
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pathlib import Path

logger = logging.getLogger(__name__)


class ProviderConfig(BaseModel):
    """Provider configuration"""
    base_url: str
    api_key_env: str
    timeout: int = 60  # default timeout in seconds


class ModelSpec(BaseModel):
    """Model specification with capabilities and metadata"""
    id: str
    provider: str
    supports_tools: bool = False
    supports_vision: bool = False
    supports_json_schema: bool = False
    max_context_tokens: int = 4096
    max_output_tokens: int = 2048
    reliability_tier: int = Field(ge=1, le=3, default=2)  # 3 = most reliable
    cost_tier: int = Field(ge=1, le=3, default=2)  # 1 = cheapest
    speed_tier: int = Field(ge=1, le=3, default=2)  # 3 = fastest
    tags: List[str] = Field(default_factory=list)


class RouteCondition(BaseModel):
    """Condition for route matching"""
    always: Optional[bool] = None
    any: Optional[List[Dict[str, Any]]] = None
    all: Optional[List[Dict[str, Any]]] = None


class RouteSpec(BaseModel):
    """Route specification"""
    name: str
    when: RouteCondition
    use_model: str
    fallback_models: List[str] = Field(default_factory=list)
    timeout_ms: int = 30000


class ModelRegistryConfig(BaseModel):
    """Complete model registry configuration"""
    providers: Dict[str, ProviderConfig]
    models: List[ModelSpec]
    routes: List[RouteSpec]


class ModelRegistry:
    """
    Model registry singleton that loads configuration and provides
    model lookup and capability checking.
    """

    _instance: Optional['ModelRegistry'] = None

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the model registry"""
        self.config: Optional[ModelRegistryConfig] = None
        self.models_by_id: Dict[str, ModelSpec] = {}
        self.models_by_provider: Dict[str, List[ModelSpec]] = {}

        if config_path:
            self.load_config(config_path)

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> 'ModelRegistry':
        """Get or create singleton instance"""
        if cls._instance is None:
            # Default config path
            if config_path is None:
                config_path = os.getenv(
                    'MODEL_REGISTRY_CONFIG',
                    'backend/open_webui/config/model_registry.yaml'
                )
            cls._instance = cls(config_path)
        return cls._instance

    def load_config(self, config_path: str) -> None:
        """Load configuration from YAML file"""
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Model registry config not found at {config_path}, using defaults")
                self._load_defaults()
                return

            with open(path, 'r') as f:
                config_data = yaml.safe_load(f)

            self.config = ModelRegistryConfig(**config_data)

            # Build lookup tables
            self.models_by_id = {model.id: model for model in self.config.models}
            self.models_by_provider = {}
            for model in self.config.models:
                if model.provider not in self.models_by_provider:
                    self.models_by_provider[model.provider] = []
                self.models_by_provider[model.provider].append(model)

            logger.info(f"Loaded {len(self.config.models)} models from {len(self.config.providers)} providers")

        except Exception as e:
            logger.error(f"Failed to load model registry config: {e}")
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load minimal default configuration"""
        self.config = ModelRegistryConfig(
            providers={
                "openai": ProviderConfig(
                    base_url="https://api.openai.com/v1",
                    api_key_env="OPENAI_API_KEY"
                )
            },
            models=[
                ModelSpec(
                    id="gpt-4",
                    provider="openai",
                    supports_tools=True,
                    supports_vision=True,
                    supports_json_schema=True,
                    max_context_tokens=128000,
                    max_output_tokens=4096,
                    reliability_tier=3,
                    cost_tier=3,
                    speed_tier=2,
                    tags=["general", "reliable"]
                )
            ],
            routes=[
                RouteSpec(
                    name="default",
                    when=RouteCondition(always=True),
                    use_model="gpt-4",
                    fallback_models=[],
                    timeout_ms=30000
                )
            ]
        )
        self.models_by_id = {model.id: model for model in self.config.models}
        self.models_by_provider = {"openai": self.config.models}

    def get_model(self, model_id: str) -> Optional[ModelSpec]:
        """Get model by ID"""
        return self.models_by_id.get(model_id)

    def get_provider_config(self, provider: str) -> Optional[ProviderConfig]:
        """Get provider configuration"""
        if not self.config:
            return None
        return self.config.providers.get(provider)

    def get_models_by_provider(self, provider: str) -> List[ModelSpec]:
        """Get all models for a provider"""
        return self.models_by_provider.get(provider, [])

    def get_models_by_tag(self, tag: str) -> List[ModelSpec]:
        """Get all models with a specific tag"""
        return [model for model in self.config.models if tag in model.tags]

    def get_models_by_capability(
        self,
        supports_tools: Optional[bool] = None,
        supports_vision: Optional[bool] = None,
        supports_json_schema: Optional[bool] = None,
        min_context_tokens: Optional[int] = None
    ) -> List[ModelSpec]:
        """Get models matching capability requirements"""
        results = []
        for model in self.config.models:
            if supports_tools is not None and model.supports_tools != supports_tools:
                continue
            if supports_vision is not None and model.supports_vision != supports_vision:
                continue
            if supports_json_schema is not None and model.supports_json_schema != supports_json_schema:
                continue
            if min_context_tokens is not None and model.max_context_tokens < min_context_tokens:
                continue
            results.append(model)
        return results

    def get_routes(self) -> List[RouteSpec]:
        """Get all route specifications"""
        if not self.config:
            return []
        return self.config.routes

    def validate_model_exists(self, model_id: str) -> bool:
        """Check if model exists in registry"""
        return model_id in self.models_by_id

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for provider.

        For OpenAI, gets from Open WebUI settings (openai.api_keys).
        For other providers, falls back to environment variable.
        """
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            return None

        # Special handling for OpenAI - use Open WebUI settings
        if provider.lower() == 'openai':
            try:
                from open_webui.config import OPENAI_API_KEYS
                if OPENAI_API_KEYS and len(OPENAI_API_KEYS) > 0:
                    return OPENAI_API_KEYS[0]  # Use first configured key
            except Exception as e:
                logger.warning(f"Failed to get OpenAI API key from settings: {e}")

        # For DeepSeek and other providers, check environment variable
        return os.getenv(provider_config.api_key_env)

    def get_base_url(self, provider: str) -> Optional[str]:
        """
        Get base URL for provider.

        For OpenAI, gets from Open WebUI settings (openai.api_base_urls).
        For other providers, uses config file.
        """
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            return None

        # Special handling for OpenAI - use Open WebUI settings
        if provider.lower() == 'openai':
            try:
                from open_webui.config import OPENAI_API_BASE_URLS
                if OPENAI_API_BASE_URLS and len(OPENAI_API_BASE_URLS) > 0:
                    return OPENAI_API_BASE_URLS[0]  # Use first configured URL
            except Exception as e:
                logger.warning(f"Failed to get OpenAI base URL from settings: {e}")

        # For other providers, use configured base_url
        return provider_config.base_url


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get or create the global model registry instance"""
    global _registry
    if _registry is None:
        _registry = ModelRegistry.get_instance()
    return _registry


def reload_model_registry(config_path: Optional[str] = None) -> ModelRegistry:
    """Reload the model registry from config"""
    global _registry
    _registry = ModelRegistry(config_path)
    return _registry
