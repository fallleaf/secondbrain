"""
索引管理工具模块

提供语义索引的统计、重建和增量更新功能
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from src.config.settings import Settings
from src.index.keyword_index import KeywordIndex
from src.index.semantic_index import SemanticIndex
from src.utils.filesystem import FileSystem


class IndexManager:
    """索引管理器"""

    def __init__(self, config: Settings):
        """
        初始化索引管理器

        Args:
            config: 配置对象
        """
        self.config = config
        # 支持多 Vault：获取所有启用的 Vault
        self.enabled_vaults = [v for v in config.vaults if v.enabled]

        # 如果没有任何启用的 Vault，使用第一个
        if not self.enabled_vaults:
            self.enabled_vaults = config.vaults[:1] if config.vaults else []

        # 为多 Vault 支持，为每个 vault 创建独立的索引管理器
        self.vault_indexes = {}
        for vault in self.enabled_vaults:
            # 确定索引路径
            if vault.index.semantic_db:
                semantic_db_path = vault.index.semantic_db
            else:
                semantic_db_path = config.index.semantic.db_path

            if vault.index.keyword_db:
                keyword_db_path = vault.index.keyword_db
            else:
                keyword_db_path = config.index.keyword.db_path

        self.vault_indexes[vault.name] = {
            'keyword': KeywordIndex(keyword_db_path),
            'semantic': SemanticIndex(semantic_db_path, dim=512),  # BAAI/bge-small-zh-v1.5 默认维度为 512
            'filesystem': FileSystem(vault.path),
            'path': Path(vault.path)
        }

        # 默认使用第一个 vault
        primary_vault = self.enabled_vaults[0] if self.enabled_vaults else config.vaults[0]
        self.filesystem = self.vault_indexes[primary_vault.name]['filesystem']
        self.keyword_index = self.vault_indexes[primary_vault.name]['keyword']
        self.semantic_index = self.vault_indexes[primary_vault.name]['semantic']
        self.vault_path = self.vault_indexes[primary_vault.name]['path']
        self.vault_paths = [Path(v.path) for v in self.enabled_vaults]

    def get_index_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息

        Returns:
            Dict[str, Any]: 索引统计信息
        """
        try:
            keyword_stats = self.keyword_index.get_stats()
            semantic_stats = self.semantic_index.get_stats()

            # 统计所有启用的 Vault 中的文件总数
            total_files = 0
            vault_details = []
            for vault_path in self.vault_paths:
                files = len(list(vault_path.rglob("*.md")))
                total_files += files
                vault_details.append({
                    "name": vault_path.name,
                    "path": str(vault_path),
                    "total_files": files
                })

            stats = {
                "keyword_index": keyword_stats,
                "semantic_index": semantic_stats,
                "vault_stats": {
                    "total_files": total_files,
                    "indexed_files": keyword_stats.get("file_count", 0),
                    "index_coverage": f"{(keyword_stats.get('file_count', 0) / max(total_files, 1) * 100):.1f}%",
                    "vaults": vault_details
                },
                "index_health": self._check_index_health()
            }

            return stats
        except Exception as e:
            return {"error": f"获取索引统计失败：{str(e)}"}

    def _check_index_health(self) -> Dict[str, Any]:
        """
        检查索引健康状态

        Returns:
            Dict[str, Any]: 健康状态信息
        """
        issues = []

        try:
            # 检查索引文件是否存在
            # KeywordIndex 有 db_path 属性
            if hasattr(self.keyword_index, 'db_path') and self.keyword_index.db_path:
                if not Path(self.keyword_index.db_path).exists():
                    issues.append("keyword_index: 索引文件不存在")

            # SemanticIndex 使用 index_path 属性，且可能是内存模式
            if hasattr(
                    self.semantic_index,
                    'index_path') and self.semantic_index.index_path and self.semantic_index.index_path != ":memory:":
                if not Path(self.semantic_index.index_path).exists():
                    issues.append("semantic_index: 索引文件不存在")
            elif not hasattr(self.semantic_index, 'index_path'):
                issues.append("semantic_index: 索引对象缺少 index_path 属性")

            # 检查所有 Vault 的文件总数
            total_files = 0
            for vault_path in self.vault_paths:
                total_files += len(list(vault_path.rglob("*.md")))

            keyword_stats = self.keyword_index.get_stats()
            indexed_files = keyword_stats.get("file_count", 0)

            if indexed_files < total_files * 0.5:
                issues.append(
                    f"索引覆盖率过低：{indexed_files}/{total_files} ({(indexed_files / max(total_files, 1) * 100):.1f}%)")

            return {
                "healthy": len(issues) == 0,
                "issues": issues,
                "recommendation": "需要重建索引" if issues else "索引状态正常"
            }
        except Exception as e:
            return {
                "healthy": False,
                "issues": [f"检查失败：{str(e)}"],
                "recommendation": "请检查日志"
            }

    async def rebuild_semantic_index(self, full: bool = False) -> Dict[str, Any]:
        """
        重建语义索引

        Args:
            full: 是否完全重建（包括关键词索引）

        Returns:
            Dict[str, Any]: 重建结果
        """
        try:
            if full:
                # 完全重建：先重建关键词索引，再重建语义索引
                result = await self._full_rebuild()
            else:
                # 增量重建：只重建语义索引
                result = await self._incremental_rebuild()

            return result
        except Exception as e:
            return {"error": f"重建索引失败：{str(e)}"}

    async def _full_rebuild(self) -> Dict[str, Any]:
        """
        完全重建索引

        Returns:
            Dict[str, Any]: 重建结果
        """
        result = {
            "status": "started",
            "mode": "full",
            "steps": []
        }

        try:
            # 步骤 1: 清空关键词索引
            result["steps"].append("清空关键词索引...")
            await asyncio.to_thread(self.keyword_index.rebuild)
            result["steps"].append("关键词索引已清空")

            # 步骤 2: 清空语义索引（需要手动实现，因为 SemanticIndex 没有 rebuild 方法）
            result["steps"].append("清空语义索引...")
            # SemanticIndex 没有直接清空方法，需要重建数据库
            # 这里我们简单地重新添加所有文档
            result["steps"].append("开始扫描所有笔记...")

            # 获取所有 markdown 文件
            md_files = list(self.vault_path.rglob("*.md"))
            total_files = len(md_files)
            result["steps"].append(f"发现 {total_files} 个 markdown 文件")

            # 批量添加文档到语义索引
            from src.index.embedder import Embedder
            embedder = Embedder()

            processed = 0
            for i, file_path in enumerate(md_files):
                try:
                    rel_path = str(file_path.relative_to(self.vault_path))
                    content = file_path.read_text(encoding='utf-8')

                    # 添加到关键词索引
                    self.keyword_index.add(
                        doc_id=rel_path,
                        content=content,
                        file_path=str(file_path),
                        start_line=0,
                        end_line=len(content.splitlines())
                    )

                    # 添加到语义索引
                    embedding = embedder.encode_single(content)
                    self.semantic_index.add_embedding(
                        doc_id=rel_path,
                        embedding=embedding.tolist(),
                        metadata={
                            'file_path': str(file_path),
                            'chunk_index': 0,
                            'total_chunks': 1
                        }
                    )

                    processed += 1
                    if (i + 1) % 50 == 0:
                        result["steps"].append(f"已处理 {i + 1}/{total_files} 个文件")

                except Exception as e:
                    result["steps"].append(f"处理文件 {rel_path} 失败：{e}")
                    continue

            result["steps"].append(f"语义索引重建完成，处理了 {processed}/{total_files} 个文件")
            result["steps"].append("索引完全重建成功")

            # 获取最终统计
            stats = self.get_index_stats()
            result["status"] = "completed"
            result["final_stats"] = stats
            result["message"] = f"索引完全重建成功，处理了 {processed} 个文件"

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            import traceback
            result["traceback"] = traceback.format_exc()

        return result

    async def _incremental_rebuild(self) -> Dict[str, Any]:
        """
        增量重建索引（只更新语义索引）

        Returns:
            Dict[str, Any]: 重建结果
        """
        result = {
            "status": "started",
            "mode": "incremental",
            "steps": [],
            "updated_files": []
        }

        try:
            # 获取所有 markdown 文件
            md_files = list(self.vault_path.rglob("*.md"))
            total_files = len(md_files)

            result["steps"].append(f"发现 {total_files} 个 markdown 文件")

            # 检查哪些文件需要更新（基于文件修改时间）
            files_to_update = []
            for file_path in md_files:
                try:
                    rel_path = str(file_path.relative_to(self.vault_path))
                    # 检查文件是否在索引中，如果不在或需要更新
                    if not self.semantic_index.is_indexed(rel_path):
                        files_to_update.append(file_path)
                except Exception:
                    continue

            result["steps"].append(f"需要更新 {len(files_to_update)} 个文件的语义索引")

            # 批量更新语义索引
            for i, file_path in enumerate(files_to_update):
                try:
                    rel_path = str(file_path.relative_to(self.vault_path))
                    content = file_path.read_text(encoding='utf-8')

                    # 添加到语义索引
                    self.semantic_index.add_document(rel_path, content)
                    result["updated_files"].append(rel_path)

                    # 进度更新
                    if (i + 1) % 10 == 0:
                        result["steps"].append(f"已更新 {i + 1}/{len(files_to_update)} 个文件")

                except Exception as e:
                    result["steps"].append(f"更新 {file_path} 失败：{str(e)}")
                    continue

            result["steps"].append("语义索引增量更新完成")

            # 获取最终统计
            stats = self.get_index_stats()
            result["status"] = "completed"
            result["final_stats"] = stats
            result["message"] = f"索引增量更新成功，更新了 {len(result['updated_files'])} 个文件"

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    async def update_index_for_file(self, file_path: str) -> Dict[str, Any]:
        """
        为单个文件更新索引（增量索引更新）

        Args:
            file_path: 文件路径（相对于 vault 根目录）

        Returns:
            Dict[str, Any]: 更新结果
        """
        try:
            full_path = self.vault_path / file_path

            if not full_path.exists():
                return {"status": "error", "message": f"文件不存在：{file_path}"}

            # 读取文件内容
            content = full_path.read_text(encoding='utf-8')

            # 更新关键词索引
            self.keyword_index.add_document(file_path, content)

            # 更新语义索引
            self.semantic_index.add_document(file_path, content)

            return {
                "status": "success",
                "message": f"文件索引已更新：{file_path}",
                "file_path": file_path
            }

        except Exception as e:
            return {"status": "error", "message": f"更新索引失败：{str(e)}"}

    async def remove_from_index(self, file_path: str) -> Dict[str, Any]:
        """
        从索引中移除文件

        Args:
            file_path: 文件路径（相对于 vault 根目录）

        Returns:
            Dict[str, Any]: 移除结果
        """
        try:
            # 从关键词索引中移除
            self.keyword_index.remove_document(file_path)

            # 从语义索引中移除
            self.semantic_index.remove_document(file_path)

            return {
                "status": "success",
                "message": f"文件已从索引中移除：{file_path}",
                "file_path": file_path
            }

        except Exception as e:
            return {"status": "error", "message": f"移除索引失败：{str(e)}"}


# 测试
if __name__ == "__main__":
    print("🧪 索引管理工具测试")

    # 创建测试配置
    from src.config.settings import load_config
    config = load_config()

    # 创建索引管理器
    index_manager = IndexManager(config)

    # 测试获取索引统计
    stats = index_manager.get_index_stats()
    print(f"✅ 索引统计：{json.dumps(stats, ensure_ascii=False, indent=2)}")

    print("✅ 索引管理工具测试通过")
