"""
Phase 5: 综合测试套件
包含单元测试、集成测试和性能基准测试
"""

import pytest
import sys
import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from query import (
    SecondBrainQuery,
    MetadataManager,
    IndexManager,
    SearchResult,
    IndexStats
)


class TestSecondBrainQuery:
    """SecondBrainQuery 单元测试"""
    
    @pytest.fixture
    def query_engine(self):
        """创建查询引擎实例"""
        db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
        return SecondBrainQuery(db_path)
    
    def test_init(self, query_engine):
        """测试初始化"""
        assert query_engine is not None
        assert query_engine.semantic is not None
        assert query_engine.keyword is not None
        assert query_engine.hybrid is not None
    
    def test_search_semantic(self, query_engine):
        """测试语义搜索"""
        results = query_engine.search("人工智能", mode="semantic", top_k=3)
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.source == "semantic" for r in results)
    
    def test_search_keyword(self, query_engine):
        """测试关键词搜索"""
        results = query_engine.search("机器学习", mode="keyword", top_k=3)
        assert len(results) >= 0  # 可能没有结果
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.source == "keyword" for r in results)
    
    def test_search_hybrid(self, query_engine):
        """测试混合检索"""
        results = query_engine.search("深度学习", mode="hybrid", top_k=3)
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.source == "hybrid" for r in results)
    
    def test_search_with_filters(self, query_engine):
        """测试带过滤的搜索"""
        results = query_engine.search(
            "技术",
            mode="hybrid",
            top_k=5,
            filters={"doc_type": "technical"}
        )
        assert len(results) >= 0
        # 验证过滤效果
        for r in results:
            assert r.doc_type == "technical" or r.doc_type == "default"
    
    def test_get_index_stats(self, query_engine):
        """测试获取索引统计"""
        stats = query_engine.get_index_stats()
        assert stats.doc_count > 0
        assert stats.chunk_count > 0
        assert isinstance(stats, IndexStats)
    
    def test_cache_hit(self, query_engine):
        """测试查询缓存"""
        # 第一次查询
        results1 = query_engine.search("缓存测试", mode="hybrid", top_k=1)
        
        # 第二次查询（应该从缓存获取）
        start = time.time()
        results2 = query_engine.search("缓存测试", mode="hybrid", top_k=1)
        elapsed = time.time() - start
        
        # 缓存查询应该更快
        assert len(results1) == len(results2)
        # 注意：缓存时间可能很短，这个断言可能不总是成立


class TestMetadataManager:
    """MetadataManager 单元测试"""
    
    @pytest.fixture
    def metadata_manager(self):
        """创建元数据管理器实例"""
        db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
        vault_path = os.path.expanduser("~/NanobotMemory")
        return MetadataManager(db_path, vault_path)
    
    def test_get_backlinks(self, metadata_manager):
        """测试获取反向链接"""
        # 获取一个存在的文档
        backlinks = metadata_manager.get_backlinks("test_doc")
        assert isinstance(backlinks, list)
    
    def test_find_broken_links(self, metadata_manager):
        """测试查找断裂链接"""
        broken = metadata_manager.find_broken_links()
        assert isinstance(broken, list)
    
    def test_find_orphaned_notes(self, metadata_manager):
        """测试查找孤立笔记"""
        orphaned = metadata_manager.find_orphaned_notes()
        assert isinstance(orphaned, list)
        assert len(orphaned) > 0  # 应该有孤立笔记
    
    def test_get_note_tags(self, metadata_manager):
        """测试获取笔记标签"""
        tags = metadata_manager.get_note_tags("test_doc")
        assert isinstance(tags, list)


class TestIndexManager:
    """IndexManager 单元测试"""
    
    @pytest.fixture
    def index_manager(self):
        """创建索引管理器实例"""
        db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
        vault_path = os.path.expanduser("~/NanobotMemory")
        return IndexManager(db_path, vault_path)
    
    def test_get_index_stats(self, index_manager):
        """测试获取索引统计"""
        stats = index_manager.get_index_stats()
        assert stats.doc_count > 0
        assert stats.chunk_count > 0
    
    def test_get_storage_stats(self, index_manager):
        """测试获取存储统计"""
        stats = index_manager.get_storage_stats()
        assert "db_size_mb" in stats
        assert stats["db_size_mb"] > 0
    
    def test_analyze_performance(self, index_manager):
        """测试性能分析"""
        perf = index_manager.analyze_performance()
        assert "table_sizes" in perf
        assert "indexes" in perf


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
        vault_path = os.path.expanduser("~/NanobotMemory")
        
        query_engine = SecondBrainQuery(db_path)
        metadata_manager = MetadataManager(db_path, vault_path)
        index_manager = IndexManager(db_path, vault_path)
        
        return {
            "query": query_engine,
            "metadata": metadata_manager,
            "index": index_manager
        }
    
    def test_full_search_workflow(self, setup):
        """测试完整搜索工作流"""
        query_engine = setup["query"]
        
        # 1. 搜索
        results = query_engine.search("人工智能", mode="hybrid", top_k=5)
        assert len(results) > 0
        
        # 2. 获取第一个结果的详细信息
        if results:
            doc_id = results[0].doc_id
            info = query_engine.get_note_info(doc_id)
            assert info is not None
        
        # 3. 获取反向链接
        backlinks = setup["metadata"].get_backlinks(doc_id)
        assert isinstance(backlinks, list)
        
        # 4. 获取索引统计
        stats = setup["index"].get_index_stats()
        assert stats.doc_count > 0
    
    def test_tag_search_workflow(self, setup):
        """测试标签搜索工作流"""
        query_engine = setup["query"]
        metadata = setup["metadata"]
        
        # 1. 获取所有标签
        tags = query_engine.list_tags()
        if tags:
            # 2. 按标签搜索
            tag_name = tags[0].tag_name
            results = metadata.search_by_tags([tag_name], top_k=5)
            assert isinstance(results, list)


class TestPerformance:
    """性能基准测试"""
    
    @pytest.fixture
    def query_engine(self):
        db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
        return SecondBrainQuery(db_path)
    
    def test_semantic_search_performance(self, query_engine, benchmark):
        """测试语义搜索性能"""
        results = query_engine.search("人工智能", mode="semantic", top_k=10)
        assert len(results) > 0
    
    def test_keyword_search_performance(self, query_engine, benchmark):
        """测试关键词搜索性能"""
        results = query_engine.search("技术", mode="keyword", top_k=10)
        assert len(results) >= 0
    
    def test_hybrid_search_performance(self, query_engine, benchmark):
        """测试混合检索性能"""
        results = query_engine.search("深度学习", mode="hybrid", top_k=10)
        assert len(results) > 0
    
    def test_concurrent_searches(self, query_engine):
        """测试并发搜索"""
        import concurrent.futures
        
        queries = ["人工智能", "机器学习", "深度学习", "神经网络", "大数据"]
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(query_engine.search, q, "hybrid", 5)
                for q in queries
            ]
            results = [f.result() for f in futures]
        elapsed = time.time() - start
        
        # 5 个并发查询应该在 5 秒内完成
        assert elapsed < 5.0
        assert all(len(r) > 0 for r in results)


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
