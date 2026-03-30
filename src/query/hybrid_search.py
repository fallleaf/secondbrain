"""
混合检索模块
使用 RRF (Reciprocal Rank Fusion) 算法融合语义和关键词搜索结果
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from .models import SearchResult
from .semantic_search import SemanticSearch
from .keyword_search import KeywordSearch


class HybridSearch:
    """混合检索类"""
    
    def __init__(self, db_path: str, k: float = 60.0):
        """
        初始化混合检索
        
        Args:
            db_path: 数据库路径
            k: RRF 常数（默认 60）
        """
        self.db_path = db_path
        self.k = k
        self.semantic = SemanticSearch(db_path)
        self.keyword = KeywordSearch(db_path)
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        执行混合检索
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数
            semantic_weight: 语义搜索权重
            keyword_weight: 关键词搜索权重
            filters: 过滤条件
        
        Returns:
            List[SearchResult]: 融合后的搜索结果
        """
        # 1. 执行语义搜索
        semantic_results = self.semantic.search(query, top_k=top_k * 2, filters=filters)
        
        # 2. 执行关键词搜索
        keyword_results = self.keyword.search(query, top_k=top_k * 2, filters=filters)
        
        # 3. RRF 融合
        fused_results = self._rrf_fusion(
            semantic_results,
            keyword_results,
            semantic_weight,
            keyword_weight
        )
        
        return fused_results[:top_k]
    
    def _rrf_fusion(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.5
    ) -> List[SearchResult]:
        """
        Reciprocal Rank Fusion (RRF) 融合算法
        
        RRF 公式：score = Σ (weight / (k + rank))
        
        Args:
            semantic_results: 语义搜索结果
            keyword_results: 关键词搜索结果
            semantic_weight: 语义搜索权重
            keyword_weight: 关键词搜索权重
        
        Returns:
            融合后的结果列表
        """
        # 构建文档 ID 到分数的映射
        doc_scores: Dict[str, float] = defaultdict(float)
        doc_info: Dict[str, SearchResult] = {}
        
        # 处理语义结果
        for rank, result in enumerate(semantic_results):
            doc_id = result.doc_id
            rrf_score = semantic_weight / (self.k + rank + 1)
            doc_scores[doc_id] += rrf_score
            doc_info[doc_id] = result
        
        # 处理关键词结果
        for rank, result in enumerate(keyword_results):
            doc_id = result.doc_id
            rrf_score = keyword_weight / (self.k + rank + 1)
            doc_scores[doc_id] += rrf_score
            
            # 如果文档不在 doc_info 中，使用关键词结果的信息
            if doc_id not in doc_info:
                doc_info[doc_id] = result
        
        # 按分数降序排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 构建最终结果
        fused_results = []
        for doc_id, total_score in sorted_docs:
            result = doc_info[doc_id]
            result.score = total_score
            result.source = "hybrid"
            fused_results.append(result)
        
        return fused_results
    
    def search_with_weights(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        带权重的混合搜索
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数
            filters: 过滤条件
            **kwargs: 其他参数（semantic_weight, keyword_weight）
        
        Returns:
            List[SearchResult]: 搜索结果
        """
        semantic_weight = kwargs.get("semantic_weight", 0.5)
        keyword_weight = kwargs.get("keyword_weight", 0.5)
        
        return self.search(
            query,
            top_k=top_k,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            filters=filters
        )


# 测试
if __name__ == "__main__":
    import os
    
    db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
    
    if not os.path.exists(db_path):
        print(f"数据库不存在：{db_path}")
        exit(1)
    
    searcher = HybridSearch(db_path)
    
    print("🔍 测试混合检索...")
    results = searcher.search("人工智能", top_k=5)
    
    print(f"\n找到 {len(results)} 个结果:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.file_path} (score: {result.score:.4f})")
        print(f"   Source: {result.source}")
        print(f"   Content: {result.content[:100]}...")
        print()
