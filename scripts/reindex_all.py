#!/usr/bin/env python3
"""
全量资料库重新索引脚本
使用 AdaptiveChunker 处理 NanobotMemory 和 Obsidian 两个 Vault
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.adaptive_chunker import AdaptiveChunker
from src.config.settings import load_config
from fastembed import TextEmbedding
import sqlite_vec
import sqlite3
import numpy as np
import json
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime

class ReindexReporter:
    """索引构建报告器"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.start_time = None
        self.end_time = None
        self.stats = {
            'total_files': 0,
            'success_files': 0,
            'error_files': 0,
            'total_chunks': 0,
            'doc_type_distribution': {},
            'errors': [],
            'vault_stats': {}
        }
        
    def start(self):
        self.start_time = time.time()
        self._log("=" * 70)
        self._log("全量资料库重新索引任务开始")
        self._log(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log("=" * 70)
        
    def end(self):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        self._log("=" * 70)
        self._log("索引构建完成")
        self._log(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"总耗时：{elapsed:.2f} 秒 ({elapsed/60:.2f} 分钟)")
        self._log("=" * 70)
        
    def _log(self, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
            
    def record_vault_start(self, vault_name: str, vault_path: str):
        self._log(f"\n📂 开始处理 Vault: {vault_name}")
        self._log(f"   路径：{vault_path}")
        self.stats['vault_stats'][vault_name] = {
            'files': 0,
            'chunks': 0,
            'errors': 0
        }
        
    def record_vault_end(self, vault_name: str):
        stats = self.stats['vault_stats'][vault_name]
        self._log(f"   ✅ Vault {vault_name} 完成: {stats['files']} 文件，{stats['chunks']} 块")
        
    def record_file_processed(self, vault_name: str, file_path: str, chunks_count: int, doc_type: str):
        self.stats['vault_stats'][vault_name]['files'] += 1
        self.stats['vault_stats'][vault_name]['chunks'] += chunks_count
        self.stats['success_files'] += 1
        self.stats['total_chunks'] += chunks_count
        
        # 文档类型统计
        self.stats['doc_type_distribution'][doc_type] = self.stats['doc_type_distribution'].get(doc_type, 0) + 1
        
        # 进度显示
        if self.stats['success_files'] % 50 == 0 or self.stats['success_files'] < 10:
            self._log(f"   ✓ 已处理 {self.stats['success_files']} 文件，累计 {self.stats['total_chunks']} 块")
            
    def record_file_error(self, vault_name: str, file_path: str, error: str):
        self.stats['vault_stats'][vault_name]['files'] += 1
        self.stats['vault_stats'][vault_name]['errors'] += 1
        self.stats['error_files'] += 1
        error_info = {'file': file_path, 'error': str(error)}
        self.stats['errors'].append(error_info)
        self._log(f"   ❌ 错误: {file_path} - {error}")
        
    def save_report(self, report_path: str):
        """保存完整报告"""
        elapsed = (self.end_time - self.start_time) if self.end_time else 0
        
        report = {
            'summary': {
                'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
                'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
                'duration_seconds': round(elapsed, 2),
                'total_files': self.stats['total_files'],
                'success_files': self.stats['success_files'],
                'error_files': self.stats['error_files'],
                'total_chunks': self.stats['total_chunks'],
                'avg_chunks_per_file': round(self.stats['total_chunks'] / max(self.stats['success_files'], 1), 2)
            },
            'doc_type_distribution': self.stats['doc_type_distribution'],
            'vault_stats': self.stats['vault_stats'],
            'errors': self.stats['errors'][:50]  # 只保留前 50 个错误
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        self._log(f"\n📄 报告已保存到：{report_path}")
        return report


def build_vault_index(vault_path: str, db_path: str, model_name: str, reporter: ReindexReporter, vault_name: str) -> Tuple[int, int]:
    """
    构建单个 Vault 的语义索引
    
    Returns:
        Tuple[int, int]: (成功文件数，错误文件数)
    """
    reporter.record_vault_start(vault_name, vault_path)
    
    # 加载模型
    reporter._log("   📥 加载嵌入模型...")
    model = TextEmbedding(model_name=model_name)
    test_embedding = list(model.embed(["test"]))[0]
    actual_dim = len(test_embedding)
    reporter._log(f"   ✅ 模型加载成功 (维度：{actual_dim})")
    
    # 初始化数据库
    reporter._log("   🗄️ 初始化数据库...")
    if os.path.exists(db_path):
        os.remove(db_path)
        reporter._log(f"   - 已删除旧数据库")
    
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
    reporter._log(f"   ✅ 数据库初始化成功 (路径：{db_path})")
    
    # 初始化 AdaptiveChunker
    chunker = AdaptiveChunker()
    
    # 扫描文件
    vault_path = Path(vault_path)
    md_files = list(vault_path.rglob("*.md"))
    excluded = {'.obsidian', '.trash', '.git', '__pycache__', '.stfolder', '.secondbrain'}
    filtered_files = [f for f in md_files if not any(excluded.intersection(f.parts))]
    
    reporter.stats['total_files'] += len(filtered_files)
    reporter._log(f"   📄 发现 {len(filtered_files)} 个笔记文件")
    
    success_count = 0
    error_count = 0
    start_time = time.time()
    
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
                
                # 合并元数据
                metadata = chunk.metadata.copy()
                metadata.update({
                    'file_path': rel_path,
                    'chunk_index': j,
                    'total_chunks': len(chunks),
                    'embedding_dim': actual_dim
                })
                metadata_json = json.dumps(metadata, ensure_ascii=False)
                
                cursor.execute("""
                INSERT OR REPLACE INTO vectors (doc_id, embedding, metadata)
                VALUES (?, ?, ?)
                """, (doc_id, embedding_bytes, metadata_json))
                
                # 插入到虚拟表
                rowid = abs(hash(doc_id)) % (2**31 - 1) + 1
                cursor.execute("""
                INSERT OR REPLACE INTO vectors_vec (rowid, embedding)
                VALUES (?, ?)
                """, (rowid, embedding_bytes))
            
            # 记录成功
            doc_type = chunks[0].metadata.get('doc_type', 'unknown') if chunks else 'unknown'
            reporter.record_file_processed(vault_name, str(file_path), len(chunks), doc_type)
            success_count += 1
            
            # 定期提交
            if i % 50 == 0:
                conn.commit()
                
            # 进度显示
            if i % 100 == 0 or i == len(filtered_files):
                elapsed = time.time() - start_time
                speed = i / elapsed if elapsed > 0 else 0
                reporter._log(f"   [{i}/{len(filtered_files)}] 速度：{speed:.1f} 文件/秒")
                
        except Exception as e:
            error_count += 1
            reporter.record_file_error(vault_name, str(file_path), str(e))
    
    # 提交剩余数据
    conn.commit()
    conn.close()
    
    elapsed = time.time() - start_time
    reporter.record_vault_end(vault_name)
    reporter._log(f"   耗时：{elapsed:.2f} 秒，平均：{len(filtered_files) / elapsed:.1f} 文件/秒")
    
    return success_count, error_count


def verify_index(db_path: str, reporter: ReindexReporter) -> Dict[str, Any]:
    """验证索引完整性"""
    reporter._log(f"\n🔍 验证索引完整性: {db_path}")
    
    if not os.path.exists(db_path):
        return {'valid': False, 'error': '数据库文件不存在'}
    
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    cursor = conn.cursor()
    
    result = {'valid': True, 'db_path': db_path}
    
    # 检查向量表
    cursor.execute("SELECT COUNT(*) FROM vectors")
    vector_count = cursor.fetchone()[0]
    result['vector_count'] = vector_count
    reporter._log(f"   ✓ 向量记录数：{vector_count}")
    
    # 检查元数据完整性
    cursor.execute("SELECT COUNT(*) FROM vectors WHERE metadata IS NULL OR metadata = ''")
    null_metadata = cursor.fetchone()[0]
    result['null_metadata_count'] = null_metadata
    if null_metadata > 0:
        reporter._log(f"   ⚠️ 警告：{null_metadata} 条记录缺少元数据")
    else:
        reporter._log(f"   ✓ 元数据完整性：100%")
    
    # 检查维度一致性
    cursor.execute("SELECT embedding FROM vectors LIMIT 1")
    row = cursor.fetchone()
    if row:
        embedding = row[0]
        dim = len(np.frombuffer(embedding, dtype=np.float32))
        result['embedding_dim'] = dim
        reporter._log(f"   ✓ 嵌入维度：{dim}")
    
    # 检查 doc_type 分布
    cursor.execute("""
        SELECT json_extract(metadata, '$.doc_type') as doc_type, COUNT(*) as count
        FROM vectors
        GROUP BY doc_type
        ORDER BY count DESC
    """)
    doc_type_dist = {row[0]: row[1] for row in cursor.fetchall()}
    result['doc_type_distribution'] = doc_type_dist
    reporter._log(f"   ✓ 文档类型分布：{len(doc_type_dist)} 种类型")
    
    conn.close()
    return result


def test_search(db_path: str, model_name: str, reporter: ReindexReporter, queries: List[str]) -> List[Dict[str, Any]]:
    """测试语义搜索功能"""
    reporter._log(f"\n🔎 测试语义搜索功能")
    
    if not os.path.exists(db_path):
        return [{'query': q, 'error': '数据库不存在'} for q in queries]
    
    model = TextEmbedding(model_name=model_name)
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    cursor = conn.cursor()
    
    results = []
    
    for query in queries:
        reporter._log(f"   查询：'{query}'")
        try:
            # 生成查询向量
            query_embedding = list(model.embed([query]))[0]
            query_embedding_bytes = sqlite_vec.serialize_float32(query_embedding.tolist())
            
            # 执行相似度搜索
            cursor.execute(f"""
                SELECT doc_id, metadata, distance
                FROM vectors_vec
                JOIN vectors ON vectors_vec.rowid = vectors.rowid
                WHERE embedding MATCH ? AND k = 5
                ORDER BY distance
            """, (query_embedding_bytes,))
            
            matches = cursor.fetchall()
            
            if matches:
                result_info = {
                    'query': query,
                    'success': True,
                    'match_count': len(matches),
                    'top_results': []
                }
                for i, match in enumerate(matches[:3]):
                    doc_id, metadata, distance = match
                    try:
                        meta = json.loads(metadata)
                        result_info['top_results'].append({
                            'doc_id': doc_id,
                            'doc_type': meta.get('doc_type', 'unknown'),
                            'file_path': meta.get('file_path', 'unknown'),
                            'distance': round(distance, 6)
                        })
                    except:
                        result_info['top_results'].append({
                            'doc_id': doc_id,
                            'distance': round(distance, 6)
                        })
                results.append(result_info)
                reporter._log(f"      ✓ 找到 {len(matches)} 个结果")
            else:
                results.append({'query': query, 'success': True, 'match_count': 0})
                reporter._log(f"      ⚠️ 未找到结果")
                
        except Exception as e:
            results.append({'query': query, 'error': str(e)})
            reporter._log(f"      ❌ 错误：{e}")
    
    conn.close()
    return results


def main():
    """主函数"""
    # 设置日志文件
    log_dir = Path.home() / ".local" / "share" / "secondbrain" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f"reindex_{timestamp}.log"
    report_file = log_dir / f"reindex_report_{timestamp}.json"
    
    # 初始化报告器
    reporter = ReindexReporter(str(log_file))
    reporter.start()
    
    try:
        # 加载配置
        reporter._log("📋 加载配置文件...")
        config = load_config()
        model_name = config.index.semantic.model
        reporter._log(f"   模型：{model_name}")
        
        # 获取所有启用的 Vault
        vaults = [v for v in config.vaults if v.enabled]
        if not vaults:
            reporter._log("❌ 没有启用的 Vault")
            return
        
        reporter._log(f"   发现 {len(vaults)} 个启用的 Vault")
        
        # 依次处理每个 Vault
        for vault in vaults:
            # 确定数据库路径
            if hasattr(vault, 'index') and vault.index and vault.index.semantic_db:
                db_path = os.path.expanduser(vault.index.semantic_db)
            else:
                db_path = config.index.semantic.db_path
            
            # 确保目录存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # 构建索引
            success, errors = build_vault_index(
                vault.path, db_path, model_name, reporter, vault.name
            )
        
        # 验证所有索引
        reporter._log("\n" + "=" * 70)
        reporter._log("🔍 索引验证阶段")
        reporter._log("=" * 70)
        
        verification_results = {}
        for vault in vaults:
            if hasattr(vault, 'index') and vault.index and vault.index.semantic_db:
                db_path = os.path.expanduser(vault.index.semantic_db)
            else:
                db_path = config.index.semantic.db_path
            
            if os.path.exists(db_path):
                verification_results[vault.name] = verify_index(db_path, reporter)
        
        # 测试搜索功能
        reporter._log("\n" + "=" * 70)
        reporter._log("🧪 搜索测试阶段")
        reporter._log("=" * 70)
        
        test_queries = ["极简网络", "nanobot 配置", "宽带接入", "光交规划"]
        search_results = {}
        
        for vault in vaults:
            if hasattr(vault, 'index') and vault.index and vault.index.semantic_db:
                db_path = os.path.expanduser(vault.index.semantic_db)
            else:
                db_path = config.index.semantic.db_path
            
            if os.path.exists(db_path):
                search_results[vault.name] = test_search(db_path, model_name, reporter, test_queries)
        
        # 保存报告
        reporter.end()
        report = reporter.save_report(str(report_file))
        
        # 打印摘要
        print("\n" + "=" * 70)
        print("📊 重新索引任务摘要")
        print("=" * 70)
        print(f"总文件数：{report['summary']['total_files']}")
        print(f"成功处理：{report['summary']['success_files']}")
        print(f"错误数量：{report['summary']['error_files']}")
        print(f"总块数：{report['summary']['total_chunks']}")
        print(f"平均每文件块数：{report['summary']['avg_chunks_per_file']}")
        print(f"总耗时：{report['summary']['duration_seconds']} 秒")
        print("\n文档类型分布:")
        for doc_type, count in sorted(report['doc_type_distribution'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {doc_type}: {count}")
        print("\n日志文件:", log_file)
        print("报告文件:", report_file)
        print("=" * 70)
        
    except Exception as e:
        reporter._log(f"❌ 任务失败：{e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
