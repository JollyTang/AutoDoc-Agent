#!/usr/bin/env python3
"""
增强的 LLM 集成演示

演示 OpenAI 和 Claude API 的增强功能，包括：
- 文本嵌入
- 图像生成
- 图像分析
- 工具调用
- 微调管理
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
    get_api_key_from_keyring
)
from src.llm.openai_integration import (
    EnhancedOpenAIProvider, OpenAIEmbeddingRequest, OpenAIImageGenerationRequest,
    create_enhanced_openai_provider, get_openai_embedding, generate_openai_image
)
from src.llm.claude_integration import (
    EnhancedClaudeProvider, ClaudeRequest, ClaudeMessage, ClaudeContentBlock,
    ClaudeTool, create_enhanced_claude_provider, create_claude_tool,
    analyze_image_with_claude, call_claude_tool
)


def safe_get_api_key(provider_type: ProviderType) -> Optional[str]:
    """安全地获取 API 密钥"""
    try:
        return get_api_key_from_keyring(provider_type)
    except Exception as e:
        print(f"⚠️  获取 {provider_type.value} API 密钥失败: {e}")
        return None


async def demo_openai_embeddings():
    """演示 OpenAI 文本嵌入功能"""
    print("=== OpenAI 文本嵌入演示 ===")
    
    api_key = safe_get_api_key(ProviderType.OPENAI)
    if not api_key:
        print("⚠️  未找到 OpenAI API 密钥，跳过演示")
        return
    
    try:
        provider = create_enhanced_openai_provider(api_key)
        
        # 创建嵌入请求
        request = OpenAIEmbeddingRequest(
            input=["这是一个测试句子", "这是另一个测试句子"],
            model="text-embedding-ada-002"
        )
        
        print("发送嵌入请求...")
        response = await provider.create_embedding(request)
        
        print(f"嵌入模型: {response.model}")
        print(f"嵌入数量: {len(response.data)}")
        print(f"第一个嵌入向量维度: {len(response.data[0]['embedding'])}")
        print(f"使用量: {response.usage}")
        
        # 使用便捷函数
        print("\n使用便捷函数获取嵌入...")
        embeddings = await get_openai_embedding(
            "这是一个简单的测试文本",
            api_key
        )
        print(f"便捷函数嵌入维度: {len(embeddings[0])}")
        
    except Exception as e:
        print(f"❌ OpenAI 嵌入演示失败: {e}")


async def demo_openai_image_generation():
    """演示 OpenAI 图像生成功能"""
    print("\n=== OpenAI 图像生成演示 ===")
    
    api_key = safe_get_api_key(ProviderType.OPENAI)
    if not api_key:
        print("⚠️  未找到 OpenAI API 密钥，跳过演示")
        return
    
    try:
        provider = create_enhanced_openai_provider(api_key)
        
        # 创建图像生成请求
        request = OpenAIImageGenerationRequest(
            prompt="一只可爱的小猫坐在电脑前编程，卡通风格",
            model="dall-e-3",
            size="1024x1024",
            quality="standard"
        )
        
        print("生成图像...")
        response = await provider.generate_image(request)
        
        print(f"创建时间: {response.created}")
        print(f"图像数量: {len(response.data)}")
        for i, image_data in enumerate(response.data):
            print(f"图像 {i+1} URL: {image_data['url']}")
        
        # 使用便捷函数
        print("\n使用便捷函数生成图像...")
        image_urls = await generate_openai_image(
            "一个美丽的日落场景",
            api_key,
            size="1024x1024"
        )
        print(f"便捷函数生成图像 URL: {image_urls[0]}")
        
    except Exception as e:
        print(f"❌ OpenAI 图像生成演示失败: {e}")


async def demo_openai_fine_tuning():
    """演示 OpenAI 微调功能"""
    print("\n=== OpenAI 微调管理演示 ===")
    
    api_key = safe_get_api_key(ProviderType.OPENAI)
    if not api_key:
        print("⚠️  未找到 OpenAI API 密钥，跳过演示")
        return
    
    try:
        provider = create_enhanced_openai_provider(api_key)
        
        # 获取微调任务列表
        print("获取微调任务列表...")
        jobs = await provider.list_fine_tuning_jobs(limit=5)
        
        print(f"找到 {len(jobs)} 个微调任务:")
        for job in jobs:
            print(f"  - ID: {job.id}")
            print(f"    模型: {job.model}")
            print(f"    状态: {job.status}")
            print(f"    创建时间: {job.created_at}")
            if job.fine_tuned_model:
                print(f"    微调模型: {job.fine_tuned_model}")
            print()
        
        # 获取文件列表
        print("获取文件列表...")
        files = await provider.list_files()
        
        print(f"找到 {len(files)} 个文件:")
        for file_info in files[:3]:  # 只显示前3个
            print(f"  - ID: {file_info['id']}")
            print(f"    文件名: {file_info['filename']}")
            print(f"    用途: {file_info['purpose']}")
            print(f"    大小: {file_info['bytes']} 字节")
            print()
        
        # 获取使用情况
        print("获取使用情况...")
        usage = await provider.get_usage()
        print(f"使用情况: {usage}")
        
    except Exception as e:
        print(f"❌ OpenAI 微调演示失败: {e}")


async def demo_claude_image_analysis():
    """演示 Claude 图像分析功能"""
    print("\n=== Claude 图像分析演示 ===")
    
    api_key = safe_get_api_key(ProviderType.CLAUDE)
    if not api_key:
        print("⚠️  未找到 Claude API 密钥，跳过演示")
        return
    
    try:
        provider = create_enhanced_claude_provider(api_key)
        
        # 注意：这里使用一个示例图像 URL，实际使用时需要替换为真实的图像
        image_url = "https://example.com/sample-image.jpg"
        
        print("分析图像...")
        response = await provider.analyze_image(
            image_url=image_url,
            prompt="请描述这张图像中的内容，包括主要对象、颜色、场景等。",
            model="claude-3-vision-20240229"
        )
        
        print(f"响应 ID: {response.id}")
        print(f"模型: {response.model}")
        print(f"停止原因: {response.stop_reason}")
        
        # 提取文本内容
        text_content = ""
        for block in response.content:
            if block.type == "text" and block.text:
                text_content += block.text
        
        print(f"分析结果: {text_content[:200]}...")
        
        # 使用便捷函数
        print("\n使用便捷函数分析图像...")
        try:
            result = await analyze_image_with_claude(
                image_url=image_url,
                prompt="这张图像是什么风格的艺术作品？",
                api_key=api_key
            )
            print(f"便捷函数结果: {result[:200]}...")
        except Exception as e:
            print(f"便捷函数失败: {e}")
        
    except Exception as e:
        print(f"❌ Claude 图像分析演示失败: {e}")


async def demo_claude_tool_calling():
    """演示 Claude 工具调用功能"""
    print("\n=== Claude 工具调用演示 ===")
    
    api_key = safe_get_api_key(ProviderType.CLAUDE)
    if not api_key:
        print("⚠️  未找到 Claude API 密钥，跳过演示")
        return
    
    try:
        provider = create_enhanced_claude_provider(api_key)
        
        # 创建工具定义
        weather_tool = create_claude_tool(
            name="get_weather",
            description="获取指定城市的天气信息",
            input_schema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    },
                    "country": {
                        "type": "string",
                        "description": "国家代码（可选）"
                    }
                },
                "required": ["city"]
            }
        )
        
        calculator_tool = create_claude_tool(
            name="calculate",
            description="执行数学计算",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式"
                    }
                },
                "required": ["expression"]
            }
        )
        
        tools = [weather_tool, calculator_tool]
        
        # 创建消息
        messages = [
            ClaudeMessage(
                role="user",
                content="请帮我获取北京的天气信息，然后计算 15 * 23 的结果。"
            )
        ]
        
        print("调用工具...")
        response = await provider.call_tool(messages, tools)
        
        print(f"响应 ID: {response.id}")
        print(f"模型: {response.model}")
        print(f"停止原因: {response.stop_reason}")
        
        # 提取工具调用内容
        tool_calls = []
        for block in response.content:
            if block.type == "text" and block.text:
                print(f"文本内容: {block.text}")
        
        # 使用便捷函数
        print("\n使用便捷函数调用工具...")
        try:
            result = await call_claude_tool(messages, tools, api_key)
            print(f"便捷函数响应 ID: {result.id}")
        except Exception as e:
            print(f"便捷函数失败: {e}")
        
    except Exception as e:
        print(f"❌ Claude 工具调用演示失败: {e}")


async def demo_claude_enhanced_chat():
    """演示 Claude 增强聊天功能"""
    print("\n=== Claude 增强聊天演示 ===")
    
    api_key = safe_get_api_key(ProviderType.CLAUDE)
    if not api_key:
        print("⚠️  未找到 Claude API 密钥，跳过演示")
        return
    
    try:
        provider = create_enhanced_claude_provider(api_key)
        
        # 创建增强的 Claude 请求
        request = ClaudeRequest(
            model="claude-3-sonnet-20240229",
            messages=[
                ClaudeMessage(
                    role="user",
                    content="请用中文写一个关于人工智能的简短故事。"
                )
            ],
            max_tokens=300,
            temperature=0.8,
            system="你是一个富有创造力的故事讲述者。"
        )
        
        print("发送增强聊天请求...")
        response = await provider.chat_completion_enhanced(request)
        
        print(f"响应 ID: {response.id}")
        print(f"模型: {response.model}")
        print(f"停止原因: {response.stop_reason}")
        
        # 提取文本内容
        text_content = ""
        for block in response.content:
            if block.type == "text" and block.text:
                text_content += block.text
        
        print(f"故事内容: {text_content}")
        
        # 流式响应演示
        print("\n演示流式响应...")
        request.stream = True
        
        print("流式内容: ", end="", flush=True)
        async for chunk in provider.chat_completion_stream_enhanced(request):
            if chunk.type == "content_block_delta" and chunk.delta and "text" in chunk.delta:
                print(chunk.delta["text"], end="", flush=True)
        print()  # 换行
        
    except Exception as e:
        print(f"❌ Claude 增强聊天演示失败: {e}")


async def demo_provider_comparison():
    """演示不同提供商的比较"""
    print("\n=== 提供商功能比较 ===")
    
    openai_key = safe_get_api_key(ProviderType.OPENAI)
    claude_key = safe_get_api_key(ProviderType.CLAUDE)
    
    print("功能对比表:")
    print("功能                    | OpenAI | Claude")
    print("------------------------|--------|--------")
    print("聊天完成                |   ✅   |   ✅   ")
    print("流式响应                |   ✅   |   ✅   ")
    print("文本嵌入                |   ✅   |   ❌   ")
    print("图像生成                |   ✅   |   ❌   ")
    print("图像分析                |   ❌   |   ✅   ")
    print("工具调用                |   ✅   |   ✅   ")
    print("微调管理                |   ✅   |   ❌   ")
    print("文件管理                |   ✅   |   ❌   ")
    print("使用统计                |   ✅   |   ❌   ")
    
    print("\n模型对比:")
    print("OpenAI 模型:")
    print("  - GPT-3.5-turbo (聊天)")
    print("  - GPT-4 (高级聊天)")
    print("  - GPT-4-turbo (最新)")
    print("  - text-embedding-ada-002 (嵌入)")
    print("  - dall-e-3 (图像生成)")
    
    print("\nClaude 模型:")
    print("  - claude-3-haiku (快速)")
    print("  - claude-3-sonnet (平衡)")
    print("  - claude-3-opus (最强)")
    print("  - claude-3-vision (视觉)")
    
    print("\n建议使用场景:")
    print("OpenAI 适合:")
    print("  - 需要文本嵌入的应用")
    print("  - 图像生成需求")
    print("  - 模型微调")
    print("  - 文件处理")
    
    print("Claude 适合:")
    print("  - 图像分析任务")
    print("  - 长文本处理")
    print("  - 代码生成")
    print("  - 复杂推理")


async def main():
    """主函数"""
    print("增强的 LLM 集成演示\n")
    
    # OpenAI 功能演示
    await demo_openai_embeddings()
    await demo_openai_image_generation()
    await demo_openai_fine_tuning()
    
    # Claude 功能演示
    await demo_claude_image_analysis()
    await demo_claude_tool_calling()
    await demo_claude_enhanced_chat()
    
    # 提供商比较
    await demo_provider_comparison()
    
    print("\n=== 演示完成 ===")
    print("\n总结:")
    print("1. OpenAI 提供全面的 AI 服务，包括文本、图像、嵌入等")
    print("2. Claude 在图像分析和长文本处理方面表现优秀")
    print("3. 两个提供商都支持工具调用和流式响应")
    print("4. 可以根据具体需求选择合适的提供商")
    print("5. 增强的集成模块提供了更多高级功能")


if __name__ == "__main__":
    asyncio.run(main()) 