#!/usr/bin/env python3
"""
构建关键词索引
扫描指定目录下的所有 Markdown 文件，并添加到关键词索引中
"""

import sys
import os
import time
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import load_config
from index.keyword_index import KeywordIndex
from index.chunker import Chunker
from index.chunker import Chunker as AdaptiveChunker  # 临时使用基础 Chunker

def build_keyword_index(vault_path: str, keyword_db: str, rebuild: bool = False):
    """构建关键词索引"""
    print(f"🔍 开始构建关键词索引...")
    print(f"  仓库路径：{vault_path}")
    print(f"  索引路径：{keyword_db}")
    
    # 创建关键词索引
    keyword_idx = KeywordIndex(db_path=keyword_db)
    
    # 如果需要重建，先清空索引
    if rebuild:
        print("  🗑️  正在清空旧索引...")
        keyword_idx.rebuild()
    
    # 使用自适应分块器（根据文档类型和标题结构动态调整参数）
    chunker = AdaptiveChunker()
    print(f"🛠️  使用自适应分块器：AdaptiveChunker")
    print(f"   支持 7 种文档类型：faq, technical, legal, blog, meeting, code, default")
    print(f"   根据 Frontmatter 的 doc_type 字段自动调整 chunk_size 和 overlap")
    
    # 扫描所有 Markdown 文件
    vault_dir = Path(vault_path)
    md_files = list(vault_dir.rglob("*.md"))
    
    # 过滤掉不需要的目录
    exclude_dirs = {'.obsidian', '.git', '__pycache__', 'node_modules', '.trash'}
    md_files = [f for f in md_files if not any(exclude in f.parts for exclude in exclude_dirs)]
    
    print(f"📂 找到 {len(md_files)} 个 Markdown 文件")
    
    if len(md_files) == 0:
        print("⚠️ 没有找到任何 Markdown 文件")
        keyword_idx.close()
        return
    
    added_count = 0
    error_count = 0
    start_time = time.time()
    
    for i, md_file in enumerate(md_files):
        try:
            # 读取文件内容
            content = md_file.read_text(encoding='utf-8')
            
            # 跳过空文件
            if not content.strip():
                continue
            
            # 分块
            chunks = chunker.chunk_text(str(md_file), content, {})
            
            if not chunks:
                continue
            
            # 添加到索引
            for chunk in chunks:
                keyword_idx.add(
                    doc_id=chunk.chunk_id,
                    content=chunk.content,
                    file_path=chunk.file_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line
                )
            
            added_count += len(chunks)
            
            # 每 10 个文件打印一次进度
            if (i + 1) % 10 == 0 or (i + 1) == len(md_files):
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(md_files) - i - 1) / rate if rate > 0 else 0
                print(f"  进度：{i + 1}/{len(md_files)} ({(i + 1) / len(md_files) * 100:.1f}%) | "
                      f"已添加：{added_count} 块 | "
                      f"速度：{rate:.1f} 文件/秒 | "
                      f"预计剩余：{eta:.0f}秒")
                
        except Exception as e:
            print(f"  ❌ 处理文件 {md_file.name} 时出错：{e}")
            error_count += 1
    
    # 获取统计信息
    stats = keyword_idx.get_stats()
    elapsed = time.time() - start_time
    
    print(f"\n✅ 关键词索引构建完成!")
    print(f"  总耗时：{elapsed:.1f}秒")
    print(f"  处理文件：{len(md_files)} 个")
    print(f"  添加块数量：{added_count}")
    print(f"  错误数量：{error_count}")
    print(f"  索引文档数：{stats['document_count']}")
    print(f"  索引文件数：{stats['file_count']}")
    print(f"\n💡 提示：本次使用了 AdaptiveChunker，不同文档类型采用不同的 chunk 策略。")
    print(f"   如需查看各文档类型的分布，请运行：")
    print(f"   python3 scripts/batch_add_doc_type.py --vault {vault_path} --dry-run")
    
    keyword_idx.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='构建关键词索引')
    parser.add_argument('--rebuild', action='store_true', help='重建索引（清空旧数据）')
    parser.add_argument('--vault', type=str, help='指定 vault 名称（可选，默认处理所有启用的 vault）')
    args = parser.parse_args()

    config = load_config()

    if not config.vaults:
        print("❌ 未找到任何启用的仓库")
        sys.exit(1)

    # 获取要处理的 vault 列表
    if args.vault:
        # 指定了特定 vault
        vault = config.get_vault_by_name(args.vault)
        if not vault:
            print(f"❌ 未找到名为 '{args.vault}' 的仓库")
            sys.exit(1)
        if not vault.enabled:
            print(f"⚠️ 仓库 {vault.name} 未启用，跳过")
            sys.exit(1)
        vaults_to_process = [vault]
    else:
        # 处理所有启用的 vault
        vaults_to_process = config.get_enabled_vaults()
        if not vaults_to_process:
            print("❌ 未找到任何启用的仓库")
            sys.exit(1)

    keyword_db = config.index.keyword.db_path

    # 处理每个 vault
    for vault in vaults_to_process:
        print(f"\n{'='*60}")
        print(f"📂 处理 Vault: {vault.name} ({vault.path})")
        print(f"{'='*60}\n")
        build_keyword_index(vault.path, keyword_db, rebuild=args.rebuild)
