# SecondBrain

**基于优先级分类的 Obsidian Vault 管具**

SecondBrain 是一个基于优先级分类的 Obsidian Vault 管理工具，支持语义搜索、关键词搜索和混合检索。

## 🎯 特性

- 🔍 **混合检索**: Keyword (BM25) + Semantic (向量) + Priority 加权
- 📊 **优先级系统**: 1-9 间隔分级 (中央发文→网络收集)
- ⚡ **增量更新**: checksum 检测 + sqlite-vec 增量索引
- 🗂️ **多 Vault 支持**: 配置文件指定多个目录

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/yourname/secondbrain.git
cd secondbrain

# 安装依赖
pip install -r requirements.txt

# 安装为可编辑模式
pip install -e .
```

### 配置

```bash
# 创建配置目录
mkdir -p ~/.config/secondbrain

# 复制配置模板
cp config.example.yaml ~/.config/secondbrain/config.yaml
cp priority_config.example.yaml ~/.config/secondbrain/priority_config.yaml
```

### 运行

```bash
# 启动 MCP 服务器
python -m src.server

# 或作为 MCP 工具
secondbrain
```

## 📋 工具

| 工具 | 功能 | 状态 |
|------|------|------|
| `semantic_search` | 语义搜索 (hybrid/semantic/keyword) | ✅ 可用 |
| `read_note` | 读取笔记 | ✅ 可用 |
| `write_note` | 创建/更新笔记 | ✅ 可用 |
| `list_notes` | 列出目录 | ✅ 可用 |
| `delete_note` | 软删除笔记 | ✅ 可用 |
| `move_note` | 移动/重命名 | ✅ 可用 |
| `search_notes` | 关键词搜索 | ✅ 可用 |
| `get_index_stats` | 索引统计 | ✅ 可用 |
| `rebuild_semantic_index` | 重建索引 | ✅ 可用 |
| `get_priority_config` | 优先级配置 | ✅ 可用 |

## 📊 优先级系统

| 优先级 | 标签 | 描述 | 保留期 | 权重 |
|--------|------|------|--------|------|
| 9 | central_gov | 中央政府、国家级文件 | Permanent | 2.0 |
| 7 | ministry_gov | 部委、省级文件 | 10 年 | 1.6 |
| 5 | company | 公司文档、项目文件 | 3 年 | 1.2 |
| 3 | personal_work | 个人工作笔记 | 1 年 | 1.0 |
| 1 | web | 网络收集、待验证 | 90 天 | 0.8 |

## 🧪 测试

运行单元测试：
```bash
# 安装测试依赖
pip install -e ".[dev]"

# 运行所有测试
pytest tests/ -v

# 运行测试并查看覆盖率
pytest tests/ -v --cov=src --cov-report=term-missing

# 运行特定测试类
pytest tests/test_core.py::TestEmbedder -v
```

当前覆盖率：13% (核心功能已覆盖)



## 📚 文档

### 核心文档
- [API 文档](docs/API.md) - 完整的 API 参考
- [配置指南](docs/CONFIG.md) - 详细配置说明
- [部署指南](docs/DEPLOY.md) - 生产环境部署
- [架构设计](docs/ARCHITECTURE.md) - 系统架构详解

### 历史文档
- [实施计划](docs/RELEASES/IMPLEMENTATION_PLAN_FULL.md)
- [阶段报告](docs/RELEASES/) - PHASE1-3 完成报告
- [发布说明](docs/RELEASES/RELEASE_v1_0_0.md)

### 性能指标
- 语义搜索：10-50ms (1000 文档)
- 关键词搜索：5-20ms
- 混合检索：15-70ms
- 向量生成：10-20ms/块

## 📝 许可证

MIT License

## 👥 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发指南。
