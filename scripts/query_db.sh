#!/bin/bash
# SecondBrain SQLite 数据库查询工具
# 正确显示 UTF-8 中文字符

DB_PATH="${1:-$HOME/.local/share/secondbrain/semantic_index.db}"

if [ ! -f "$DB_PATH" ]; then
    echo "错误：数据库文件不存在：$DB_PATH"
    exit 1
fi

echo "=========================================="
echo "SecondBrain SQLite 数据库查询工具"
echo "数据库：$DB_PATH"
echo "=========================================="
echo ""
echo "可用命令:"
echo "  1. 查看所有文档 (SELECT * FROM vectors)"
echo "  2. 查看文档 ID 和文件路径"
echo "  3. 统计文档数量"
echo "  4. 自定义查询"
echo ""
read -p "请选择 (1-4 或输入自定义 SQL): " choice

case $choice in
    1)
        sqlite3 "$DB_PATH" ".mode column" ".headers on" "SELECT doc_id, json_extract(metadata, '$.file_path') as file_path FROM vectors LIMIT 30;"
        ;;
    2)
        sqlite3 "$DB_PATH" ".mode column" ".headers on" "SELECT doc_id, json_extract(metadata, '$.file_path') as path FROM vectors;"
        ;;
    3)
        sqlite3 "$DB_PATH" "SELECT COUNT(*) as '文档总数' FROM vectors;"
        ;;
    4)
        read -p "输入 SQL 查询: " sql
        sqlite3 "$DB_PATH" ".mode column" ".headers on" "$sql"
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "提示：使用 '.mode column' 和 '.headers on' 正确显示 UTF-8"
echo "=========================================="
