#!/usr/bin/env python3
"""
测试新表结构的创建
"""

import sqlite3
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def create_test_database():
    """创建测试数据库并应用新表结构"""
    
    # 测试数据库路径
    test_db = os.path.expanduser("~/.local/share/secondbrain/test_new_schema.db")
    
    # 如果已存在，删除
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"已删除旧测试数据库：{test_db}")
    
    # 创建目录
    os.makedirs(os.path.dirname(test_db), exist_ok=True)
    
    # 连接数据库
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA encoding='UTF-8'")
    cursor = conn.cursor()
    
    print(f"✅ 创建测试数据库：{test_db}")
    
    # 读取 SQL 脚本
    sql_file = Path(__file__).parent / "create_new_schema.sql"
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # 执行 SQL 脚本
    print("📝 执行 SQL 脚本...")
    try:
        cursor.executescript(sql_script)
        conn.commit()
        print("✅ SQL 脚本执行成功")
    except Exception as e:
        print(f"❌ SQL 脚本执行失败：{e}")
        conn.close()
        return None
    
    # 验证表结构
    print("\n🔍 验证表结构...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f"\n📊 创建的表 ({len(tables)} 个):")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"  - {table_name}: {len(columns)} 列")
    
    # 验证视图
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
    views = cursor.fetchall()
    
    print(f"\n📊 创建的视图 ({len(views)} 个):")
    for view in views:
        print(f"  - {view[0]}")
    
    # 验证索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    indexes = cursor.fetchall()
    
    print(f"\n📊 创建的索引 ({len(indexes)} 个):")
    for idx in indexes:
        print(f"  - {idx[0]}")
    
    # 测试视图查询
    print("\n🧪 测试视图查询...")
    try:
        cursor.execute("SELECT * FROM v_index_stats")
        stats = cursor.fetchone()
        print(f"✅ v_index_stats 查询成功：{stats}")
    except Exception as e:
        print(f"❌ v_index_stats 查询失败：{e}")
    
    # 关闭连接
    conn.close()
    
    print(f"\n✅ 测试数据库创建完成：{test_db}")
    return test_db

def test_with_existing_data():
    """使用现有数据库测试（只创建新表，不迁移数据）"""
    
    existing_db = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
    
    if not os.path.exists(existing_db):
        print(f"⚠️  现有数据库不存在：{existing_db}")
        return None
    
    # 创建备份
    backup_db = existing_db + ".test_backup"
    import shutil
    shutil.copy2(existing_db, backup_db)
    print(f"✅ 已创建备份：{backup_db}")
    
    # 连接数据库
    conn = sqlite3.connect(existing_db)
    conn.execute("PRAGMA encoding='UTF-8'")
    cursor = conn.cursor()
    
    print(f"\n📝 在现有数据库上创建新表结构...")
    
    # 读取 SQL 脚本
    sql_file = Path(__file__).parent / "create_new_schema.sql"
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # 执行 SQL 脚本（跳过已存在的表）
    try:
        # 分割 SQL 语句
        statements = sql_script.split(';')
        for stmt in statements:
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    cursor.execute(stmt)
                except sqlite3.OperationalError as e:
                    if "already exists" in str(e):
                        # 忽略已存在的表
                        pass
                    else:
                        raise
        
        conn.commit()
        print("✅ 新表结构创建成功")
    except Exception as e:
        print(f"❌ 创建失败：{e}")
        conn.close()
        return None
    
    # 验证
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print(f"\n📊 当前数据库表数：{len(tables)}")
    
    conn.close()
    return existing_db

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试新表结构创建")
    parser.add_argument("--test", action="store_true", help="创建新的测试数据库")
    parser.add_argument("--existing", action="store_true", help="在现有数据库上创建新表")
    
    args = parser.parse_args()
    
    if args.test or not args.existing:
        test_db = create_test_database()
        if test_db:
            print(f"\n📁 测试数据库路径：{test_db}")
            print("💡 可以使用以下命令查看:")
            print(f"   sqlite3 {test_db} '.tables'")
            print(f"   sqlite3 {test_db} 'SELECT * FROM v_index_stats;'")
    
    if args.existing:
        existing_db = test_with_existing_data()
        if existing_db:
            print(f"\n📁 现有数据库路径：{existing_db}")
