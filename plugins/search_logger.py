"""
示例插件 - 搜索日志插件

记录所有搜索查询到日志文件
"""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import json

from src.utils.plugin import Plugin, PluginInfo, hook


class SearchLoggerPlugin(Plugin):
    """搜索日志插件"""

    def __init__(self):
        super().__init__()
        self.info = PluginInfo(
            name="search_logger",
            version="1.0.0",
            description="记录所有搜索查询到日志文件",
            author="SecondBrain"
        )
        self.log_file: Path = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化插件"""
        # 获取日志文件路径
        log_dir = Path(config.get("log_dir", "~/.local/share/secondbrain/plugin_logs")).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = log_dir / "search_log.jsonl"

        print(f"✅ 搜索日志插件已初始化，日志文件：{self.log_file}")

    def shutdown(self) -> None:
        """关闭插件"""
        print(f"🔌 搜索日志插件已关闭")

    @hook("on_search_start")
    def on_search_start(self, query: str, mode: str, top_k: int) -> None:
        """搜索开始时记录"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "search_start",
            "query": query,
            "mode": mode,
            "top_k": top_k
        }
        self._write_log(log_entry)

    @hook("on_search_end")
    def on_search_end(self, query: str, mode: str, result_count: int, duration_ms: float) -> None:
        """搜索结束时记录"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "search_end",
            "query": query,
            "mode": mode,
            "result_count": result_count,
            "duration_ms": duration_ms
        }
        self._write_log(log_entry)

    @hook("on_search_result")
    def on_search_result(self, query: str, results: list) -> None:
        """搜索结果时记录"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "search_result",
            "query": query,
            "result_count": len(results),
            "top_results": [
                {
                    "doc_id": r.get("doc_id"),
                    "score": r.get("score")
                }
                for r in results[:5]
            ]
        }
        self._write_log(log_entry)

    def _write_log(self, entry: Dict[str, Any]) -> None:
        """写入日志"""
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')


# 插件工厂函数
def create_plugin() -> SearchLoggerPlugin:
    """创建插件实例"""
    return SearchLoggerPlugin()


if __name__ == "__main__":
    # 测试插件
    plugin = SearchLoggerPlugin()
    plugin.initialize({})

    # 模拟搜索事件
    plugin.on_search_start("人工智能", "hybrid", 10)
    plugin.on_search_end("人工智能", "hybrid", 5, 25.5)
    plugin.on_search_result("人工智能", [
        {"doc_id": "doc1", "score": 0.95},
        {"doc_id": "doc2", "score": 0.87}
    ])

    print("✅ 搜索日志插件测试完成")
