"""
Ollama 集成模块的单元测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.llm.ollama_integration import (
    EnhancedOllamaProvider, OllamaEmbeddingRequest, OllamaEmbeddingResponse,
    OllamaGenerateRequest, OllamaGenerateResponse, OllamaModelInfo,
    OllamaModel, OllamaSystemInfo, create_enhanced_ollama_provider,
    get_ollama_embedding, generate_ollama_text, list_ollama_models,
    pull_ollama_model, get_ollama_system_info
)
from src.llm.providers import ProviderConfig, ProviderType


class TestEnhancedOllamaProvider:
    """增强的 Ollama 提供商测试"""
    
    def test_enhanced_ollama_provider_creation(self):
        """测试增强的 Ollama 提供商创建"""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_base="http://localhost:11434"
        )
        
        provider = EnhancedOllamaProvider(config)
        
        assert provider.config.provider_type == ProviderType.OLLAMA
        assert provider.config.api_base == "http://localhost:11434"
        assert provider.logger is not None
    
    @pytest.mark.asyncio
    async def test_create_embedding(self):
        """测试创建嵌入"""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_base="http://localhost:11434"
        )
        
        provider = EnhancedOllamaProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        
        with patch.object(provider, 'client', mock_client):
            request = OllamaEmbeddingRequest(
                model="llama2",
                prompt="测试文本"
            )
            
            response = await provider.create_embedding(request)
            
            assert isinstance(response, OllamaEmbeddingResponse)
            assert len(response.embedding) == 5
            assert response.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    @pytest.mark.asyncio
    async def test_generate_text(self):
        """测试文本生成"""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_base="http://localhost:11434"
        )
        
        provider = EnhancedOllamaProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "model": "llama2",
            "created_at": "2024-01-01T00:00:00Z",
            "response": "生成的文本内容",
            "done": True,
            "total_duration": 1000,
            "eval_count": 50
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        
        with patch.object(provider, 'client', mock_client):
            request = OllamaGenerateRequest(
                model="llama2",
                prompt="测试提示",
                system="系统提示"
            )
            
            response = await provider.generate_text(request)
            
            assert isinstance(response, OllamaGenerateResponse)
            assert response.model == "llama2"
            assert response.response == "生成的文本内容"
            assert response.done is True
            assert response.total_duration == 1000
            assert response.eval_count == 50
    
    @pytest.mark.asyncio
    async def test_get_model_info(self):
        """测试获取模型信息"""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_base="http://localhost:11434"
        )
        
        provider = EnhancedOllamaProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "license": "MIT",
            "modelfile": "FROM llama2",
            "parameters": "7B",
            "template": "{{ .Prompt }}",
            "system": "系统提示",
            "digest": "sha256:abc123"
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        
        with patch.object(provider, 'client', mock_client):
            model_info = await provider.get_model_info("llama2")
            
            assert isinstance(model_info, OllamaModelInfo)
            assert model_info.license == "MIT"
            assert model_info.modelfile == "FROM llama2"
            assert model_info.parameters == "7B"
            assert model_info.template == "{{ .Prompt }}"
            assert model_info.system == "系统提示"
            assert model_info.digest == "sha256:abc123"
    
    @pytest.mark.asyncio
    async def test_list_models_detailed(self):
        """测试获取详细模型列表"""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_base="http://localhost:11434"
        )
        
        provider = EnhancedOllamaProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama2",
                    "modified_at": "2024-01-01T00:00:00Z",
                    "size": 4000000000,
                    "digest": "sha256:abc123"
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        
        with patch.object(provider, 'client', mock_client):
            models = await provider.list_models_detailed()
            
            assert len(models) == 1
            assert isinstance(models[0], OllamaModel)
            assert models[0].name == "llama2"
            assert models[0].size == 4000000000
            assert models[0].digest == "sha256:abc123"
    
    @pytest.mark.asyncio
    async def test_pull_model(self):
        """测试拉取模型"""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_base="http://localhost:11434"
        )
        
        provider = EnhancedOllamaProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        
        with patch.object(provider, 'client', mock_client):
            result = await provider.pull_model("llama2")
            
            assert result == {"status": "success"}
    
    @pytest.mark.asyncio
    async def test_get_system_info(self):
        """测试获取系统信息"""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_base="http://localhost:11434"
        )
        
        provider = EnhancedOllamaProvider(config)
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "version": "0.1.0",
            "library": "ollama",
            "num_cpu": 8,
            "num_gpu": 1,
            "gpu_layers": 35,
            "total_memory": 16000000000,
            "free_memory": 8000000000,
            "used_memory": 8000000000
        }
        mock_response.raise_for_status = MagicMock()
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        
        with patch.object(provider, 'client', mock_client):
            system_info = await provider.get_system_info()
            
            assert isinstance(system_info, OllamaSystemInfo)
            assert system_info.version == "0.1.0"
            assert system_info.library == "ollama"
            assert system_info.num_cpu == 8
            assert system_info.num_gpu == 1
            assert system_info.gpu_layers == 35
            assert system_info.total_memory == 16000000000


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    @pytest.mark.asyncio
    async def test_create_enhanced_ollama_provider(self):
        """测试创建增强的 Ollama 提供商便捷函数"""
        provider = create_enhanced_ollama_provider(
            api_base="http://localhost:11434"
        )
        
        assert isinstance(provider, EnhancedOllamaProvider)
        assert provider.config.api_base == "http://localhost:11434"
        assert provider.config.provider_type == ProviderType.OLLAMA
    
    @pytest.mark.asyncio
    async def test_get_ollama_embedding(self):
        """测试获取 Ollama 嵌入便捷函数"""
        # 模拟提供商
        mock_provider = AsyncMock()
        mock_response = OllamaEmbeddingResponse(embedding=[0.1, 0.2, 0.3])
        mock_provider.create_embedding.return_value = mock_response
        
        with patch('src.llm.ollama_integration.create_enhanced_ollama_provider', return_value=mock_provider):
            embedding = await get_ollama_embedding(
                text="测试文本",
                model="llama2"
            )
            
            assert embedding == [0.1, 0.2, 0.3]
            mock_provider.create_embedding.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_ollama_text(self):
        """测试生成 Ollama 文本便捷函数"""
        # 模拟提供商
        mock_provider = AsyncMock()
        mock_response = OllamaGenerateResponse(
            model="llama2",
            created_at="2024-01-01T00:00:00Z",
            response="生成的文本",
            done=True
        )
        mock_provider.generate_text.return_value = mock_response
        
        with patch('src.llm.ollama_integration.create_enhanced_ollama_provider', return_value=mock_provider):
            text = await generate_ollama_text(
                prompt="测试提示",
                model="llama2",
                system="系统提示"
            )
            
            assert text == "生成的文本"
            mock_provider.generate_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_ollama_models(self):
        """测试获取 Ollama 模型列表便捷函数"""
        # 模拟提供商
        mock_provider = AsyncMock()
        mock_models = [
            OllamaModel(
                name="llama2",
                modified_at="2024-01-01T00:00:00Z",
                size=4000000000,
                digest="sha256:abc123"
            )
        ]
        mock_provider.list_models_detailed.return_value = mock_models
        
        with patch('src.llm.ollama_integration.create_enhanced_ollama_provider', return_value=mock_provider):
            models = await list_ollama_models()
            
            assert len(models) == 1
            assert models[0].name == "llama2"
            mock_provider.list_models_detailed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pull_ollama_model(self):
        """测试拉取 Ollama 模型便捷函数"""
        # 模拟提供商
        mock_provider = AsyncMock()
        mock_result = {"status": "success"}
        mock_provider.pull_model.return_value = mock_result
        
        with patch('src.llm.ollama_integration.create_enhanced_ollama_provider', return_value=mock_provider):
            result = await pull_ollama_model("llama2")
            
            assert result == {"status": "success"}
            mock_provider.pull_model.assert_called_once_with("llama2", False)
    
    @pytest.mark.asyncio
    async def test_get_ollama_system_info(self):
        """测试获取 Ollama 系统信息便捷函数"""
        # 模拟提供商
        mock_provider = AsyncMock()
        mock_system_info = OllamaSystemInfo(
            total_memory=16000000000,
            free_memory=8000000000,
            used_memory=8000000000,
            num_cpu=8,
            num_gpu=1,
            gpu_layers=35,
            library="ollama",
            version="0.1.0"
        )
        mock_provider.get_system_info.return_value = mock_system_info
        
        with patch('src.llm.ollama_integration.create_enhanced_ollama_provider', return_value=mock_provider):
            system_info = await get_ollama_system_info()
            
            assert system_info.version == "0.1.0"
            assert system_info.num_cpu == 8
            mock_provider.get_system_info.assert_called_once()


class TestDataStructures:
    """数据结构测试"""
    
    def test_ollama_embedding_request(self):
        """测试 Ollama 嵌入请求数据结构"""
        request = OllamaEmbeddingRequest(
            model="llama2",
            prompt="测试文本",
            options={"temperature": 0.7}
        )
        
        assert request.model == "llama2"
        assert request.prompt == "测试文本"
        assert request.options == {"temperature": 0.7}
    
    def test_ollama_embedding_response(self):
        """测试 Ollama 嵌入响应数据结构"""
        response = OllamaEmbeddingResponse(
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
        )
        
        assert len(response.embedding) == 5
        assert response.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    def test_ollama_generate_request(self):
        """测试 Ollama 文本生成请求数据结构"""
        request = OllamaGenerateRequest(
            model="llama2",
            prompt="测试提示",
            system="系统提示",
            options={"temperature": 0.8},
            stream=False
        )
        
        assert request.model == "llama2"
        assert request.prompt == "测试提示"
        assert request.system == "系统提示"
        assert request.options == {"temperature": 0.8}
        assert request.stream is False
    
    def test_ollama_generate_response(self):
        """测试 Ollama 文本生成响应数据结构"""
        response = OllamaGenerateResponse(
            model="llama2",
            created_at="2024-01-01T00:00:00Z",
            response="生成的文本",
            done=True,
            total_duration=1000,
            eval_count=50
        )
        
        assert response.model == "llama2"
        assert response.response == "生成的文本"
        assert response.done is True
        assert response.total_duration == 1000
        assert response.eval_count == 50
    
    def test_ollama_model_info(self):
        """测试 Ollama 模型信息数据结构"""
        model_info = OllamaModelInfo(
            license="MIT",
            modelfile="FROM llama2",
            parameters="7B",
            template="{{ .Prompt }}",
            system="系统提示"
        )
        
        assert model_info.license == "MIT"
        assert model_info.modelfile == "FROM llama2"
        assert model_info.parameters == "7B"
        assert model_info.template == "{{ .Prompt }}"
        assert model_info.system == "系统提示"
    
    def test_ollama_model(self):
        """测试 Ollama 模型数据结构"""
        model = OllamaModel(
            name="llama2",
            modified_at="2024-01-01T00:00:00Z",
            size=4000000000,
            digest="sha256:abc123"
        )
        
        assert model.name == "llama2"
        assert model.size == 4000000000
        assert model.digest == "sha256:abc123"
    
    def test_ollama_system_info(self):
        """测试 Ollama 系统信息数据结构"""
        system_info = OllamaSystemInfo(
            total_memory=16000000000,
            free_memory=8000000000,
            used_memory=8000000000,
            num_cpu=8,
            num_gpu=1,
            gpu_layers=35,
            library="ollama",
            version="0.1.0"
        )
        
        assert system_info.total_memory == 16000000000
        assert system_info.num_cpu == 8
        assert system_info.num_gpu == 1
        assert system_info.library == "ollama"
        assert system_info.version == "0.1.0" 