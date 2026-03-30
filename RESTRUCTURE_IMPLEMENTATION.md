# SecondBrain 数据库重构实施计划

**创建时间**: 2026-03-30  
**版本**: v1.0  
**状态**: 准备执行  

---

## 📋 总体目标

重新梳理 SecondBrain 的数据库结构和查询功能，实现：
1. **规范化数据库设计** - 减少冗余，提高查询效率
2. **统一查询接口** - 提供一致的搜索和元数据访问
3. **高级过滤功能** - 支持标签、文档类型、优先级等过滤
4. **完善的测试覆盖** - 确保功能正确性和性能

---

## 🎯 分阶段实施方案

### Phase 1: 数据库结构优化 (预计 3-5 天)

**目标**: 设计并实现新的数据库表结构，完成数据迁移

#### 任务清单

| ID | 任务 | 预计时间 | 优先级 | 状态 | 交付物 |
|----|------|----------|--------|------|--------|
| 1.1 | 创建新表结构 SQL 脚本 | 2 小时 | P0 | ⏳ | `scripts/create_new_schema.sql` |
| 1.2 | 实现数据迁移脚本 | 4 小时 | P0 | ⏳ | `scripts/migrate_to_v2.py` |
| 1.3 | 创建视图和索引 | 2 小时 | P0 | ⏳ | `scripts/create_views.py` |
| 1.4 | 实现数据验证脚本 | 3 小时 | P0 | ⏳ | `scripts/verify_migration.py` |
| 1.5 | 测试迁移流程 | 4 小时 | P0 | ⏳ | 迁移测试报告 |
| 1.6 | 执行正式迁移 | 2 小时 | P0 | ⏳ | 迁移后的数据库 |

#### 详细步骤

**步骤 1.1: 创建新表结构**

```bash
# 创建 SQL 脚本
cat > scripts/create_new_schema.sql << 'EOF'
-- 新表结构定义
-- (参考 DB_RESTRUCTURE_PLAN.md 中的设计)
EOF
```

**步骤 1.2: 实现数据迁移脚本**

```python
# scripts/migrate_to_v2.py
# 主要功能:
# 1. 备份现有数据库
# 2. 创建新表结构
# 3. 迁移数据 (vectors -> documents, chunks -> chunks)
# 4. 解析 metadata 提取 tags、doc_type
# 5. 创建标签关联
# 6. 创建索引和视图
```

**步骤 1.3: 创建视图和索引**

```python
# scripts/create_views.py
# 创建统计视图:
# - v_index_stats
# - v_tag_stats
# - v_doc_type_stats
```

**步骤 1.4: 实现数据验证**

```python
# scripts/verify_migration.py
# 验证项:
# - 记录数一致性
# - 数据完整性
# - 索引正确性
# - 视图可用性
```

**步骤 1.5: 测试迁移流程**

```bash
# 在测试数据库上执行迁移
python3 scripts/migrate_to_v2.py --test-mode

# 验证迁移结果
python3 scripts/verify_migration.py --db-path test_db
```

**步骤 1.6: 执行正式迁移**

```bash
# 备份生产数据库
cp ~/.local/share/secondbrain/semantic_index.db \
   ~/.local/share/secondbrain/semantic_index.db.backup.$(date +%Y%m%d)

# 执行迁移
python3 scripts/migrate_to_v2.py

# 验证迁移结果
python3 scripts/verify_migration.py
```

#### Phase 1 验收标准

- ✅ 新表结构创建成功
- ✅ 所有数据成功迁移 (5001 条记录)
- ✅ 视图和索引创建成功
- ✅ 数据验证通过 (记录数、完整性)
- ✅ 查询功能正常 (语义搜索、关键词搜索)

---

### Phase 2: 统一查询接口实现 (预计 3-5 天)

**目标**: 实现统一的查询接口，支持多种搜索模式和高级过滤

#### 任务清单

| ID | 任务 | 预计时间 | 优先级 | 状态 | 交付物 |
|----|------|----------|--------|------|--------|
| 2.1 | 设计查询接口 API | 2 小时 | P0 | ⏳ | `docs/QUERY_API.md` |
| 2.2 | 实现 SecondBrainQuery 基类 | 4 小时 | P0 | ⏳ | `src/query/query_engine.py` |
| 2.3 | 实现语义搜索模块 | 4 小时 | P0 | ⏳ | `src/query/semantic_search.py` |
| 2.4 | 实现关键词搜索模块 | 3 小时 | P0 | ⏳ | `src/query/keyword_search.py` |
| 2.5 | 实现混合检索模块 | 4 小时 | P0 | ⏳ | `src/query/hybrid_search.py` |
| 2.6 | 实现过滤器模块 | 4 小时 | P0 | ⏳ | `src/query/filters.py` |
| 2.7 | 实现查询缓存 | 3 小时 | P1 | ⏳ | `src/utils/query_cache.py` |
| 2.8 | 单元测试 | 4 小时 | P0 | ⏳ | `tests/test_query_engine.py` |

#### 详细步骤

**步骤 2.1: 设计查询接口 API**

```python
# 核心接口定义
class SecondBrainQuery:
    def search(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]
    
    def get_note_info(self, doc_id: str) -> Dict
    def get_backlinks(self, doc_id: str) -> List[Dict]
    def find_broken_links(self) -> List[Dict]
    def find_orphaned_notes(self) -> List[Dict]
    def get_index_stats(self) -> Dict
```

**步骤 2.2-2.6: 实现各模块**

```python
# src/query/query_engine.py
class SecondBrainQuery:
    def __init__(self, db_path: str):
        self.conn = self._init_connection(db_path)
        self.semantic = SemanticSearch(self.conn)
        self.keyword = KeywordSearch(self.conn)
        self.hybrid = HybridSearch(self.conn, self.semantic, self.keyword)
        self.filters = QueryFilters()
        self.cache = QueryCache()
    
    def search(self, query, mode, top_k, filters):
        # 1. 检查缓存
        cache_key = self._generate_cache_key(query, mode, top_k, filters)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # 2. 应用过滤器
        filter_conditions, params = self.filters.apply(filters)
        
        # 3. 执行搜索
        if mode == "semantic":
            results = self.semantic.search(query, top_k, filter_conditions, params)
        elif mode == "keyword":
            results = self.keyword.search(query, top_k, filter_conditions, params)
        else:
            results = self.hybrid.search(query, top_k, filter_conditions, params)
        
        # 4. 缓存结果
        self.cache.set(cache_key, results, ttl=300)
        
        return results
```

**步骤 2.7: 实现查询缓存**

```python
# src/utils/query_cache.py
class QueryCache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache = LRUCache(max_size)
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[List[SearchResult]]:
        # 检查缓存是否存在且未过期
        pass
    
    def set(self, key: str, value: List[SearchResult], ttl: int = None):
        # 存储结果到缓存
        pass
    
    def invalidate(self, pattern: str = None):
        # 清除缓存 (支持通配符)
        pass
```

**步骤 2.8: 编写单元测试**

```python
# tests/test_query_engine.py
class TestSecondBrainQuery:
    def test_semantic_search(self):
        query_engine = SecondBrainQuery(test_db)
        results = query_engine.search("人工智能", mode="semantic")
        assert len(results) > 0
    
    def test_keyword_search(self):
        results = query_engine.search("机器学习", mode="keyword")
        assert len(results) > 0
    
    def test_hybrid_search(self):
        results = query_engine.search("深度学习", mode="hybrid")
        assert len(results) > 0
    
    def test_tag_filter(self):
        results = query_engine.search(
            "AI",
            filters={"tags": ["important", "work"]}
        )
        assert all("important" in r.tags for r in results)
    
    def test_doc_type_filter(self):
        results = query_engine.search(
            "技术",
            filters={"doc_type": "technical"}
        )
        assert all(r.doc_type == "technical" for r in results)
```

#### Phase 2 验收标准

- ✅ 统一查询接口实现完成
- ✅ 三种搜索模式正常工作
- ✅ 高级过滤功能正常 (tags, doc_type, priority, file_path)
- ✅ 查询缓存机制正常
- ✅ 单元测试覆盖率 >90%

---

### Phase 3: 元数据管理功能 (预计 3-4 天)

**目标**: 实现标签管理、链接分析、反向链接等元数据功能

#### 任务清单

| ID | 任务 | 预计时间 | 优先级 | 状态 | 交付物 |
|----|------|----------|--------|------|--------|
| 3.1 | 实现标签管理模块 | 4 小时 | P0 | ⏳ | `src/query/tag_manager.py` |
| 3.2 | 实现链接分析模块 | 4 小时 | P1 | ⏳ | `src/query/link_analyzer.py` |
| 3.3 | 实现反向链接查询 | 3 小时 | P1 | ⏳ | `src/query/backlinks.py` |
| 3.4 | 实现断裂链接检测 | 3 小时 | P2 | ⏳ | `src/query/broken_links.py` |
| 3.5 | 实现孤立笔记检测 | 3 小时 | P2 | ⏳ | `src/query/orphaned_notes.py` |
| 3.6 | 实现笔记信息获取 | 2 小时 | P0 | ⏳ | `src/query/note_info.py` |
| 3.7 | 集成测试 | 4 小时 | P1 | ⏳ | `tests/test_metadata.py` |

#### 详细步骤

**步骤 3.1: 标签管理模块**

```python
# src/query/tag_manager.py
class TagManager:
    def list_tags(self, vault_name: str = None) -> List[Dict]:
        """列出所有标签及使用情况"""
        pass
    
    def get_note_tags(self, doc_id: str) -> List[str]:
        """获取笔记的标签列表"""
        pass
    
    def add_tag(self, doc_id: str, tag_name: str):
        """添加标签到笔记"""
        pass
    
    def remove_tag(self, doc_id: str, tag_name: str):
        """从笔记移除标签"""
        pass
    
    def search_by_tags(self, tags: List[str], mode: str = "any") -> List[str]:
        """按标签搜索笔记 (any/all)"""
        pass
```

**步骤 3.2: 链接分析模块**

```python
# src/query/link_analyzer.py
class LinkAnalyzer:
    def get_links(self, doc_id: str) -> List[Dict]:
        """获取笔记的出站链接"""
        pass
    
    def get_backlinks(self, doc_id: str) -> List[Dict]:
        """获取笔记的反向链接"""
        pass
    
    def find_broken_links(self) -> List[Dict]:
        """查找所有断裂链接"""
        pass
    
    def find_orphaned_notes(self) -> List[str]:
        """查找孤立笔记 (无入链)"""
        pass
    
    def get_link_graph(self) -> Dict:
        """获取链接图数据 (用于可视化)"""
        pass
```

**步骤 3.3-3.5: 实现其他功能**

```python
# src/query/note_info.py
def get_note_info(doc_id: str) -> Dict:
    """
    获取笔记详细信息
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
```

#### Phase 3 验收标准

- ✅ 标签管理功能正常
- ✅ 链接分析功能正常
- ✅ 反向链接查询正常
- ✅ 断裂链接检测正常
- ✅ 孤立笔记检测正常
- ✅ 笔记信息获取正常

---

### Phase 4: 索引管理功能 (预计 2-3 天)

**目标**: 实现索引统计、重建、优化等功能

#### 任务清单

| ID | 任务 | 预计时间 | 优先级 | 状态 | 交付物 |
|----|------|----------|--------|------|--------|
| 4.1 | 实现索引统计模块 | 3 小时 | P0 | ⏳ | `src/query/index_stats.py` |
| 4.2 | 实现索引重建模块 | 4 小时 | P0 | ⏳ | `src/query/index_rebuild.py` |
| 4.3 | 实现增量索引模块 | 4 小时 | P1 | ⏳ | `src/query/incremental_index.py` |
| 4.4 | 实现索引优化模块 | 2 小时 | P2 | ⏳ | `src/query/index_optimize.py` |
| 4.5 | 性能测试 | 4 小时 | P1 | ⏳ | 性能测试报告 |

#### 详细步骤

**步骤 4.1: 索引统计模块**

```python
# src/query/index_stats.py
class IndexStats:
    def get_stats(self) -> Dict:
        """
        获取索引统计信息
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
    
    def get_doc_type_stats(self) -> List[Dict]:
        """获取文档类型分布"""
        pass
    
    def get_tag_stats(self) -> List[Dict]:
        """获取标签使用统计"""
        pass
```

**步骤 4.2: 索引重建模块**

```python
# src/query/index_rebuild.py
class IndexRebuild:
    def rebuild_full(self, vault_path: str, progress_callback=None):
        """全量重建索引"""
        pass
    
    def rebuild_incremental(self, vault_path: str, changed_files: List[str]):
        """增量重建索引"""
        pass
    
    def delete_index(self):
        """删除现有索引"""
        pass
```

#### Phase 4 验收标准

- ✅ 索引统计功能正常
- ✅ 索引重建功能正常
- ✅ 增量索引更新正常
- ✅ 性能指标达标

---

### Phase 5: 全面测试与优化 (预计 3-5 天)

**目标**: 完成所有功能的测试和优化

#### 任务清单

| ID | 任务 | 预计时间 | 优先级 | 状态 | 交付物 |
|----|------|----------|--------|------|--------|
| 5.1 | 完善单元测试 | 4 小时 | P0 | ⏳ | 测试覆盖率 >90% |
| 5.2 | 集成测试 | 4 小时 | P0 | ⏳ | 集成测试报告 |
| 5.3 | 性能基准测试 | 4 小时 | P1 | ⏳ | 性能基准报告 |
| 5.4 | 压力测试 | 4 小时 | P2 | ⏳ | 压力测试报告 |
| 5.5 | 查询优化 | 4 小时 | P1 | ⏳ | 优化后的查询系统 |
| 5.6 | 文档完善 | 4 小时 | P1 | ⏳ | 完整文档 |

#### 详细步骤

**步骤 5.1-5.2: 测试覆盖**

```bash
# 运行单元测试
pytest tests/test_query_engine.py -v --cov=src/query

# 运行集成测试
pytest tests/test_integration.py -v

# 查看测试覆盖率
coverage report -m
```

**步骤 5.3: 性能基准测试**

```python
# tests/test_benchmark.py
def test_semantic_search_performance(benchmark):
    """测试语义搜索性能"""
    results = query_engine.search("人工智能", mode="semantic", top_k=10)
    assert len(results) == 10

def test_hybrid_search_performance(benchmark):
    """测试混合检索性能"""
    results = query_engine.search("机器学习", mode="hybrid", top_k=10)
    assert len(results) == 10

# 性能指标
# - 语义搜索：<50ms
# - 关键词搜索：<20ms
# - 混合检索：<70ms
```

**步骤 5.4: 压力测试**

```python
# tests/test_stress.py
def test_concurrent_searches():
    """测试并发查询"""
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [
            executor.submit(query_engine.search, f"查询{i}", "hybrid")
            for i in range(100)
        ]
        results = [f.result() for f in futures]
    assert len(results) == 100
```

#### Phase 5 验收标准

- ✅ 单元测试覆盖率 >90%
- ✅ 所有集成测试通过
- ✅ 性能指标达标
- ✅ 压力测试通过
- ✅ 文档完整

---

## 📊 总体时间估算

| Phase | 预计时间 | 优先级 |
|-------|----------|--------|
| Phase 1: 数据库结构优化 | 3-5 天 | P0 |
| Phase 2: 统一查询接口 | 3-5 天 | P0 |
| Phase 3: 元数据管理功能 | 3-4 天 | P1 |
| Phase 4: 索引管理功能 | 2-3 天 | P1 |
| Phase 5: 全面测试与优化 | 3-5 天 | P0 |
| **总计** | **14-22 天** | |

---

## 🎯 成功标准

### 功能完整性

- ✅ 支持 3 种搜索模式 (semantic/keyword/hybrid)
- ✅ 支持 5 种高级过滤 (tags/doc_type/priority/file_path/date)
- ✅ 支持元数据查询 (info/tags/links/backlinks)
- ✅ 支持索引管理 (stats/rebuild/incremental)

### 性能指标

- ✅ 语义搜索 <50ms (P95)
- ✅ 关键词搜索 <20ms (P95)
- ✅ 混合检索 <70ms (P95)
- ✅ 查询缓存命中率 >80%

### 代码质量

- ✅ 单元测试覆盖率 >90%
- ✅ 无严重 bug
- ✅ 文档完整度 100%

---

## 🔄 风险管理

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 数据迁移失败 | 高 | 中 | 完整备份 + 回滚脚本 |
| 性能不达标 | 中 | 中 | 提前进行性能测试 + 优化 |
| 测试覆盖率不足 | 中 | 低 | 持续集成 + 强制覆盖率要求 |
| 时间超期 | 中 | 中 | 优先实现核心功能 + 分阶段交付 |

---

## 📝 下一步行动

1. **立即开始**: Phase 1 任务 1.1 - 创建新表结构 SQL 脚本
2. **每日检查**: 更新任务状态和进度
3. **每周回顾**: 评估进度和调整计划

---

**创建者**: nanobot  
**最后更新**: 2026-03-30
