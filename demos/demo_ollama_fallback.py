#!/usr/bin/env python3
"""
Ollama 降级处理演示

演示当 Ollama 本地服务不可用时的降级处理机制，包括：
- 自动检测 Ollama 可用性
- 回退到 OpenAI 服务
- 优雅的错误处理
- 用户友好的提示信息
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.ollama_integration import (
    check_ollama_availability, get_ollama_embedding, generate_ollama_text,
    list_ollama_models, get_ollama_installation_guide, OllamaNotAvailableError
)
from src.llm.providers import get_api_key_from_keyring, ProviderType


async def demo_ollama_availability_check():
    """演示 Ollama 可用性检查"""
    print("=== Ollama 可用性检查 ===")
    
    is_available = check_ollama_availability()
    
    if is_available:
        print("✅ Ollama 服务可用")
        print("可以使用本地 OSS 模型进行 AI 任务")
    else:
        print("❌ Ollama 服务不可用")
        print("将使用云端 AI 服务作为替代")
    
    return is_available


async def demo_ollama_embedding_with_fallback():
    """演示带降级的嵌入功能"""
    print("\n=== 嵌入功能演示（带降级） ===")
    
    try:
        print("尝试获取文本嵌入...")
        embedding = await get_ollama_embedding(
            text="这是一个测试句子，用于演示嵌入功能",
            model="llama2",
            fallback_to_openai=True
        )
        
        print(f"✅ 成功获取嵌入向量，维度: {len(embedding)}")
        print(f"前5个值: {embedding[:5]}")
        
    except OllamaNotAvailableError as e:
        print(f"❌ Ollama 不可用: {e}")
        print("建议:")
        print("1. 安装并启动 Ollama 服务")
        print("2. 或者配置 OpenAI API 密钥作为回退")
        
    except Exception as e:
        print(f"❌ 其他错误: {e}")


async def demo_ollama_text_generation_with_fallback():
    """演示带降级的文本生成功能"""
    print("\n=== 文本生成功能演示（带降级） ===")
    
    try:
        print("尝试生成文本...")
        text = await generate_ollama_text(
            prompt="请用中文简单介绍一下人工智能",
            model="llama2",
            system="你是一个技术专家",
            fallback_to_openai=True
        )
        
        print(f"✅ 成功生成文本:")
        print(f"内容: {text[:200]}...")
        
    except OllamaNotAvailableError as e:
        print(f"❌ Ollama 不可用: {e}")
        print("建议:")
        print("1. 安装并启动 Ollama 服务")
        print("2. 或者配置 OpenAI API 密钥作为回退")
        
    except Exception as e:
        print(f"❌ 其他错误: {e}")


async def demo_ollama_model_management_with_fallback():
    """演示模型管理功能（无降级）"""
    print("\n=== 模型管理功能演示 ===")
    
    try:
        print("尝试获取模型列表...")
        models = await list_ollama_models()
        
        print(f"✅ 成功获取 {len(models)} 个模型:")
        for model in models:
            print(f"  - {model.name} ({model.size / (1024*1024*1024):.1f} GB)")
        
    except OllamaNotAvailableError as e:
        print(f"❌ Ollama 不可用: {e}")
        print("模型管理功能需要本地 Ollama 服务")
        print("请先安装并启动 Ollama")
        
    except Exception as e:
        print(f"❌ 其他错误: {e}")


async def demo_api_key_check():
    """演示 API 密钥检查"""
    print("\n=== API 密钥检查 ===")
    
    # 检查 OpenAI API 密钥
    openai_key = get_api_key_from_keyring(ProviderType.OPENAI)
    if openai_key:
        print("✅ OpenAI API 密钥已配置")
        print("可以作为 Ollama 的回退服务")
    else:
        print("❌ OpenAI API 密钥未配置")
        print("无法使用 OpenAI 作为回退服务")
        print("建议配置 OpenAI API 密钥以提供更好的降级支持")
    
    # 检查 Claude API 密钥
    claude_key = get_api_key_from_keyring(ProviderType.CLAUDE)
    if claude_key:
        print("✅ Claude API 密钥已配置")
    else:
        print("❌ Claude API 密钥未配置")


async def demo_installation_guide():
    """演示安装指南"""
    print("\n=== Ollama 安装指南 ===")
    
    guide = get_ollama_installation_guide()
    print(guide)


async def demo_error_handling_scenarios():
    """演示各种错误处理场景"""
    print("\n=== 错误处理场景演示 ===")
    
    scenarios = [
        {
            "name": "Ollama 不可用，无回退",
            "fallback": False,
            "description": "强制使用 Ollama，不允许回退"
        },
        {
            "name": "Ollama 不可用，有回退",
            "fallback": True,
            "description": "允许回退到 OpenAI"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n场景: {scenario['name']}")
        print(f"描述: {scenario['description']}")
        
        try:
            embedding = await get_ollama_embedding(
                text="测试文本",
                fallback_to_openai=scenario["fallback"]
            )
            print(f"✅ 成功: 获取到 {len(embedding)} 维嵌入向量")
        except OllamaNotAvailableError as e:
            print(f"❌ 预期错误: {e}")
        except Exception as e:
            print(f"❌ 意外错误: {e}")


async def demo_graceful_degradation():
    """演示优雅降级"""
    print("\n=== 优雅降级演示 ===")
    
    print("1. 检查 Ollama 可用性...")
    ollama_available = check_ollama_availability()
    
    print("2. 检查 API 密钥配置...")
    openai_available = get_api_key_from_keyring(ProviderType.OPENAI) is not None
    claude_available = get_api_key_from_keyring(ProviderType.CLAUDE) is not None
    
    print("3. 确定可用的 AI 服务...")
    available_services = []
    
    if ollama_available:
        available_services.append("Ollama (本地)")
    if openai_available:
        available_services.append("OpenAI (云端)")
    if claude_available:
        available_services.append("Claude (云端)")
    
    if not available_services:
        print("❌ 没有可用的 AI 服务")
        print("建议:")
        print("1. 安装 Ollama 进行本地 AI 处理")
        print("2. 或者配置 OpenAI/Claude API 密钥")
        return
    
    print(f"✅ 可用的 AI 服务: {', '.join(available_services)}")
    
    # 根据可用服务选择最佳策略
    if ollama_available:
        print("🎯 推荐策略: 使用本地 Ollama 服务")
        print("优势: 隐私保护、无成本、离线可用")
    elif openai_available:
        print("🎯 推荐策略: 使用 OpenAI 服务")
        print("优势: 功能完整、性能稳定")
    elif claude_available:
        print("🎯 推荐策略: 使用 Claude 服务")
        print("优势: 长文本处理、图像分析")
    
    print("\n4. 执行 AI 任务...")
    try:
        if ollama_available:
            print("使用 Ollama 生成文本...")
            text = await generate_ollama_text(
                prompt="解释什么是机器学习",
                fallback_to_openai=False
            )
        elif openai_available:
            print("使用 OpenAI 生成文本...")
            from src.llm.providers import create_provider, Message, ChatCompletionRequest
            provider = create_provider(ProviderType.OPENAI, api_key=get_api_key_from_keyring(ProviderType.OPENAI))
            request = ChatCompletionRequest(
                messages=[Message(role="user", content="解释什么是机器学习")],
                model="gpt-3.5-turbo"
            )
            response = await provider.chat_completion(request)
            text = response.choices[0]["message"]["content"]
        else:
            print("使用 Claude 生成文本...")
            from src.llm.providers import create_provider, Message, ChatCompletionRequest
            provider = create_provider(ProviderType.CLAUDE, api_key=get_api_key_from_keyring(ProviderType.CLAUDE))
            request = ChatCompletionRequest(
                messages=[Message(role="user", content="解释什么是机器学习")],
                model="claude-3-haiku-20240307"
            )
            response = await provider.chat_completion(request)
            text = response.choices[0]["message"]["content"]
        
        print(f"✅ 成功生成文本: {text[:100]}...")
        
    except Exception as e:
        print(f"❌ 任务执行失败: {e}")


async def main():
    """主函数"""
    print("Ollama 降级处理演示\n")
    
    # 基础检查
    await demo_ollama_availability_check()
    await demo_api_key_check()
    
    # 功能演示
    await demo_ollama_embedding_with_fallback()
    await demo_ollama_text_generation_with_fallback()
    await demo_ollama_model_management_with_fallback()
    
    # 错误处理
    await demo_error_handling_scenarios()
    
    # 优雅降级
    await demo_graceful_degradation()
    
    # 安装指南
    await demo_installation_guide()
    
    print("\n=== 演示完成 ===")
    print("\n总结:")
    print("1. 项目会自动检测 Ollama 可用性")
    print("2. 当 Ollama 不可用时，会尝试回退到云端服务")
    print("3. 提供详细的错误信息和解决建议")
    print("4. 支持多种 AI 服务的优雅降级")
    print("5. 确保项目在任何环境下都能正常工作")


if __name__ == "__main__":
    asyncio.run(main()) 