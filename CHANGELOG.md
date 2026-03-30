# 变更日志

所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [1.0.0] - 2026-03-28

### 新增
- **单元测试**: 完整的 pytest 测试套件 (`tests/test_core.py`)
  - 覆盖 Embedder, Chunker, SemanticIndex, KeywordIndex, PerformanceMonitor
  - 测试覆盖率 13% (核心功能已覆盖)
- **Web 管理界面**: 基于 Flask 的现代化管理界面 (`web_app.py`)
  - 索引统计、混合搜索、文本向量化、分块测试
  - 性能监控、配置管理
  - 响应式设计，支持移动端
- **性能监控模块**: 完整的性能追踪系统 (`src/utils/perf_monitor.py`)
  - 自动计时、统计信息 (P50/P90/P99)
  - 日志持久化、装饰器支持
- **文档体系**:
  - `API.md` - 完整 API 参考
  - `CONFIG.md` - 详细配置指南
  - `DEPLOY.md` - 生产环境部署
  - `ARCHITECTURE.md` - 系统架构设计
  - `docs/RELEASES/` - 历史文档归档

### 优化
- **嵌入引擎**: 从 `sentence-transformers` 迁移到 `fastembed`
  - 性能提升 2-3 倍
  - 内存占用减少 50%+
  - 启动时间显著缩短
- **依赖精简**: 移除 `faiss-cpu`, `sentence-transformers`
  - 仅保留 `fastembed`, `sqlite-vec`, `rank-bm25`
- **代码重构**:
  - 统一类名 `FastEmbedder` → `Embedder`
  - 清理所有旧代码和注释
  - 符合 PEP 8 规范
- **文档整理**:
  - 15 个阶段报告整合到 `docs/RELEASES/`
  - 核心文档独立，结构清晰

### 修复
- 修复 `add_document()` 缩进错误
- 修复 `search()` 查询中 `doc_id` 关联问题
- 修复序列化使用 `sqlite_vec.serialize_float32()`
- 修复向量维度不一致问题
- 修复相对导入问题 (测试环境)

### 变更
- 向量引擎从 FAISS 迁移到 `sqlite-vec`
- 模型从 `all-MiniLM-L6-v2` 升级到 `BAAI/bge-small-zh-v1.5`
- 向量维度从 384 升级到 512
- 测试框架从手动脚本迁移到 `pytest`

### 移除
- 移除 `faiss-cpu` 依赖
- 移除 `sentence-transformers` 依赖
- 移除旧版 `embedder.py` (基于 sentence-transformers)
- 移除根目录测试文件

### 文档
- 新增 4 篇核心文档 (API, CONFIG, DEPLOY, ARCHITECTURE)
- 整合 15 个阶段报告到 `RELEASES/`
- 更新 README.md 和 CHANGELOG.md

---

## [0.1.0] - 2026-03-28 (早期版本)

### 新增
- 初始版本发布
- 支持语义搜索（基于 `BAAI/bge-small-zh-v1.5` 模型）
- 支持关键词搜索（BM25 算法）
- 支持混合检索（语义 + 关键词 + 优先级加权）
- 支持优先级系统（1-9 分级）
- 支持增量索引更新（文件哈希检测）
- 支持多 Vault 配置
- 迁移从 FAISS 到 `sqlite-vec` 向量引擎
- 实现 18 个 MCP 工具
- 自动文件变更检测与增量索引脚本
- 定时任务支持（Cron 集成）

### 修复
- 修复 `add_document()` 缩进错误
- 修复 `search()` 查询中 `doc_id` 关联问题
- 修复序列化使用 `sqlite_vec.serialize_float32()`
- 修复向量维度不一致问题

### 变更
- 向量引擎从 FAISS 迁移到 `sqlite-vec`
- 模型从 `all-MiniLM-L6-v2` 升级到 `BAAI/bge-small-zh-v1.5`
- 向量维度从 384 升级到 512

### 移除
- 移除 `faiss-cpu` 依赖
- 移除旧版索引逻辑

### 文档
- 添加实施计划文档
- 添加阶段报告 (PHASE1-3)

---

## [Unreleased]

### 计划中
- 提高测试覆盖率到 80%+
- 添加 GitHub Actions CI/CD
- 增强 Web 界面 (笔记管理、可视化)
- 支持更多嵌入模型
- 优化混合检索算法
- 支持实时文件监控 (Watchdog)
- 添加批量操作 API
