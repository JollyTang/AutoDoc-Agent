"""
AutoDoc Agent CLI 主入口

当运行 python -m src.cli 时调用此模块。
"""

from .commands import app

if __name__ == "__main__":
    app() 