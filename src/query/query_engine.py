"""
统一查询接口 - SecondBrainQuery 主类
"""

import sqlite3
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

import sqlite_vec

from .models import SearchResult, NoteInfo, LinkInfo, TagInfo, IndexStats
from .cache import QueryCache, get_query_cache
from .filters import QueryFilters
from .semantic_search import SemanticSearch
from .keyword_search import KeywordSearch
from .hybrid_search import HybridSearch


class SecondBrainQuery:
    """统一查询接口"""
    
    def __init__(self, db_path: str, vault_path: str = None):
        """
        初始化查询引擎
        
        Args:
            db_path: 数据库路径
            vault_path: Vault 根路径（用于拼接文件绝对路径）
        """
        self.db_path = os.path.expanduser(db_path)
        self.vault_path = os.path.expanduser(vault_path) if vault_path else None
        
        # 初始化组件
        self.semantic = SemanticSearch(self.db_path)
        self.keyword = KeywordSearch(self.db_path)
        self.hybrid = HybridSearch(self.db_path)
        self.filters = QueryFilters()
        self.cache = get_query_cache()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA encoding='UTF-8'")
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def search(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        统一搜索接口
        
        Args:
            query: 搜索关键词
            mode: 搜索模式 (semantic/keyword/hybrid)
            top_k: 返回结果数
            filters: 过滤条件
        
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        # 检查缓存
        cache_key = (query, mode, top_k, str(filters))
        cached = self.cache.get(*cache_key)
        if cached is not None:
            return cached
        
        # 执行搜索
        if mode == "semantic":
            results = self.semantic.search(query, top_k=top_k, filters=filters)
        elif mode == "keyword":
            results = self.keyword.search(query, top_k=top_k, filters=filters)
        else:  # hybrid
            results = self.hybrid.search(query, top_k=top_k, filters=filters)
        
        # 缓存结果
        self.cache.set(results, *cache_key, ttl=300)
        
        return results
    
    def get_note_info(self, doc_id: str) -> Optional[NoteInfo]:
        """获取笔记详细信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 获取文档基本信息
        cursor.execute("""
            SELECT * FROM documents WHERE doc_id = ?
        """, (doc_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        # 获取标签
        cursor.execute("""
            SELECT t.tag_name FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.tag_id
            WHERE dt.doc_id = ?
        """, (doc_id,))
        tags = [r["tag_name"] for r in cursor.fetchall()]
        
        # 获取链接统计
        cursor.execute("SELECT COUNT(*) FROM links WHERE source_doc_id = ?", (doc_id,))
        link_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM links WHERE target_doc_id = ?", (doc_id,))
        backlink_count = cursor.fetchone()[0]
        
        # 获取标题（从文件路径或 frontmatter）
        title = self._extract_title(row["file_path"])
        
        conn.close()
        
        return NoteInfo(
            doc_id=doc_id,
            file_path=row["file_path"],
            vault_name=row["vault_name"],
            title=title,
            tags=tags,
            priority=row["priority"],
            doc_type=row["doc_type"],
            link_count=link_count,
            backlink_count=backlink_count,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            indexed_at=row["indexed_at"]
        )
    
    def get_backlinks(self, doc_id: str) -> List[LinkInfo]:
        """获取笔记的反向链接"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, d.file_path as source_file_path
            FROM links l
            LEFT JOIN documents d ON l.source_doc_id = d.doc_id
            WHERE l.target_doc_id = ?
        """, (doc_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_link_info(row) for row in rows]
    
    def get_links(self, doc_id: str) -> List[LinkInfo]:
        """获取笔记的出站链接"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, d.file_path as target_file_path
            FROM links l
            LEFT JOIN documents d ON l.target_doc_id = d.doc_id
            WHERE l.source_doc_id = ?
        """, (doc_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_link_info(row) for row in rows]
    
    def find_broken_links(self) -> List[LinkInfo]:
        """查找所有断裂链接"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, d.file_path as source_file_path
            FROM links l
            LEFT JOIN documents d ON l.source_doc_id = d.doc_id
            WHERE l.is_broken = 1
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_link_info(row) for row in rows]
    
    def find_orphaned_notes(self) -> List[str]:
        """查找孤立笔记（无入链）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT doc_id FROM documents
            WHERE doc_id NOT IN (
                SELECT target_doc_id FROM links WHERE target_doc_id IS NOT NULL
            )
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row["doc_id"] for row in rows]
    
    def get_index_stats(self) -> IndexStats:
        """获取索引统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 基本统计
        cursor.execute("SELECT * FROM v_index_stats")
        stats_row = cursor.fetchone()
        
        # 文档类型分布
        cursor.execute("SELECT * FROM v_doc_type_stats")
        doc_type_dist = {row["doc_type"]: row["count"] for row in cursor.fetchall()}
        
        # 优先级分布
        cursor.execute("SELECT * FROM v_priority_stats")
        priority_dist = {int(row["priority"]): row["count"] for row in cursor.fetchall()}
        
        conn.close()
        
        return IndexStats(
            doc_count=stats_row[0],
            chunk_count=stats_row[1],
            tag_count=stats_row[2],
            link_count=stats_row[3],
            broken_link_count=stats_row[4],
            file_count=stats_row[5],
            frontmatter_count=stats_row[6],
            doc_type_distribution=doc_type_dist,
            priority_distribution=priority_dist
        )
    
    def list_tags(self, vault_name: str = None) -> List[TagInfo]:
        """列出所有标签及使用情况"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        query = "SELECT * FROM v_tag_stats ORDER BY actual_count DESC"
        cursor.execute(query)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            TagInfo(
                tag_id=row[0],
                tag_name=row[1],
                usage_count=row[2],
                actual_count=row[3]
            )
            for row in rows
        ]
    
    def search_by_tags(
        self,
        tags: List[str],
        mode: str = "any",
        top_k: int = 10
    ) -> List[NoteInfo]:
        """按标签搜索笔记"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if mode == "all":
            # 必须包含所有标签
            placeholders = ",".join(["?" for _ in tags])
            query = f"""
                SELECT d.* FROM documents d
                JOIN document_tags dt ON d.doc_id = dt.doc_id
                JOIN tags t ON dt.tag_id = t.tag_id
                WHERE t.tag_name IN ({placeholders})
                GROUP BY d.doc_id
                HAVING COUNT(DISTINCT t.tag_name) = ?
                LIMIT ?
            """
            cursor.execute(query, tags + [len(tags), top_k])
        else:
            # 包含任意标签
            placeholders = ",".join(["?" for _ in tags])
            query = f"""
                SELECT DISTINCT d.* FROM documents d
                JOIN document_tags dt ON d.doc_id = dt.doc_id
                JOIN tags t ON dt.tag_id = t.tag_id
                WHERE t.tag_name IN ({placeholders})
                LIMIT ?
            """
            cursor.execute(query, tags + [top_k])
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_note_info(row) for row in rows]
    
    # 辅助方法
    def _extract_title(self, file_path: str) -> str:
        """从文件路径提取标题"""
        if not file_path:
            return "Untitled"
        
        # 提取文件名
        path = Path(file_path)
        title = path.stem
        
        # 替换特殊字符
        title = title.replace("-", " ").replace("_", " ")
        
        return title.title()
    
    def _row_to_link_info(self, row) -> LinkInfo:
        """转换数据库行到 LinkInfo"""
        return LinkInfo(
            link_id=row["link_id"],
            source_doc_id=row["source_doc_id"],
            source_file_path=row["source_file_path"] or "",
            target_doc_id=row["target_doc_id"],
            target_file_path=row["target_file_path"],
            link_text=row["link_text"],
            link_type=row["link_type"] or "internal",
            is_broken=bool(row["is_broken"]),
            created_at=row["created_at"]
        )
    
    def _row_to_note_info(self, row) -> NoteInfo:
        """转换数据库行到 NoteInfo"""
        # 获取标签
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.tag_name FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.tag_id
            WHERE dt.doc_id = ?
        """, (row["doc_id"],))
        tags = [r["tag_name"] for r in cursor.fetchall()]
        conn.close()
        
        return NoteInfo(
            doc_id=row["doc_id"],
            file_path=row["file_path"],
            vault_name=row["vault_name"],
            title=self._extract_title(row["file_path"]),
            tags=tags,
            priority=row["priority"],
            doc_type=row["doc_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            indexed_at=row["indexed_at"]
        )


# 测试
if __name__ == "__main__":
    db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
    
    if not os.path.exists(db_path):
        print(f"数据库不存在：{db_path}")
        exit(1)
    
    query_engine = SecondBrainQuery(db_path)
    
    print("🔍 测试统一查询接口...")
    
    # 测试搜索
    print("\n1. 混合搜索 '人工智能':")
    results = query_engine.search("人工智能", mode="hybrid", top_k=3)
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r.file_path} (score: {r.score:.4f})")
    
    # 测试统计
    print("\n2. 索引统计:")
    stats = query_engine.get_index_stats()
    print(f"   文档数：{stats.doc_count}")
    print(f"   分块数：{stats.chunk_count}")
    print(f"   标签数：{stats.tag_count}")
    
    # 测试标签列表
    print("\n3. 标签列表 (前 5):")
    tags = query_engine.list_tags()
    for tag in tags[:5]:
        print(f"   {tag.tag_name}: {tag.actual_count} 次")
    
    print("\n✅ 测试完成!")
