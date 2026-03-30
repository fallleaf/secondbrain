# SecondBrain 项目初始化报告

**日期**: 2026-03-27 19:15  
**项目**: secondbrain-mcp  
**位置**: ~/project/secondbrain

---

## ✅ 已完成工作

### 1. 项目结构创建

```
~/project/secondbrain/
├── README.md                      # 项目说明
├── IMPLEMENTATION_PLAN.md         # 实施计划
├── pyproject.toml                 # 项目配置
├── requirements.txt               # 依赖列表
├── config.example.yaml            # 配置模板
├── priority_config.example.yaml   # 优先级配置模板
├── scripts/
│   └── build_index.py             # 索引构建脚本
├── src/
│   ├── __init__.py
│   ├── config/__init__.py
│   ├── index/__init__.py
│   ├── tools/__init__.py
│   └── utils/__init__.py
├── tests/
│   └── __init__.py
└── docs/
    ├── IMPLEMENTATION_PLAN_FULL.md    # 完整实施计划
    └── PROJECT_STRUCTURE.md           # 项目结构说明
```

**总计**: 14 个文件，9 个目录

---

### 2. 文档创建

| 文档 | 说明 | 行数 |
|------|------|------|
| `README.md` | 项目说明和快速开始 | ~90 行 |
| `IMPLEMENTATION_PLAN.md` | 实施计划 (简版) | ~188 行 |
| `docs/IMPLEMENTATION_PLAN_FULL.md` | 完整实施计划 | ~250 行 |
| `docs/PROJECT_STRUCTURE.md` | 项目结构说明 | ~120 行 |

---

### 3. 配置文件模板

| 配置文件 | 说明 |
|---------|------|
| `config.example.yaml` | 主配置 (Vault、索引、安全、日志) |
| `priority_config.example.yaml` | 优先级配置 (1-9 分级，5 个级别) |

---

### 4. 实施计划 (4 个 Phase)

#### Phase 1: 核心搜索工具 (1-2 周)
- 13 个任务
- 目标：实现 semantic_search 和基础读取工具
- 交付物：可运行的 MCP 服务器

#### Phase 2: 写入与管理工具 (1-2 周)
- 8 个任务
- 目标：实现 CRUD 完整功能
- 交付物：原子写入、软删除、路径验证

#### Phase 3: 批量操作与索引管理 (2-3 周)
- 8 个任务
- 目标：批量操作和索引管理
- 交付物：批量工具、增量更新、性能优化

#### Phase 4: 元数据与高级功能 (1-2 周)
- 8 个任务
- 目标：元数据管理和链接分析
- 交付物：标签管理、链接分析、文档完善

---

## 🎯 核心技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| **语言** | Python 3.10+ | 主开发语言 |
| **MCP 框架** | FastMCP | Model Context Protocol |
| **向量索引** | FAISS / sqlite-vec | 语义搜索 |
| **关键词索引** | SQLite FTS5 / BM25 | 全文检索 |
| **嵌入模型** | BAAI/bge-small-zh-v1.5 | 中文优化 |
| **优先级系统** | 1-9 间隔分级 | 5 个主要级别 |

---

## 📊 优先级系统设计

| 优先级 | 标签 | 描述 | 保留期 | 权重 |
|--------|------|------|--------|------|
| 9 | central_gov | 中央政府文件 | Permanent | 2.0 |
| 7 | ministry_gov | 部委文件 | 10 年 | 1.6 |
| 5 | company | 公司文档 | 3 年 | 1.2 |
| 3 | personal_work | 个人笔记 | 1 年 | 1.0 |
| 1 | web | 网络收集 | 90 天 | 0.8 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ~/project/secondbrain
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. 配置环境

```bash
# 创建配置目录
mkdir -p ~/.config/secondbrain

# 复制配置模板
cp config.example.yaml ~/.config/secondbrain/config.yaml
cp priority_config.example.yaml ~/.config/secondbrain/priority_config.yaml
```

### 3. 运行服务器

```bash
# 开发模式
python -m secondbrain.server

# 或作为 MCP 服务器
secondbrain-mcp
```

### 4. Claude Desktop 配置

```json
{
  "mcpServers": {
    "secondbrain": {
      "command": "python",
      "args": ["-m", "secondbrain.server"],
      "cwd": "/home/fallleaf/project/secondbrain",
      "env": {
        "SECOND_BRAIN_CONFIG": "/home/fallleaf/.config/secondbrain/config.yaml"
      }
    }
  }
}
```

---

## 📈 里程碑

| 里程碑 | 目标日期 | 交付物 |
|--------|---------|--------|
| M1: Phase 1 完成 | 2026-04-10 | 核心搜索工具可用 |
| M2: Phase 2 完成 | 2026-04-24 | 完整 CRUD 工具集 |
| M3: Phase 3 完成 | 2026-05-15 | 批量操作 + 索引管理 |
| M4: Phase 4 完成 | 2026-05-29 | 高级功能 + 文档完善 |
| M5: v1.0 发布 | 2026-06-05 | PyPI 发布 + 文档 |

---

## ⚠️ 下一步行动

### 本周任务 (Phase 1)

1. **创建配置加载器** (`src/config/settings.py`)
   - YAML 配置解析
   - 环境变量覆盖
   - 配置验证

2. **实现优先级分类器** (`src/utils/priority.py`)
   - 路径模式匹配
   - 优先级推断
   - 权重计算

3. **实现文本分块器** (`src/index/chunker.py`)
   - Markdown 感知分块
   - 重叠处理
   - Checksum 计算

4. **实现嵌入模型封装** (`src/index/embedder.py`)
   - 模型加载
   - 批量嵌入
   - 缓存机制

5. **创建 MCP 服务器框架** (`src/server.py`)
   - FastMCP 初始化
   - 工具注册
   - 错误处理

---

## 📚 参考文档

- [GitHub 调研报告](../../.nanobot/workspace/Obsidian-MCP 工具分类调研.md)
- [完整实施计划](docs/IMPLEMENTATION_PLAN_FULL.md)
- [项目结构说明](docs/PROJECT_STRUCTURE.md)

---

## 🎉 项目状态

**当前状态**: 规划完成 ✅  
**下一阶段**: Phase 1 实施 🚧  
**进度**: 5% (项目初始化完成)

---

**报告生成**: 2026-03-27 19:15  
**负责人**: @fallleaf
