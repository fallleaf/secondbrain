# SecondBrain 插件系统文档

## 概述

SecondBrain 插件系统提供可扩展的架构，允许开发者通过插件扩展系统功能。

## 插件架构

### 核心组件

```
Plugin (基类)
    ↓
PluginManager (管理器)
    ↓
PluginInfo (插件信息)
```

### 插件生命周期

```
加载 → 初始化 → 运行 → 关闭 → 卸载
```

## 插件开发

### 创建插件

```python
from src.utils.plugin import Plugin, PluginInfo, hook

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.info = PluginInfo(
            name="my_plugin",
            version="1.0.0",
            description="我的插件",
            author="Your Name"
        )

    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化插件"""
        # 加载配置
        # 初始化资源
        pass

    def shutdown(self) -> None:
        """关闭插件"""
        # 释放资源
        pass

    @hook("on_search_start")
    def on_search_start(self, query: str, mode: str, top_k: int) -> None:
        """搜索开始时执行"""
        # 处理事件
        pass
```

### 可用钩子事件

| 事件名称 | 描述 | 参数 |
|---------|------|------|
| `on_index_start` | 索引开始 | - |
| `on_index_end` | 索引结束 | - |
| `on_document_added` | 文档添加 | doc_id, metadata |
| `on_document_updated` | 文档更新 | doc_id, metadata |
| `on_document_deleted` | 文档删除 | doc_id |
| `on_search_start` | 搜索开始 | query, mode, top_k |
| `on_search_end` | 搜索结束 | query, mode, result_count, duration_ms |
| `on_search_result` | 搜索结果 | query, results |
| `on_plugin_load` | 插件加载 | plugin_name |
| `on_plugin_unload` | 插件卸载 | plugin_name |
| `on_config_change` | 配置变更 | config |

### 插件配置

在 `~/.config/secondbrain/plugins.yaml` 中配置插件：

```yaml
plugins:
  search_logger:
    enabled: true
    config:
      log_dir: "~/.local/share/secondbrain/plugin_logs"

  priority_boost:
    enabled: true
    config:
      boost_rules:
        recent:
          days: 7
          boost: 1.2
        frequent:
          count: 5
          boost: 1.1
```

## 插件管理

### 加载插件

```python
from src.utils.plugin import get_plugin_manager

manager = get_plugin_manager()

# 加载单个插件
manager.load_plugin("/path/to/plugin.py")

# 加载所有插件
count = manager.load_all_plugins()
print(f"加载了 {count} 个插件")
```

### 卸载插件

```python
# 卸载插件
manager.unload_plugin("plugin_name")
```

### 获取插件信息

```python
# 获取所有插件
plugins = manager.get_all_plugins()
for plugin in plugins:
    print(f"{plugin.name} v{plugin.version}: {plugin.description}")

# 获取单个插件
plugin = manager.get_plugin("plugin_name")
```

### 触发事件

```python
# 触发事件
manager.trigger_event("on_search_start", "查询", "hybrid", 10)
```

## 内置插件

### 1. 搜索日志插件 (search_logger)

**功能**：记录所有搜索查询到日志文件

**配置**：
```yaml
search_logger:
  enabled: true
  config:
    log_dir: "~/.local/share/secondbrain/plugin_logs"
```

**日志格式**：
```json
{
  "timestamp": "2026-03-28T18:00:00",
  "event": "search_start",
  "query": "人工智能",
  "mode": "hybrid",
  "top_k": 10
}
```

### 2. 优先级增强插件 (priority_boost)

**功能**：根据时间自动调整笔记优先级

**配置**：
```yaml
priority_boost:
  enabled: true
  config:
    boost_rules:
      recent:
        days: 7
        boost: 1.2
      frequent:
        count: 5
        boost: 1.1
```

**提升规则**：
- 最近文档：7 天内创建的文档分数提升 1.2 倍
- 频繁文档：访问次数超过 5 次的文档分数提升 1.1 倍

## 插件开发最佳实践

### 1. 错误处理

```python
@hook("on_search_start")
def on_search_start(self, query: str, mode: str, top_k: int) -> None:
    try:
        # 处理事件
        pass
    except Exception as e:
        print(f"插件错误：{e}")
        # 不要抛出异常，避免影响其他插件
```

### 2. 资源管理

```python
def initialize(self, config: Dict[str, Any]) -> None:
    # 打开文件、数据库连接等
    self.log_file = open(config["log_file"], "a")

def shutdown(self) -> None:
    # 关闭文件、数据库连接等
    if self.log_file:
        self.log_file.close()
```

### 3. 性能优化

```python
@hook("on_search_result")
def on_search_result(self, query: str, results: list) -> None:
    # 只处理前 N 个结果
    for result in results[:10]:
        # 处理结果
        pass
```

### 4. 配置验证

```python
def initialize(self, config: Dict[str, Any]) -> None:
    # 验证配置
    required_keys = ["log_dir", "max_size"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"缺少必需的配置项：{key}")
```

## 插件测试

### 单元测试

```python
import pytest
from src.utils.plugin import Plugin, PluginInfo

class TestMyPlugin:
    def test_initialize(self):
        plugin = MyPlugin()
        plugin.initialize({})
        assert plugin.info is not None

    def test_shutdown(self):
        plugin = MyPlugin()
        plugin.initialize({})
        plugin.shutdown()
        # 验证资源已释放
```

### 集成测试

```python
from src.utils.plugin import get_plugin_manager

def test_plugin_loading():
    manager = get_plugin_manager()
    count = manager.load_all_plugins()
    assert count > 0

def test_plugin_hooks():
    manager = get_plugin_manager()
    manager.trigger_event("on_search_start", "测试", "hybrid", 10)
    # 验证钩子已执行
```

## 插件发布

### 插件目录结构

```
my_plugin/
├── __init__.py
├── plugin.py          # 插件主文件
├── config.yaml        # 默认配置
├── README.md          # 说明文档
└── tests/             # 测试文件
    └── test_plugin.py
```

### 插件清单

在 `plugins.yaml` 中声明插件：

```yaml
plugins:
  my_plugin:
    version: "1.0.0"
    description: "我的插件"
    author: "Your Name"
    repository: "https://github.com/yourname/my_plugin"
    license: "MIT"
```

## 故障排查

### 插件加载失败

1. 检查插件文件路径是否正确
2. 检查插件类是否继承自 `Plugin`
3. 检查插件信息是否完整
4. 查看错误日志

### 钩子未执行

1. 检查钩子装饰器是否正确使用
2. 检查事件名称是否正确
3. 检查插件是否已加载

### 性能问题

1. 检查插件是否有阻塞操作
2. 使用异步处理耗时操作
3. 限制处理的数据量

## 示例插件

### 完整示例

```python
"""
示例插件 - 统计插件
"""

from typing import Dict, Any
from collections import defaultdict
import json

from src.utils.plugin import Plugin, PluginInfo, hook


class StatsPlugin(Plugin):
    """统计插件"""

    def __init__(self):
        super().__init__()
        self.info = PluginInfo(
            name="stats",
            version="1.0.0",
            description="统计搜索和索引数据",
            author="SecondBrain"
        )
        self.stats = defaultdict(int)

    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化插件"""
        print(f"✅ 统计插件已初始化")

    def shutdown(self) -> None:
        """关闭插件"""
        print(f"📊 统计数据：{dict(self.stats)}")

    @hook("on_search_start")
    def on_search_start(self, query: str, mode: str, top_k: int) -> None:
        """搜索开始时统计"""
        self.stats["search_count"] += 1
        self.stats[f"search_{mode}"] += 1

    @hook("on_document_added")
    def on_document_added(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """文档添加时统计"""
        self.stats["document_count"] += 1


def create_plugin() -> StatsPlugin:
    """创建插件实例"""
    return StatsPlugin()
```

## 参考资料

- [插件系统源码](../src/utils/plugin.py)
- [示例插件](../plugins/)
- [MCP 协议文档](../docs/API.md)
