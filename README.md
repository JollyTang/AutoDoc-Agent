# AutoDoc Agent

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

智能代码文档生成工具，支持多种编程语言和 LLM 集成，自动生成高质量的 README、API 文档和架构图。

## ✨ 特性

- 🔍 **多语言 AST 解析**: 支持 Python、Go、Java、TypeScript 等主流编程语言
- 🤖 **LLM 智能生成**: 集成 OpenAI、Claude、Ollama 等多种 LLM 提供商
- 📊 **可视化图表**: 自动生成 Mermaid 架构图和模块关系图
- 🔄 **Git 集成**: 支持自动提交、PR 创建和变更摘要生成
- ⚡ **高性能**: 并发处理、缓存机制和智能优化
- 🛡️ **安全可靠**: API 密钥安全存储、敏感信息过滤

## 🚀 快速开始

### 安装

```bash
# 从PyPI安装
pip install autodoc-agent

# 或从源码安装
git clone https://github.com/autodoc-agent/autodoc-agent.git
cd autodoc-agent
pip install -e .
```

### 基本使用

```bash
# 初始化项目配置
autodoc init

# 生成文档
autodoc update

# 查看帮助
autodoc --help
```

### 配置 LLM

```bash
# 设置OpenAI API密钥
autodoc config set llm.openai.api_key "your-api-key"

# 或使用环境变量
export OPENAI_API_KEY="your-api-key"
```

## 📖 详细文档

- [安装指南](docs/installation.md)
- [配置说明](docs/configuration.md)
- [使用教程](docs/tutorial.md)
- [API 参考](docs/api.md)
- [示例项目](docs/examples/)

## 🏗️ 项目结构

```
autodoc-agent/
├── src/
│   ├── cli/           # CLI工具
│   ├── core/          # 核心功能
│   ├── llm/           # LLM集成
│   ├── docs/          # 文档生成
│   └── utils/         # 工具函数
├── tests/             # 测试文件
├── docs/              # 项目文档
└── examples/          # 示例项目
```

## 🔧 开发

### 环境设置

```bash
# 克隆仓库
git clone https://github.com/autodoc-agent/autodoc-agent.git
cd autodoc-agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 安装pre-commit钩子
pre-commit install
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_ast_parser.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 代码格式化

```bash
# 格式化代码
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# 代码检查
flake8 src/
```

## 🤝 贡献

欢迎贡献代码！请查看[贡献指南](CONTRIBUTING.md)了解详情。

### 开发流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 🙏 致谢

- [libcst](https://github.com/Instagram/LibCST) - Python AST 解析
- [tree-sitter](https://tree-sitter.github.io/tree-sitter/) - 多语言解析
- [Typer](https://typer.tiangolo.com/) - CLI 框架
- [Rich](https://rich.readthedocs.io/) - 终端美化

## 📞 联系我们

- 项目主页: https://github.com/autodoc-agent/autodoc-agent
- 问题反馈: https://github.com/autodoc-agent/autodoc-agent/issues
- 文档: https://autodoc-agent.readthedocs.io

---

**AutoDoc Agent** - 让代码文档生成变得简单高效 🚀
