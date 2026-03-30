#!/usr/bin/env python3
"""
SecondBrain 数据库迁移脚本 (v1 -> v2)
将现有数据库迁移到新的规范化结构

创建时间：2026-03-30
"""

import sqlite3
import json
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import sqlite_vec


class DatabaseMigrator:
    """数据库迁移器"""
    
    def __init__(self, source_db: str, target_db: str = None):
        """
        初始化迁移器
        
        Args:
            source_db: 源数据库路径
            target_db: 目标数据库路径（如果为 None，则在源数据库上直接迁移）
        """
        self.source_db = os.path.expanduser(source_db)
        self.target_db = os.path.expanduser(target_db) if target_db else source_db
        self.backup_db = f"{self.source_db}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not os.path.exists(self.source_db):
            raise FileNotFoundError(f"源数据库不存在：{self.source_db}")
    
    def backup_database(self):
        """备份源数据库"""
        print(f"📦 备份数据库：{self.source_db}")
        shutil.copy2(self.source_db, self.backup_db)
        print(f"✅ 备份完成：{self.backup_db}")
        return self.backup_db
    
    def _get_source_conn(self) -> sqlite3.Connection:
        """获取源数据库连接"""
        conn = sqlite3.connect(self.source_db)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _get_target_conn(self) -> sqlite3.Connection:
        """获取目标数据库连接"""
        # 如果目标数据库不存在，创建新数据库
        if self.target_db != self.source_db and not os.path.exists(self.target_db):
            os.makedirs(os.path.dirname(self.target_db), exist_ok=True)
        
        conn = sqlite3.connect(self.target_db)
        conn.execute("PRAGMA encoding='UTF-8'")
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def migrate(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        执行迁移
        
        Args:
            dry_run: 仅模拟，不实际执行
        
        Returns:
            迁移统计信息
        """
        stats = {
            "source_db": self.source_db,
            "target_db": self.target_db,
            "start_time": datetime.now().isoformat(),
            "steps": []
        }
        
        print("=" * 60)
        print("🔄 SecondBrain 数据库迁移 (v1 -> v2)")
        print("=" * 60)
        
        # 步骤 1: 备份数据库
        print("\n[1/6] 备份数据库...")
        if not dry_run:
            self.backup_database()
        stats["steps"].append({"step": "backup", "status": "skipped" if dry_run else "completed"})
        
        # 步骤 2: 创建新表结构
        print("\n[2/6] 创建新表结构...")
        if not dry_run:
            self._create_new_schema()
        stats["steps"].append({"step": "create_schema", "status": "skipped" if dry_run else "completed"})
        
        # 步骤 3: 迁移文档数据
        print("\n[3/6] 迁移文档数据...")
        doc_stats = self._migrate_documents() if not dry_run else {"skipped": True}
        stats["steps"].append({"step": "migrate_documents", "status": "completed", "stats": doc_stats})
        
        # 步骤 4: 迁移标签数据
        print("\n[4/6] 迁移标签数据...")
        tag_stats = self._migrate_tags() if not dry_run else {"skipped": True}
        stats["steps"].append({"step": "migrate_tags", "status": "completed", "stats": tag_stats})
        
        # 步骤 5: 迁移向量数据
        print("\n[5/6] 迁移向量数据...")
        vec_stats = self._migrate_vectors() if not dry_run else {"skipped": True}
        stats["steps"].append({"step": "migrate_vectors", "status": "completed", "stats": vec_stats})
        
        # 步骤 6: 验证迁移结果
        print("\n[6/6] 验证迁移结果...")
        if not dry_run:
            verify_stats = self._verify_migration()
            stats["steps"].append({"step": "verify", "status": "completed", "stats": verify_stats})
        else:
            stats["steps"].append({"step": "verify", "status": "skipped"})
        
        stats["end_time"] = datetime.now().isoformat()
        stats["dry_run"] = dry_run
        
        print("\n" + "=" * 60)
        print("✅ 迁移完成!")
        print("=" * 60)
        
        return stats
    
    def _create_new_schema(self):
        """创建新表结构"""
        conn = self._get_target_conn()
        cursor = conn.cursor()
        
        # 读取 SQL 脚本
        sql_file = Path(__file__).parent / "create_new_schema.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # 执行 SQL 脚本（跳过 vectors_vec 和 chunks_fts，稍后单独创建）
        lines = sql_script.split('\n')
        filtered_lines = []
        skip_block = False
        
        for line in lines:
            if 'CREATE VIRTUAL TABLE IF NOT EXISTS vectors_vec' in line:
                skip_block = True
            if skip_block and ');' in line:
                skip_block = False
                continue
            if skip_block:
                continue
                
            if 'CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts' in line:
                skip_block = True
            if skip_block and ');' in line:
                skip_block = False
                continue
            if skip_block:
                continue
                
            filtered_lines.append(line)
        
        filtered_sql = '\n'.join(filtered_lines)
        cursor.executescript(filtered_sql)
        
        # 单独创建 vectors_vec 表
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vectors_vec USING vec0(
                chunk_id TEXT PRIMARY KEY,
                embedding float[512]
            )
        """)
        
        # 单独创建 chunks_fts 表
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id,
                content,
                content='chunks',
                content_rowid='rowid'
            )
        """)
        
        conn.commit()
        
        print(f"✅ 新表结构创建成功")
        
        conn.close()
    
    def _migrate_documents(self) -> Dict[str, Any]:
        """迁移文档数据"""
        source_conn = self._get_source_conn()
        target_conn = self._get_target_conn()
        
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        stats = {"documents": 0, "chunks": 0, "errors": 0}
        
        # 从 chunks 表获取所有唯一的 doc_id
        source_cursor.execute("""
            SELECT DISTINCT doc_id, start_line, end_line 
            FROM chunks 
            ORDER BY doc_id
        """)
        
        chunks = source_cursor.fetchall()
        total = len(chunks)
        
        print(f"   发现 {total} 个文档块，开始迁移...")
        
        # 批量处理
        batch_size = 100
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            
            for chunk in batch:
                doc_id = chunk["doc_id"]
                start_line = chunk["start_line"] or 0
                end_line = chunk["end_line"] or 0
                
                try:
                    # 从 vectors 表获取 metadata
                    source_cursor.execute("SELECT metadata FROM vectors WHERE doc_id = ?", (doc_id,))
                    vec_row = source_cursor.fetchone()
                    
                    metadata = {}
                    file_path = doc_id
                    doc_type = "default"
                    priority = 5
                    tags = []
                    
                    if vec_row and vec_row["metadata"]:
                        try:
                            metadata = json.loads(vec_row["metadata"])
                            # 提取 metadata 中的信息
                            file_path = metadata.get("file_path", doc_id)
                            doc_type = metadata.get("doc_type", "default")
                            priority = metadata.get("priority", 5)
                            tags = metadata.get("tags", [])
                            
                            # 如果 metadata 中有 chunk_content，说明这是分块数据
                            if "chunk_content" in metadata:
                                # 从 chunks 表获取 content
                                source_cursor.execute(
                                    "SELECT content FROM chunks WHERE doc_id = ?",
                                    (doc_id,)
                                )
                                chunk_row = source_cursor.fetchone()
                                if chunk_row:
                                    metadata["chunk_content"] = chunk_row["content"]
                        except json.JSONDecodeError:
                            pass
                    
                    # 插入到 documents 表
                    target_cursor.execute("""
                        INSERT OR REPLACE INTO documents 
                        (doc_id, file_path, doc_type, priority, created_at, updated_at, indexed_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (doc_id, file_path, doc_type, priority))
                    
                    # 插入标签
                    for tag_name in tags:
                        # 确保标签存在
                        target_cursor.execute("""
                            INSERT OR IGNORE INTO tags (tag_name)
                            VALUES (?)
                        """, (tag_name,))
                        
                        # 获取 tag_id
                        target_cursor.execute(
                            "SELECT tag_id FROM tags WHERE tag_name = ?",
                            (tag_name,)
                        )
                        tag_row = target_cursor.fetchone()
                        
                        if tag_row:
                            target_cursor.execute("""
                                INSERT OR IGNORE INTO document_tags (doc_id, tag_id)
                                VALUES (?, ?)
                            """, (doc_id, tag_row["tag_id"]))
                    
                    # 插入 frontmatter
                    if metadata:
                        # 过滤出 frontmatter 相关字段
                        frontmatter_data = {k: v for k, v in metadata.items() 
                                          if k not in ['chunk_content', 'start_line', 'end_line']}
                        if frontmatter_data:
                            target_cursor.execute("""
                                INSERT OR REPLACE INTO frontmatter (doc_id, data)
                                VALUES (?, ?)
                            """, (doc_id, json.dumps(frontmatter_data, ensure_ascii=False)))
                    
                    stats["documents"] += 1
                    
                except Exception as e:
                    print(f"   ⚠️  迁移失败 doc_id={doc_id}: {e}")
                    stats["errors"] += 1
            
            processed += len(batch)
            if processed % 500 == 0:
                print(f"   进度：{processed}/{total} ({100*processed/total:.1f}%)")
            
            target_conn.commit()
        
        # 迁移 chunks 表（保持原有数据）
        print("   迁移 chunks 表...")
        source_cursor.execute("SELECT COUNT(*) FROM chunks")
        total_chunks = source_cursor.fetchone()[0]
        
        batch_size = 500
        for i in range(0, total_chunks, batch_size):
            source_cursor.execute("""
                SELECT doc_id, chunk_index, content, start_line, end_line
                FROM chunks
                LIMIT ? OFFSET ?
            """, (batch_size, i))
            
            chunks_batch = source_cursor.fetchall()
            
            for chunk in chunks_batch:
                # 生成 chunk_id
                chunk_id = f"{chunk['doc_id']}#{chunk['chunk_index']}"
                
                target_cursor.execute("""
                    INSERT OR REPLACE INTO chunks 
                    (chunk_id, doc_id, chunk_index, content, start_line, end_line, heading_level)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (
                    chunk_id,
                    chunk["doc_id"],
                    chunk["chunk_index"],
                    chunk["content"],
                    chunk["start_line"],
                    chunk["end_line"]
                ))
            
            target_conn.commit()
        
        stats["chunks"] = total_chunks
        
        source_conn.close()
        target_conn.close()
        
        print(f"✅ 文档迁移完成：{stats['documents']} 个文档，{stats['chunks']} 个块，{stats['errors']} 个错误")
        return stats
    
    def _migrate_vectors(self) -> Dict[str, Any]:
        """迁移向量数据"""
        source_conn = self._get_source_conn()
        target_conn = self._get_target_conn()
        
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        stats = {"vectors": 0, "errors": 0}
        
        # 从 vectors_vec 表获取所有向量
        source_cursor.execute("SELECT doc_id, embedding FROM vectors_vec")
        vectors = source_cursor.fetchall()
        
        total = len(vectors)
        print(f"   发现 {total} 个向量，开始迁移...")
        
        batch_size = 100
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = vectors[i:i + batch_size]
            
            for vec in batch:
                try:
                    # 生成 chunk_id
                    doc_id = vec["doc_id"]
                    chunk_id = f"{doc_id}#0"  # 默认 chunk_index = 0
                    
                    target_cursor.execute("""
                        INSERT OR REPLACE INTO vectors_vec (chunk_id, embedding)
                        VALUES (?, ?)
                    """, (chunk_id, vec["embedding"]))
                    
                    stats["vectors"] += 1
                    
                except Exception as e:
                    print(f"   ⚠️  迁移失败 chunk_id={chunk_id}: {e}")
                    stats["errors"] += 1
            
            processed += len(batch)
            if processed % 500 == 0:
                print(f"   进度：{processed}/{total} ({100*processed/total:.1f}%)")
            
            target_conn.commit()
        
        source_conn.close()
        target_conn.close()
        
        print(f"✅ 向量迁移完成：{stats['vectors']} 个向量，{stats['errors']} 个错误")
        return stats
    
    def _migrate_tags(self) -> Dict[str, Any]:
        """迁移标签数据（已在 migrate_documents 中完成）"""
        # 这个函数保留用于未来扩展
        return {"status": "completed_in_migrate_documents"}
    
    def _verify_migration(self) -> Dict[str, Any]:
        """验证迁移结果"""
        source_conn = self._get_source_conn()
        target_conn = self._get_target_conn()
        
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        stats = {}
        
        # 比较记录数
        print("   比较记录数...")
        
        # Documents
        source_cursor.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks")
        source_docs = source_cursor.fetchone()[0]
        
        target_cursor.execute("SELECT COUNT(*) FROM documents")
        target_docs = target_cursor.fetchone()[0]
        
        stats["documents"] = {
            "source": source_docs,
            "target": target_docs,
            "match": source_docs == target_docs
        }
        
        # Chunks
        source_cursor.execute("SELECT COUNT(*) FROM chunks")
        source_chunks = source_cursor.fetchone()[0]
        
        target_cursor.execute("SELECT COUNT(*) FROM chunks")
        target_chunks = target_cursor.fetchone()[0]
        
        stats["chunks"] = {
            "source": source_chunks,
            "target": target_chunks,
            "match": source_chunks == target_chunks
        }
        
        # Vectors
        source_cursor.execute("SELECT COUNT(*) FROM vectors_vec")
        source_vecs = source_cursor.fetchone()[0]
        
        target_cursor.execute("SELECT COUNT(*) FROM vectors_vec")
        target_vecs = target_cursor.fetchone()[0]
        
        stats["vectors"] = {
            "source": source_vecs,
            "target": target_vecs,
            "match": source_vecs == target_vecs
        }
        
        # Tags
        target_cursor.execute("SELECT COUNT(*) FROM tags")
        stats["tags"] = {"target": target_cursor.fetchone()[0]}
        
        target_cursor.execute("SELECT COUNT(*) FROM document_tags")
        stats["document_tags"] = {"target": target_cursor.fetchone()[0]}
        
        # Frontmatter
        target_cursor.execute("SELECT COUNT(*) FROM frontmatter")
        stats["frontmatter"] = {"target": target_cursor.fetchone()[0]}
        
        # 测试视图查询
        print("   测试视图查询...")
        try:
            target_cursor.execute("SELECT * FROM v_index_stats")
            stats_view = target_cursor.fetchone()
            stats["views"] = {
                "v_index_stats": {
                    "doc_count": stats_view[0],
                    "chunk_count": stats_view[1],
                    "tag_count": stats_view[2]
                }
            }
            stats["views_ok"] = True
        except Exception as e:
            stats["views_ok"] = False
            stats["views_error"] = str(e)
        
        source_conn.close()
        target_conn.close()
        
        # 打印验证结果
        print("\n   验证结果:")
        for key, value in stats.items():
            if isinstance(value, dict) and "match" in value:
                status = "✅" if value["match"] else "❌"
                print(f"   {status} {key}: {value['source']} -> {value['target']}")
        
        return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SecondBrain 数据库迁移工具")
    parser.add_argument("--source", default="~/.local/share/secondbrain/semantic_index.db",
                       help="源数据库路径")
    parser.add_argument("--target", default=None,
                       help="目标数据库路径（默认：在源数据库上直接迁移）")
    parser.add_argument("--dry-run", action="store_true",
                       help="仅模拟，不实际执行")
    parser.add_argument("--backup-only", action="store_true",
                       help="仅备份，不迁移")
    
    args = parser.parse_args()
    
    try:
        migrator = DatabaseMigrator(args.source, args.target)
        
        if args.backup_only:
            migrator.backup_database()
        else:
            stats = migrator.migrate(dry_run=args.dry_run)
            
            # 保存迁移统计
            stats_file = Path(__file__).parent.parent / "docs" / "migration_stats.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            print(f"\n📊 迁移统计已保存到：{stats_file}")
    
    except Exception as e:
        print(f"\n❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
