#!/usr/bin/env python3
"""
SecondBrain 增量索引构建脚本

检测文件变化并只向量化变更的文件
支持：新增、修改、删除
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import sqlite3
import sqlite_vec
from fastembed import TextEmbedding

from src.config.settings import load_config


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


def get_file_hash(file_path: Path) -> str:
    """计算文件哈希 (MD5)"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def load_index_state(db_path: str, state_file: str) -> Dict[str, Dict[str, Any]]:
    """
    加载索引状态 (已索引文件的哈希和元数据)
    
    Args:
        db_path: 数据库路径
        state_file: 状态文件路径 (存储文件哈希)
    
    Returns:
        Dict: {file_path: {'hash': str, 'chunks': int, 'doc_ids': List[str]}}
    """
    state = {}
    
    # 从状态文件加载哈希
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except Exception as e:
            print(f"⚠️ 加载状态文件失败：{e}")
            state = {}
    
    # 从数据库加载 doc_ids
    if not os.path.exists(db_path):
        return state
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT doc_id, metadata FROM vectors")
        for doc_id, metadata_json in cursor.fetchall():
            metadata = json.loads(metadata_json)
            file_path = metadata['file_path']
            
            if file_path not in state:
                state[file_path] = {
                    'hash': None,
                    'chunks': 0,
                    'doc_ids': []
                }
            
            state[file_path]['doc_ids'].append(doc_id)
            state[file_path]['chunks'] += 1
        
        conn.close()
    except Exception as e:
        print(f"⚠️ 加载数据库状态失败：{e}")
    
    return state


def save_index_state(state: Dict[str, Dict[str, Any]], state_file: str):
    """保存索引状态到文件"""
    # 只保存 hash 和 chunks，不保存 doc_ids (节省空间)
    save_state = {
        path: {'hash': data['hash'], 'chunks': data['chunks']}
        for path, data in state.items()
    }
    
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(save_state, f, ensure_ascii=False, indent=2)


def scan_vault(vault_path: str) -> Dict[str, Dict[str, Any]]:
    """
    扫描 Vault 获取所有文件的当前状态
    
    Returns:
        Dict: {file_path: {'hash': str, 'mtime': float}}
    """
    vault_path = Path(vault_path)
    md_files = list(vault_path.rglob("*.md"))
    
    # 排除目录
    excluded = {'.obsidian', '.trash', '.git', '__pycache__'}
    filtered_files = [f for f in md_files if not any(excluded.intersection(f.parts))]
    
    current_state = {}
    
    for file_path in filtered_files:
        try:
            mtime = file_path.stat().st_mtime
            file_hash = get_file_hash(file_path)
            rel_path = str(file_path.relative_to(vault_path))
            
            current_state[rel_path] = {
                'hash': file_hash,
                'mtime': mtime,
                'full_path': file_path
            }
        except Exception as e:
            print(f"⚠️ 扫描文件失败 {file_path}: {e}")
    
    return current_state


def detect_changes(
    index_state: Dict[str, Dict[str, Any]],
    current_state: Dict[str, Dict[str, Any]]
) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    检测文件变化
    
    Returns:
        Tuple: (新增文件，修改文件，删除文件)
    """
    index_files = set(index_state.keys())
    current_files = set(current_state.keys())
    
    # 新增文件
    new_files = current_files - index_files
    
    # 删除文件
    deleted_files = index_files - current_files
    
    # 修改文件 (哈希不同)
    modified_files = set()
    for file_path in index_files & current_files:
        if index_state[file_path]['hash'] != current_state[file_path]['hash']:
            modified_files.add(file_path)
    
    return new_files, modified_files, deleted_files


def build_incremental_index(
    vault_path: str,
    db_path: str,
    model_name: str = "BAAI/bge-small-zh-v1.5",
    state_file: str = None
):
    """
    构建增量索引
    
    Args:
        vault_path: Vault 路径
        db_path: 数据库路径
        model_name: 嵌入模型名称
        state_file: 状态文件路径 (存储文件哈希)
    """
    print(f"🚀 开始增量索引构建...")
    print(f"   - Vault: {vault_path}")
    print(f"   - 数据库：{db_path}")
    if state_file:
        print(f"   - 状态文件：{state_file}")
    print()
    
    # 设置默认状态文件
    if state_file is None:
        state_file = os.path.join(os.path.dirname(db_path), 'index_state.json')
    
    # 加载模型并获取实际维度
    print("📥 加载嵌入模型...")
    model = TextEmbedding(model_name=model_name)
    
    # 测试获取实际维度
    test_embedding = list(model.embed(["test"]))[0]
    actual_dim = len(test_embedding)
    print(f"✅ 模型加载成功 (维度：{actual_dim})")
    print()
    
    # 初始化数据库连接
    print("🗄️ 连接数据库...")
    if not os.path.exists(db_path):
        print(f"❌ 数据库不存在，请先运行全量索引构建")
        return
    
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    cursor = conn.cursor()
    print(f"✅ 数据库连接成功")
    print()
    
    # 加载索引状态
    print("📊 加载索引状态...")
    index_state = load_index_state(db_path, state_file)
    print(f"   - 已索引文件：{len(index_state)}")
    print()
    
    # 扫描当前文件
    print("🔍 扫描 Vault...")
    current_state = scan_vault(vault_path)
    print(f"   - 当前文件：{len(current_state)}")
    print()
    
    # 检测变化
    print("🔎 检测文件变化...")
    new_files, modified_files, deleted_files = detect_changes(index_state, current_state)
    
    print(f"   - 新增文件：{len(new_files)}")
    print(f"   - 修改文件：{len(modified_files)}")
    print(f"   - 删除文件：{len(deleted_files)}")
    print()
    
    if not new_files and not modified_files and not deleted_files:
        print("✅ 无文件变化，无需更新索引")
        conn.close()
        return
    
    # 处理新增和修改的文件
    changed_files = new_files | modified_files
    total_chunks = 0
    success_count = 0
    error_count = 0
    
    start_time = time.time()
    
    print(f"📝 处理 {len(changed_files)} 个变更文件...")
    
    for i, file_path in enumerate(changed_files, 1):
        try:
            full_path = current_state[file_path]['full_path']
            
            # 读取文件
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分块
            chunks = chunk_text(content, chunk_size=800, chunk_overlap=150)
            
            if not chunks:
                continue
            
            # 向量化
            embeddings = list(model.embed(chunks))
            embeddings = [np.array(e) for e in embeddings]
            
            # 删除旧的向量记录 (如果是修改的文件)
            if file_path in index_state and index_state[file_path].get('doc_ids'):
                for doc_id in index_state[file_path]['doc_ids']:
                    cursor.execute("DELETE FROM vectors WHERE doc_id = ?", (doc_id,))
                    cursor.execute("DELETE FROM vectors_vec WHERE rowid = ?", (doc_id,))
            
            # 插入新的向量记录
            for j, embedding in enumerate(embeddings):
                doc_id = f"{file_path}#{j}"
                embedding_bytes = sqlite_vec.serialize_float32(embedding.tolist())
                metadata = json.dumps({
                    'file_path': file_path,
                    'chunk_index': j,
                    'total_chunks': len(embeddings)
                })
                
                cursor.execute("""
                    INSERT OR REPLACE INTO vectors (doc_id, embedding, metadata)
                    VALUES (?, ?, ?)
                """, (doc_id, embedding_bytes, metadata))
                
                total_chunks += 1
            
            success_count += 1
            
            # 进度显示
            if i % 5 == 0 or i == len(changed_files):
                elapsed = time.time() - start_time
                speed = i / elapsed if elapsed > 0 else 0
                print(f"   [{i}/{len(changed_files)}] 处理 {file_path} - "
                      f"速度：{speed:.1f} 文件/秒 - "
                      f"累计块数：{total_chunks}")
        
        except Exception as e:
            error_count += 1
            print(f"   ❌ 错误处理 {file_path}: {e}")
            import traceback
            traceback.print_exc()
    
    # 处理删除的文件
    if deleted_files:
        print(f"\n🗑️ 处理 {len(deleted_files)} 个删除文件...")
        for i, file_path in enumerate(deleted_files, 1):
            try:
                if file_path in index_state and index_state[file_path].get('doc_ids'):
                    for doc_id in index_state[file_path]['doc_ids']:
                        cursor.execute("DELETE FROM vectors WHERE doc_id = ?", (doc_id,))
                        cursor.execute("DELETE FROM vectors_vec WHERE rowid = ?", (doc_id,))
            except Exception as e:
                print(f"   ❌ 错误删除 {file_path}: {e}")
    
    conn.commit()
    conn.close()
    
    # 保存状态
    print("\n💾 保存索引状态...")
    for file_path in current_state:
        if file_path not in index_state:
            index_state[file_path] = {'hash': None, 'chunks': 0, 'doc_ids': []}
        index_state[file_path]['hash'] = current_state[file_path]['hash']
    
    save_index_state(index_state, state_file)
    print(f"✅ 状态已保存到 {state_file}")
    
    elapsed = time.time() - start_time
    
    print()
    print("✅ 增量索引构建完成!")
    print(f"   - 新增文件：{len(new_files)}")
    print(f"   - 修改文件：{len(modified_files)}")
    print(f"   - 删除文件：{len(deleted_files)}")
    print(f"   - 处理文件：{success_count}/{len(changed_files)}")
    print(f"   - 错误文件：{error_count}")
    print(f"   - 新增/更新块数：{total_chunks}")
    print(f"   - 耗时：{elapsed:.2f} 秒")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='SecondBrain 增量索引构建')
    parser.add_argument('--check-only', action='store_true', help='只检查变化，不执行向量化')
    parser.add_argument('--state-file', type=str, help='状态文件路径')
    args = parser.parse_args()
    
    if args.check_only:
        # 只检查变化
        from scripts.check_changes import check_changes
        config = load_config()
        check_changes(config.vaults[0].path, config.index.semantic.db_path)
    else:
        # 执行增量索引
        config = load_config()
        vault_path = config.vaults[0].path
        db_path = config.index.semantic.db_path
        state_file = args.state_file
        
        build_incremental_index(vault_path, db_path, state_file=state_file)
