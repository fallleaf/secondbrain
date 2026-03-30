# 动态权重调整示例代码
"""
在 hybrid_retriever.py 中，修改 _convert_keyword_results 和 _convert_semantic_results 方法

修改要点:
1. 确保 metadata 包含完整的 Frontmatter 信息（tags, doc_type 等）
2. 调用 _calculate_dynamic_weight() 计算动态权重
3. 将动态权重应用到最终分数

示例修改:
"""

# 修改 _convert_keyword_results 方法
def _convert_keyword_results(self, keyword_results: List[Dict], priority_weight: float = 1.0) -> List[SearchResult]:
    """转换关键词搜索结果"""
    results = []
    for item in keyword_results:
        # 构建完整的 metadata，包含 Frontmatter 信息
        metadata = item.copy()
        
        # 提取 tags 和 doc_type（如果存在于 item 中）
        if 'tags' not in metadata and 'frontmatter' in item:
            metadata['tags'] = item['frontmatter'].get('tags', [])
        if 'doc_type' not in metadata and 'frontmatter' in item:
            metadata['doc_type'] = item['frontmatter'].get('doc_type', 'default')
        
        # 计算基础权重
        base_weight = 1.0
        if self.priority_classifier:
            priority, _, _ = self.priority_classifier.infer_priority(item.get('file_path', ''))
            base_weight = self.priority_classifier.get_search_weight(priority)
        else:
            base_weight = priority_weight
        
        # 创建临时 SearchResult 用于计算动态权重
        temp_result = SearchResult(
            doc_id=item.get('doc_id', str(hash(str(item)))) ,
            score=0,
            content=item.get('content', ''),
            file_path=item.get('file_path', ''),
            start_line=item.get('start_line', 0),
            end_line=item.get('end_line', 0),
            source='keyword',
            metadata=metadata
        )
        
        # 计算动态权重（基于 tags 和 doc_type）
        dynamic_weight = self._calculate_dynamic_weight(temp_result)
        
        # 应用优先级加权
        rank = item.get('rank', 0)
        weighted_score = (1.0 / (rank + 1.0)) * base_weight * dynamic_weight

        results.append(SearchResult(
            doc_id=temp_result.doc_id,
            score=weighted_score,
            content=temp_result.content,
            file_path=temp_result.file_path,
            start_line=temp_result.start_line,
            end_line=temp_result.end_line,
            source='keyword',
            metadata=metadata
        ))
    return results

# 修改 _convert_semantic_results 方法
def _convert_semantic_results(self, semantic_results: List[Tuple[str, float]], priority_weight: float = 1.0) -> List[SearchResult]:
    """转换语义搜索结果"""
    results = []
    for doc_id, distance in semantic_results:
        # 距离越小越相似，转换为相似度分数
        similarity = 1.0 / (1.0 + distance)
        
        # 获取文档内容（需要从语义索引中获取）
        if '#' in doc_id:
            file_path, chunk_index = doc_id.rsplit('#', 1)
            start_line = int(chunk_index) * 10
            end_line = start_line + 10
            content = f"[语义搜索结果] {doc_id}"
        else:
            file_path = doc_id
            start_line = 0
            end_line = 0
            content = f"[语义搜索结果] {doc_id}"
        
        # 创建临时 metadata（实际应该从数据库获取完整的 frontmatter）
        metadata = {
            'distance': distance,
            'tags': [],  # 实际应该从索引中获取
            'doc_type': 'default'
        }
        
        # 创建临时 SearchResult 用于计算动态权重
        temp_result = SearchResult(
            doc_id=doc_id,
            score=similarity,
            content=content,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            source='semantic',
            metadata=metadata
        )
        
        # 计算动态权重
        dynamic_weight = self._calculate_dynamic_weight(temp_result)
        
        results.append(SearchResult(
            doc_id=doc_id,
            score=similarity * dynamic_weight,  # 应用动态权重
            content=content,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            source='semantic',
            metadata=metadata
        ))
    return results

"""
使用示例:

# 创建混合检索器，自定义标签权重
retriever = HybridRetriever(
    keyword_index=keyword_idx,
    semantic_index=semantic_idx,
    tag_weights={
        "important": 3.0,    # #important 标签提权 3 倍
        "urgent": 2.0,       # #urgent 标签提权 2 倍
        "pinned": 5.0        # #pinned 标签提权 5 倍
    }
)

# 执行搜索
results = retriever.search("如何构建第二大脑", top_k=10)

# 查看结果
for r in results:
    print(f"Score: {r.score:.4f}, Tags: {r.get_tags()}, DocType: {r.get_doc_type()}")
    print(f"  Content: {r.content[:100]}...")
"""
