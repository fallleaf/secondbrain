"""
性能监控模块

记录索引构建、搜索等操作的性能指标
"""

import time
import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化性能监控器

        Args:
            log_dir: 日志存储目录
        """
        self.log_dir = Path(log_dir or "~/.local/share/secondbrain/perf_logs")
        self.log_dir = Path(os.path.expanduser(self.log_dir))
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._current_context: Optional[str] = None
        self._start_time: Optional[float] = None

    def start(self, operation: str) -> 'PerformanceMonitor':
        """
        开始计时

        Args:
            operation: 操作名称 (如 "index_build", "semantic_search")
        """
        self._current_context = operation
        self._start_time = time.time()
        return self  # 返回 self 以支持 with 语句

    def stop(self, metadata: Optional[Dict[str, Any]] = None) -> float:
        """
        停止计时并记录

        Args:
            metadata: 额外元数据 (如文档数量、结果数量等)

        Returns:
            耗时 (秒)
        """
        if self._start_time is None:
            raise RuntimeError("未调用 start()")

        elapsed = time.time() - self._start_time
        operation = self._current_context

        # 记录指标
        record = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "duration_sec": elapsed,
            "duration_ms": elapsed * 1000,
            "metadata": metadata or {}
        }

        if operation not in self.metrics:
            self.metrics[operation] = []

        self.metrics[operation].append(record)

        # 限制历史记录数量
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]

        # 日志
        logger.info(f"⏱️ {operation}: {elapsed*1000:.2f}ms")

        # 重置
        self._start_time = None
        self._current_context = None

        return elapsed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start_time:
            self.stop()

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        获取性能统计

        Args:
            operation: 操作名称，None 表示所有操作

        Returns:
            统计信息
        """
        if operation:
            records = self.metrics.get(operation, [])
        else:
            records = [r for ops in self.metrics.values() for r in ops]

        if not records:
            return {}

        durations = [r["duration_sec"] for r in records]

        stats = {
            "count": len(records),
            "total_sec": sum(durations),
            "avg_sec": sum(durations) / len(durations),
            "min_sec": min(durations),
            "max_sec": max(durations),
            "avg_ms": (sum(durations) / len(durations)) * 1000,
            "min_ms": min(durations) * 1000,
            "max_ms": max(durations) * 1000
        }

        # 百分位数
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        stats["p50_ms"] = sorted_durations[int(n * 0.5)] * 1000
        stats["p90_ms"] = sorted_durations[int(n * 0.9)] * 1000
        stats["p99_ms"] = sorted_durations[int(n * 0.99)] * 1000

        return stats

    def save_logs(self, filename: Optional[str] = None) -> str:
        """
        保存性能日志到文件

        Args:
            filename: 文件名，None 表示自动生成

        Returns:
            文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"perf_{timestamp}.json"

        filepath = self.log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 性能日志已保存：{filepath}")
        return str(filepath)

    def load_logs(self, filepath: str) -> None:
        """
        加载性能日志

        Args:
            filepath: 日志文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            self.metrics = json.load(f)

    def clear(self) -> None:
        """清除所有记录"""
        self.metrics.clear()
        logger.info("🗑️ 性能监控记录已清除")


# 全局实例
_perf_monitor = PerformanceMonitor()


def get_perf_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    return _perf_monitor


# 装饰器：自动监控函数性能
def monitor_performance(operation_name: Optional[str] = None):
    """
    性能监控装饰器

    Args:
        operation_name: 操作名称，None 使用函数名
    """
    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_perf_monitor()
            name = operation_name or func.__name__

            with monitor.start(name):
                try:
                    result = func(*args, **kwargs)
                    monitor.stop({"status": "success"})
                    return result
                except Exception as e:
                    monitor.stop({"status": "error", "error": str(e)})
                    raise

        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试
    monitor = get_perf_monitor()

    # 测试计时
    with monitor.start("test_operation"):
        time.sleep(0.1)
    monitor.stop({"test": "data"})

    # 测试装饰器
    @monitor_performance("decorated_func")
    def test_func():
        time.sleep(0.05)
        return "done"

    test_func()

    # 获取统计
    stats = monitor.get_stats("test_operation")
    print(f"统计：{stats}")

    # 保存日志
    monitor.save_logs()
