"""
LLM 提供商抽象接口的单元测试

测试 LLM 提供商的核心功能和接口。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

from src.llm.providers import (
    LLMProvider, OpenAIProvider, ClaudeProvider, OllamaProvider,
    LLMManager, ProviderType, Message, ChatCompletionRequest,
    ChatCompletionResponse, ChatCompletionChunk, ProviderConfig,
    create_provider, get_global_llm_manager
)


class TestProviderConfig:
    """测试提供商配置"""
    
    def test_provider_config_creation(self):
        """测试提供商配置创建"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            api_base="https://test.api.com",
            timeout=60,
            max_retries=5
        )
        
        assert config.provider_type == ProviderType.OPENAI
        assert config.api_key == "test-key"
        assert config.api_base == "https://test.api.com"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 1.0
        assert config.model_mapping == {}


class TestMessage:
    """测试消息类"""
    
    def test_message_creation(self):
        """测试消息创建"""
        message = Message(
            role="user",
            content="Hello, world!",
            name="test_user"
        )
        
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.name == "test_user"
    
    def test_message_without_name(self):
        """测试没有名称的消息"""
        message = Message(role="system", content="You are a helpful assistant.")
        
        assert message.role == "system"
        assert message.content == "You are a helpful assistant."
        assert message.name is None


class TestChatCompletionRequest:
    """测试聊天完成请求"""
    
    def test_request_creation(self):
        """测试请求创建"""
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!")
        ]
        
        request = ChatCompletionRequest(
            messages=messages,
            model="gpt-3.5-turbo",
            temperature=0.8,
            max_tokens=100
        )
        
        assert request.messages == messages
        assert request.model == "gpt-3.5-turbo"
        assert request.temperature == 0.8
        assert request.max_tokens == 100
        assert request.top_p == 1.0
        assert request.frequency_penalty == 0.0
        assert request.presence_penalty == 0.0
        assert request.stream is False
        assert request.stop is None


class TestLLMProvider:
    """测试 LLM 提供商基类"""
    
    def test_provider_initialization(self):
        """测试提供商初始化"""
        config = ProviderConfig(provider_type=ProviderType.OPENAI)
        
        # 使用 OpenAIProvider 作为具体实现
        provider = OpenAIProvider(config)
        
        assert provider.config == config
        assert provider.api_base == "https://api.openai.com/v1"
        assert provider.client is not None
    
    def test_format_messages(self):
        """测试消息格式化"""
        config = ProviderConfig(provider_type=ProviderType.OPENAI)
        provider = OpenAIProvider(config)
        
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!", name="user1")
        ]
        
        formatted = provider._format_messages(messages)
        
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are a helpful assistant."
        assert "name" not in formatted[0]
        
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "Hello!"
        assert formatted[1]["name"] == "user1"
    
    def test_create_system_message(self):
        """测试创建系统消息"""
        config = ProviderConfig(provider_type=ProviderType.OPENAI)
        provider = OpenAIProvider(config)
        
        message = provider._create_system_message("You are a helpful assistant.")
        
        assert message.role == "system"
        assert message.content == "You are a helpful assistant."
        assert message.name is None


class TestOpenAIProvider:
    """测试 OpenAI 提供商"""
    
    def test_openai_provider_creation(self):
        """测试 OpenAI 提供商创建"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key"
        )
        
        provider = OpenAIProvider(config)
        
        assert provider.api_base == "https://api.openai.com/v1"
        assert provider.config.api_key == "test-key"
    
    def test_get_model_name(self):
        """测试模型名称获取"""
        config = ProviderConfig(provider_type=ProviderType.OPENAI)
        provider = OpenAIProvider(config)
        
        # 测试默认模型名称
        assert provider.get_model_name("gpt-3.5-turbo") == "gpt-3.5-turbo"
        
        # 测试模型映射
        config.model_mapping = {"gpt-3.5": "gpt-3.5-turbo"}
        provider = OpenAIProvider(config)
        assert provider.get_model_name("gpt-3.5") == "gpt-3.5-turbo"


class TestClaudeProvider:
    """测试 Claude 提供商"""
    
    def test_claude_provider_creation(self):
        """测试 Claude 提供商创建"""
        config = ProviderConfig(
            provider_type=ProviderType.CLAUDE,
            api_key="test-key"
        )
        
        provider = ClaudeProvider(config)
        
        assert provider.api_base == "https://api.anthropic.com/v1"
        assert provider.config.api_key == "test-key"
    
    def test_get_model_name(self):
        """测试模型名称获取"""
        config = ProviderConfig(
            provider_type=ProviderType.CLAUDE,
            api_key="test-key"  # 添加 API 密钥
        )
        provider = ClaudeProvider(config)
        
        assert provider.get_model_name("claude-3-haiku") == "claude-3-haiku"
        
        # 测试模型映射
        config.model_mapping = {"claude": "claude-3-haiku-20240307"}
        provider = ClaudeProvider(config)
        assert provider.get_model_name("claude") == "claude-3-haiku-20240307"


class TestOllamaProvider:
    """测试 Ollama 提供商"""
    
    def test_ollama_provider_creation(self):
        """测试 Ollama 提供商创建"""
        config = ProviderConfig(provider_type=ProviderType.OLLAMA)
        
        provider = OllamaProvider(config)
        
        assert provider.api_base == "http://localhost:11434"
    
    def test_ollama_provider_custom_base(self):
        """测试 Ollama 提供商自定义基础 URL"""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_base="http://custom.ollama.com:11434"
        )
        
        provider = OllamaProvider(config)
        
        assert provider.api_base == "http://custom.ollama.com:11434"
    
    def test_get_model_name(self):
        """测试模型名称获取"""
        config = ProviderConfig(provider_type=ProviderType.OLLAMA)
        provider = OllamaProvider(config)
        
        assert provider.get_model_name("llama2") == "llama2"
        
        # 测试模型映射
        config.model_mapping = {"llama": "llama2"}
        provider = OllamaProvider(config)
        assert provider.get_model_name("llama") == "llama2"


class TestLLMManager:
    """测试 LLM 管理器"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        manager = LLMManager()
        
        assert manager.providers == {}
        assert manager.default_provider is None
    
    def test_add_provider(self):
        """测试添加提供商"""
        manager = LLMManager()
        config = ProviderConfig(provider_type=ProviderType.OPENAI)
        provider = OpenAIProvider(config)
        
        manager.add_provider(ProviderType.OPENAI, provider)
        
        assert ProviderType.OPENAI in manager.providers
        assert manager.providers[ProviderType.OPENAI] == provider
        assert manager.default_provider == ProviderType.OPENAI
    
    def test_set_default_provider(self):
        """测试设置默认提供商"""
        manager = LLMManager()
        config = ProviderConfig(provider_type=ProviderType.OPENAI)
        provider = OpenAIProvider(config)
        
        manager.add_provider(ProviderType.OPENAI, provider)
        manager.set_default_provider(ProviderType.OPENAI)
        
        assert manager.default_provider == ProviderType.OPENAI
    
    def test_set_default_provider_not_found(self):
        """测试设置不存在的默认提供商"""
        manager = LLMManager()
        
        with pytest.raises(ValueError, match="提供商 ProviderType.OPENAI 未注册"):
            manager.set_default_provider(ProviderType.OPENAI)


class TestCreateProvider:
    """测试创建提供商函数"""
    
    def test_create_openai_provider(self):
        """测试创建 OpenAI 提供商"""
        provider = create_provider(
            provider_type=ProviderType.OPENAI,
            api_key="test-key"
        )
        
        assert isinstance(provider, OpenAIProvider)
        assert provider.config.api_key == "test-key"
        assert provider.api_base == "https://api.openai.com/v1"
    
    def test_create_claude_provider(self):
        """测试创建 Claude 提供商"""
        provider = create_provider(
            provider_type=ProviderType.CLAUDE,
            api_key="test-key"
        )
        
        assert isinstance(provider, ClaudeProvider)
        assert provider.config.api_key == "test-key"
        assert provider.api_base == "https://api.anthropic.com/v1"
    
    def test_create_ollama_provider(self):
        """测试创建 Ollama 提供商"""
        provider = create_provider(
            provider_type=ProviderType.OLLAMA,
            api_base="http://custom.ollama.com:11434"
        )
        
        assert isinstance(provider, OllamaProvider)
        assert provider.api_base == "http://custom.ollama.com:11434"
    
    def test_create_unknown_provider(self):
        """测试创建未知提供商"""
        with pytest.raises(ValueError, match="不支持的提供商类型"):
            create_provider(provider_type="unknown")


class TestGlobalLLMManager:
    """测试全局 LLM 管理器"""
    
    def test_get_global_manager(self):
        """测试获取全局管理器"""
        manager = get_global_llm_manager()
        
        assert isinstance(manager, LLMManager)
        assert manager.providers == {}
        assert manager.default_provider is None
    
    def test_global_manager_singleton(self):
        """测试全局管理器单例模式"""
        manager1 = get_global_llm_manager()
        manager2 = get_global_llm_manager()
        
        assert manager1 is manager2


@pytest.mark.asyncio
class TestAsyncProviderMethods:
    """测试异步提供商方法"""
    
    @pytest.fixture
    def mock_response(self):
        """模拟响应"""
        response = MagicMock()
        response.json.return_value = {
            "id": "test-id",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello, I'm a test response!"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        return response
    
    async def test_openai_chat_completion(self, mock_response):
        """测试 OpenAI 聊天完成"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key"
        )
        provider = OpenAIProvider(config)
        
        # 模拟 HTTP 客户端
        mock_client = AsyncMock()
        mock_client.post.return_value.__aenter__.return_value = mock_response
        mock_response.raise_for_status = MagicMock()  # 添加这行
        provider.client = mock_client
        
        request = ChatCompletionRequest(
            messages=[Message(role="user", content="Hello!")],
            model="gpt-3.5-turbo"
        )
        
        response = await provider.chat_completion(request)
        
        assert response.id == "test-id"
        assert response.model == "gpt-3.5-turbo"
        assert response.choices[0]["message"]["content"] == "Hello, I'm a test response!"
        assert response.usage["total_tokens"] == 30
    
    async def test_provider_health_check_success(self):
        """测试提供商健康检查成功"""
        config = ProviderConfig(provider_type=ProviderType.OPENAI)
        provider = OpenAIProvider(config)
        
        # 模拟成功的模型列表请求
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-3.5-turbo"}]}
        mock_response.raise_for_status = MagicMock()  # 添加这行
        mock_client.get.return_value.__aenter__.return_value = mock_response
        provider.client = mock_client
        
        is_healthy = await provider.health_check()
        
        assert is_healthy is True
    
    async def test_provider_health_check_failure(self):
        """测试提供商健康检查失败"""
        config = ProviderConfig(provider_type=ProviderType.OPENAI)
        provider = OpenAIProvider(config)
        
        # 模拟失败的请求
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection failed")
        provider.client = mock_client
        
        is_healthy = await provider.health_check()
        
        assert is_healthy is False


if __name__ == "__main__":
    pytest.main([__file__]) 