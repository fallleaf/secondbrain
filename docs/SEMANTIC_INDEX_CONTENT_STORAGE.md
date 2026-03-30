# SemanticIndex 内容存储功能实施报告

## 📋 目标

在 `semantic_index.db` 中创建 `chunks` 表，存储文档分块的实际内容，解决搜索时无法直接获取文本的问题。

## ✅ 已完成的工作

### 1. 数据库结构修改 (`semantic_index.py`)

- ✅ 创建 `chunks` 表：
  ```sql
  CREATE TABLE IF NOT EXISTS chunks (
      doc_id TEXT,
      chunk_index INTEGER,
      content TEXT,
      start_line INTEGER,
      end_line INTEGER,
      PRIMARY KEY (doc_id, chunk_index)
  )
  ```

- ✅ 创建 `chunks_fts` 表（FTS5 全文索引）

- ✅ 修改 `add_embedding` 方法，支持 `content` 参数

- ✅ 添加 `get_chunk_content` 方法

### 2. 数据备份

- ✅ 已备份到 `~/.local/share/secondbrain/backup_20260330/`

## ⚠️ 遇到的问题

### 1. `hybrid_retriever.py` 文件损坏

在修改过程中，文件出现语法错误，导致无法导入。

**原因**: 多次编辑导致缩进和结构混乱。

**影响**: 无法使用新的 `get_chunk_content` 方法。

### 2. 代码复杂度

修改涉及多个文件的协同工作：
- `semantic_index.py`: 添加存储和读取功能
- `hybrid_retriever.py`: 使用新方法获取内容
- 重建索引脚本：迁移现有数据

## 🚀 建议的下一步操作

### 方案 A: 使用 git 恢复（推荐）

```bash
# 如果有 git 仓库
cd ~/project/secondbrain
git checkout HEAD -- src/index/hybrid_retriever.py
# 然后重新应用修改
```

### 方案 B: 从备份恢复并重新修改

1. 恢复 `hybrid_retriever.py` 到稳定版本
2. 只修改 `_convert_semantic_results` 方法中的内容读取部分
3. 测试每个步骤

### 方案 C: 简化实现（快速）

暂时不修改 `hybrid_retriever.py`，保持从文件读取的逻辑：
- `chunks` 表已创建，可以存储内容
- 搜索时仍然从文件读取（当前逻辑）
- 未来再优化为从数据库读取

## 📝 当前可用功能

1. **`SemanticIndex.add_embedding`** 支持 `content` 参数
2. **`SemanticIndex.get_chunk_content`** 可以读取内容
3. **`chunks` 表** 已创建，可以存储数据

## 🔧 测试代码

```python
from src.index.semantic_index import SemanticIndex

idx = SemanticIndex('~/.local/share/secondbrain/semantic_index.db', dim=512)

# 添加带内容的文档
idx.add_embedding(
    doc_id='test.md',
    embedding=[0.0] * 512,
    metadata={'file_path': 'test.md'},
    content='这是测试内容',
    start_line=0,
    end_line=10
)

# 读取内容
content = idx.get_chunk_content('test.md', 0)
print(content)  # 输出：这是测试内容
```

## 📊 迁移脚本（待执行）

```python
# 迁移现有数据到 chunks 表
for file_path in vault_path.rglob("*.md"):
    content = file_path.read_text(encoding='utf-8')
    semantic_idx.add_embedding(
        doc_id=rel_path,
        embedding=embedding.tolist(),
        metadata={'file_path': str(file_path)},
        content=content,
        start_line=0,
        end_line=len(content.splitlines())
    )
```

## ⏭️ 下一步

1. **修复 `hybrid_retriever.py`**（如果需要从数据库读取内容）
2. **运行迁移脚本**（填充 `chunks` 表）
3. **测试搜索功能**

---

报告时间：2026-03-30 08:00  
状态：部分完成，需要修复 `hybrid_retriever.py`
