"""
AutoDoc Agent CLI 工具

提供命令行界面，支持文档生成、配置管理等功能。
"""

import typer
from rich.console import Console
from rich.traceback import install

from .commands import app

# 安装Rich的异常处理
install(show_locals=True)

# 创建控制台实例
console = Console()

# 导出主应用
__all__ = ["app"]
