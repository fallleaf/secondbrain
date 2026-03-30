"""
关键词搜索模块
基于 SQLite FTS5 的全文检索
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional

from .models import SearchResult


class KeywordSearch:
    """关键词搜索类"""
    
    def __init__(self, db_path: str):
        """
        初始化关键词搜索
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = os.path.expanduser(db_path)
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA encoding='UTF-8'")
        conn.row_factory = sqlite3.Row
        return conn
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        file_path: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        执行关键词搜索
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数
            file_path: 文件路径过滤
            filters: 其他过滤条件
        
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 清理查询
        query = self._clean_query(query)
        
        if not query:
            conn.close()
            return []
        
        # 构建查询
        base_query = """
            SELECT 
                c.doc_id as chunk_id,
                c.content,
                c.start_line,
                c.end_line,
                d.doc_id,
                d.file_path,
                d.doc_type,
                d.priority,
                rank
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.doc_id = c.doc_id
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE chunks_fts MATCH ?
        """
        
        params = [query]
        
        # 文件路径过滤
        if file_path:
            base_query += " AND d.file_path LIKE ?"
            params.append(f"%{file_path}%")
        
        # 其他过滤
        if filters:
            if "doc_type" in filters:
                base_query += " AND d.doc_type = ?"
                params.append(filters["doc_type"])
            
            if "min_priority" in filters:
                base_query += " AND d.priority >= ?"
                params.append(filters["min_priority"])
        
        base_query += " ORDER BY rank LIMIT ?"
        params.append(top_k)
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # 转换结果
        results = []
        for row in rows:
            # 计算分数（FTS5 rank 越小越好，转换为相似度）
            rank = row["rank"] or 0
            score = 1.0 / (1.0 + abs(rank)) if rank != 0 else 0.5
            
            result = SearchResult(
                doc_id=row["chunk_id"],
                score=score,
                content=row["content"] or "",
                file_path=row["file_path"] or "",
                start_line=row["start_line"] or 0,
                end_line=row["end_line"] or 0,
                source="keyword",
                metadata={},
                tags=[],
                doc_type=row["doc_type"] or "default",
                priority=row["priority"] or 5
            )
            results.append(result)
        
        return results
    
    def _clean_query(self, query: str) -> str:
        """
        清理查询字符串
        
        Args:
            query: 原始查询
        
        Returns:
            清理后的查询
        """
        query = query.strip()
        
        # 转义特殊字符（保留 * 作为通配符）
        chars_to_escape = ['(', ')', '[', ']', '{', '}', '"', '^', '$']
        for char in chars_to_escape:
            query = query.replace(char, f'\\{char}')
        
        return query
    
    def search_with_highlight(
        self,
        query: str,
        top_k: int = 10,
        highlight_tags: tuple = ("<mark>", "</mark>")
    ) -> List[Dict[str, Any]]:
        """
        执行带高亮的搜索
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数
            highlight_tags: 高亮标签
        
        Returns:
            搜索结果列表（包含高亮内容）
        """
        # 简化实现，暂不处理高亮
        return [r.to_dict() for r in self.search(query, top_k)]


# 测试
if __name__ == "__main__":
    import os
    
    db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
    
    if not os.path.exists(db_path):
        print(f"数据库不存在：{db_path}")
        exit(1)
    
    searcher = KeywordSearch(db_path)
    
    print("🔍 测试关键词搜索...")
    results = searcher.search("机器学习", top_k=5)
    
    print(f"\n找到 {len(results)} 个结果:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.file_path} (score: {result.score:.4f})")
        print(f"   Content: {result.content[:100]}...")
        print()
