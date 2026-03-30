"""
语义搜索模块
基于 sqlite-vec 的向量相似度搜索
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

import sqlite_vec

# 导入项目模块
import sys
from pathlib import Path as PathLib
project_root = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.query.models import SearchResult
from src.index.embedder import Embedder


class SemanticSearch:
    """语义搜索类"""
    
    def __init__(self, db_path: str):
        """
        初始化语义搜索
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = os.path.expanduser(db_path)
        self.embedder = Embedder()
        self.dim = self.embedder.embedding_dim
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        min_distance: float = None,
        max_distance: float = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        执行语义搜索
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数
            min_distance: 最小距离阈值
            max_distance: 最大距离阈值
            filters: 过滤条件
        
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        # 1. 生成查询向量
        query_vector = self.embedder.encode_single(query)
        
        # 2. 执行向量搜索
        conn = self._get_conn()
        cursor = conn.cursor()
        
        query_blob = sqlite_vec.serialize_float32(query_vector.tolist())
        
        # 基础查询
        base_query = """
            SELECT 
                v.doc_id as chunk_id,
                v.distance,
                vm.metadata,
                c.content,
                c.start_line,
                c.end_line,
                d.file_path,
                d.doc_type,
                d.priority
            FROM vectors_vec v
            JOIN vectors vm ON v.doc_id = vm.doc_id
            JOIN chunks c ON v.doc_id = c.doc_id
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE v.embedding MATCH ? AND k = ?
        """
        
        params = [query_blob, top_k * 2]
        
        # 应用过滤条件
        if filters:
            where_clauses = []
            
            # 文档类型过滤
            if "doc_type" in filters:
                where_clauses.append("d.doc_type = ?")
                params.append(filters["doc_type"])
            
            # 优先级过滤
            if "min_priority" in filters:
                where_clauses.append("d.priority >= ?")
                params.append(filters["min_priority"])
            
            # 文件路径过滤
            if "file_path" in filters:
                where_clauses.append("d.file_path LIKE ?")
                params.append(f"%{filters['file_path']}%")
            
            if where_clauses:
                base_query += " AND " + " AND ".join(where_clauses)
        
        base_query += " ORDER BY distance LIMIT ?"
        params.append(top_k * 2)
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # 3. 转换结果
        results = []
        for row in rows:
            distance = float(row["distance"])
            
            # 应用距离过滤
            if min_distance is not None and distance < min_distance:
                continue
            if max_distance is not None and distance > max_distance:
                continue
            
            # 解析 metadata
            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except json.JSONDecodeError:
                    pass
            
            # 转换为相似度分数
            similarity = 1.0 / (1.0 + distance)
            
            # 提取标签
            tags = metadata.get("tags", [])
            
            result = SearchResult(
                doc_id=row["chunk_id"],
                score=similarity,
                content=row["content"] or "",
                file_path=row["file_path"] or "",
                start_line=row["start_line"] or 0,
                end_line=row["end_line"] or 0,
                source="semantic",
                metadata=metadata,
                tags=tags,
                doc_type=row["doc_type"] or "default",
                priority=row["priority"] or 5
            )
            results.append(result)
        
        return results
    
    def search_by_vector(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        通过向量执行搜索
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数
            filters: 过滤条件
        
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        if len(query_vector) != self.dim:
            raise ValueError(f"Expected dimension {self.dim}, got {len(query_vector)}")
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        query_blob = sqlite_vec.serialize_float32(query_vector)
        
        query = """
            SELECT 
                v.chunk_id,
                v.distance,
                v.metadata,
                c.content,
                c.start_line,
                c.end_line,
                d.file_path,
                d.doc_type,
                d.priority
            FROM vectors_vec v
            JOIN vectors_meta vm ON v.chunk_id = vm.chunk_id
            JOIN chunks c ON v.chunk_id = c.chunk_id
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY distance
            LIMIT ?
        """
        
        cursor.execute(query, [query_blob, top_k, top_k])
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            distance = float(row["distance"])
            similarity = 1.0 / (1.0 + distance)
            
            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except json.JSONDecodeError:
                    pass
            
            tags = metadata.get("tags", [])
            
            result = SearchResult(
                doc_id=row["chunk_id"],
                score=similarity,
                content=row["content"] or "",
                file_path=row["file_path"] or "",
                start_line=row["start_line"] or 0,
                end_line=row["end_line"] or 0,
                source="semantic",
                metadata=metadata,
                tags=tags,
                doc_type=row["doc_type"] or "default",
                priority=row["priority"] or 5
            )
            results.append(result)
        
        return results
    
    def get_similar_chunks(
        self,
        doc_id: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        获取与指定文档相似的块
        
        Args:
            doc_id: 文档 ID
            top_k: 返回结果数
        
        Returns:
            List[SearchResult]: 相似块列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 获取文档的向量
        cursor.execute("""
            SELECT embedding FROM vectors_vec
            WHERE chunk_id = ?
        """, (doc_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return []
        
        query_vector = sqlite_vec.deserialize_float32(row["embedding"])
        conn.close()
        
        return self.search_by_vector(query_vector.tolist(), top_k)


# 测试
if __name__ == "__main__":
    # 测试语义搜索
    db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
    
    if not os.path.exists(db_path):
        print(f"数据库不存在：{db_path}")
        exit(1)
    
    searcher = SemanticSearch(db_path)
    
    print("🔍 测试语义搜索...")
    results = searcher.search("人工智能", top_k=5)
    
    print(f"\n找到 {len(results)} 个结果:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.file_path} (score: {result.score:.4f})")
        print(f"   Tags: {', '.join(result.tags)}")
        print(f"   Content: {result.content[:100]}...")
        print()
