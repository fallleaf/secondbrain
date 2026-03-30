"""
SecondBrain 扩展测试套件

补充测试用例，提高测试覆盖率
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

# 导入模块
from src.index.embedder import Embedder
from src.index.chunker import Chunker
from src.index.semantic_index import SemanticIndex
from src.index.keyword_index import KeywordIndex
from src.index.hybrid_retriever import HybridRetriever, SearchMode
from src.utils.priority import PriorityClassifier
from src.utils.filesystem import FileSystem


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
计算机视觉 (CV) 让机器能够"看"懂图像。
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


@pytest.fixture
def priority_classifier():
    """初始化优先级分类器"""
    return PriorityClassifier()


@pytest.fixture
def filesystem(temp_dir):
    """初始化文件系统工具"""
    return FileSystem(temp_dir)


class TestHybridRetriever:
    """测试混合检索器"""

    def test_hybrid_search(self, keyword_index, semantic_index, embedder, priority_classifier):
        """测试混合搜索"""
        # 添加测试文档
        keyword_index.add("doc1", "人工智能是未来的方向", "test/doc1.md")
        semantic_index.add_text("doc1", "人工智能是未来的方向", {"file_path": "test/doc1.md"})

        keyword_index.add("doc2", "机器学习很重要", "test/doc2.md")
        semantic_index.add_text("doc2", "机器学习很重要", {"file_path": "test/doc2.md"})

        # 创建混合检索器
        retriever = HybridRetriever(keyword_index, semantic_index, priority_classifier)

        # 执行混合搜索
        results = retriever.search("人工智能", mode=SearchMode.HYBRID, top_k=5)

        assert len(results) > 0
        assert all(r.source == 'hybrid' for r in results)

    def test_keyword_only_search(self, keyword_index, semantic_index, priority_classifier):
        """测试仅关键词搜索"""
        keyword_index.add("doc1", "人工智能是未来的方向", "test/doc1.md")

        retriever = HybridRetriever(keyword_index, semantic_index, priority_classifier)
        results = retriever.search("人工智能", mode=SearchMode.KEYWORD, top_k=5)

        assert len(results) > 0
        assert all(r.source == 'keyword' for r in results)

    def test_semantic_only_search(self, keyword_index, semantic_index, embedder, priority_classifier):
        """测试仅语义搜索"""
        # 使用更长的文本确保生成有效块
        long_text = "人工智能是未来的发展方向。机器学习和深度学习是人工智能的核心技术。" * 10
        semantic_index.add_text("doc1", long_text, {"file_path": "test/doc1.md"})

        retriever = HybridRetriever(keyword_index, semantic_index, priority_classifier)
        results = retriever.search("人工智能", mode=SearchMode.SEMANTIC, top_k=5)

        assert len(results) > 0
        assert all(r.source == 'semantic' for r in results)


class TestPriorityClassifier:
    """测试优先级分类器"""

    def test_infer_priority(self, priority_classifier):
        """测试优先级推断"""
        test_cases = [
            ("07.项目/国家政策/国务院文件.md", 9, "central_gov"),
            ("05.工作/项目 A/需求文档.md", 5, "company"),
            ("03.日记/2026-03-27.md", 3, "personal_work"),
            ("02.收集/网页文章.md", 1, "web"),
        ]

        for path, expected_priority, expected_label in test_cases:
            priority, label, _ = priority_classifier.infer_priority(path)
            assert priority == expected_priority
            assert label == expected_label

    def test_get_search_weight(self, priority_classifier):
        """测试搜索权重获取"""
        assert priority_classifier.get_search_weight(9) == 2.0
        assert priority_classifier.get_search_weight(7) == 1.6
        assert priority_classifier.get_search_weight(5) == 1.2
        assert priority_classifier.get_search_weight(3) == 1.0
        assert priority_classifier.get_search_weight(1) == 0.8

    def test_get_retention_days(self, priority_classifier):
        """测试保留天数获取"""
        assert priority_classifier.get_retention_days(9) is None  # 永久保留
        assert priority_classifier.get_retention_days(7) == 3650
        assert priority_classifier.get_retention_days(5) == 1095
        assert priority_classifier.get_retention_days(3) == 365
        assert priority_classifier.get_retention_days(1) == 90


class TestFileSystem:
    """测试文件系统工具"""

    def test_write_and_read(self, filesystem):
        """测试写入和读取"""
        test_content = "# 测试文档\n\n这是测试内容"
        filesystem.write_file("test.md", test_content, overwrite=True)

        content = filesystem.read_file("test.md")
        assert content == test_content

    def test_file_exists(self, filesystem):
        """测试文件存在检查"""
        assert not filesystem.file_exists("nonexistent.md")

        filesystem.write_file("test.md", "内容", overwrite=True)
        assert filesystem.file_exists("test.md")

    def test_list_files(self, filesystem):
        """测试文件列表"""
        filesystem.write_file("test1.md", "内容1", overwrite=True)
        filesystem.write_file("test2.md", "内容2", overwrite=True)

        files = filesystem.list_files()
        assert len(files) == 2
        assert "test1.md" in files
        assert "test2.md" in files

    def test_delete_file(self, filesystem):
        """测试文件删除"""
        filesystem.write_file("test.md", "内容", overwrite=True)
        assert filesystem.file_exists("test.md")

        filesystem.delete_file("test.md")
        assert not filesystem.file_exists("test.md")
        # 检查是否移动到 .trash/
        assert filesystem.file_exists(".trash/test.md")

    def test_move_file(self, filesystem):
        """测试文件移动"""
        filesystem.write_file("source.md", "内容", overwrite=True)
        filesystem.move_file("source.md", "dest.md")

        assert not filesystem.file_exists("source.md")
        assert filesystem.file_exists("dest.md")


class TestChunkerEdgeCases:
    """测试分块器边界情况"""

    def test_empty_text(self, chunker):
        """测试空文本"""
        chunks = chunker.chunk_file("test.md", "", {})
        assert len(chunks) == 0

    def test_very_short_text(self, chunker):
        """测试非常短的文本"""
        chunks = chunker.chunk_file("test.md", "短文本", {})
        assert len(chunks) == 0  # 小于 min_chunk_size

    def test_very_long_text(self, chunker):
        """测试非常长的文本"""
        long_text = "这是一个很长的文本。" * 1000
        chunks = chunker.chunk_file("test.md", long_text, {})
        assert len(chunks) > 1

    def test_text_without_sections(self, chunker):
        """测试没有章节的文本"""
        # 使用更长的文本确保生成有效块
        text = "这是第一段。" * 50 + "\n\n" + "这是第二段。" * 50 + "\n\n" + "这是第三段。" * 50
        chunks = chunker.chunk_file("test.md", text, {})
        assert len(chunks) > 0


class TestEmbedderEdgeCases:
    """测试嵌入模型边界情况"""

    def test_empty_text(self, embedder):
        """测试空文本"""
        emb = embedder.encode_single("")
        assert len(emb) == 512

    def test_special_characters(self, embedder):
        """测试特殊字符"""
        special_text = "特殊字符：!@#$%^&*()_+-=[]{}|;':\",./<>?"
        emb = embedder.encode_single(special_text)
        assert len(emb) == 512

    def test_unicode_text(self, embedder):
        """测试 Unicode 文本"""
        unicode_text = "Unicode 测试：中文、日本語、한국어、العربية"
        emb = embedder.encode_single(unicode_text)
        assert len(emb) == 512


class TestSemanticIndexEdgeCases:
    """测试语义索引边界情况"""

    def test_duplicate_document(self, semantic_index):
        """测试重复文档"""
        # 使用更长的文本确保生成有效块
        long_text = "这是一个很长的文档。" * 50
        semantic_index.add_text("doc1", long_text, {})
        semantic_index.add_text("doc1", long_text, {})  # 重复添加

        stats = semantic_index.get_stats()
        # 应该至少有一个文档（可能有多个块）
        assert stats["document_count"] >= 1

    def test_delete_nonexistent_document(self, semantic_index):
        """测试删除不存在的文档"""
        result = semantic_index.delete_document("nonexistent")
        assert result is False

    def test_large_document(self, semantic_index):
        """测试大文档"""
        large_text = "这是一个很长的文档。" * 1000
        semantic_index.add_text("large_doc", large_text, {})

        stats = semantic_index.get_stats()
        assert stats["document_count"] >= 1


class TestKeywordIndexEdgeCases:
    """测试关键词索引边界情况"""

    def test_empty_query(self, keyword_index):
        """测试空查询"""
        keyword_index.add("doc1", "测试内容", "test.md")
        results = keyword_index.search("", top_k=5)
        assert len(results) == 0

    def test_special_characters_query(self, keyword_index):
        """测试特殊字符查询"""
        keyword_index.add("doc1", "测试内容：包含特殊字符!@#", "test.md")
        results = keyword_index.search("特殊字符", top_k=5)
        assert len(results) > 0

    def test_case_insensitive_search(self, keyword_index):
        """测试大小写不敏感搜索"""
        keyword_index.add("doc1", "人工智能 AI", "test.md")

        results1 = keyword_index.search("AI", top_k=5)
        results2 = keyword_index.search("ai", top_k=5)

        assert len(results1) > 0
        assert len(results2) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
