# SecondBrain 项目结构

**生成时间**: 2026-03-27  
**版本**: v0.1.0

---

## 📁 目录结构

```
secondbrain/
├── 📄 README.md                      # 项目说明
├── 📄 IMPLEMENTATION_PLAN.md         # 实施计划 (简版)
├── 📄 pyproject.toml                 # Python 项目配置
├── 📄 requirements.txt               # Python 依赖
├── 📄 config.example.yaml            # 配置模板
├── 📄 priority_config.example.yaml   # 优先级配置模板
│
├── 📂 src/                           # 源代码
│   ├── __init__.py
│   ├── config/                       # 配置模块
│   │   └── __init__.py
│   ├── index/                        # 索引模块
│   │   └── __init__.py
│   ├── tools/                        # MCP 工具
│   │   └── __init__.py
│   └── utils/                        # 工具函数
│       └── __init__.py
│
├── 📂 tests/                         # 测试代码
│   └── __init__.py
│
├── 📂 scripts/                       # 工具脚本
│   └── build_index.py                # 索引构建脚本
│
└── 📂 docs/                          # 文档
    └── IMPLEMENTATION_PLAN_FULL.md   # 完整实施计划
```

---

## 📋 文件说明

### 核心文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `README.md` | 项目说明和快速开始 | ✅ 已完成 |
| `IMPLEMENTATION_PLAN.md` | 实施计划 (简版) | ✅ 已完成 |
| `pyproject.toml` | Python 项目配置 | ✅ 已完成 |
| `requirements.txt` | 依赖列表 | ✅ 已完成 |

### 配置文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `config.example.yaml` | 主配置模板 | ✅ 已完成 |
| `priority_config.example.yaml` | 优先级配置模板 | ✅ 已完成 |

### 源代码模块

| 模块 | 说明 | 待实现文件 |
|------|------|-----------|
| `src/config/` | 配置加载 | `settings.py` |
| `src/index/` | 索引管理 | `chunker.py`, `embedder.py`, `keyword_index.py`, `semantic_index.py`, `hybrid_retriever.py` |
| `src/tools/` | MCP 工具 | `search.py`, `read.py`, `write.py`, `delete.py`, `move.py`, `batch.py`, `index_mgmt.py`, `meta.py` |
| `src/utils/` | 工具函数 | `filesystem.py`, `validators.py`, `frontmatter.py`, `priority.py` |

### 测试

| 文件 | 说明 | 状态 |
|------|------|------|
| `tests/test_search.py` | 搜索测试 | ⏳ 待创建 |
| `tests/test_index.py` | 索引测试 | ⏳ 待创建 |
| `tests/test_tools.py` | 工具测试 | ⏳ 待创建 |

### 脚本

| 脚本 | 说明 | 状态 |
|------|------|------|
| `scripts/build_index.py` | 索引构建 | 🚧 框架已完成 |
| `scripts/migrate.py` | 数据迁移 | ⏳ 待创建 |

---

## 🎯 下一步行动

### Phase 1 (本周)

1. **创建核心模块**
   - [ ] `src/config/settings.py` - 配置加载器
   - [ ] `src/utils/priority.py` - 优先级分类器
   - [ ] `src/index/chunker.py` - 文本分块器
   - [ ] `src/index/embedder.py` - 嵌入模型封装

2. **创建 MCP 服务器框架**
   - [ ] `src/server.py` - MCP 服务器入口

3. **实现第一个工具**
   - [ ] `src/tools/search.py` - `semantic_search` 工具

### 开发环境设置

```bash
cd ~/project/secondbrain

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装为可编辑模式
pip install -e .

# 运行测试
pytest tests/ -v
```

---

## 📊 进度追踪

| 阶段 | 任务数 | 已完成 | 进度 |
|------|--------|--------|------|
| Phase 1 | 13 | 0 | 0% |
| Phase 2 | 8 | 0 | 0% |
| Phase 3 | 8 | 0 | 0% |
| Phase 4 | 8 | 0 | 0% |
| **总计** | **37** | **0** | **0%** |

---

## 🔗 相关文档

- [完整实施计划](docs/IMPLEMENTATION_PLAN_FULL.md)
- [GitHub 调研报告](../../.nanobot/workspace/Obsidian-MCP 工具分类调研.md)
- [MCP Protocol](https://modelcontextprotocol.io/)

---

**最后更新**: 2026-03-27  
**维护者**: @fallleaf
