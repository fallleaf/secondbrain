# SecondBrain MCP 实施计划

**项目名称**: SecondBrain MCP Server  
**创建时间**: 2026-03-27  
**版本**: v0.1.0  
**状态**: 规划阶段

---

## 📋 项目概述

### 目标
构建一个基于 MCP (Model Context Protocol) 的 Obsidian Vault 管理服务器，支持语义搜索、优先级分类、批量操作等功能。

### 核心特性
1. **混合检索**: Keyword (BM25) + Semantic (向量) + Priority 加权
2. **优先级系统**: 1-9 间隔分级 (中央发文→网络收集)
3. **增量更新**: checksum 检测 + sqlite-vec 增量索引
4. **多 Vault 支持**: 配置文件指定多个目录
5. **本地优先**: 直接文件系统访问，无需 Obsidian 运行时

---

## 🏗️ 技术架构

### 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| **语言** | Python 3.10+ | 主开发语言 |
| **MCP 框架** | FastMCP / MCP SDK | Model Context Protocol |
| **向量索引** | FAISS / sqlite-vec | 语义搜索 |
| **关键词索引** | SQLite FTS5 / BM25 | 全文检索 |
| **嵌入模型** | BAAI/bge-small-zh-v1.5 | 中文优化 |
| **配置管理** | PyYAML | YAML 配置文件 |
| **文件监控** | watchdog | 增量更新触发 |

### 目录结构

```
secondbrain/
├── src/
│   ├── __init__.py
│   ├── server.py              # MCP 服务器入口
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py        # 配置加载
│   │   └── priority_config.yaml  # 优先级配置
│   ├── index/
│   │   ├── __init__.py
│   │   ├── chunker.py         # 文本分块
│   │   ├── embedder.py        # 向量化
│   │   ├── keyword_index.py   # BM25/FTS5 索引
│   │   ├── semantic_index.py  # FAISS/向量索引
│   │   └── hybrid_retriever.py # 混合检索
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── search.py          # 搜索工具
│   │   ├── read.py            # 读取工具
│   │   ├── write.py           # 写入工具
│   │   ├── delete.py          # 删除工具
│   │   ├── move.py            # 移动工具
│   │   ├── batch.py           # 批量操作
│   │   ├── index_mgmt.py      # 索引管理
│   │   └── meta.py            # 元数据工具
│   └── utils/
│       ├── __init__.py
│       ├── filesystem.py      # 文件系统操作
│       ├── validators.py      # 路径验证
│       └── frontmatter.py     # Frontmatter 解析
├── tests/
│   ├── __init__.py
│   ├── test_search.py
│   ├── test_index.py
│   └── test_tools.py
├── docs/
│   ├── API.md
│   ├── CONFIG.md
│   └── DEPLOY.md
├── scripts/
│   ├── build_index.py
│   └── migrate.py
├── pyproject.toml
├── requirements.txt
├── README.md
└── IMPLEMENTATION_PLAN.md  # 本文档
```

---

## 📅 实施阶段

### Phase 1: 核心搜索工具 (1-2 周)

**目标**: 实现基础搜索功能，支持混合检索和优先级过滤

#### 任务清单

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P1-01 | 项目初始化 (目录、依赖) | `pyproject.toml` | P0 | ⏳ |
| P1-02 | 配置文件加载器 | `src/config/settings.py` | P0 | ⏳ |
| P1-03 | 优先级分类器实现 | `src/utils/priority.py` | P0 | ⏳ |
| P1-04 | 文本分块器 | `src/index/chunker.py` | P0 | ⏳ |
| P1-05 | 嵌入模型封装 | `src/index/embedder.py` | P0 | ⏳ |
| P1-06 | 关键词索引 (BM25/FTS5) | `src/index/keyword_index.py` | P0 | ⏳ |
| P1-07 | 语义索引 (FAISS/sqlite-vec) | `src/index/semantic_index.py` | P0 | ⏳ |
| P1-08 | 混合检索器 (RRF 融合) | `src/index/hybrid_retriever.py` | P0 | ⏳ |
| P1-09 | MCP 服务器框架 | `src/server.py` | P0 | ⏳ |
| P1-10 | `semantic_search` 工具 | `src/tools/search.py` | P0 | ⏳ |
| P1-11 | `read_note` 工具 | `src/tools/read.py` | P1 | ⏳ |
| P1-12 | `list_notes` 工具 | `src/tools/read.py` | P1 | ⏳ |
| P1-13 | 单元测试 | `tests/test_search.py` | P1 | ⏳ |

#### 交付物
- ✅ 可运行的 MCP 服务器
- ✅ 支持 hybrid/semantic/keyword 三种搜索模式
- ✅ 优先级加权排序
- ✅ 基础读取工具

---

### Phase 2: 写入与管理工具 (1-2 周)

**目标**: 实现笔记写入、删除、移动等核心管理功能

#### 任务清单

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P2-01 | `write_note` 工具 (原子写入) | `src/tools/write.py` | P0 | ⏳ |
| P2-02 | Frontmatter 合并逻辑 | `src/utils/frontmatter.py` | P1 | ⏳ |
| P2-03 | `delete_note` 工具 (软删除) | `src/tools/delete.py` | P0 | ⏳ |
| P2-04 | `move_note` 工具 (自动更新链接) | `src/tools/move.py` | P1 | ⏳ |
| P2-05 | `search_notes` 关键词搜索 | `src/tools/search.py` | P1 | ⏳ |
| P2-06 | `search_frontmatter` 工具 | `src/tools/search.py` | P1 | ⏳ |
| P2-07 | 路径验证与安全机制 | `src/utils/validators.py` | P0 | ⏳ |
| P2-08 | 集成测试 | `tests/test_tools.py` | P1 | ⏳ |

#### 交付物
- ✅ 完整的 CRUD 工具集
- ✅ 原子写入 (write-to-temp-then-rename)
- ✅ 软删除 (.trash/)
- ✅ 路径安全验证

---

### Phase 3: 批量操作与索引管理 (2-3 周)

**目标**: 实现批量操作和索引管理功能

#### 任务清单

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P3-01 | `batch_update_frontmatter` 工具 | `src/tools/batch.py` | P1 | ⏳ |
| P3-02 | `batch_delete` 工具 | `src/tools/batch.py` | P1 | ⏳ |
| P3-03 | `rebuild_semantic_index` 工具 | `src/tools/index_mgmt.py` | P1 | ⏳ |
| P3-04 | `get_index_stats` 工具 | `src/tools/index_mgmt.py` | P1 | ⏳ |
| P3-05 | 增量索引更新 (watchdog) | `src/index/watcher.py` | P1 | ⏳ |
| P3-06 | Checksum 检测机制 | `src/index/chunker.py` | P1 | ⏳ |
| P3-07 | 性能优化 (并发、缓存) | `src/index/semantic_index.py` | P2 | ⏳ |
| P3-08 | 压力测试 | `tests/test_performance.py` | P2 | ⏳ |

#### 交付物
- ✅ 批量操作工具 (max 20 文件/次)
- ✅ 索引重建与统计
- ✅ 增量更新机制
- ✅ 性能基准测试报告

---

### Phase 4: 元数据与高级功能 (1-2 周)

**目标**: 实现元数据管理、标签管理、链接分析等高级功能

#### 任务清单

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P4-01 | `get_note_info` 工具 | `src/tools/meta.py` | P2 | ⏳ |
| P4-02 | `get_priority_config` 工具 | `src/tools/meta.py` | P2 | ⏳ |
| P4-03 | `set_note_priority` 工具 | `src/tools/meta.py` | P2 | ⏳ |
| P4-04 | `list_tags` 工具 | `src/tools/meta.py` | P2 | ⏳ |
| P4-05 | `get_backlinks` 工具 | `src/tools/meta.py` | P2 | ⏳ |
| P4-06 | `find_broken_links` 工具 | `src/tools/meta.py` | P3 | ⏳ |
| P4-07 | `find_orphaned_notes` 工具 | `src/tools/meta.py` | P3 | ⏳ |
| P4-08 | 文档完善 (API.md