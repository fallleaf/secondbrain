# SecondBrain 查询接口 API 设计

**创建时间**: 2026-03-31  
**版本**: v1.0  
**状态**: 设计完成  

---

## 📋 概述

统一查询接口提供一致的搜索和元数据访问功能，支持多种搜索模式和高级过滤。

---

## 🎯 核心接口

### SecondBrainQuery 类

```python
class SecondBrainQuery:
    """统一查询接口"""
    
    def __init__(self, db_path: str, vault_path: str = None):
        """
        初始化查询引擎
        
        Args:
            db_path: 数据库路径
            vault_path: Vault 根路径（用于拼接文件绝对路径）
        """
        pass
    
    def search(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        统一搜索接口
        
        Args:
            query: 搜索关键词
            mode: 搜索模式 (semantic/keyword/hybrid)
            top_k: 返回结果数
            filters: 过滤条件
                - tags: List[str] - 标签过滤
                - doc_type: str - 文档类型过滤
                - min_priority: int - 最小优先级 (1-9)
                - file_path: str - 文件路径过滤
                - date_range: tuple - 时间范围过滤 (start, end)
        
        Returns:
            List[SearchResult]: 搜索结果列表
        
        Example:
            >>> query_engine = SecondBrainQuery(db_path)
            >>> results = query_engine.search(
            ...     "人工智能",
            ...     mode="hybrid",
            ...     top_k=10,
            ...     filters={"tags": ["important"], "doc_type": "technical"}
            ... )
        """
        pass
    
    def get_note_info(self, doc_id: str) -> Dict:
        """
        获取笔记详细信息
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            Dict: 笔记信息
                {
                    "doc_id": "...",
                    "file_path": "...",
                    "title": "...",
                    "tags": [...],
                    "priority": 5,
                    "doc_type": "technical",
                    "link_count": 10,
                    "backlink_count": 5,
                    "created_at": "...",
                    "updated_at": "..."
                }
        """
        pass
    
    def get_note_tags(self, doc_id: str) -> List[str]:
        """获取笔记的标签列表"""
        pass
    
    def get_backlinks(self, doc_id: str) -> List[Dict]:
        """
        获取笔记的反向链接
        
        Returns:
            List[Dict]: 反向链接列表
                [
                    {
                        "source_doc_id": "...",
                        "source_file_path": "...",
                        "link_text": "...",
                        "link_type": "internal"
                    }
                ]
        """
        pass
    
    def get_links(self, doc_id: str) -> List[Dict]:
        """获取笔记的出站链接"""
        pass
    
    def find_broken_links(self) -> List[Dict]:
        """查找所有断裂链接"""
        pass
    
    def find_orphaned_notes(self) -> List[str]:
        """查找孤立笔记（无入链）"""
        pass
    
    def get_index_stats(self) -> Dict:
        """
        获取索引统计信息
        
        Returns:
            Dict: 统计信息
                {
                    "doc_count": 137,
                    "chunk_count": 1919,
                    "tag_count": 50,
                    "link_count": 200,
                    "broken_link_count": 5,
                    "file_count": 137,
                    "doc_type_distribution": {...},
                    "tag_usage_stats": [...]
                }
        """
        pass
    
    def list_tags(self, vault_name: str = None) -> List[Dict]:
        """列出所有标签及使用情况"""
        pass
    
    def search_by_tags(
        self,
        tags: List[str],
        mode: str = "any",
        top_k: int = 10
    ) -> List[Dict]:
        """
        按标签搜索笔记
        
        Args:
            tags: 标签列表
            mode: 匹配模式 (any/all)
            top_k: 返回结果数
        
        Returns:
            List[Dict]: 匹配的笔记信息
        """
        pass
```

---

## 📦 数据模型

### SearchResult

```python
@dataclass
class SearchResult:
    """搜索结果"""
    doc_id: str
    score: float
    content: str
    file_path: str
    start_line: int = 0
    end_line: int = 0
    source: str = "hybrid"  # semantic/keyword/hybrid
    metadata: Dict[str, Any] = None
    tags: List[str] = None
    doc_type: str = "default"
    priority: int = 5
    
    def __post_init__(self):
        """确保字段初始化"""
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = self.metadata.get("tags", [])
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "doc_id": self.doc_id,
            "score": self.score,
            "content": self.content,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "source": self.source,
            "metadata": self.metadata,
            "tags": self.tags,
            "doc_type": self.doc_type,
            "priority": self.priority
        }
```

### FilterOptions

```python
@dataclass
class FilterOptions:
    """过滤选项"""
    tags: Optional[List[str]] = None
    doc_type: Optional[str] = None
    min_priority: Optional[int] = None
    file_path: Optional[str] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    vault_name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items() if v is not None
        }
```

---

## 🔍 搜索模式

### 1. 语义搜索 (semantic)

- **原理**: 向量相似度搜索
- **适用场景**: 模糊查询、概念搜索
- **特点**: 理解语义，支持同义词

```python
# 示例
results = query_engine.search(
    "低成本建网思路",
    mode="semantic",
    top_k=10
)
```

### 2. 关键词搜索 (keyword)

- **原理**: FTS5 全文检索
- **适用场景**: 精确词匹配、专有名词
- **特点**: 精确匹配，支持通配符

```python
# 示例
results = query_engine.search(
    "网络三性",
    mode="keyword",
    top_k=10
)
```

### 3. 混合检索 (hybrid)

- **原理**: RRF 融合 + 优先级加权
- **适用场景**: 通用搜索
- **特点**: 结合语义和关键词优势

```python
# 示例
results = query_engine.search(
    "AI 技术",
    mode="hybrid",
    top_k=10,
    filters={"tags": ["important"]}
)
```

---

## 🎚️ 高级过滤

### 标签过滤

```python
# 单个标签
results = query_engine.search(
    "网络优化",
    filters={"tags": ["work"]}
)

# 多个标签 (AND 逻辑)
results = query_engine.search(
    "技术文档",
    filters={"tags": ["work", "important"]}
)
```

### 文档类型过滤

```python
results = query_engine.search(
    "技术",
    filters={"doc_type": "technical"}
)
```

### 优先级过滤

```python
# 高优先级文档
results = query_engine.search(
    "政策",
    filters={"min_priority": 7}
)
```

### 文件路径过滤

```python
results = query_engine.search(
    "配置",
    filters={"file_path": "05.工作/"}
)
```

### 组合过滤

```python
results = query_engine.search(
    "网络优化",
    filters={
        "tags": ["work", "important"],
        "doc_type": "technical",
        "min_priority": 6,
        "file_path": "05.工作/"
    }
)
```

---

## 📊 元数据查询

### 获取笔记信息

```python
info = query_engine.get_note_info("doc_001")
print(info)
# {
#     "doc_id": "doc_001",
#     "file_path": "05.工作/会议.md",
#     "title": "网络优化会议",
#     "tags": ["work", "meeting"],
#     "priority": 7,
#     "doc_type": "meeting",
#     "link_count": 5,
#     "backlink_count": 3,
#     "created_at": "2026-03-30T10:00:00",
#     "updated_at": "2026-03-30T15:00:00"
# }
```

### 获取反向链接

```python
backlinks = query_engine.get_backlinks("doc_001")
for link in backlinks:
    print(f"{link['source_file_path']} -> {link['link_text']}")
```

### 查找断裂链接

```python
broken = query_engine.find_broken_links()
for link in broken:
    print(f"{link['source_file_path']}: {link['target_file_path']} (断裂)")
```

### 查找孤立笔记

```python
orphaned = query_engine.find_orphaned_notes()
print(f"发现 {len(orphaned)} 个孤立笔记")
```

---

## 📈 统计功能

### 索引统计

```python
stats = query_engine.get_index_stats()
print(f"文档数：{stats['doc_count']}")
print(f"分块数：{stats['chunk_count']}")
print(f"标签数：{stats['tag_count']}")
print(f"断裂链接：{stats['broken_link_count']}")
```

### 标签列表

```python
tags = query_engine.list_tags()
for tag in tags[:10]:
    print(f"{tag['tag_name']}: {tag['actual_count']} 次")
```

### 文档类型分布

```python
stats = query_engine.get_index_stats()
for doc_type, count in stats['doc_type_distribution'].items():
    print(f"{doc_type}: {count}")
```

---

## 🚀 性能优化

### 查询缓存

```python
# 自动缓存（默认 5 分钟）
results1 = query_engine.search("人工智能")  # 执行搜索
results2 = query_engine.search("人工智能")  # 从缓存获取

# 手动清除缓存
query_engine.cache.invalidate(pattern="*人工智能*")
```

### 批量查询

```python
# 批量获取笔记信息
doc_ids = ["doc_001", "doc_002", "doc_003"]
infos = query_engine.batch_get_note_info(doc_ids)
```

---

## 🧪 使用示例

### 完整示例

```python
from src.query.query_engine import SecondBrainQuery

# 初始化
query_engine = SecondBrainQuery(
    db_path="~/.local/share/secondbrain/semantic_index.db",
    vault_path="~/NanobotMemory"
)

# 1. 混合搜索 + 高级过滤
results = query_engine.search(
    "网络优化",
    mode="hybrid",
    top_k=10,
    filters={
        "tags": ["work", "important"],
        "doc_type": "technical",
        "min_priority": 6
    }
)

# 2. 打印结果
for i, result in enumerate(results, 1):
    print(f"{i}. {result.file_path} (score: {result.score:.4f})")
    print(f"   Tags: {', '.join(result.tags)}")
    print(f"   Content: {result.content[:100]}...")
    print()

# 3. 获取统计信息
stats = query_engine.get_index_stats()
print(f"总文档数：{stats['doc_count']}")
print(f"总标签数：{stats['tag_count']}")

# 4. 查找断裂链接
broken = query_engine.find_broken_links()
if broken:
    print(f"\n发现 {len(broken)} 个断裂链接:")
    for link in broken:
        print(f"  - {link['source_file_path']} -> {link['target_file_path']}")
```

---

## 📝 实现说明

### 模块结构

```
src/query/
├── __init__.py
├── query_engine.py        # SecondBrainQuery 主类
├── semantic_search.py     # 语义搜索模块
├── keyword_search.py      # 关键词搜索模块
├── hybrid_search.py       # 混合检索模块
├── filters.py             # 过滤器模块
├── metadata.py            # 元数据查询模块
├── index_stats.py         # 索引统计模块
└── cache.py               # 查询缓存模块
```

### 依赖关系

```
query_engine.py
├── semantic_search.py
├── keyword_search.py
├── hybrid_search.py
├── filters.py
├── metadata.py
├── index_stats.py
└── cache.py
```

---

## 🎯 成功标准

- ✅ 支持 3 种搜索模式
- ✅ 支持 5 种高级过滤
- ✅ 查询响应时间 <100ms (P95)
- ✅ 查询缓存命中率 >80%
- ✅ 单元测试覆盖率 >90%

---

**下一步**: 开始实现各模块代码
