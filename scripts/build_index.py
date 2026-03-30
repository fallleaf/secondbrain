#!/usr/bin/env python3
"""
SecondBrain 索引构建脚本

将 NanobotMemory 中的所有笔记向量化并存入 SQLite 数据库
使用 fastembed (轻量级，无需 GPU)
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import sqlite3
import sqlite_vec
from fastembed import TextEmbedding

from src.config.settings import load_config
from src.index.chunker import SemanticChunker  # 导入智能分块器


def extract_frontmatter(content: str) -> Dict[str, Any]:
    """
    从 Markdown 内容中提取 Frontmatter (YAML)
    
    Args:
        content: Markdown 文件内容
        
    Returns:
        Dict[str, Any]: Frontmatter 字典，若无则返回空字典
    """
    if not content.startswith('---'):
        return {}
    
    # 查找第一个 --- 和第二个 --- 之间的内容
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    
    frontmatter_str = match.group(1)
    
    # 简单解析 YAML (仅支持基本键值对)
    # 注意：这里使用简单的正则解析，不支持复杂 YAML 结构
    frontmatter = {}
    for line in frontmatter_str.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            frontmatter[key] = value
    
    return frontmatter


def get_doc_type(content: str) -> Optional[str]:
    """
    从内容中提取 doc_type
    
    Args:
        content: Markdown 文件内容
        
    Returns:
        Optional[str]: doc_type 值，若无则返回 None
    """
    frontmatter = extract_frontmatter(content)
    return frontmatter.get('doc_type')


# 初始化智能分块器（全局，避免重复初始化）
chunker = SemanticChunker(max_chars=800, overlap=100, min_chars=100)


def chunk_text(file_path: str, content: str) -> List[Dict[str, Any]]:
    """
    使用 SemanticChunker 进行智能分块

    Args:
        file_path: 文件路径（用于生成 doc_id）
        content: 原始文本内容

    Returns:
        List[Dict]: 分块信息列表，包含 content, chunk_id, start_line, end_line 等
    """
    # 使用 SemanticChunker 分块
    chunks = chunker.chunk_text(file_path, content)
    
    # 转换为字典格式，兼容原有逻辑
    result = []
    for chunk in chunks:
        result.append({
            "content": chunk.content,
            "chunk_id": chunk.chunk_id,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "metadata": chunk.metadata
        })

    return result


def build_index(vault_path: str, db_path: str, model_name: str = "BAAI/bge-small-zh-v1.5", append_mode: bool = False):
    """
    构建语义索引

    Args:
        vault_path: Vault 路径
        db_path: 数据库路径
        model_name: 嵌入模型名称
        append_mode: 是否追加模式（不清空旧数据）
    """
    print(f"🚀 开始构建语义索引...")
    print(f" - Vault: {vault_path}")
    print(f" - 数据库：{db_path}")
    print(f" - 模型：{model_name}")
    print(f" - 模式：{'追加' if append_mode else '完全重建'}")
    print()

    # 加载模型并获取实际维度
    print("📥 加载嵌入模型 (fastembed)...")
    model = TextEmbedding(model_name=model_name)

    # 测试获取实际维度
    test_embedding = list(model.embed(["test"]))[0]
    actual_dim = len(test_embedding)
    print(f"✅ 模型加载成功 (维度：{actual_dim})")
    print()

    # 初始化数据库
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

    # 创建表 (使用实际维度)
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS vectors (
        doc_id TEXT PRIMARY KEY,
        embedding F32_BLOB({actual_dim}),
        metadata TEXT
    )
    """)

    cursor.execute(f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS vectors_vec USING vec0(
        embedding float[{actual_dim}]
    )
    """)

    conn.commit()
    print(f"✅ 数据库初始化成功 (维度：{actual_dim})")
    print()

    # 遍历所有笔记
    vault_path = Path(vault_path)
    md_files = list(vault_path.rglob("*.md"))

    # 排除目录
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
            # 读取文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

        # 分块（使用 SemanticChunker）
            rel_path = str(file_path.relative_to(vault_path))
            chunk_infos = chunk_text(rel_path, content)

            if not chunk_infos:
                continue

        # 提取内容列表用于向量化
            chunk_contents = [info["content"] for info in chunk_infos]

        # 向量化 (batch)
            embeddings = list(model.embed(chunk_contents))
            embeddings = [np.array(e) for e in embeddings]

        # 存入数据库
            for j, (embedding, chunk_info) in enumerate(zip(embeddings, chunk_infos)):
                doc_id = chunk_info["chunk_id"]  # 使用 chunker 生成的 doc_id (file_path#chunk_index)
                embedding_bytes = sqlite_vec.serialize_float32(embedding.tolist())

            # 提取 doc_type（优先使用 chunk metadata 中的，如果没有则重新提取）
                doc_type = chunk_info["metadata"].get("doc_type")
                if not doc_type:
                    doc_type = get_doc_type(content)

            # 合并 metadata
                metadata_dict = chunk_info["metadata"].copy()
                metadata_dict["doc_type"] = doc_type
                metadata_dict["total_chunks"] = len(chunk_infos)
                metadata = json.dumps(metadata_dict)

                cursor.execute("""
                    INSERT OR REPLACE INTO vectors (doc_id, embedding, metadata)
                    VALUES (?, ?, ?)
                    """, (doc_id, embedding_bytes, metadata))

                # 同时插入到 vectors_vec 虚拟表（用于向量搜索）
                # 注意：sqlite-vec 的 vec0 表使用 rowid 作为主键，但插入时不应手动指定 rowid
                # 应该让数据库自动分配，或者使用 doc_id 关联
                    cursor.execute("""
                    INSERT INTO vectors_vec (embedding)
                    VALUES (?)
                    """, (embedding_bytes,))

                # 获取自动分配的 rowid
                    rowid = cursor.lastrowid
                    total_chunks += 1

                success_count += 1

            # 进度显示
                if i % 10 == 0 or i == len(filtered_files):
                    elapsed = time.time() - start_time
                    speed = i / elapsed if elapsed > 0 else 0
                    print(f" [{i}/{len(filtered_files)}] 处理 {file_path.name} - "
                          f"速度：{speed:.1f} 文件/秒 - "
                          f"累计块数：{total_chunks}")

        except Exception as e:
            error_count += 1
            print(f" ❌ 错误处理 {file_path}: {e}")
            import traceback
            traceback.print_exc()

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


if __name__ == "__main__":
    # 配置
    config = load_config()
    
    # 获取所有启用的 Vault
    enabled_vaults = [v for v in config.vaults if v.enabled]
    if not enabled_vaults:
        enabled_vaults = config.vaults[:1] if config.vaults else []
    
    db_path = config.index.semantic.db_path
    
    # 依次构建每个 Vault 的索引
    for idx, vault in enumerate(enabled_vaults):
        print(f"\n{'='*60}")
        print(f"📂 处理 Vault: {vault.name} ({vault.path})")
        print(f"{'='*60}\n")
        
        # 第一个 Vault 完全重建，后续 Vault 追加模式
        append_mode = (idx > 0)
        build_index(vault.path, db_path, append_mode=append_mode)
