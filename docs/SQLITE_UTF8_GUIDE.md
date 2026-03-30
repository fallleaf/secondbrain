# SecondBrain SQLite 数据库 UTF-8 显示指南

## 问题描述

在使用 `sqlite3` 命令行工具查询 SecondBrain 的 SQLite 数据库时，中文字符可能显示为 Unicode 转义（如 `\u4efb\u52a1\u6e05\u5355`），而不是正常的中文（如 `任务清单`）。

## 原因分析

**数据本身是正确的**！SQLite 数据库以 UTF-8 编码正确存储了中文字符。问题出在 `sqlite3` 命令行工具的**默认显示模式**上。

## 解决方案

### 方法 1: 使用正确的显示模式（推荐）

```bash
# 设置列模式和显示表头
sqlite3 ~/.local/share/secondbrain/semantic_index.db ".mode column" ".headers on" "SELECT * FROM vectors LIMIT 5;"

# 或者分步设置
sqlite3 ~/.local/share/secondbrain/semantic_index.db
sqlite> .mode column
sqlite> .headers on
sqlite> SELECT doc_id, json_extract(metadata, '$.file_path') as path FROM vectors LIMIT 5;
```

### 方法 2: 使用 JSON 模式

```bash
sqlite3 ~/.local/share/secondbrain/semantic_index.db ".mode json" "SELECT doc_id, metadata FROM vectors LIMIT 3;"
```

### 方法 3: 使用自定义查询脚本

```bash
# 使用提供的查询脚本
./scripts/query_db.sh

# 或直接查询
./scripts/query_db.sh ~/.local/share/secondbrain/keyword_index.db
```

## 常用查询示例

### 查看所有文档

```bash
sqlite3 ~/.local/share/secondbrain/semantic_index.db \
  ".mode column" ".headers on" \
  "SELECT doc_id, json_extract(metadata, '$.file_path') as file_path FROM vectors LIMIT 20;"
```

### 统计文档数量

```bash
sqlite3 ~/.local/share/secondbrain/semantic_index.db \
  "SELECT COUNT(*) as '文档总数' FROM vectors;"
```

### 搜索特定文件

```bash
sqlite3 ~/.local/share/secondbrain/semantic_index.db \
  ".mode column" ".headers on" \
  "SELECT doc_id, json_extract(metadata, '$.file_path') as path \
   FROM vectors \
   WHERE json_extract(metadata, '$.file_path') LIKE '%日记%';"
```

### 查看元数据详情

```bash
sqlite3 ~/.local/share/secondbrain/semantic_index.db \
  ".mode column" ".headers on" \
  "SELECT doc_id, \
          json_extract(metadata, '$.file_path') as file_path, \
          json_extract(metadata, '$.tags') as tags \
   FROM vectors \
   LIMIT 5;"
```

## sqlite3 常用模式说明

| 模式 | 命令 | 说明 |
|------|------|------|
| 列模式 | `.mode column` | 对齐的列，适合阅读 |
| 表格模式 | `.mode table` | ASCII 表格 |
| CSV 模式 | `.mode csv` | CSV 格式 |
| JSON 模式 | `.mode json` | JSON 格式 |
| 行模式 | `.mode line` | 每行一个字段 |

## 持久化设置

可以在 `~/.sqliterc` 文件中添加默认设置：

```bash
# 创建或编辑 ~/.sqliterc
echo ".mode column" >> ~/.sqliterc
echo ".headers on" >> ~/.sqliterc
echo ".nullvalue NULL" >> ~/.sqliterc
```

之后每次启动 sqlite3 都会自动应用这些设置。

## 验证数据完整性

```bash
# 检查是否有损坏的数据
sqlite3 ~/.local/share/secondbrain/semantic_index.db "PRAGMA integrity_check;"

# 查看表结构
sqlite3 ~/.local/share/secondbrain/semantic_index.db ".schema"

# 检查字符集
sqlite3 ~/.local/share/secondbrain/semantic_index.db "SELECT sqlite_version();"
```

## 数据库文件位置

- **语义索引**: `~/.local/share/secondbrain/semantic_index.db`
- **关键词索引**: `~/.local/share/secondbrain/keyword_index.db`
- **测试索引**: `~/.local/share/secondbrain/test_keyword_index.db`

## 常见问题

### Q: 为什么数据看起来是乱码？

A: 数据实际上是正确的 UTF-8 编码，只是显示模式不对。使用 `.mode column` 和 `.headers on` 即可正确显示。

### Q: 能否直接修改数据库字符集？

A: 不需要。SQLite 默认使用 UTF-8 编码，数据已经正确存储。只需调整显示模式即可。

### Q: 如何在 Python 中正确读取？

A: Python 的 `sqlite3` 模块默认支持 UTF-8，无需特殊设置：

```python
import sqlite3
conn = sqlite3.connect('~/.local/share/secondbrain/semantic_index.db')
cursor = conn.cursor()
cursor.execute("SELECT doc_id, metadata FROM vectors LIMIT 5")
for row in cursor:
    print(row[0], row[1])  # 中文字符正常显示
```

## 参考

- [SQLite 命令行工具文档](https://www.sqlite.org/cli.html)
- [SQLite 字符集支持](https://www.sqlite.org/unicode.html)

---

**更新日期**: 2026-03-28  
**维护者**: nanobot
