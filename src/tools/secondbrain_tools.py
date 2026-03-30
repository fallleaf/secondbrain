"""
SecondBrain MCP 工具实现 - 多 Vault 支持

实现所有 MCP 工具的完整逻辑，支持多个 Vault 的独立索引和文件系统操作
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from src.config.settings import Settings
from src.utils.filesystem import FileSystem
from src.utils.priority import PriorityClassifier
from src.utils.frontmatter import parse_frontmatter, update_frontmatter
from src.index.keyword_index import KeywordIndex
from src.index.semantic_index import SemanticIndex
from src.index.hybrid_retriever import HybridRetriever
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)
from src.tools.link_analyzer import LinkAnalyzer
from src.tools.tag_manager import TagManager


class SecondBrainTools:
    """SecondBrain 工具实现 - 支持多 Vault"""

    def __init__(self, config: Settings):
        """
        初始化工具

        Args:
            config: 配置对象
        """
        self.config = config

        # 获取所有启用的 Vault
        enabled_vaults = config.get_enabled_vaults()
        if not enabled_vaults:
            raise ValueError("没有启用的 Vault，请至少启用一个 Vault")

        # 存储每个 Vault 的索引和文件系统
        self.vault_indexes: Dict[str, Dict[str, Any]] = {}
        self.vault_filesystems: Dict[str, FileSystem] = {}
        self.vault_link_analyzers: Dict[str, LinkAnalyzer] = {}
        self.vault_tag_managers: Dict[str, TagManager] = {}

        # 为每个启用的 Vault 创建独立的索引和文件系统
        for vault in enabled_vaults:
            vault_name = vault.name
            vault_path = vault.path
            try:
                # 创建文件系统
                self.vault_filesystems[vault_name] = FileSystem(vault_path)

                # 创建链接分析器和标签管理器
                self.vault_link_analyzers[vault_name] = LinkAnalyzer(vault_path)
                self.vault_tag_managers[vault_name] = TagManager(vault_path)

                # 确定索引路径
                # 如果 Vault 配置了独立索引路径，使用独立索引；否则使用全局索引
                keyword_db_path = vault.index.keyword_db or config.index.keyword.db_path
                semantic_db_path = vault.index.semantic_db or config.index.semantic.db_path

                # 创建关键词索引
                keyword_index = KeywordIndex(keyword_db_path)

                # 创建语义索引（如果启用）
                semantic_index = None
                if config.index.semantic.enabled:
                    try:
                        # 尝试自动检测维度（如果数据库已存在）
                        # 如果数据库不存在，使用默认维度 512
                        semantic_index = SemanticIndex(semantic_db_path, dim=None)
                        logger.info("✅ 语义索引初始化成功 (维度：%s)", semantic_index.dim)
                    except ImportError as e:
                        logger.warning("警告：语义索引不可用 (%s)，将仅使用关键词索引", e)
                    except Exception as e:
                        logger.warning("警告：语义索引初始化失败 (%s)，将仅使用关键词索引", e)

                # 创建优先级分类器（每个 Vault 共享同一个）
                priority_classifier = PriorityClassifier(config.priority.config_path)

                # 创建混合检索器
                hybrid_retriever = HybridRetriever(
                    keyword_index,
                    semantic_index,
                    priority_classifier,
                    tag_weights={"important": 2.0, "urgent": 1.5, "priority": 1.5, "pinned": 2.0},
                    vault_path=vault_path
                )

                # 存储到字典
                self.vault_indexes[vault_name] = {
                    'keyword_index': keyword_index,
                    'semantic_index': semantic_index,
                    'hybrid_retriever': hybrid_retriever,
                    'priority_classifier': priority_classifier
                }
                logger.info("✅ Vault '%s' 初始化成功", vault_name)

            except Exception as e:
                logger.error("❌ 初始化 Vault '%s' 失败：%s", vault_name, e)
                import traceback
                traceback.print_exc()
                continue  # 跳过失败的 Vault

        # 设置默认 Vault（第一个启用的 Vault）
        default_vault = enabled_vaults[0]
        default_vault_name = default_vault.name

        # 保留默认 Vault 的引用到顶层属性，保持向后兼容
        self.filesystem = self.vault_filesystems[default_vault_name]
        self.keyword_index = self.vault_indexes[default_vault_name]['keyword_index']
        self.semantic_index = self.vault_indexes[default_vault_name]['semantic_index']
        self.hybrid_retriever = self.vault_indexes[default_vault_name]['hybrid_retriever']
        self.priority_classifier = self.vault_indexes[default_vault_name]['priority_classifier']
        self.link_analyzer = self.vault_link_analyzers[default_vault_name]
        self.tag_manager = self.vault_tag_managers[default_vault_name]

        # 存储默认 Vault 名称
        self._default_vault_name = default_vault_name

    def _get_vault_name(self, vault_name: str) -> str:
        """
        获取有效的 Vault 名称

        Args:
            vault_name: 用户提供的 Vault 名称（可能为空）

        Returns:
            str: 有效的 Vault 名称

        Raises:
            ValueError: 如果指定的 Vault 不存在或未启用
        """
        enabled_vaults = self.config.get_enabled_vaults()
        enabled_vault_names = [v.name for v in enabled_vaults]

        # 如果 vault_name 为空，使用默认 Vault
        if not vault_name:
            return self._default_vault_name

        # 检查指定的 Vault 是否存在且已启用
        if vault_name not in enabled_vault_names:
            available_vaults = ', '.join(enabled_vault_names)
            raise ValueError(
                f"Vault '{vault_name}' 不存在或未启用。"
                f"可用的 Vault: {available_vaults}"
            )

        return vault_name

    def _get_vault_data(self, vault_name: str) -> Dict[str, Any]:
        """
        获取指定 Vault 的索引数据

        Args:
            vault_name: Vault 名称

        Returns:
            Dict[str, Any]: 包含 keyword_index, semantic_index, hybrid_retriever, priority_classifier 的字典
        """
        return self.vault_indexes[vault_name]

    def _get_filesystem(self, vault_name: str) -> FileSystem:
        """
        获取指定 Vault 的文件系统

        Args:
            vault_name: Vault 名称

        Returns:
            FileSystem: 该 Vault 的文件系统实例
        """
        return self.vault_filesystems[vault_name]

    def _get_link_analyzer(self, vault_name: str) -> LinkAnalyzer:
        """
        获取指定 Vault 的链接分析器

        Args:
            vault_name: Vault 名称

        Returns:
            LinkAnalyzer: 该 Vault 的链接分析器实例
        """
        return self.vault_link_analyzers[vault_name]

    def _get_tag_manager(self, vault_name: str) -> TagManager:
        """
        获取指定 Vault 的标签管理器

        Args:
            vault_name: Vault 名称

        Returns:
            TagManager: 该 Vault 的标签管理器实例
        """
        return self.vault_tag_managers[vault_name]

    async def semantic_search(self, arguments: Dict[str, Any]) -> List[str]:
        """
        语义搜索工具

        Args:
            arguments: 工具参数
                - query: 搜索查询
                - mode: 搜索模式 (hybrid, semantic, keyword)
                - top_k: 返回结果数量
                - vault_name: Vault 名称（可选，为空时使用默认 Vault）

        Returns:
            List[str]: 搜索结果
        """
        query = arguments.get("query", "")
        mode = arguments.get("mode", "hybrid")
        top_k = arguments.get("top_k", 10)
        vault_name = arguments.get("vault_name", "")

        if not query:
            return [json.dumps({"error": "缺少必需参数：query"}, ensure_ascii=False)]

        try:
            # 获取有效的 Vault 名称
            vault_name = self._get_vault_name(vault_name)

            # 获取该 Vault 的检索器
            vault_data = self._get_vault_data(vault_name)
            retriever = vault_data['hybrid_retriever']

            # 执行搜索
            from src.index.hybrid_retriever import SearchMode
            search_mode = SearchMode(mode) if mode in ['hybrid', 'semantic', 'keyword'] else SearchMode.HYBRID

            results = retriever.search(query, mode=search_mode, top_k=top_k)

            # 格式化结果
            result_list = []
            for result in results:
                result_dict = {
                    'doc_id': result.doc_id,
                    'score': result.score,
                    'content': result.content,
                    'file_path': result.file_path,
                    'start_line': result.start_line,
                    'end_line': result.end_line,
                    'source': result.source
                }
                result_list.append(json.dumps(result_dict, ensure_ascii=False))

            return result_list

        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            return [json.dumps({"error": f"搜索失败：{str(e)}"}, ensure_ascii=False)]

    async def read_note(self, arguments: Dict[str, Any]) -> List[str]:
        """
        读取笔记工具

        Args:
            arguments: 工具参数
                - path: 笔记路径
                - vault_name: Vault 名称（可选）

        Returns:
            List[str]: 笔记内容
        """
        path = arguments.get("path", "")
        vault_name = arguments.get("vault_name", "")

        if not path:
            return [json.dumps({"error": "缺少必需参数：path"}, ensure_ascii=False)]

        try:
            # 获取有效的 Vault 名称和文件系统
            vault_name = self._get_vault_name(vault_name)
            filesystem = self._get_filesystem(vault_name)

            content = filesystem.read_file(path)
            return [content]
        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            return [json.dumps({"error": f"读取文件失败：{str(e)}"}, ensure_ascii=False)]

    async def list_notes(self, arguments: Dict[str, Any]) -> List[str]:
        """
        列出笔记工具

        Args:
            arguments: 工具参数
                - directory: 目录路径
                - recursive: 是否递归
                - vault_name: Vault 名称（可选）

        Returns:
            List[str]: 文件列表
        """
        directory = arguments.get("directory", ".")
        recursive = arguments.get("recursive", False)
        vault_name = arguments.get("vault_name", "")

        try:
            # 获取有效的 Vault 名称和文件系统
            vault_name = self._get_vault_name(vault_name)
            filesystem = self._get_filesystem(vault_name)

            files = filesystem.list_files(directory, recursive)
            return files
        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            return [json.dumps({"error": f"列出文件失败：{str(e)}"}, ensure_ascii=False)]

    async def write_note(self, arguments: Dict[str, Any]) -> List[str]:
        """
        写入笔记工具

        Args:
            arguments: 工具参数
                - path: 笔记路径
                - content: 文件内容
                - overwrite: 是否覆盖现有文件
                - vault_name: Vault 名称（可选）

        Returns:
            List[str]: 写入结果
        """
        path = arguments.get("path", "")
        content = arguments.get("content", "")
        overwrite = arguments.get("overwrite", False)
        vault_name = arguments.get("vault_name", "")

        if not path:
            return [json.dumps({"error": "缺少必需参数：path"}, ensure_ascii=False)]

        try:
            # 获取有效的 Vault 名称和文件系统
            vault_name = self._get_vault_name(vault_name)
            filesystem = self._get_filesystem(vault_name)

            filesystem.write_file(path, content, overwrite)
            return [json.dumps({"status": "success", "message": f"文件写入成功：{path}"}, ensure_ascii=False)]
        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            return [json.dumps({"error": f"写入文件失败：{str(e)}"}, ensure_ascii=False)]

    async def delete_note(self, arguments: Dict[str, Any]) -> List[str]:
        """
        删除笔记工具

        Args:
            arguments: 工具参数
                - path: 笔记路径
                - confirm: 是否确认删除
                - vault_name: Vault 名称（可选）

        Returns:
            List[str]: 删除结果
        """
        path = arguments.get("path", "")
        confirm = arguments.get("confirm", False)
        vault_name = arguments.get("vault_name", "")

        if not path:
            return [json.dumps({"error": "缺少必需参数：path"}, ensure_ascii=False)]

        if not confirm:
            return [json.dumps({"error": f"需要确认才能删除文件：{path}", "message": "请设置 confirm=true 来确认删除"}, ensure_ascii=False)]

        try:
            # 获取有效的 Vault 名称和文件系统
            vault_name = self._get_vault_name(vault_name)
            filesystem = self._get_filesystem(vault_name)

            filesystem.delete_file(path)
            return [json.dumps({"status": "success", "message": f"文件删除成功：{path}"}, ensure_ascii=False)]
        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            return [json.dumps({"error": f"删除文件失败：{str(e)}"}, ensure_ascii=False)]

    async def move_note(self, arguments: Dict[str, Any]) -> List[str]:
        """
        移动笔记工具

        Args:
            arguments: 工具参数
                - source: 源路径
                - destination: 目标路径
                - update_links: 是否更新链接（暂未实现）
                - vault_name: Vault 名称（可选）

        Returns:
            List[str]: 移动结果
        """
        source = arguments.get("source", "")
        destination = arguments.get("destination", "")
        update_links = arguments.get("update_links", True)
        vault_name = arguments.get("vault_name", "")

        if not source or not destination:
            return [json.dumps({"error": "缺少必需参数：source 和 destination"}, ensure_ascii=False)]

        try:
            # 获取有效的 Vault 名称和文件系统
            vault_name = self._get_vault_name(vault_name)
            filesystem = self._get_filesystem(vault_name)

            filesystem.move_file(source, destination)

            result = {
                "status": "success",
                "message": f"文件移动成功：{source} -> {destination}",
                "links_updated": update_links  # 暂未实现链接更新
            }
            return [json.dumps(result, ensure_ascii=False)]
        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            return [json.dumps({"error": f"移动文件失败：{str(e)}"}, ensure_ascii=False)]

    async def search_notes(self, arguments: Dict[str, Any]) -> List[str]:
        """
        搜索笔记工具（混合检索：关键词 + 语义，支持跨 Vault）

        Args:
            arguments: 工具参数
            - query: 搜索查询
            - max_results: 最大结果数
            - vault_name: Vault 名称（可选，为空时搜索所有启用的 Vault）
            - mode: 搜索模式 (hybrid, keyword, semantic)

        Returns:
            List[str]: 搜索结果
        """
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 50)
        vault_name = arguments.get("vault_name", "")
        mode = arguments.get("mode", "hybrid")  # 默认混合检索

        if not query:
            return [json.dumps({"error": "缺少必需参数：query"}, ensure_ascii=False)]

        try:
            # 确定要搜索的 Vault 列表
            if vault_name:
                # 指定单个 Vault
                vaults_to_search = [vault_name]
            else:
                # 搜索所有启用的 Vault
                vaults_to_search = list(self.vault_indexes.keys())

            if not vaults_to_search:
                return [json.dumps({"error": "没有可用的 Vault"}, ensure_ascii=False)]

            # 收集所有 Vault 的搜索结果
            all_results = []
            for v_name in vaults_to_search:
                if v_name not in self.vault_indexes:
                    continue

                vault_data = self.vault_indexes[v_name]
                hybrid_retriever = vault_data.get('hybrid_retriever')

                if not hybrid_retriever:
                    continue

                # 执行混合检索
                from src.index.hybrid_retriever import SearchMode
                search_mode = SearchMode.HYBRID if mode == "hybrid" else (
                    SearchMode.KEYWORD if mode == "keyword" else SearchMode.SEMANTIC
                )

                results = hybrid_retriever.search(query, mode=search_mode, top_k=max_results)

                # 转换为字典格式并添加 Vault 名称
                for r in results:
                    # 确保 file_path 包含 Vault 信息（如果是相对路径，添加 Vault 前缀）
                    file_path = r.file_path
                    if not file_path.startswith('/'):
                        # 相对路径，添加 Vault 名称前缀以区分
                        file_path = f"{v_name}/{file_path}"

                    result_dict = {
                        'doc_id': r.doc_id,
                        'file_path': file_path,
                        'content': r.content,
                        'start_line': r.start_line,
                        'end_line': r.end_line,
                        'score': r.score,
                        'vault_name': v_name,
                        'source': r.source,
                        'metadata': r.metadata
                    }
                    all_results.append(result_dict)

            # 合并所有结果并去重（按 vault_name + doc_id 组合）
            seen_keys = set()
            unique_results = []
            for result in all_results:
                # 使用 (vault_name, doc_id) 作为唯一标识
                key = (result.get('vault_name', ''), result.get('doc_id', ''))
                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_results.append(result)

            # 按得分排序并限制结果数量
            unique_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            unique_results = unique_results[:max_results]

            # 格式化结果
            result_list = [json.dumps(r, ensure_ascii=False) for r in unique_results]
            return result_list

        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            import traceback
            return [json.dumps({"error": f"搜索失败：{str(e)}\n{traceback.format_exc()}"}, ensure_ascii=False)]

    async def get_index_stats(self, arguments: Dict[str, Any]) -> List[str]:
        """
        获取索引统计工具

        Args:
            arguments: 工具参数
                - vault_name: Vault 名称（可选）

        Returns:
            List[str]: 统计信息
        """
        vault_name = arguments.get("vault_name", "")

        try:
            # 获取有效的 Vault 名称和索引
            vault_name = self._get_vault_name(vault_name)
            vault_data = self._get_vault_data(vault_name)
            keyword_index = vault_data['keyword_index']

            stats = keyword_index.get_stats()
            return [json.dumps(stats, ensure_ascii=False, indent=2)]
        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            return [json.dumps({"error": f"获取索引统计失败：{str(e)}"}, ensure_ascii=False)]

    async def rebuild_semantic_index(self, arguments: Dict[str, Any]) -> List[str]:
        """
        重建语义索引工具

        Args:
            arguments: 工具参数
                - full: 是否完全重建
                - vault_name: Vault 名称（可选）

        Returns:
            List[str]: 重建结果
        """
        full = arguments.get("full", False)
        vault_name = arguments.get("vault_name", "")

        try:
            # 获取有效的 Vault 名称和索引
            vault_name = self._get_vault_name(vault_name)
            vault_data = self._get_vault_data(vault_name)
            keyword_index = vault_data['keyword_index']

            # 重建关键词索引
            keyword_index.rebuild()

            result = {
                "status": "success",
                "message": f"{'完全' if full else '开始'}重建索引完成",
                "vault_name": vault_name
            }
            return [json.dumps(result, ensure_ascii=False)]
        except ValueError as e:
            return [json.dumps({"error": str(e)}, ensure_ascii=False)]
        except Exception as e:
            return [json.dumps({"error": f"重建索引失败：{str(e)}"}, ensure_ascii=False)]

    async def get_priority_config(self, arguments: Dict[str, Any]) -> List[str]:
        """
        获取优先级配置工具

        Args:
            arguments: 工具参数

        Returns:
            List[str]: 优先级配置
        """
        try:
            config = {
                "default_priority": self.config.priority.default_priority,
                "config_path": self.config.priority.config_path,
                "enabled": self.config.priority.enabled,
                "description": "1-9 分级系统，1 为最高优先级"
            }
            return [json.dumps(config, ensure_ascii=False, indent=2)]
        except Exception as e:
            return [json.dumps({"error": f"获取优先级配置失败：{str(e)}"}, ensure_ascii=False)]

    # ========== Phase 4 元数据工具 ==========

    async def get_note_info(self, arguments: Dict[str, Any]) -> str:
        """
        获取笔记元数据工具

        Args:
            arguments: 工具参数
                - path: 笔记路径
                - vault_name: Vault 名称（可选）

        Returns:
            str: JSON 格式的笔记元数据（标题、标签、链接数、优先级）
        """
        path = arguments.get("path", "")
        vault_name = arguments.get("vault_name", "")

        if not path:
            return json.dumps({"error": "缺少必需参数：path"}, ensure_ascii=False)

        try:
            # 获取有效的 Vault 名称和文件系统
            vault_name = self._get_vault_name(vault_name)
            filesystem = self._get_filesystem(vault_name)
            link_analyzer = self._get_link_analyzer(vault_name)
            tag_manager = self._get_tag_manager(vault_name)
            vault_data = self._get_vault_data(vault_name)
            priority_classifier = vault_data['priority_classifier']

            # 获取完整路径
            full_path = Path(filesystem.root_path) / path
            full_path = full_path.expanduser().resolve()

            if not full_path.exists():
                return json.dumps({"error": f"文件不存在：{path}"}, ensure_ascii=False)

            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析 frontmatter 获取标题和标签
            frontmatter, _ = parse_frontmatter(content)

            # 获取标题
            title = frontmatter.get('title', '') if frontmatter else ''
            if not title:
                title = full_path.stem

            # 获取标签
            tags = []
            if frontmatter and 'tags' in frontmatter:
                tags = frontmatter['tags'] if isinstance(frontmatter['tags'], list) else [frontmatter['tags']]
            # 也检查内容中的 #tag 格式
            content_tags = tag_manager._extract_tags(content)
            for tag in content_tags:
                if tag not in tags:
                    tags.append(tag)

            # 获取链接数（出站链接）
            outbound_links = link_analyzer.find_outbound_links(path)
            link_count = len(outbound_links)

            # 获取反向链接数
            backlinks = link_analyzer.find_backlinks(path)
            backlink_count = len(backlinks)

            # 获取优先级
            relative_path = str(full_path.relative_to(filesystem.root_path))
            priority, source_type, sub_category = priority_classifier.infer_priority(relative_path)
            priority_label = priority_classifier.get_priority_label(priority)
            priority_description = priority_classifier.get_priority_description(priority)

            result = {
                "path": path,
                "title": title,
                "tags": tags,
                "link_count": link_count,
                "outbound_links": outbound_links,
                "backlink_count": backlink_count,
                "backlinks": backlinks,
                "priority": priority,
                "priority_label": priority_label,
                "priority_description": priority_description,
                "source_type": source_type,
                "sub_category": sub_category,
                "file_size": full_path.stat().st_size,
                "exists": True,
                "vault_name": vault_name
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"获取笔记信息失败：{str(e)}"}, ensure_ascii=False)

    async def get_note_tags(self, arguments: Dict[str, Any]) -> str:
        """
        获取笔记标签列表工具

        Args:
            arguments: 工具参数
                - path: 笔记路径
                - vault_name: Vault 名称（可选）

        Returns:
            str: JSON 格式的标签列表
        """
        path = arguments.get("path", "")
        vault_name = arguments.get("vault_name", "")

        if not path:
            return json.dumps({"error": "缺少必需参数：path"}, ensure_ascii=False)

        try:
            # 获取有效的 Vault 名称和标签管理器
            vault_name = self._get_vault_name(vault_name)
            tag_manager = self._get_tag_manager(vault_name)
            filesystem = self._get_filesystem(vault_name)

            # 获取完整路径
            full_path = Path(filesystem.root_path) / path
            full_path = full_path.expanduser().resolve()

            if not full_path.exists():
                return json.dumps({"error": f"文件不存在：{path}"}, ensure_ascii=False)

            # 使用 TagManager 获取标签
            tags = tag_manager.list_tags(path)

            result = {
                "path": path,
                "tags": tags,
                "tag_count": len(tags),
                "vault_name": vault_name
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"获取标签失败：{str(e)}"}, ensure_ascii=False)

    async def get_note_links(self, arguments: Dict[str, Any]) -> str:
        """
        获取笔记链接工具（出站链接和反向链接）

        Args:
            arguments: 工具参数
                - path: 笔记路径
                - vault_name: Vault 名称（可选）

        Returns:
            str: JSON 格式的链接信息
        """
        path = arguments.get("path", "")
        vault_name = arguments.get("vault_name", "")

        if not path:
            return json.dumps({"error": "缺少必需参数：path"}, ensure_ascii=False)

        try:
            # 获取有效的 Vault 名称和链接分析器
            vault_name = self._get_vault_name(vault_name)
            link_analyzer = self._get_link_analyzer(vault_name)
            filesystem = self._get_filesystem(vault_name)

            # 获取完整路径
            full_path = Path(filesystem.root_path) / path
            full_path = full_path.expanduser().resolve()

            if not full_path.exists():
                return json.dumps({"error": f"文件不存在：{path}"}, ensure_ascii=False)

            # 获取出站链接
            outbound_links = link_analyzer.find_outbound_links(path)

            # 获取反向链接
            backlinks = link_analyzer.find_backlinks(path)

            result = {
                "path": path,
                "outbound_links": outbound_links,
                "outbound_count": len(outbound_links),
                "backlinks": backlinks,
                "backlink_count": len(backlinks),
                "total_links": len(outbound_links) + len(backlinks),
                "vault_name": vault_name
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"获取链接失败：{str(e)}"}, ensure_ascii=False)

    async def get_backlinks(self, arguments: Dict[str, Any]) -> str:
        """
        获取反向链接工具

        Args:
            arguments: 工具参数
                - path: 笔记路径
                - vault_name: Vault 名称（可选）

        Returns:
            str: JSON 格式的反向链接列表
        """
        path = arguments.get("path", "")
        vault_name = arguments.get("vault_name", "")

        if not path:
            return json.dumps({"error": "缺少必需参数：path"}, ensure_ascii=False)

        try:
            # 获取有效的 Vault 名称和链接分析器
            vault_name = self._get_vault_name(vault_name)
            link_analyzer = self._get_link_analyzer(vault_name)
            filesystem = self._get_filesystem(vault_name)

            # 获取完整路径
            full_path = Path(filesystem.root_path) / path
            full_path = full_path.expanduser().resolve()

            if not full_path.exists():
                return json.dumps({"error": f"文件不存在：{path}"}, ensure_ascii=False)

            # 获取反向链接
            backlinks = link_analyzer.find_backlinks(path)

            result = {
                "path": path,
                "backlinks": backlinks,
                "backlink_count": len(backlinks),
                "vault_name": vault_name
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"获取反向链接失败：{str(e)}"}, ensure_ascii=False)

    async def find_broken_links(self, arguments: Dict[str, Any]) -> str:
        """
        查找断裂链接工具

        Args:
            arguments: 工具参数
                - vault_name: Vault 名称（可选）

        Returns:
            str: JSON 格式的断裂链接信息
        """
        vault_name = arguments.get("vault_name", "")

        try:
            # 获取有效的 Vault 名称和链接分析器
            vault_name = self._get_vault_name(vault_name)
            link_analyzer = self._get_link_analyzer(vault_name)

            # 使用 LinkAnalyzer 查找断裂链接
            broken_links = link_analyzer.find_broken_links()

            # 计算统计信息
            total_broken = sum(len(links) for links in broken_links.values())

            result = {
                "broken_links": broken_links,
                "total_files_with_broken_links": len(broken_links),
                "total_broken_links": total_broken,
                "vault_name": vault_name
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"查找断裂链接失败：{str(e)}"}, ensure_ascii=False)

    async def find_orphaned_notes(self, arguments: Dict[str, Any]) -> str:
        """
        查找孤立笔记工具

        Args:
            arguments: 工具参数
                - vault_name: Vault 名称（可选）

        Returns:
            str: JSON 格式的孤立笔记列表
        """
        vault_name = arguments.get("vault_name", "")

        try:
            # 获取有效的 Vault 名称和链接分析器
            vault_name = self._get_vault_name(vault_name)
            link_analyzer = self._get_link_analyzer(vault_name)

            # 使用 LinkAnalyzer 查找孤立笔记
            orphaned_notes = link_analyzer.find_orphaned_notes()

            result = {
                "orphaned_notes": orphaned_notes,
                "orphaned_count": len(orphaned_notes),
                "vault_name": vault_name
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"查找孤立笔记失败：{str(e)}"}, ensure_ascii=False)

    async def set_note_priority(self, arguments: Dict[str, Any]) -> str:
        """
        设置笔记优先级工具

        Args:
            arguments: 工具参数
                - path: 笔记路径
                - priority: 优先级值 (1-9)
                - vault_name: Vault 名称（可选）

        Returns:
            str: JSON 格式的操作结果
        """
        path = arguments.get("path", "")
        priority = arguments.get("priority")
        vault_name = arguments.get("vault_name", "")

        if not path:
            return json.dumps({"error": "缺少必需参数：path"}, ensure_ascii=False)

        if priority is None:
            return json.dumps({"error": "缺少必需参数：priority"}, ensure_ascii=False)

        try:
            # 验证优先级值
            if not isinstance(priority, int) or priority < 1 or priority > 9:
                return json.dumps({"error": "优先级必须是 1-9 之间的整数"}, ensure_ascii=False)

            # 获取有效的 Vault 名称和文件系统
            vault_name = self._get_vault_name(vault_name)
            filesystem = self._get_filesystem(vault_name)
            vault_data = self._get_vault_data(vault_name)
            priority_classifier = vault_data['priority_classifier']

            # 获取完整路径
            full_path = Path(filesystem.root_path) / path
            full_path = full_path.expanduser().resolve()

            if not full_path.exists():
                return json.dumps({"error": f"文件不存在：{path}"}, ensure_ascii=False)

            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 更新 frontmatter 中的优先级
            updated_content = update_frontmatter(content, {"priority": priority})

            # 写回文件
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            # 获取优先级标签和描述
            priority_label = priority_classifier.get_priority_label(priority)
            priority_description = priority_classifier.get_priority_description(priority)

            result = {
                "status": "success",
                "path": path,
                "priority": priority,
                "priority_label": priority_label,
                "priority_description": priority_description,
                "message": f"优先级设置成功：{priority} ({priority_label})",
                "vault_name": vault_name
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"设置优先级失败：{str(e)}"}, ensure_ascii=False)

    async def list_tags(self, arguments: Dict[str, Any]) -> str:
        """
        列出所有标签工具

        Args:
            arguments: 工具参数
                - vault_name: Vault 名称（可选）

        Returns:
            str: JSON 格式的所有标签列表
        """
        vault_name = arguments.get("vault_name", "")

        try:
            # 获取有效的 Vault 名称和标签管理器
            vault_name = self._get_vault_name(vault_name)
            tag_manager = self._get_tag_manager(vault_name)
            filesystem = self._get_filesystem(vault_name)

            all_tags = set()
            vault_path = Path(filesystem.root_path)

            # 遍历所有 markdown 文件
            for md_file in vault_path.rglob("*.md"):
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    tags = tag_manager._extract_tags(content)
                    all_tags.update(tags)
                except Exception:
                    continue

            # 转换为列表并排序
            tags_list = sorted(list(all_tags))

            result = {
                "tags": tags_list,
                "tag_count": len(tags_list),
                "vault_name": vault_name
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return [f"错误：{str(e)}"]
        except Exception as e:
            return [f"获取标签列表失败：{str(e)}"]
