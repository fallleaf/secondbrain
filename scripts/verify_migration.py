#!/usr/bin/env python3
"""
迁移验证脚本
验证数据库迁移的正确性和完整性
"""

import sqlite3
import json
import os
import sys
from pathlib import Path
from datetime import datetime

import sqlite_vec


def verify_migration(source_db: str, target_db: str) -> dict:
    """
    验证迁移结果
    
    Args:
        source_db: 源数据库路径
        target_db: 目标数据库路径
    
    Returns:
        验证报告
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "source_db": source_db,
        "target_db": target_db,
        "checks": [],
        "summary": {}
    }
    
    # 连接数据库
    def get_conn(db_path):
        conn = sqlite3.connect(db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row
        return conn
    
    source_conn = get_conn(source_db)
    target_conn = get_conn(target_db)
    
    source_cur = source_conn.cursor()
    target_cur = target_conn.cursor()
    
    # 检查 1: 文档数量
    print("📊 检查 1: 文档数量...")
    source_cur.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks")
    source_docs = source_cur.fetchone()[0]
    
    target_cur.execute("SELECT COUNT(*) FROM documents")
    target_docs = target_cur.fetchone()[0]
    
    check = {
        "name": "文档数量",
        "source": source_docs,
        "target": target_docs,
        "pass": source_docs == target_docs
    }
    report["checks"].append(check)
    print(f"   {'✅' if check['pass'] else '❌'} {source_docs} -> {target_docs}")
    
    # 检查 2: 分块数量
    print("📊 检查 2: 分块数量...")
    source_cur.execute("SELECT COUNT(*) FROM chunks")
    source_chunks = source_cur.fetchone()[0]
    
    target_cur.execute("SELECT COUNT(*) FROM chunks")
    target_chunks = target_cur.fetchone()[0]
    
    check = {
        "name": "分块数量",
        "source": source_chunks,
        "target": target_chunks,
        "pass": source_chunks == target_chunks
    }
    report["checks"].append(check)
    print(f"   {'✅' if check['pass'] else '❌'} {source_chunks} -> {target_chunks}")
    
    # 检查 3: 向量数量
    print("📊 检查 3: 向量数量...")
    source_cur.execute("SELECT COUNT(*) FROM vectors_vec")
    source_vecs = source_cur.fetchone()[0]
    
    target_cur.execute("SELECT COUNT(*) FROM vectors_vec")
    target_vecs = target_cur.fetchone()[0]
    
    check = {
        "name": "向量数量",
        "source": source_vecs,
        "target": target_vecs,
        "pass": source_vecs == target_vecs
    }
    report["checks"].append(check)
    print(f"   {'✅' if check['pass'] else '❌'} {source_vecs} -> {target_vecs}")
    
    # 检查 4: 标签统计
    print("📊 检查 4: 标签统计...")
    target_cur.execute("SELECT COUNT(*) FROM tags")
    tag_count = target_cur.fetchone()[0]
    
    target_cur.execute("SELECT COUNT(*) FROM document_tags")
    doc_tag_count = target_cur.fetchone()[0]
    
    check = {
        "name": "标签统计",
        "tag_count": tag_count,
        "document_tag_count": doc_tag_count,
        "pass": tag_count > 0 or doc_tag_count == 0  # 允许没有标签
    }
    report["checks"].append(check)
    print(f"   {'✅' if check['pass'] else '❌'} 标签数：{tag_count}, 关联数：{doc_tag_count}")
    
    # 检查 5: Frontmatter 统计
    print("📊 检查 5: Frontmatter 统计...")
    target_cur.execute("SELECT COUNT(*) FROM frontmatter")
    frontmatter_count = target_cur.fetchone()[0]
    
    check = {
        "name": "Frontmatter 统计",
        "count": frontmatter_count,
        "pass": True
    }
    report["checks"].append(check)
    print(f"   ✅ Frontmatter 数：{frontmatter_count}")
    
    # 检查 6: 视图查询
    print("📊 检查 6: 视图查询...")
    views_ok = True
    view_results = {}
    
    try:
        target_cur.execute("SELECT * FROM v_index_stats")
        stats = target_cur.fetchone()
        view_results["v_index_stats"] = {
            "doc_count": stats[0],
            "chunk_count": stats[1],
            "tag_count": stats[2]
        }
    except Exception as e:
        views_ok = False
        view_results["error"] = str(e)
    
    check = {
        "name": "视图查询",
        "pass": views_ok,
        "results": view_results
    }
    report["checks"].append(check)
    print(f"   {'✅' if views_ok else '❌'} 视图查询 {'成功' if views_ok else '失败'}")
    
    # 检查 7: 文档类型分布
    print("📊 检查 7: 文档类型分布...")
    target_cur.execute("SELECT * FROM v_doc_type_stats")
    doc_types = target_cur.fetchall()
    
    check = {
        "name": "文档类型分布",
        "pass": len(doc_types) > 0,
        "distribution": {row[0]: row[1] for row in doc_types}
    }
    report["checks"].append(check)
    print(f"   {'✅' if check['pass'] else '❌'} 文档类型：{list(check['distribution'].keys())}")
    
    # 检查 8: 数据完整性抽样
    print("📊 检查 8: 数据完整性抽样...")
    sample_size = min(10, target_docs)
    target_cur.execute("SELECT doc_id, file_path, doc_type, priority FROM documents LIMIT ?", (sample_size,))
    samples = target_cur.fetchall()
    
    integrity_ok = all(
        sample[1] is not None and  # file_path not null
        sample[2] in ['faq', 'technical', 'blog', 'legal', 'meeting', 'default'] and  # valid doc_type
        1 <= sample[3] <= 9  # valid priority
        for sample in samples
    )
    
    check = {
        "name": "数据完整性抽样",
        "sample_size": sample_size,
        "pass": integrity_ok,
        "samples": [{"doc_id": s[0], "file_path": s[1], "doc_type": s[2], "priority": s[3]} for s in samples[:3]]
    }
    report["checks"].append(check)
    print(f"   {'✅' if integrity_ok else '❌'} 抽样检查 {'通过' if integrity_ok else '失败'}")
    
    # 生成总结
    passed = sum(1 for c in report["checks"] if c["pass"])
    total = len(report["checks"])
    
    report["summary"] = {
        "total_checks": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": f"{100*passed/total:.1f}%",
        "overall": "PASS" if passed == total else "FAIL"
    }
    
    # 关闭连接
    source_conn.close()
    target_conn.close()
    
    # 打印总结
    print("\n" + "=" * 60)
    print("📊 验证总结")
    print("=" * 60)
    print(f"总检查数：{total}")
    print(f"通过：{passed}")
    print(f"失败：{total - passed}")
    print(f"通过率：{report['summary']['pass_rate']}")
    print(f"总体结果：{report['summary']['overall']}")
    print("=" * 60)
    
    return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="验证数据库迁移结果")
    parser.add_argument("--source", default="~/.local/share/secondbrain/semantic_index.db.backup.*",
                       help="源数据库路径（支持通配符）")
    parser.add_argument("--target", default="~/.local/share/secondbrain/semantic_index.db",
                       help="目标数据库路径")
    parser.add_argument("--output", default=None,
                       help="输出报告文件路径")
    
    args = parser.parse_args()
    
    # 处理源数据库路径（支持通配符）
    source_db = os.path.expanduser(args.source)
    if '*' in source_db:
        import glob
        backups = glob.glob(source_db)
        if not backups:
            print(f"❌ 未找到备份文件：{source_db}")
            sys.exit(1)
        # 选择最新的备份
        source_db = max(backups, key=os.path.getmtime)
    else:
        source_db = os.path.expanduser(source_db)
    
    target_db = os.path.expanduser(args.target)
    
    if not os.path.exists(source_db):
        print(f"❌ 源数据库不存在：{source_db}")
        sys.exit(1)
    
    if not os.path.exists(target_db):
        print(f"❌ 目标数据库不存在：{target_db}")
        sys.exit(1)
    
    print(f"🔍 开始验证迁移...")
    print(f"   源数据库：{source_db}")
    print(f"   目标数据库：{target_db}")
    print()
    
    report = verify_migration(source_db, target_db)
    
    # 保存报告
    if args.output:
        output_path = os.path.expanduser(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 报告已保存到：{output_path}")
    else:
        # 默认保存到 docs 目录
        docs_dir = Path(__file__).parent.parent / "docs"
        docs_dir.mkdir(exist_ok=True)
        output_path = docs_dir / f"migration_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 报告已保存到：{output_path}")
    
    # 退出码
    sys.exit(0 if report["summary"]["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
