#!/usr/bin/env python3
"""
SecondBrain 索引构建脚本 - 修复版
添加 vectors_vec 虚拟表插入逻辑
"""

from src.config.settings import load_config
from fastembed import TextEmbedding
import sqlite_vec
import sqlite3
import numpy as np
import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
    """文本分块"""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(para) > chunk_size:
                words = para.split()
                current_word_chunk = ""
                for word in words:
                    if len(current_word_chunk) + len(word) < chunk_size - chunk_overlap:
                        current_word_chunk += word + " "
                    else:
                        if current_word_chunk:
                            chunks.append(current_word_chunk.strip())
                        current_word_chunk = word + " "
                current_chunk = current_word_chunk
            else:
                current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def build_index(vault_path: str, db_path: str, model_name: str = "BAAI/bge-small-zh-v1.5", append_mode: bool = False):
    """构建语义索引"""
    print(f"🚀 开始构建语义索引...")
    print(f" - Vault: {vault_path}")
    print(f" - 数据库：{db_path}")
    print(f" - 模型：{model_name}")
    print(f" - 模式：{'追加' if append_mode else '完全重建'}")
    print()

    model = TextEmbedding(model_name=model_name)
    test_embedding = list(model.embed(["test"]))[0]
    actual_dim = len(test_embedding)
    print(f"✅ 模型加载成功 (维度：{actual_dim})")
    print()

    print("🗄️ 初始化数据库...")
    if os.path.exists(db_path) and not append_mode:
        os.remove(db_path)
        print(f" - 已删除旧数据库")
    elif os.path.exists(db_path) and append_mode:
        print(f" - 追加模式：保留现有数据")
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

    for i, file_path in enumerate(filtered_files, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            chunks = chunk_text(content, chunk_size=800, chunk_overlap=150)

            if not chunks:
                continue

            embeddings = list(model.embed(chunks))
            embeddings = [np.array(e) for e in embeddings]

            rel_path = str(file_path.relative_to(vault_path))

            for j, embedding in enumerate(embeddings):
                doc_id = f"{rel_path}#{j}"
                embedding_bytes = sqlite_vec.serialize_float32(embedding.tolist())
                metadata = json.dumps({
                    'file_path': rel_path,
                    'chunk_index': j,
                    'total_chunks': len(embeddings)
                })

                cursor.execute("""
                INSERT OR REPLACE INTO vectors (doc_id, embedding, metadata)
                VALUES (?, ?, ?)
                """, (doc_id, embedding_bytes, metadata))

                # 插入到 vectors_vec 虚拟表
                cursor.execute("""
                INSERT OR REPLACE INTO vectors_vec (rowid, embedding)
                VALUES (?, ?)
                """, (total_chunks + 1, embedding_bytes))

                total_chunks += 1

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
    print(f" - 平均速度：{len(filtered_files) / elapsed:.1f} 文件/秒")


if __name__ == "__main__":
    config = load_config()
    enabled_vaults = [v for v in config.vaults if v.enabled]
    if not enabled_vaults:
        enabled_vaults = config.vaults[:1] if config.vaults else []

    db_path = config.index.semantic.db_path

    for idx, vault in enumerate(enabled_vaults):
        print(f"\n{'=' * 60}")
        print(f"📂 处理 Vault: {vault.name} ({vault.path})")
        print(f"{'=' * 60}\n")

        append_mode = (idx > 0)
        build_index(vault.path, db_path, append_mode=append_mode)
