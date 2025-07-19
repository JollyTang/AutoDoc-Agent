"""
Claude API 集成模块

提供完整的 Claude API 集成功能，包括：
- 聊天完成
- 文本生成
- 图像分析
- 工具调用
- 内容过滤
- 模型管理
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, Field

from .providers import (
    ClaudeProvider, ProviderType, Message, ChatCompletionRequest,
    ChatCompletionResponse, ChatCompletionChunk, ProviderConfig
)

logger = logging.getLogger(__name__)


@dataclass
class ClaudeContentBlock:
    """Claude 内容块"""
    type: str  # "text", "image"
    text: Optional[str] = None
    source: Optional[Dict[str, Any]] = None


@dataclass
class ClaudeMessage:
    """Claude 消息"""
    role: str  # "user", "assistant"
    content: Union[str, List[ClaudeContentBlock]]


@dataclass
class ClaudeTool:
    """Claude 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class ClaudeToolUse:
    """Claude 工具使用"""
    id: str
    type: str = "tool_use"
    name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaudeToolResult:
    """Claude 工具结果"""
    type: str = "tool_result"
    tool_use_id: str = ""
    content: str = ""
    is_error: bool = False


@dataclass
class ClaudeRequest:
    """Claude 请求"""
    model: str
    messages: List[ClaudeMessage]
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: int = 40
    stream: bool = False
    system: Optional[str] = None
    tools: Optional[List[ClaudeTool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    stop_sequences: Optional[List[str]] = None


@dataclass
class ClaudeResponse:
    """Claude 响应"""
    id: str
    type: str
    role: str
    content: List[ClaudeContentBlock]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


@dataclass
class ClaudeStreamResponse:
    """Claude 流式响应"""
    type: str
    index: int
    delta: Optional[Dict[str, Any]] = None
    content_block: Optional[ClaudeContentBlock] = None
    message: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, int]] = None


class EnhancedClaudeProvider(ClaudeProvider):
    """
    增强的 Claude 提供商
    
    提供更完整的 Claude API 功能。
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.EnhancedClaudeProvider")
    
    def _format_claude_messages(
        self, 
        messages: List[Message]
    ) -> List[ClaudeMessage]:
        """格式化 Claude 消息"""
        claude_messages = []
        for msg in messages:
            if msg.role == "system":
                # Claude 使用 system 字段而不是消息
                continue
            
            if isinstance(msg.content, str):
                claude_messages.append(ClaudeMessage(
                    role=msg.role,
                    content=msg.content
                ))
            else:
                # 处理复杂内容（如图像）
                claude_messages.append(ClaudeMessage(
                    role=msg.role,
                    content=msg.content
                ))
        
        return claude_messages
    
    async def chat_completion_enhanced(
        self, 
        request: ClaudeRequest
    ) -> ClaudeResponse:
        """
        增强的聊天完成请求
        
        Args:
            request: Claude 请求
            
        Returns:
            Claude 响应
        """
        url = "/messages"
        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content if isinstance(msg.content, str) else [
                        {
                            "type": block.type,
                            "text": block.text,
                            "source": block.source
                        } for block in msg.content
                    ]
                }
                for msg in request.messages
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "stream": False
        }
        
        if request.system:
            payload["system"] = request.system
        if request.tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema
                }
                for tool in request.tools
            ]
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.metadata:
            payload["metadata"] = request.metadata
        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences
        
        async with self.client as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return ClaudeResponse(
                id=data["id"],
                type=data["type"],
                role=data["role"],
                content=[
                    ClaudeContentBlock(
                        type=block["type"],
                        text=block.get("text"),
                        source=block.get("source")
                    )
                    for block in data["content"]
                ],
                model=data["model"],
                stop_reason=data.get("stop_reason"),
                stop_sequence=data.get("stop_sequence"),
                usage=data.get("usage")
            )
    
    async def chat_completion_stream_enhanced(
        self, 
        request: ClaudeRequest
    ) -> AsyncGenerator[ClaudeStreamResponse, None]:
        """
        增强的流式聊天完成请求
        
        Args:
            request: Claude 请求
            
        Yields:
            Claude 流式响应
        """
        url = "/messages"
        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content if isinstance(msg.content, str) else [
                        {
                            "type": block.type,
                            "text": block.text,
                            "source": block.source
                        } for block in msg.content
                    ]
                }
                for msg in request.messages
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "stream": True
        }
        
        if request.system:
            payload["system"] = request.system
        if request.tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema
                }
                for tool in request.tools
            ]
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.metadata:
            payload["metadata"] = request.metadata
        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences
        
        async with self.client as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data)
                            
                            if chunk_data["type"] == "content_block_delta":
                                yield ClaudeStreamResponse(
                                    type=chunk_data["type"],
                                    index=chunk_data["index"],
                                    delta=chunk_data.get("delta")
                                )
                            elif chunk_data["type"] == "content_block":
                                yield ClaudeStreamResponse(
                                    type=chunk_data["type"],
                                    index=chunk_data["index"],
                                    content_block=ClaudeContentBlock(
                                        type=chunk_data["content_block"]["type"],
                                        text=chunk_data["content_block"].get("text"),
                                        source=chunk_data["content_block"].get("source")
                                    )
                                )
                            elif chunk_data["type"] == "message":
                                yield ClaudeStreamResponse(
                                    type=chunk_data["type"],
                                    index=chunk_data["index"],
                                    message=chunk_data.get("message")
                                )
                            elif chunk_data["type"] == "message_delta":
                                yield ClaudeStreamResponse(
                                    type=chunk_data["type"],
                                    index=chunk_data["index"],
                                    delta=chunk_data.get("delta")
                                )
                            elif chunk_data["type"] == "usage":
                                yield ClaudeStreamResponse(
                                    type=chunk_data["type"],
                                    index=chunk_data["index"],
                                    usage=chunk_data.get("usage")
                                )
                        except json.JSONDecodeError:
                            continue
    
    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        model: str = "claude-3-vision-20240229"
    ) -> ClaudeResponse:
        """
        分析图像
        
        Args:
            image_url: 图像 URL
            prompt: 分析提示
            model: 模型名称
            
        Returns:
            分析结果
        """
        request = ClaudeRequest(
            model=model,
            messages=[
                ClaudeMessage(
                    role="user",
                    content=[
                        ClaudeContentBlock(
                            type="text",
                            text=prompt
                        ),
                        ClaudeContentBlock(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_url
                            }
                        )
                    ]
                )
            ]
        )
        
        return await self.chat_completion_enhanced(request)
    
    async def call_tool(
        self,
        messages: List[ClaudeMessage],
        tools: List[ClaudeTool],
        model: str = "claude-3-sonnet-20240229"
    ) -> ClaudeResponse:
        """
        调用工具
        
        Args:
            messages: 消息列表
            tools: 工具列表
            model: 模型名称
            
        Returns:
            工具调用结果
        """
        request = ClaudeRequest(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        return await self.chat_completion_enhanced(request)
    
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        获取模型信息
        
        Args:
            model: 模型名称
            
        Returns:
            模型信息
        """
        # Claude API 不提供模型信息端点，返回预定义信息
        model_info = {
            "claude-3-opus-20240229": {
                "id": "claude-3-opus-20240229",
                "object": "model",
                "created": 1707855360,
                "owned_by": "anthropic",
                "context_length": 200000,
                "supports_vision": True,
                "supports_tools": True
            },
            "claude-3-sonnet-20240229": {
                "id": "claude-3-sonnet-20240229",
                "object": "model",
                "created": 1707855360,
                "owned_by": "anthropic",
                "context_length": 200000,
                "supports_vision": True,
                "supports_tools": True
            },
            "claude-3-haiku-20240307": {
                "id": "claude-3-haiku-20240307",
                "object": "model",
                "created": 1709856000,
                "owned_by": "anthropic",
                "context_length": 200000,
                "supports_vision": True,
                "supports_tools": True
            }
        }
        
        return model_info.get(model, {
            "id": model,
            "object": "model",
            "created": 0,
            "owned_by": "anthropic",
            "context_length": 200000,
            "supports_vision": False,
            "supports_tools": False
        })
    
    async def get_usage(self) -> Dict[str, Any]:
        """
        获取使用情况
        
        Returns:
            使用情况
        """
        # Claude API 不提供使用情况端点，返回空数据
        return {
            "object": "usage",
            "daily_costs": [],
            "monthly_costs": []
        }


# 便捷函数
def create_enhanced_claude_provider(
    api_key: str,
    api_base: Optional[str] = None,
    **kwargs
) -> EnhancedClaudeProvider:
    """
    创建增强的 Claude 提供商
    
    Args:
        api_key: Claude API 密钥
        api_base: API 基础 URL
        **kwargs: 其他配置参数
        
    Returns:
        增强的 Claude 提供商实例
    """
    config = ProviderConfig(
        provider_type=ProviderType.CLAUDE,
        api_key=api_key,
        api_base=api_base,
        **kwargs
    )
    
    return EnhancedClaudeProvider(config)


async def analyze_image_with_claude(
    image_url: str,
    prompt: str,
    api_key: str,
    model: str = "claude-3-vision-20240229"
) -> str:
    """
    使用 Claude 分析图像的便捷函数
    
    Args:
        image_url: 图像 URL
        prompt: 分析提示
        api_key: Claude API 密钥
        model: 模型名称
        
    Returns:
        分析结果文本
    """
    provider = create_enhanced_claude_provider(api_key)
    response = await provider.analyze_image(image_url, prompt, model)
    
    # 提取文本内容
    text_content = ""
    for block in response.content:
        if block.type == "text" and block.text:
            text_content += block.text
    
    return text_content


async def call_claude_tool(
    messages: List[ClaudeMessage],
    tools: List[ClaudeTool],
    api_key: str,
    model: str = "claude-3-sonnet-20240229"
) -> ClaudeResponse:
    """
    使用 Claude 调用工具的便捷函数
    
    Args:
        messages: 消息列表
        tools: 工具列表
        api_key: Claude API 密钥
        model: 模型名称
        
    Returns:
        工具调用结果
    """
    provider = create_enhanced_claude_provider(api_key)
    return await provider.call_tool(messages, tools, model)


def create_claude_tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any]
) -> ClaudeTool:
    """
    创建 Claude 工具的便捷函数
    
    Args:
        name: 工具名称
        description: 工具描述
        input_schema: 输入模式
        
    Returns:
        Claude 工具
    """
    return ClaudeTool(
        name=name,
        description=description,
        input_schema=input_schema
    ) 