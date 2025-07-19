"""
Ollama 本地 OSS 模型集成模块

提供完整的 Ollama 本地模型集成功能，包括：
- 聊天完成
- 文本生成
- 模型管理
- 嵌入向量
- 模型拉取和删除
- 系统信息
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, Field

from .providers import (
    OllamaProvider, ProviderType, Message, ChatCompletionRequest,
    ChatCompletionResponse, ChatCompletionChunk, ProviderConfig
)

logger = logging.getLogger(__name__)


@dataclass
class OllamaEmbeddingRequest:
    """Ollama 嵌入请求"""
    model: str
    prompt: str
    options: Optional[Dict[str, Any]] = None


@dataclass
class OllamaEmbeddingResponse:
    """Ollama 嵌入响应"""
    embedding: List[float]


@dataclass
class OllamaGenerateRequest:
    """Ollama 文本生成请求"""
    model: str
    prompt: str
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[List[int]] = None
    options: Optional[Dict[str, Any]] = None
    format: Optional[str] = None
    stream: bool = False
    raw: bool = False
    keep_alive: Optional[str] = None


@dataclass
class OllamaGenerateResponse:
    """Ollama 文本生成响应"""
    model: str
    created_at: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


@dataclass
class OllamaModelInfo:
    """Ollama 模型信息"""
    license: Optional[str] = None
    modelfile: Optional[str] = None
    parameters: Optional[str] = None
    template: Optional[str] = None
    system: Optional[str] = None
    digest: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class OllamaModel:
    """Ollama 模型"""
    name: str
    modified_at: str
    size: int
    digest: str
    details: Optional[OllamaModelInfo] = None


@dataclass
class OllamaSystemInfo:
    """Ollama 系统信息"""
    total_memory: int
    free_memory: int
    used_memory: int
    num_cpu: int
    num_gpu: int
    gpu_layers: int
    library: str
    version: str


class EnhancedOllamaProvider(OllamaProvider):
    """
    增强的 Ollama 提供商
    
    提供更完整的 Ollama 本地模型功能。
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.EnhancedOllamaProvider")
    
    async def create_embedding(
        self, 
        request: OllamaEmbeddingRequest
    ) -> OllamaEmbeddingResponse:
        """
        创建文本嵌入
        
        Args:
            request: 嵌入请求
            
        Returns:
            嵌入响应
        """
        url = "/api/embeddings"
        payload = {
            "model": self.get_model_name(request.model),
            "prompt": request.prompt
        }
        
        if request.options:
            payload["options"] = request.options
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return OllamaEmbeddingResponse(
                embedding=data["embedding"]
            )
    
    async def generate_text(
        self, 
        request: OllamaGenerateRequest
    ) -> OllamaGenerateResponse:
        """
        生成文本
        
        Args:
            request: 文本生成请求
            
        Returns:
            文本生成响应
        """
        url = "/api/generate"
        payload = {
            "model": self.get_model_name(request.model),
            "prompt": request.prompt,
            "stream": False
        }
        
        if request.system:
            payload["system"] = request.system
        if request.template:
            payload["template"] = request.template
        if request.context:
            payload["context"] = request.context
        if request.options:
            payload["options"] = request.options
        if request.format:
            payload["format"] = request.format
        if request.raw:
            payload["raw"] = request.raw
        if request.keep_alive:
            payload["keep_alive"] = request.keep_alive
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return OllamaGenerateResponse(
                model=data["model"],
                created_at=data["created_at"],
                response=data["response"],
                done=data["done"],
                context=data.get("context"),
                total_duration=data.get("total_duration"),
                load_duration=data.get("load_duration"),
                prompt_eval_count=data.get("prompt_eval_count"),
                prompt_eval_duration=data.get("prompt_eval_duration"),
                eval_count=data.get("eval_count"),
                eval_duration=data.get("eval_duration")
            )
    
    async def generate_text_stream(
        self, 
        request: OllamaGenerateRequest
    ) -> AsyncGenerator[OllamaGenerateResponse, None]:
        """
        流式生成文本
        
        Args:
            request: 文本生成请求
            
        Yields:
            文本生成响应块
        """
        url = "/api/generate"
        payload = {
            "model": self.get_model_name(request.model),
            "prompt": request.prompt,
            "stream": True
        }
        
        if request.system:
            payload["system"] = request.system
        if request.template:
            payload["template"] = request.template
        if request.context:
            payload["context"] = request.context
        if request.options:
            payload["options"] = request.options
        if request.format:
            payload["format"] = request.format
        if request.raw:
            payload["raw"] = request.raw
        if request.keep_alive:
            payload["keep_alive"] = request.keep_alive
        
        async with self.client as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            yield OllamaGenerateResponse(
                                model=data["model"],
                                created_at=data["created_at"],
                                response=data["response"],
                                done=data["done"],
                                context=data.get("context"),
                                total_duration=data.get("total_duration"),
                                load_duration=data.get("load_duration"),
                                prompt_eval_count=data.get("prompt_eval_count"),
                                prompt_eval_duration=data.get("prompt_eval_duration"),
                                eval_count=data.get("eval_count"),
                                eval_duration=data.get("eval_duration")
                            )
                        except json.JSONDecodeError:
                            continue
    
    async def get_model_info(self, model: str) -> OllamaModelInfo:
        """
        获取模型信息
        
        Args:
            model: 模型名称
            
        Returns:
            模型信息
        """
        url = f"/api/show"
        payload = {"name": self.get_model_name(model)}
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return OllamaModelInfo(
                license=data.get("license"),
                modelfile=data.get("modelfile"),
                parameters=data.get("parameters"),
                template=data.get("template"),
                system=data.get("system"),
                digest=data.get("digest"),
                details=data.get("details")
            )
    
    async def list_models_detailed(self) -> List[OllamaModel]:
        """
        获取详细的模型列表
        
        Returns:
            模型列表
        """
        async with self.client as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            
            models = []
            for model_data in data["models"]:
                model = OllamaModel(
                    name=model_data["name"],
                    modified_at=model_data["modified_at"],
                    size=model_data["size"],
                    digest=model_data["digest"]
                )
                
                # 获取详细信息
                try:
                    model.details = await self.get_model_info(model.name)
                except Exception as e:
                    self.logger.warning(f"获取模型 {model.name} 详细信息失败: {e}")
                
                models.append(model)
            
            return models
    
    async def pull_model(self, model: str, insecure: bool = False) -> Dict[str, Any]:
        """
        拉取模型
        
        Args:
            model: 模型名称
            insecure: 是否使用不安全模式
            
        Returns:
            拉取结果
        """
        url = "/api/pull"
        payload = {"name": model}
        
        if insecure:
            payload["insecure"] = True
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def push_model(self, model: str, insecure: bool = False) -> Dict[str, Any]:
        """
        推送模型
        
        Args:
            model: 模型名称
            insecure: 是否使用不安全模式
            
        Returns:
            推送结果
        """
        url = "/api/push"
        payload = {"name": model}
        
        if insecure:
            payload["insecure"] = True
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def delete_model(self, model: str) -> Dict[str, Any]:
        """
        删除模型
        
        Args:
            model: 模型名称
            
        Returns:
            删除结果
        """
        url = "/api/delete"
        payload = {"name": model}
        
        async with self.client as client:
            response = await client.delete(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def copy_model(self, source: str, destination: str) -> Dict[str, Any]:
        """
        复制模型
        
        Args:
            source: 源模型名称
            destination: 目标模型名称
            
        Returns:
            复制结果
        """
        url = "/api/copy"
        payload = {
            "source": source,
            "destination": destination
        }
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def get_system_info(self) -> OllamaSystemInfo:
        """
        获取系统信息
        
        Returns:
            系统信息
        """
        async with self.client as client:
            response = await client.get("/api/version")
            response.raise_for_status()
            data = response.json()
            
            return OllamaSystemInfo(
                total_memory=data.get("total_memory", 0),
                free_memory=data.get("free_memory", 0),
                used_memory=data.get("used_memory", 0),
                num_cpu=data.get("num_cpu", 0),
                num_gpu=data.get("num_gpu", 0),
                gpu_layers=data.get("gpu_layers", 0),
                library=data.get("library", ""),
                version=data.get("version", "")
            )
    
    async def create_model(self, name: str, modelfile: str) -> Dict[str, Any]:
        """
        创建模型
        
        Args:
            name: 模型名称
            modelfile: 模型文件内容
            
        Returns:
            创建结果
        """
        url = "/api/create"
        payload = {
            "name": name,
            "modelfile": modelfile
        }
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表（重写父类方法）"""
        models = await self.list_models_detailed()
        return [
            {
                "id": model.name,
                "object": "model",
                "name": model.name,
                "size": model.size,
                "modified_at": model.modified_at
            }
            for model in models
        ]


# 便捷函数
def create_enhanced_ollama_provider(
    api_base: str = "http://localhost:11434",
    **kwargs
) -> EnhancedOllamaProvider:
    """
    创建增强的 Ollama 提供商
    
    Args:
        api_base: Ollama API 基础 URL
        **kwargs: 其他配置参数
        
    Returns:
        增强的 Ollama 提供商实例
    """
    config = ProviderConfig(
        provider_type=ProviderType.OLLAMA,
        api_base=api_base,
        **kwargs
    )
    
    return EnhancedOllamaProvider(config)


def check_ollama_availability(api_base: str = "http://localhost:11434") -> bool:
    """
    检查 Ollama 服务是否可用
    
    Args:
        api_base: Ollama API 基础 URL
        
    Returns:
        是否可用
    """
    try:
        import httpx
        
        # 使用同步客户端进行快速检查
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{api_base}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


class OllamaNotAvailableError(Exception):
    """Ollama 服务不可用异常"""
    pass


async def get_ollama_embedding(
    text: str,
    model: str = "llama2",
    api_base: str = "http://localhost:11434",
    fallback_to_openai: bool = True
) -> List[float]:
    """
    获取文本嵌入的便捷函数
    
    Args:
        text: 文本内容
        model: 模型名称
        api_base: Ollama API 基础 URL
        fallback_to_openai: 是否在 Ollama 不可用时回退到 OpenAI
        
    Returns:
        嵌入向量
        
    Raises:
        OllamaNotAvailableError: 当 Ollama 不可用且不允许回退时
    """
    # 首先检查 Ollama 是否可用
    if not check_ollama_availability(api_base):
        if fallback_to_openai:
            try:
                # 尝试使用 OpenAI 作为回退
                from .openai_integration import get_openai_embedding
                from .providers import get_api_key_from_keyring, ProviderType
                
                api_key = get_api_key_from_keyring(ProviderType.OPENAI)
                if api_key:
                    print("⚠️  Ollama 不可用，回退到 OpenAI 嵌入服务")
                    return await get_openai_embedding(text, api_key)
                else:
                    raise OllamaNotAvailableError("Ollama 不可用且未配置 OpenAI API 密钥")
            except ImportError:
                raise OllamaNotAvailableError("Ollama 不可用且无法导入 OpenAI 模块")
        else:
            raise OllamaNotAvailableError("Ollama 服务不可用")
    
    try:
        provider = create_enhanced_ollama_provider(api_base)
        request = OllamaEmbeddingRequest(model=model, prompt=text)
        response = await provider.create_embedding(request)
        return response.embedding
    except Exception as e:
        if fallback_to_openai:
            try:
                from .openai_integration import get_openai_embedding
                from .providers import get_api_key_from_keyring, ProviderType
                
                api_key = get_api_key_from_keyring(ProviderType.OPENAI)
                if api_key:
                    print(f"⚠️  Ollama 调用失败: {e}，回退到 OpenAI")
                    return await get_openai_embedding(text, api_key)
            except Exception:
                pass
        
        raise OllamaNotAvailableError(f"Ollama 调用失败: {e}")


async def generate_ollama_text(
    prompt: str,
    model: str = "llama2",
    system: Optional[str] = None,
    api_base: str = "http://localhost:11434",
    fallback_to_openai: bool = True
) -> str:
    """
    生成文本的便捷函数
    
    Args:
        prompt: 提示文本
        model: 模型名称
        system: 系统提示
        api_base: Ollama API 基础 URL
        fallback_to_openai: 是否在 Ollama 不可用时回退到 OpenAI
        
    Returns:
        生成的文本
        
    Raises:
        OllamaNotAvailableError: 当 Ollama 不可用且不允许回退时
    """
    # 首先检查 Ollama 是否可用
    if not check_ollama_availability(api_base):
        if fallback_to_openai:
            try:
                # 尝试使用 OpenAI 作为回退
                from .providers import create_provider, ProviderType, Message, ChatCompletionRequest
                from .providers import get_api_key_from_keyring
                
                api_key = get_api_key_from_keyring(ProviderType.OPENAI)
                if api_key:
                    print("⚠️  Ollama 不可用，回退到 OpenAI 文本生成")
                    provider = create_provider(ProviderType.OPENAI, api_key=api_key)
                    request = ChatCompletionRequest(
                        messages=[Message(role="user", content=prompt)],
                        model="gpt-3.5-turbo",
                        max_tokens=500
                    )
                    response = await provider.chat_completion(request)
                    return response.choices[0]["message"]["content"]
                else:
                    raise OllamaNotAvailableError("Ollama 不可用且未配置 OpenAI API 密钥")
            except ImportError:
                raise OllamaNotAvailableError("Ollama 不可用且无法导入 OpenAI 模块")
        else:
            raise OllamaNotAvailableError("Ollama 服务不可用")
    
    try:
        provider = create_enhanced_ollama_provider(api_base)
        request = OllamaGenerateRequest(
            model=model,
            prompt=prompt,
            system=system
        )
        response = await provider.generate_text(request)
        return response.response
    except Exception as e:
        if fallback_to_openai:
            try:
                from .providers import create_provider, ProviderType, Message, ChatCompletionRequest
                from .providers import get_api_key_from_keyring
                
                api_key = get_api_key_from_keyring(ProviderType.OPENAI)
                if api_key:
                    print(f"⚠️  Ollama 调用失败: {e}，回退到 OpenAI")
                    provider = create_provider(ProviderType.OPENAI, api_key=api_key)
                    request = ChatCompletionRequest(
                        messages=[Message(role="user", content=prompt)],
                        model="gpt-3.5-turbo",
                        max_tokens=500
                    )
                    response = await provider.chat_completion(request)
                    return response.choices[0]["message"]["content"]
            except Exception:
                pass
        
        raise OllamaNotAvailableError(f"Ollama 调用失败: {e}")


async def list_ollama_models(
    api_base: str = "http://localhost:11434"
) -> List[OllamaModel]:
    """
    获取 Ollama 模型列表的便捷函数
    
    Args:
        api_base: Ollama API 基础 URL
        
    Returns:
        模型列表
        
    Raises:
        OllamaNotAvailableError: 当 Ollama 不可用时
    """
    if not check_ollama_availability(api_base):
        raise OllamaNotAvailableError("Ollama 服务不可用")
    
    provider = create_enhanced_ollama_provider(api_base)
    return await provider.list_models_detailed()


async def pull_ollama_model(
    model: str,
    api_base: str = "http://localhost:11434",
    insecure: bool = False
) -> Dict[str, Any]:
    """
    拉取 Ollama 模型的便捷函数
    
    Args:
        model: 模型名称
        api_base: Ollama API 基础 URL
        insecure: 是否使用不安全模式
        
    Returns:
        拉取结果
        
    Raises:
        OllamaNotAvailableError: 当 Ollama 不可用时
    """
    if not check_ollama_availability(api_base):
        raise OllamaNotAvailableError("Ollama 服务不可用")
    
    provider = create_enhanced_ollama_provider(api_base)
    return await provider.pull_model(model, insecure)


async def get_ollama_system_info(
    api_base: str = "http://localhost:11434"
) -> OllamaSystemInfo:
    """
    获取 Ollama 系统信息的便捷函数
    
    Args:
        api_base: Ollama API 基础 URL
        
    Returns:
        系统信息
        
    Raises:
        OllamaNotAvailableError: 当 Ollama 不可用时
    """
    if not check_ollama_availability(api_base):
        raise OllamaNotAvailableError("Ollama 服务不可用")
    
    provider = create_enhanced_ollama_provider(api_base)
    return await provider.get_system_info()


def get_ollama_installation_guide() -> str:
    """
    获取 Ollama 安装指南
    
    Returns:
        安装指南文本
    """
    return """
Ollama 安装指南:

1. 访问官方网站: https://ollama.ai/
2. 下载适合您操作系统的安装包
3. 安装完成后，启动服务:
   - Windows: ollama serve
   - macOS: ollama serve  
   - Linux: ollama serve
4. 拉取模型:
   - 通用模型: ollama pull llama2
   - 代码模型: ollama pull codellama
   - 轻量模型: ollama pull gemma
5. 验证安装: ollama list

注意事项:
- 首次拉取模型可能需要较长时间
- 确保有足够的磁盘空间（至少 5GB）
- 建议使用 GPU 加速（如果可用）
- 默认端口为 11434，确保未被占用

如果遇到问题:
- 检查防火墙设置
- 确保端口 11434 可访问
- 查看 Ollama 日志: ollama logs
- 重启服务: ollama stop && ollama serve
""" 