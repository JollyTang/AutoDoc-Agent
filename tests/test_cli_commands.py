"""
CLI命令的单元测试

测试所有CLI命令的功能和参数。
"""

import pytest
from typer.testing import CliRunner
from src.cli.commands import app


@pytest.fixture
def runner():
    """创建CLI测试运行器"""
    return CliRunner()


def test_app_version(runner):
    """测试版本信息显示"""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "AutoDoc Agent v0.1.0" in result.stdout


def test_app_help(runner):
    """测试帮助信息显示"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "智能代码文档生成工具" in result.stdout


def test_init_command(runner):
    """测试初始化命令"""
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "正在初始化 AutoDoc Agent" in result.stdout


def test_init_command_force(runner):
    """测试强制初始化命令"""
    result = runner.invoke(app, ["init", "--force"])
    assert result.exit_code == 0
    assert "正在初始化 AutoDoc Agent" in result.stdout


def test_update_command(runner):
    """测试更新命令"""
    result = runner.invoke(app, ["update"])
    assert result.exit_code == 0
    assert "正在更新文档" in result.stdout


def test_update_command_with_path(runner):
    """测试指定路径的更新命令"""
    result = runner.invoke(app, ["update", "/path/to/project"])
    assert result.exit_code == 0
    assert "/path/to/project" in result.stdout


def test_update_command_force(runner):
    """测试强制更新命令"""
    result = runner.invoke(app, ["update", "--force"])
    assert result.exit_code == 0
    assert "正在更新文档" in result.stdout


def test_update_command_dry_run(runner):
    """测试试运行模式"""
    result = runner.invoke(app, ["update", "--dry-run"])
    assert result.exit_code == 0
    assert "正在更新文档" in result.stdout


def test_config_command_show(runner):
    """测试配置显示命令"""
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "当前配置" in result.stdout


def test_config_command_set(runner):
    """测试配置设置命令"""
    result = runner.invoke(app, ["config", "set", "test.key", "test.value"])
    assert result.exit_code == 0
    assert "设置配置" in result.stdout


def test_config_command_get(runner):
    """测试配置获取命令"""
    result = runner.invoke(app, ["config", "get", "test.key"])
    assert result.exit_code == 0
    assert "获取配置" in result.stdout


def test_config_command_reset(runner):
    """测试配置重置命令"""
    result = runner.invoke(app, ["config", "reset"])
    assert result.exit_code == 0
    assert "重置配置" in result.stdout


def test_config_command_invalid(runner):
    """测试无效的配置命令"""
    result = runner.invoke(app, ["config", "invalid"])
    assert result.exit_code == 1
    assert "无效的配置操作" in result.stdout


def test_status_command(runner):
    """测试状态检查命令"""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "系统状态检查" in result.stdout 