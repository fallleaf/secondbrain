"""
查询缓存模块
使用 LRU 缓存机制提高查询性能
"""

import hashlib
import json
import time
from typing import Any, Optional, List
from collections import OrderedDict
from threading import Lock


class LRUCache:
    """LRU 缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化 LRU 缓存
        
        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在则返回 None
        """
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Any, max_size: int = None):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            max_size: 最大缓存条目数（可选）
        """
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            
            # 检查是否超过最大容量
            if len(self.cache) > (max_size or self.max_size):
                # 删除最旧的条目
                self.cache.popitem(last=False)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
        
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def invalidate_pattern(self, pattern: str):
        """
        按模式清除缓存（支持通配符）
        
        Args:
            pattern: 匹配模式（如 "*search*"）
        """
        with self.lock:
            if pattern == "*":
                self.cache.clear()
                return
            
            # 简单通配符匹配
            import fnmatch
            keys_to_delete = [
                key for key in self.cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            for key in keys_to_delete:
                del self.cache[key]
    
    def __len__(self) -> int:
        """返回缓存大小"""
        return len(self.cache)
    
    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self.cache


class QueryCache:
    """查询缓存管理器"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        初始化查询缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self.cache = LRUCache(max_size)
        self.default_ttl = default_ttl
        self.ttl_cache: OrderedDict = OrderedDict()  # 存储过期时间
        self.lock = Lock()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            缓存键（MD5 哈希）
        """
        # 序列化参数
        data = {
            "args": args,
            "kwargs": kwargs
        }
        serialized = json.dumps(data, sort_keys=True, default=str)
        
        # 生成 MD5 哈希
        return hashlib.md5(serialized.encode()).hexdigest()
    
    def get(self, *args, **kwargs) -> Optional[Any]:
        """
        获取缓存结果
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            缓存结果，如果不存在或已过期则返回 None
        """
        key = self._generate_key(*args, **kwargs)
        
        with self.lock:
            # 检查是否过期
            if key in self.ttl_cache:
                expire_time = self.ttl_cache[key]
                if time.time() > expire_time:
                    # 已过期，删除
                    self.delete(key)
                    return None
            
            return self.cache.get(key)
    
    def set(self, value: Any, *args, ttl: int = None, **kwargs) -> None:
        """
        设置缓存结果
        
        Args:
            value: 缓存值
            *args: 位置参数
            **kwargs: 关键字参数
            ttl: 过期时间（秒）
        """
        key = self._generate_key(*args, **kwargs)
        ttl = ttl or self.default_ttl
        
        with self.lock:
            self.cache.set(key, value)
            self.ttl_cache[key] = time.time() + ttl
    
    def delete(self, *args, **kwargs) -> bool:
        """
        删除缓存项
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            是否成功删除
        """
        key = self._generate_key(*args, **kwargs)
        
        with self.lock:
            deleted = self.cache.delete(key)
            if key in self.ttl_cache:
                del self.ttl_cache[key]
            return deleted
    
    def invalidate(self, pattern: str = None):
        """
        清除缓存
        
        Args:
            pattern: 匹配模式（如 "*search*"），None 表示清空所有
        """
        with self.lock:
            if pattern is None or pattern == "*":
                self.cache.clear()
                self.ttl_cache.clear()
            else:
                # 按模式清除
                import fnmatch
                keys_to_delete = [
                    key for key in self.ttl_cache.keys()
                    if fnmatch.fnmatch(key, pattern)
                ]
                for key in keys_to_delete:
                    self.cache.delete(key)
                    del self.ttl_cache[key]
    
    def cleanup_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的条目数
        """
        current_time = time.time()
        deleted_count = 0
        
        with self.lock:
            expired_keys = [
                key for key, expire_time in self.ttl_cache.items()
                if current_time > expire_time
            ]
            
            for key in expired_keys:
                self.cache.delete(key)
                del self.ttl_cache[key]
                deleted_count += 1
        
        return deleted_count
    
    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            current_time = time.time()
            expired_count = sum(
                1 for expire_time in self.ttl_cache.values()
                if current_time > expire_time
            )
            
            return {
                "size": len(self.cache),
                "ttl_entries": len(self.ttl_cache),
                "expired": expired_count,
                "hit_rate": "N/A"  # 需要额外统计
            }


# 全局缓存实例
_cache_instance: Optional[QueryCache] = None


def get_query_cache(max_size: int = 1000, default_ttl: int = 300) -> QueryCache:
    """
    获取全局查询缓存实例
    
    Args:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间（秒）
    
    Returns:
        QueryCache 实例
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = QueryCache(max_size, default_ttl)
    return _cache_instance


def reset_query_cache():
    """重置全局缓存（用于测试）"""
    global _cache_instance
    if _cache_instance:
        _cache_instance.invalidate()
        _cache_instance = None
