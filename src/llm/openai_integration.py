"""
OpenAI API 集成模块

提供完整的 OpenAI API 集成功能，包括：
- 聊天完成
- 文本生成
- 图像生成
- 嵌入向量
- 微调
- 模型管理
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
    OpenAIProvider, ProviderType, Message, ChatCompletionRequest,
    ChatCompletionResponse, ChatCompletionChunk, ProviderConfig
)

logger = logging.getLogger(__name__)


@dataclass
class OpenAIEmbeddingRequest:
    """OpenAI 嵌入请求"""
    input: Union[str, List[str]]
    model: str = "text-embedding-ada-002"
    encoding_format: str = "float"
    dimensions: Optional[int] = None
    user: Optional[str] = None


@dataclass
class OpenAIEmbeddingResponse:
    """OpenAI 嵌入响应"""
    object: str
    data: List[Dict[str, Any]]
    model: str
    usage: Dict[str, int]


@dataclass
class OpenAIImageGenerationRequest:
    """OpenAI 图像生成请求"""
    prompt: str
    model: str = "dall-e-3"
    n: int = 1
    quality: str = "standard"
    response_format: str = "url"
    size: str = "1024x1024"
    style: Optional[str] = None
    user: Optional[str] = None


@dataclass
class OpenAIImageGenerationResponse:
    """OpenAI 图像生成响应"""
    created: int
    data: List[Dict[str, Any]]


@dataclass
class OpenAIFineTuningJob:
    """OpenAI 微调任务"""
    id: str
    object: str
    model: str
    created_at: int
    finished_at: Optional[int]
    fine_tuned_model: Optional[str]
    organization_id: str
    result_files: List[str]
    status: str
    validation_file: Optional[str]
    training_file: str
    trained_tokens: Optional[int]
    error: Optional[Dict[str, Any]]
    hyperparameters: Dict[str, Any]


class EnhancedOpenAIProvider(OpenAIProvider):
    """
    增强的 OpenAI 提供商
    
    提供更完整的 OpenAI API 功能。
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.EnhancedOpenAIProvider")
    
    async def create_embedding(
        self, 
        request: OpenAIEmbeddingRequest
    ) -> OpenAIEmbeddingResponse:
        """
        创建文本嵌入
        
        Args:
            request: 嵌入请求
            
        Returns:
            嵌入响应
        """
        url = "/embeddings"
        payload = {
            "input": request.input,
            "model": request.model,
            "encoding_format": request.encoding_format
        }
        
        if request.dimensions:
            payload["dimensions"] = request.dimensions
        if request.user:
            payload["user"] = request.user
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return OpenAIEmbeddingResponse(
                object=data["object"],
                data=data["data"],
                model=data["model"],
                usage=data["usage"]
            )
    
    async def generate_image(
        self, 
        request: OpenAIImageGenerationRequest
    ) -> OpenAIImageGenerationResponse:
        """
        生成图像
        
        Args:
            request: 图像生成请求
            
        Returns:
            图像生成响应
        """
        url = "/images/generations"
        payload = {
            "prompt": request.prompt,
            "model": request.model,
            "n": request.n,
            "quality": request.quality,
            "response_format": request.response_format,
            "size": request.size
        }
        
        if request.style:
            payload["style"] = request.style
        if request.user:
            payload["user"] = request.user
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return OpenAIImageGenerationResponse(
                created=data["created"],
                data=data["data"]
            )
    
    async def list_fine_tuning_jobs(
        self, 
        limit: int = 20,
        after: Optional[str] = None
    ) -> List[OpenAIFineTuningJob]:
        """
        获取微调任务列表
        
        Args:
            limit: 返回数量限制
            after: 分页游标
            
        Returns:
            微调任务列表
        """
        url = "/fine_tuning/jobs"
        params = {"limit": limit}
        if after:
            params["after"] = after
        
        async with self.client as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            for job_data in data["data"]:
                job = OpenAIFineTuningJob(
                    id=job_data["id"],
                    object=job_data["object"],
                    model=job_data["model"],
                    created_at=job_data["created_at"],
                    finished_at=job_data.get("finished_at"),
                    fine_tuned_model=job_data.get("fine_tuned_model"),
                    organization_id=job_data["organization_id"],
                    result_files=job_data["result_files"],
                    status=job_data["status"],
                    validation_file=job_data.get("validation_file"),
                    training_file=job_data["training_file"],
                    trained_tokens=job_data.get("trained_tokens"),
                    error=job_data.get("error"),
                    hyperparameters=job_data["hyperparameters"]
                )
                jobs.append(job)
            
            return jobs
    
    async def create_fine_tuning_job(
        self,
        model: str,
        training_file: str,
        validation_file: Optional[str] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        suffix: Optional[str] = None
    ) -> OpenAIFineTuningJob:
        """
        创建微调任务
        
        Args:
            model: 基础模型
            training_file: 训练文件 ID
            validation_file: 验证文件 ID
            hyperparameters: 超参数
            suffix: 模型后缀
            
        Returns:
            微调任务
        """
        url = "/fine_tuning/jobs"
        payload = {
            "model": model,
            "training_file": training_file
        }
        
        if validation_file:
            payload["validation_file"] = validation_file
        if hyperparameters:
            payload["hyperparameters"] = hyperparameters
        if suffix:
            payload["suffix"] = suffix
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return OpenAIFineTuningJob(
                id=data["id"],
                object=data["object"],
                model=data["model"],
                created_at=data["created_at"],
                finished_at=data.get("finished_at"),
                fine_tuned_model=data.get("fine_tuned_model"),
                organization_id=data["organization_id"],
                result_files=data["result_files"],
                status=data["status"],
                validation_file=data.get("validation_file"),
                training_file=data["training_file"],
                trained_tokens=data.get("trained_tokens"),
                error=data.get("error"),
                hyperparameters=data["hyperparameters"]
            )
    
    async def get_fine_tuning_job(self, job_id: str) -> OpenAIFineTuningJob:
        """
        获取微调任务详情
        
        Args:
            job_id: 任务 ID
            
        Returns:
            微调任务详情
        """
        url = f"/fine_tuning/jobs/{job_id}"
        
        async with self.client as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            return OpenAIFineTuningJob(
                id=data["id"],
                object=data["object"],
                model=data["model"],
                created_at=data["created_at"],
                finished_at=data.get("finished_at"),
                fine_tuned_model=data.get("fine_tuned_model"),
                organization_id=data["organization_id"],
                result_files=data["result_files"],
                status=data["status"],
                validation_file=data.get("validation_file"),
                training_file=data["training_file"],
                trained_tokens=data.get("trained_tokens"),
                error=data.get("error"),
                hyperparameters=data["hyperparameters"]
            )
    
    async def cancel_fine_tuning_job(self, job_id: str) -> OpenAIFineTuningJob:
        """
        取消微调任务
        
        Args:
            job_id: 任务 ID
            
        Returns:
            微调任务详情
        """
        url = f"/fine_tuning/jobs/{job_id}/cancel"
        
        async with self.client as client:
            response = await client.post(url)
            response.raise_for_status()
            data = response.json()
            
            return OpenAIFineTuningJob(
                id=data["id"],
                object=data["object"],
                model=data["model"],
                created_at=data["created_at"],
                finished_at=data.get("finished_at"),
                fine_tuned_model=data.get("fine_tuned_model"),
                organization_id=data["organization_id"],
                result_files=data["result_files"],
                status=data["status"],
                validation_file=data.get("validation_file"),
                training_file=data["training_file"],
                trained_tokens=data.get("trained_tokens"),
                error=data.get("error"),
                hyperparameters=data["hyperparameters"]
            )
    
    async def list_fine_tuning_events(
        self, 
        job_id: str,
        limit: int = 20,
        after: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取微调任务事件列表
        
        Args:
            job_id: 任务 ID
            limit: 返回数量限制
            after: 分页游标
            
        Returns:
            事件列表
        """
        url = f"/fine_tuning/jobs/{job_id}/events"
        params = {"limit": limit}
        if after:
            params["after"] = after
        
        async with self.client as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data["data"]
    
    async def upload_file(
        self,
        file_path: str,
        purpose: str = "fine-tune"
    ) -> Dict[str, Any]:
        """
        上传文件
        
        Args:
            file_path: 文件路径
            purpose: 文件用途
            
        Returns:
            文件信息
        """
        url = "/files"
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"purpose": purpose}
            
            async with self.client as client:
                response = await client.post(url, files=files, data=data)
                response.raise_for_status()
                return response.json()
    
    async def list_files(self) -> List[Dict[str, Any]]:
        """
        获取文件列表
        
        Returns:
            文件列表
        """
        url = "/files"
        
        async with self.client as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            return data["data"]
    
    async def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        删除文件
        
        Args:
            file_id: 文件 ID
            
        Returns:
            删除结果
        """
        url = f"/files/{file_id}"
        
        async with self.client as client:
            response = await client.delete(url)
            response.raise_for_status()
            return response.json()
    
    async def get_usage(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取使用情况
        
        Args:
            date: 日期 (YYYY-MM-DD 格式)
            
        Returns:
            使用情况
        """
        url = "/usage"
        params = {}
        if date:
            params["date"] = date
        
        async with self.client as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()


# 便捷函数
def create_enhanced_openai_provider(
    api_key: str,
    api_base: Optional[str] = None,
    **kwargs
) -> EnhancedOpenAIProvider:
    """
    创建增强的 OpenAI 提供商
    
    Args:
        api_key: OpenAI API 密钥
        api_base: API 基础 URL
        **kwargs: 其他配置参数
        
    Returns:
        增强的 OpenAI 提供商实例
    """
    config = ProviderConfig(
        provider_type=ProviderType.OPENAI,
        api_key=api_key,
        api_base=api_base,
        **kwargs
    )
    
    return EnhancedOpenAIProvider(config)


async def get_openai_embedding(
    text: Union[str, List[str]],
    api_key: str,
    model: str = "text-embedding-ada-002"
) -> List[List[float]]:
    """
    获取文本嵌入的便捷函数
    
    Args:
        text: 文本或文本列表
        api_key: OpenAI API 密钥
        model: 嵌入模型
        
    Returns:
        嵌入向量列表
    """
    provider = create_enhanced_openai_provider(api_key)
    request = OpenAIEmbeddingRequest(input=text, model=model)
    response = await provider.create_embedding(request)
    
    return [item["embedding"] for item in response.data]


async def generate_openai_image(
    prompt: str,
    api_key: str,
    model: str = "dall-e-3",
    size: str = "1024x1024"
) -> List[str]:
    """
    生成图像的便捷函数
    
    Args:
        prompt: 图像描述
        api_key: OpenAI API 密钥
        model: 图像生成模型
        size: 图像尺寸
        
    Returns:
        图像 URL 列表
    """
    provider = create_enhanced_openai_provider(api_key)
    request = OpenAIImageGenerationRequest(
        prompt=prompt,
        model=model,
        size=size
    )
    response = await provider.generate_image(request)
    
    return [item["url"] for item in response.data] 