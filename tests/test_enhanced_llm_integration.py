"""
增强的 LLM 集成测试

测试 OpenAI 和 Claude API 的增强功能。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

from src.llm.providers import ProviderType, ProviderConfig
from src.llm.openai_integration import (
    EnhancedOpenAIProvider, OpenAIEmbeddingRequest, OpenAIImageGenerationRequest,
    create_enhanced_openai_provider, get_openai_embedding, generate_openai_image
)
from src.llm.claude_integration import (
    EnhancedClaudeProvider, ClaudeRequest, ClaudeMessage, ClaudeContentBlock,
    ClaudeTool, create_enhanced_claude_provider, create_claude_tool,
    analyze_image_with_claude, call_claude_tool
)


class TestEnhancedOpenAIProvider:
    """测试增强的 OpenAI 提供商"""
    
    def test_enhanced_openai_provider_creation(self):
        """测试增强的 OpenAI 提供商创建"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key"
        )
        
        provider = EnhancedOpenAIProvider(config)
        
        assert isinstance(provider, EnhancedOpenAIProvider)
        assert provider.api_base == "https://api.openai.com/v1"
        assert provider.config.api_key == "test-key"
    
    @pytest.mark.asyncio
    async def test_create_embedding(self):
        """测试创建嵌入"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key"
        )
        provider = EnhancedOpenAIProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1, 0.2, 0.3],
                    "index": 0
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {
                "prompt_tokens": 5,
                "total_tokens": 5
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.post.return_value.__aenter__.return_value = mock_response
        provider.client = mock_client
        
        request = OpenAIEmbeddingRequest(
            input="测试文本",
            model="text-embedding-ada-002"
        )
        
        response = await provider.create_embedding(request)
        
        assert response.object == "list"
        assert response.model == "text-embedding-ada-002"
        assert len(response.data) == 1
        assert response.data[0]["embedding"] == [0.1, 0.2, 0.3]
        assert response.usage["total_tokens"] == 5
    
    @pytest.mark.asyncio
    async def test_generate_image(self):
        """测试生成图像"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key"
        )
        provider = EnhancedOpenAIProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "created": 1234567890,
            "data": [
                {
                    "url": "https://example.com/image.jpg",
                    "revised_prompt": "修改后的提示"
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.post.return_value.__aenter__.return_value = mock_response
        provider.client = mock_client
        
        request = OpenAIImageGenerationRequest(
            prompt="测试图像",
            model="dall-e-3"
        )
        
        response = await provider.generate_image(request)
        
        assert response.created == 1234567890
        assert len(response.data) == 1
        assert response.data[0]["url"] == "https://example.com/image.jpg"
    
    @pytest.mark.asyncio
    async def test_list_fine_tuning_jobs(self):
        """测试获取微调任务列表"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key"
        )
        provider = EnhancedOpenAIProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "ft-job-123",
                    "object": "fine_tuning.job",
                    "model": "gpt-3.5-turbo",
                    "created_at": 1234567890,
                    "finished_at": None,
                    "fine_tuned_model": None,
                    "organization_id": "org-123",
                    "result_files": [],
                    "status": "running",
                    "validation_file": None,
                    "training_file": "file-123",
                    "trained_tokens": None,
                    "error": None,
                    "hyperparameters": {
                        "n_epochs": 3
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.get.return_value.__aenter__.return_value = mock_response
        provider.client = mock_client
        
        jobs = await provider.list_fine_tuning_jobs()
        
        assert len(jobs) == 1
        assert jobs[0].id == "ft-job-123"
        assert jobs[0].model == "gpt-3.5-turbo"
        assert jobs[0].status == "running"


class TestEnhancedClaudeProvider:
    """测试增强的 Claude 提供商"""
    
    def test_enhanced_claude_provider_creation(self):
        """测试增强的 Claude 提供商创建"""
        config = ProviderConfig(
            provider_type=ProviderType.CLAUDE,
            api_key="test-key"
        )
        
        provider = EnhancedClaudeProvider(config)
        
        assert isinstance(provider, EnhancedClaudeProvider)
        assert provider.api_base == "https://api.anthropic.com/v1"
        assert provider.config.api_key == "test-key"
    
    def test_format_claude_messages(self):
        """测试格式化 Claude 消息"""
        config = ProviderConfig(
            provider_type=ProviderType.CLAUDE,
            api_key="test-key"
        )
        provider = EnhancedClaudeProvider(config)
        
        from src.llm.providers import Message
        
        messages = [
            Message(role="system", content="系统提示"),
            Message(role="user", content="用户消息"),
            Message(role="assistant", content="助手回复")
        ]
        
        claude_messages = provider._format_claude_messages(messages)
        
        assert len(claude_messages) == 2  # 系统消息被过滤
        assert claude_messages[0].role == "user"
        assert claude_messages[0].content == "用户消息"
        assert claude_messages[1].role == "assistant"
        assert claude_messages[1].content == "助手回复"
    
    @pytest.mark.asyncio
    async def test_chat_completion_enhanced(self):
        """测试增强的聊天完成"""
        config = ProviderConfig(
            provider_type=ProviderType.CLAUDE,
            api_key="test-key"
        )
        provider = EnhancedClaudeProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "msg-123",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "这是一个测试回复"
                }
            ],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.post.return_value.__aenter__.return_value = mock_response
        provider.client = mock_client
        
        request = ClaudeRequest(
            model="claude-3-sonnet-20240229",
            messages=[
                ClaudeMessage(
                    role="user",
                    content="测试消息"
                )
            ]
        )
        
        response = await provider.chat_completion_enhanced(request)
        
        assert response.id == "msg-123"
        assert response.model == "claude-3-sonnet-20240229"
        assert response.stop_reason == "end_turn"
        assert len(response.content) == 1
        assert response.content[0].type == "text"
        assert response.content[0].text == "这是一个测试回复"
    
    @pytest.mark.asyncio
    async def test_analyze_image(self):
        """测试图像分析"""
        config = ProviderConfig(
            provider_type=ProviderType.CLAUDE,
            api_key="test-key"
        )
        provider = EnhancedClaudeProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "msg-123",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "这是一张图像的分析结果"
                }
            ],
            "model": "claude-3-vision-20240229",
            "stop_reason": "end_turn"
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.post.return_value.__aenter__.return_value = mock_response
        provider.client = mock_client
        
        response = await provider.analyze_image(
            image_url="data:image/jpeg;base64,test",
            prompt="分析这张图像",
            model="claude-3-vision-20240229"
        )
        
        assert response.id == "msg-123"
        assert response.model == "claude-3-vision-20240229"
        assert len(response.content) == 1
        assert response.content[0].text == "这是一张图像的分析结果"
    
    @pytest.mark.asyncio
    async def test_call_tool(self):
        """测试工具调用"""
        config = ProviderConfig(
            provider_type=ProviderType.CLAUDE,
            api_key="test-key"
        )
        provider = EnhancedClaudeProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "msg-123",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "工具调用结果"
                }
            ],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn"
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.post.return_value.__aenter__.return_value = mock_response
        provider.client = mock_client
        
        tool = ClaudeTool(
            name="test_tool",
            description="测试工具",
            input_schema={"type": "object"}
        )
        
        messages = [
            ClaudeMessage(
                role="user",
                content="调用测试工具"
            )
        ]
        
        response = await provider.call_tool(messages, [tool])
        
        assert response.id == "msg-123"
        assert response.model == "claude-3-sonnet-20240229"
        assert len(response.content) == 1
        assert response.content[0].text == "工具调用结果"


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    @pytest.mark.asyncio
    async def test_create_enhanced_openai_provider(self):
        """测试创建增强的 OpenAI 提供商"""
        provider = create_enhanced_openai_provider(
            api_key="test-key",
            api_base="https://test.api.com"
        )
        
        assert isinstance(provider, EnhancedOpenAIProvider)
        assert provider.config.api_key == "test-key"
        assert provider.api_base == "https://test.api.com"
    
    @pytest.mark.asyncio
    async def test_create_enhanced_claude_provider(self):
        """测试创建增强的 Claude 提供商"""
        provider = create_enhanced_claude_provider(
            api_key="test-key",
            api_base="https://test.api.com"
        )
        
        assert isinstance(provider, EnhancedClaudeProvider)
        assert provider.config.api_key == "test-key"
        assert provider.api_base == "https://test.api.com"
    
    @pytest.mark.asyncio
    async def test_get_openai_embedding(self):
        """测试获取 OpenAI 嵌入"""
        with patch('src.llm.openai_integration.create_enhanced_openai_provider') as mock_create:
            mock_provider = AsyncMock()
            mock_provider.create_embedding.return_value = MagicMock(
                data=[{"embedding": [0.1, 0.2, 0.3]}]
            )
            mock_create.return_value = mock_provider
            
            embeddings = await get_openai_embedding(
                "测试文本",
                "test-key"
            )
            
            assert embeddings == [[0.1, 0.2, 0.3]]
    
    @pytest.mark.asyncio
    async def test_generate_openai_image(self):
        """测试生成 OpenAI 图像"""
        with patch('src.llm.openai_integration.create_enhanced_openai_provider') as mock_create:
            mock_provider = AsyncMock()
            mock_provider.generate_image.return_value = MagicMock(
                data=[{"url": "https://example.com/image.jpg"}]
            )
            mock_create.return_value = mock_provider
            
            urls = await generate_openai_image(
                "测试图像",
                "test-key"
            )
            
            assert urls == ["https://example.com/image.jpg"]
    
    @pytest.mark.asyncio
    async def test_analyze_image_with_claude(self):
        """测试使用 Claude 分析图像"""
        with patch('src.llm.claude_integration.create_enhanced_claude_provider') as mock_create:
            mock_provider = AsyncMock()
            mock_provider.analyze_image.return_value = MagicMock(
                content=[
                    MagicMock(type="text", text="图像分析结果")
                ]
            )
            mock_create.return_value = mock_provider
            
            result = await analyze_image_with_claude(
                "data:image/jpeg;base64,test",
                "分析图像",
                "test-key"
            )
            
            assert result == "图像分析结果"
    
    @pytest.mark.asyncio
    async def test_call_claude_tool(self):
        """测试调用 Claude 工具"""
        with patch('src.llm.claude_integration.create_enhanced_claude_provider') as mock_create:
            mock_provider = AsyncMock()
            mock_provider.call_tool.return_value = MagicMock(
                id="msg-123",
                model="claude-3-sonnet-20240229"
            )
            mock_create.return_value = mock_provider
            
            tool = ClaudeTool(
                name="test_tool",
                description="测试工具",
                input_schema={"type": "object"}
            )
            
            messages = [
                ClaudeMessage(
                    role="user",
                    content="测试消息"
                )
            ]
            
            result = await call_claude_tool(messages, [tool], "test-key")
            
            assert result.id == "msg-123"
            assert result.model == "claude-3-sonnet-20240229"
    
    def test_create_claude_tool(self):
        """测试创建 Claude 工具"""
        tool = create_claude_tool(
            name="test_tool",
            description="测试工具",
            input_schema={"type": "object", "properties": {}}
        )
        
        assert isinstance(tool, ClaudeTool)
        assert tool.name == "test_tool"
        assert tool.description == "测试工具"
        assert tool.input_schema["type"] == "object"


class TestDataStructures:
    """测试数据结构"""
    
    def test_openai_embedding_request(self):
        """测试 OpenAI 嵌入请求"""
        request = OpenAIEmbeddingRequest(
            input=["文本1", "文本2"],
            model="text-embedding-ada-002",
            encoding_format="float"
        )
        
        assert request.input == ["文本1", "文本2"]
        assert request.model == "text-embedding-ada-002"
        assert request.encoding_format == "float"
    
    def test_openai_image_generation_request(self):
        """测试 OpenAI 图像生成请求"""
        request = OpenAIImageGenerationRequest(
            prompt="生成图像",
            model="dall-e-3",
            size="1024x1024"
        )
        
        assert request.prompt == "生成图像"
        assert request.model == "dall-e-3"
        assert request.size == "1024x1024"
    
    def test_claude_message(self):
        """测试 Claude 消息"""
        message = ClaudeMessage(
            role="user",
            content="测试消息"
        )
        
        assert message.role == "user"
        assert message.content == "测试消息"
    
    def test_claude_content_block(self):
        """测试 Claude 内容块"""
        block = ClaudeContentBlock(
            type="text",
            text="文本内容"
        )
        
        assert block.type == "text"
        assert block.text == "文本内容"
    
    def test_claude_tool(self):
        """测试 Claude 工具"""
        tool = ClaudeTool(
            name="test_tool",
            description="测试工具",
            input_schema={"type": "object"}
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "测试工具"
        assert tool.input_schema["type"] == "object"
    
    def test_claude_request(self):
        """测试 Claude 请求"""
        request = ClaudeRequest(
            model="claude-3-sonnet-20240229",
            messages=[
                ClaudeMessage(role="user", content="测试")
            ],
            max_tokens=1000
        )
        
        assert request.model == "claude-3-sonnet-20240229"
        assert len(request.messages) == 1
        assert request.max_tokens == 1000


if __name__ == "__main__":
    pytest.main([__file__]) 