#!/usr/bin/env python3
"""
生产级语义索引类，支持向量搜索、元数据管理和全文检索
"""
import json
import logging
import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

import sqlite_vec

# 修复相对导入问题
try:
    from ..utils.perf_monitor import get_perf_monitor
except ImportError:
    def get_perf_monitor():
        return None

logger = logging.getLogger(__name__)


class SemanticIndex:
    """生产级语义索引类，支持向量搜索、元数据管理和全文检索"""

    DEFAULT_DIM = 512  # BAAI/bge-small-zh-v1.5 默认维度

    def __init__(self, index_path: str, dim: Optional[int] = None):
        """
        初始化语义索引

        Args:
            index_path: 索引数据库路径
            dim: 向量维度，如果为 None 则使用默认值
        """
        self.index_path = index_path
        self.dim = dim or self.DEFAULT_DIM
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        conn = sqlite3.connect(self.index_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        cursor = conn.cursor()

        # 创建 vectors 表（存储元数据）
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS vectors (
            doc_id TEXT PRIMARY KEY,
            metadata TEXT
        )
        """)

        # 创建 vectors_vec 虚拟表（存储向量）
        cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vectors_vec USING vec0(
            doc_id TEXT PRIMARY KEY,
            embedding float[{self.dim}]
        )
        """)

        # 创建 chunks 表（存储分块内容）
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS chunks (
            doc_id TEXT PRIMARY KEY,
            chunk_index INTEGER,
            content TEXT,
            start_line INTEGER,
            end_line INTEGER
        )
        """)

        # 创建 FTS5 全文检索索引
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            doc_id,
            chunk_index,
            content,
            content=''
        )
        """)

        conn.commit()
        conn.close()

        logger.info("Database initialized at %s (dim=%d)", self.index_path, int(self.dim))

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.index_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row  # 启用行访问
        return conn

    @staticmethod
    def _transaction(conn: sqlite3.Connection):
        """事务上下文管理器"""
        class Transaction:
            def __enter__(self_):
                return conn

            def __exit__(self_, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    conn.commit()
                else:
                    conn.rollback()

        return Transaction()

    def _ensure_utf8(self, obj: Any) -> Any:
        """确保对象中的字符串是 UTF-8 编码"""
        if isinstance(obj, str):
            return str(obj)
        elif isinstance(obj, dict):
            return {self._ensure_utf8(k): self._ensure_utf8(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_utf8(item) for item in obj]
        else:
            return obj

    # -----------------------------
    # Insert APIs
    # -----------------------------
    def add_embedding(
        self,
        doc_id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        content: Optional[str] = None,
        start_line: int = 0,
        end_line: int = 0
    ) -> bool:
        """
        添加向量嵌入

        Args:
            doc_id: 文档 ID
            embedding: 向量嵌入
            metadata: 元数据
            content: 文本内容（可选，如果提供则存储到 chunks 表）
            start_line: 起始行号
            end_line: 结束行号

        Returns:
            bool: 操作是否成功
        """
        if len(embedding) != self.dim:
            raise ValueError(f"Expected dim {self.dim}, got {len(embedding)}")

        # 确保 metadata 中的字符串是 UTF-8
        metadata = self._ensure_utf8(metadata) if metadata else {}

        monitor = get_perf_monitor()
        if monitor:
            with monitor.start("add_embedding"):
                pass

        try:
            with self._transaction(self._get_conn()) as conn:
                cur = conn.cursor()

                doc_id_str = str(doc_id)
                emb_blob = sqlite_vec.serialize_float32(embedding)
                metadata_json = json.dumps(metadata, ensure_ascii=False)

                # 1. 插入元数据
                cur.execute(
                    "INSERT OR REPLACE INTO vectors (doc_id, metadata) VALUES (?, ?)",
                    (doc_id_str, metadata_json)
                )

                # 2. 插入向量到 vectors_vec 虚拟表（指定 doc_id）
                cur.execute(
                    "INSERT OR REPLACE INTO vectors_vec (doc_id, embedding) VALUES (?, ?)",
                    (doc_id_str, emb_blob)
                )

                # 3. 如果提供了 content，插入到 chunks 表和 FTS 索引
                if content is not None:
                    # 更新 metadata 中的 chunk 信息
                    chunk_metadata = metadata.copy()
                    chunk_metadata['chunk_content'] = content
                    chunk_metadata['start_line'] = start_line
                    chunk_metadata['end_line'] = end_line
                    metadata_json = json.dumps(chunk_metadata, ensure_ascii=False)

                    # 更新 vectors 表
                    cur.execute(
                        "UPDATE vectors SET metadata = ? WHERE doc_id = ?",
                        (metadata_json, doc_id_str)
                    )

                    # 插入到 chunks 表
                    chunk_index = 0
                    if '#' in doc_id_str:
                        try:
                            chunk_index = int(doc_id_str.rsplit('#', 1)[1])
                        except (ValueError, IndexError):
                            chunk_index = 0

                    sl = int(start_line) if start_line is not None else 0
                    el = int(end_line) if end_line is not None else 0

                    cur.execute("""
                    INSERT OR REPLACE INTO chunks (doc_id, chunk_index, content, start_line, end_line)
                    VALUES (?, ?, ?, ?, ?)
                    """, (doc_id_str, chunk_index, content, sl, el))

                    # 插入到 FTS5 索引
                    cur.execute("""
                    INSERT OR REPLACE INTO chunks_fts (doc_id, chunk_index, content)
                    VALUES (?, ?, ?)
                    """, (doc_id_str, chunk_index, content))

                if monitor:
                    pass

                logger.debug(f"Added embedding for doc_id: {doc_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to add embedding for {doc_id}: {e}")
            return False

    def add_embeddings_batch(
        self,
        items: List[Tuple[str, List[float], Optional[Dict[str, Any]], Optional[str], int, int]]
    ) -> Tuple[int, int]:
        """
        批量添加向量嵌入

        Args:
            items: List of (doc_id, embedding, metadata, content, start_line, end_line)

        Returns:
            Tuple[int, int]: (成功数量，失败数量)
        """
        if not items:
            return 0, 0

        success_count = 0
        fail_count = 0

        try:
            with self._transaction(self._get_conn()) as conn:
                cur = conn.cursor()

                vec_rows = []
                meta_rows = []
                chunk_rows = []
                fts_rows = []

                for item in items:
                    # 兼容旧版本（3 个元素）和新版本（6 个元素）
                    if len(item) == 3:
                        doc_id, emb, meta = item
                        content, start_line, end_line = None, 0, 0
                    elif len(item) == 6:
                        doc_id, emb, meta, content, start_line, end_line = item
                    else:
                        logger.warning(f"Invalid item format: {item}")
                        fail_count += 1
                        continue

                    if len(emb) != self.dim:
                        logger.warning(f"Dim mismatch for {doc_id}: expected {self.dim}, got {len(emb)}")
                        fail_count += 1
                        continue

                    # 确保 meta 是字典或字符串
                    if isinstance(meta, str):
                        metadata_dict = json.loads(meta) if meta else {}
                    elif isinstance(meta, dict):
                        metadata_dict = meta
                    else:
                        metadata_dict = {}

                    doc_id_str = str(doc_id)

                    # 序列化 metadata 为 JSON 字符串
                    metadata_json = json.dumps(metadata_dict, ensure_ascii=False)

                    vec_rows.append((doc_id_str, sqlite_vec.serialize_float32(emb)))
                    meta_rows.append((doc_id_str, metadata_json))

                    # 如果有内容，准备 chunks 和 FTS 数据
                    if content is not None:
                        # 从 doc_id 中提取 chunk_index (格式：file_path#chunk_index)
                        chunk_index = 0
                        if '#' in doc_id_str:
                            try:
                                chunk_index = int(doc_id_str.rsplit('#', 1)[1])
                            except (ValueError, IndexError):
                                chunk_index = 0

                        # 确保 start_line 和 end_line 是整数
                        sl = int(start_line) if start_line is not None else 0
                        el = int(end_line) if end_line is not None else 0

                        chunk_rows.append((doc_id_str, chunk_index, content, sl, el))
                        fts_rows.append((doc_id_str, chunk_index, content))

                # 批量插入 vectors
                if meta_rows:
                    logger.debug(f"Inserting {len(meta_rows)} rows into vectors table")
                    cur.executemany(
                        "INSERT OR REPLACE INTO vectors (doc_id, metadata) VALUES (?, ?)",
                        meta_rows
                    )

                # 批量插入 vectors_vec
                if vec_rows:
                    logger.debug(f"Inserting {len(vec_rows)} rows into vectors_vec table")
                    cur.executemany(
                        "INSERT OR REPLACE INTO vectors_vec (doc_id, embedding) VALUES (?, ?)",
                        vec_rows
                    )

                # 批量插入 chunks
                if chunk_rows:
                    logger.debug(f"Inserting {len(chunk_rows)} rows into chunks table")
                    cur.executemany("""
                    INSERT OR REPLACE INTO chunks (doc_id, chunk_index, content, start_line, end_line)
                    VALUES (?, ?, ?, ?, ?)
                    """, chunk_rows)

                # 批量插入 FTS
                if fts_rows:
                    logger.debug(f"Inserting {len(fts_rows)} rows into chunks_fts table")
                    cur.executemany("""
                    INSERT OR REPLACE INTO chunks_fts (doc_id, chunk_index, content)
                    VALUES (?, ?, ?)
                    """, fts_rows)

                success_count = len(vec_rows)
                logger.info(f"Batch insert completed: {success_count} success, {fail_count} failed")
                return success_count, fail_count

        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            import traceback
            traceback.print_exc()
            return success_count, len(items) - success_count

    # -----------------------------
    # Search APIs
    # -----------------------------
    def search(
        self,
        query: List[float],
        top_k: int = 10,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
        include_content: bool = True
    ) -> List[Dict[str, Any]]:
        """
        执行语义搜索

        Args:
            query: 查询向量
            top_k: 返回结果数
            min_distance: 最小距离阈值（过滤）
            max_distance: 最大距离阈值（过滤）
            include_content: 是否包含 content 字段（默认 True）

        Returns:
            List[Dict]: 搜索结果，包含 doc_id, distance, metadata, content, start_line, end_line
        """
        if len(query) != self.dim:
            raise ValueError(f"Query dim mismatch: expected {self.dim}, got {len(query)}")

        conn = self._get_conn()
        cur = conn.cursor()

        query_blob = sqlite_vec.serialize_float32(query)

        # 构建查询语句：同时获取 metadata 和 content
        base_query = """
        SELECT vectors.doc_id, distance, vectors.metadata, chunks.content, chunks.start_line, chunks.end_line
        FROM vectors_vec
        JOIN vectors ON vectors_vec.doc_id = vectors.doc_id
        LEFT JOIN chunks ON chunks.doc_id = vectors.doc_id
        WHERE vectors_vec.embedding MATCH ? AND k = ?
        ORDER BY distance
        """

        params = [query_blob, top_k]

        cur.execute(base_query, params)

        results = []
        for row in cur.fetchall():
            doc_id = row["doc_id"]
            distance = float(row["distance"])

            # 应用距离过滤
            if min_distance is not None and distance < min_distance:
                continue
            if max_distance is not None and distance > max_distance:
                continue

            metadata_raw = row["metadata"]

            # 解析 metadata JSON
            try:
                metadata = json.loads(metadata_raw) if metadata_raw else {}
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse metadata for {doc_id}: {e}")
                metadata = {}

            # 构建结果字典
            result = {
                "doc_id": doc_id,
                "distance": distance,
                "metadata": metadata,
            }

            # 如果请求包含 content，直接从数据库获取
            if include_content:
                result["content"] = row["content"] or ""
                result["start_line"] = row["start_line"] or 0
                result["end_line"] = row["end_line"] or 0
            else:
                result["content"] = None
                result["start_line"] = None
                result["end_line"] = None

            results.append(result)

        logger.debug(f"Search completed: {len(results)} results for top_k={top_k}")
        return results

    def search_text(self, query: str, top_k: int = 10) -> List[Tuple[str, int, str, float]]:
        """
        执行全文检索（关键词搜索）

        Args:
            query: 查询文本
            top_k: 返回结果数

        Returns:
            List[Tuple[doc_id, chunk_index, content, score]]
        """
        conn = self._get_conn()
        cur = conn.cursor()

        # 使用 FTS5 搜索
        cur.execute(f"""
        SELECT doc_id, chunk_index, content, rank
        FROM chunks_fts
        WHERE chunks_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """, (query, top_k))

        results = []
        for row in cur.fetchall():
            doc_id = row[0]
            chunk_index = row[1]
            content = row[2]
            rank = row[3]

            # 将 rank 转换为相似度分数（越小越好）
            score = 1.0 / (1.0 + rank)

            results.append((doc_id, chunk_index, content, score))

        logger.debug(f"Text search completed: {len(results)} results for query='{query}'")
        return results

    def delete(self, doc_id: str) -> bool:
        """
        删除文档

        Args:
            doc_id: 文档 ID

        Returns:
            bool: 操作是否成功
        """
        try:
            conn = self._get_conn()
            cur = conn.cursor()

            # 删除 vectors 表
            cur.execute("DELETE FROM vectors WHERE doc_id = ?", (doc_id,))

            # 删除 vectors_vec 表
            cur.execute("DELETE FROM vectors_vec WHERE doc_id = ?", (doc_id,))

            # 删除 chunks 表
            cur.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))

            # 删除 FTS 索引
            cur.execute("DELETE FROM chunks_fts WHERE doc_id = ?", (doc_id,))

            conn.commit()
            conn.close()

            logger.info(f"Deleted doc_id: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete doc_id {doc_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息

        Returns:
            Dict: 统计信息
        """
        conn = self._get_conn()
        cur = conn.cursor()

        stats = {}

        # 统计 vectors 表
        cur.execute("SELECT COUNT(*) FROM vectors")
        stats["vectors_count"] = cur.fetchone()[0]

        # 统计 chunks 表
        cur.execute("SELECT COUNT(*) FROM chunks")
        stats["chunks_count"] = cur.fetchone()[0]

        # 统计总内容长度
        cur.execute("SELECT SUM(length(content)) FROM chunks")
        stats["total_content_length"] = cur.fetchone()[0] or 0

        conn.close()

        return stats
