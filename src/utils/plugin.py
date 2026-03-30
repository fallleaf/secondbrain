"""
插件系统

提供可扩展的插件架构，支持动态加载和管理插件
"""

import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)


class Plugin(ABC):
    """插件基类"""

    def __init__(self):
        self.info: Optional[PluginInfo] = None
        self._hooks: Dict[str, List[Callable]] = {}

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化插件

        Args:
            config: 插件配置
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """关闭插件"""
        pass

    def register_hook(self, event: str, callback: Callable) -> None:
        """
        注册钩子

        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def get_hooks(self, event: str) -> List[Callable]:
        """
        获取钩子

        Args:
            event: 事件名称

        Returns:
            List[Callable]: 回调函数列表
        """
        return self._hooks.get(event, [])


class PluginManager:
    """插件管理器"""

    # 定义插件钩子事件
    EVENTS = {
        # 索引事件
        "on_index_start": "索引开始",
        "on_index_end": "索引结束",
        "on_document_added": "文档添加",
        "on_document_updated": "文档更新",
        "on_document_deleted": "文档删除",

        # 搜索事件
        "on_search_start": "搜索开始",
        "on_search_end": "搜索结束",
        "on_search_result": "搜索结果",

        # 系统事件
        "on_plugin_load": "插件加载",
        "on_plugin_unload": "插件卸载",
        "on_config_change": "配置变更",
    }

    def __init__(self, plugin_dir: Optional[str] = None):
        """
        初始化插件管理器

        Args:
            plugin_dir: 插件目录
        """
        self.plugin_dir = Path(plugin_dir or "~/.local/share/secondbrain/plugins").expanduser()
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}

        # 初始化钩子
        for event in self.EVENTS:
            self._hooks[event] = []

    def load_plugin(self, plugin_path: str) -> bool:
        """
        加载插件

        Args:
            plugin_path: 插件路径

        Returns:
            bool: 是否成功加载
        """
        try:
            # 添加插件目录到 Python 路径
            plugin_dir = Path(plugin_path).parent
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir))

            # 动态导入插件模块
            module_name = Path(plugin_path).stem
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找插件类
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Plugin) and obj != Plugin:
                    plugin_class = obj
                    break

            if plugin_class is None:
                return False

            # 实例化插件
            plugin = plugin_class()

            # 检查插件信息
            if not hasattr(plugin, 'info') or plugin.info is None:
                return False

            # 初始化插件
            plugin.initialize({})

            # 注册插件
            self._plugins[plugin.info.name] = plugin

            # 注册钩子
            for event, callbacks in plugin._hooks.items():
                for callback in callbacks:
                    self.register_hook(event, callback)

            # 触发插件加载事件
            self.trigger_event("on_plugin_load", plugin.info.name)

            return True

        except Exception as e:
            print(f"加载插件失败：{e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 是否成功卸载
        """
        if plugin_name not in self._plugins:
            return False

        try:
            plugin = self._plugins[plugin_name]

            # 关闭插件
            plugin.shutdown()

            # 移除钩子
            for event, callbacks in plugin._hooks.items():
                for callback in callbacks:
                    if callback in self._hooks.get(event, []):
                        self._hooks[event].remove(callback)

            # 移除插件
            del self._plugins[plugin_name]

            # 触发插件卸载事件
            self.trigger_event("on_plugin_unload", plugin_name)

            return True

        except Exception as e:
            print(f"卸载插件失败：{e}")
            return False

    def load_all_plugins(self) -> int:
        """
        加载所有插件

        Returns:
            int: 成功加载的插件数量
        """
        count = 0

        # 查找所有插件文件
        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            if self.load_plugin(str(plugin_file)):
                count += 1

        return count

    def register_hook(self, event: str, callback: Callable) -> None:
        """
        注册钩子

        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def trigger_event(self, event: str, *args, **kwargs) -> None:
        """
        触发事件

        Args:
            event: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        if event not in self._hooks:
            return

        for callback in self._hooks[event]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"执行钩子失败：{e}")

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        获取插件

        Args:
            plugin_name: 插件名称

        Returns:
            Optional[Plugin]: 插件实例
        """
        return self._plugins.get(plugin_name)

    def get_all_plugins(self) -> List[PluginInfo]:
        """
        获取所有插件信息

        Returns:
            List[PluginInfo]: 插件信息列表
        """
        return [plugin.info for plugin in self._plugins.values() if plugin.info]

    def get_hooks_info(self) -> Dict[str, List[str]]:
        """
        获取钩子信息

        Returns:
            Dict[str, List[str]]: 钩子信息
        """
        info = {}
        for event, callbacks in self._hooks.items():
            info[event] = [callback.__name__ for callback in callbacks]
        return info


# 全局插件管理器实例
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager(plugin_dir: Optional[str] = None) -> PluginManager:
    """
    获取全局插件管理器实例

    Args:
        plugin_dir: 插件目录

    Returns:
        PluginManager: 插件管理器实例
    """
    global _plugin_manager

    if _plugin_manager is None:
        _plugin_manager = PluginManager(plugin_dir)

    return _plugin_manager


# 装饰器：注册钩子
def hook(event: str):
    """
    钩子装饰器

    Args:
        event: 事件名称

    Returns:
        装饰器函数
    """
    def decorator(func):
        # 在插件初始化时注册钩子
        func._hook_event = event
        return func
    return decorator


if __name__ == "__main__":
    # 测试插件系统

    # 创建示例插件
    example_plugin_code = '''
from src.utils.plugin import Plugin, PluginInfo, hook

class ExamplePlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.info = PluginInfo(
            name="example",
            version="1.0.0",
            description="示例插件",
            author="SecondBrain"
        )

    def initialize(self, config):
        print(f"初始化插件：{self.info.name}")

    def shutdown(self):
        print(f"关闭插件：{self.info.name}")

    @hook("on_search_start")
    def on_search_start(self, query):
        print(f"搜索开始：{query}")
'''

    # 保存示例插件
    plugin_dir = Path("~/.local/share/secondbrain/plugins").expanduser()
    plugin_dir.mkdir(parents=True, exist_ok=True)

    example_plugin_path = plugin_dir / "example_plugin.py"
    with open(example_plugin_path, 'w', encoding='utf-8') as f:
        f.write(example_plugin_code)

    # 测试插件管理器
    manager = get_plugin_manager()

    # 加载插件
    count = manager.load_all_plugins()
    print(f"✅ 加载了 {count} 个插件")

    # 获取插件信息
    plugins = manager.get_all_plugins()
    print("📦 插件列表：")
    for plugin in plugins:
        print(f"  - {plugin.name} v{plugin.version}: {plugin.description}")

    # 获取钩子信息
    hooks = manager.get_hooks_info()
    print("🔗 钩子信息：")
    for event, callbacks in hooks.items():
        if callbacks:
            print(f"  - {event}: {', '.join(callbacks)}")

    # 触发事件
    print("\n🔔 触发事件：")
    manager.trigger_event("on_search_start", "测试查询")

    # 卸载插件
    manager.unload_plugin("example")
    print("✅ 插件已卸载")

    print("✅ 插件系统测试完成")
