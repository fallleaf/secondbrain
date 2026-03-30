"""
FastEmbed 嵌入模型封装

使用 fastembed 实现轻量级、高性能的文本嵌入
"""

from utils.logger import get_logger
import os
from typing import List, Optional, Union
import numpy as np

# 导入日志
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = get_logger(__name__)

try:
    from fastembed import TextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False
    TextEmbedding = None


class Embedder:
    """FastEmbed 文本嵌入模型封装"""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        cache_dir: Optional[str] = None,
        max_length: int = 512,
        batch_size: int = 256
    ):
        """
        初始化 FastEmbed 嵌入模型

        Args:
            model_name: 模型名称 (fastembed 支持的模型)
            cache_dir: 模型缓存目录
            max_length: 最大序列长度
            batch_size: 批次大小
        """
        if not FASTEMBED_AVAILABLE:
            raise ImportError(
                "fastembed 未安装。请运行：pip install fastembed"
            )

        self.model_name = model_name
        self.cache_dir = cache_dir or "~/.cache/secondbrain/fastembed"
        self.cache_dir = os.path.expanduser(self.cache_dir)
        self.max_length = max_length
        self.batch_size = batch_size

        self._model = None
        self._embedding_dim = None

        # 设置模型维度映射
        self._model_dims = {
            "BAAI/bge-small-zh-v1.5": 512,
            "BAAI/bge-base-zh-v1.5": 768,
            "BAAI/bge-large-zh-v1.5": 1024,
        }

    @property
    def model(self):
        """懒加载模型"""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def embedding_dim(self) -> int:
        """获取嵌入维度"""
        if self._embedding_dim is None:
            # 从模型名称获取维度，或实际测试
            if self.model_name in self._model_dims:
                self._embedding_dim = self._model_dims[self.model_name]
            else:
                # 实际编码一个文本来获取维度
                test_embedding = self.encode(["test"])[0]
                self._embedding_dim = len(test_embedding)
                self._fastembed_actual_dim = self._embedding_dim
        return self._embedding_dim

    def _load_model(self) -> None:
        """加载模型"""
        logger.info(f"🔄 加载 FastEmbed 模型：{self.model_name}")
        logger.info(f" 缓存目录：{self.cache_dir}")

        # 创建缓存目录
        os.makedirs(self.cache_dir, exist_ok=True)

        # 加载模型
        self._model = TextEmbedding(
            model_name=self.model_name,
            cache_dir=self.cache_dir,
            max_length=self.max_length
        )

        logger.info("✅ FastEmbed 模型加载完成")
        logger.info(f" 嵌入维度：{self.embedding_dim}")
        logger.info(f" 批次大小：{self.batch_size}")

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: Optional[int] = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        编码文本为向量

        Args:
            texts: 文本字符串或列表
            batch_size: 批次大小 (覆盖默认值)
            show_progress: 是否显示进度

        Returns:
            np.ndarray: 嵌入向量数组 (shape: (num_texts, embedding_dim))
        """
        if isinstance(texts, str):
            texts = [texts]

        if batch_size is None:
            batch_size = self.batch_size

        # fastembed 返回的是生成器，需要转换为 numpy 数组
        embeddings = list(self.model.embed(
            texts,
            batch_size=batch_size,
            show_progress=show_progress
        ))

        # 转换为 numpy 数组
        embeddings = np.array(embeddings)

        return embeddings

    def encode_single(self, text: str) -> np.ndarray:
        """
        编码单个文本

        Args:
            text: 文本内容

        Returns:
            np.ndarray: 嵌入向量 (shape: (embedding_dim,))
        """
        embedding = self.encode([text])[0]
        return embedding

    def encode_chunks(
        self,
        chunks: List[str],
        batch_size: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        编码文本块列表

        Args:
            chunks: 文本块列表
            batch_size: 批次大小

        Returns:
            List[np.ndarray]: 嵌入向量列表
        """
        embeddings = self.encode(chunks, batch_size=batch_size)
        return [emb for emb in embeddings]

    def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            float: 余弦相似度 (-1 到 1)
        """
        emb1 = self.encode_single(text1)
        emb2 = self.encode_single(text2)

        # 归一化
        emb1_norm = emb1 / np.linalg.norm(emb1)
        emb2_norm = emb2 / np.linalg.norm(emb2)

        # 计算余弦相似度
        similarity = np.dot(emb1_norm, emb2_norm)

        return float(similarity)

    def find_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5
    ) -> List[tuple]:
        """
        查找与查询最相似的文本

        Args:
            query: 查询文本
            candidates: 候选文本列表
            top_k: 返回数量

        Returns:
            List[tuple]: [(索引，相似度), ...] 列表，按相似度降序排列
        """
        query_emb = self.encode_single(query)

        # 编码所有候选文本
        candidate_embs = self.encode(candidates)

        # 归一化
        query_norm = query_emb / np.linalg.norm(query_emb)
        candidate_norms = candidate_embs / np.linalg.norm(candidate_embs, axis=1, keepdims=True)

        # 计算相似度
        similarities = np.dot(candidate_norms, query_norm)

        # 获取 top_k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = [(int(idx), float(similarities[idx])) for idx in top_indices]

        return results

    def get_supported_models(self) -> List[str]:
        """
        获取 fastembed 支持的模型列表

        Returns:
            List[str]: 支持的模型名称列表
        """
        # fastembed 内置模型列表
        return [
            "BAAI/bge-small-zh-v1.5",
            "BAAI/bge-base-zh-v1.5",
            "BAAI/bge-large-zh-v1.5",
        ]

    def clear_cache(self) -> None:
        """清除模型缓存"""
        import shutil

        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            logger.info(f"🗑️ 已清除 FastEmbed 缓存：{self.cache_dir}")
        else:
            logger.info(f"ℹ️ 缓存目录不存在：{self.cache_dir}")


# 全局实例
_embedder = None


def get_embedder(
    model_name: str = "BAAI/bge-small-zh-v1.5",
    cache_dir: Optional[str] = None
) -> Embedder:
    """
    获取全局 Embedder 实例

    Args:
        model_name: 模型名称
        cache_dir: 缓存目录

    Returns:
        Embedder: FastEmbed 嵌入模型实例
    """
    global _embedder

    if _embedder is None:
        _embedder = Embedder(model_name, cache_dir)

    return _embedder


if __name__ == "__main__":
    # 测试 FastEmbed 嵌入模型
    embedder = Embedder(model_name="BAAI/bge-small-zh-v1.5")

    # 测试编码
    texts = [
        "这是一个测试句子。",
        "这是另一个测试句子。",
        "机器学习是人工智能的一个重要分支。",
        "深度学习在自然语言处理中取得了巨大成功。"
    ]

    print("🧪 FastEmbed 嵌入模型测试")
    print("-" * 50)

    import time

    # 测试编码性能
    start_time = time.time()
    embeddings = embedder.encode(texts, show_progress=True)
    encode_time = time.time() - start_time

    print("\n📊 编码结果")
    print(f"文本数量：{len(texts)}")
    print(f"嵌入维度：{embedder.embedding_dim}")
    print(f"形状：{embeddings.shape}")
    print(f"编码时间：{encode_time:.3f}秒")
    print(f"平均每个文本：{encode_time / len(texts) * 1000:.2f}毫秒")

    # 测试相似度
    print("\n🔍 相似度测试")
    query = "人工智能"
    start_time = time.time()
    results = embedder.find_similar(query, texts, top_k=3)
    sim_time = time.time() - start_time

    print(f"查询：{query}")
    print(f"相似度计算时间：{sim_time * 1000:.2f}毫秒")
    for idx, sim in results:
        print(f"  {sim:.4f}: {texts[idx]}")

    # 测试单文本编码
    print("\n⚡ 单文本编码性能测试")
    test_text = "快速嵌入模型测试"
    times = []
    for i in range(5):
        start = time.time()
        _ = embedder.encode_single(test_text)
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)
    print(f"5 次平均编码时间：{avg_time * 1000:.2f}毫秒")

    print("\n✅ FastEmbed 测试完成")
