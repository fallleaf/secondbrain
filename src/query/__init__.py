"""
查询模块
统一查询接口和搜索功能
"""

from .models import (
    SearchResult,
    FilterOptions,
    NoteInfo,
    LinkInfo,
    TagInfo,
    IndexStats,
    SearchMode
)
from .cache import QueryCache, get_query_cache, reset_query_cache
from .filters import QueryFilters, build_tag_filter_sql
from .semantic_search import SemanticSearch
from .keyword_search import KeywordSearch
from .hybrid_search import HybridSearch
from .query_engine import SecondBrainQuery
from .metadata import MetadataManager
from .index_mgmt import IndexManager

__all__ = [
    # 数据模型
    "SearchResult",
    "FilterOptions",
    "NoteInfo",
    "LinkInfo",
    "TagInfo",
    "IndexStats",
    "SearchMode",
    
    # 缓存
    "QueryCache",
    "get_query_cache",
    "reset_query_cache",
    
    # 过滤器
    "QueryFilters",
    "build_tag_filter_sql",
    
    # 搜索模块
    "SemanticSearch",
    "KeywordSearch",
    "HybridSearch",
    
    # 主查询引擎
    "SecondBrainQuery",
    
    # 元数据管理
    "MetadataManager",
    
    # 索引管理
    "IndexManager"
]
