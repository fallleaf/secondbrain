# SecondBrain 数据库重构快速参考

## 🚀 快速开始

### 1. 查看新表结构

```bash
# 创建测试数据库
python3 scripts/test_new_schema.py --test

# 查看表结构
sqlite3 ~/.local/share/secondbrain/test_new_schema.db '.tables'
sqlite3 ~/.local/share/secondbrain/test_new_schema.db '.schema documents'
```

### 2. 执行数据迁移

```bash
# Dry-run 测试（不实际执行）
python3 scripts/migrate_to_v2.py --dry-run

# 执行实际迁移
python3 scripts/migrate_to_v2.py

# 迁移到新的数据库文件（保留原数据库）
python3 scripts/migrate_to_v2.py --target ~/.local/share/secondbrain/semantic_index_v2.db
```

### 3. 验证迁移结果

```bash
# 验证迁移（自动查找最新备份）
python3 scripts/verify_migration.py

# 指定源和目标数据库
python3 scripts/verify_migration.py \
  --source ~/.local/share/secondbrain/semantic_index.db.backup.20260330 \
  --target ~/.local/share/secondbrain/semantic_index.db

# 输出详细报告
python3 scripts/verify_migration.py --output docs/verification_report.json
```

### 4. 回滚迁移

```bash
# 恢复备份
cp ~/.local/share/secondbrain/semantic_index.db.backup.* \
   ~/.local/share/secondbrain/semantic_index.db

# 验证恢复
python3 scripts/verify_migration.py
```

---

## 📊 常用查询

### 索引统计

```sql
-- 总体统计
SELECT * FROM v_index_stats;

-- 文档类型分布
SELECT * FROM v_doc_type_stats;

-- 优先级分布
SELECT * FROM v_priority_stats;

-- 标签使用统计
SELECT * FROM v_tag_stats LIMIT 20;
```

### 文档查询

```sql
-- 获取文档详情（包含标签和链接统计）
SELECT * FROM v_document_details WHERE doc_id = 'xxx';

-- 按文档类型查询
SELECT * FROM documents WHERE doc_type = 'technical';

-- 按优先级查询
SELECT * FROM documents WHERE priority >= 7;

-- 按标签查询
SELECT d.* FROM documents d
JOIN document_tags dt ON d.doc_id = dt.doc_id
JOIN tags t ON dt.tag_id = t.tag_id
WHERE t.tag_name = 'important';
```

### 链接分析

```sql
-- 查找断裂链接
SELECT * FROM links WHERE is_broken = 1;

-- 查找孤立笔记（无入链）
SELECT d.* FROM documents d
WHERE d.doc_id NOT IN (
  SELECT target_doc_id FROM links WHERE target_doc_id IS NOT NULL
);

-- 获取文档的出站链接
SELECT * FROM links WHERE source_doc_id = 'xxx';

-- 获取文档的反向链接
SELECT * FROM links WHERE target_doc_id = 'xxx';
```

---

## 🔧 脚本说明

### create_new_schema.sql
- **功能**: 创建新表结构
- **使用**: 直接导入 SQLite 数据库
- **输出**: 7 个表 + 5 个视图 + 14 个索引

### test_new_schema.py
- **功能**: 测试新表结构创建
- **参数**:
  - `--test`: 创建新的测试数据库
  - `--existing`: 在现有数据库上创建新表
- **输出**: 测试数据库和验证报告

### migrate_to_v2.py
- **功能**: 数据迁移
- **参数**:
  - `--source`: 源数据库路径（默认：现有数据库）
  - `--target`: 目标数据库路径（默认：覆盖源数据库）
  - `--dry-run`: 仅模拟，不实际执行
  - `--backup-only`: 仅备份，不迁移
- **输出**: 迁移统计和日志

### verify_migration.py
- **功能**: 验证迁移结果
- **参数**:
  - `--source`: 源数据库路径（支持通配符）
  - `--target`: 目标数据库路径
  - `--output`: 输出报告路径
- **输出**: JSON 格式的验证报告

---

## 📈 性能优化建议

### 索引优化

```sql
-- 分析查询计划
EXPLAIN QUERY PLAN SELECT * FROM documents WHERE doc_type = 'technical';

-- 重建索引
REINDEX;

-- 优化数据库
VACUUM;
```

### 查询优化

```sql
-- 使用索引
SELECT * FROM documents 
WHERE doc_type = 'technical' 
  AND priority >= 7
LIMIT 10;

-- 避免全表扫描
SELECT * FROM documents 
WHERE file_path LIKE '%NanobotMemory%';
```

---

## 🐛 故障排查

### 问题 1: 迁移失败

**症状**: 迁移脚本报错

**解决**:
```bash
# 1. 检查备份
ls -lh ~/.local/share/secondbrain/semantic_index.db.backup.*

# 2. 恢复备份
cp backup.* semantic_index.db

# 3. 检查数据库完整性
sqlite3 semantic_index.db "PRAGMA integrity_check;"

# 4. 重新执行迁移
python3 scripts/migrate_to_v2.py
```

### 问题 2: 视图查询失败

**症状**: 查询视图时报错

**解决**:
```bash
# 1. 检查视图是否存在
sqlite3 database.db ".schema v_index_stats"

# 2. 重新创建视图
sqlite3 database.db < scripts/create_new_schema.sql

# 3. 检查表数据
sqlite3 database.db "SELECT COUNT(*) FROM documents;"
```

### 问题 3: 查询性能差

**症状**: 查询响应时间过长

**解决**:
```bash
# 1. 分析查询计划
sqlite3 database.db "EXPLAIN QUERY PLAN SELECT ..."

# 2. 检查索引
sqlite3 database.db ".indexes"

# 3. 优化数据库
sqlite3 database.db "VACUUM;"
sqlite3 database.db "REINDEX;"
```

---

## 📚 相关文档

- [数据库重构设计](DB_RESTRUCTURE_PLAN.md) - 详细设计文档
- [实施方案](../RESTRUCTURE_IMPLEMENTATION.md) - 分阶段实施计划
- [Phase 1 测试报告](PHASE1_TEST_REPORT.md) - 测试报告
- [项目总结](PROJECT_SUMMARY.md) - 项目总体情况

---

## 📞 技术支持

- **问题反馈**: 查看 `docs/` 目录下的相关文档
- **脚本帮助**: `python3 scripts/<script>.py --help`

---

**最后更新**: 2026-03-30
