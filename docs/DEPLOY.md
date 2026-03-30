# SecondBrain 部署指南

## 系统要求

### 硬件要求
- **CPU**: 双核以上 (推荐 4 核)
- **内存**: 2GB 以上 (推荐 4GB+)
- **存储**: 500MB 可用空间 (取决于索引大小)
- **GPU**: 可选 (CUDA 加速，非必需)

### 软件要求
- **操作系统**: Linux (推荐), macOS, Windows
- **Python**: 3.10+ (推荐 3.12)
- **依赖**: `fastembed`, `sqlite-vec`, `pydantic` 等

## 快速部署

### 1. 克隆项目
```bash
git clone https://github.com/fallleaf/secondbrain.git
cd secondbrain
```

### 2. 创建虚拟环境
```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. 安装依赖
```bash
# 开发模式 (推荐)
pip install -e ".[dev]"

# 或生产模式
pip install -e "."
```

### 4. 配置环境变量
```bash
# 创建 .env 文件
cat > .env << EOF
SECOND_BRAIN_VAULT_PATH=~/NanobotMemory
SECOND_BRAIN_CONFIG_PATH=~/.config/secondbrain/config.yaml
SECOND_BRAIN_LOG_LEVEL=INFO
EOF

# 加载环境变量
source .env
```

### 5. 初始化配置
```bash
# 创建配置目录
mkdir -p ~/.config/secondbrain
mkdir -p ~/.local/share/secondbrain

# 复制配置模板
cp config.example.yaml ~/.config/secondbrain/config.yaml
cp priority_config.example.yaml ~/.config/secondbrain/priority_config.yaml

# 编辑配置 (根据需要修改)
vim ~/.config/secondbrain/config.yaml
```

### 6. 构建索引
```bash
# 首次运行需要构建索引
python3 scripts/build_index.py

# 或使用增量构建
python3 scripts/auto_detect_and_index.py
```

### 7. 启动服务

#### 方式 1: 直接运行
```bash
python -m src.server
```

#### 方式 2: 作为 MCP 服务器
```bash
# 在 nanobot 配置中添加
{
  "mcpServers": {
    "secondbrain": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/secondbrain",
      "env": { "PYTHONPATH": "/path/to/secondbrain" }
    }
  }
}
```

#### 方式 3: Docker 部署
```bash
# 构建镜像
docker build -t secondbrain .

# 运行容器
docker run -d \
  --name secondbrain \
  -v ~/NanobotMemory:/data/vault \
  -v ~/.config/secondbrain:/data/config \
  -v ~/.local/share/secondbrain:/data/index \
  secondbrain:latest
```

## 生产环境部署

### 1. 使用 systemd 服务 (Linux)

创建服务文件 `/etc/systemd/system/secondbrain.service`:
```ini
[Unit]
Description=SecondBrain MCP Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/secondbrain
Environment="PATH=/path/to/secondbrain/venv/bin"
ExecStart=/path/to/secondbrain/venv/bin/python -m src.server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable secondbrain
sudo systemctl start secondbrain
sudo systemctl status secondbrain
```

### 2. 使用 Docker Compose

创建 `docker-compose.yml`:
```yaml
version: '3.8'

services:
  secondbrain:
    build: .
    container_name: secondbrain
    volumes:
      - ~/NanobotMemory:/data/vault
      - ~/.config/secondbrain:/data/config
      - ~/.local/share/secondbrain:/data/index
    environment:
      - SECOND_BRAIN_LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

运行:
```bash
docker-compose up -d
docker-compose logs -f
```

### 3. 使用 Kubernetes

创建 `deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secondbrain
spec:
  replicas: 1
  selector:
    matchLabels:
      app: secondbrain
  template:
    metadata:
      labels:
        app: secondbrain
    spec:
      containers:
      - name: secondbrain
        image: secondbrain:latest
        volumeMounts:
        - name: vault
          mountPath: /data/vault
        - name: config
          mountPath: /data/config
        - name: index
          mountPath: /data/index
      volumes:
      - name: vault
        hostPath:
          path: /mnt/data/vault
      - name: config
        hostPath:
          path: /mnt/data/config
      - name: index
        hostPath:
          path: /mnt/data/index
```

应用:
```bash
kubectl apply -f deployment.yaml
kubectl get pods
```

## 性能调优

### 1. 调整分块大小
```yaml
# config.yaml
index:
  semantic:
    chunk_size: 600  # 减小分块提高精度
    chunk_overlap: 100
```

### 2. 启用 GPU 加速
```python
# 在代码中设置
embedder = Embedder(
    model_name="BAAI/bge-small-zh-v1.5",
    device="cuda"  # 或 "mps" (Mac)
)
```

### 3. 优化数据库
```bash
# 定期优化 SQLite
sqlite3 ~/.local/share/secondbrain/semantic_index.db "VACUUM;"
sqlite3 ~/.local/share/secondbrain/keyword_index.db "VACUUM;"
```

### 4. 调整日志级别
```yaml
# 生产环境使用 WARNING
logging:
  level: WARNING
```

## 监控与日志

### 1. 查看日志
```bash
# 实时查看
tail -f ~/.local/share/secondbrain/mcp.log

# 查看性能日志
tail -f ~/.local/share/secondbrain/perf_logs/perf_*.json
```

### 2. 性能监控
```bash
# 获取性能统计
python3 -c "from src.utils.perf_monitor import get_perf_monitor; print(get_perf_monitor().get_stats())"
```

### 3. 健康检查
```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查索引状态
python3 scripts/check_index_status.py
```

## 备份与恢复

### 1. 备份索引
```bash
# 备份数据库
tar -czf secondbrain_backup_$(date +%Y%m%d).tar.gz \
  ~/.local/share/secondbrain/ \
  ~/.config/secondbrain/
```

### 2. 恢复索引
```bash
# 解压备份
tar -xzf secondbrain_backup_20260328.tar.gz -C ~/

# 重建索引 (可选)
python3 scripts/build_index.py
```

### 3. 定期备份
```bash
# 添加到 crontab
0 2 * * * tar -czf /backup/secondbrain_$(date +\%Y\%m\%d).tar.gz ~/.local/share/secondbrain/
```

## 故障排除

### 问题 1: 内存不足
**症状**: `MemoryError` 或 OOM
**解决**:
```bash
# 减小分块大小
chunk_size: 400

# 或增加内存
# 使用 swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 问题 2: 索引损坏
**症状**: 搜索异常或报错
**解决**:
```bash
# 删除索引重建
rm ~/.local/share/secondbrain/*.db
python3 scripts/build_index.py --full
```

### 问题 3: 模型下载失败
**症状**: `ConnectionError` 或超时
**解决**:
```bash
# 手动下载模型
python3 -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-zh-v1.5')"

# 或使用镜像
export HF_ENDPOINT=https://hf-mirror.com
```

### 问题 4: 权限错误
**症状**: `PermissionError`
**解决**:
```bash
# 修复权限
sudo chown -R $USER:$USER ~/.local/share/secondbrain/
sudo chown -R $USER:$USER ~/.config/secondbrain/
```

## 升级

### 1. 升级代码
```bash
cd ~/project/secondbrain
git pull origin main
pip install -e ".[dev]"
```

### 2. 迁移数据
```bash
# 备份旧数据
cp -r ~/.local/share/secondbrain ~/.local/share/secondbrain.backup

# 运行迁移脚本 (如果有)
python3 scripts/migrate.py
```

### 3. 验证升级
```bash
# 测试基本功能
python3 -c "from src.index import Embedder; e = Embedder(); print(e.encode(['test']).shape)"
```

## 参考

- [API 文档](API.md)
- [配置指南](CONFIG.md)
- [变更日志](../CHANGELOG.md)
