"""
智能分块器：根据文档类型和标题结构动态调整切割参数
支持 Frontmatter 显式声明 + 标题层级自适应调整
"""

import hashlib
import re
import yaml
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field

# 导入基础分块器
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.index.chunker import Chunker, Chunk


@dataclass
class DocTypeConfig:
    """文档类型配置"""
    name: str
    base_chunk_size: int  # 基准大小
    base_overlap: int  # 基准重叠
    min_chunk_size: int  # 最小块大小
    # 标题层级调整系数 (H1-H6)
    heading_adjustments: Dict[int, float] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self):
        if not self.heading_adjustments:
            # 默认：所有层级不调整
            self.heading_adjustments = {i: 1.0 for i in range(1, 7)}


class AdaptiveChunker:
    """自适应分块器：类型优先 + 结构感知"""

    # 预定义文档类型配置
    DOC_TYPE_CONFIGS = {
        "faq": DocTypeConfig(
            name="faq",
            base_chunk_size=400,
            base_overlap=80,
            min_chunk_size=50,  # 降低最小块大小
            heading_adjustments={1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0},
            description="FAQ/问答类：小 chunk 精确匹配，不随标题变大"
        ),
        "technical": DocTypeConfig(
            name="technical",
            base_chunk_size=1000,
            base_overlap=200,
            min_chunk_size=80,  # 降低最小块大小
            heading_adjustments={1: 1.2, 2: 1.1, 3: 1.0, 4: 0.9, 5: 0.9, 6: 0.9},
            description="技术文档：大 chunk 保持上下文，大章节允许更大"
        ),
        "legal": DocTypeConfig(
            name="legal",
            base_chunk_size=1200,
            base_overlap=250,
            min_chunk_size=100,  # 降低最小块大小
            heading_adjustments={1: 1.3, 2: 1.2, 3: 1.1, 4: 1.0, 5: 1.0, 6: 1.0},
            description="法律文档：超大 chunk 保持条款完整性"
        ),
        "blog": DocTypeConfig(
            name="blog",
            base_chunk_size=600,
            base_overlap=120,
            min_chunk_size=50,  # 降低最小块大小
            heading_adjustments={1: 1.1, 2: 1.0, 3: 0.9, 4: 0.9, 5: 0.8, 6: 0.8},
            description="博客/文章：平衡策略，细节部分更精确"
        ),
        "meeting": DocTypeConfig(
            name="meeting",
            base_chunk_size=500,
            base_overlap=100,
            min_chunk_size=50,  # 降低最小块大小
            heading_adjustments={1: 1.1, 2: 1.0, 3: 0.9, 4: 0.9, 5: 0.8, 6: 0.8},
            description="会议记录：按议题分割，中等 chunk"
        ),
        "code": DocTypeConfig(
            name="code",
            base_chunk_size=800,
            base_overlap=150,
            min_chunk_size=30,  # 代码可以更小
            heading_adjustments={1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0},
            description="代码文件：按函数/类切割，不随标题调整"
        ),
        "default": DocTypeConfig(
            name="default",
            base_chunk_size=800,
            base_overlap=150,
            min_chunk_size=50,  # 降低默认最小块大小
            heading_adjustments={1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0},
            description="默认配置：通用策略"
        )
    }

    # 类型映射表（处理用户输入的差异）
    TYPE_MAPPING = {
        "question": "faq",
        "qna": "faq",
        "qa": "faq",
        "api": "technical",
        "guide": "technical",
        "manual": "technical",
        "doc": "technical",
        "contract": "legal",
        "agreement": "legal",
        "law": "legal",
        "note": "blog",
        "diary": "blog",
        "article": "blog",
        "post": "blog",
        "meeting_note": "meeting",
        "minutes": "meeting",
        "snippet": "code",
        "script": "code"
    }

    def __init__(self, custom_configs: Optional[Dict[str, DocTypeConfig]] = None):
        """
        初始化自适应分块器

        Args:
            custom_configs: 自定义文档类型配置
        """
        self.configs = self.DOC_TYPE_CONFIGS.copy()
        if custom_configs:
            self.configs.update(custom_configs)

    def detect_doc_type(self, file_path: str, content: str) -> str:
        """
        检测文档类型

        优先级：
        1. Frontmatter 中的 doc_type
        2. 文件名/路径关键词匹配
        3. 内容特征分析
        """
        # 1. 检查 Frontmatter
        if content.startswith("---"):
            try:
                end = content.find("---", 3)
                if end > 0:
                    frontmatter = yaml.safe_load(content[3:end])
                    if frontmatter and "doc_type" in frontmatter:
                        doc_type = frontmatter["doc_type"].lower()
                        # 类型映射
                        return self.TYPE_MAPPING.get(doc_type, doc_type)
            except Exception:
                pass

        # 2. 文件名/路径匹配
        file_name = Path(file_path).name.lower()
        if any(kw in file_name for kw in ["faq", "问", "答", "问题"]):
            return "faq"
        if any(kw in file_name for kw in ["api", "接口", "manual", "手册"]):
            return "technical"
        if any(kw in file_name for kw in ["合同", "协议", "law", "legal"]):
            return "legal"
        if any(kw in file_name for kw in ["meeting", "会议", "纪要"]):
            return "meeting"
        # 代码文件：只匹配特定扩展名，不匹配 .md
        if any(file_name.endswith(ext) for ext in [".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs"]):
            return "code"

        # 3. 内容特征分析（简化版）
        if re.search(r"问 [：:]\s*答 [：:]", content):
            return "faq"
        if re.search(r"##\s+.*[？?]\s*$", content, re.MULTILINE):
            return "faq"

        return "blog"  # 默认

    def detect_format(self, file_path: str) -> str:
        """检测文件格式"""
        ext = Path(file_path).suffix.lower()
        format_map = {
            ".md": "markdown",
            ".txt": "text",
            ".py": "python",
            ".js": "javascript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".html": "html",
            ".xml": "xml",
            ".csv": "csv"
        }
        return format_map.get(ext, "unknown")

    def _detect_sections(self, content: str) -> List[Tuple[int, str, int]]:
        """
        检测标题结构

        Returns:
            List[Tuple[int, str, int]]: [(行号，标题文本，标题层级), ...]
        """
        sections = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # 匹配 Markdown 标题
            match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                sections.append((i, title, level))

        return sections

    def _get_adjusted_chunk_size(self, doc_type: str, heading_level: int) -> int:
        """根据文档类型和标题层级调整 chunk_size"""
        config = self.configs.get(doc_type, self.configs["default"])
        factor = config.heading_adjustments.get(heading_level, 1.0)
        adjusted = int(config.base_chunk_size * factor)
        return max(adjusted, config.min_chunk_size)

    def _get_adjusted_overlap(self, doc_type: str, heading_level: int) -> int:
        """根据文档类型和标题层级调整 overlap"""
        # overlap 通常保持 chunk_size 的 20%
        chunk_size = self._get_adjusted_chunk_size(doc_type, heading_level)
        return int(chunk_size * 0.2)

    def chunk_file(
        self,
        file_path: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> List[Chunk]:
        """
        智能分块：类型决定基准，结构决定切割点

        Args:
            file_path: 文件路径
            content: 文件内容
            metadata: 额外元数据

        Returns:
            List[Chunk]: 文本块列表
        """
        # 1. 检测文档类型
        doc_type = self.detect_doc_type(file_path, content)
        config = self.configs.get(doc_type, self.configs["default"])

        # 2. 检测标题结构
        sections = self._detect_sections(content)

        # 3. 分块策略
        chunks = []

        if sections:
            # 按章节分块 (结构感知)
            sections.append((len(content.split('\n')), "", 0))  # 添加结束标记

            for i in range(len(sections) - 1):
                start_line, title, level = sections[i]
                end_line, _, _ = sections[i + 1]

                # 提取章节内容
                lines_content = content.split('\n')
                section_content = '\n'.join(lines_content[start_line:end_line])

                # 动态计算该章节的 chunk_size 和 overlap
                current_chunk_size = self._get_adjusted_chunk_size(doc_type, level)
                current_overlap = self._get_adjusted_overlap(doc_type, level)

                # 如果章节太大，递归切割
                if len(section_content) > current_chunk_size:
                    sub_chunks = self._chunk_text_with_level(
                        section_content,
                        file_path,
                        start_line + 1,
                        end_line,
                        doc_type,
                        level,
                        current_chunk_size,
                        current_overlap,
                        config.min_chunk_size,
                        title
                    )
                    chunks.extend(sub_chunks)
                elif len(section_content) >= config.min_chunk_size:
                    # 创建单个块
                    chunk = self._create_chunk(
                        section_content,
                        file_path,
                        start_line + 1,
                        end_line,
                        metadata,
                        title=title,
                        doc_type=doc_type,
                        heading_level=level,
                        chunk_size_used=current_chunk_size
                    )
                    chunks.append(chunk)
                # else: 章节太短，跳过（不添加任何块）
        else:
            # 无标题结构，使用基准大小
            chunker = Chunker(
                max_chars=config.base_chunk_size,
                overlap=config.base_overlap,
                min_chars=config.min_chunk_size
            )
            chunks = chunker.chunk_text(file_path, content, metadata)

        # 4. 增强元数据
        for chunk in chunks:
            chunk.metadata.update({
                "doc_type": doc_type,
                "heading_level": chunk.metadata.get("heading_level", 0),
                "chunk_size_used": chunk.metadata.get("chunk_size_used", config.base_chunk_size),
                "overlap_used": chunk.metadata.get("overlap_used", config.base_overlap),
                "doc_type_name": config.name,
                "description": config.description
            })

        return chunks

    def _chunk_text_with_level(
        self,
        content: str,
        file_path: str,
        start_line: int,
        end_line: int,
        doc_type: str,
        heading_level: int,
        chunk_size: int,
        overlap: int,
        min_size: int,
        title: str = ""
    ) -> List[Chunk]:
        """
        按标题层级递归切割

        Args:
            content: 章节内容
            file_path: 文件路径
            start_line: 起始行号
            end_line: 结束行号
            doc_type: 文档类型
            heading_level: 标题层级
            chunk_size: 当前 chunk_size
            overlap: 当前 overlap
            min_size: 最小块大小
            title: 章节标题

        Returns:
            List[Chunk]: 文本块列表
        """
        # 创建临时 Chunker 进行切割
        chunker = Chunker(
            max_chars=chunk_size,
            overlap=overlap,
            min_chars=min_size
        )

        # 调用基础分块器的 chunk_text 方法（只传必要参数）
        sub_chunks = chunker.chunk_text(file_path, content, {})

        # 检测文件格式
        file_format = self.detect_format(file_path)

        # 增强元数据
        for chunk in sub_chunks:
            chunk.metadata["doc_type"] = doc_type
            chunk.metadata["format"] = file_format
            chunk.metadata["heading_level"] = heading_level
            chunk.metadata["chunk_size_used"] = chunk_size
            chunk.metadata["overlap_used"] = overlap
            if title:
                chunk.metadata["section_title"] = title

        return sub_chunks

    def _create_chunk(
        self,
        content: str,
        file_path: str,
        start_line: int,
        end_line: int,
        metadata: Optional[dict],
        title: str = "",
        doc_type: str = "default",
        heading_level: int = 0,
        chunk_size_used: int = 800
    ) -> Chunk:
        """
        创建单个 Chunk

        Args:
            content: 文本内容
            file_path: 文件路径
            start_line: 起始行号
            end_line: 结束行号
            metadata: 额外元数据
            title: 标题
            doc_type: 文档类型
            heading_level: 标题层级
            chunk_size_used: 使用的 chunk_size

        Returns:
            Chunk: 文本块
        """
        # 生成唯一 ID
        chunk_id = f"{file_path}#{start_line}-{end_line}"
        if title:
            chunk_id += f"#{hashlib.md5(title.encode()).hexdigest()[:8]}"

        # 创建 Chunk
        chunk = Chunk(
            chunk_id=chunk_id,
            content=content.strip(),
            metadata={},
            file_path=file_path,
            start_line=start_line,
            end_line=end_line
        )

        # 设置元数据
        chunk.metadata.update({
            "title": title,
            "doc_type": doc_type,
            "heading_level": heading_level,
            "chunk_size_used": chunk_size_used
        })

        if metadata:
            chunk.metadata.update(metadata)

        return chunk
