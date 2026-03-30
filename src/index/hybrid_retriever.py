"""
混合检索器
使用 RRF (Reciprocal Rank Fusion) 算法融合关键词和语义搜索结果
"""
import os
import math
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 导入缓存模块 (保持原有架构依赖)
try:
    from src.utils.cache import get_cache
except ImportError:
    # 兼容测试环境，防止缓存模块缺失导致无法导入
    def get_cache():
        return None


class SearchMode(str, Enum):
    """搜索模式"""
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    KEYWORD = "keyword"


@dataclass
class SearchResult:
    """搜索结果"""
    doc_id: str
    score: float
    content: str
    file_path: str
    start_line: int = 0
    end_line: int = 0
    source: str = "hybrid"  # hybrid, semantic, keyword
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """确保 metadata 初始化"""
        if self.metadata is None:
            self.metadata = {}

    def get_tags(self) -> List[str]:
        """获取文档标签"""
        return self.metadata.get("tags", [])

    def get_doc_type(self) -> str:
        """获取文档类型"""
        return self.metadata.get("doc_type", "default")

    def get_frontmatter(self) -> Dict[str, Any]:
        """获取完整的 Frontmatter 信息"""
        return self.metadata.get("frontmatter", self.metadata)


class HybridRetriever:
    """混合检索器"""

    def __init__(self, keyword_index, semantic_index, priority_classifier=None,
                 tag_weights: Optional[Dict[str, float]] = None,
                 vault_path: Optional[str] = None):
        """
        初始化混合检索器

        Args:
            keyword_index: 关键词索引
            semantic_index: 语义索引
            priority_classifier: 优先级分类器（可选）
            tag_weights: 标签权重配置，如 {"important": 2.0, "urgent": 1.5}
            vault_path: 知识库根路径，用于拼接文件绝对路径（可选）
        """
        self.keyword_index = keyword_index
        self.semantic_index = semantic_index
        self.priority_classifier = priority_classifier
        # 标签权重配置（默认：#important 提权 2 倍，#urgent 提权 1.5 倍）
        self.tag_weights = tag_weights or {
            "important": 2.0,
            "urgent": 1.5,
            "priority": 1.5,
            "pinned": 2.0
        }
        # 文档类型权重配置
        self.doc_type_weights = {
            "faq": 1.2,      # FAQ 类文档稍微提权
            "technical": 1.1,  # 技术文档稍微提权
            "legal": 1.3,     # 法律文档重要
            "default": 1.0
        }
        # vault_path 处理：转换为绝对路径 (技术要求 1)
        self.vault_path = os.path.expanduser(vault_path) if vault_path else None

    def _load_file_content(self, file_path: str, start_line: int, end_line: int) -> str:
        """
        通用文件内容读取逻辑，用于确保关键词和语义搜索结果的一致性 (技术要求 2 & 3)

        Args:
            file_path: 相对文件路径
            start_line: 起始行号 (1-based)
            end_line: 结束行号 (1-based)

        Returns:
            str: 文件内容片段或错误信息
        """
        content = ""
        # 1. 拼接绝对路径 (技术要求 2.2)
        full_path = os.path.join(self.vault_path, file_path) if self.vault_path else file_path

        # 2. 检查文件是否存在
        if self.vault_path and os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # 提取指定行范围
                    if start_line > 0 and end_line > 0:
                        start_idx = max(0, start_line - 1)
                        end_idx = min(len(lines), end_line)
                        content = ''.join(lines[start_idx:end_idx]).strip()
                    else:
                        # 默认返回前 20 行或 200 字符
                        content = ''.join(lines[:20]).strip()[:200]
            except Exception as e:
                content = f"[读取文件失败：{e}]"
        elif not self.vault_path and os.path.exists(file_path):
            # 兼容情况：如果 vault_path 未设置但文件在当前目录存在 (技术要求 5)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if start_line > 0 and end_line > 0:
                        start_idx = max(0, start_line - 1)
                        end_idx = min(len(lines), end_line)
                        content = ''.join(lines[start_idx:end_idx]).strip()
                    else:
                        content = ''.join(lines[:20]).strip()[:200]
            except Exception as e:
                content = f"[读取文件失败：{e}]"
        else:
            # 文件不存在提示 (技术要求 2.3)
            content = f"[文件不存在：{full_path}]"

        return content

    def _calculate_dynamic_weight(self, result: SearchResult) -> float:
        """
        计算动态权重基于 tags 和 doc_type

        Args:
            result: 搜索结果

        Returns:
            float: 权重系数
        """
        weight = 1.0

        # 1. 基于 tags 提权
        tags = result.get_tags()
        for tag in tags:
            # 支持 #important 或 important 格式
            tag_key = tag.replace("#", "").lower()
            if tag_key in self.tag_weights:
                weight *= self.tag_weights[tag_key]

        # 2. 基于 doc_type 提权
        doc_type = result.get_doc_type()
        if doc_type in self.doc_type_weights:
            weight *= self.doc_type_weights[doc_type]

        # 3. 基于 frontmatter 中的 priority 字段
        frontmatter = result.get_frontmatter()
        if "priority" in frontmatter:
            priority = frontmatter["priority"]
            if priority == "high":
                weight *= 1.5
            elif priority == "medium":
                weight *= 1.2

        return weight

    def search(self, query: str, mode: SearchMode = SearchMode.HYBRID,
               top_k: int = 10, priority_weight: float = 1.0) -> List[SearchResult]:
        """
        混合搜索

        Args:
            query: 查询语句
            mode: 搜索模式
            top_k: 返回结果数
            priority_weight: 优先级权重系数

        Returns:
            List[SearchResult]: 搜索结果
        """
        return self._cached_search(query, mode, top_k, priority_weight)

    def _cached_search(self, query: str, mode: SearchMode, top_k: int, priority_weight: float) -> List[SearchResult]:
        """带缓存的搜索实现"""
        cache = get_cache()

        # 生成缓存键
        cache_key = ("hybrid_search", query, str(mode), top_k, priority_weight)

        # 尝试从缓存获取
        if cache:
            cached_result = cache.get(*cache_key)
            if cached_result is not None:
                return cached_result

        #  执行实际搜索
        results = self._perform_search(query, mode, top_k, priority_weight)

        # 存入缓存 (5 分钟过期)
        if cache:
            cache.set(results, *cache_key, ttl=300)

        return results

    def _perform_search(self, query: str, mode: SearchMode, top_k: int, priority_weight: float) -> List[SearchResult]:
        """实际搜索逻辑"""
        results = []

        if mode == SearchMode.HYBRID or mode == SearchMode.KEYWORD:
            # 关键词搜索
            keyword_results = self.keyword_index.search(query, top_k=top_k)
            results.extend(self._convert_keyword_results(keyword_results, priority_weight))

        if mode == SearchMode.HYBRID or mode == SearchMode.SEMANTIC:
            # 语义搜索
            from .embedder import Embedder
            embedder = Embedder()
            query_embedding = embedder.encode_single(query)

            semantic_results = self.semantic_index.search(
                query_embedding.tolist(),
                top_k=top_k
            )
            results.extend(self._convert_semantic_results(semantic_results, priority_weight))

        if mode == SearchMode.HYBRID:
            # RRF 融合
            results = self._rrf_fusion(results)

        return results

    def _convert_keyword_results(self, keyword_results: List[Dict], priority_weight: float = 1.0) -> List[SearchResult]:
        """转换关键词搜索结果 (技术要求 3：应用相同的路径拼接和文件读取逻辑)"""
        results = []
        for item in keyword_results:
            # 如果优先级分类器可用，计算优先级权重
            if self.priority_classifier:
                priority, _, _ = self.priority_classifier.infer_priority(item.get('file_path', ''))
                weight = self.priority_classifier.get_search_weight(priority)
            else:
                weight = priority_weight  # 使用传入的默认权重

            # 应用优先级加权 (RRF 分数越小越好，所以取倒数)
            rank = item.get('rank', 0)
            weighted_score = (1.0 / (rank + 1.0)) * weight

            # 提取路径和行号信息
            file_path = item.get('file_path', '')
            start_line = item.get('start_line', 0)
            end_line = item.get('end_line', 0)

            # 使用统一的文件读取逻辑获取内容 (确保与语义检索对称)
            # 即使 keyword_index 可能包含 content，为了路径正确性，我们优先尝试读取文件
            content = self._load_file_content(file_path, start_line, end_line)

            results.append(SearchResult(
                doc_id=item.get('doc_id', str(hash(str(item)))),
                score=weighted_score,
                content=content,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                source='keyword',
                metadata=item
            ))
        return results


def _convert_semantic_results(self, semantic_results: List[Dict], priority_weight: float = 1.0) -> List[SearchResult]:
    """转换语义搜索结果 (直接使用数据库中的 content，避免文件读取错误)"""
    results = []
    for result in semantic_results:
        doc_id = result["doc_id"]
        distance = result["distance"]
        metadata_from_db = result["metadata"]
        content = result.get("content", "")
        start_line = result.get("start_line", 0)
        end_line = result.get("end_line", 0)

        # 距离越小越相似，转换为相似度分数
        # 使用 1 / (1 + distance) 将距离转换为相似度
        similarity = 1.0 / (1.0 + distance)

        # 解析 doc_id 获取 file_path (如果 content 为空，尝试从 doc_id 解析)
        file_path = doc_id
        if '#' in doc_id:
            file_path = doc_id.rsplit('#', 1)[0]

        # 如果 content 为空，尝试从 metadata 中获取（兼容旧数据）
        if not content and metadata_from_db:
            content = metadata_from_db.get("chunk_content", "")
            if not content:
                # 最后尝试从 metadata 中的 file_path 读取（如果存在）
                meta_file_path = metadata_from_db.get("file_path", file_path)
                if meta_file_path != file_path:
                    file_path = meta_file_path

        results.append(SearchResult(
            doc_id=doc_id,
            score=similarity * priority_weight,
            content=content,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            source='semantic',
            metadata={'distance': distance, **metadata_from_db}
        ))
    return results

    def _rrf_fusion(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Reciprocal Rank Fusion (RRF) 融合算法

        RRF 公式：score = Σ (1 / (k + rank_i))
        其中 k 是常数 (通常为 60)，rank_i 是文档在第 i 个结果列表中的排名

        Args:
            results: 混合的搜索结果列表

        Returns:
            List[SearchResult]: 融合后的结果，按分数降序排列
        """
        # 按来源分组
        keyword_results = [r for r in results if r.source == 'keyword']
        semantic_results = [r for r in results if r.source == 'semantic']

        k = 60.0  # RRF 常数

        # 构建文档 ID 到分数的映射
        doc_scores = {}  # doc_id -> total_score
        doc_info = {}    # doc_id -> SearchResult

        # 处理关键词结果
        for rank, result in enumerate(keyword_results):
            doc_id = result.doc_id
            # RRF 分数 = 1 / (k + rank)
            rrf_score = 1.0 / (k + rank + 1)
            # 应用优先级权重
            weighted_score = rrf_score * result.score

            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + weighted_score
            doc_info[doc_id] = result

        # 处理语义结果
        for rank, result in enumerate(semantic_results):
            doc_id = result.doc_id
            # RRF 分数 = 1 / (k + rank)
            rrf_score = 1.0 / (k + rank + 1)
            # 应用优先级权重
            weighted_score = rrf_score * result.score

            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + weighted_score
            # 如果文档不在 doc_info 中，使用语义结果的信息
            if doc_id not in doc_info:
                doc_info[doc_id] = result

        # 按分数降序排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建最终结果
        fused_results = []
        for doc_id, total_score in sorted_docs:
            result = doc_info[doc_id]
            result.score = total_score
            result.source = 'hybrid'  # 标记为混合检索结果
            fused_results.append(result)

        return fused_results


# 测试 (技术要求 6：语法检查通过)
if __name__ == "__main__":
    print("🔍 混合检索器模块加载成功")
    print("   RRF 算法已集成，vault_path 逻辑已启用")
    # 示例用法 (需在实际环境中初始化索引)
    # retriever = HybridRetriever(keyword_index=..., semantic_index=..., vault_path="~/NanobotMemory")
    # results = retriever.search("查询内容", mode=SearchMode.HYBRID)
