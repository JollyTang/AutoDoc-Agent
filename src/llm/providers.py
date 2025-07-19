"""
LLM 提供商集成模块

提供统一的 LLM 接口，支持多个提供商：
- OpenAI API
- Claude API  
- Ollama (本地 OSS 模型)
"""

import abc
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from urllib.parse import urljoin

import httpx
import keyring
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """模型类型枚举"""
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    OLLAMA_LLAMA2 = "llama2"
    OLLAMA_CODEGEN = "codellama"
    OLLAMA_MISTRAL = "mistral"


class ProviderType(Enum):
    """提供商类型枚举"""
    OPENAI = "openai"
    CLAUDE = "claude"
    OLLAMA = "ollama"


@dataclass
class Message:
    """聊天消息"""
    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None


@dataclass
class ChatCompletionRequest:
    """聊天完成请求"""
    messages: List[Message]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False
    stop: Optional[List[str]] = None


@dataclass
class ChatCompletionResponse:
    """聊天完成响应"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


@dataclass
class ChatCompletionChunk:
    """流式聊天完成块"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]


@dataclass
class ProviderConfig:
    """提供商配置"""
    provider_type: ProviderType
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    model_mapping: Dict[str, str] = field(default_factory=dict)


class LLMProvider(ABC):
    """
    LLM 提供商抽象基类
    
    定义了所有 LLM 提供商必须实现的接口。
    """
    
    def __init__(self, config: ProviderConfig):
        """
        初始化提供商
        
        Args:
            config: 提供商配置
        """
        self.config = config
        # 设置默认的 api_base
        if config.provider_type == ProviderType.OPENAI:
            self.api_base = config.api_base or "https://api.openai.com/v1"
        elif config.provider_type == ProviderType.CLAUDE:
            self.api_base = config.api_base or "https://api.anthropic.com/v1"
        elif config.provider_type == ProviderType.OLLAMA:
            self.api_base = config.api_base or "http://localhost:11434"
        else:
            self.api_base = config.api_base
        
        self.client = self._create_client()
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def _create_client(self) -> Any:
        """创建 HTTP 客户端"""
        pass
    
    @abstractmethod
    async def chat_completion(
        self, 
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        发送聊天完成请求
        
        Args:
            request: 聊天完成请求
            
        Returns:
            聊天完成响应
        """
        pass
    
    @abstractmethod
    async def chat_completion_stream(
        self, 
        request: ChatCompletionRequest
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        发送流式聊天完成请求
        
        Args:
            request: 聊天完成请求
            
        Yields:
            聊天完成块
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        获取可用模型列表
        
        Returns:
            模型列表
        """
        pass
    
    @abstractmethod
    def get_model_name(self, model: str) -> str:
        """
        获取实际的模型名称（处理模型映射）
        
        Args:
            model: 请求的模型名称
            
        Returns:
            实际的模型名称
        """
        pass
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            是否健康
        """
        try:
            await self.list_models()
            return True
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            return False
    
    def _format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """格式化消息列表"""
        formatted = []
        for msg in messages:
            formatted_msg = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                formatted_msg["name"] = msg.name
            formatted.append(formatted_msg)
        return formatted
    
    def _create_system_message(self, system_prompt: str) -> Message:
        """创建系统消息"""
        return Message(role="system", content=system_prompt)


class OpenAIProvider(LLMProvider):
    """OpenAI API 提供商"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
    
    def _create_client(self) -> httpx.AsyncClient:
        """创建 OpenAI HTTP 客户端"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        return httpx.AsyncClient(
            base_url=self.api_base,
            headers=headers,
            timeout=self.config.timeout
        )
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """发送聊天完成请求"""
        url = "/chat/completions"
        payload = {
            "model": self.get_model_name(request.model),
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": False
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return ChatCompletionResponse(
                id=data["id"],
                object=data["object"],
                created=data["created"],
                model=data["model"],
                choices=data["choices"],
                usage=data.get("usage"),
                finish_reason=data["choices"][0].get("finish_reason")
            )
    
    async def chat_completion_stream(
        self, 
        request: ChatCompletionRequest
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """发送流式聊天完成请求"""
        url = "/chat/completions"
        payload = {
            "model": self.get_model_name(request.model),
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": True
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        
        async with self.client as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前缀
                        if data == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data)
                            yield ChatCompletionChunk(
                                id=chunk_data["id"],
                                object=chunk_data["object"],
                                created=chunk_data["created"],
                                model=chunk_data["model"],
                                choices=chunk_data["choices"]
                            )
                        except json.JSONDecodeError:
                            continue
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        async with self.client as client:
            response = await client.get("/models")
            response.raise_for_status()
            data = response.json()
            return data["data"]
    
    def get_model_name(self, model: str) -> str:
        """获取实际的模型名称"""
        return self.config.model_mapping.get(model, model)


class ClaudeProvider(LLMProvider):
    """Claude API 提供商"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
    
    def _create_client(self) -> httpx.AsyncClient:
        """创建 Claude HTTP 客户端"""
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        return httpx.AsyncClient(
            base_url=self.api_base,
            headers=headers,
            timeout=self.config.timeout
        )
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """发送聊天完成请求"""
        url = "/messages"
        payload = {
            "model": self.get_model_name(request.model),
            "messages": self._format_messages(request.messages),
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": False
        }
        
        if request.stop:
            payload["stop_sequences"] = request.stop
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # 转换为 OpenAI 格式
            return ChatCompletionResponse(
                id=data["id"],
                object="chat.completion",
                created=int(time.time()),
                model=data["model"],
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": data["content"][0]["text"]
                    },
                    "finish_reason": data.get("stop_reason")
                }],
                usage=data.get("usage")
            )
    
    async def chat_completion_stream(
        self, 
        request: ChatCompletionRequest
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """发送流式聊天完成请求"""
        url = "/messages"
        payload = {
            "model": self.get_model_name(request.model),
            "messages": self._format_messages(request.messages),
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": True
        }
        
        if request.stop:
            payload["stop_sequences"] = request.stop
        
        async with self.client as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data)
                            if chunk_data["type"] == "content_block_delta":
                                yield ChatCompletionChunk(
                                    id=chunk_data.get("id", ""),
                                    object="chat.completion.chunk",
                                    created=int(time.time()),
                                    model=request.model,
                                    choices=[{
                                        "index": 0,
                                        "delta": {
                                            "content": chunk_data["delta"]["text"]
                                        },
                                        "finish_reason": None
                                    }]
                                )
                        except json.JSONDecodeError:
                            continue
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        # Claude API 不提供模型列表端点，返回预定义模型
        return [
            {"id": "claude-3-opus-20240229", "object": "model"},
            {"id": "claude-3-sonnet-20240229", "object": "model"},
            {"id": "claude-3-haiku-20240307", "object": "model"}
        ]
    
    def get_model_name(self, model: str) -> str:
        """获取实际的模型名称"""
        return self.config.model_mapping.get(model, model)


class OllamaProvider(LLMProvider):
    """Ollama 本地模型提供商"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
    
    def _create_client(self) -> httpx.AsyncClient:
        """创建 Ollama HTTP 客户端"""
        return httpx.AsyncClient(
            base_url=self.api_base,
            timeout=self.config.timeout
        )
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """发送聊天完成请求"""
        url = "/api/chat"
        payload = {
            "model": self.get_model_name(request.model),
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": False
        }
        
        if request.max_tokens:
            payload["num_predict"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # 转换为 OpenAI 格式
            return ChatCompletionResponse(
                id=f"ollama-{int(time.time())}",
                object="chat.completion",
                created=int(time.time()),
                model=data["model"],
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": data["message"]["content"]
                    },
                    "finish_reason": "stop"
                }],
                usage=data.get("usage")
            )
    
    async def chat_completion_stream(
        self, 
        request: ChatCompletionRequest
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """发送流式聊天完成请求"""
        url = "/api/chat"
        payload = {
            "model": self.get_model_name(request.model),
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": True
        }
        
        if request.max_tokens:
            payload["num_predict"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        
        async with self.client as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk_data = json.loads(line)
                            if "message" in chunk_data:
                                yield ChatCompletionChunk(
                                    id=f"ollama-{int(time.time())}",
                                    object="chat.completion.chunk",
                                    created=int(time.time()),
                                    model=chunk_data["model"],
                                    choices=[{
                                        "index": 0,
                                        "delta": {
                                            "content": chunk_data["message"]["content"]
                                        },
                                        "finish_reason": None
                                    }]
                                )
                        except json.JSONDecodeError:
                            continue
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        async with self.client as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [{"id": model["name"], "object": "model"} for model in data["models"]]
    
    def get_model_name(self, model: str) -> str:
        """获取实际的模型名称"""
        return self.config.model_mapping.get(model, model)


class LLMManager:
    """
    LLM 管理器
    
    管理多个 LLM 提供商，提供统一的接口和故障转移机制。
    """
    
    def __init__(self):
        self.providers: Dict[ProviderType, LLMProvider] = {}
        self.default_provider: Optional[ProviderType] = None
        self.logger = logging.getLogger(f"{__name__}.LLMManager")
    
    def add_provider(self, provider_type: ProviderType, provider: LLMProvider):
        """添加提供商"""
        self.providers[provider_type] = provider
        if not self.default_provider:
            self.default_provider = provider_type
    
    def set_default_provider(self, provider_type: ProviderType):
        """设置默认提供商"""
        if provider_type in self.providers:
            self.default_provider = provider_type
        else:
            raise ValueError(f"提供商 {provider_type} 未注册")
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest,
        provider_type: Optional[ProviderType] = None
    ) -> ChatCompletionResponse:
        """
        发送聊天完成请求，支持故障转移
        
        Args:
            request: 聊天完成请求
            provider_type: 指定提供商，None 使用默认提供商
            
        Returns:
            聊天完成响应
        """
        provider_type = provider_type or self.default_provider
        if not provider_type:
            raise ValueError("未设置默认提供商")
        
        provider = self.providers[provider_type]
        
        # 重试机制
        for attempt in range(provider.config.max_retries):
            try:
                return await provider.chat_completion(request)
            except Exception as e:
                self.logger.warning(f"提供商 {provider_type} 请求失败 (尝试 {attempt + 1}): {e}")
                if attempt < provider.config.max_retries - 1:
                    await asyncio.sleep(provider.config.retry_delay * (2 ** attempt))
                else:
                    raise
    
    async def chat_completion_stream(
        self, 
        request: ChatCompletionRequest,
        provider_type: Optional[ProviderType] = None
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        发送流式聊天完成请求
        
        Args:
            request: 聊天完成请求
            provider_type: 指定提供商，None 使用默认提供商
            
        Yields:
            聊天完成块
        """
        provider_type = provider_type or self.default_provider
        if not provider_type:
            raise ValueError("未设置默认提供商")
        
        provider = self.providers[provider_type]
        
        try:
            async for chunk in provider.chat_completion_stream(request):
                yield chunk
        except Exception as e:
            self.logger.error(f"流式请求失败: {e}")
            raise
    
    async def health_check_all(self) -> Dict[ProviderType, bool]:
        """检查所有提供商的健康状态"""
        results = {}
        for provider_type, provider in self.providers.items():
            results[provider_type] = await provider.health_check()
        return results


# 便捷函数
def create_provider(
    provider_type: ProviderType,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    创建 LLM 提供商
    
    Args:
        provider_type: 提供商类型
        api_key: API 密钥
        api_base: API 基础 URL
        **kwargs: 其他配置参数
        
    Returns:
        LLM 提供商实例
    """
    config = ProviderConfig(
        provider_type=provider_type,
        api_key=api_key,
        api_base=api_base,
        **kwargs
    )
    
    if provider_type == ProviderType.OPENAI:
        return OpenAIProvider(config)
    elif provider_type == ProviderType.CLAUDE:
        return ClaudeProvider(config)
    elif provider_type == ProviderType.OLLAMA:
        return OllamaProvider(config)
    else:
        raise ValueError(f"不支持的提供商类型: {provider_type}")


def get_api_key_from_keyring(provider_type: ProviderType) -> Optional[str]:
    """
    从 keyring 获取 API 密钥
    
    Args:
        provider_type: 提供商类型
        
    Returns:
        API 密钥，如果不存在则返回 None
    """
    try:
        return keyring.get_password("autodoc-agent", f"{provider_type.value}_api_key")
    except Exception as e:
        logger.warning(f"从 keyring 获取 API 密钥失败: {e}")
        return None


def set_api_key_to_keyring(provider_type: ProviderType, api_key: str):
    """
    将 API 密钥存储到 keyring
    
    Args:
        provider_type: 提供商类型
        api_key: API 密钥
    """
    try:
        keyring.set_password("autodoc-agent", f"{provider_type.value}_api_key", api_key)
        logger.info(f"API 密钥已存储到 keyring: {provider_type.value}")
    except Exception as e:
        logger.error(f"存储 API 密钥到 keyring 失败: {e}")
        raise


# 全局 LLM 管理器实例
_global_llm_manager: Optional[LLMManager] = None


def get_global_llm_manager() -> LLMManager:
    """获取全局 LLM 管理器实例"""
    global _global_llm_manager
    if _global_llm_manager is None:
        _global_llm_manager = LLMManager()
    return _global_llm_manager


def set_global_llm_manager(manager: LLMManager):
    """设置全局 LLM 管理器实例"""
    global _global_llm_manager
    _global_llm_manager = manager 