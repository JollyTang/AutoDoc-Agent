AutoDocAgent  
基于 Commit 的增量文档自动生成系统  
详细产品需求文档（PRD）  
版本：v1.0  
日期：2025-07-19  
语言：简体中文

---

## 1 产品愿景
让每一次代码提交（commit）都能在 **3 秒内** 自动生成并更新对应模块的**高质量中文技术文档**，确保“代码即文档，文档永不过时”。

---

## 2 目标用户
| 角色 | 痛点 | 使用场景 |
|---|---|---|
| **开源 Maintainer** | PR 合并后文档滞后 | 接受外部贡献，需快速同步文档 |
| **企业研发团队** | 微服务/Monorepo 文档维护成本高 | 每日大量 Commit，需自动化文档 |
| **DevOps 工程师** | 发布流水线缺少文档环节 | 在 CI/CD 中加入文档自动生成步骤 |

---

## 3 需求范围（MVP）
| 功能 | 本期必须 | 本期不做 |
|---|---|---|
| 1. 全仓库初始化扫描 | ✅ | ❌ IDE 插件 |
| 2. Commit 级别增量更新 | ✅ | ❌ 图形化配置界面 |
| 3. 模块级 Markdown 输出 | ✅ | ❌ Word/PDF 导出 |
| 4. 本地 CLI & GitHub Action | ✅ | ❌ GitLab/Gitea |
| 5. 中英文双语摘要 | ✅ | ❌ 多语言全文翻译 |

---

## 4 功能需求详述

### 4.1 初始化（init）
| 需求编号 | 描述 | 验收标准 |
|---|---|---|
| F-1-1 | 用户执行 `autodoc init` 后，自动识别仓库语言/框架 | 支持 Go、Python、Java、TypeScript 四种 |
| F-1-2 | 生成 `.autodoc/` 目录，包含 snapshot.sha、module_map.json | 目录结构符合 PRD 附录 A |
| F-1-3 | 对全仓库进行一次 AST 扫描并生成模块级 README | 单测：100 k 行代码 ≤ 5 min 完成 |

### 4.2 增量更新（update）
| 需求编号 | 描述 | 验收标准 |
|---|---|---|
| F-2-1 | 监听 `git push` 事件（本地 CLI 或 GitHub Action） | 触发延迟 ≤ 2 s |
| F-2-2 | 计算 `<snapshot.sha>..HEAD` 的文件 diff | 只解析改动模块，耗时 ≤ 1 s |
| F-2-3 | 调用 LLM 生成/更新对应模块文档 | 单模块 LLM 耗时 ≤ 2 s（网络正常） |
| F-2-4 | 自动 commit 或提 PR，更新 snapshot.sha | 无人工干预 |

### 4.3 文档内容
| 需求编号 | 描述 | 验收标准 |
|---|---|---|
| F-3-1 | 每个模块 README 包含：功能概述、核心 API、示例代码 | 中文 80 % + 英文 20 % |
| F-3-2 | 类/函数变更自动生成 Mermaid 类图或时序图 | 图例渲染正确 |
| F-3-3 | 提供“本次变更摘要”段落 | 50 字以内，放在文件顶部 |

### 4.4 用户交互
| 需求编号 | 描述 | 验收标准 |
|---|---|---|
| F-4-1 | 本地 CLI：`autodoc init`, `autodoc update`, `autodoc --help` | Typer 自动生成帮助 |
| F-4-2 | GitHub Action：`.github/workflows/autodoc.yml` 一键启用 | 拷贝即用，无需额外配置 |
| F-4-3 | 可选开关：用户可在 commit message 加 `[skip-autodoc]` 跳过 | 正则匹配 `[skip-autodoc]` |

### 4.5 性能与可靠性
| 需求编号 | 描述 | 验收标准 |
|---|---|---|
| F-5-1 | 增量更新总耗时 ≤ 3 s（含网络） | 95 百分位 |
| F-5-2 | 网络异常时降级本地 OSS 小模型 | 耗时 ≤ 5 s |
| F-5-3 | 失败自动重试 3 次并写日志 | 日志存 `~/.autodoc/logs/` |

---

## 5 非功能需求

| 类别 | 需求 |
|---|---|
| 兼容性 | Python 3.10+、Git ≥ 2.30 |
| 安全 | LLM API Key 仅保存在本地 `keyring`；GitHub Action 使用 `secrets` |
| 可观测性 | 每步输出 JSONL 日志，Prometheus 指标（可选） |
| 开源协议 | MIT |

---

## 6 技术架构图

```
┌--------------┐     Webhook     ┌--------------┐
│ GitHub Push  │ --------------> │ FastAPI/CLI  │
└--------------┘                 └------┬-------┘
                                       |
      ┌-------------┬------------------┴----------------┐
      │ 1. Git Diff │ 2. AST 解析      │ 3. LLM 生成   │
      │ 耗时 < 1s   │ 多进程并行       │ 耗时 < 2s     │
      └-------------┴------------------┬----------------┘
                                       |
                             ┌---------┴---------┐
                             │ 4. 写回 docs/*.md │
                             │ 5. git commit     │
                             └-------------------┘
```

---

## 7 四周单人开发里程碑

| 周 | 任务 | 输出 | 验收 |
|---|---|---|---|
| W1 | 脚手架 + AST 扫描 | CLI `init`，生成 module_map.json | 本地跑通 10 k 行仓库 |
| W2 | LLM 文档模板 | README 模板 + Prompt 固化 | 人工 Review 通过 |
| W3 | 增量更新 + GitHub Action | `.github/workflows/autodoc.yml` | 在线仓库 Demo |
| W4 | 性能优化 + README 视频 | 录屏 GIF、性能报告 | P95 ≤ 3 s |

---

## 8 用户故事（UAT）

| 故事 | 场景 | 期望结果 |
|---|---|---|
| US-1 | 首次使用 | `pip install autodoc && autodoc init` 后 5 分钟完成全仓库文档 |
| US-2 | 日常开发 | 推送 commit 后 30 秒内收到 “docs updated” 通知 |
| US-3 | 网络异常 | 本地小模型兜底，仍能在 5 s 内完成更新 |

---

## 9 风险与对策

| 风险 | 概率 | 对策 |
|---|---|---|
| LLM 调用失败 | 中 | 本地 OSS 模型 + 重试队列 |
| 大文件 diff 超限制 | 低 | 按函数切片，只传变更片段 |
| AST 解析语言版本差异 | 低 | 使用 libcst 自带版本检测 |

---

## 10 附录

### A. `.autodoc/` 目录结构
```
.autodoc/
├── snapshot.sha          # 文档水印 commit
├── module_map.json       # {file_path: module_name}
├── logs/
│   └── 2025-07-19.jsonl
└── cache/
    └── ast.pickle        # 可选 AST 缓存
```

### B. 命令行示例
```bash
# 安装
pip install autodoc-agent

# 初始化
autodoc init --lang=go --out=docs

# 立即增量更新
autodoc update --repo=. --remote=github
```

---

如需第一周详细代码仓库脚手架（含 GitHub Action YAML + libcst 解析器），留言即可直接发。