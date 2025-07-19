#!/usr/bin/env python3
"""
LLM 调用重试和降级机制演示

演示增强的重试策略、降级机制和错误处理功能：
- 指数退避重试策略
- 智能降级机制
- 错误分类和处理
- 性能监控和统计
- 熔断器模式
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.retry_fallback import (
    RetryConfig, FallbackConfig, CircuitBreakerConfig, RetryStrategy, ErrorType,
    create_enhanced_llm_manager, retry_decorator, EnhancedLLMManager
)
from src.llm.providers import (
    ProviderType, Message, ChatCompletionRequest, create_provider,
    get_api_key_from_keyring
)


async def demo_retry_strategies():
    """演示不同的重试策略"""
    print("=== 重试策略演示 ===")
    
    strategies = [
        (RetryStrategy.EXPONENTIAL_BACKOFF, "指数退避"),
        (RetryStrategy.LINEAR_BACKOFF, "线性退避"),
        (RetryStrategy.CONSTANT_DELAY, "固定延迟"),
        (RetryStrategy.RANDOM_BACKOFF, "随机退避")
    ]
    
    for strategy, name in strategies:
        print(f"\n策略: {name}")
        config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            strategy=strategy,
            jitter=True
        )
        
        print("重试延迟序列:")
        for attempt in range(config.max_retries):
            if strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                delay = config.base_delay * (2 ** attempt)
            elif strategy == RetryStrategy.LINEAR_BACKOFF:
                delay = config.base_delay * (attempt + 1)
            elif strategy == RetryStrategy.CONSTANT_DELAY:
                delay = config.base_delay
            elif strategy == RetryStrategy.RANDOM_BACKOFF:
                delay = config.base_delay * (2 ** attempt)  # 基础值
            else:
                delay = config.base_delay
            
            print(f"  尝试 {attempt + 1}: {delay:.2f}s")


async def demo_error_classification():
    """演示错误分类"""
    print("\n=== 错误分类演示 ===")
    
    from src.llm.retry_fallback import ErrorClassifier
    
    # 模拟不同类型的错误
    test_errors = [
        (Exception("Connection failed"), "连接失败"),
        (Exception("Request timeout"), "请求超时"),
        (Exception("Rate limit exceeded"), "速率限制"),
        (Exception("Invalid API key"), "无效 API 密钥"),
        (Exception("Quota exceeded"), "配额超限"),
        (Exception("Server error 500"), "服务器错误"),
        (Exception("Model not available"), "模型不可用"),
        (Exception("Unknown error"), "未知错误")
    ]
    
    print("错误分类结果:")
    for error, description in test_errors:
        error_type = ErrorClassifier.classify_error(error)
        print(f"  {description}: {error_type.value}")


async def demo_retry_manager():
    """演示重试管理器"""
    print("\n=== 重试管理器演示 ===")
    
    from src.llm.retry_fallback import RetryManager, RetryConfig, ErrorType
    
    # 创建一个会失败几次然后成功的模拟函数
    call_count = 0
    
    async def mock_function():
        nonlocal call_count
        call_count += 1
        
        if call_count <= 2:
            raise Exception("模拟网络错误")
        else:
            return "成功!"
    
    # 配置重试
    retry_config = RetryConfig(
        max_retries=3,
        base_delay=0.5,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retry_on_errors=[ErrorType.NETWORK, ErrorType.TIMEOUT]
    )
    
    retry_manager = RetryManager(retry_config)
    
    print("执行带重试的函数...")
    start_time = time.time()
    
    try:
        result = await retry_manager.execute_with_retry(mock_function)
        print(f"✅ 最终结果: {result}")
        
        # 显示统计信息
        stats = retry_manager.get_stats()
        print(f"总请求数: {stats.total_requests}")
        print(f"成功请求数: {stats.successful_requests}")
        print(f"失败请求数: {stats.failed_requests}")
        print(f"重试次数: {stats.retry_attempts}")
        print(f"总重试时间: {stats.total_retry_time:.2f}s")
        print(f"平均响应时间: {stats.average_response_time:.2f}s")
        
        total_time = time.time() - start_time
        print(f"总耗时: {total_time:.2f}s")
        
    except Exception as e:
        print(f"❌ 所有重试都失败了: {e}")


async def demo_circuit_breaker():
    """演示熔断器模式"""
    print("\n=== 熔断器模式演示 ===")
    
    from src.llm.retry_fallback import CircuitBreaker, CircuitBreakerConfig
    
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=5.0
    )
    
    circuit_breaker = CircuitBreaker(config)
    
    # 模拟连续失败
    print("模拟连续失败...")
    for i in range(5):
        if circuit_breaker.can_execute():
            print(f"  尝试 {i + 1}: 执行请求")
            # 模拟失败
            circuit_breaker.on_failure()
            print(f"    失败，状态: {circuit_breaker.state}")
        else:
            print(f"  尝试 {i + 1}: 熔断器已打开，跳过")
    
    # 等待恢复
    print(f"\n等待 {config.recovery_timeout}s 后恢复...")
    await asyncio.sleep(config.recovery_timeout + 0.1)
    
    if circuit_breaker.can_execute():
        print("熔断器已恢复，可以执行请求")
        # 模拟成功
        circuit_breaker.on_success()
        print(f"请求成功，状态: {circuit_breaker.state}")
    else:
        print("熔断器仍未恢复")


async def demo_enhanced_llm_manager():
    """演示增强的 LLM 管理器"""
    print("\n=== 增强 LLM 管理器演示 ===")
    
    # 创建配置
    retry_config = RetryConfig(
        max_retries=2,
        base_delay=0.5,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )
    
    fallback_config = FallbackConfig(
        enable_fallback=True,
        fallback_providers=[ProviderType.OPENAI, ProviderType.CLAUDE, ProviderType.OLLAMA]
    )
    
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=10.0
    )
    
    # 创建增强管理器
    manager = create_enhanced_llm_manager(
        retry_config=retry_config,
        fallback_config=fallback_config,
        circuit_breaker_config=circuit_breaker_config
    )
    
    print("增强 LLM 管理器已创建")
    print(f"重试配置: 最大重试 {retry_config.max_retries} 次")
    print(f"降级配置: 启用降级，降级提供商 {len(fallback_config.fallback_providers)} 个")
    print(f"熔断器配置: 失败阈值 {circuit_breaker_config.failure_threshold}")
    
    # 尝试添加提供商（这里只是演示，实际需要有效的 API 密钥）
    try:
        # 检查是否有可用的 API 密钥
        openai_key = get_api_key_from_keyring(ProviderType.OPENAI)
        if openai_key:
            openai_provider = create_provider(ProviderType.OPENAI, api_key=openai_key)
            manager.add_provider(ProviderType.OPENAI, openai_provider)
            manager.set_default_provider(ProviderType.OPENAI)
            print("✅ OpenAI 提供商已添加")
        else:
            print("⚠️  OpenAI API 密钥未配置")
    except Exception as e:
        print(f"⚠️  添加 OpenAI 提供商失败: {e}")
    
    # 显示熔断器状态
    status = manager.get_circuit_breaker_status()
    print(f"\n熔断器状态: {status}")


async def demo_retry_decorator():
    """演示重试装饰器"""
    print("\n=== 重试装饰器演示 ===")
    
    call_count = 0
    
    @retry_decorator(max_retries=2, base_delay=0.5)
    async def decorated_function():
        nonlocal call_count
        call_count += 1
        
        if call_count <= 2:
            raise Exception("模拟错误")
        else:
            return "装饰器重试成功!"
    
    print("使用重试装饰器...")
    try:
        result = await decorated_function()
        print(f"✅ 结果: {result}")
    except Exception as e:
        print(f"❌ 失败: {e}")


async def demo_performance_monitoring():
    """演示性能监控"""
    print("\n=== 性能监控演示 ===")
    
    from src.llm.retry_fallback import RetryManager, RetryConfig, ErrorType
    
    # 创建重试管理器
    retry_config = RetryConfig(max_retries=2, base_delay=0.1)
    retry_manager = RetryManager(retry_config)
    
    # 模拟多次调用
    async def mock_api_call():
        await asyncio.sleep(0.1)  # 模拟 API 调用延迟
        if random.random() < 0.3:  # 30% 失败率
            raise Exception("模拟 API 错误")
        return "API 调用成功"
    
    import random
    
    print("执行多次 API 调用...")
    for i in range(10):
        try:
            result = await retry_manager.execute_with_retry(mock_api_call)
            print(f"  调用 {i + 1}: {result}")
        except Exception as e:
            print(f"  调用 {i + 1}: 失败 - {e}")
    
    # 显示性能统计
    stats = retry_manager.get_stats()
    print(f"\n性能统计:")
    print(f"  总请求数: {stats.total_requests}")
    print(f"  成功请求数: {stats.successful_requests}")
    print(f"  失败请求数: {stats.failed_requests}")
    print(f"  成功率: {stats.successful_requests / stats.total_requests * 100:.1f}%")
    print(f"  重试次数: {stats.retry_attempts}")
    print(f"  平均响应时间: {stats.average_response_time:.3f}s")
    print(f"  总重试时间: {stats.total_retry_time:.3f}s")
    
    if stats.error_counts:
        print(f"  错误分布:")
        for error_type, count in stats.error_counts.items():
            print(f"    {error_type.value}: {count} 次")


async def demo_fallback_scenarios():
    """演示降级场景"""
    print("\n=== 降级场景演示 ===")
    
    scenarios = [
        {
            "name": "主要提供商失败，降级到备用",
            "description": "当主要提供商失败时，自动切换到备用提供商"
        },
        {
            "name": "认证错误，需要降级",
            "description": "认证错误通常需要降级到其他提供商"
        },
        {
            "name": "配额超限，需要降级",
            "description": "配额超限时降级到其他提供商"
        },
        {
            "name": "模型不可用，需要降级",
            "description": "特定模型不可用时降级到其他模型"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
    
    print("\n注意: 实际降级需要配置有效的 API 密钥和可用的提供商")


async def main():
    """主函数"""
    print("LLM 调用重试和降级机制演示\n")
    
    # 基础功能演示
    await demo_retry_strategies()
    await demo_error_classification()
    await demo_retry_manager()
    await demo_circuit_breaker()
    
    # 高级功能演示
    await demo_enhanced_llm_manager()
    await demo_retry_decorator()
    await demo_performance_monitoring()
    await demo_fallback_scenarios()
    
    print("\n=== 演示完成 ===")
    print("\n总结:")
    print("1. 支持多种重试策略（指数退避、线性退避、固定延迟、随机退避）")
    print("2. 智能错误分类和处理")
    print("3. 熔断器模式防止级联失败")
    print("4. 自动降级机制确保服务可用性")
    print("5. 详细的性能监控和统计")
    print("6. 装饰器支持简化使用")
    print("7. 灵活的配置选项")


if __name__ == "__main__":
    asyncio.run(main()) 