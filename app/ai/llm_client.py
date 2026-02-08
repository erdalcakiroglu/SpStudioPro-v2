"""
Unified LLM Client - Multi-provider support with active provider selection

Bu modül birden fazla LLM provider'ı destekler:
- Ollama (local)
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- DeepSeek
- Azure OpenAI

Aktif provider settings'den otomatik olarak alınır.
"""

import json
import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger('ai.llm_client')


class LLMProviderType(Enum):
    """Desteklenen LLM provider türleri"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    DEEPSEEK = "deepseek"


@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider_type: LLMProviderType
    provider_id: str
    name: str
    model: str
    host: str = ""
    api_key: str = ""
    endpoint: str = ""
    deployment: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 120
    
    @classmethod
    def from_dict(cls, provider_id: str, config: Dict[str, Any]) -> 'LLMConfig':
        """Dict'ten LLMConfig oluştur"""
        provider_type = LLMProviderType(config.get("type", "ollama"))
        return cls(
            provider_type=provider_type,
            provider_id=provider_id,
            name=config.get("name", provider_id),
            model=config.get("model", "codellama"),
            host=config.get("host", "http://localhost:11434"),
            api_key=config.get("api_key", ""),
            endpoint=config.get("endpoint", ""),
            deployment=config.get("deployment", ""),
            temperature=config.get("temperature", 0.1),
            max_tokens=config.get("max_tokens", 4096),
            timeout=config.get("timeout", 120),
        )


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate response from LLM"""
        pass

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> str:
        """
        Streaming üretim için varsayılan fallback.
        Provider özel streaming yoksa standart generate çağrılır.
        """
        response = await self.generate(prompt=prompt, system_prompt=system_prompt, **kwargs)
        self._emit_stream_chunk(on_chunk, response)
        return response
    
    @abstractmethod
    async def check_connection(self) -> bool:
        """Check if provider is available"""
        pass
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def model(self) -> str:
        return self.config.model

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        """Safely convert usage values to int."""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _estimate_tokens(text: Optional[str]) -> int:
        """Rough token estimate when provider does not return usage."""
        if not text:
            return 0
        # Practical heuristic for mixed SQL + natural language payloads.
        return max(1, int(len(text) / 3.8))

    @staticmethod
    def _emit_stream_chunk(on_chunk: Optional[Callable[[str], None]], chunk: str) -> None:
        """Safely forward stream chunk to callback."""
        if not on_chunk or not chunk:
            return
        try:
            on_chunk(chunk)
        except Exception:
            pass

    async def _stream_openai_compatible(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Parse SSE stream from OpenAI-compatible chat/completions APIs.
        Returns (full_text, usage_dict).
        """
        chunks: List[str] = []
        usage: Dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_line = line[5:].strip()
                    if not data_line:
                        continue
                    if data_line == "[DONE]":
                        break

                    try:
                        event = json.loads(data_line)
                    except Exception:
                        continue

                    event_usage = event.get("usage")
                    if isinstance(event_usage, dict) and event_usage:
                        usage = event_usage

                    choices = event.get("choices")
                    if not isinstance(choices, list) or not choices:
                        continue
                    choice0 = choices[0] if isinstance(choices[0], dict) else {}
                    delta = choice0.get("delta")
                    piece = ""
                    if isinstance(delta, dict):
                        piece = delta.get("content") or ""
                    if not piece:
                        msg = choice0.get("message")
                        if isinstance(msg, dict):
                            piece = msg.get("content") or ""
                    if piece:
                        chunks.append(piece)
                        self._emit_stream_chunk(on_chunk, piece)

        return "".join(chunks), usage

    def _log_token_usage(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_text: str,
        usage: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log sent/received token counts in a unified format."""
        usage = usage if isinstance(usage, dict) else {}

        prompt_tokens = (
            self._to_int(usage.get("prompt_tokens"))
            or self._to_int(usage.get("input_tokens"))
            or self._to_int(usage.get("prompt_eval_count"))
        )
        completion_tokens = (
            self._to_int(usage.get("completion_tokens"))
            or self._to_int(usage.get("output_tokens"))
            or self._to_int(usage.get("eval_count"))
        )
        total_tokens = self._to_int(usage.get("total_tokens"))

        if prompt_tokens is None:
            prompt_tokens = self._estimate_tokens(prompt) + self._estimate_tokens(system_prompt)
        if completion_tokens is None:
            completion_tokens = self._estimate_tokens(response_text)
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens

        source = "api" if usage else "estimated"
        logger.info(
            f"Token usage | provider={self.name} | model={self.model} | "
            f"sent={prompt_tokens:,} | received={completion_tokens:,} | total={total_tokens:,} | source={source}"
        )


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider"""
    
    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.config.host}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Mevcut modelleri listele"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.config.host}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m['name'] for m in data.get('models', [])]
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
        return []
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        url = f"{self.config.host}/api/generate"
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": kwargs.get("top_p", 0.9),
                "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "")
                self._log_token_usage(prompt, system_prompt, text, usage=data)
                return text
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        url = f"{self.config.host}/api/generate"
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": kwargs.get("top_p", 0.9),
                "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        chunks: List[str] = []
        usage: Dict[str, Any] = {}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                        except Exception:
                            continue
                        piece = event.get("response") or ""
                        if piece:
                            chunks.append(piece)
                            self._emit_stream_chunk(on_chunk, piece)
                        if event.get("done") and isinstance(event, dict):
                            usage = event
            text = "".join(chunks)
            self._log_token_usage(prompt, system_prompt, text, usage=usage)
            return text
        except Exception as e:
            logger.error(f"Ollama streaming generation failed: {e}")
            raise


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider (GPT-4, GPT-3.5)"""
    
    BASE_URL = "https://api.openai.com/v1"
    
    async def check_connection(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenAI connection check failed: {e}")
            return False
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                self._log_token_usage(prompt, system_prompt, text, usage=data.get("usage"))
                return text
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            text, usage = await self._stream_openai_compatible(
                url=f"{self.BASE_URL}/chat/completions",
                headers=headers,
                payload=payload,
                on_chunk=on_chunk,
            )
            self._log_token_usage(prompt, system_prompt, text, usage=usage)
            return text
        except Exception as e:
            logger.error(f"OpenAI streaming generation failed: {e}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider"""
    
    BASE_URL = "https://api.anthropic.com/v1"
    
    async def check_connection(self) -> bool:
        if not self.config.api_key:
            return False
        # Anthropic doesn't have a simple health check endpoint
        # We'll just verify the API key format
        return len(self.config.api_key) > 10
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature or self.config.temperature,
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/messages",
                    headers={
                        "x-api-key": self.config.api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                text = data["content"][0]["text"]
                self._log_token_usage(prompt, system_prompt, text, usage=data.get("usage"))
                return text
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> str:
        # Keep safe fallback for Anthropic until native SSE parser is introduced.
        logger.info("Anthropic streaming fallback: using non-stream generate.")
        return await super().generate_streaming(
            prompt=prompt,
            system_prompt=system_prompt,
            on_chunk=on_chunk,
            **kwargs,
        )


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider"""
    
    BASE_URL = "https://api.deepseek.com/v1"
    
    async def check_connection(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"DeepSeek connection check failed: {e}")
            return False
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                self._log_token_usage(prompt, system_prompt, text, usage=data.get("usage"))
                return text
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {e}")
            raise

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            text, usage = await self._stream_openai_compatible(
                url=f"{self.BASE_URL}/chat/completions",
                headers=headers,
                payload=payload,
                on_chunk=on_chunk,
            )
            self._log_token_usage(prompt, system_prompt, text, usage=usage)
            return text
        except Exception as e:
            logger.error(f"DeepSeek streaming generation failed: {e}")
            raise


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI API provider"""
    
    async def check_connection(self) -> bool:
        if not self.config.api_key or not self.config.endpoint:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.config.endpoint}/openai/deployments?api-version=2024-02-01"
                response = await client.get(
                    url,
                    headers={"api-key": self.config.api_key}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Azure OpenAI connection check failed: {e}")
            return False
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        deployment = self.config.deployment or self.config.model
        url = f"{self.config.endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-01"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    url,
                    headers={
                        "api-key": self.config.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                self._log_token_usage(prompt, system_prompt, text, usage=data.get("usage"))
                return text
        except Exception as e:
            logger.error(f"Azure OpenAI generation failed: {e}")
            raise

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        deployment = self.config.deployment or self.config.model
        url = f"{self.config.endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-01"
        headers = {
            "api-key": self.config.api_key,
            "Content-Type": "application/json",
        }
        try:
            text, usage = await self._stream_openai_compatible(
                url=url,
                headers=headers,
                payload=payload,
                on_chunk=on_chunk,
            )
            self._log_token_usage(prompt, system_prompt, text, usage=usage)
            return text
        except Exception as e:
            logger.error(f"Azure OpenAI streaming generation failed: {e}")
            raise


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED LLM CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedLLMClient:
    """
    Unified LLM Client - Aktif provider'ı otomatik kullanır
    
    Usage:
        client = UnifiedLLMClient()
        response = await client.generate(prompt, system_prompt)
        
        # Veya belirli bir provider ile:
        response = await client.generate(prompt, provider_id="my_openai")
    """
    
    _instance: Optional['UnifiedLLMClient'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._initialized = True
        self._load_providers()
    
    def _load_providers(self) -> None:
        """Settings'den provider'ları yükle"""
        settings = get_settings()
        self._providers.clear()
        
        if settings.ai.providers:
            for provider_id, config_dict in settings.ai.providers.items():
                try:
                    config = LLMConfig.from_dict(provider_id, config_dict)
                    provider = self._create_provider(config)
                    self._providers[provider_id] = provider
                    logger.info(f"Loaded provider: {provider_id} ({config.provider_type.value})")
                except Exception as e:
                    logger.error(f"Failed to load provider {provider_id}: {e}")
        
        # Default Ollama provider yoksa oluştur
        if not self._providers:
            default_config = LLMConfig(
                provider_type=LLMProviderType.OLLAMA,
                provider_id="default_ollama",
                name="Default Ollama",
                model=settings.ai.model,
                host=settings.ai.ollama_host,
                temperature=settings.ai.temperature,
                max_tokens=settings.ai.max_tokens,
                timeout=settings.ai.timeout,
            )
            self._providers["default_ollama"] = OllamaProvider(default_config)
            logger.info("Created default Ollama provider")
    
    def _create_provider(self, config: LLMConfig) -> BaseLLMProvider:
        """Config'e göre provider oluştur"""
        provider_map = {
            LLMProviderType.OLLAMA: OllamaProvider,
            LLMProviderType.OPENAI: OpenAIProvider,
            LLMProviderType.ANTHROPIC: AnthropicProvider,
            LLMProviderType.DEEPSEEK: DeepSeekProvider,
            LLMProviderType.AZURE_OPENAI: AzureOpenAIProvider,
        }
        
        provider_class = provider_map.get(config.provider_type, OllamaProvider)
        return provider_class(config)
    
    def reload_providers(self) -> None:
        """Provider'ları yeniden yükle (settings değiştiğinde)"""
        self._load_providers()
        logger.info("Reloaded LLM providers")
    
    @property
    def active_provider_id(self) -> str:
        """Aktif provider ID'sini döndür"""
        settings = get_settings()
        return settings.ai.active_provider_id or "default_ollama"
    
    @property
    def active_provider(self) -> Optional[BaseLLMProvider]:
        """Aktif provider'ı döndür"""
        provider = self._providers.get(self.active_provider_id)
        if not provider and self._providers:
            # Fallback: ilk provider'ı kullan
            provider = next(iter(self._providers.values()))
        return provider
    
    def get_provider(self, provider_id: str) -> Optional[BaseLLMProvider]:
        """Belirli bir provider'ı döndür"""
        return self._providers.get(provider_id)
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """Tüm provider'ları listele"""
        return [
            {
                "id": pid,
                "name": p.name,
                "model": p.model,
                "type": p.config.provider_type.value,
                "is_active": pid == self.active_provider_id
            }
            for pid, p in self._providers.items()
        ]
    
    async def check_active_connection(self) -> bool:
        """Aktif provider bağlantısını kontrol et"""
        provider = self.active_provider
        if provider:
            return await provider.check_connection()
        return False

    def _resolve_provider(self, provider_id: Optional[str] = None) -> BaseLLMProvider:
        """Resolve selected or active provider and validate existence."""
        if provider_id:
            provider = self.get_provider(provider_id)
            if not provider:
                raise ValueError(f"Provider not found: {provider_id}")
            return provider

        provider = self.active_provider
        if not provider:
            raise ValueError("No active LLM provider configured")
        return provider
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        LLM'den yanıt üret
        
        Args:
            prompt: Kullanıcı prompt'u
            system_prompt: System prompt
            provider_id: Belirli bir provider kullan (opsiyonel)
            **kwargs: Ek parametreler (temperature, max_tokens, etc.)
            
        Returns:
            LLM yanıtı
        """
        provider = self._resolve_provider(provider_id)
        
        logger.info(f"Generating with provider: {provider.name} (model: {provider.model})")
        
        return await provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            **kwargs
        )

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider_id: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> str:
        """
        LLM'den streaming yanıt üretir.
        """
        provider = self._resolve_provider(provider_id)
        logger.info(f"Generating (streaming) with provider: {provider.name} (model: {provider.model})")

        return await provider.generate_streaming(
            prompt=prompt,
            system_prompt=system_prompt,
            on_chunk=on_chunk,
            **kwargs,
        )


# Singleton instance
def get_llm_client() -> UnifiedLLMClient:
    """Get unified LLM client instance"""
    return UnifiedLLMClient()


# Convenience functions
async def generate_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider_id: Optional[str] = None,
    **kwargs
) -> str:
    """Shortcut for generating LLM response"""
    client = get_llm_client()
    return await client.generate(prompt, system_prompt, provider_id, **kwargs)


async def check_llm_connection() -> bool:
    """Check if active LLM is available"""
    client = get_llm_client()
    return await client.check_active_connection()
