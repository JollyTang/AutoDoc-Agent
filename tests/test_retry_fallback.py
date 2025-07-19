"""
重试和降级机制的单元测试
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from src.llm.retry_fallback import (
    RetryConfig, FallbackConfig, CircuitBreakerConfig, RetryStrategy, ErrorType,
    CircuitBreaker, ErrorClassifier, RetryManager, FallbackManager, EnhancedLLMManager,
    create_enhanced_llm_manager, retry_decorator
)
from src.llm.providers import (
    ProviderType, Message, ChatCompletionRequest, LLMManager
)


class TestErrorClassifier:
    """错误分类器测试"""
    
    def test_classify_network_error(self):
        """测试网络错误分类"""
        error = Exception("Connection failed")
        error_type = ErrorClassifier.classify_error(error)
        assert error_type == ErrorType.NETWORK
    
    def test_classify_timeout_error(self):
        """测试超时错误分类"""
        error = Exception("Request timeout")
        error_type = ErrorClassifier.classify_error(error)
        assert error_type == ErrorType.TIMEOUT
    
    def test_classify_rate_limit_error(self):
        """测试速率限制错误分类"""
        error = Exception("Rate limit exceeded")
        error_type = ErrorClassifier.classify_error(error)
        assert error_type == ErrorType.RATE_LIMIT
    
    def test_classify_auth_error(self):
        """测试认证错误分类"""
        error = Exception("Invalid API key")
        error_type = ErrorClassifier.classify_error(error)
        assert error_type == ErrorType.AUTHENTICATION
    
    def test_classify_quota_error(self):
        """测试配额错误分类"""
        error = Exception("Quota exceeded")
        error_type = ErrorClassifier.classify_error(error)
        assert error_type == ErrorType.QUOTA_EXCEEDED
    
    def test_classify_server_error(self):
        """测试服务器错误分类"""
        error = Exception("Server error 500")
        error_type = ErrorClassifier.classify_error(error)
        assert error_type == ErrorType.SERVER_ERROR
    
    def test_classify_model_error(self):
        """测试模型错误分类"""
        error = Exception("Model not available")
        error_type = ErrorClassifier.classify_error(error)
        assert error_type == ErrorType.MODEL_UNAVAILABLE
    
    def test_classify_unknown_error(self):
        """测试未知错误分类"""
        error = Exception("Unknown error")
        error_type = ErrorClassifier.classify_error(error)
        assert error_type == ErrorType.UNKNOWN
    
    def test_should_retry(self):
        """测试是否应该重试"""
        retry_config = RetryConfig()
        assert ErrorClassifier.should_retry(ErrorType.NETWORK, retry_config) == True
        assert ErrorClassifier.should_retry(ErrorType.AUTHENTICATION, retry_config) == False
    
    def test_should_fallback(self):
        """测试是否应该降级"""
        fallback_config = FallbackConfig()
        assert ErrorClassifier.should_fallback(ErrorType.AUTHENTICATION, fallback_config) == True
        assert ErrorClassifier.should_fallback(ErrorType.NETWORK, fallback_config) == False


class TestCircuitBreaker:
    """熔断器测试"""
    
    def test_circuit_breaker_initial_state(self):
        """测试熔断器初始状态"""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_success(self):
        """测试熔断器成功处理"""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)
        
        assert cb.can_execute() == True
        cb.on_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_failure(self):
        """测试熔断器失败处理"""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config)
        
        # 第一次失败
        cb.on_failure()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 1
        assert cb.can_execute() == True
        
        # 第二次失败，触发熔断
        cb.on_failure()
        assert cb.state == "OPEN"
        assert cb.failure_count == 2
        assert cb.can_execute() == False
    
    def test_circuit_breaker_recovery(self):
        """测试熔断器恢复"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker(config)
        
        # 触发熔断
        cb.on_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() == False
        
        # 等待恢复
        time.sleep(0.2)
        assert cb.can_execute() == True
        assert cb.state == "HALF_OPEN"
        
        # 成功恢复
        cb.on_success()
        assert cb.state == "CLOSED"


class TestRetryManager:
    """重试管理器测试"""
    
    @pytest.mark.asyncio
    async def test_retry_manager_success_on_first_try(self):
        """测试第一次就成功的情况"""
        config = RetryConfig(max_retries=3, base_delay=0.1)
        manager = RetryManager(config)
        
        async def success_func():
            return "success"
        
        result = await manager.execute_with_retry(success_func)
        assert result == "success"
        
        stats = manager.get_stats()
        assert stats.total_requests == 1
        assert stats.successful_requests == 1
        assert stats.failed_requests == 0
        assert stats.retry_attempts == 0
    
    @pytest.mark.asyncio
    async def test_retry_manager_success_after_retries(self):
        """测试重试后成功的情况"""
        config = RetryConfig(max_retries=3, base_delay=0.1, jitter=False)
        manager = RetryManager(config)
        
        call_count = 0
        
        async def fail_then_success():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Connection failed")  # 使用网络错误关键词
            return "success"
        
        result = await manager.execute_with_retry(fail_then_success)
        assert result == "success"
        
        stats = manager.get_stats()
        assert stats.total_requests == 3
        assert stats.successful_requests == 1
        assert stats.failed_requests == 2
        assert stats.retry_attempts == 2
    
    @pytest.mark.asyncio
    async def test_retry_manager_all_retries_fail(self):
        """测试所有重试都失败的情况"""
        config = RetryConfig(max_retries=2, base_delay=0.1, jitter=False)
        manager = RetryManager(config)
        
        async def always_fail():
            raise Exception("Connection failed")  # 使用网络错误关键词
        
        with pytest.raises(Exception, match="Connection failed"):
            await manager.execute_with_retry(always_fail)
        
        stats = manager.get_stats()
        assert stats.total_requests == 3
        assert stats.successful_requests == 0
        assert stats.failed_requests == 3
        assert stats.retry_attempts == 2
    
    def test_calculate_delay_exponential(self):
        """测试指数退避延迟计算"""
        config = RetryConfig(strategy=RetryStrategy.EXPONENTIAL_BACKOFF, base_delay=1.0, jitter=False)
        manager = RetryManager(config)
        
        assert manager.calculate_delay(0) == 1.0
        assert manager.calculate_delay(1) == 2.0
        assert manager.calculate_delay(2) == 4.0
    
    def test_calculate_delay_linear(self):
        """测试线性退避延迟计算"""
        config = RetryConfig(strategy=RetryStrategy.LINEAR_BACKOFF, base_delay=1.0, jitter=False)
        manager = RetryManager(config)
        
        assert manager.calculate_delay(0) == 1.0
        assert manager.calculate_delay(1) == 2.0
        assert manager.calculate_delay(2) == 3.0
    
    def test_calculate_delay_constant(self):
        """测试固定延迟计算"""
        config = RetryConfig(strategy=RetryStrategy.CONSTANT_DELAY, base_delay=1.0, jitter=False)
        manager = RetryManager(config)
        
        assert manager.calculate_delay(0) == 1.0
        assert manager.calculate_delay(1) == 1.0
        assert manager.calculate_delay(2) == 1.0


class TestRetryDecorator:
    """重试装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_retry_decorator_success(self):
        """测试重试装饰器成功情况"""
        call_count = 0
        
        @retry_decorator(max_retries=2, base_delay=0.1)
        async def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise Exception("Connection failed")  # 使用网络错误关键词
            return "success"
        
        result = await decorated_func()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_decorator_failure(self):
        """测试重试装饰器失败情况"""
        @retry_decorator(max_retries=1, base_delay=0.1)
        async def decorated_func():
            raise Exception("Connection failed")  # 使用网络错误关键词
        
        with pytest.raises(Exception, match="Connection failed"):
            await decorated_func()


class TestEnhancedLLMManager:
    """增强 LLM 管理器测试"""
    
    def test_create_enhanced_llm_manager(self):
        """测试创建增强 LLM 管理器"""
        manager = create_enhanced_llm_manager()
        assert isinstance(manager, EnhancedLLMManager)
        assert manager.retry_config is not None
        assert manager.fallback_config is not None
        assert manager.circuit_breaker_config is not None
    
    def test_get_circuit_breaker_status(self):
        """测试获取熔断器状态"""
        manager = create_enhanced_llm_manager()
        status = manager.get_circuit_breaker_status()
        assert isinstance(status, dict)
        assert len(status) == 0  # 初始状态为空
    
    def test_get_retry_stats(self):
        """测试获取重试统计"""
        manager = create_enhanced_llm_manager()
        stats = manager.get_retry_stats()
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0


class TestRetryConfig:
    """重试配置测试"""
    
    def test_retry_config_defaults(self):
        """测试重试配置默认值"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.jitter == True
        assert len(config.retry_on_errors) > 0
    
    def test_retry_config_custom(self):
        """测试自定义重试配置"""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            jitter=False
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.strategy == RetryStrategy.LINEAR_BACKOFF
        assert config.jitter == False


class TestFallbackConfig:
    """降级配置测试"""
    
    def test_fallback_config_defaults(self):
        """测试降级配置默认值"""
        config = FallbackConfig()
        assert config.enable_fallback == True
        assert len(config.fallback_providers) == 3
        assert ProviderType.OPENAI in config.fallback_providers
        assert ProviderType.CLAUDE in config.fallback_providers
        assert ProviderType.OLLAMA in config.fallback_providers
        assert len(config.fallback_on_errors) > 0
    
    def test_fallback_config_custom(self):
        """测试自定义降级配置"""
        config = FallbackConfig(
            enable_fallback=False,
            fallback_providers=[ProviderType.OPENAI],
            fallback_on_errors=[ErrorType.AUTHENTICATION]
        )
        assert config.enable_fallback == False
        assert config.fallback_providers == [ProviderType.OPENAI]
        assert config.fallback_on_errors == [ErrorType.AUTHENTICATION]


class TestCircuitBreakerConfig:
    """熔断器配置测试"""
    
    def test_circuit_breaker_config_defaults(self):
        """测试熔断器配置默认值"""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.expected_exception == Exception
        assert config.monitor_interval == 10.0
    
    def test_circuit_breaker_config_custom(self):
        """测试自定义熔断器配置"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0
        )
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0 