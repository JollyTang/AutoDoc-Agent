"""
LLM 调用重试和降级机制

提供完善的 LLM 调用重试策略、降级机制和错误处理功能：
- 指数退避重试策略
- 智能降级机制
- 错误分类和处理
- 性能监控和统计
- 熔断器模式
"""

import asyncio
import logging
import time
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, AsyncGenerator
from functools import wraps

import httpx

from .providers import (
    LLMProvider, ProviderType, ChatCompletionRequest, ChatCompletionResponse,
    ChatCompletionChunk, ProviderConfig, LLMManager
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorType(Enum):
    """错误类型枚举"""
    NETWORK = "network"           # 网络错误
    TIMEOUT = "timeout"           # 超时错误
    RATE_LIMIT = "rate_limit"     # 速率限制
    AUTHENTICATION = "auth"       # 认证错误
    QUOTA_EXCEEDED = "quota"      # 配额超限
    SERVER_ERROR = "server"       # 服务器错误
    MODEL_UNAVAILABLE = "model"   # 模型不可用
    UNKNOWN = "unknown"           # 未知错误


class RetryStrategy(Enum):
    """重试策略枚举"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数退避
    LINEAR_BACKOFF = "linear_backoff"            # 线性退避
    CONSTANT_DELAY = "constant_delay"            # 固定延迟
    RANDOM_BACKOFF = "random_backoff"            # 随机退避


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True
    retry_on_errors: List[ErrorType] = field(default_factory=lambda: [
        ErrorType.NETWORK, ErrorType.TIMEOUT, ErrorType.RATE_LIMIT, 
        ErrorType.SERVER_ERROR, ErrorType.MODEL_UNAVAILABLE
    ])


@dataclass
class FallbackConfig:
    """降级配置"""
    enable_fallback: bool = True
    fallback_providers: List[ProviderType] = field(default_factory=lambda: [
        ProviderType.OPENAI, ProviderType.CLAUDE, ProviderType.OLLAMA
    ])
    fallback_on_errors: List[ErrorType] = field(default_factory=lambda: [
        ErrorType.AUTHENTICATION, ErrorType.QUOTA_EXCEEDED, 
        ErrorType.MODEL_UNAVAILABLE, ErrorType.SERVER_ERROR
    ])
    preserve_original_request: bool = True


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: type = Exception
    monitor_interval: float = 10.0


@dataclass
class RetryStats:
    """重试统计信息"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_attempts: int = 0
    total_retry_time: float = 0.0
    average_response_time: float = 0.0
    error_counts: Dict[ErrorType, int] = field(default_factory=dict)


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
    
    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def on_success(self):
        """请求成功时的处理"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        """请求失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"熔断器打开，失败次数: {self.failure_count}")


class ErrorClassifier:
    """错误分类器"""
    
    @staticmethod
    def classify_error(error: Exception) -> ErrorType:
        """分类错误类型"""
        error_str = str(error).lower()
        
        # 网络相关错误
        if any(keyword in error_str for keyword in ["connection", "network", "connect"]):
            return ErrorType.NETWORK
        elif any(keyword in error_str for keyword in ["timeout", "timed out"]):
            return ErrorType.TIMEOUT
        elif any(keyword in error_str for keyword in ["rate limit", "rate_limit", "429"]):
            return ErrorType.RATE_LIMIT
        elif any(keyword in error_str for keyword in ["auth", "unauthorized", "401", "invalid api key"]):
            return ErrorType.AUTHENTICATION
        elif any(keyword in error_str for keyword in ["quota", "402", "billing"]):
            return ErrorType.QUOTA_EXCEEDED
        elif any(keyword in error_str for keyword in ["server", "500", "502", "503", "504"]):
            return ErrorType.SERVER_ERROR
        elif any(keyword in error_str for keyword in ["model", "model not available"]):
            return ErrorType.MODEL_UNAVAILABLE
        else:
            return ErrorType.UNKNOWN
    
    @staticmethod
    def should_retry(error_type: ErrorType, retry_config: RetryConfig) -> bool:
        """判断是否应该重试"""
        return error_type in retry_config.retry_on_errors
    
    @staticmethod
    def should_fallback(error_type: ErrorType, fallback_config: FallbackConfig) -> bool:
        """判断是否应该降级"""
        return error_type in fallback_config.fallback_on_errors


class RetryManager:
    """重试管理器"""
    
    def __init__(self, retry_config: RetryConfig):
        self.config = retry_config
        self.stats = RetryStats()
        self.logger = logging.getLogger(f"{__name__}.RetryManager")
    
    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (2 ** attempt)
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.CONSTANT_DELAY:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.RANDOM_BACKOFF:
            delay = random.uniform(0, self.config.base_delay * (2 ** attempt))
        else:
            delay = self.config.base_delay
        
        # 添加抖动
        if self.config.jitter:
            delay *= random.uniform(0.5, 1.5)
        
        return min(delay, self.config.max_delay)
    
    async def execute_with_retry(
        self, 
        func: Callable[..., T], 
        *args, 
        **kwargs
    ) -> T:
        """执行带重试的函数"""
        last_error = None
        start_time = time.time()
        
        for attempt in range(self.config.max_retries + 1):
            try:
                self.stats.total_requests += 1
                result = await func(*args, **kwargs)
                self.stats.successful_requests += 1
                
                # 计算响应时间
                response_time = time.time() - start_time
                if self.stats.successful_requests == 1:
                    self.stats.average_response_time = response_time
                else:
                    self.stats.average_response_time = (
                        (self.stats.average_response_time * (self.stats.successful_requests - 1) + response_time) 
                        / self.stats.successful_requests
                    )
                
                return result
                
            except Exception as e:
                last_error = e
                self.stats.failed_requests += 1
                
                # 分类错误
                error_type = ErrorClassifier.classify_error(e)
                self.stats.error_counts[error_type] = self.stats.error_counts.get(error_type, 0) + 1
                
                # 判断是否应该重试
                if attempt < self.config.max_retries and ErrorClassifier.should_retry(error_type, self.config):
                    self.stats.retry_attempts += 1
                    delay = self.calculate_delay(attempt)
                    self.stats.total_retry_time += delay
                    
                    self.logger.warning(
                        f"请求失败 (尝试 {attempt + 1}/{self.config.max_retries + 1}): "
                        f"{error_type.value} - {e}. 等待 {delay:.2f}s 后重试"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    break
        
        # 所有重试都失败了
        self.logger.error(f"所有重试都失败了: {last_error}")
        raise last_error
    
    def get_stats(self) -> RetryStats:
        """获取统计信息"""
        return self.stats


class FallbackManager:
    """降级管理器"""
    
    def __init__(self, fallback_config: FallbackConfig, llm_manager: LLMManager):
        self.config = fallback_config
        self.llm_manager = llm_manager
        self.logger = logging.getLogger(f"{__name__}.FallbackManager")
    
    async def execute_with_fallback(
        self,
        request: ChatCompletionRequest,
        primary_provider: ProviderType,
        operation: str = "chat_completion"
    ) -> Union[ChatCompletionResponse, AsyncGenerator[ChatCompletionChunk, None]]:
        """执行带降级的操作"""
        providers_to_try = [primary_provider] + self.config.fallback_providers
        
        for provider_type in providers_to_try:
            if provider_type not in self.llm_manager.providers:
                continue
            
            try:
                provider = self.llm_manager.providers[provider_type]
                
                if operation == "chat_completion":
                    return await provider.chat_completion(request)
                elif operation == "chat_completion_stream":
                    return provider.chat_completion_stream(request)
                else:
                    raise ValueError(f"不支持的操作: {operation}")
                    
            except Exception as e:
                error_type = ErrorClassifier.classify_error(e)
                
                if ErrorClassifier.should_fallback(error_type, self.config):
                    self.logger.warning(
                        f"提供商 {provider_type.value} 失败 ({error_type.value}): {e}. "
                        f"尝试下一个提供商"
                    )
                    continue
                else:
                    # 不应该降级的错误，直接抛出
                    raise
        
        # 所有提供商都失败了
        raise Exception("所有可用的 LLM 提供商都失败了")


class EnhancedLLMManager(LLMManager):
    """增强的 LLM 管理器，包含重试和降级机制"""
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        fallback_config: Optional[FallbackConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        super().__init__()
        
        self.retry_config = retry_config or RetryConfig()
        self.fallback_config = fallback_config or FallbackConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        
        self.retry_manager = RetryManager(self.retry_config)
        self.fallback_manager = FallbackManager(self.fallback_config, self)
        self.circuit_breakers: Dict[ProviderType, CircuitBreaker] = {}
        
        self.logger = logging.getLogger(f"{__name__}.EnhancedLLMManager")
    
    def _get_circuit_breaker(self, provider_type: ProviderType) -> CircuitBreaker:
        """获取或创建熔断器"""
        if provider_type not in self.circuit_breakers:
            self.circuit_breakers[provider_type] = CircuitBreaker(self.circuit_breaker_config)
        return self.circuit_breakers[provider_type]
    
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        provider_type: Optional[ProviderType] = None
    ) -> ChatCompletionResponse:
        """增强的聊天完成请求，包含重试和降级"""
        provider_type = provider_type or self.default_provider
        if not provider_type:
            raise ValueError("未设置默认提供商")
        
        # 检查熔断器
        circuit_breaker = self._get_circuit_breaker(provider_type)
        if not circuit_breaker.can_execute():
            raise Exception(f"提供商 {provider_type.value} 的熔断器已打开")
        
        try:
            # 使用降级管理器
            result = await self.fallback_manager.execute_with_fallback(
                request, provider_type, "chat_completion"
            )
            circuit_breaker.on_success()
            return result
            
        except Exception as e:
            circuit_breaker.on_failure()
            raise
    
    async def chat_completion_stream(
        self,
        request: ChatCompletionRequest,
        provider_type: Optional[ProviderType] = None
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """增强的流式聊天完成请求"""
        provider_type = provider_type or self.default_provider
        if not provider_type:
            raise ValueError("未设置默认提供商")
        
        # 检查熔断器
        circuit_breaker = self._get_circuit_breaker(provider_type)
        if not circuit_breaker.can_execute():
            raise Exception(f"提供商 {provider_type.value} 的熔断器已打开")
        
        try:
            # 使用降级管理器
            async for chunk in self.fallback_manager.execute_with_fallback(
                request, provider_type, "chat_completion_stream"
            ):
                yield chunk
            circuit_breaker.on_success()
            
        except Exception as e:
            circuit_breaker.on_failure()
            raise
    
    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """执行带重试的操作"""
        return await self.retry_manager.execute_with_retry(func, *args, **kwargs)
    
    def get_retry_stats(self) -> RetryStats:
        """获取重试统计信息"""
        return self.retry_manager.get_stats()
    
    def get_circuit_breaker_status(self) -> Dict[ProviderType, Dict[str, Any]]:
        """获取熔断器状态"""
        status = {}
        for provider_type, circuit_breaker in self.circuit_breakers.items():
            status[provider_type] = {
                "state": circuit_breaker.state,
                "failure_count": circuit_breaker.failure_count,
                "last_failure_time": circuit_breaker.last_failure_time
            }
        return status


# 便捷函数
def create_enhanced_llm_manager(
    retry_config: Optional[RetryConfig] = None,
    fallback_config: Optional[FallbackConfig] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None
) -> EnhancedLLMManager:
    """创建增强的 LLM 管理器"""
    return EnhancedLLMManager(retry_config, fallback_config, circuit_breaker_config)


def retry_decorator(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_on_errors: Optional[List[ErrorType]] = None
):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                retry_on_errors=retry_on_errors or [
                    ErrorType.NETWORK, ErrorType.TIMEOUT, ErrorType.RATE_LIMIT
                ]
            )
            retry_manager = RetryManager(retry_config)
            return await retry_manager.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


def fallback_decorator(
    fallback_providers: List[ProviderType],
    fallback_on_errors: Optional[List[ErrorType]] = None
):
    """降级装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里需要 LLM 管理器实例，实际使用时需要传入
            # 这是一个简化的装饰器示例
            return await func(*args, **kwargs)
        return wrapper
    return decorator 