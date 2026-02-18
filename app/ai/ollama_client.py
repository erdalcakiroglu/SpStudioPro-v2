"""
Ollama API Client - Enhanced with better model support and advanced options

Supports:
- Multiple models (CodeLlama, SQLCoder, DeepSeek-Coder, etc.)
- Advanced generation options (top_p, repeat_penalty, etc.)
- Model availability checking
- Streaming responses
"""

import json
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger('ai.ollama')


class RecommendedModel(Enum):
    """SQL optimizasyonu için önerilen modeller"""
    CODELLAMA = "codellama"           # Genel kod, SQL desteği
    CODELLAMA_34B = "codellama:34b"   # Daha büyük, daha iyi
    SQLCODER = "sqlcoder"             # SQL-specialized (defog/sqlcoder)
    SQLCODER_7B = "sqlcoder:7b"       # SQLCoder 7B variant
    DEEPSEEK_CODER = "deepseek-coder" # Code optimization
    DEEPSEEK_CODER_33B = "deepseek-coder:33b"
    LLAMA3 = "llama3"                 # General purpose
    MIXTRAL = "mixtral"               # MoE, good for complex tasks
    QWEN_CODER = "qwen2.5-coder"      # Alibaba code model


@dataclass
class GenerationOptions:
    """Advanced generation options for Ollama"""
    temperature: float = 0.1          # Düşük = tutarlı, Yüksek = yaratıcı
    top_p: float = 0.9                # Nucleus sampling
    top_k: int = 40                   # Top-k sampling
    repeat_penalty: float = 1.1       # Tekrar önleme
    num_predict: int = 4096           # Max tokens
    num_ctx: int = 8192               # Context window
    stop: Optional[List[str]] = None  # Stop sequences
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Ollama options dict"""
        opts = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "num_predict": self.num_predict,
            "num_ctx": self.num_ctx,
        }
        if self.stop:
            opts["stop"] = self.stop
        return opts


class OllamaClient:
    """
    Enhanced Ollama API Client
    
    Features:
    - Model availability checking
    - Advanced generation options
    - Automatic model fallback
    - Better error handling
    """
    
    # Fallback model listesi (tercih sırasına göre)
    FALLBACK_MODELS = [
        "sqlcoder",
        "codellama",
        "deepseek-coder",
        "llama3",
        "mixtral",
    ]
    
    def __init__(self, model: Optional[str] = None):
        settings = get_settings()
        self.host = settings.ai.ollama_host
        self.model = model or settings.ai.model
        self.timeout = settings.ai.timeout
        self._available_models: Optional[List[str]] = None
    
    async def check_connection(self) -> bool:
        """Ollama servisinin çalışıp çalışmadığını kontrol eder"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Mevcut modellerin listesini döndürür"""
        if self._available_models is not None:
            return self._available_models
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    self._available_models = [m['name'] for m in data.get('models', [])]
                    logger.info(f"Available models: {self._available_models}")
                    return self._available_models
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
        
        return []
    
    async def is_model_available(self, model_name: str) -> bool:
        """Belirtilen modelin mevcut olup olmadığını kontrol eder"""
        models = await self.get_available_models()
        # Exact match or prefix match (e.g., "codellama" matches "codellama:7b")
        return any(m == model_name or m.startswith(f"{model_name}:") for m in models)
    
    async def get_best_available_model(self) -> str:
        """
        SQL optimizasyonu için en iyi mevcut modeli döndürür.
        Öncelik: sqlcoder > codellama > deepseek-coder > diğerleri
        """
        models = await self.get_available_models()
        
        # Öncelikli modelleri kontrol et
        for preferred in self.FALLBACK_MODELS:
            for available in models:
                if available == preferred or available.startswith(f"{preferred}:"):
                    logger.info(f"Selected best model: {available}")
                    return available
        
        # Hiçbiri yoksa ilk mevcut modeli döndür
        if models:
            return models[0]
        
        # Varsayılan
        return self.model
    
    async def pull_model(self, model_name: str) -> bool:
        """Modeli indir (varsa atla)"""
        if await self.is_model_available(model_name):
            logger.info(f"Model already available: {model_name}")
            return True
        
        try:
            logger.info(f"Pulling model: {model_name}")
            async with httpx.AsyncClient(timeout=600.0) as client:  # 10 dakika timeout
                response = await client.post(
                    f"{self.host}/api/pull",
                    json={"name": model_name},
                    timeout=600.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        stream: bool = False,
        options: Optional[GenerationOptions] = None,
        model: Optional[str] = None
    ) -> Any:
        """
        Ollama'dan yanıt üretir
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (role definition)
            stream: Enable streaming response
            options: Advanced generation options
            model: Override default model
            
        Returns:
            Generated response text (or async generator if streaming)
        """
        url = f"{self.host}/api/generate"
        
        # Model seçimi
        use_model = model or self.model
        
        # Options
        if options is None:
            settings = get_settings()
            options = GenerationOptions(
                temperature=settings.ai.temperature,
                num_predict=settings.ai.max_tokens,
            )
        
        payload = {
            "model": use_model,
            "prompt": prompt,
            "stream": stream,
            "options": options.to_dict()
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        logger.debug(f"Generating with model: {use_model}, prompt length: {len(prompt)}")
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    return self._handle_stream(client, url, payload)
                else:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    
                    result = response.json()
                    generated_text = result.get("response", "")
                    
                    # Log metrics
                    if "total_duration" in result:
                        duration_ms = result["total_duration"] / 1_000_000
                        logger.info(f"Generation completed in {duration_ms:.0f}ms")
                    
                    return generated_text
                    
        except httpx.TimeoutException:
            logger.error(f"Ollama generation timed out after {self.timeout}s")
            raise
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def _handle_stream(self, client, url, payload) -> AsyncGenerator[str, None]:
        """Stream yanıtlarını işler"""
        async with client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    
    async def generate_with_best_model(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        options: Optional[GenerationOptions] = None
    ) -> str:
        """
        En iyi mevcut model ile yanıt üret.
        Model yoksa fallback kullan.
        """
        best_model = await self.get_best_available_model()
        return await self.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            options=options,
            model=best_model
        )


# SQL optimizasyonu için önerilen options
SQL_OPTIMIZATION_OPTIONS = GenerationOptions(
    temperature=0.1,      # Düşük - tutarlı sonuçlar
    top_p=0.9,
    top_k=40,
    repeat_penalty=1.1,
    num_predict=4096,
    num_ctx=8192,
)

# Code generation için options
CODE_GENERATION_OPTIONS = GenerationOptions(
    temperature=0.2,      # Biraz daha yaratıcı
    top_p=0.95,
    top_k=50,
    repeat_penalty=1.15,
    num_predict=6000,
    num_ctx=8192,
)

# Chat/conversation için options  
CHAT_OPTIONS = GenerationOptions(
    temperature=0.7,      # Daha doğal konuşma
    top_p=0.9,
    top_k=40,
    repeat_penalty=1.0,
    num_predict=2048,
    num_ctx=4096,
)
