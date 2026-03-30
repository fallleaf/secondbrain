# SecondBrain MCP 服务器配置指南

## 📁 配置文件位置

```
~/.config/secondbrain/config.yaml
```

## 📝 配置示例

```yaml
# Vault 配置 (支持多个笔记库)
vaults:
  - path: ~/NanobotMemory
    name: personal
    enabled: true
  - path: ~/Work/Notes
    name: work
    enabled: false

# 索引设置
index:
  semantic:
    enabled: true
    model: BAAI/bge-small-zh-v1.5  # 嵌入模型
    chunk_size: 800                # 文本块大小
    chunk_overlap: 150             # 块重叠部分
    db_path: ~/.local/share/secondbrain/semantic_index.db
  keyword:
    enabled: true
    backend: sqlite_fts5           # 或 bm25

# 优先级配置
priority:
  config_path: ~/.config/secondbrain/priority_config.yaml
  enabled: true
  default_priority: 3

# 安全设置
security:
  max_read_size: 1048576           # 1MB
  max_batch_size: 20
  require_confirm_delete: true
  excluded_dirs:
    - .obsidian
    - .trash
    - .git

# 日志设置
logging:
  level: INFO
  file: ~/.local/share/secondbrain/mcp.log
  max_size: 10485760               # 10MB
  backup_count: 5
```

## 🚀 启动 MCP 服务器

### 方法 1: 直接运行
```bash
cd ~/project/secondbrain
PYTHONPATH=. python3 -m src.server
```

### 方法 2: 使用 CLI
```bash
cd ~/project/secondbrain
python3 -m src.server
```

### 方法 3: 创建可执行脚本
```bash
# 创建启动脚本
cat > ~/bin/secondbrain-mcp << 'EOF'
#!/bin/bash
cd ~/project/secondbrain
PYTHONPATH=. python3 -m src.server "$@"
EOF
chmod +x ~/bin/secondbrain-mcp

# 使用
secondbrain-mcp
```

## 🔧 在 Obsidian 中配置

### 使用 Obsidian MCP 插件

1. 安装 Obsidian MCP 插件
2. 配置服务器：
```json
{
  "servers": [
    {
      "name": "SecondBrain",
      "command": "python3",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "/home/fallleaf/project/secondbrain",
      "env": {
        "PYTHONPATH": "/home/fallleaf/project/secondbrain"
      }
    }
  ]
}
```

### 使用 VS Code / Cursor

在 `.vscode/settings.json` 或 `settings.json` 中配置：
```json
{
  "mcp.servers": {
    "secondbrain": {
      "command": "python3",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "/home/fallleaf/project/secondbrain",
      "env": {
        "PYTHONPATH": "/home/fallleaf/project/secondbrain"
      }
    }
  }
}
```

## 🧪 测试连接

### 方法 1: 使用 mcp-cli
```bash
mcp-cli secondbrain
```

### 方法 2: 手动测试
```bash
cd ~/project/secondbrain
echo '{"jsonrpc":"2.0","id":1,"method":"list_tools","params":{}}' | \
  PYTHONPATH=. python3 -m src.server
```

## 📊 可用工具列表

1. `semantic_search` - 语义搜索
2. `read_note` - 读取笔记
3. `list_notes` - 列出笔记
4. `write_note` - 写入笔记
5. `delete_note` - 删除笔记
6. `move_note` - 移动笔记
7. `search_notes` - 关键词搜索
8. `get_index_stats` - 索引统计
9. `rebuild_semantic_index` - 重建索引
10. `get_priority_config` - 获取优先级配置
11. `get_note_info` - 获取笔记信息
12. `get_note_tags` - 获取笔记标签
13. `get_note_links` - 获取链接信息
14. `get_backlinks` - 获取反向链接
15. `find_broken_links` - 查找断裂链接
16. `find_orphaned_notes` - 查找孤立笔记
17. `set_note_priority` - 设置笔记优先级
18. `list_tags` - 列出所有标签

## 🔍 故障排查

### 问题 1: 配置加载失败
```bash
# 检查配置文件是否存在
ls -la ~/.config/secondbrain/config.yaml

# 检查配置语法
python3 -c "from src.config.settings import load_config; print(load_config())"
```

### 问题 2: 数据库连接失败
```bash
# 检查数据库文件
ls -la ~/.local/share/secondbrain/semantic_index.db

# 重建索引
python3 scripts/build_index.py
```

### 问题 3: 工具调用失败
```bash
# 查看详细日志
tail -f ~/.local/share/secondbrain/mcp.log
```

## 📚 参考文档

- [SecondBrain README](~/project/secondbrain/README.md)
- [配置示例](~/project/secondbrain/config.example.yaml)
- [实现计划](~/project/secondbrain/IMPLEMENTATION_PLAN.md)
