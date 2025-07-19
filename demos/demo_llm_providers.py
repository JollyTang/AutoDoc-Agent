#!/usr/bin/env python3
"""
LLM 提供商抽象接口演示

演示如何使用统一的 LLM 接口与不同的提供商进行交互。
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.providers import (
    LLMManager, ProviderType, Message, ChatCompletionRequest,
    create_provider, get_api_key_from_keyring, set_api_key_to_keyring,
    get_global_llm_manager
)


def safe_get_api_key(provider_type: ProviderType) -> Optional[str]:
    """安全地获取 API 密钥"""
    try:
        return get_api_key_from_keyring(provider_type)
    except Exception as e:
        print(f"⚠️  获取 {provider_type.value} API 密钥失败: {e}")
        return None


async def demo_openai_provider():
    """演示 OpenAI 提供商"""
    print("=== OpenAI 提供商演示 ===")
    
    # 从 keyring 获取 API 密钥
    api_key = safe_get_api_key(ProviderType.OPENAI)
    if not api_key:
        print("⚠️  未找到 OpenAI API 密钥，跳过演示")
        print("   使用 set_api_key_to_keyring(ProviderType.OPENAI, 'your-api-key') 设置")
        return
    
    try:
        # 创建 OpenAI 提供商
        provider = create_provider(
            provider_type=ProviderType.OPENAI,
            api_key=api_key
        )
        
        # 创建请求
        request = ChatCompletionRequest(
            messages=[
                Message(role="system", content="你是一个有用的编程助手。"),
                Message(role="user", content="请用 Python 写一个简单的计算器函数。")
            ],
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=500
        )
        
        print("发送请求到 OpenAI...")
        response = await provider.chat_completion(request)
        
        print(f"响应 ID: {response.id}")
        print(f"模型: {response.model}")
        print(f"内容: {response.choices[0]['message']['content']}")
        if response.usage:
            print(f"使用量: {response.usage}")
        
        # 健康检查
        is_healthy = await provider.health_check()
        print(f"健康状态: {'✅ 健康' if is_healthy else '❌ 不健康'}")
        
    except Exception as e:
        print(f"❌ OpenAI 演示失败: {e}")


async def demo_claude_provider():
    """演示 Claude 提供商"""
    print("\n=== Claude 提供商演示 ===")
    
    # 从 keyring 获取 API 密钥
    api_key = safe_get_api_key(ProviderType.CLAUDE)
    if not api_key:
        print("⚠️  未找到 Claude API 密钥，跳过演示")
        print("   使用 set_api_key_to_keyring(ProviderType.CLAUDE, 'your-api-key') 设置")
        return
    
    try:
        # 创建 Claude 提供商
        provider = create_provider(
            provider_type=ProviderType.CLAUDE,
            api_key=api_key
        )
        
        # 创建请求
        request = ChatCompletionRequest(
            messages=[
                Message(role="system", content="你是一个专业的代码审查助手。"),
                Message(role="user", content="请审查这段 Python 代码：\n\ndef add(a, b):\n    return a + b")
            ],
            model="claude-3-haiku-20240307",
            temperature=0.3,
            max_tokens=300
        )
        
        print("发送请求到 Claude...")
        response = await provider.chat_completion(request)
        
        print(f"响应 ID: {response.id}")
        print(f"模型: {response.model}")
        print(f"内容: {response.choices[0]['message']['content']}")
        
        # 健康检查
        is_healthy = await provider.health_check()
        print(f"健康状态: {'✅ 健康' if is_healthy else '❌ 不健康'}")
        
    except Exception as e:
        print(f"❌ Claude 演示失败: {e}")


async def demo_ollama_provider():
    """演示 Ollama 提供商"""
    print("\n=== Ollama 提供商演示 ===")
    
    try:
        # 创建 Ollama 提供商
        provider = create_provider(
            provider_type=ProviderType.OLLAMA,
            api_base="http://localhost:11434"  # 默认 Ollama 地址
        )
        
        # 检查 Ollama 是否运行
        is_healthy = await provider.health_check()
        if not is_healthy:
            print("⚠️  Ollama 服务未运行，跳过演示")
            print("   请启动 Ollama 服务：ollama serve")
            return
        
        # 获取可用模型
        models = await provider.list_models()
        print(f"可用模型: {[model['id'] for model in models]}")
        
        if not models:
            print("⚠️  没有可用的 Ollama 模型")
            print("   请安装模型：ollama pull llama2")
            return
        
        # 使用第一个可用模型
        model_name = models[0]['id']
        
        # 创建请求
        request = ChatCompletionRequest(
            messages=[
                Message(role="system", content="你是一个简洁的编程助手。"),
                Message(role="user", content="解释什么是递归函数。")
            ],
            model=model_name,
            temperature=0.5,
            max_tokens=200
        )
        
        print(f"发送请求到 Ollama ({model_name})...")
        response = await provider.chat_completion(request)
        
        print(f"响应 ID: {response.id}")
        print(f"模型: {response.model}")
        print(f"内容: {response.choices[0]['message']['content']}")
        
    except Exception as e:
        print(f"❌ Ollama 演示失败: {e}")


async def demo_llm_manager():
    """演示 LLM 管理器"""
    print("\n=== LLM 管理器演示 ===")
    
    # 获取全局管理器
    manager = get_global_llm_manager()
    
    # 添加提供商
    providers_added = 0
    
    # 尝试添加 OpenAI
    openai_key = safe_get_api_key(ProviderType.OPENAI)
    if openai_key:
        try:
            openai_provider = create_provider(
                provider_type=ProviderType.OPENAI,
                api_key=openai_key
            )
            manager.add_provider(ProviderType.OPENAI, openai_provider)
            providers_added += 1
            print("✅ 添加 OpenAI 提供商")
        except Exception as e:
            print(f"❌ 添加 OpenAI 提供商失败: {e}")
    
    # 尝试添加 Claude
    claude_key = safe_get_api_key(ProviderType.CLAUDE)
    if claude_key:
        try:
            claude_provider = create_provider(
                provider_type=ProviderType.CLAUDE,
                api_key=claude_key
            )
            manager.add_provider(ProviderType.CLAUDE, claude_provider)
            providers_added += 1
            print("✅ 添加 Claude 提供商")
        except Exception as e:
            print(f"❌ 添加 Claude 提供商失败: {e}")
    
    # 尝试添加 Ollama
    try:
        ollama_provider = create_provider(ProviderType.OLLAMA)
        if await ollama_provider.health_check():
            manager.add_provider(ProviderType.OLLAMA, ollama_provider)
            providers_added += 1
            print("✅ 添加 Ollama 提供商")
        else:
            print("⚠️  Ollama 服务未运行，跳过")
    except Exception as e:
        print(f"❌ 添加 Ollama 提供商失败: {e}")
    
    if providers_added == 0:
        print("⚠️  没有可用的提供商")
        return
    
    # 设置默认提供商
    if ProviderType.OPENAI in manager.providers:
        manager.set_default_provider(ProviderType.OPENAI)
        print("✅ 设置 OpenAI 为默认提供商")
    elif ProviderType.CLAUDE in manager.providers:
        manager.set_default_provider(ProviderType.CLAUDE)
        print("✅ 设置 Claude 为默认提供商")
    elif ProviderType.OLLAMA in manager.providers:
        manager.set_default_provider(ProviderType.OLLAMA)
        print("✅ 设置 Ollama 为默认提供商")
    
    # 健康检查所有提供商
    print("\n检查所有提供商健康状态...")
    health_status = await manager.health_check_all()
    for provider_type, is_healthy in health_status.items():
        status = "✅ 健康" if is_healthy else "❌ 不健康"
        print(f"  {provider_type.value}: {status}")
    
    # 使用管理器发送请求
    if manager.default_provider:
        print(f"\n使用默认提供商 ({manager.default_provider.value}) 发送请求...")
        request = ChatCompletionRequest(
            messages=[
                Message(role="system", content="你是一个友好的助手。"),
                Message(role="user", content="请简单介绍一下你自己。")
            ],
            model="gpt-3.5-turbo" if manager.default_provider == ProviderType.OPENAI else "claude-3-haiku-20240307",
            temperature=0.7,
            max_tokens=150
        )
        
        try:
            response = await manager.chat_completion(request)
            print(f"响应: {response.choices[0]['message']['content']}")
        except Exception as e:
            print(f"❌ 请求失败: {e}")


async def demo_streaming():
    """演示流式响应"""
    print("\n=== 流式响应演示 ===")
    
    # 获取可用的提供商
    manager = get_global_llm_manager()
    
    if not manager.default_provider:
        print("⚠️  没有可用的提供商")
        return
    
    provider = manager.providers[manager.default_provider]
    
    # 创建流式请求
    request = ChatCompletionRequest(
        messages=[
            Message(role="system", content="你是一个故事讲述者。"),
            Message(role="user", content="请讲一个关于程序员的小故事。")
        ],
        model="gpt-3.5-turbo" if manager.default_provider == ProviderType.OPENAI else "claude-3-haiku-20240307",
        temperature=0.8,
        max_tokens=200,
        stream=True
    )
    
    print("开始流式响应...")
    print("内容: ", end="", flush=True)
    
    try:
        async for chunk in provider.chat_completion_stream(request):
            if chunk.choices and chunk.choices[0].get('delta', {}).get('content'):
                content = chunk.choices[0]['delta']['content']
                print(content, end="", flush=True)
        print()  # 换行
    except Exception as e:
        print(f"\n❌ 流式请求失败: {e}")


async def demo_api_key_management():
    """演示 API 密钥管理"""
    print("\n=== API 密钥管理演示 ===")
    
    # 检查现有的 API 密钥
    print("检查现有的 API 密钥:")
    
    openai_key = safe_get_api_key(ProviderType.OPENAI)
    if openai_key:
        print(f"  OpenAI: {'*' * (len(openai_key) - 4) + openai_key[-4:]}")
    else:
        print("  OpenAI: 未设置")
    
    claude_key = safe_get_api_key(ProviderType.CLAUDE)
    if claude_key:
        print(f"  Claude: {'*' * (len(claude_key) - 4) + claude_key[-4:]}")
    else:
        print("  Claude: 未设置")
    
    print("\n要设置 API 密钥，请使用:")
    print("  set_api_key_to_keyring(ProviderType.OPENAI, 'your-openai-api-key')")
    print("  set_api_key_to_keyring(ProviderType.CLAUDE, 'your-claude-api-key')")


async def demo_provider_interface():
    """演示提供商接口的基本功能"""
    print("\n=== 提供商接口演示 ===")
    
    # 演示创建提供商
    print("1. 创建提供商实例...")
    try:
        # 创建 OpenAI 提供商（不需要 API 密钥来演示接口）
        provider = create_provider(
            provider_type=ProviderType.OPENAI,
            api_key="dummy-key"
        )
        print("✅ 成功创建 OpenAI 提供商")
        
        # 演示消息格式化
        messages = [
            Message(role="system", content="你是一个助手。"),
            Message(role="user", content="你好！")
        ]
        formatted = provider._format_messages(messages)
        print(f"✅ 消息格式化: {formatted}")
        
        # 演示模型名称获取
        model_name = provider.get_model_name("gpt-3.5-turbo")
        print(f"✅ 模型名称: {model_name}")
        
    except Exception as e:
        print(f"❌ 提供商接口演示失败: {e}")


async def main():
    """主函数"""
    print("LLM 提供商抽象接口演示\n")
    
    # 基本接口演示
    await demo_provider_interface()
    
    # API 密钥管理演示
    await demo_api_key_management()
    
    # 各个提供商演示
    await demo_openai_provider()
    await demo_claude_provider()
    await demo_ollama_provider()
    
    # LLM 管理器演示
    await demo_llm_manager()
    
    # 流式响应演示
    await demo_streaming()
    
    print("\n=== 演示完成 ===")
    print("\n总结:")
    print("1. 统一的 LLM 接口支持多个提供商")
    print("2. 自动重试和故障转移机制")
    print("3. 安全的 API 密钥管理")
    print("4. 支持流式和非流式响应")
    print("5. 健康检查和监控")


if __name__ == "__main__":
    asyncio.run(main()) 