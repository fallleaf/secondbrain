"""
查询缓存模块

提供查询结果缓存功能，提高搜索性能
"""

import hashlib
import json
import time
from typing import Any, Optional, Dict
from functools import wraps
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: int = 3600  # 默认 1 小时过期

    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.timestamp > self.ttl


class QueryCache:
    """查询缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        初始化查询缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间 (秒)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}

    def _generate_key(self, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            str: 缓存键
        """
        # 将参数转换为字符串
        key_parts = []

        # 处理位置参数
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # 对于复杂对象，使用 JSON 序列化
                try:
                    key_parts.append(json.dumps(arg, sort_keys=True))
                except Exception:
                    key_parts.append(str(arg))

        # 处理关键字参数
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}={v}")
            else:
                try:
                    key_parts.append(f"{k}={json.dumps(v, sort_keys=True)}")
                except Exception:
                    key_parts.append(f"{k}={str(v)}")

        # 生成 MD5 哈希
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    def get(self, *args, **kwargs) -> Optional[Any]:
        """
        获取缓存值

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Optional[Any]: 缓存值，如果不存在或已过期则返回 None
        """
        key = self._generate_key(*args, **kwargs)

        if key not in self._cache:
            return None

        entry = self._cache[key]

        # 检查是否过期
        if entry.is_expired():
            del self._cache[key]
            return None

        return entry.value

    def set(self, value: Any, *args, ttl: Optional[int] = None, **kwargs) -> None:
        """
        设置缓存值

        Args:
            value: 缓存值
            *args: 位置参数
            ttl: 过期时间 (秒)，None 表示使用默认值
            **kwargs: 关键字参数
        """
        key = self._generate_key(*args, **kwargs)
        
        # 如果缓存已满，删除最旧的条目
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        # 设置缓存
        entry = CacheEntry(
            key=key,
            value=value,
            ttl=ttl or self.default_ttl
        )
        self._cache[key] = entry

    def _evict_oldest(self) -> None:
        """删除最旧的缓存条目"""
        if not self._cache:
            return

        # 找到最旧的条目
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
        del self._cache[oldest_key]

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "max_size": self.max_size,
            "default_ttl": self.default_ttl
        }


# 全局缓存实例
_global_cache: Optional[QueryCache] = None


def get_cache(max_size: int = 1000, default_ttl: int = 3600) -> QueryCache:
    """
    获取全局缓存实例

    Args:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间 (秒)

    Returns:
        QueryCache: 缓存实例
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = QueryCache(max_size, default_ttl)

    return _global_cache


    def cached(ttl: int = 3600, key_prefix: str = ""):
        """
        缓存装饰器

        Args:
            ttl: 过期时间 (秒)
            key_prefix: 键前缀

        Returns:
            装饰器函数
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache = get_cache()

                # 生成缓存键
                cache_key = (key_prefix, func.__name__, args, frozenset(kwargs.items()))

                # 尝试从缓存获取
                cached_result = cache.get(*cache_key)
                if cached_result is not None:
                    return cached_result

                # 执行函数
                result = func(*args, **kwargs)

                # 存入缓存
                cache.set(result, *cache_key, ttl=ttl)
                
                return result

            return wrapper

        return decorator


if __name__ == "__main__":
    # 测试查询缓存
    cache = QueryCache(max_size=10, default_ttl=60)

    # 测试设置和获取
    cache.set("测试值", ttl=10, query="人工智能", top_k=5)
    result = cache.get(query="人工智能", top_k=5)

    print("✅ 缓存测试")
    print(f"获取结果：{result}")

    # 测试缓存统计
    stats = cache.get_stats()
    print(f"缓存统计：{stats}")

# 测试缓存装饰器
# @cached(ttl=30, key_prefix="search")
# def expensive_search(query: str, top_k: int = 10):
#     print(f"执行搜索：{query}")
#     return [f"结果{i}" for i in range(top_k)]

# 第一次调用会执行函数
# result1 = expensive_search("测试查询", top_k=5)
# print(f"第一次调用：{result1}")

# 第二次调用会从缓存获取
# result2 = expensive_search("测试查询", top_k=5)
# print(f"第二次调用：{result2}")

# print("✅ 查询缓存测试完成")
