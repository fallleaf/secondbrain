"""
SecondBrain 单元测试套件
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.chdir(project_root)
os.environ['PYTHONPATH'] = str(project_root / "src")

# 现在导入
from src.index.embedder import Embedder
from src.index.chunker import Chunker
from src.index.semantic_index import SemanticIndex
from src.index.keyword_index import KeywordIndex
from src.utils.perf_monitor import PerformanceMonitor, get_perf_monitor

# 测试配置
TEST_MODEL = "BAAI/bge-small-zh-v1.5"
TEST_TEXT = """
# 测试文档

这是一个用于测试 SecondBrain 系统的文档。

## 章节一

人工智能 (AI) 是计算机科学的一个重要分支，致力于创造能够模拟人类智能的机器。
机器学习 (Machine Learning) 是 AI 的核心，通过数据训练模型。
深度学习 (Deep Learning) 是机器学习的一个子集，使用神经网络。

## 章节二

自然语言处理 (NLP) 让机器能够理解和生成人类语言。
计算机视觉 (CV) 让机器能够“看”懂图像。
强化学习 (RL) 让机器通过与环境交互来学习。

## 总结

AI 技术正在快速发展，改变着我们的生活和工作方式。
"""

@pytest.fixture
def temp_dir():
    """创建临时测试目录"""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)

@pytest.fixture
def embedder():
    """初始化嵌入模型"""
    return Embedder(model_name=TEST_MODEL)

@pytest.fixture
def chunker():
    """初始化分块器"""
    return Chunker(chunk_size=200, chunk_overlap=50)

@pytest.fixture
def semantic_index(temp_dir):
    """初始化语义索引"""
    db_path = os.path.join(temp_dir, "test_semantic.db")
    return SemanticIndex(index_path=db_path, dim=512)

@pytest.fixture
def keyword_index(temp_dir):
    """初始化关键词索引"""
    db_path = os.path.join(temp_dir, "test_keyword.db")
    return KeywordIndex(db_path=db_path)

class TestEmbedder:
    """测试嵌入模型"""

    def test_init(self, embedder):
        """测试初始化"""
        assert embedder.model_name == TEST_MODEL
        assert embedder.embedding_dim == 512

    def test_encode_single(self, embedder):
        """测试单文本编码"""
        emb = embedder.encode_single("测试句子")
        assert isinstance(emb, list) or hasattr(emb, 'tolist')
        assert len(emb) == 512

    def test_encode_batch(self, embedder):
        """测试批量编码"""
        texts = ["句子1", "句子2", "句子3"]
        embs = embedder.encode(texts)
        assert len(embs) == 3
        assert embs.shape[1] == 512

    def test_similarity(self, embedder):
        """测试相似度计算"""
        sim = embedder.similarity("苹果", "水果")
        assert -1.0 <= sim <= 1.0
        # 苹果和水果应该比较相似
        assert sim > 0.5

class TestChunker:
    """测试文本分块"""

    def test_chunk_file(self, chunker):
        """测试文件分块"""
        chunks = chunker.chunk_file("test.md", TEST_TEXT, {})
        assert len(chunks) > 0
        assert all(isinstance(c.content, str) for c in chunks)
        # 检查块大小
        for c in chunks:
            assert len(c.content) <= 200 + 50  # 允许重叠

    def test_chunk_structure(self, chunker):
        """测试分块结构"""
        chunks = chunker.chunk_file("test.md", TEST_TEXT, {})
        # 检查是否按章节分割
        has_section1 = any("章节一" in c.content for c in chunks)
        has_section2 = any("章节二" in c.content for c in chunks)
        assert has_section1 or has_section2

class TestSemanticIndex:
    """测试语义索引"""

    def test_add_text(self, semantic_index, embedder):
        """测试添加文本"""
        semantic_index.add_text("doc_001", TEST_TEXT, {"priority": 5})
        stats = semantic_index.get_stats()
        assert stats["document_count"] >= 1

    def test_search(self, semantic_index, embedder):
        """测试语义搜索"""
        # 添加文档
        semantic_index.add_text("doc_001", TEST_TEXT, {"priority": 5})
        
        # 搜索
        query_emb = embedder.encode_single("人工智能")
        results = semantic_index.search(query_emb, top_k=3)
        
        assert len(results) > 0
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    def test_delete_document(self, semantic_index, embedder):
        """测试删除文档"""
        semantic_index.add_text("doc_002", "这是要删除的文档内容", {})
        semantic_index.delete_document("doc_002")
        
        query_emb = embedder.encode_single("删除的文档")
        results = semantic_index.search(query_emb, top_k=5)
        # 应该没有结果或结果很少
        assert len(results) == 0 or all("doc_002" not in r[0] for r in results)

class TestKeywordIndex:
    """测试关键词索引"""

    def test_add_and_search(self, keyword_index):
        """测试添加和搜索"""
        keyword_index.add("doc_001", "人工智能是未来的方向", "test/doc1.md")
        keyword_index.add("doc_002", "机器学习很重要", "test/doc2.md")

        results = keyword_index.search("人工智能", top_k=5)
        assert len(results) > 0
        assert any("doc_001" in r['doc_id'] for r in results)

class TestPerformanceMonitor:
    """测试性能监控"""

    def test_start_stop(self):
        """测试计时"""
        monitor = PerformanceMonitor()
        with monitor.start("test_op"):
            pass  # 空操作
        
        stats = monitor.get_stats("test_op")
        assert stats["count"] == 1
        assert stats["avg_ms"] >= 0

    def test_decorator(self):
        """测试装饰器"""
        from src.utils.perf_monitor import monitor_performance

        @monitor_performance("decorated_func")
        def dummy_func():
            pass

        dummy_func()

        monitor = get_perf_monitor()
        stats = monitor.get_stats("decorated_func")
        assert stats["count"] == 1

    def test_save_load_logs(self, temp_dir):
        """测试日志保存和加载"""
        monitor = PerformanceMonitor(log_dir=temp_dir)
        with monitor.start("test"):
            pass
        # with 语句会自动调用 stop()，不需要手动调用

        filepath = monitor.save_logs("test_log.json")
        assert os.path.exists(filepath)

        new_monitor = PerformanceMonitor(log_dir=temp_dir)
        new_monitor.load_logs(filepath)
        assert "test" in new_monitor.metrics

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
