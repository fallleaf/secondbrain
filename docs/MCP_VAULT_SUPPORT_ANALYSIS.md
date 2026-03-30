# MCP 查询工具多 Vault 支持问题分析与修复方案

## 📋 问题描述

当前 SecondBrain MCP 服务器的查询工具**没有按照 `config.yaml` 中配置的 `vaults` 进行查询**，存在以下问题：

### 问题 1: 初始化时只使用第一个 Vault
```python
# src/tools/secondbrain_tools.py:35
self.filesystem = FileSystem(config.vaults[0].path)  # ❌ 只使用第一个
self.link_analyzer = LinkAnalyzer(config.vaults[0].path)  # ❌ 只使用第一个
self.tag_manager = TagManager(config.vaults[0].path)  # ❌ 只使用第一个
```

### 问题 2: 索引是全局的，不支持多 Vault
```python
# src/tools/secondbrain_tools.py:39-40
self.keyword_index = KeywordIndex(config.index.keyword.db_path)  # ❌ 全局索引
self.semantic_index = SemanticIndex(config.index.semantic.db_path)  # ❌ 全局索引
```

### 问题 3: `vault_name` 参数被接收但未使用
```python
# src/tools/secondbrain_tools.py:64
vault_name = arguments.get("vault_name", "")  # ❌ 接收了但没用

# src/tools/secondbrain_tools.py:84
content = self.filesystem.read_file(path)  # ❌ 始终使用第一个 vault
```

---

## 🔍 影响分析

### 当前行为
| 工具 | 参数 `vault_name` | 实际行为 |
|------|------------------|---------|
| `semantic_search` | "NanobotMemory" | ❌ 搜索全局索引（所有 vault 混合） |
| `read_note` | "NanobotMemory" | ❌ 从第一个 vault 读取 |
| `list_notes` | "NanobotMemory" | ❌ 列出第一个 vault 的文件 |
| `find_broken_links` | "NanobotMemory" | ❌ 检查第一个 vault |

### 预期行为
| 工具 | 参数 `vault_name` | 预期行为 |
|------|------------------|---------|
| `semantic_search` | "NanobotMemory" | ✅ 只搜索 NanobotMemory vault 的索引 |
| `read_note` | "NanobotMemory" | ✅ 从 NanobotMemory vault 读取 |
| `list_notes` | "NanobotMemory" | ✅ 列出 NanobotMemory vault 的文件 |

---

## 🛠️ 修复方案

### 方案 A: 每个 Vault 独立索引（推荐）

#### 1. 修改配置结构
```yaml
# ~/.config/secondbrain/config.yaml
vaults:
  - name: NanobotMemory
    path: ~/NanobotMemory
    enabled: true
    index:
      semantic_db: ~/.local/share/secondbrain/nanobot_memory_semantic.db
      keyword_db: ~/.local/share/secondbrain/nanobot_memory_keyword.db
  - name: Obsidian
    path: ~/Obsidian
    enabled: true
    index:
      semantic_db: ~/.local/share/secondbrain/obsidian_semantic.db
      keyword_db: ~/.local/share/secondbrain/obsidian_keyword.db
```

#### 2. 修改 `SecondBrainTools` 初始化
```python
class SecondBrainTools:
    def __init__(self, config: Settings):
        self.config = config
        # 为每个 vault 创建独立的索引
        self.vault_indexes = {}
        for vault in config.vaults:
            if vault.enabled:
                keyword_db = vault.index.keyword_db or f"~/.local/share/secondbrain/{vault.name}_keyword.db"
                semantic_db = vault.index.semantic_db or f"~/.local/share/secondbrain/{vault.name}_semantic.db"
                
                self.vault_indexes[vault.name] = {
                    'keyword': KeywordIndex(keyword_db),
                    'semantic': SemanticIndex(semantic_db),
                    'filesystem': FileSystem(vault.path),
                    'retriever': HybridRetriever(...)
                }
```

#### 3. 修改工具方法
```python
async def semantic_search(self, arguments: Dict[str, Any]) -> List[str]:
    query = arguments.get("query", "")
    vault_name = arguments.get("vault_name", "")
    
    # 根据 vault_name 选择索引
    if vault_name:
        vault = self.config.get_vault_by_name(vault_name)
        if not vault or not vault.enabled:
            raise ValueError(f"Vault '{vault_name}' 不存在或未启用")
        index = self.vault_indexes[vault_name]
    else:
        # 默认使用第一个 vault
        index = self.vault_indexes[self.config.vaults[0].name]
    
    # 执行搜索
    results = index['retriever'].search(query, ...)
    return results
```

**优点**:
- ✅ 每个 vault 完全隔离
- ✅ 搜索性能更好（索引更小）
- ✅ 支持独立重建索引

**缺点**:
- ⚠️ 需要为每个 vault 维护独立索引
- ⚠️ 跨 vault 搜索需要特殊处理

---

### 方案 B: 单索引 + 路径过滤（快速修复）

#### 1. 保持全局索引
```python
# 不修改索引初始化
self.keyword_index = KeywordIndex(config.index.keyword.db_path)
self.semantic_index = SemanticIndex(config.index.semantic.db_path)
```

#### 2. 修改搜索逻辑，添加路径过滤
```python
async def semantic_search(self, arguments: Dict[str, Any]) -> List[str]:
    query = arguments.get("query", "")
    vault_name = arguments.get("vault_name", "")
    
    # 如果指定了 vault，获取其路径
    vault_path = None
    if vault_name:
        vault = self.config.get_vault_by_name(vault_name)
        if vault:
            vault_path = vault.path
    
    # 执行搜索
    results = self.hybrid_retriever.search(query, ...)
    
    # 过滤结果（只保留指定 vault 的文件）
    if vault_path:
        results = [r for r in results if r.file_path.startswith(vault_path)]
    
    return results
```

#### 3. 修改文件操作工具
```python
async def read_note(self, arguments: Dict[str, Any]) -> List[str]:
    path = arguments.get("path", "")
    vault_name = arguments.get("vault_name", "")
    
    # 如果指定了 vault，拼接完整路径
    if vault_name:
        vault = self.config.get_vault_by_name(vault_name)
        if vault:
            full_path = os.path.join(vault.path, path)
        else:
            raise ValueError(f"Vault '{vault_name}' 不存在")
    else:
        full_path = path  # 使用默认 vault
    
    content = self.filesystem.read_file(full_path)
    return [content]
```

**优点**:
- ✅ 快速修复，改动小
- ✅ 无需重建索引
- ✅ 支持跨 vault 搜索（不指定 vault_name）

**缺点**:
- ⚠️ 索引包含所有 vault，可能较大
- ⚠️ 路径过滤可能不精确（如果路径重叠）

---

### 方案 C: 混合方案（平衡）

#### 1. 文件操作使用独立 FileSystem
```python
class SecondBrainTools:
    def __init__(self, config: Settings):
        self.config = config
        # 全局索引
        self.keyword_index = KeywordIndex(config.index.keyword.db_path)
        self.semantic_index = SemanticIndex(config.index.semantic.db_path)
        self.hybrid_retriever = HybridRetriever(...)
        
        # 每个 vault 独立的 FileSystem
        self.vault_filesystems = {}
        for vault in config.vaults:
            if vault.enabled:
                self.vault_filesystems[vault.name] = FileSystem(vault.path)
```

#### 2. 工具方法根据 vault_name 选择 FileSystem
```python
async def read_note(self, arguments: Dict[str, Any]) -> List[str]:
    path = arguments.get("path", "")
    vault_name = arguments.get("vault_name", "")
    
    if vault_name:
        if vault_name not in self.vault_filesystems:
            raise ValueError(f"Vault '{vault_name}' 不存在")
        filesystem = self.vault_filesystems[vault_name]
    else:
        filesystem = self.vault_filesystems[self.config.vaults[0].name]
    
    content = filesystem.read_file(path)
    return [content]
```

**优点**:
- ✅ 文件操作完全隔离
- ✅ 搜索可以跨 vault 或按 vault 过滤
- ✅ 改动适中

**缺点**:
- ⚠️ 索引仍是全局的

---

## 🚀 推荐实施步骤

### 阶段 1: 快速修复（方案 B + C 混合）
1. **修改 `SecondBrainTools.__init__`**
   - 为每个 vault 创建独立的 `FileSystem`
   - 保持全局索引

2. **修改文件操作工具**
   - `read_note`, `list_notes`, `write_note`, `delete_note`, `move_note`
   - 根据 `vault_name` 选择对应的 `FileSystem`

3. **修改搜索工具**
   - `semantic_search`, `search_notes`
   - 根据 `vault_name` 过滤搜索结果

### 阶段 2: 独立索引（方案 A）
1. **修改配置结构**
   - 为每个 vault 添加独立的索引路径配置

2. **修改索引管理工具**
   - `rebuild_semantic_index` 支持指定 vault
   - `get_index_stats` 支持按 vault 统计

3. **重建索引**
   - 为每个 vault 创建独立索引

---

## 📝 代码修改清单

### 需要修改的文件
1. `src/config/settings.py`
   - 在 `VaultConfig` 中添加 `index` 字段（可选）

2. `src/tools/secondbrain_tools.py`
   - `__init__`: 为每个 vault 创建 `FileSystem`
   - `read_note`: 根据 `vault_name` 选择 filesystem
   - `list_notes`: 根据 `vault_name` 选择 filesystem
   - `write_note`: 根据 `vault_name` 选择 filesystem
   - `delete_note`: 根据 `vault_name` 选择 filesystem
   - `move_note`: 根据 `vault_name` 选择 filesystem
   - `semantic_search`: 根据 `vault_name` 过滤结果
   - `search_notes`: 根据 `vault_name` 过滤结果
   - `find_broken_links`: 根据 `vault_name` 选择 filesystem
   - `find_orphaned_notes`: 根据 `vault_name` 选择 filesystem
   - `list_tags`: 根据 `vault_name` 选择 filesystem
   - `get_note_info`, `get_note_tags`, `get_note_links`, `get_backlinks`: 根据 `vault_name` 选择 filesystem

3. `src/server.py`
   - 更新工具描述，说明 `vault_name` 的作用

---

## ⚠️ 注意事项

### 1. 向后兼容
- 如果 `vault_name` 为空，默认使用第一个 vault
- 保持现有 API 不变

### 2. 错误处理
- 如果指定的 `vault_name` 不存在，返回清晰错误
- 如果 vault 未启用，提示用户

### 3. 性能
- 方案 B 的路径过滤可能影响性能
- 方案 A 的独立索引需要更多磁盘空间

---

## 🎯 总结

**当前状态**: ❌ **完全不支持多 vault**
- 所有工具都基于第一个 vault
- `vault_name` 参数被忽略

**推荐方案**: **阶段 1（快速修复）+ 阶段 2（独立索引）**
- 阶段 1: 1-2 小时，支持文件操作隔离
- 阶段 2: 4-6 小时，支持完全隔离

**立即行动**:
```bash
# 1. 检查当前配置
cat ~/.config/secondbrain/config.yaml

# 2. 测试当前行为
# 指定不同的 vault_name，观察是否真的切换了 vault

# 3. 实施阶段 1 修复
# 修改 src/tools/secondbrain_tools.py
```

---

分析时间：2026-03-30 07:15  
问题严重性：**高**（多 vault 功能完全缺失）
