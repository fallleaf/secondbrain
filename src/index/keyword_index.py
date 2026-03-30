"""
关键词索引模块

使用 SQLite FTS5 实现全文检索
"""

from utils.logger import get_logger
import sqlite3
import os
import threading
from typing import List, Optional, Dict, Any
import hashlib

# 可选：jieba 分词（用于中文增强）
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    pass

# 导入日志
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = get_logger(__name__)


def _segment_chinese_text(text: str) -> str:
    """
    对中文文本进行分词，在词之间添加空格，增强 FTS5 搜索效果

    Args:
        text: 原始文本

    Returns:
        分词后的文本（词之间用空格分隔）
    """
    if not JIEBA_AVAILABLE:
        # 如果 jieba 不可用，返回原文本（FTS5 unicode61 会按字符切分）
        return text

    # 使用 jieba 精确模式分词
    words = jieba.lcut(text)

    # 过滤掉纯空白字符，但保留标点符号
    filtered_words = []
    for word in words:
        if word.strip():  # 非空
            filtered_words.append(word)
        elif word in [' ', '\t', '\n']:  # 空白字符用空格替代
            filtered_words.append(' ')
        else:
            filtered_words.append(word)

    # 用空格连接所有词
    return ' '.join(filtered_words).strip()


class KeywordIndex:
    """SQLite FTS5 关键词索引"""

    def __init__(self, db_path: str):
        """
        初始化关键词索引

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = os.path.expanduser(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._local = threading.local()  # 线程本地存储
        self._ensure_db()

    def _get_connection(self) -> sqlite3.Connection:
        """获取线程安全的数据库连接（强制 UTF-8 编码）"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            # 连接数据库，确保使用 UTF-8 编码
            self._local.conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # 设置编码（SQLite 默认 UTF-8，但显式设置更安全）
            self._local.conn.execute("PRAGMA encoding='UTF-8'")
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _ensure_db(self) -> None:
        """确保数据库存在并初始化（强制 UTF-8 编码）"""
        # 创建目录
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # 连接数据库，确保使用 UTF-8 编码
        self.conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        # 显式设置编码
        self.conn.execute("PRAGMA encoding='UTF-8'")
        self.conn.row_factory = sqlite3.Row

        # 创建 FTS5 表
        self._create_tables()

    def _create_tables(self) -> None:
        """创建索引表"""
        cursor = self._get_connection().cursor()

        # 创建 FTS5 全文索引表
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(
                content,
                doc_id,
                file_path,
                start_line,
                end_line,
                tokenize='porter unicode61'
            )
        """)

        # 创建元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                doc_id TEXT PRIMARY KEY,
                file_path TEXT,
                start_line INTEGER,
                end_line INTEGER,
                checksum TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_file
            ON metadata(file_path)
        """)

        self._get_connection().commit()

    def add(self, doc_id: str, content: str, file_path: str,
            start_line: int = 0, end_line: int = 0) -> None:
        """添加文档到索引（确保 UTF-8 编码）"""
        cursor = self._get_connection().cursor()

        # 确保 content 是 UTF-8 字符串
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        if isinstance(file_path, bytes):
            file_path = file_path.decode('utf-8')

        checksum = hashlib.md5(content.encode('utf-8')).hexdigest()

        # 检查文档是否已存在
        cursor.execute("SELECT checksum FROM metadata WHERE doc_id = ?", (doc_id,))
        existing = cursor.fetchone()

        if existing:
            if existing['checksum'] == checksum:
                return
            self.delete(doc_id)

        # 中文分词预处理（增强 FTS5 搜索效果）
        segmented_content = _segment_chinese_text(content)

        # 插入文档（使用分词后的内容，确保 UTF-8）
        cursor.execute("""
        INSERT INTO documents (content, doc_id, file_path, start_line, end_line)
        VALUES (?, ?, ?, ?, ?)
        """, (str(segmented_content), str(doc_id), str(file_path), int(start_line), int(end_line)))

        # 插入元数据
        cursor.execute("""
        INSERT OR REPLACE INTO metadata
        (doc_id, file_path, start_line, end_line, checksum, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (str(doc_id), str(file_path), int(start_line), int(end_line), checksum))

        self._get_connection().commit()

    def delete(self, doc_id: str) -> None:
        """删除文档"""
        cursor = self._get_connection().cursor()
        cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        cursor.execute("DELETE FROM metadata WHERE doc_id = ?", (doc_id,))
        self._get_connection().commit()

    def update(self, doc_id: str, content: str, file_path: str,
               start_line: int = 0, end_line: int = 0) -> None:
        """更新文档"""
        self.delete(doc_id)
        self.add(doc_id, content, file_path, start_line, end_line)

    def search(self, query: str, top_k: int = 10,
               file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """搜索文档"""
        cursor = self._get_connection().cursor()
        query = self._clean_query(query)

        if not query:
            return []

        results = []

        # 尝试 FTS5 搜索
        try:
            sql = """
            SELECT doc_id, file_path, start_line, end_line, content, rank
            FROM documents
            WHERE documents MATCH ?
            """
            params: List[Any] = [query]

            if file_path:
                sql += " AND file_path LIKE ?"
                params.append(f"%{file_path}%")

            sql += " ORDER BY rank LIMIT ?"
            params.append(top_k)

            cursor.execute(sql, params)

            for row in cursor.fetchall():
                content = row['content']
                # 确保 content 是 UTF-8 字符串
                if isinstance(content, bytes):
                    content = content.decode('utf-8')

                results.append({
                    'doc_id': row['doc_id'],
                    'file_path': row['file_path'],
                    'start_line': row['start_line'],
                    'end_line': row['end_line'],
                    'content': content,
                    'rank': row['rank']
                })
        except Exception:
            # FTS5 搜索失败，回退到 LIKE 搜索
            pass

        # 如果 FTS5 没有结果，使用 LIKE 搜索（对中文支持更好）
        if not results:
            sql = """
            SELECT doc_id, file_path, start_line, end_line, content, 0 as rank
            FROM documents
            WHERE content LIKE ?
            """
            params = [f"%{query}%"]

            if file_path:
                sql += " AND file_path LIKE ?"
                params.append(f"%{file_path}%")

            sql += " LIMIT ?"
            params.append(top_k)

            cursor.execute(sql, params)

            for row in cursor.fetchall():
                content = row['content']
                # 确保 content 是 UTF-8 字符串
                if isinstance(content, bytes):
                    content = content.decode('utf-8')

                results.append({
                    'doc_id': row['doc_id'],
                    'file_path': row['file_path'],
                    'start_line': row['start_line'],
                    'end_line': row['end_line'],
                    'content': content,
                    'rank': row['rank']
                })

        return results

    def _clean_query(self, query: str) -> str:
        """
        清理查询字符串

        注意：保留 * 作为通配符（如 telecom*），其他特殊字符进行转义
        """
        query = query.strip()
        if not query:
            return query

        # 需要转义的特殊字符（排除 *，保留其作为通配符功能）
        chars_to_escape = ['(', ')', '[', ']', '{', '}', '"', '^', '$']

        for char in chars_to_escape:
            query = query.replace(char, f'\\{char}')

        return query

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        cursor = self._get_connection().cursor()

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(length(content)) FROM documents")
        total_size = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(DISTINCT file_path) FROM metadata")
        file_count = cursor.fetchone()[0]

        db_size = 0
        if os.path.exists(self.db_path):
            db_size = os.path.getsize(self.db_path)

        return {
            'document_count': doc_count,
            'file_count': file_count,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / 1024 / 1024,
            'db_path': self.db_path,
            'db_size_mb': db_size / 1024 / 1024
        }

    def rebuild(self) -> None:
        """重建索引"""
        cursor = self._get_connection().cursor()
        cursor.execute("DELETE FROM documents")
        cursor.execute("DELETE FROM metadata")
        self._get_connection().commit()
        logger.info("✅ 索引已清空")

    def close(self) -> None:
        """关闭数据库连接，清理线程本地资源"""
        # 关闭主连接
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                logger.warning(f"关闭主连接时出错：{e}")
            self.conn = None

        # 清理线程本地连接
        if hasattr(self._local, 'conn') and self._local.conn:
            try:
                self._local.conn.close()
            except Exception as e:
                logger.warning(f"关闭线程本地连接时出错：{e}")
            self._local.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 测试
if __name__ == "__main__":
    # 删除旧测试数据库
    test_db = os.path.expanduser("~/.local/share/secondbrain/test_keyword_index.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    # 创建测试索引
    index = KeywordIndex(test_db)

    # 添加测试文档
    test_docs = [
        {
            'doc_id': 'doc1',
            'content': '这是第一个测试文档。它包含一些关键词：机器学习、人工智能。',
            'file_path': 'test/doc1.md',
            'start_line': 1,
            'end_line': 5
        },
        {
            'doc_id': 'doc2',
            'content': '这是第二个测试文档。它讨论了深度学习和神经网络。',
            'file_path': 'test/doc2.md',
            'start_line': 1,
            'end_line': 3
        },
        {
            'doc_id': 'doc3',
            'content': '人工智能是未来的趋势。机器学习和深度学习都是重要领域。',
            'file_path': 'test/doc3.md',
            'start_line': 1,
            'end_line': 2
        }
    ]

    for doc in test_docs:
        index.add(**doc)

    print("✅ 测试文档已添加")

    # 搜索测试
    print("\n🔍 搜索测试：'机器学习'")
    results = index.search('机器学习', top_k=5)
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['file_path']} (行 {result['start_line']}-{result['end_line']})")
        print(f"   内容：{result['content'][:80]}...")

    print("\n🔍 搜索测试：'人工智能'")
    results = index.search('人工智能', top_k=5)
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['file_path']} (行 {result['start_line']}-{result['end_line']})")
        print(f"   内容：{result['content'][:80]}...")

    # 统计信息
    print("\n📊 索引统计")
    stats = index.get_stats()
    print(f"文档数量：{stats['document_count']}")
    print(f"文件数量：{stats['file_count']}")
    print(f"总大小：{stats['total_size_mb']:.2f} MB")
    print(f"数据库大小：{stats['db_size_mb']:.2f} MB")

    index.close()
