"""
示例插件 - 优先级增强插件

根据时间自动调整笔记优先级
"""

from typing import Dict, Any
from datetime import datetime, timedelta
import json

from src.utils.plugin import Plugin, PluginInfo, hook


class PriorityBoostPlugin(Plugin):
    """优先级增强插件"""

    def __init__(self):
        super().__init__()
        self.info = PluginInfo(
            name="priority_boost",
            version="1.0.0",
            description="根据时间自动调整笔记优先级",
            author="SecondBrain"
        )
        self.boost_rules: Dict[str, Any] = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化插件"""
        # 加载提升规则
        self.boost_rules = config.get("boost_rules", {
            "recent": {
                "days": 7,
                "boost": 1.2
            },
            "frequent": {
                "count": 5,
                "boost": 1.1
            }
        })

        print(f"✅ 优先级增强插件已初始化")

    def shutdown(self) -> None:
        """关闭插件"""
        print(f"🔌 优先级增强插件已关闭")

    @hook("on_search_result")
    def on_search_result(self, query: str, results: list) -> None:
        """搜索结果时调整优先级"""
        for result in results:
            # 检查是否是最近创建的文档
            if "created_at" in result.get("metadata", {}):
                created_at = datetime.fromisoformat(result["metadata"]["created_at"])
                days_ago = (datetime.now() - created_at).days

                if days_ago < self.boost_rules["recent"]["days"]:
                    # 提升最近文档的分数
                    result["score"] *= self.boost_rules["recent"]["boost"]
                    result["metadata"]["boost_reason"] = "recent_document"

    @hook("on_document_added")
    def on_document_added(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """文档添加时记录"""
        # 添加创建时间
        metadata["created_at"] = datetime.now().isoformat()
        metadata["access_count"] = 0

    @hook("on_search_start")
    def on_search_start(self, query: str, mode: str, top_k: int) -> None:
        """搜索开始时记录查询"""
        # 这里可以记录查询频率，用于后续提升频繁访问的文档
        pass


# 插件工厂函数
def create_plugin() -> PriorityBoostPlugin:
    """创建插件实例"""
    return PriorityBoostPlugin()


if __name__ == "__main__":
    # 测试插件
    plugin = PriorityBoostPlugin()
    plugin.initialize({})

    # 模拟文档添加事件
    plugin.on_document_added("doc1", {"title": "测试文档"})

    # 模拟搜索结果事件
    results = [
        {
            "doc_id": "doc1",
            "score": 0.8,
            "metadata": {
                "created_at": (datetime.now() - timedelta(days=3)).isoformat()
            }
        },
        {
            "doc_id": "doc2",
            "score": 0.7,
            "metadata": {
                "created_at": (datetime.now() - timedelta(days=30)).isoformat()
            }
        }
    ]

    print("调整前：")
    for r in results:
        print(f"  {r['doc_id']}: {r['score']}")

    plugin.on_search_result("测试", results)

    print("调整后：")
    for r in results:
        print(f"  {r['doc_id']}: {r['score']} (原因: {r['metadata'].get('boost_reason', '无')})")

    print("✅ 优先级增强插件测试完成")
