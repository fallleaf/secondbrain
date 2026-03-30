#!/usr/bin/env python3
"""
SecondBrain 自动文件变更检测与增量索引

功能：
1. 自动检测文件变化 (新增/修改/删除)
2. 只在有变化时执行向量化
3. 支持定时任务调用
4. 详细日志记录

运行环境：~/project/venv/nanobot
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
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Set, Tuple

# 设置虚拟环境路径
VENV_PATH = os.path.expanduser("~/project/venv/nanobot")
if os.path.exists(VENV_PATH):
    # 确保使用虚拟环境中的 Python
    venv_bin = os.path.join(VENV_PATH, "bin")
    if os.path.exists(venv_bin):
        os.environ["PATH"] = venv_bin + os.pathsep + os.environ["PATH"]

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            os.path.expanduser('~/.local/share/secondbrain/logs/auto_index.log'),
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_file_hash(file_path: Path) -> str:
    """计算文件 MD5 哈希"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def load_index_state(state_file: str) -> Dict[str, Dict[str, Any]]:
    """加载索引状态"""
    if not os.path.exists(state_file):
        return {}

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载状态文件失败：{e}")
        return {}


def save_index_state(state: Dict[str, Dict[str, Any]], state_file: str):
    """保存索引状态"""
    os.makedirs(os.path.dirname(state_file), exist_ok=True)

    # 只保存必要信息
    save_state = {
        path: {'hash': data['hash'], 'chunks': data.get('chunks', 0)}
        for path, data in state.items()
    }

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(save_state, f, ensure_ascii=False, indent=2)


def scan_vault(vault_path: str) -> Dict[str, Dict[str, Any]]:
    """扫描 Vault 获取所有文件状态"""
    vault_path = Path(vault_path)
    md_files = list(vault_path.rglob("*.md"))

    excluded = {'.obsidian', '.trash', '.git', '__pycache__'}
    filtered_files = [f for f in md_files if not any(excluded.intersection(f.parts))]

    current_state = {}

    for file_path in filtered_files:
        try:
            file_hash = get_file_hash(file_path)
            rel_path = str(file_path.relative_to(vault_path))

            current_state[rel_path] = {
                'hash': file_hash,
                'full_path': file_path
            }
        except Exception as e:
            logger.warning(f"扫描文件失败 {file_path}: {e}")

    return current_state


def detect_changes(
    index_state: Dict[str, Dict[str, Any]],
    current_state: Dict[str, Dict[str, Any]]
) -> Tuple[Set[str], Set[str], Set[str]]:
    """检测文件变化"""
    index_files = set(index_state.keys())
    current_files = set(current_state.keys())

    new_files = current_files - index_files
    deleted_files = index_files - current_files

    modified_files = set()
    for file_path in index_files & current_files:
        index_hash = index_state[file_path].get('hash')
        current_hash = current_state[file_path]['hash']

        if index_hash is None or index_hash != current_hash:
            modified_files.add(file_path)

    return new_files, modified_files, deleted_files


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list:
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


def auto_incremental_index(vault_path: str, db_path: str, state_file: str = None):
    """
    自动增量索引

    1. 检测文件变化
    2. 只在有变化时执行向量化
    3. 更新状态文件
    """
    logger.info("=" * 60)
    logger.info("🚀 开始自动文件变更检测与增量索引")
    logger.info(f"Vault: {vault_path}")
    logger.info(f"数据库：{db_path}")

    # 设置默认状态文件
    if state_file is None:
        state_file = os.path.join(os.path.dirname(db_path), 'index_state.json')

    # 加载模型
    logger.info("📥 加载嵌入模型...")
    try:
        model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
        test_embedding = list(model.embed(["test"]))[0]
        actual_dim = len(test_embedding)
        logger.info(f"✅ 模型加载成功 (维度：{actual_dim})")
    except Exception as e:
        logger.error(f"❌ 模型加载失败：{e}")
        return False

    # 检查数据库
    if not os.path.exists(db_path):
        logger.error(f"❌ 数据库不存在：{db_path}")
        logger.info("请先运行全量索引构建：python3 scripts/build_index.py")
        return False

    # 加载索引状态
    logger.info("📊 加载索引状态...")
    index_state = load_index_state(state_file)
    logger.info(f"   已索引文件：{len(index_state)}")

    # 扫描当前文件
    logger.info("🔍 扫描 Vault...")
    current_state = scan_vault(vault_path)
    logger.info(f"   当前文件：{len(current_state)}")

    # 检测变化
    logger.info("🔎 检测文件变化...")
    new_files, modified_files, deleted_files = detect_changes(index_state, current_state)

    logger.info(f"   新增文件：{len(new_files)}")
    logger.info(f"   修改文件：{len(modified_files)}")
    logger.info(f"   删除文件：{len(deleted_files)}")

    # 无变化时退出
    if not new_files and not modified_files and not deleted_files:
        logger.info("✅ 无文件变化，跳过向量化")
        return True

    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    cursor = conn.cursor()

    # 处理变更文件
    changed_files = new_files | modified_files
    total_chunks = 0
    success_count = 0
    error_count = 0

    start_time = time.time()
    logger.info(f"📝 开始处理 {len(changed_files)} 个变更文件...")

    for i, file_path in enumerate(changed_files, 1):
        try:
            full_path = current_state[file_path]['full_path']

            # 读取文件
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 分块
            chunks = chunk_text(content)
            if not chunks:
                continue

            # 向量化
            embeddings = list(model.embed(chunks))
            embeddings = [np.array(e) for e in embeddings]

            # 删除旧记录
            if file_path in index_state:
                # 需要从数据库获取 doc_ids
                cursor.execute(
                    "SELECT doc_id FROM vectors WHERE metadata LIKE ? OR metadata LIKE ?",
                    (f'"file_path": "{file_path}"%', f'"file_path": "{file_path.replace("\\", "\\\\")}"%')
                )
                old_doc_ids = [row[0] for row in cursor.fetchall()]
                for doc_id in old_doc_ids:
                    cursor.execute("DELETE FROM vectors WHERE doc_id = ?", (doc_id,))
                    cursor.execute("DELETE FROM vectors_vec WHERE rowid = ?", (doc_id,))

            # 插入新记录
            for j, embedding in enumerate(embeddings):
                doc_id = f"{file_path}#{j}"
                embedding_bytes = sqlite_vec.serialize_float32(embedding.tolist())
                metadata = json.dumps({
                    'file_path': file_path,
                    'chunk_index': j,
                    'total_chunks': len(embeddings)
                })

                cursor.execute(
                    "INSERT OR REPLACE INTO vectors (doc_id, embedding, metadata) VALUES (?, ?, ?)",
                    (doc_id, embedding_bytes, metadata)
                )
                total_chunks += 1

            success_count += 1

            # 进度日志
            if i % 10 == 0 or i == len(changed_files):
                elapsed = time.time() - start_time
                speed = i / elapsed if elapsed > 0 else 0
                logger.info(f"   [{i}/{len(changed_files)}] 处理 {file_path} - "
                            f"速度：{speed:.1f} 文件/秒 - 累计块数：{total_chunks}")

        except Exception as e:
            error_count += 1
            logger.error(f"❌ 错误处理 {file_path}: {e}")

    # 处理删除的文件
    if deleted_files:
        logger.info(f"🗑️ 处理 {len(deleted_files)} 个删除文件...")
        for file_path in deleted_files:
            try:
                if file_path in index_state:
                    cursor.execute(
                        "SELECT doc_id FROM vectors WHERE metadata LIKE ?",
                        (f'"file_path": "{file_path}"%',)
                    )
                    doc_ids = [row[0] for row in cursor.fetchall()]
                    for doc_id in doc_ids:
                        cursor.execute("DELETE FROM vectors WHERE doc_id = ?", (doc_id,))
                        cursor.execute("DELETE FROM vectors_vec WHERE rowid = ?", (doc_id,))
            except Exception as e:
                logger.error(f"❌ 错误删除 {file_path}: {e}")

    conn.commit()
    conn.close()

    # 更新状态
    for file_path in current_state:
        if file_path not in index_state:
            index_state[file_path] = {'hash': None, 'chunks': 0}
        index_state[file_path]['hash'] = current_state[file_path]['hash']

    save_index_state(index_state, state_file)

    elapsed = time.time() - start_time

    # 最终日志
    logger.info("=" * 60)
    logger.info("✅ 自动增量索引完成")
    logger.info(f"   新增文件：{len(new_files)}")
    logger.info(f"   修改文件：{len(modified_files)}")
    logger.info(f"   删除文件：{len(deleted_files)}")
    logger.info(f"   处理文件：{success_count}/{len(changed_files)}")
    logger.info(f"   错误文件：{error_count}")
    logger.info(f"   新增/更新块数：{total_chunks}")
    logger.info(f"   耗时：{elapsed:.2f} 秒")
    logger.info("=" * 60)

    return error_count == 0


def main():
    """主函数"""
    try:
        config = load_config()
        vault_path = config.vaults[0].path
        db_path = config.index.semantic.db_path

        success = auto_incremental_index(vault_path, db_path)

        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"❌ 程序执行失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
