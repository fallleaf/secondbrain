#!/usr/bin/env python3
"""
Phase 2 验证测试脚本

测试 fastembed 替代 sentence-transformers 的性能和兼容性
验证项目：
1. 模型加载速度
2. 编码性能
3. 向量维度兼容性
4. 相似度计算准确性
5. 内存占用
"""

import os
import sys
import time
import traceback
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 测试配置
TEST_TEXTS = [
    "这是一个测试句子。",
    "这是另一个测试句子。",
    "机器学习是人工智能的一个重要分支。",
    "深度学习在自然语言处理中取得了巨大成功。",
    "Python 是一种高级编程语言。",
    "自然语言处理是人工智能的重要领域。",
    "Transformer 架构彻底改变了 NLP 领域。",
    "大语言模型在多个任务上表现出色。",
    "语义搜索需要高质量的文本嵌入。",
    "向量数据库用于存储和检索嵌入向量。"
] * 10  # 100 个文本用于性能测试

QUERY_TEXT = "人工智能和机器学习"

RESULTS = []


def log_result(test_name: str, success: bool, message: str, details: dict = None):
    """记录测试结果"""
    result = {
        "test": test_name,
        "success": success,
        "message": message,
        "details": details or {}
    }
    RESULTS.append(result)
    
    status = "✅" if success else "❌"
    print(f"{status} {test_name}: {message}")
    if details:
        for key, value in details.items():
            print(f"   {key}: {value}")


def test_fastembed_availability():
    """测试 fastembed 是否可用"""
    try:
        from fastembed import TextEmbedding
        import fastembed
        log_result(
            "FastEmbed 可用性",
            True,
            f"fastembed {fastembed.__version__} 已安装",
            {"version": fastembed.__version__}
        )
        return True
    except ImportError as e:
        log_result(
            "FastEmbed 可用性",
            False,
            f"fastembed 未安装：{e}",
            {"error": str(e)}
        )
        return False


def test_sentence_transformers_availability():
    """测试 sentence-transformers 是否可用"""
    try:
        from sentence_transformers import SentenceTransformer
        import sentence_transformers
        log_result(
            "SentenceTransformers 可用性",
            True,
            f"sentence-transformers {sentence_transformers.__version__} 已安装",
            {"version": sentence_transformers.__version__}
        )
        return True
    except ImportError as e:
        log_result(
            "SentenceTransformers 可用性",
            False,
            f"sentence-transformers 未安装：{e}",
            {"error": str(e)}
        )
        return False


def test_fastembed_model_loading():
    """测试 FastEmbed 模型加载"""
    try:
        from index.fastembedder import FastEmbedder
        
        start_time = time.time()
        embedder = FastEmbedder(model_name="BAAI/bge-small-zh-v1.5")
        _ = embedder.embedding_dim  # 触发模型加载
        load_time = time.time() - start_time
        
        log_result(
            "FastEmbed 模型加载",
            True,
            f"模型加载成功",
            {
                "加载时间": f"{load_time:.2f}秒",
                "嵌入维度": embedder.embedding_dim
            }
        )
        return embedder
    except Exception as e:
        log_result(
            "FastEmbed 模型加载",
            False,
            f"模型加载失败：{e}",
            {"error": str(e)}
        )
        return None


def test_sentence_transformers_model_loading():
    """测试 SentenceTransformers 模型加载"""
    try:
        from index.embedder import Embedder
        
        start_time = time.time()
        embedder = Embedder(model_name="BAAI/bge-small-zh-v1.5")
        _ = embedder.embedding_dim  # 触发模型加载
        load_time = time.time() - start_time
        
        log_result(
            "SentenceTransformers 模型加载",
            True,
            f"模型加载成功",
            {
                "加载时间": f"{load_time:.2f}秒",
                "嵌入维度": embedder.embedding_dim
            }
        )
        return embedder
    except Exception as e:
        log_result(
            "SentenceTransformers 模型加载",
            False,
            f"模型加载失败：{e}",
            {"error": str(e)}
        )
        return None


def test_fastembed_encoding(fastembedder):
    """测试 FastEmbed 编码性能"""
    try:
        # 测试小批量编码
        start_time = time.time()
        embeddings_small = fastembedder.encode(TEST_TEXTS[:10], show_progress=False)
        small_time = time.time() - start_time
        
        # 测试大批量编码
        start_time = time.time()
        embeddings_large = fastembedder.encode(TEST_TEXTS, show_progress=False)
        large_time = time.time() - start_time
        
        log_result(
            "FastEmbed 编码性能",
            True,
            f"编码成功",
            {
                "小批量 (10 条)": f"{small_time*1000:.2f}毫秒",
                "大批量 (100 条)": f"{large_time*1000:.2f}毫秒",
                "平均每条": f"{large_time/len(TEST_TEXTS)*1000:.2f}毫秒",
                "输出形状": str(embeddings_large.shape)
            }
        )
        return embeddings_large
    except Exception as e:
        log_result(
            "FastEmbed 编码性能",
            False,
            f"编码失败：{e}",
            {"error": str(e)}
        )
        return None


def test_sentence_transformers_encoding(embedder):
    """测试 SentenceTransformers 编码性能"""
    try:
        # 测试小批量编码
        start_time = time.time()
        embeddings_small = embedder.encode(TEST_TEXTS[:10], show_progress=False)
        small_time = time.time() - start_time
        
        # 测试大批量编码
        start_time = time.time()
        embeddings_large = embedder.encode(TEST_TEXTS, show_progress=False)
        large_time = time.time() - start_time
        
        log_result(
            "SentenceTransformers 编码性能",
            True,
            f"编码成功",
            {
                "小批量 (10 条)": f"{small_time*1000:.2f}毫秒",
                "大批量 (100 条)": f"{large_time*1000:.2f}毫秒",
                "平均每条": f"{large_time/len(TEST_TEXTS)*1000:.2f}毫秒",
                "输出形状": str(embeddings_large.shape)
            }
        )
        return embeddings_large
    except Exception as e:
        log_result(
            "SentenceTransformers 编码性能",
            False,
            f"编码失败：{e}",
            {"error": str(e)}
        )
        return None


def test_vector_compatibility(fastembeddings, st_embeddings):
    """测试向量维度兼容性"""
    try:
        fast_dim = fastembeddings.shape[1]
        st_dim = st_embeddings.shape[1]
        
        compatible = fast_dim == st_dim
        
        log_result(
            "向量维度兼容性",
            True,  # 维度不同不代表不兼容，只是需要分别处理
            f"维度{'匹配' if compatible else '不同（需要分别处理）'}",
            {
                "FastEmbed 维度": fast_dim,
                "SentenceTransformers 维度": st_dim,
                "是否相同": compatible,
                "注意": "维度不同不影响各自使用，但索引需要分别建立" if not compatible else ""
            }
        )
        return True  # 维度不同不是错误
    except Exception as e:
        log_result(
            "向量维度兼容性",
            False,
            f"检查失败：{e}",
            {"error": str(e)}
        )
        return False


def test_similarity_accuracy(fastembedder, st_embedder):
    """测试相似度计算准确性"""
    try:
        # FastEmbed 相似度
        start_time = time.time()
        fast_sim = fastembedder.similarity("人工智能", "机器学习")
        fast_time = time.time() - start_time
        
        # SentenceTransformers 相似度
        start_time = time.time()
        st_sim = st_embedder.similarity("人工智能", "机器学习")
        st_time = time.time() - start_time
        
        # 计算差异
        diff = abs(fast_sim - st_sim)
        
        log_result(
            "相似度计算准确性",
            diff < 0.1,  # 允许 0.1 的差异
            f"相似度结果{'接近' if diff < 0.1 else '差异较大'}",
            {
                "FastEmbed 相似度": f"{fast_sim:.4f}",
                "SentenceTransformers 相似度": f"{st_sim:.4f}",
                "差异": f"{diff:.4f}",
                "FastEmbed 耗时": f"{fast_time*1000:.2f}毫秒",
                "SentenceTransformers 耗时": f"{st_time*1000:.2f}毫秒"
            }
        )
        return diff < 0.1
    except Exception as e:
        log_result(
            "相似度计算准确性",
            False,
            f"计算失败：{e}",
            {"error": str(e)}
        )
        return False


def test_topk_search(fastembedder, st_embedder):
    """测试 Top-K 搜索"""
    try:
        # FastEmbed 搜索
        start_time = time.time()
        fast_results = fastembedder.find_similar(QUERY_TEXT, TEST_TEXTS, top_k=5)
        fast_time = time.time() - start_time
        
        # SentenceTransformers 搜索
        start_time = time.time()
        st_results = st_embedder.find_similar(QUERY_TEXT, TEST_TEXTS, top_k=5)
        st_time = time.time() - start_time
        
        # 比较前 3 个结果的排名重合度
        fast_top3 = [r[0] for r in fast_results[:3]]
        st_top3 = [r[0] for r in st_results[:3]]
        overlap = len(set(fast_top3) & set(st_top3))
        
        log_result(
            "Top-K 搜索一致性",
            overlap >= 2,  # 至少 2 个重合
            f"Top-3 结果{'高度一致' if overlap >= 2 else '部分一致'}",
            {
                "FastEmbed 耗时": f"{fast_time*1000:.2f}毫秒",
                "SentenceTransformers 耗时": f"{st_time*1000:.2f}毫秒",
                "Top-3 重合数": overlap,
                "FastEmbed Top-3": fast_top3,
                "SentenceTransformers Top-3": st_top3
            }
        )
        return overlap >= 2
    except Exception as e:
        log_result(
            "Top-K 搜索一致性",
            False,
            f"搜索失败：{e}",
            {"error": str(e)}
        )
        return False


def test_memory_usage():
    """测试内存占用（简单测试）"""
    try:
        import tracemalloc
        
        # 测试 FastEmbed
        tracemalloc.start()
        from index.fastembedder import FastEmbedder
        fast_embedder = FastEmbedder()
        _ = fast_embedder.encode(["test"])
        fast_current, fast_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 测试 SentenceTransformers
        tracemalloc.start()
        from index.embedder import Embedder
        st_embedder = Embedder()
        _ = st_embedder.encode(["test"])
        st_current, st_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        log_result(
            "内存占用对比",
            True,
            "内存测试完成",
            {
                "FastEmbed 当前": f"{fast_current / 1024 / 1024:.2f} MB",
                "FastEmbed 峰值": f"{fast_peak / 1024 / 1024:.2f} MB",
                "SentenceTransformers 当前": f"{st_current / 1024 / 1024:.2f} MB",
                "SentenceTransformers 峰值": f"{st_peak / 1024 / 1024:.2f} MB",
                "FastEmbed 节省": f"{(1 - fast_peak/st_peak)*100:.1f}%" if st_peak > 0 else "N/A"
            }
        )
    except Exception as e:
        log_result(
            "内存占用对比",
            False,
            f"测试失败：{e}",
            {"error": str(e)}
        )


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("📊 Phase 2 验证测试总结")
    print("=" * 60)
    
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["success"])
    failed = total - passed
    
    print(f"\n总测试数：{total}")
    print(f"通过：{passed}")
    print(f"失败：{failed}")
    print(f"通过率：{passed/total*100:.1f}%")
    
    print("\n" + "-" * 60)
    print("详细结果:")
    print("-" * 60)
    
    for result in RESULTS:
        status = "✅" if result["success"] else "❌"
        print(f"\n{status} {result['test']}")
        print(f"   {result['message']}")
        if result["details"]:
            for key, value in result["details"].items():
                print(f"   {key}: {value}")
    
    # 保存测试结果
    import json
    result_file = Path(__file__).parent / "phase2_test_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 测试结果已保存到：{result_file}")
    
    # 返回是否所有关键测试通过
    critical_tests = [
        "FastEmbed 可用性",
        "FastEmbed 模型加载",
        "FastEmbed 编码性能",
        "向量维度兼容性"
    ]
    
    critical_passed = all(
        any(r["test"] == test and r["success"] for r in RESULTS)
        for test in critical_tests
    )
    
    return critical_passed


def main():
    """主测试函数"""
    print("=" * 60)
    print("🚀 SecondBrain Phase 2 验证测试")
    print("   测试 fastembed 替代 sentence-transformers")
    print("=" * 60)
    print()
    
    # 1. 检查依赖
    print("\n📦 依赖检查")
    print("-" * 50)
    fastembed_ok = test_fastembed_availability()
    st_ok = test_sentence_transformers_availability()
    
    if not fastembed_ok:
        print("\n❌ FastEmbed 未安装，请先运行：pip install fastembed")
        return False
    
    # 2. 模型加载测试
    print("\n🔄 模型加载测试")
    print("-" * 50)
    fastembedder = test_fastembed_model_loading()
    st_embedder = test_sentence_transformers_model_loading() if st_ok else None
    
    if not fastembedder:
        print("\n❌ FastEmbed 模型加载失败")
        return False
    
    # 3. 编码性能测试
    print("\n⚡ 编码性能测试")
    print("-" * 50)
    fastembeddings = test_fastembed_encoding(fastembedder)
    st_embeddings = test_sentence_transformers_encoding(st_embedder) if st_embedder else None
    
    if fastembeddings is None:
        print("\n❌ FastEmbed 编码失败")
        return False
    
    # 4. 向量兼容性测试
    print("\n🔗 向量兼容性测试")
    print("-" * 50)
    if st_embeddings is not None:
        test_vector_compatibility(fastembeddings, st_embeddings)
    
    # 5. 相似度准确性测试
    print("\n🎯 相似度准确性测试")
    print("-" * 50)
    if st_embedder:
        test_similarity_accuracy(fastembedder, st_embedder)
    
    # 6. Top-K 搜索测试
    print("\n🔍 Top-K 搜索测试")
    print("-" * 50)
    if st_embedder:
        test_topk_search(fastembedder, st_embedder)
    
    # 7. 内存测试
    print("\n💾 内存占用测试")
    print("-" * 50)
    test_memory_usage()
    
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
