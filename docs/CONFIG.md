# SecondBrain 配置指南

## 快速开始

### 1. 安装依赖
```bash
cd ~/project/secondbrain
source ~/project/venv/nanobot/bin/activate
pip install -e .
```

### 2. 创建配置文件
```bash
# 创建配置目录
mkdir -p ~/.config/secondbrain

# 复制配置模板
cp config.example.yaml ~/.config/secondbrain/config.yaml
cp priority_config.example.yaml ~/.config/secondbrain/priority_config.yaml
```

### 3. 编辑配置
编辑 `~/.config/secondbrain/config.yaml`:
```yaml
vaults:
  - path: "~/NanobotMemory"  # 你的 Obsidian Vault 路径
    name: "personal"
    enabled: true

index:
  semantic:
    enabled: true
    model: "BAAI/bge-small-zh-v1.5"  # 默认模型
    chunk_size: 800
    chunk_overlap: 150
    db_path: "~/.local/share/secondbrain/semantic_index.db"
```

### 4. 初始化索引
```bash
# 首次运行需要构建索引
cd ~/project/secondbrain
python3 scripts/build_index.py
```

### 5. 启动 MCP 服务器
```bash
# 开发模式
python -m src.server

# 或作为 MCP 服务器
secondbrain-mcp
```

## 详细配置

### Vault 配置

#### 多 Vault 支持
```yaml
vaults:
  - path: "~/NanobotMemory"
    name: "personal"
    enabled: true
  - path: "~/work/vault"
    name: "work"
    enabled: true
  - path: "~/archive/old-vault"
    name: "archive"
    enabled: false  # 禁用
```

#### Vault 路径规则
- 支持 `~` 展开
- 支持绝对路径
- 必须是有效的 Obsidian Vault (包含 `.obsidian` 目录)

### 索引配置

#### 语义索引
```yaml
index:
  semantic:
    enabled: true
    model: "BAAI/bge-small-zh-v1.5"  # 支持的模型
    chunk_size: 800  # 分块大小 (字符)
    chunk_overlap: 150  # 重叠部分
    db_path: "~/.local/share/secondbrain/semantic_index.db"
```

**支持的模型**:
- `BAAI/bge-small-zh-v1.5` (推荐，512 维)
- `BAAI/bge-base-zh-v1.5` (768 维)
- `BAAI/bge-large-zh-v1.5` (1024 维)

**分块策略**:
- `chunk_size`: 每个块的最大字符数 (建议 500-1000)
- `chunk_overlap`: 块之间的重叠字符数 (建议 100-200)

#### 关键词索引
```yaml
index:
  keyword:
    enabled: true
    backend: "sqlite_fts5"  # 或 "bm25"
    db_path: "~/.local/share/secondbrain/keyword_index.db"
```

### 优先级配置

#### 优先级级别
```yaml
levels:
  - priority: 9
    tags: ["central_gov", "national"]
    description: "国家级文件"
    retention_days: -1  # -1 表示永久
    weight: 2.0
  - priority: 7
    tags: ["ministry_gov", "provincial"]
    description: "部委/省级文件"
    retention_days: 3650  # 10 年
    weight: 1.6
  - priority: 5
    tags: ["company", "project"]
    description: "公司/项目文档"
    retention_days: 1095  # 3 年
    weight: 1.2
  - priority: 3
    tags: ["personal_work"]
    description: "个人工作笔记"
    retention_days: 365  # 1 年
    weight: 1.0
  - priority: 1
    tags: ["web", "temp"]
    description: "网络收集/临时"
    retention_days: 90
    weight: 0.8

default_priority: 3
```

**优先级说明**:
- **9**: 国家级/中央政府文件 (永久保留，权重 2.0)
- **7**: 部委/省级文件 (10 年，权重 1.6)
- **5**: 公司/项目文档 (3 年，权重 1.2)
- **3**: 个人工作笔记 (1 年，权重 1.0)
- **1**: 网络收集/临时文件 (90 天，权重 0.8)

### 安全配置
```yaml
security:
  max_read_size: 1048576  # 最大文件大小 (1MB)
  max_batch_size: 20  # 批量操作最大数量
  require_confirm_delete: true  # 删除前确认
  excluded_dirs: [".obsidian", ".trash", ".git", "__pycache__"]
```

### 日志配置
```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "~/.local/share/secondbrain/mcp.log"
  max_size: 10485760  # 10MB
  backup_count: 5  # 保留 5 个备份文件
```

## 环境变量

支持以下环境变量覆盖配置:

```bash
# 覆盖 Vault 路径
export SECOND_BRAIN_VAULT_PATH="~/custom/vault"

# 覆盖日志级别
export SECOND_BRAIN_LOG_LEVEL="DEBUG"

# 覆盖嵌入模型
export SECOND_BRAIN_INDEX_MODEL="BAAI/bge-base-zh-v1.5"
```

## 自动增量索引

### 配置定时任务
```bash
# 使用 cron 工具
nanobot cron add \
  --cron "0 2 * * *" \
  --message "自动执行 SecondBrain 增量索引" \
  --tz "Asia/Shanghai"
```

### 手动运行
```bash
cd ~/project/secondbrain
source ~/project/venv/nanobot/bin/activate
python3 scripts/auto_detect_and_index.py
```

### 日志查看
```bash
tail -f ~/.local/share/secondbrain/logs/auto_index.log
```

## 性能优化

### 1. 调整分块大小
```yaml
index:
  semantic:
    chunk_size: 600  # 减小分块，提高精度
    chunk_overlap: 100
```

### 2. 启用硬件加速
```python
# 在代码中设置
embedder = Embedder(
    model_name="BAAI/bge-small-zh-v1.5",
    device="cuda"  # 或 "mps" (Mac), "cpu"
)
```

### 3. 批量操作
```python
# 使用批量 API
tools.batch_write_notes([
    {"path": "note1.md", "content": "..."},
    {"path": "note2.md", "content": "..."}
])
```

### 4. 索引优化
```bash
# 定期重建索引 (清理碎片)
python3 scripts/build_index.py --full
```

## 故障排除

### 问题 1: 模型加载失败
**症状**: `OSError: Cannot find model`
**解决**:
```bash
# 手动下载模型
python3 -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-zh-v1.5')"

# 或检查网络连接
curl -I https://huggingface.co
```

### 问题 2: 索引损坏
**症状**: 搜索返回空结果或错误
**解决**:
```bash
# 重建索引
python3 scripts/build_index.py --full

# 或删除数据库重新创建
rm ~/.local/share/secondbrain/semantic_index.db
python3 scripts/build_index.py
```

### 问题 3: 性能下降
**症状**: 搜索变慢
**解决**:
```yaml
# 优化配置
index:
  semantic:
    chunk_size: 500  # 减小分块
  keyword:
    backend: "sqlite_fts5"  # 使用更快的后端
```

### 问题 4: 权限错误
**症状**: `PermissionError: [Errno 13]`
**解决**:
```bash
# 检查目录权限
ls -la ~/NanobotMemory
chmod -R u+rwx ~/NanobotMemory

# 检查数据库权限
ls -la ~/.local/share/secondbrain/
chmod -R u+rwx ~/.local/share/secondbrain/
```

## 高级配置

### 自定义分块策略
```python
from src.index import Chunker

class CustomChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        # 自定义分块逻辑
        paragraphs = text.split('\n\n')
        # ... 自定义逻辑
        return chunks
```

### 自定义优先级权重
```python
from src.config import load_config

config = load_config()
# 动态调整权重
for level in config.priority.levels:
    if level.priority == 9:
        level.weight = 2.5  # 提高国家级文件权重
```

### 集成 MCP 客户端
```json
// ~/.config/nanobot/config.json
{
  "mcpServers": {
    "secondbrain": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "src.server"],
      "cwd": "/home/fallleaf/project/secondbrain",
      "env": { "PYTHONPATH": "/home/fallleaf/project/secondbrain" },
      "toolTimeout": 120
    }
  }
}
```

## 参考

- [API 文档](API.md)
- [部署指南](DEPLOY.md)
- [架构设计](ARCHITECTURE.md)
- [变更日志](../CHANGELOG.md)
