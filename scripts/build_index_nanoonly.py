#!/usr/bin/env python3
"""
只处理 NanobotMemory vault 的索引构建脚本
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import sqlite3
import sqlite_vec
from fastembed import TextEmbedding

from src.tools.adaptive_chunker import AdaptiveChunker


def build_index(vault_path: str, db_path: str, model_name: str = "BAAI/bge-small-zh-v1.5"):
    """构建语义索引（使用 AdaptiveChunker）"""
    print(f"🚀 开始构建语义索引（AdaptiveChunker）...")
    print(f" - Vault: {vault_path}")
    print(f" - 数据库：{db_path}")
    print(f" - 模型：{model_name}")
    print()

    model = TextEmbedding(model_name=model_name)
    test_embedding = list(model.embed(["test"]))[0]
    actual_dim = len(test_embedding)
    print(f"✅ 模型加载成功 (维度：{actual_dim})")
    print()

    print("🗄️ 初始化数据库...")
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f" - 已删除旧数据库")
    else:
        print(f" - 新建数据库")

    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    cursor = conn.cursor()

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS vectors (
    doc_id TEXT PRIMARY KEY,
    embedding F32_BLOB({actual_dim}),
    metadata TEXT
    )
    """)

    cursor.execute(f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS vectors_vec USING vec0(
    rowid INTEGER PRIMARY KEY,
    embedding float[{actual_dim}]
    )
    """)

    conn.commit()
    print(f"✅ 数据库初始化成功 (维度：{actual_dim})")
    print()

    # 初始化 AdaptiveChunker
    chunker = AdaptiveChunker()

    vault_path = Path(vault_path)
    md_files = list(vault_path.rglob("*.md"))
    excluded = {'.obsidian', '.trash', '.git', '__pycache__'}
    filtered_files = [f for f in md_files if not any(excluded.intersection(f.parts))]

    print(f"📄 发现 {len(filtered_files)} 个笔记文件")
    print()

    total_chunks = 0
    success_count = 0
    error_count = 0
    start_time = time.time()

    # 统计文档类型分布
    doc_type_stats = {}

    for i, file_path in enumerate(filtered_files, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用 AdaptiveChunker 分块
            chunks = chunker.chunk_file(str(file_path), content, {})

            if not chunks:
                continue

            # 向量化 (batch)
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = list(model.embed(chunk_texts))
            embeddings = [np.array(e) for e in embeddings]

            rel_path = str(file_path.relative_to(vault_path))

            for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_id = f"{rel_path}#{j}"
                embedding_bytes = sqlite_vec.serialize_float32(embedding.tolist())

                # 合并 chunk 的元数据和额外信息
                metadata = chunk.metadata.copy()
                metadata.update({
                    'file_path': rel_path,
                    'chunk_index': j,
                    'total_chunks': len(chunks)
                })
                metadata_json = json.dumps(metadata)

                cursor.execute("""
                INSERT OR REPLACE INTO vectors (doc_id, embedding, metadata)
                VALUES (?, ?, ?)
                """, (doc_id, embedding_bytes, metadata_json))

                # 插入到 vectors_vec 虚拟表（使用 doc_id 的哈希作为 rowid）
                rowid = abs(hash(doc_id)) % (2**31 - 1) + 1
                cursor.execute("""
                INSERT OR REPLACE INTO vectors_vec (rowid, embedding)
                VALUES (?, ?)
                """, (rowid, embedding_bytes))

                total_chunks += 1

                # 统计文档类型
                doc_type = chunks[0].metadata.get('doc_type', 'unknown') if chunks else 'unknown'
                doc_type_stats[doc_type] = doc_type_stats.get(doc_type, 0) + 1

            success_count += 1

            if i % 10 == 0 or i == len(filtered_files):
                elapsed = time.time() - start_time
                speed = i / elapsed if elapsed > 0 else 0
                print(f" [{i}/{len(filtered_files)}] 处理 {file_path.name} - "
                      f"速度：{speed:.1f} 文件/秒 - "
                      f"累计块数：{total_chunks}")

        except Exception as e:
            error_count += 1
            print(f" ❌ 错误处理 {file_path}: {e}")

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time

    print()
    print("✅ 索引构建完成!")
    print(f" - 处理文件：{success_count}/{len(filtered_files)}")
    print(f" - 错误文件：{error_count}")
    print(f" - 总块数：{total_chunks}")
    print(f" - 耗时：{elapsed:.2f} 秒")
    print(f" - 平均速度：{len(filtered_files)/elapsed:.1f} 文件/秒")

    print(f"\n📊 文档类型分布:")
    for doc_type, count in sorted(doc_type_stats.items(), key=lambda x: x[1], reverse=True):
        print(f" {doc_type}: {count} 个文件")


if __name__ == "__main__":
    vault_path = os.path.expanduser("~/NanobotMemory")
    db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
    
    print(f"\n{'='*60}")
    print(f"📂 只处理 Vault: NanobotMemory ({vault_path})")
    print(f"{'='*60}\n")
    
    build_index(vault_path, db_path)
