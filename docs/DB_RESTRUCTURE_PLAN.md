# SecondBrain 数据库结构与查询功能重新梳理

**创建时间**: 2026-03-30  
**版本**: v2.0  
**状态**: 规划阶段  
**负责人**: nanobot  

---

## 📋 当前状态分析

### 现有数据库结构

#### 1. 语义索引数据库 (`semantic_index.db`)

**表结构**:
```sql
-- 元数据表
CREATE TABLE vectors (
    doc_id TEXT PRIMARY KEY,
    metadata TEXT  -- JSON 格式，包含 tags, doc_type, frontmatter 等
);

-- 向量存储表 (sqlite-vec 虚拟表)
CREATE VIRTUAL TABLE vectors_vec USING vec0(
    doc_id TEXT PRIMARY KEY,
    embedding float[512]
);

-- 内容存储表
CREATE TABLE chunks (
    doc_id TEXT PRIMARY KEY,
    chunk_index INTEGER,
    content TEXT,
    start_line INTEGER,
    end_line INTEGER
);

-- 全文检索索引 (FTS5)
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    doc_id,
    chunk_index,
    content
);
```

**当前数据量**:
- vectors: 5001 条记录
- chunks: 5001 条记录
- vectors_vec: 5001 条记录

#### 2. 关键词索引数据库 (`keyword_index.db`)

**表结构**:
```sql
-- FTS5 全文索引
CREATE VIRTUAL TABLE documents USING fts5(
    content,
    doc_id,
    file_path,
    start_line,
    end_line
);

-- 元数据表
CREATE TABLE metadata (
    doc_id TEXT PRIMARY KEY,
    file_path TEXT,
    start_line INTEGER,
    end_line INTEGER,
    checksum TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 现有功能评估

✅ **已实现功能**:
1. 语义搜索 (sqlite-vec + BAAI/bge-small-zh-v1.5)
2. 关键词搜索 (SQLite FTS5)
3. 混合检索 (RRF 融合算法)
4. 优先级加权
5. 批量索引构建
6. AdaptiveChunker 智能分块

⚠️ **存在问题**:
1. 数据库表结构不够规范化，缺少索引统计视图
2. 查询功能分散，缺少统一的查询接口
3. 缺少高级查询功能（如标签过滤、文档类型过滤）
4. 缺少查询性能监控和优化
5. 缺少查询结果缓存机制
6. 缺少查询日志和分析功能

---

## 🎯 功能需求梳理

### 核心查询功能

#### 1. 基础搜索功能

| 功能 | 模式 | 说明 | 优先级 |
|------|------|------|--------|
| 语义搜索 | `semantic` | 向量相似度搜索 | P0 |
| 关键词搜索 | `keyword` | 全文检索 (FTS5) | P0 |
| 混合检索 | `hybrid` | RRF 融合 + 优先级加权 | P0 |

#### 2. 高级过滤功能

| 功能 | 参数 | 说明 | 优先级 |
|------|------|------|--------|
| 标签过滤 | `tags: List[str]` | 按标签过滤结果 | P0 |
| 文档类型过滤 | `doc_type: str` | FAQ/Technical/Blog/Legal | P0 |
| 优先级过滤 | `min_priority: int` | 最小优先级 (1-9) | P1 |
| 文件路径过滤 | `file_path: str` | 按文件路径过滤 | P1 |
| 时间范围过滤 | `date_range: tuple` | 创建/更新时间范围 | P2 |

#### 3. 元数据查询功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 获取笔记信息 | 标题、标签、链接数、优先级等 | P0 |
| 获取标签列表 | 所有使用的标签及统计 | P0 |
| 获取反向链接 | 哪些笔记链接到当前笔记 | P1 |
| 获取链接信息 | 出站链接和反向链接 | P1 |
| 查找断裂链接 | 所有指向不存在文件的链接 | P2 |
| 查找孤立笔记 | 没有被任何笔记链接的笔记 | P2 |

#### 4. 索引管理功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 获取索引统计 | 文档数、块数、大小等 | P0 |
| 重建语义索引 | 全量或增量重建 | P0 |
| 增量索引更新 | 监听文件变化自动更新 | P1 |
| 索引优化 | VACUUM、REINDEX 等 | P2 |

---

## 🏗️ 优化后的数据库结构

### 设计原则

1. **规范化**: 减少数据冗余，提高查询效率
2. **可扩展性**: 支持未来功能扩展
3. **性能优化**: 合理设计索引，支持快速查询
4. **兼容性**: 保持与现有数据的兼容

### 新表结构设计

```sql
-- ========================================
-- 核心表
-- ========================================

-- 1. 文档主表 (规范化文档元数据)
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    vault_name TEXT DEFAULT 'NanobotMemory',
    checksum TEXT,
    doc_type TEXT DEFAULT 'default',  -- faq/technical/blog/legal/meeting/default
    priority INTEGER DEFAULT 5,       -- 1-9
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    indexed_at TIMESTAMP
);

-- 2. 分块内容表
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,        -- doc_id#chunk_index
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    heading_level INTEGER,            -- 标题层级
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- 3. 向量存储表 (sqlite-vec)
CREATE VIRTUAL TABLE IF NOT EXISTS vectors_vec USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding float[512]
);

-- 4. 全文检索索引
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id,
    content,
    content='chunks',
    content_rowid='rowid'
);

-- ========================================
-- 元数据表
-- ========================================

-- 5. 标签表 (规范化标签管理)
CREATE TABLE IF NOT EXISTS tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT UNIQUE NOT NULL,
    usage_count INTEGER DEFAULT 0
);

-- 6. 文档 - 标签关联表
CREATE TABLE IF NOT EXISTS document_tags (
    doc_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (doc_id, tag_id),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
);

-- 7. Frontmatter 存储表 (JSON 格式)
CREATE TABLE IF NOT EXISTS frontmatter (
    doc_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,  -- JSON 格式存储完整 frontmatter
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- ========================================
-- 链接关系表
-- ========================================

-- 8. 链接表 (存储笔记间的链接关系)
CREATE TABLE IF NOT EXISTS links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_doc_id TEXT NOT NULL,
    target_doc_id TEXT,
    target_file_path TEXT,
    link_text TEXT,
    link_type TEXT,  -- internal/external/image
    is_broken INTEGER DEFAULT 0,
    FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- 9. 索引创建链接 (doc_id -> chunk_id)
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_document_tags_doc_id ON document_tags(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_tags_tag_id ON document_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_doc_id);
CREATE INDEX IF NOT EXISTS idx_links_broken ON links(is_broken);

-- ========================================
-- 性能优化视图
-- ========================================

-- 10. 索引统计视图
CREATE VIEW IF NOT EXISTS v_index_stats AS
SELECT 
    (SELECT COUNT(*) FROM documents) as doc_count,
    (SELECT COUNT(*) FROM chunks) as chunk_count,
    (SELECT COUNT(*) FROM tags) as tag_count,
    (SELECT COUNT(*) FROM links) as link_count,
    (SELECT COUNT(*) FROM links WHERE is_broken = 1) as broken_link_count,
    (SELECT COUNT(DISTINCT file_path) FROM documents) as file_count;

-- 11. 标签使用统计视图
CREATE VIEW IF NOT EXISTS v_tag_stats AS
SELECT 
    t.tag_name,
    t.usage_count,
    (SELECT COUNT(*) FROM document_tags dt WHERE dt.tag_id = t.tag_id) as actual_count
FROM tags t
ORDER BY t.usage_count DESC;

-- 12. 文档类型分布视图
CREATE VIEW IF NOT EXISTS v_doc_type_stats AS
SELECT 
    doc_type,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM documents), 2) as percentage
FROM documents
GROUP BY doc_type
ORDER BY count DESC;
```

### 迁移策略

```python
# 迁移脚本流程
1. 备份现有数据库
2. 创建新表结构
3. 数据迁移:
   - 从 vectors 表迁移到 documents 表
   - 从 chunks 表迁移到 chunks 表 (保持兼容)
   - 从 vectors_vec 迁移到 vectors_vec (保持兼容)
   - 解析 metadata 提取 tags、doc_type 等
4. 创建索引和视图
5. 验证数据完整性
6. 删除旧表 (可选)
```

---

## 🔧 查询功能实现方案

### 1. 统一查询接口设计

```python
class SecondBrainQuery:
    """统一查询接口"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_connection()
    
    def search(
        self,
        query: str,
        mode: str = "hybrid",  # semantic/keyword/hybrid
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        统一搜索接口
        
        Args:
            query: 搜索关键词
            mode: 搜索模式
            top_k: 返回结果数
            filters: 过滤条件
                - tags: List[str]
                - doc_type: str
                - min_priority: int
                - file_path: str
                - date_range: tuple
        
        Returns:
            List[SearchResult]
        """
        pass
    
    def get_note_info(self, doc_id: str) -> Dict:
        """获取笔记详细信息"""
        pass
    
    def get_backlinks(self, doc_id: str) -> List[Dict]:
        """获取反向链接"""
        pass
    
    def find_broken_links(self) -> List[Dict]:
        """查找断裂链接"""
        pass
    
    def find_orphaned_notes(self) -> List[Dict]:
        """查找孤立笔记"""
        pass
    
    def get_index_stats(self) -> Dict:
        """获取索引统计"""
        pass
```

### 2. 高级过滤实现

```python
def _apply_filters(self, query: str, filters: Dict) -> str:
    """
    应用过滤条件到 SQL 查询
    
    支持:
    1. 标签过滤：JOIN document_tags + JOIN tags
    2. 文档类型过滤：WHERE doc_type = ?
    3. 优先级过滤：WHERE priority >= ?
    4. 文件路径过滤：WHERE file_path LIKE ?
    5. 时间范围过滤：WHERE created_at BETWEEN ? AND ?
    """
    conditions = []
    params = []
    
    # 标签过滤
    if 'tags' in filters:
        conditions.append("""
            doc_id IN (
                SELECT dt.doc_id FROM document_tags dt
                JOIN tags t ON dt.tag_id = t.tag_id
                WHERE t.tag_name IN ({})
            )
        """.format(','.join(['?' for _ in filters['tags']])))
        params.extend(filters['tags'])
    
    # 文档类型过滤
    if 'doc_type' in filters:
        conditions.append("doc_type = ?")
        params.append(filters['doc_type'])
    
    # 优先级过滤
    if 'min_priority' in filters:
        conditions.append("priority >= ?")
        params.append(filters['min_priority'])
    
    # 文件路径过滤
    if 'file_path' in filters:
        conditions.append("file_path LIKE ?")
        params.append(f"%{filters['file_path']}%")
    
    return conditions, params
```

### 3. 查询性能优化

```python
class QueryOptimizer:
    """查询性能优化器"""
    
    @staticmethod
    def optimize_search_query(query: str) -> str:
        """
        优化搜索查询
        1. 去除停用词
        2. 中文分词
        3. 查询扩展
        """
        pass
    
    @staticmethod
    def cache_result(key: str, result: Any, ttl: int = 300):
        """结果缓存"""
        pass
    
    @staticmethod
    def analyze_query_performance(query: str, execution_time: float):
        """查询性能分析"""
        pass
```

---

## 📅 实施计划

### Phase 1: 数据库结构优化 (1 周)

**目标**: 完成新表结构设计和数据迁移

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P1-01 | 设计新表结构 | `docs/DB_SCHEMA_v2.md` | P0 | ⏳ |
| P1-02 | 创建迁移脚本 | `scripts/migrate_to_v2.py` | P0 | ⏳ |
| P1-03 | 实现数据迁移逻辑 | `src/utils/migration.py` | P0 | ⏳ |
| P1-04 | 测试数据迁移 | `tests/test_migration.py` | P0 | ⏳ |
| P1-05 | 创建视图和索引 | `scripts/create_views.py` | P0 | ⏳ |
| P1-06 | 验证数据完整性 | `scripts/verify_migration.py` | P0 | ⏳ |

**交付物**:
- ✅ 新数据库表结构
- ✅ 数据迁移脚本
- ✅ 迁移验证报告

### Phase 2: 核心查询功能 (1 周)

**目标**: 实现统一查询接口和高级过滤

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P2-01 | 实现 SecondBrainQuery 类 | `src/query/query_engine.py` | P0 | ⏳ |
| P2-02 | 实现语义搜索 | `src/query/semantic_search.py` | P0 | ⏳ |
| P2-03 | 实现关键词搜索 | `src/query/keyword_search.py` | P0 | ⏳ |
| P2-04 | 实现混合检索 | `src/query/hybrid_search.py` | P0 | ⏳ |
| P2-05 | 实现高级过滤 | `src/query/filters.py` | P0 | ⏳ |
| P2-06 | 实现查询缓存 | `src/utils/query_cache.py` | P1 | ⏳ |
| P2-07 | 单元测试 | `tests/test_query_engine.py` | P0 | ⏳ |

**交付物**:
- ✅ 统一查询接口
- ✅ 三种搜索模式
- ✅ 高级过滤功能
- ✅ 查询缓存机制

### Phase 3: 元数据管理功能 (1 周)

**目标**: 实现标签、链接、反向链接等元数据功能

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P3-01 | 实现标签管理 | `src/query/tag_manager.py` | P0 | ⏳ |
| P3-02 | 实现链接分析 | `src/query/link_analyzer.py` | P1 | ⏳ |
| P3-03 | 实现反向链接查询 | `src/query/backlinks.py` | P1 | ⏳ |
| P3-04 | 实现断裂链接检测 | `src/query/broken_links.py` | P2 | ⏳ |
| P3-05 | 实现孤立笔记检测 | `src/query/orphaned_notes.py` | P2 | ⏳ |
| P3-06 | 实现笔记信息获取 | `src/query/note_info.py` | P0 | ⏳ |
| P3-07 | 集成测试 | `tests/test_metadata.py` | P1 | ⏳ |

**交付物**:
- ✅ 标签管理系统
- ✅ 链接分析功能
- ✅ 反向链接查询
- ✅ 断裂/孤立笔记检测

### Phase 4: 索引管理功能 (3 天)

**目标**: 实现索引统计、重建、优化等功能

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P4-01 | 实现索引统计 | `src/query/index_stats.py` | P0 | ⏳ |
| P4-02 | 实现索引重建 | `src/query/index_rebuild.py` | P0 | ⏳ |
| P4-03 | 实现增量索引 | `src/query/incremental_index.py` | P1 | ⏳ |
| P4-04 | 实现索引优化 | `src/query/index_optimize.py` | P2 | ⏳ |
| P4-05 | 性能测试 | `tests/test_index_performance.py` | P1 | ⏳ |

**交付物**:
- ✅ 索引统计功能
- ✅ 索引重建功能
- ✅ 增量索引更新

### Phase 5: 全面测试与优化 (1 周)

**目标**: 完成所有功能的测试和优化

| ID | 任务 | 文件 | 优先级 | 状态 |
|----|------|------|--------|------|
| P5-01 | 单元测试覆盖 | `tests/` | P0 | ⏳ |
| P5-02 | 集成测试 | `tests/test_integration.py` | P0 | ⏳ |
| P5-03 | 性能基准测试 | `tests/test_benchmark.py` | P1 | ⏳ |
| P5-04 | 压力测试 | `tests/test_stress.py` | P2 | ⏳ |
| P5-05 | 查询优化 | `src/query/optimizer.py` | P1 | ⏳ |
| P5-06 | 文档完善 | `docs/` | P1 | ⏳ |

**交付物**:
- ✅ 完整的测试套件
- ✅ 性能基准报告
- ✅ 优化后的查询系统
- ✅ 完善的文档

---

## 🧪 测试策略

### 1. 单元测试

```python
# 测试覆盖目标
- 查询引擎：100%
- 过滤器：100%
- 标签管理：95%
- 链接分析：90%
- 索引管理：95%
```

### 2. 集成测试

```python
# 测试场景
1. 完整搜索流程
2. 标签过滤 + 语义搜索
3. 文档类型过滤 + 关键词搜索
4. 混合检索 + 优先级加权
5. 反向链接查询
6. 断裂链接检测
```

### 3. 性能测试

```python
# 性能指标
- 语义搜索：<50ms (1000 文档)
- 关键词搜索：<20ms
- 混合检索：<70ms
- 标签过滤：<10ms
- 反向链接查询：<30ms
```

### 4. 压力测试

```python
# 测试场景
- 并发查询：100 并发
- 大数据量：10000 文档
- 长时间运行：24 小时
```

---

## 📊 成功标准

### 功能完整性

- ✅ 支持 3 种搜索模式 (semantic/keyword/hybrid)
- ✅ 支持 5 种高级过滤 (tags/doc_type/priority/file_path/date)
- ✅ 支持元数据查询 (info/tags/links/backlinks)
- ✅ 支持索引管理 (stats/rebuild/incremental)

### 性能指标

- ✅ 搜索响应时间 <100ms (P95)
- ✅ 查询缓存命中率 >80%
- ✅ 索引构建速度 >100 文档/分钟
- ✅ 内存占用 <500MB

### 代码质量

- ✅ 单元测试覆盖率 >90%
- ✅ 代码审查通过率 100%
- ✅ 无严重 bug
- ✅ 文档完整度 100%

---

## 🔄 回滚计划

如果迁移失败，执行以下回滚步骤:

```bash
# 1. 停止服务
pkill -f secondbrain

# 2. 恢复备份
cp ~/.local/share/secondbrain/semantic_index.db.backup \
   ~/.local/share/secondbrain/semantic_index.db

# 3. 验证恢复
python3 scripts/verify_migration.py --check-only

# 4. 重启服务
python3 -m src.server
```

---

## 📝 变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-03-30 | v2.0 | 初始版本，重新梳理数据库结构和查询功能 | nanobot |

---

## 🔗 相关文档

- [架构设计](docs/ARCHITECTURE.md)
- [实施计划](IMPLEMENTATION_PLAN.md)
- [API 文档](docs/API.md)
- [配置指南](docs/CONFIG.md)

---

**下一步**: 开始 Phase 1 实施，创建新表结构设计和迁移脚本。
