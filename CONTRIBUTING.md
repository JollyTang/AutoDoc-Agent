# 贡献指南

感谢您对 AutoDoc Agent 项目的关注！我们欢迎所有形式的贡献。

## 贡献方式

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- 🧪 编写测试
- 🌍 翻译文档

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/autodoc-agent/autodoc-agent.git
cd autodoc-agent
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 4. 安装 pre-commit 钩子

```bash
pre-commit install
```

## 开发流程

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 2. 开发代码

- 遵循[代码规范](#代码规范)
- 编写测试用例
- 更新相关文档

### 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_ast_parser.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 4. 代码检查

```bash
# 格式化代码
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# 代码检查
flake8 src/
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: 添加新功能描述"
git push origin feature/your-feature-name
```

### 6. 创建 Pull Request

在 GitHub 上创建 Pull Request，并填写 PR 模板。

## 代码规范

### Python 代码风格

- 使用[Black](https://black.readthedocs.io/)进行代码格式化
- 使用[isort](https://pycqa.github.io/isort/)进行导入排序
- 遵循[PEP 8](https://www.python.org/dev/peps/pep-0008/)规范
- 使用类型注解

### 提交信息规范

使用[Conventional Commits](https://www.conventionalcommits.org/)规范：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

类型说明：

- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

示例：

```
feat(ast): 添加Python AST解析器
fix(cli): 修复配置文件路径问题
docs: 更新安装指南
```

### 测试规范

- 新功能必须包含测试用例
- 测试覆盖率不低于 80%
- 使用 pytest 作为测试框架
- 测试文件命名：`test_*.py`

## 问题报告

### Bug 报告

请包含以下信息：

- 操作系统和 Python 版本
- 错误信息和堆栈跟踪
- 重现步骤
- 预期行为

### 功能建议

请包含以下信息：

- 功能描述
- 使用场景
- 实现建议（可选）

## 发布流程

### 版本号规范

使用[语义化版本](https://semver.org/lang/zh-CN/)：

- `MAJOR.MINOR.PATCH`
- `MAJOR`: 不兼容的 API 修改
- `MINOR`: 向下兼容的功能性新增
- `PATCH`: 向下兼容的问题修正

### 发布步骤

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建发布标签
4. 发布到 PyPI

## 行为准则

- 尊重所有贡献者
- 保持专业和友善的交流
- 接受建设性的批评
- 关注项目的最佳利益

## 联系方式

- 项目维护者: [@maintainers](https://github.com/orgs/autodoc-agent/people)
- 讨论区: [GitHub Discussions](https://github.com/autodoc-agent/autodoc-agent/discussions)
- 问题反馈: [GitHub Issues](https://github.com/autodoc-agent/autodoc-agent/issues)

感谢您的贡献！🎉
