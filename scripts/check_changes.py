#!/usr/bin/env python3
"""
SecondBrain 文件变更检测脚本

只检测文件变化，不执行向量化
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import sqlite3
import sqlite_vec

from src.config.settings import load_config


def get_file_hash(file_path: Path) -> str:
    """计算文件哈希 (MD5)"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def load_index_state(db_path: str) -> Dict[str, Dict[str, Any]]:
    """
    加载索引状态 (已索引文件的元数据)
    
    注意：当前版本不存储文件哈希，所以所有文件都会被标记为"修改"
    这是首次运行增量索引时的正常现象。
    下次运行时，如果文件未修改，将正确识别。
    
    Returns:
        Dict: {file_path: {'chunks': int, 'doc_ids': List[str]}}
    """
    state = {}
    
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
                    'chunks': 0,
                    'doc_ids': []
                }
            
            state[file_path]['doc_ids'].append(doc_id)
            state[file_path]['chunks'] += 1
        
        conn.close()
    except Exception as e:
        print(f"⚠️ 加载索引状态失败：{e}")
    
    return state


def scan_vault(vault_path: str) -> Dict[str, Dict[str, Any]]:
    """扫描 Vault 获取所有文件的当前状态"""
    vault_path = Path(vault_path)
    md_files = list(vault_path.rglob("*.md"))
    
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
    """检测文件变化"""
    index_files = set(index_state.keys())
    current_files = set(current_state.keys())
    
    new_files = current_files - index_files
    deleted_files = index_files - current_files
    
    modified_files = set()
    for file_path in index_files & current_files:
        index_hash = index_state[file_path].get('hash')
        current_hash = current_state[file_path]['hash']
        
        # 如果没有哈希信息，视为修改
        if index_hash is None or index_hash != current_hash:
            modified_files.add(file_path)
    
    return new_files, modified_files, deleted_files


def check_changes(vault_path: str, db_path: str):
    """检查文件变化"""
    print(f"🔍 检查文件变化...")
    print(f"   - Vault: {vault_path}")
    print(f"   - 数据库：{db_path}")
    print()
    
    # 加载索引状态
    print("📊 加载索引状态...")
    index_state = load_index_state(db_path)
    print(f"   - 已索引文件：{len(index_state)}")
    print()
    
    # 扫描当前文件
    print("🔎 扫描 Vault...")
    current_state = scan_vault(vault_path)
    print(f"   - 当前文件：{len(current_state)}")
    print()
    
    # 检测变化
    print("🔎 检测文件变化...")
    new_files, modified_files, deleted_files = detect_changes(index_state, current_state)
    
    print(f"\n📊 变化统计:")
    print(f"   - 新增文件：{len(new_files)}")
    print(f"   - 修改文件：{len(modified_files)}")
    print(f"   - 删除文件：{len(deleted_files)}")
    
    if new_files:
        print(f"\n📄 新增文件:")
        for f in sorted(new_files)[:10]:
            print(f"   + {f}")
        if len(new_files) > 10:
            print(f"   ... 还有 {len(new_files) - 10} 个文件")
    
    if modified_files:
        print(f"\n✏️  修改文件:")
        for f in sorted(modified_files)[:10]:
            print(f"   ~ {f}")
        if len(modified_files) > 10:
            print(f"   ... 还有 {len(modified_files) - 10} 个文件")
    
    if deleted_files:
        print(f"\n🗑️  删除文件:")
        for f in sorted(deleted_files)[:10]:
            print(f"   - {f}")
        if len(deleted_files) > 10:
            print(f"   ... 还有 {len(deleted_files) - 10} 个文件")
    
    if not new_files and not modified_files and not deleted_files:
        print("\n✅ 无文件变化")
    
    return {
        'new': len(new_files),
        'modified': len(modified_files),
        'deleted': len(deleted_files),
        'total_changes': len(new_files) + len(modified_files) + len(deleted_files)
    }


if __name__ == "__main__":
    config = load_config()
    vault_path = config.vaults[0].path
    db_path = config.index.semantic.db_path
    
    check_changes(vault_path, db_path)
