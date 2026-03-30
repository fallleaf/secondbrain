"""
查询过滤器模块
支持多种过滤条件：标签、文档类型、优先级、文件路径、时间范围
"""

from typing import List, Dict, Any, Optional, Tuple, Tuple as TupleType
from datetime import datetime
import sqlite3

from .models import FilterOptions


class QueryFilters:
    """查询过滤器"""
    
    def __init__(self):
        """初始化过滤器"""
        pass
    
    def apply(self, filters: Optional[Dict[str, Any]] = None) -> Tuple[List[str], List[Any]]:
        """
        应用过滤条件
        
        Args:
            filters: 过滤条件字典
                - tags: List[str]
                - doc_type: str
                - min_priority: int
                - max_priority: int
                - file_path: str
                - date_range: Tuple[datetime, datetime]
                - vault_name: str
        
        Returns:
            (conditions, params): 过滤条件和参数列表
        
        Example:
            >>> filters = {"tags": ["work", "important"], "doc_type": "technical"}
            >>> conditions, params = QueryFilters().apply(filters)
            >>> print(conditions)
            ['doc_id IN (SELECT dt.doc_id FROM document_tags dt JOIN tags t ON dt.tag_id = t.tag_id WHERE t.tag_name IN (?, ?))', 'doc_type = ?']
            >>> print(params)
            ['work', 'important', 'technical']
        """
        if not filters:
            return [], []
        
        conditions = []
        params = []
        
        # 1. 标签过滤
        if "tags" in filters:
            tags = filters["tags"]
            if tags:
                condition, tag_params = self._build_tag_filter(tags)
                conditions.append(condition)
                params.extend(tag_params)
        
        # 2. 文档类型过滤
        if "doc_type" in filters:
            conditions.append("doc_type = ?")
            params.append(filters["doc_type"])
        
        # 3. 优先级过滤
        if "min_priority" in filters:
            conditions.append("priority >= ?")
            params.append(filters["min_priority"])
        
        if "max_priority" in filters:
            conditions.append("priority <= ?")
            params.append(filters["max_priority"])
        
        # 4. 文件路径过滤
        if "file_path" in filters:
            conditions.append("file_path LIKE ?")
            params.append(f"%{filters['file_path']}%")
        
        # 5. 时间范围过滤
        if "date_range" in filters:
            date_range = filters["date_range"]
            if date_range and len(date_range) == 2:
                start_date, end_date = date_range
                if isinstance(start_date, datetime):
                    start_date = start_date.isoformat()
                if isinstance(end_date, datetime):
                    end_date = end_date.isoformat()
                
                conditions.append("updated_at BETWEEN ? AND ?")
                params.extend([start_date, end_date])
        
        # 6. Vault 名称过滤
        if "vault_name" in filters:
            conditions.append("vault_name = ?")
            params.append(filters["vault_name"])
        
        return conditions, params
    
    def _build_tag_filter(self, tags: List[str]) -> Tuple[str, List[str]]:
        """
        构建标签过滤条件
        
        Args:
            tags: 标签列表
        
        Returns:
            (condition, params): 过滤条件和参数
        """
        if not tags:
            return "1=1", []
        
        # 使用 IN 子查询
        placeholders = ",".join(["?" for _ in tags])
        condition = f"""
            doc_id IN (
                SELECT dt.doc_id FROM document_tags dt
                JOIN tags t ON dt.tag_id = t.tag_id
                WHERE t.tag_name IN ({placeholders})
            )
        """
        return condition, tags
    
    def build_sql_where(
        self,
        filters: Optional[Dict[str, Any]] = None,
        base_table: str = "documents"
    ) -> Tuple[str, List[Any]]:
        """
        构建完整的 WHERE 子句
        
        Args:
            filters: 过滤条件
            base_table: 基础表名
        
        Returns:
            (where_clause, params): WHERE 子句和参数
        """
        conditions, params = self.apply(filters)
        
        if not conditions:
            return "", []
        
        where_clause = "WHERE " + " AND ".join(conditions)
        return where_clause, params
    
    def apply_to_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        mode: str = "hybrid",
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        将过滤条件应用到搜索查询
        
        Args:
            query: 搜索关键词
            filters: 过滤条件
            mode: 搜索模式
            top_k: 返回结果数
        
        Returns:
            搜索参数字典
        """
        return {
            "query": query,
            "mode": mode,
            "top_k": top_k,
            "filters": filters or {}
        }


def build_tag_filter_sql(tags: List[str], mode: str = "any") -> Tuple[str, List[str]]:
    """
    构建标签过滤 SQL
    
    Args:
        tags: 标签列表
        mode: 匹配模式 (any/all)
    
    Returns:
        (sql, params): SQL 语句和参数
    """
    if not tags:
        return "1=1", []
    
    if mode == "all":
        # 必须包含所有标签
        placeholders = ",".join(["?" for _ in tags])
        sql = f"""
            doc_id IN (
                SELECT doc_id FROM document_tags dt
                JOIN tags t ON dt.tag_id = t.tag_id
                WHERE t.tag_name IN ({placeholders})
                GROUP BY doc_id
                HAVING COUNT(DISTINCT t.tag_name) = ?
            )
        """
        return sql, tags + [len(tags)]
    else:
        # 包含任意标签
        placeholders = ",".join(["?" for _ in tags])
        sql = f"""
            doc_id IN (
                SELECT dt.doc_id FROM document_tags dt
                JOIN tags t ON dt.tag_id = t.tag_id
                WHERE t.tag_name IN ({placeholders})
            )
        """
        return sql, tags


def build_priority_filter_sql(min_priority: int = None, max_priority: int = None) -> Tuple[str, List[int]]:
    """
    构建优先级过滤 SQL
    
    Args:
        min_priority: 最小优先级
        max_priority: 最大优先级
    
    Returns:
        (sql, params): SQL 语句和参数
    """
    conditions = []
    params = []
    
    if min_priority is not None:
        conditions.append("priority >= ?")
        params.append(min_priority)
    
    if max_priority is not None:
        conditions.append("priority <= ?")
        params.append(max_priority)
    
    if not conditions:
        return "1=1", []
    
    return " AND ".join(conditions), params


def build_file_path_filter_sql(file_path: str) -> Tuple[str, List[str]]:
    """
    构建文件路径过滤 SQL
    
    Args:
        file_path: 文件路径
    
    Returns:
        (sql, params): SQL 语句和参数
    """
    return "file_path LIKE ?", [f"%{file_path}%"]


# 测试
if __name__ == "__main__":
    # 测试标签过滤
    filters = QueryFilters()
    
    # 测试 1: 标签过滤
    conditions, params = filters.apply({"tags": ["work", "important"]})
    print("测试 1 - 标签过滤:")
    print(f"  条件：{conditions[0][:80]}...")
    print(f"  参数：{params}")
    
    # 测试 2: 组合过滤
    conditions, params = filters.apply({
        "tags": ["work"],
        "doc_type": "technical",
        "min_priority": 6
    })
    print("\n测试 2 - 组合过滤:")
    for i, cond in enumerate(conditions):
        print(f"  条件{i+1}: {cond}")
    print(f"  参数：{params}")
    
    # 测试 3: 无过滤
    conditions, params = filters.apply({})
    print("\n测试 3 - 无过滤:")
    print(f"  条件数：{len(conditions)}")
    print(f"  参数数：{len(params)}")
