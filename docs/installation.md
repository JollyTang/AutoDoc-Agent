# 安装指南

## 系统要求

- Python 3.8 或更高版本
- Git（用于版本控制集成）
- 网络连接（用于 LLM API 调用）

## 安装方法

### 方法一：从 PyPI 安装（推荐）

```bash
pip install autodoc-agent
```

### 方法二：从源码安装

```bash
# 克隆仓库
git clone https://github.com/autodoc-agent/autodoc-agent.git
cd autodoc-agent

# 安装依赖
pip install -e .
```

### 方法三：使用 conda

```bash
conda install -c conda-forge autodoc-agent
```

## 验证安装

安装完成后，运行以下命令验证：

```bash
autodoc --version
```

应该显示类似输出：

```
autodoc-agent 0.1.0
```

## 配置 LLM 提供商

### OpenAI

```bash
# 设置API密钥
export OPENAI_API_KEY="your-api-key"

# 或使用autodoc命令
autodoc config set llm.openai.api_key "your-api-key"
```

### Claude (Anthropic)

```bash
# 设置API密钥
export ANTHROPIC_API_KEY="your-api-key"

# 或使用autodoc命令
autodoc config set llm.claude.api_key "your-api-key"
```

### Ollama (本地模型)

```bash
# 安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama pull codellama:7b

# 配置autodoc使用Ollama
autodoc config set llm.default_provider "ollama"
```

## 故障排除

### 常见问题

1. **权限错误**

   ```bash
   # 使用用户安装
   pip install --user autodoc-agent
   ```

2. **依赖冲突**

   ```bash
   # 创建虚拟环境
   python -m venv autodoc-env
   source autodoc-env/bin/activate
   pip install autodoc-agent
   ```

3. **网络问题**
   ```bash
   # 使用国内镜像
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple autodoc-agent
   ```

### 获取帮助

如果遇到问题，请：

1. 查看[常见问题](faq.md)
2. 提交[Issue](https://github.com/autodoc-agent/autodoc-agent/issues)
3. 查看[日志](troubleshooting.md#日志分析)
