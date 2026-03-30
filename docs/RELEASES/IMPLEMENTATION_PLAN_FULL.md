
---

## 🔧 配置示例

### config.yaml 示例

```yaml
# SecondBrain MCP 配置文件
# 路径：~/.config/secondbrain/config.yaml

# Vault 配置
vaults:
  - path: ~/NanobotMemory
    name: personal
    enabled: true
  - path: ~/Work/Notes
    name: work
    enabled: true

# 索引设置
index:
  semantic:
    enabled: true
    model: BAAI/bge-small-zh-v1.5
    chunk_size: 800
    chunk_overlap: 150
    db_path: ~/.local/share/secondbrain/semantic_index.db
  keyword:
    enabled: true
    backend: sqlite_fts5

# 优先级配置
priority:
  config_path: ~/.config/secondbrain/priority_config.yaml
  enabled: true
  default_priority: 3

# 安全设置
security:
  max_read_size: 1048576  # 1MB
  max_batch_size: 20
  require_confirm_delete: true
  excluded_dirs:
    - .obsidian
    - .trash
    - .git

# 日志设置
logging:
  level: INFO
  file: ~/.local/share/secondbrain/mcp.log
  max_size: 10485760  # 10MB
  backup_count: 5
```

### priority_config.yaml 示例

```yaml
# 优先级配置 (1-9 间隔分级)

priority_levels:
  - priority: 9
    label: central_gov
    description: 中央政府、国务院、国家级文件
    retention_days: null  # permanent
    search_weight: 2.0
    path_patterns:
      - "07.项目/国家政策/*"
      - "08.技术/国家标准/*"
    sub_categories:
      - name: state_council
        patterns: ["国务院/*", "国发/*"]

  - priority: 7
    label: ministry_gov
    description: 部委、省级政府文件
    retention_days: 3650  # 10 年
    search_weight: 1.6
    path_patterns:
      - "07.项目/部委文件/*"
      - "08.技术/行业标准/*"

  - priority: 5
    label: company
    description: 公司文档、项目文件
    retention_days: 1095  # 3 年
    search_weight: 1.2
    path_patterns:
      - "05.工作/*"
      - "07.项目/*"

  - priority: 3
    label: personal_work
    description: 个人工作笔记
    retention_days: 365  # 1 年
    search_weight: 1.0
    path_patterns:
      - "03.日记/*"
      - "06.学习/*"

  - priority: 1
    label: web
    description: 网络收集、待验证信息
    retention_days: 90
    search_weight: 0.8
    path_patterns:
      - "02.收集/*"
      - "01.闪念/*"

# 默认配置
default:
  priority: 3
  retention_days: 365
  search_weight: 1.0
```

---

## 🧪 测试策略

### 单元测试

```python
# tests/test_search.py
class TestSemanticSearch:
    def test_hybrid_search(self):
        """测试混合检索"""
        pass
    
    def test_priority_weighting(self):
        """测试优先级加权"""
        pass
    
    def test_keyword_search(self):
        """测试关键词搜索"""
        pass

class TestPriorityClassifier:
    def test_path_matching(self):
        """测试路径匹配"""
        pass
    
    def test_weight_calculation(self):
        """测试权重计算"""
        pass
```

### 集成测试

```python
# tests/test_integration.py
class TestMCPTools:
    def test_search_and_read(self):
        """测试搜索 + 读取流程"""
        pass
    
    def test_write_and_verify(self):
        """测试写入 + 验证流程"""
        pass
```

### 性能测试

```python
# tests/test_performance.py
class TestPerformance:
    def test_search_latency(self):
        """测试搜索延迟 (P95 <10ms)"""
        pass
    
    def test_index_build_time(self):
        """测试索引构建时间"""
        pass
```

---

## 📦 依赖管理

### requirements.txt

```txt
# MCP 框架
mcp>=1.0.0
fastmcp>=0.1.0

# 向量化
sentence-transformers>=2.2.0
faiss-cpu>=1.7.4
# 或
sqlite-vec>=0.1.0

# 关键词索引
rank-bm25>=0.2.2

# 文本处理
pyyaml>=6.0
frontmatter>=1.0.0
markdown>=3.4.0

# 文件监控
watchdog>=3.0.0

# 工具
pydantic>=2.0.0
httpx>=0.24.0
aiofiles>=23.0.0

# 测试
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "secondbrain-mcp"
version = "0.1.0"
description = "MCP Server for SecondBrain with priority-based semantic search"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
dependencies = [
    "mcp>=1.0.0",
    "sentence-transformers>=2.2.0",
    "faiss-cpu>=1.7.4",
    "pyyaml>=6.0",
    "pydantic>=2.0.0",
    "watchdog>=3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
]

[project.scripts]
secondbrain-mcp = "secondbrain.server:main"

[tool.setuptools.packages.find]
where = ["src"]
```

---

## 🚀 部署方案

### 开发环境

```bash
# 克隆项目
cd ~/project/secondbrain

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装为可编辑模式
pip install -e .

# 运行服务器
python -m secondbrain.server
```

### 生产环境 (systemd 服务)

```ini
# /etc/systemd/system/secondbrain-mcp.service
[Unit]
Description=SecondBrain MCP Server
After=network.target

[Service]
Type=simple
User=fallleaf
WorkingDirectory=/home/fallleaf/project/secondbrain
Environment="PATH=/home/fallleaf/project/secondbrain/venv/bin"
ExecStart=/home/fallleaf/project/secondbrain/venv/bin/python -m secondbrain.server
Restart=always
RestartSec=10

# 内存限制
MemoryMax=2G
MemoryHigh=1.5G

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable secondbrain-mcp
sudo systemctl start secondbrain-mcp
sudo systemctl status secondbrain-mcp
```

---

## 📊 里程碑

| 里程碑 | 目标日期 | 交付物 |
|--------|---------|--------|
| **M1: Phase 1 完成** | 2026-04-10 | 核心搜索工具可用 |
| **M2: Phase 2 完成** | 2026-04-24 | 完整 CRUD 工具集 |
| **M3: Phase 3 完成** | 2026-05-15 | 批量操作 + 索引管理 |
| **M4: Phase 4 完成** | 2026-05-29 | 高级功能 + 文档完善 |
| **M5: v1.0 发布** | 2026-06-05 | PyPI 发布 + 文档 |

---

## 📈 成功指标

### 性能指标
- [ ] 搜索延迟 P95 < 10ms (hybrid 模式)
- [ ] 索引构建速度 > 1000 文档/分钟
- [ ] 内存占用 < 1.5GB (10 万文档)
- [ ] 增量更新延迟 < 5s

### 功能指标
- [ ] 支持 10+ MCP 工具
- [ ] 支持 3 种搜索模式 (keyword/semantic/hybrid)
- [ ] 支持 5 级优先级分类
- [ ] 支持多 Vault 配置

### 质量指标
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过率 100%
- [ ] 文档完整度 100%

---

## ⚠️ 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 向量模型加载慢 | 高 | 中 | 预加载 + 缓存 |
| FAISS 索引内存占用高 | 中 | 中 | 使用 sqlite-vec 替代 |
| 大文件索引超时 | 中 | 低 | 分块处理 + 进度条 |
| 路径遍历攻击 | 高 | 低 | 严格路径验证 |
| 并发写入冲突 | 中 | 低 | 文件锁 + 原子写入 |

---

## 📚 参考文档

- [MCP Protocol](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [FAISS Documentation](https://faiss.ai/)
- [sqlite-vec](https://github.com/asg017/sqlite-vec)
- [GitHub 调研报告](../../../.nanobot/workspace/Obsidian-MCP 工具分类调研.md)

---

## ✅ 下一步行动

1. **立即**: 创建项目目录结构
2. **本周**: 完成 Phase 1 任务 (P1-01 ~ P1-05)
3. **下周**: 完成 Phase 1 剩余任务 (P1-06 ~ P1-13)
4. **4 月初**: 启动 Phase 2

---

**文档状态**: 初稿  
**最后更新**: 2026-03-27  
**负责人**: @fallleaf
