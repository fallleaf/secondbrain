#!/usr/bin/env python3
"""
Phase 2 快速验证测试 - FastEmbed 独立测试

仅测试 fastembed 功能，不依赖 sentence-transformers
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
] * 10  # 100 个文本

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
                "嵌入维度": embedder.embedding_dim,
                "模型名称": "BAAI/bge-small-zh-v1.5"
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
        
        # 测试单文本编码
        start_time = time.time()
        for _ in range(10):
            _ = fastembedder.encode_single("测试文本")
        single_avg = (time.time() - start_time) / 10
        
        log_result(
            "FastEmbed 编码性能",
            True,
            f"编码成功",
            {
                "小批量 (10 条)": f"{small_time*1000:.2f}毫秒",
                "大批量 (100 条)": f"{large_time*1000:.2f}毫秒",
                "平均每条": f"{large_time/len(TEST_TEXTS)*1000:.2f}毫秒",
                "单文本平均": f"{single_avg*1000:.2f}毫秒",
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


def test_fastembed_similarity(fastembedder):
    """测试 FastEmbed 相似度计算"""
    try:
        # 测试相似度计算
        start_time = time.time()
        sim = fastembedder.similarity("人工智能", "机器学习")
        sim_time = time.time() - start_time
        
        # 测试 Top-K 搜索
        start_time = time.time()
        results = fastembedder.find_similar(QUERY_TEXT, TEST_TEXTS, top_k=5)
        search_time = time.time() - start_time
        
        log_result(
            "FastEmbed 相似度与搜索",
            True,
            f"相似度计算和搜索成功",
            {
                "相似度 (人工智能 vs 机器学习)": f"{sim:.4f}",
                "相似度计算时间": f"{sim_time*1000:.2f}毫秒",
                "Top-K 搜索时间": f"{search_time*1000:.2f}毫秒",
                "Top-1 结果相似度": f"{results[0][1]:.4f}"
            }
        )
        return True
    except Exception as e:
        log_result(
            "FastEmbed 相似度与搜索",
            False,
            f"计算失败：{e}",
            {"error": str(e)}
        )
        return False


def test_fastembed_batch_processing(fastembedder):
    """测试 FastEmbed 批量处理"""
    try:
        # 测试不同批次大小
        batch_sizes = [1, 10, 50, 100]
        times = []
        
        for batch_size in batch_sizes:
            texts = TEST_TEXTS[:batch_size]
            start_time = time.time()
            _ = fastembedder.encode(texts, show_progress=False)
            elapsed = time.time() - start_time
            times.append((batch_size, elapsed))
        
        log_result(
            "FastEmbed 批量处理",
            True,
            f"批量处理成功",
            {
                "批次 1": f"{times[0][1]*1000:.2f}毫秒",
                "批次 10": f"{times[1][1]*1000:.2f}毫秒",
                "批次 50": f"{times[2][1]*1000:.2f}毫秒",
                "批次 100": f"{times[3][1]*1000:.2f}毫秒",
                "吞吐量 (条/秒)": f"{len(TEST_TEXTS)/times[3][1]:.1f}"
            }
        )
        return True
    except Exception as e:
        log_result(
            "FastEmbed 批量处理",
            False,
            f"批量处理失败：{e}",
            {"error": str(e)}
        )
        return False


def test_fastembed_integration(fastembedder):
    """测试 FastEmbed 与 FAISS 集成"""
    try:
        import faiss
        from index.semantic_index import SemanticIndex
        
        # 创建临时索引（使用 512 维，因为 fastembed 输出 512 维）
        temp_index_path = "/tmp/test_fastembed_index.faiss"
        index = SemanticIndex(temp_index_path, dim=fastembedder.embedding_dim)
        
        # 添加文档
        for i, text in enumerate(TEST_TEXTS[:20]):
            embedding = fastembedder.encode_single(text)
            index.add_document(f"doc_{i}", embedding, {"text": text})
        
        # 搜索
        query_embedding = fastembedder.encode_single(QUERY_TEXT)
        search_results = index.search(query_embedding, top_k=5)
        
        # 清理
        if os.path.exists(temp_index_path):
            os.remove(temp_index_path)
        if os.path.exists(temp_index_path + '.mapping.json'):
            os.remove(temp_index_path + '.mapping.json')
        
        log_result(
            "FastEmbed + FAISS 集成",
            True,
            f"集成测试成功",
            {
                "文档数量": 20,
                "搜索结果数量": len(search_results),
                "最高相似度": f"{search_results[0][1]:.4f}" if search_results else "N/A",
                "向量维度": fastembedder.embedding_dim
            }
        )
        return True
    except Exception as e:
        log_result(
            "FastEmbed + FAISS 集成",
            False,
            f"集成测试失败：{e}",
            {"error": str(e)}
        )
        return False


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("📊 Phase 2 验证测试总结 (FastEmbed)")
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
    result_file = Path(__file__).parent / "phase2_fastembed_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 测试结果已保存到：{result_file}")
    
    # 关键测试
    critical_tests = [
        "FastEmbed 可用性",
        "FastEmbed 模型加载",
        "FastEmbed 编码性能",
        "FastEmbed + FAISS 集成"
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
    print("   FastEmbed 独立功能验证")
    print("=" * 60)
    print()
    
    # 1. 检查依赖
    print("\n📦 依赖检查")
    print("-" * 50)
    fastembed_ok = test_fastembed_availability()
    
    if not fastembed_ok:
        print("\n❌ FastEmbed 未安装，请先运行：pip install fastembed")
        return False
    
    # 2. 模型加载测试
    print("\n🔄 模型加载测试")
    print("-" * 50)
    fastembedder = test_fastembed_model_loading()
    
    if not fastembedder:
        print("\n❌ FastEmbed 模型加载失败")
        return False
    
    # 3. 编码性能测试
    print("\n⚡ 编码性能测试")
    print("-" * 50)
    embeddings = test_fastembed_encoding(fastembedder)
    
    if embeddings is None:
        print("\n❌ FastEmbed 编码失败")
        return False
    
    # 4. 相似度测试
    print("\n🎯 相似度与搜索测试")
    print("-" * 50)
    test_fastembed_similarity(fastembedder)
    
    # 5. 批量处理测试
    print("\n📦 批量处理测试")
    print("-" * 50)
    test_fastembed_batch_processing(fastembedder)
    
    # 6. FAISS 集成测试
    print("\n🔗 FAISS 集成测试")
    print("-" * 50)
    test_fastembed_integration(fastembedder)
    
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
