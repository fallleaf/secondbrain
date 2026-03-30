"""
路径验证工具
"""

import os
from pathlib import Path
from typing import List, Optional


def validate_path(
    file_path: str,
    root_path: str,
    excluded_dirs: Optional[List[str]] = None
) -> Path:
    """
    验证文件路径
    
    Args:
        file_path: 文件路径
        root_path: 根目录路径
        excluded_dirs: 排除的目录列表
        
    Returns:
        Path: 验证后的路径
        
    Raises:
        ValueError: 路径无效
    """
    excluded_dirs = excluded_dirs or [".obsidian", ".trash", ".git"]
    
    # 转换为 Path 对象
    root = Path(root_path).expanduser().resolve()
    path = Path(file_path)
    
    # 如果是绝对路径，转换为相对路径
    if path.is_absolute():
        try:
            path = path.relative_to(path.root)
        except ValueError:
            raise ValueError(f"非法路径：{file_path}")
    
    # 解析完整路径
    full_path = (root / path).resolve()
    
    # 检查是否在根目录内
    if not str(full_path).startswith(str(root)):
        raise ValueError(f"路径遍历检测失败：{file_path}")
    
    # 检查排除目录
    path_parts = full_path.relative_to(root).parts
    for part in path_parts:
        if part in excluded_dirs:
            raise ValueError(f"访问被禁止的目录：{part}")
    
    return full_path


def sanitize_filename(filename: str) -> str:
    """
    清理文件名
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    # 移除危险字符
    dangerous_chars = ['/', '\\', '..', '\0', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # 移除前后空格
    filename = filename.strip()
    
    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename
