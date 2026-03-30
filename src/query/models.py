"""
查询模块 - 数据模型和基础类
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum


class SearchMode(str, Enum):
    """搜索模式"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass
class SearchResult:
    """搜索结果"""
    doc_id: str
    score: float
    content: str
    file_path: str
    start_line: int = 0
    end_line: int = 0
    source: str = "hybrid"  # semantic/keyword/hybrid
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    doc_type: str = "default"
    priority: int = 5
    
    def __post_init__(self):
        """确保字段初始化"""
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = self.metadata.get("tags", [])
        if not self.tags and "tags" in self.metadata:
            self.tags = self.metadata["tags"]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "doc_id": self.doc_id,
            "score": self.score,
            "content": self.content,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "source": self.source,
            "metadata": self.metadata,
            "tags": self.tags,
            "doc_type": self.doc_type,
            "priority": self.priority
        }
    
    def __repr__(self):
        return f"SearchResult(doc_id={self.doc_id}, score={self.score:.4f}, file_path={self.file_path})"


@dataclass
class FilterOptions:
    """过滤选项"""
    tags: Optional[List[str]] = None
    doc_type: Optional[str] = None
    min_priority: Optional[int] = None
    max_priority: Optional[int] = None
    file_path: Optional[str] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    vault_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items() if v is not None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FilterOptions":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class NoteInfo:
    """笔记信息"""
    doc_id: str
    file_path: str
    vault_name: str
    title: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    priority: int = 5
    doc_type: str = "default"
    link_count: int = 0
    backlink_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "doc_id": self.doc_id,
            "file_path": self.file_path,
            "vault_name": self.vault_name,
            "title": self.title,
            "tags": self.tags,
            "priority": self.priority,
            "doc_type": self.doc_type,
            "link_count": self.link_count,
            "backlink_count": self.backlink_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None
        }


@dataclass
class LinkInfo:
    """链接信息"""
    link_id: int
    source_doc_id: str
    source_file_path: str
    target_doc_id: Optional[str] = None
    target_file_path: Optional[str] = None
    link_text: Optional[str] = None
    link_type: str = "internal"
    is_broken: bool = False
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "link_id": self.link_id,
            "source_doc_id": self.source_doc_id,
            "source_file_path": self.source_file_path,
            "target_doc_id": self.target_doc_id,
            "target_file_path": self.target_file_path,
            "link_text": self.link_text,
            "link_type": self.link_type,
            "is_broken": self.is_broken,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class TagInfo:
    """标签信息"""
    tag_id: int
    tag_name: str
    usage_count: int
    actual_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tag_id": self.tag_id,
            "tag_name": self.tag_name,
            "usage_count": self.usage_count,
            "actual_count": self.actual_count
        }


@dataclass
class IndexStats:
    """索引统计信息"""
    doc_count: int
    chunk_count: int
    tag_count: int
    link_count: int
    broken_link_count: int
    file_count: int
    frontmatter_count: int
    doc_type_distribution: Dict[str, int] = field(default_factory=dict)
    priority_distribution: Dict[int, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "doc_count": self.doc_count,
            "chunk_count": self.chunk_count,
            "tag_count": self.tag_count,
            "link_count": self.link_count,
            "broken_link_count": self.broken_link_count,
            "file_count": self.file_count,
            "frontmatter_count": self.frontmatter_count,
            "doc_type_distribution": self.doc_type_distribution,
            "priority_distribution": self.priority_distribution
        }
