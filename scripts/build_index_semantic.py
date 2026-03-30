#!/usr/bin/env python3
"""
SecondBrain 索引构建脚本（使用 SemanticChunker 智能分块）

将 NanobotMemory 中的所有笔记向量化并存入 SQLite 数据库
使用 fastembed (轻量级，无需 GPU) 和 SemanticChunker 智能分块
"""

from src.index.semantic_index import SemanticIndex
from src.index.chunker import SemanticChunker
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
from typing import List, Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_frontmatter(content: str) -> Dict[str, Any]:
    """从 Markdown 内容中提取 Frontmatter (YAML)"""
    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    yaml_content = parts[1].strip()
    frontmatter = {}

    for line in yaml_content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if value.startswith('[') and value.endswith(']'):
                # 简单解析列表
                value = [v.strip().strip('"\'') for v in value[1:-1].split(',')]
            frontmatter[key] = value

    return frontmatter


def get_doc_type(content: str) -> Optional[str]:
    """从内容中提取 doc_type"""
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
    chunks = chunker.chunk_text(file_path, content)

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
    print(f" - 模式：{'追加' if append_mode else '覆盖'}")
    print()

    # 加载模型并获取实际维度
    print("📥 加载嵌入模型 (fastembed)...")
    model = TextEmbedding(model_name=model_name)

    test_embedding = list(model.embed(["test"]))[0]
    actual_dim = len(test_embedding)
    print(f"✅ 模型加载成功 (维度：{actual_dim})")
    print()

    # 初始化 SemanticIndex 对象（用于批量插入）
    print("🗄️ 初始化数据库...")
    if os.path.exists(db_path) and not append_mode:
        os.remove(db_path)
        print(f" - 已删除旧数据库")
    elif os.path.exists(db_path) and append_mode:
        print(f" - 追加模式：保留现有数据")
    else:
        print(f" - 创建新数据库")

    semantic_index = SemanticIndex(db_path, dim=actual_dim)
    print("✅ 数据库初始化完成")
    print()

    # 查找所有笔记
    print("📂 扫描笔记文件...")
    vault_path = Path(vault_path)
    all_files = list(vault_path.rglob("*.md"))

    # 排除目录
    exclude_dirs = {".git", "node_modules", "__pycache__", ".obsidian", "assets", "attachments"}
    filtered_files = [
        f for f in all_files
        if not any(exclude_dir in str(f) for exclude_dir in exclude_dirs)
    ]

    print(f" 找到 {len(filtered_files)} 个文件")
    print()

    # 处理每个文件
    total_chunks = 0
    success_count = 0
    error_count = 0
    start_time = time.time()
    batch_items = []
    batch_size = 100  # 每 100 个 chunk 批量插入一次

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

            # 准备批量插入数据
            for j, (embedding, chunk_info) in enumerate(zip(embeddings, chunk_infos)):
                doc_id = chunk_info["chunk_id"]

                # 提取 doc_type
                doc_type = chunk_info["metadata"].get("doc_type")
                if not doc_type:
                    doc_type = get_doc_type(content)

                # 合并 metadata（不包含 content）
                metadata_dict = chunk_info["metadata"].copy()
                metadata_dict["doc_type"] = doc_type
                metadata_dict["total_chunks"] = len(chunk_infos)
                metadata = json.dumps(metadata_dict)

                # 准备 batch item: (doc_id, embedding, metadata, content, start_line, end_line)
                content_text = chunk_info.get("content", "")
                start_line = chunk_info.get("start_line", 0) or 0
                end_line = chunk_info.get("end_line", 0) or 0
                batch_items.append((doc_id, embedding.tolist(), metadata, content_text, start_line, end_line))

                total_chunks += 1

                # 达到批量大小，执行插入
                if len(batch_items) >= batch_size:
                    success, fail = semantic_index.add_embeddings_batch(batch_items)
                    success_count += success
                    error_count += fail
                    batch_items = []

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

    # 插入剩余的 batch
    if batch_items:
        success, fail = semantic_index.add_embeddings_batch(batch_items)
        success_count += success
        error_count += fail

    # 完成
    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print("✅ 索引构建完成！")
    print(f" - 成功：{success_count} 文件")
    print(f" - 错误：{error_count} 文件")
    print(f" - 总块数：{total_chunks}")
    print(f" - 耗时：{elapsed:.1f} 秒")
    print(f" - 平均速度：{len(filtered_files) / elapsed:.1f} 文件/秒")
    print("=" * 60)


if __name__ == "__main__":
    # 加载配置
    config = load_config()

    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="构建 SecondBrain 语义索引")
    parser.add_argument("--vault", "-v", help="指定 Vault 名称 (如 'personal' 或 'work')")
    parser.add_argument("--model", "-m", default="BAAI/bge-small-zh-v1.5", help="嵌入模型名称")
    parser.add_argument("--append", "-a", action="store_true", help="追加模式（不清空旧数据）")
    parser.add_argument("--all", action="store_true", help="构建所有启用的 Vault")

    args = parser.parse_args()

    # 获取所有启用的 Vault
    vaults_to_build = []

    if args.vault:
        # 指定单个 Vault
        for vault in config.vaults:
            if vault.name == args.vault and vault.enabled:
                vaults_to_build.append(vault)
                break
        if not vaults_to_build:
            print(f"❌ 未找到名为 '{args.vault}' 的启用 Vault")
            sys.exit(1)
    elif args.all:
        # 构建所有启用的 Vault
        vaults_to_build = [v for v in config.vaults if v.enabled]
    else:
        # 默认构建第一个启用的 Vault (向后兼容)
        for vault in config.vaults:
            if vault.enabled:
                vaults_to_build.append(vault)
                break

    if not vaults_to_build:
        print("❌ 没有启用的 Vault")
        sys.exit(1)

    # 依次构建每个 Vault 的索引
    for i, vault in enumerate(vaults_to_build, 1):
        print(f"\n{'=' * 60}")
        print(f"正在处理 Vault {i}/{len(vaults_to_build)}: {vault.name}")
        print(f"{'=' * 60}\n")

        # 确定数据库路径
        if hasattr(vault, 'index') and vault.index and hasattr(vault.index, 'semantic_db') and vault.index.semantic_db:
            db_path = os.path.expanduser(vault.index.semantic_db)
        else:
            # 使用默认路径 (向后兼容)
            db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")

        vault_path = os.path.expanduser(vault.path)

        # 检查 Vault 路径是否存在
        if not os.path.exists(vault_path):
            print(f"⚠️ Vault 路径不存在：{vault_path}，跳过")
            continue

        build_index(vault_path, db_path, args.model, args.append)

    print(f"\n{'=' * 60}")
    print(f"✅ 所有 Vault 索引构建完成！")
    print(f"{'=' * 60}")
