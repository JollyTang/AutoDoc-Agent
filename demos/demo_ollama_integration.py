#!/usr/bin/env python3
"""
Ollama 本地 OSS 模型集成演示

演示 Ollama 本地模型的功能，包括：
- 聊天完成
- 文本生成
- 文本嵌入
- 模型管理
- 系统信息
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.providers import (
    ProviderType, Message, ChatCompletionRequest,
    get_global_llm_manager
)
from src.llm.ollama_integration import (
    EnhancedOllamaProvider, OllamaEmbeddingRequest, OllamaGenerateRequest,
    OllamaModel, OllamaSystemInfo, create_enhanced_ollama_provider,
    get_ollama_embedding, generate_ollama_text, list_ollama_models,
    pull_ollama_model, get_ollama_system_info
)


def check_ollama_connection(api_base: str = "http://localhost:11434") -> bool:
    """检查 Ollama 连接状态"""
    try:
        import httpx
        import asyncio
        
        async def check():
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{api_base}/api/tags")
                return response.status_code == 200
        
        return asyncio.run(check())
    except Exception:
        return False


async def demo_ollama_connection():
    """演示 Ollama 连接检查"""
    print("=== Ollama 连接检查 ===")
    
    api_base = "http://localhost:11434"
    is_connected = check_ollama_connection(api_base)
    
    if is_connected:
        print("✅ Ollama 服务连接正常")
        return True
    else:
        print("❌ Ollama 服务连接失败")
        print("请确保 Ollama 服务正在运行：")
        print("1. 安装 Ollama: https://ollama.ai/")
        print("2. 启动服务: ollama serve")
        print("3. 拉取模型: ollama pull llama2")
        return False


async def demo_ollama_chat():
    """演示 Ollama 聊天功能"""
    print("\n=== Ollama 聊天演示 ===")
    
    try:
        provider = create_enhanced_ollama_provider()
        
        # 创建聊天请求
        request = ChatCompletionRequest(
            messages=[
                Message(role="system", content="你是一个有用的 AI 助手。"),
                Message(role="user", content="请用中文简单介绍一下人工智能。")
            ],
            model="llama2",
            max_tokens=200,
            temperature=0.7
        )
        
        print("发送聊天请求...")
        response = await provider.chat_completion(request)
        
        print(f"响应 ID: {response.id}")
        print(f"模型: {response.model}")
        print(f"内容: {response.choices[0]['message']['content']}")
        
        # 流式响应演示
        print("\n演示流式响应...")
        request.stream = True
        
        print("流式内容: ", end="", flush=True)
        async for chunk in provider.chat_completion_stream(request):
            if chunk.choices[0].get("delta", {}).get("content"):
                print(chunk.choices[0]["delta"]["content"], end="", flush=True)
        print()  # 换行
        
    except Exception as e:
        print(f"❌ Ollama 聊天演示失败: {e}")


async def demo_ollama_text_generation():
    """演示 Ollama 文本生成功能"""
    print("\n=== Ollama 文本生成演示 ===")
    
    try:
        provider = create_enhanced_ollama_provider()
        
        # 创建文本生成请求
        request = OllamaGenerateRequest(
            model="llama2",
            prompt="写一个关于春天的短诗",
            system="你是一个富有诗意的诗人。",
            options={"temperature": 0.8, "top_p": 0.9}
        )
        
        print("生成文本...")
        response = await provider.generate_text(request)
        
        print(f"模型: {response.model}")
        print(f"响应: {response.response}")
        print(f"完成: {response.done}")
        if response.total_duration:
            print(f"总耗时: {response.total_duration}ms")
        
        # 使用便捷函数
        print("\n使用便捷函数生成文本...")
        text = await generate_ollama_text(
            prompt="解释什么是机器学习",
            model="llama2",
            system="你是一个技术专家。"
        )
        print(f"便捷函数结果: {text[:200]}...")
        
    except Exception as e:
        print(f"❌ Ollama 文本生成演示失败: {e}")


async def demo_ollama_embeddings():
    """演示 Ollama 嵌入功能"""
    print("\n=== Ollama 嵌入演示 ===")
    
    try:
        provider = create_enhanced_ollama_provider()
        
        # 创建嵌入请求
        request = OllamaEmbeddingRequest(
            model="llama2",
            prompt="这是一个测试句子"
        )
        
        print("创建嵌入...")
        response = await provider.create_embedding(request)
        
        print(f"嵌入维度: {len(response.embedding)}")
        print(f"前5个值: {response.embedding[:5]}")
        
        # 使用便捷函数
        print("\n使用便捷函数创建嵌入...")
        embedding = await get_ollama_embedding(
            text="另一个测试句子",
            model="llama2"
        )
        print(f"便捷函数嵌入维度: {len(embedding)}")
        
    except Exception as e:
        print(f"❌ Ollama 嵌入演示失败: {e}")


async def demo_ollama_model_management():
    """演示 Ollama 模型管理功能"""
    print("\n=== Ollama 模型管理演示 ===")
    
    try:
        provider = create_enhanced_ollama_provider()
        
        # 获取模型列表
        print("获取模型列表...")
        models = await provider.list_models_detailed()
        
        print(f"找到 {len(models)} 个模型:")
        for model in models:
            print(f"  - 名称: {model.name}")
            print(f"    大小: {model.size / (1024*1024*1024):.2f} GB")
            print(f"    修改时间: {model.modified_at}")
            if model.details:
                print(f"    参数: {model.details.parameters}")
            print()
        
        # 获取特定模型信息
        if models:
            first_model = models[0]
            print(f"获取模型 {first_model.name} 的详细信息...")
            try:
                model_info = await provider.get_model_info(first_model.name)
                print(f"许可证: {model_info.license}")
                print(f"模板: {model_info.template[:100] if model_info.template else '无'}...")
                print(f"系统提示: {model_info.system[:100] if model_info.system else '无'}...")
            except Exception as e:
                print(f"获取模型信息失败: {e}")
        
        # 使用便捷函数
        print("\n使用便捷函数获取模型列表...")
        models_list = await list_ollama_models()
        print(f"便捷函数找到 {len(models_list)} 个模型")
        
    except Exception as e:
        print(f"❌ Ollama 模型管理演示失败: {e}")


async def demo_ollama_system_info():
    """演示 Ollama 系统信息功能"""
    print("\n=== Ollama 系统信息演示 ===")
    
    try:
        provider = create_enhanced_ollama_provider()
        
        # 获取系统信息
        print("获取系统信息...")
        system_info = await provider.get_system_info()
        
        print(f"版本: {system_info.version}")
        print(f"库: {system_info.library}")
        print(f"CPU 数量: {system_info.num_cpu}")
        print(f"GPU 数量: {system_info.num_gpu}")
        print(f"GPU 层数: {system_info.gpu_layers}")
        print(f"总内存: {system_info.total_memory / (1024*1024*1024):.2f} GB")
        print(f"可用内存: {system_info.free_memory / (1024*1024*1024):.2f} GB")
        print(f"已用内存: {system_info.used_memory / (1024*1024*1024):.2f} GB")
        
        # 使用便捷函数
        print("\n使用便捷函数获取系统信息...")
        sys_info = await get_ollama_system_info()
        print(f"便捷函数版本: {sys_info.version}")
        
    except Exception as e:
        print(f"❌ Ollama 系统信息演示失败: {e}")


async def demo_ollama_model_operations():
    """演示 Ollama 模型操作功能"""
    print("\n=== Ollama 模型操作演示 ===")
    
    try:
        provider = create_enhanced_ollama_provider()
        
        # 注意：这些操作可能需要较长时间，这里只演示接口
        print("模型操作功能:")
        print("1. 拉取模型: provider.pull_model('llama2')")
        print("2. 删除模型: provider.delete_model('model_name')")
        print("3. 复制模型: provider.copy_model('source', 'destination')")
        print("4. 创建模型: provider.create_model('name', 'modelfile_content')")
        
        # 演示拉取模型（注释掉以避免意外下载）
        # print("\n演示拉取模型...")
        # result = await provider.pull_model("llama2")
        # print(f"拉取结果: {result}")
        
        # 使用便捷函数
        print("\n使用便捷函数拉取模型（演示）...")
        print("pull_ollama_model('llama2') - 需要较长时间")
        
    except Exception as e:
        print(f"❌ Ollama 模型操作演示失败: {e}")


async def demo_ollama_integration_with_manager():
    """演示 Ollama 与 LLM 管理器的集成"""
    print("\n=== Ollama 与 LLM 管理器集成演示 ===")
    
    try:
        # 获取全局 LLM 管理器
        manager = get_global_llm_manager()
        
        # 创建 Ollama 提供商
        ollama_provider = create_enhanced_ollama_provider()
        
        # 添加到管理器
        manager.add_provider(ProviderType.OLLAMA, ollama_provider)
        manager.set_default_provider(ProviderType.OLLAMA)
        
        print("Ollama 提供商已添加到 LLM 管理器")
        
        # 使用管理器发送请求
        request = ChatCompletionRequest(
            messages=[
                Message(role="user", content="简单介绍一下 Python 编程语言")
            ],
            model="llama2",
            max_tokens=150
        )
        
        print("通过管理器发送请求...")
        response = await manager.chat_completion(request)
        
        print(f"响应: {response.choices[0]['message']['content'][:200]}...")
        
        # 检查健康状态
        print("\n检查提供商健康状态...")
        health_status = await manager.health_check_all()
        for provider_type, is_healthy in health_status.items():
            status = "✅ 健康" if is_healthy else "❌ 不健康"
            print(f"  {provider_type.value}: {status}")
        
    except Exception as e:
        print(f"❌ Ollama 与 LLM 管理器集成演示失败: {e}")


async def demo_ollama_popular_models():
    """演示 Ollama 热门模型"""
    print("\n=== Ollama 热门模型介绍 ===")
    
    popular_models = {
        "llama2": {
            "description": "Meta 的 Llama 2 模型，通用性强",
            "size": "3.8GB",
            "use_case": "通用对话、文本生成"
        },
        "codellama": {
            "description": "专门用于代码生成的模型",
            "size": "3.8GB",
            "use_case": "代码生成、编程助手"
        },
        "mistral": {
            "description": "Mistral AI 的高性能模型",
            "size": "4.1GB",
            "use_case": "推理、分析、创意写作"
        },
        "gemma": {
            "description": "Google 的轻量级模型",
            "size": "2.5GB",
            "use_case": "快速响应、资源受限环境"
        },
        "phi": {
            "description": "Microsoft 的小型高效模型",
            "size": "1.7GB",
            "use_case": "快速推理、移动设备"
        }
    }
    
    print("热门 Ollama 模型:")
    for model_name, info in popular_models.items():
        print(f"\n{model_name}:")
        print(f"  描述: {info['description']}")
        print(f"  大小: {info['size']}")
        print(f"  用途: {info['use_case']}")
        print(f"  拉取命令: ollama pull {model_name}")
    
    print("\n安装建议:")
    print("1. 首次使用建议安装 llama2: ollama pull llama2")
    print("2. 编程需求建议安装 codellama: ollama pull codellama")
    print("3. 性能优先建议安装 mistral: ollama pull mistral")
    print("4. 资源受限环境建议安装 gemma: ollama pull gemma")


async def main():
    """主函数"""
    print("Ollama 本地 OSS 模型集成演示\n")
    
    # 检查连接
    is_connected = await demo_ollama_connection()
    
    if not is_connected:
        print("\n⚠️  由于 Ollama 服务未连接，以下演示将跳过")
        print("请先启动 Ollama 服务后再运行演示")
        return
    
    # 基础功能演示
    await demo_ollama_chat()
    await demo_ollama_text_generation()
    await demo_ollama_embeddings()
    
    # 管理功能演示
    await demo_ollama_model_management()
    await demo_ollama_system_info()
    await demo_ollama_model_operations()
    
    # 集成演示
    await demo_ollama_integration_with_manager()
    
    # 模型介绍
    await demo_ollama_popular_models()
    
    print("\n=== 演示完成 ===")
    print("\n总结:")
    print("1. Ollama 提供了强大的本地 OSS 模型支持")
    print("2. 支持多种热门模型（Llama2、CodeLlama、Mistral 等）")
    print("3. 完整的模型管理功能（拉取、删除、复制等）")
    print("4. 与 LLM 管理器完美集成，支持故障转移")
    print("5. 本地部署，保护隐私，降低成本")
    print("6. 支持嵌入向量和文本生成功能")


if __name__ == "__main__":
    asyncio.run(main()) 