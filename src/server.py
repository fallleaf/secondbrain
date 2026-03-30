"""
SecondBrain MCP 服务器

基于 FastMCP 的 MCP 服务器实现
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.config.settings import load_config, Settings
from src.tools.index_mgmt import IndexManager
from src.tools.secondbrain_tools import SecondBrainTools

# 配置日志：输出到 stderr，避免污染 stdout (MCP 协议要求)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr  # 关键：日志必须输出到 stderr
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class SecondBrainServer:
    """SecondBrain MCP 服务器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化服务器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config: Optional[Settings] = None
        self.tools: Optional[SecondBrainTools] = None
        self.index_manager: Optional[IndexManager] = None

        # MCP 服务器实例
        self.server = Server("secondbrain")

        # 先加载配置和初始化组件
        self._load_config()
        self._init_components()

        # 再注册工具
        self._register_tools()

    def _load_config(self) -> None:
        """加载配置"""
        logger.info("📝 加载配置...")
        try:
            self.config = load_config(self.config_path)
            logger.info("✅ 配置加载成功")
        except Exception as e:
            logger.error(f"❌ 配置加载失败：{e}")
            raise

    def _init_components(self) -> None:
        """初始化组件"""
        logger.info("\n🔧 初始化组件...")

        # 初始化工具
        self.tools = SecondBrainTools(self.config)
        self.index_manager = IndexManager(self.config)

        logger.info("✅ 组件初始化完成")

    def _register_tools(self) -> None:
        """注册 MCP 工具"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """列出所有可用工具"""
            return [
                Tool(
                    name="semantic_search",
                    description="执行语义搜索，支持混合检索 (keyword+semantic+priority)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索查询"},
                            "mode": {
                                "type": "string",
                                "enum": ["hybrid", "semantic", "keyword"],
                                "description": "搜索模式"
                            },
                            "top_k": {
                                "type": "integer",
                                "default": 10,
                                "description": "返回结果数量"
                            },
                            "vault_name": {
                                "type": "string",
                                "description": "指定 Vault 名称"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="read_note",
                    description="读取笔记内容",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "笔记路径"},
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="list_notes",
                    description="列出目录中的笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "directory": {"type": "string", "description": "目录路径"},
                            "recursive": {
                                "type": "boolean",
                                "default": False,
                                "description": "是否递归"
                            },
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["directory"]
                    }
                ),
                Tool(
                    name="write_note",
                    description="创建或更新笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "笔记路径"},
                            "content": {"type": "string", "description": "笔记内容"},
                            "overwrite": {
                                "type": "boolean",
                                "default": False,
                                "description": "是否覆盖现有文件"
                            },
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["path", "content"]
                    }
                ),
                Tool(
                    name="delete_note",
                    description="删除笔记 (软删除到 .trash/)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "笔记路径"},
                            "confirm": {
                                "type": "boolean",
                                "description": "确认删除"
                            },
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["path", "confirm"]
                    }
                ),
                Tool(
                    name="move_note",
                    description="移动或重命名笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "源路径"},
                            "destination": {"type": "string", "description": "目标路径"},
                            "update_links": {
                                "type": "boolean",
                                "default": True,
                                "description": "是否更新链接"
                            },
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["source", "destination"]
                    }
                ),
                Tool(
                    name="search_notes",
                    description="关键词搜索笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                            "max_results": {
                                "type": "integer",
                                "default": 50,
                                "description": "最大结果数"
                            },
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["query"]
                    }
                ),
                # ========== Phase 4 元数据工具 ==========
                Tool(
                    name="get_note_info",
                    description="获取笔记元数据信息（标题、标签、链接数、优先级等）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "笔记路径"},
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="get_note_tags",
                    description="获取笔记的标签列表",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "笔记路径"},
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="get_note_links",
                    description="获取笔记的链接信息（出站链接和反向链接）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "笔记路径"},
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="get_backlinks",
                    description="获取笔记的反向链接列表",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "笔记路径"},
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="find_broken_links",
                    description="查找 vault 中所有断裂的链接",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="find_orphaned_notes",
                    description="查找 vault 中没有被任何笔记链接的孤立笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="set_note_priority",
                    description="设置笔记的优先级（1-9）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "笔记路径"},
                            "priority": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 9,
                                "description": "优先级值 (1-9)"
                            },
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": ["path", "priority"]
                    }
                ),
                Tool(
                    name="list_tags",
                    description="列出 vault 中所有使用的标签",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "vault_name": {"type": "string", "description": "Vault 名称"}
                        },
                        "required": []
                    }
                ),
                # ========== 索引管理工具 ==========
                Tool(
                    name="get_index_stats",
                    description="获取索引统计信息",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="rebuild_semantic_index",
                    description="重建语义索引",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "full": {
                                "type": "boolean",
                                "default": False,
                                "description": "是否完全重建（包括关键词索引）"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_priority_config",
                    description="获取优先级配置",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """调用工具"""
            try:
                # Phase 4 元数据工具
                if name == "get_note_info":
                    result = await self.tools.get_note_info(arguments)
                elif name == "get_note_tags":
                    result = await self.tools.get_note_tags(arguments)
                elif name == "get_note_links":
                    result = await self.tools.get_note_links(arguments)
                elif name == "get_backlinks":
                    result = await self.tools.get_backlinks(arguments)
                elif name == "find_broken_links":
                    result = await self.tools.find_broken_links(arguments)
                elif name == "find_orphaned_notes":
                    result = await self.tools.find_orphaned_notes(arguments)
                elif name == "set_note_priority":
                    result = await self.tools.set_note_priority(arguments)
                elif name == "list_tags":
                    result = await self.tools.list_tags(arguments)
                # 索引管理工具
                elif name == "get_index_stats":
                    result = await asyncio.to_thread(lambda: self.index_manager.get_index_stats())
                    result = json.dumps(result, ensure_ascii=False, indent=2)
                elif name == "rebuild_semantic_index":
                    full = arguments.get("full", False)
                    result = await self.index_manager.rebuild_semantic_index(full)
                    result = json.dumps(result, ensure_ascii=False, indent=2)
                # 原有工具
                elif name == "semantic_search":
                    result = await self.tools.semantic_search(arguments)
                elif name == "read_note":
                    result = await self.tools.read_note(arguments)
                elif name == "list_notes":
                    result = await self.tools.list_notes(arguments)
                elif name == "write_note":
                    result = await self.tools.write_note(arguments)
                elif name == "delete_note":
                    result = await self.tools.delete_note(arguments)
                elif name == "move_note":
                    result = await self.tools.move_note(arguments)
                elif name == "search_notes":
                    result = await self.tools.search_notes(arguments)
                elif name == "get_priority_config":
                    result = await self.tools.get_priority_config(arguments)
                else:
                    result = [f"未知工具：{name}"]

                # 确保结果是 TextContent 列表
                if isinstance(result, str):
                    return [TextContent(type="text", text=result)]
                elif isinstance(result, list):
                    return [
                        TextContent(
                            type="text",
                            text=r) if isinstance(
                            r,
                            str) else TextContent(
                            type="text",
                            text=str(r)) for r in result]
                else:
                    return [TextContent(type="text", text=str(result))]

            except Exception as e:
                return [TextContent(type="text", text=f"工具调用失败：{str(e)}")]


async def main():
    """主函数"""
    # 创建服务器
    server = SecondBrainServer()

    # 运行服务器
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
