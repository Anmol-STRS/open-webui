"""
Provider adapters for multi-provider support

Normalizes requests/responses into a common internal format.
Ensures only supported fields are sent to each provider.
"""

import asyncio
import httpx
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator, Union
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProviderRequest(BaseModel):
    """Normalized request format"""
    model: str
    messages: list
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    tools: Optional[list] = None
    tool_choice: Optional[Union[str, dict]] = None
    response_format: Optional[dict] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None  # Internal metadata, not sent to provider


class ProviderResponse(BaseModel):
    """Normalized response format"""
    content: Optional[str] = None
    tool_calls: Optional[list] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Dict[str, Any]] = None


class ProviderError(Exception):
    """Provider-specific error"""
    def __init__(self, message: str, status_code: Optional[int] = None, error_type: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type or "unknown"


class ProviderAdapter(ABC):
    """Base class for provider adapters"""

    def __init__(self, base_url: str, api_key: str, timeout: int = 60):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    @abstractmethod
    def prepare_request(self, request: ProviderRequest) -> Dict[str, Any]:
        """
        Convert normalized request to provider-specific format.
        Must only include fields supported by the provider.
        """
        pass

    @abstractmethod
    def parse_response(self, response: Dict[str, Any]) -> ProviderResponse:
        """Convert provider response to normalized format"""
        pass

    @abstractmethod
    def parse_stream_chunk(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Parse a streaming chunk and return content delta"""
        pass

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute non-streaming completion"""
        try:
            prepared_request = self.prepare_request(request)
            headers = self.get_headers()

            start_time = time.time()
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=prepared_request,
                headers=headers
            )
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('error', {}).get('message', response.text)
                raise ProviderError(
                    message=error_message,
                    status_code=response.status_code,
                    error_type=self._categorize_error(response.status_code)
                )

            response_data = response.json()
            provider_response = self.parse_response(response_data)
            provider_response.raw_response = {"latency_ms": latency_ms}

            return provider_response

        except httpx.TimeoutException as e:
            raise ProviderError(
                message=f"Request timeout after {self.timeout}s",
                status_code=408,
                error_type="timeout"
            )
        except httpx.HTTPError as e:
            raise ProviderError(
                message=str(e),
                status_code=500,
                error_type="network"
            )
        except Exception as e:
            logger.exception(f"Provider adapter error: {e}")
            raise ProviderError(
                message=str(e),
                status_code=500,
                error_type="unknown"
            )

    async def stream_complete(self, request: ProviderRequest) -> AsyncIterator[str]:
        """Execute streaming completion"""
        try:
            prepared_request = self.prepare_request(request)
            prepared_request['stream'] = True
            headers = self.get_headers()

            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=prepared_request,
                headers=headers
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise ProviderError(
                        message=error_text.decode(),
                        status_code=response.status_code,
                        error_type=self._categorize_error(response.status_code)
                    )

                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() == '[DONE]':
                            break

                        try:
                            import json
                            chunk = json.loads(data_str)
                            content = self.parse_stream_chunk(chunk)
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            raise ProviderError(
                message=f"Stream timeout after {self.timeout}s",
                status_code=408,
                error_type="timeout"
            )
        except httpx.HTTPError as e:
            raise ProviderError(
                message=str(e),
                status_code=500,
                error_type="network"
            )

    def _categorize_error(self, status_code: int) -> str:
        """Categorize error by status code"""
        if status_code == 400:
            return "invalid_request"
        elif status_code == 401:
            return "authentication"
        elif status_code == 403:
            return "permission"
        elif status_code == 404:
            return "not_found"
        elif status_code == 408:
            return "timeout"
        elif status_code == 429:
            return "rate_limit"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown"

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class OpenAIAdapter(ProviderAdapter):
    """OpenAI API adapter"""

    def prepare_request(self, request: ProviderRequest) -> Dict[str, Any]:
        """Prepare OpenAI-compatible request"""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "stream": request.stream
        }

        # Add optional parameters only if set
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.response_format:
            payload["response_format"] = request.response_format

        return payload

    def parse_response(self, response: Dict[str, Any]) -> ProviderResponse:
        """Parse OpenAI response"""
        choice = response.get('choices', [{}])[0]
        message = choice.get('message', {})

        return ProviderResponse(
            content=message.get('content'),
            tool_calls=message.get('tool_calls'),
            finish_reason=choice.get('finish_reason'),
            usage=response.get('usage'),
            raw_response=response
        )

    def parse_stream_chunk(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Parse OpenAI streaming chunk"""
        choices = chunk.get('choices', [])
        if not choices:
            return None

        delta = choices[0].get('delta', {})
        return delta.get('content')


class DeepSeekAdapter(ProviderAdapter):
    """DeepSeek API adapter (OpenAI-compatible)"""

    def prepare_request(self, request: ProviderRequest) -> Dict[str, Any]:
        """Prepare DeepSeek request (OpenAI-compatible)"""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "stream": request.stream
        }

        # DeepSeek supports most OpenAI parameters
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty

        # Tool support (if model supports it)
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice

        # JSON schema support
        if request.response_format:
            payload["response_format"] = request.response_format

        return payload

    def parse_response(self, response: Dict[str, Any]) -> ProviderResponse:
        """Parse DeepSeek response (OpenAI-compatible)"""
        choice = response.get('choices', [{}])[0]
        message = choice.get('message', {})

        return ProviderResponse(
            content=message.get('content'),
            tool_calls=message.get('tool_calls'),
            finish_reason=choice.get('finish_reason'),
            usage=response.get('usage'),
            raw_response=response
        )

    def parse_stream_chunk(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Parse DeepSeek streaming chunk"""
        choices = chunk.get('choices', [])
        if not choices:
            return None

        delta = choices[0].get('delta', {})
        return delta.get('content')


class AdapterFactory:
    """Factory for creating provider adapters"""

    _adapters = {
        "openai": OpenAIAdapter,
        "deepseek": DeepSeekAdapter,
    }

    @classmethod
    def create(cls, provider: str, base_url: str, api_key: str, timeout: int = 60) -> ProviderAdapter:
        """Create a provider adapter"""
        adapter_class = cls._adapters.get(provider.lower())
        if not adapter_class:
            # Default to OpenAI-compatible adapter for unknown providers
            logger.warning(f"Unknown provider {provider}, using OpenAI-compatible adapter")
            adapter_class = OpenAIAdapter

        return adapter_class(base_url, api_key, timeout)

    @classmethod
    def register_adapter(cls, provider: str, adapter_class: type):
        """Register a custom adapter"""
        cls._adapters[provider.lower()] = adapter_class
