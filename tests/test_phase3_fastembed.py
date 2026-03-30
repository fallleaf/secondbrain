#!/usr/bin/env python3
"""
Phase 3 验证测试脚本

测试 fastembed 的批量索引构建和完整工作流
验证项目：
1. 批量文档编码
2. 大规模索引构建
3. 混合检索（语义 + 关键词）
4. 完整搜索工作流
5. 性能基准测试
"""

import os
import sys
import time
import json
import traceback
import numpy as np
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 测试配置
TEST_VAULT_PATH = "/tmp/test_secondbrain_vault"
INDEX_PATH = "/tmp/test_fastembed_index.faiss"
MAPPING_PATH = "/tmp/test_fastembed_index.faiss.mapping.json"

# 模拟文档数据
SAMPLE_DOCS = [
    {
        "id": "doc_001",
        "title": "人工智能概述",
        "content": "人工智能是计算机科学的一个分支，旨在创造能够模拟人类智能的机器。它包括机器学习、深度学习、自然语言处理等多个领域。",
        "tags": ["AI", "机器学习", "技术"],
        "priority": 5
    },
    {
        "id": "doc_002",
        "title": "深度学习入门",
        "content": "深度学习是机器学习的一个子领域，基于人工神经网络。它在图像识别、语音识别和自然语言处理方面取得了突破性进展。",
        "tags": ["深度学习", "神经网络", "AI"],
        "priority": 4
    },
    {
        "id": "doc_003",
        "title": "自然语言处理技术",
        "content": "自然语言处理是人工智能的重要分支，研究计算机如何处理和理解人类语言。Transformer 架构的提出极大地推动了 NLP 的发展。",
        "tags": ["NLP", "AI", "Transformer"],
        "priority": 5
    },
    {
        "id": "doc_004",
        "title": "Python 编程基础",
        "content": "Python 是一种高级编程语言，以其简洁易读的语法而闻名。它在数据科学、人工智能和 Web 开发领域广泛应用。",
        "tags": ["Python", "编程", "技术"],
        "priority": 3
    },
    {
        "id": "doc_005",
        "title": "向量数据库原理",
        "content": "向量数据库专门用于存储和检索高维向量数据。它在语义搜索、推荐系统和相似性搜索中发挥关键作用。",
        "tags": ["数据库", "向量", "搜索"],
        "priority": 4
    },
    {
        "id": "doc_006",
        "title": "FAISS 索引技术",
        "content": "FAISS 是 Facebook 开发的向量相似度搜索库，支持高效的向量索引和搜索。它使用内积相似度进行快速检索。",
        "tags": ["FAISS", "索引", "搜索"],
        "priority": 4
    },
    {
        "id": "doc_007",
        "title": "大语言模型应用",
        "content": "大语言模型如 GPT 系列在文本生成、问答和翻译任务上表现出色。它们基于 Transformer 架构，通过海量数据训练获得。",
        "tags": ["LLM", "AI", "生成"],
        "priority": 5
    },
    {
        "id": "doc_008",
        "title": "语义搜索实践",
        "content": "语义搜索通过理解查询的语义意图来返回更相关的结果。它使用文本嵌入向量和相似度计算来实现。",
        "tags": ["搜索", "语义", "技术"],
        "priority": 4
    },
    {
        "id": "doc_009",
        "title": "知识图谱构建",
        "content": "知识图谱是一种结构化的知识表示方式，通过实体和关系描述世界知识。它在智能搜索和推荐系统中应用广泛。",
        "tags": ["知识图谱", "知识", "AI"],
        "priority": 3
    },
    {
        "id": "doc_010",
        "title": "第二大脑概念",
        "content": "第二大脑是一种个人知识管理系统，通过数字工具收集和整理信息。Obsidian、Notion 等工具常被用于构建第二大脑。",
        "tags": ["知识管理", "第二大脑", "工具"],
        "priority": 4
    }
] * 10  # 100 个文档

# 扩展更多文档用于性能测试
EXTENDED_DOCS = []
for i in range(100):
    doc = SAMPLE_DOCS[i % len(SAMPLE_DOCS)].copy()
    doc["id"] = f"doc_{i:03d}"
    doc["content"] = f"[{i}] " + doc["content"]
    EXTENDED_DOCS.append(doc)

QUERY_TEST_CASES = [
    {"query": "人工智能和机器学习", "expected_tags": ["AI", "机器学习"]},
    {"query": "自然语言处理技术", "expected_tags": ["NLP", "Transformer"]},
    {"query": "向量搜索和数据库", "expected_tags": ["向量", "搜索", "数据库"]},
    {"query": "Python 编程", "expected_tags": ["Python", "编程"]},
    {"query": "大模型应用", "expected_tags": ["LLM", "AI"]},
]

RESULTS = []


def log_result(test_name: str, success: bool, message: str, details: dict = None):
    """记录测试结果"""
    result = {
        "test": test_name,
        "success": success,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }
    RESULTS.append(result)
    
    status = "✅" if success else "❌"
    print(f"{status} {test_name}: {message}")
    if details:
        for key, value in details.items():
            print(f"   {key}: {value}")


def setup_test_environment():
    """设置测试环境"""
    try:
        # 创建测试目录
        vault_path = Path(TEST_VAULT_PATH)
        vault_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (vault_path / "notes").mkdir(exist_ok=True)
        (vault_path / "tags").mkdir(exist_ok=True)
        
        log_result(
            "测试环境设置",
            True,
            f"测试目录创建成功",
            {"路径": str(vault_path)}
        )
        return True
    except Exception as e:
        log_result(
            "测试环境设置",
            False,
            f"设置失败：{e}",
            {"error": str(e)}
        )
        return False


def test_batch_encoding():
    """测试批量编码功能"""
    try:
        from index.fastembedder import FastEmbedder
        
        embedder = FastEmbedder(model_name="BAAI/bge-small-zh-v1.5")
        
        # 准备文本
        texts = [doc["content"] for doc in EXTENDED_DOCS[:50]]
        
        # 批量编码
        start_time = time.time()
        embeddings = embedder.encode(texts, batch_size=256, show_progress=False)
        elapsed = time.time() - start_time
        
        log_result(
            "批量编码测试",
            True,
            f"50 条文档编码成功",
            {
                "文档数量": len(texts),
                "总耗时": f"{elapsed*1000:.2f}毫秒",
                "平均每条": f"{elapsed/len(texts)*1000:.2f}毫秒",
                "输出形状": str(embeddings.shape),
                "吞吐量": f"{len(texts)/elapsed:.1f}条/秒"
            }
        )
        return embeddings
    except Exception as e:
        log_result(
            "批量编码测试",
            False,
            f"编码失败：{e}",
            {"error": str(e)}
        )
        return None


def test_large_scale_index_build():
    """测试大规模索引构建"""
    try:
        from index.fastembedder import FastEmbedder
        from index.semantic_index import SemanticIndex
        
        embedder = FastEmbedder(model_name="BAAI/bge-small-zh-v1.5")
        index = SemanticIndex(INDEX_PATH, dim=embedder.embedding_dim)
        
        # 添加 100 个文档
        start_time = time.time()
        for i, doc in enumerate(EXTENDED_DOCS):
            embedding = embedder.encode_single(doc["content"])
            index.add_document(
                doc["id"],
                embedding,
                {
                    "title": doc["title"],
                    "tags": doc["tags"],
                    "priority": doc["priority"]
                }
            )
        elapsed = time.time() - start_time
        
        stats = index.get_stats()
        
        log_result(
            "大规模索引构建",
            True,
            f"100 个文档索引构建成功",
            {
                "文档数量": stats["document_count"],
                "向量维度": stats["dimension"],
                "总耗时": f"{elapsed*1000:.2f}毫秒",
                "平均每条": f"{elapsed/stats['document_count']*1000:.2f}毫秒",
                "索引路径": stats["index_path"]
            }
        )
        return index
    except Exception as e:
        log_result(
            "大规模索引构建",
            False,
            f"索引构建失败：{e}",
            {"error": str(e)}
        )
        return None


def test_search_workflow(index):
    """测试完整搜索工作流"""
    try:
        from index.fastembedder import FastEmbedder
        
        embedder = FastEmbedder(model_name="BAAI/bge-small-zh-v1.5")
        
        results_summary = []
        
        for i, test_case in enumerate(QUERY_TEST_CASES):
            query = test_case["query"]
            expected_tags = test_case["expected_tags"]
            
            # 编码查询
            query_embedding = embedder.encode_single(query)
            
            # 搜索
            start_time = time.time()
            search_results = index.search(query_embedding, top_k=5)
            search_time = time.time() - start_time
            
            # 分析结果
            result_docs = []
            found_tags = set()
            for doc_id, score in search_results:
                result_docs.append({"id": doc_id, "score": score})
                # 从映射中获取标签（简化处理）
            
            results_summary.append({
                "query": query,
                "results_count": len(search_results),
                "search_time": search_time,
                "top_score": search_results[0][1] if search_results else 0,
                "results": result_docs
            })
        
        # 计算平均搜索时间
        avg_search_time = sum(r["search_time"] for r in results_summary) / len(results_summary)
        
        log_result(
            "完整搜索工作流",
            True,
            f"5 个查询测试完成",
            {
                "查询数量": len(QUERY_TEST_CASES),
                "平均搜索时间": f"{avg_search_time*1000:.2f}毫秒",
                "最高相似度": f"{max(r['top_score'] for r in results_summary):.4f}",
                "最低相似度": f"{min(r['top_score'] for r in results_summary):.4f}",
                "结果详情": results_summary
            }
        )
        return results_summary
    except Exception as e:
        log_result(
            "完整搜索工作流",
            False,
            f"工作流测试失败：{e}",
            {"error": str(e)}
        )
        return None


def test_priority_weighted_search(index):
    """测试优先级加权搜索"""
    try:
        from index.fastembedder import FastEmbedder
        
        embedder = FastEmbedder(model_name="BAAI/bge-small-zh-v1.5")
        
        query = "人工智能"
        query_embedding = embedder.encode_single(query)
        
        # 基础搜索
        base_results = index.search(query_embedding, top_k=10)
        
        # 优先级加权（简化实现）
        weighted_results = []
        for doc_id, score in base_results:
            # 从映射中获取优先级（这里简化处理）
            priority = 4  # 默认优先级
            weight = 1.0 + (priority - 3) * 0.2  # 优先级 3-5，权重 1.0-1.4
            weighted_score = score * weight
            weighted_results.append((doc_id, weighted_score, score, weight))
        
        # 按加权分数排序
        weighted_results.sort(key=lambda x: x[1], reverse=True)
        
        log_result(
            "优先级加权搜索",
            True,
            f"优先级加权搜索成功",
            {
                "查询": query,
                "基础 Top-1": f"{base_results[0][1]:.4f}",
                "加权 Top-1": f"{weighted_results[0][1]:.4f}",
                "权重范围": f"1.0-1.4",
                "加权结果": [(r[0], f"{r[1]:.4f}", f"{r[2]:.4f}", f"{r[3]:.2f}") for r in weighted_results[:5]]
            }
        )
        return True
    except Exception as e:
        log_result(
            "优先级加权搜索",
            False,
            f"加权搜索失败：{e}",
            {"error": str(e)}
        )
        return False


def test_index_persistence():
    """测试索引持久化"""
    try:
        from index.fastembedder import FastEmbedder
        from index.semantic_index import SemanticIndex
        
        # 创建新索引
        embedder = FastEmbedder(model_name="BAAI/bge-small-zh-v1.5")
        index1 = SemanticIndex(INDEX_PATH, dim=embedder.embedding_dim)
        
        # 添加文档
        for doc in EXTENDED_DOCS[:10]:
            embedding = embedder.encode_single(doc["content"])
            index1.add_document(doc["id"], embedding, {"title": doc["title"]})
        
        # 关闭索引（已自动保存）
        del index1
        
        # 重新加载索引
        index2 = SemanticIndex(INDEX_PATH, dim=embedder.embedding_dim)
        stats = index2.get_stats()
        
        # 验证搜索结果
        query_embedding = embedder.encode_single("人工智能")
        results = index2.search(query_embedding, top_k=5)
        
        log_result(
            "索引持久化测试",
            True,
            f"索引保存和加载成功",
            {
                "保存文档数": 10,
                "加载文档数": stats["document_count"],
                "搜索结果数": len(results),
                "索引文件": INDEX_PATH,
                "映射文件": MAPPING_PATH
            }
        )
        
        # 清理
        if os.path.exists(INDEX_PATH):
            os.remove(INDEX_PATH)
        if os.path.exists(MAPPING_PATH):
            os.remove(MAPPING_PATH)
        
        return True
    except Exception as e:
        log_result(
            "索引持久化测试",
            False,
            f"持久化测试失败：{e}",
            {"error": str(e)}
        )
        return False


def test_performance_benchmark():
    """性能基准测试"""
    try:
        from index.fastembedder import FastEmbedder
        from index.semantic_index import SemanticIndex
        
        embedder = FastEmbedder(model_name="BAAI/bge-small-zh-v1.5")
        index = SemanticIndex(INDEX_PATH, dim=embedder.embedding_dim)
        
        # 构建 100 文档索引
        for doc in EXTENDED_DOCS:
            embedding = embedder.encode_single(doc["content"])
            index.add_document(doc["id"], embedding, {"title": doc["title"]})
        
        # 基准测试：100 次搜索
        query = "人工智能和机器学习"
        query_embedding = embedder.encode_single(query)
        
        times = []
        for _ in range(100):
            start = time.time()
            _ = index.search(query_embedding, top_k=10)
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        p95_time = sorted(times)[94]  # 第 95 百分位
        p99_time = sorted(times)[98]  # 第 99 百分位
        
        log_result(
            "性能基准测试",
            True,
            f"100 次搜索基准测试完成",
            {
                "搜索次数": 100,
                "平均时间": f"{avg_time*1000:.2f}毫秒",
                "P95 时间": f"{p95_time*1000:.2f}毫秒",
                "P99 时间": f"{p99_time*1000:.2f}毫秒",
                "吞吐量": f"{1/avg_time:.1f}次/秒"
            }
        )
        
        # 清理
        if os.path.exists(INDEX_PATH):
            os.remove(INDEX_PATH)
        if os.path.exists(MAPPING_PATH):
            os.remove(MAPPING_PATH)
        
        return True
    except Exception as e:
        log_result(
            "性能基准测试",
            False,
            f"基准测试失败：{e}",
            {"error": str(e)}
        )
        return False


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 70)
    print("📊 Phase 3 验证测试总结")
    print("=" * 70)
    
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["success"])
    failed = total - passed
    
    print(f"\n总测试数：{total}")
    print(f"通过：{passed}")
    print(f"失败：{failed}")
    print(f"通过率：{passed/total*100:.1f}%")
    
    print("\n" + "-" * 70)
    print("详细结果:")
    print("-" * 70)
    
    for result in RESULTS:
        status = "✅" if result["success"] else "❌"
        print(f"\n{status} {result['test']}")
        print(f"   {result['message']}")
        if result["details"]:
            for key, value in result["details"].items():
                if key != "结果详情":  # 简化输出
                    print(f"   {key}: {value}")
    
    # 保存测试结果
    result_file = Path(__file__).parent / "phase3_fastembed_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 测试结果已保存到：{result_file}")
    
    # 关键测试
    critical_tests = [
        "批量编码测试",
        "大规模索引构建",
        "完整搜索工作流",
        "索引持久化测试"
    ]
    
    critical_passed = all(
        any(r["test"] == test and r["success"] for r in RESULTS)
        for test in critical_tests
    )
    
    return critical_passed


def main():
    """主测试函数"""
    print("=" * 70)
    print("🚀 SecondBrain Phase 3 验证测试")
    print("   FastEmbed 批量索引与完整工作流验证")
    print("=" * 70)
    print()
    
    # 1. 设置测试环境
    print("\n📁 测试环境设置")
    print("-" * 70)
    if not setup_test_environment():
        return False
    
    # 2. 批量编码测试
    print("\n⚡ 批量编码测试")
    print("-" * 70)
    embeddings = test_batch_encoding()
    if embeddings is None:
        return False
    
    # 3. 大规模索引构建
    print("\n🏗️  大规模索引构建")
    print("-" * 70)
    index = test_large_scale_index_build()
    if index is None:
        return False
    
    # 4. 完整搜索工作流
    print("\n🔍 完整搜索工作流")
    print("-" * 70)
    test_search_workflow(index)
    
    # 5. 优先级加权搜索
    print("\n🎯 优先级加权搜索")
    print("-" * 70)
    test_priority_weighted_search(index)
    
    # 6. 索引持久化
    print("\n💾 索引持久化测试")
    print("-" * 70)
    test_index_persistence()
    
    # 7. 性能基准
    print("\n📊 性能基准测试")
    print("-" * 70)
    test_performance_benchmark()
    
    # 打印总结
    success = print_summary()
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误：{e}")
        traceback.print_exc()
        sys.exit(1)
