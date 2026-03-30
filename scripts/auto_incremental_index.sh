#!/bin/bash
# SecondBrain 自动增量索引脚本
# 用途：定时任务 (cron) 调用
# 位置：~/project/secondbrain/scripts/auto_incremental_index.sh
# 虚拟环境：~/project/venv/nanobot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$HOME/project/venv/nanobot"
LOG_DIR="$HOME/.local/share/secondbrain/logs"
LOG_FILE="$LOG_DIR/auto_index_$(date +%Y%m%d_%H%M%S).log"

# 创建日志目录
mkdir -p "$LOG_DIR"

echo "========================================" | tee -a "$LOG_FILE"
echo "🚀 开始自动增量索引检测" | tee -a "$LOG_FILE"
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "虚拟环境：$VENV_PATH" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 激活虚拟环境
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo "✅ 虚拟环境已激活" | tee -a "$LOG_FILE"
else
    echo "⚠️ 虚拟环境不存在，使用系统 Python" | tee -a "$LOG_FILE"
fi

# 切换到项目目录
cd "$PROJECT_DIR"

# 执行增量索引 (自动处理变更)
echo "📝 执行增量索引..." | tee -a "$LOG_FILE"
if python3 scripts/auto_detect_and_index.py >> "$LOG_FILE" 2>&1; then
    echo "✅ 增量索引完成" | tee -a "$LOG_FILE"
else
    echo "❌ 增量索引失败，请检查日志" | tee -a "$LOG_FILE"
    exit 1
fi

echo "========================================" | tee -a "$LOG_FILE"
echo "🏁 自动增量索引结束" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
