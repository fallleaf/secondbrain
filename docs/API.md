# SecondBrain API 文档

## 概述
SecondBrain 是一个基于优先级分类的 Obsidian Vault 管理工具，支持语义搜索、关键词搜索和混合检索。

## 核心模块

### 1. 索引模块 (`src/index/`)

#### Embedder (文本嵌入)
```python
from src.index import Embedder

# 初始化
embedder = Embedder(
    model_name="BAAI/bge-small-zh-v1.5",  # 默认模型
    cache_dir="~/.cache/secondbrain/fastembed",
    max_length=512,
    batch_size=256
)

# 编码文本
texts = ["句子1", "句子2"]
embeddings = embedder.encode(texts)  # shape: (num_texts, 512)

# 编码单个文本
emb = embedder.encode_single("单个句子")

# 获取维度
dim = embedder.embedding_dim  # 512

# 相似度计算
sim = embedder.similarity("文本1", "文本2")

# 查找相似文本
results = embedder.find_similar("查询", ["候选1", "候选2", ...], top_k=5)
```

#### Chunker (文本分块)
```python
from src.index import Chunker

chunker = Chunker(
    chunk_size=800,
    chunk_overlap=150
)

chunks = chunker.chunk("长文本内容...")
# 返回：["块1", "块2", ...]
```

#### SemanticIndex (语义索引)
```python
from src.index import SemanticIndex

# 初始化
index = SemanticIndex(
    index_path="~/.local/share/secondbrain/semantic_index.db",
    dim=512
)

# 添加文档
index.add_document(
    doc_id="note_001",
    text="文档内容...",
    metadata={"file_path": "03.日记/2026-03-28.md", "priority": 5}
)

# 批量添加
index.add_documents([
    {"doc_id": "id1", "text": "内容1", "metadata": {...}},
    {"doc_id": "id2", "text": "内容2", "metadata": {...}}
])

# 语义搜索
results = index.search(
    query="搜索关键词",
    top_k=10,
    filter_expr="priority > 3"  # 可选过滤
)

# 获取统计
stats = index.get_stats()
# {"total_docs": 133, "total_chunks": 1250, "dim": 512}

# 重建索引
index.rebuild()
```

#### KeywordIndex (关键词索引)
```python
from src.index import KeywordIndex

index = KeywordIndex(
    db_path="~/.local/share/secondbrain/keyword_index.db",
    backend="sqlite_fts5"  # 或 "bm25"
)

# 添加文档
index.add_document(doc_id="id1", text="内容", metadata={})

# 关键词搜索
results = index.search(query="关键词", top_k=10)
```

#### HybridRetriever (混合检索)
```python
from src.index import HybridRetriever

retriever = HybridRetriever(
    semantic_index=semantic_idx,
    keyword_index=keyword_idx,
    priority_config=priority_config
)

# 混合搜索 (默认 RRF 融合)
results = retriever.search(
    query="搜索词",
    mode="hybrid",  # "hybrid", "semantic", "keyword"
    top_k=10,
    priority_weight=1.5  # 优先级加权系数
)

# 返回格式
# [
#   {"doc_id": "id1", "score": 0.95, "metadata": {...}, "rank": 1},
#   ...
# ]
```

### 2. 工具模块 (`src/tools/`)

#### SecondBrainTools (MCP 工具集)
```python
from src.tools import SecondBrainTools

tools = SecondBrainTools(config_path="~/.config/secondbrain/config.yaml")

# 语义搜索
results = tools.semantic_search(
    query="网络三性",
    mode="keyword",  # "hybrid", "semantic", "keyword"
    top_k=5,
    vault_name="personal"
)

# 读取笔记
content = tools.read_note(path="03.日记/2026-03-28.md", vault_name="personal")

# 写入笔记
tools.write_note(
    path="05.工作/会议.md",
    content="# 会议记录\n...",
    overwrite=False,
    vault_name="personal"
)

# 列出笔记
notes = tools.list_notes(directory="03.日记/", recursive=True, vault_name="personal")

# 删除笔记 (软删除)
tools.delete_note(path="03.日记/旧笔记.md", vault_name="personal")

# 移动笔记
tools.move_note(
    source="03.日记/旧.md",
    destination="09.归档/旧.md",
    update_links=True,
    vault_name="personal"
)

# 关键词搜索
results = tools.search_notes(query="极简网络", max_results=20, vault_name="personal")

# 获取索引统计
stats = tools.get_index_stats(vault_name="personal")

# 重建索引
tools.rebuild_semantic_index(full=False, vault_name="personal")

# 获取优先级配置
config = tools.get_priority_config()

# 获取笔记信息
info = tools.get_note_info(path="03.日记/2026-03-28.md", vault_name="personal")
# {"title": "日记", "tags": ["工作"], "priority": 5, "links": 3, "backlinks": 2}

# 获取标签
tags = tools.get_note_tags(path="03.日记/2026-03-28.md", vault_name="personal")

# 获取链接
links = tools.get_note_links(path="03.日记/2026-03-28.md", vault_name="personal")
# {"outgoing": [...], "incoming": [...]}

# 获取反向链接
backlinks = tools.get_backlinks(path="03.日记/2026-03-28.md", vault_name="personal")

# 查找断裂链接
broken = tools.find_broken_links(vault_name="personal")

# 查找孤立笔记
orphaned = tools.find_orphaned_notes(vault_name="personal")

# 设置优先级
tools.set_note_priority(path="03.日记/2026-03-28.md", priority=7, vault_name="personal")

# 列出所有标签
all_tags = tools.list_tags(vault_name="personal")
```

### 3. 配置模块 (`src/config/`)

```python
from src.config import load_config

# 加载配置
config = load_config(config_path="~/.config/secondbrain/config.yaml")

# 访问配置
vaults = config.vaults  # List[VaultConfig]
semantic = config.index.semantic  # SemanticIndexConfig
priority = config.priority  # PriorityConfig

# 创建默认配置
from src.config import create_default_config
path = create_default_config("~/.config/secondbrain/config.yaml")
```

## 配置示例

### config.yaml
```yaml
vaults:
  - path: "~/NanobotMemory"
    name: "personal"
    enabled: true

index:
  semantic:
    enabled: true
    model: "BAAI/bge-small-zh-v1.5"
    chunk_size: 800
    chunk_overlap: 150
    db_path: "~/.local/share/secondbrain/semantic_index.db"
  keyword:
    enabled: true
    backend: "sqlite_fts5"
    db_path: "~/.local/share/secondbrain/keyword_index.db"

priority:
  config_path: "~/.config/secondbrain/priority_config.yaml"
  enabled: true
  default_priority: 3

security:
  max_read_size: 1048576
  max_batch_size: 20
  require_confirm_delete: true
  excluded_dirs: [".obsidian", ".trash", ".git"]

logging:
  level: "INFO"
  file: "~/.local/share/secondbrain/mcp.log"
  max_size: 10485760
  backup_count: 5
```

### priority_config.yaml
```yaml
levels:
  - priority: 9
    tags: ["central_gov"]
    description: "中央政府、国家级文件"
    retention_days: -1  # 永久
    weight: 2.0
  - priority: 7
    tags: ["ministry_gov"]
    description: "部委、省级文件"
    retention_days: 3650  # 10 年
    weight: 1.6
  - priority: 5
    tags: ["company"]
    description: "公司文档、项目文件"
    retention_days: 1095  # 3 年
    weight: 1.2
  - priority: 3
    tags: ["personal_work"]
    description: "个人工作笔记"
    retention_days: 365  # 1 年
    weight: 1.0
  - priority: 1
    tags: ["web"]
    description: "网络收集、待验证"
    retention_days: 90
    weight: 0.8

default_priority: 3
```

## 性能指标

### 索引构建性能
- **单文档处理**: ~50-100ms (取决于文档大小)
- **批量处理**: ~1000 文档/分钟
- **模型加载**: ~2-5 秒 (首次), ~0.5 秒 (缓存后)
- **向量生成**: ~10-20ms/文本块

### 搜索性能
- **语义搜索**: ~10-50ms (1000 文档)
- **关键词搜索**: ~5-20ms
- **混合检索**: ~15-70ms
- **结果排序**: ~1-5ms

### 内存占用
- **模型加载**: ~200-500MB
- **索引数据库**: ~50-200MB (取决于文档数量)
- **运行时**: ~300-800MB

## 最佳实践

1. **增量更新**: 使用 `auto_detect_and_index.py` 自动检测文件变化
2. **批量操作**: 使用 `batch_operations.py` 批量处理笔记
3. **优先级加权**: 在搜索时设置 `priority_weight` 提高重要文档排名
4. **缓存管理**: 定期清理 `~/.cache/secondbrain/` 释放空间
5. **日志监控**: 查看 `~/.local/share/secondbrain/mcp.log` 监控性能

## 故障排除

### 常见问题
1. **模型加载失败**: 检查网络连接，或手动下载模型到缓存目录
2. **索引损坏**: 运行 `rebuild_semantic_index(full=True)` 重建
3. **性能下降**: 检查 `chunk_size` 设置，优化分块策略
4. **权限错误**: 确保对 Vault 目录有读写权限

### 调试模式
```python
import logging
logging.getLogger("secondbrain").setLevel(logging.DEBUG)
```
