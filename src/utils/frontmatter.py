"""
Frontmatter 解析工具
"""

import re
from typing import Any, Dict, Optional, Tuple


def parse_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    解析 Markdown 文件的 frontmatter

    Args:
        content: 文件内容

    Returns:
        Tuple[Optional[Dict[str, Any]], str]: (frontmatter 字典，剩余内容)
    """
    # 检查是否有 frontmatter
    if not content.startswith('---'):
        return None, content

    # 查找结束标记
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return None, content

    # 提取 frontmatter
    frontmatter_str = content[3:end_match.start() + 3]
    remaining = content[end_match.end() + 1:]

    # 解析 YAML
    try:
        import yaml
        frontmatter = yaml.safe_load(frontmatter_str)
        if frontmatter is None:
            frontmatter = {}
        return frontmatter, remaining
    except Exception:
        return None, content


def update_frontmatter(
    content: str,
    frontmatter: Dict[str, Any],
    merge: bool = True
) -> str:
    """
    更新或创建 frontmatter

    Args:
        content: 文件内容
        frontmatter: 新的 frontmatter 字典
        merge: 是否合并现有 frontmatter

    Returns:
        str: 更新后的内容
    """
    # 解析现有 frontmatter
    existing_fm, remaining = parse_frontmatter(content)

    # 合并 frontmatter
    if merge and existing_fm:
        existing_fm.update(frontmatter)
        frontmatter = existing_fm

    # 生成新的 frontmatter
    import yaml
    fm_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)

    # 构建新内容
    return f"---\n{fm_str}---\n{remaining}"


def get_frontmatter_field(content: str, field_name: str) -> Optional[Any]:
    """
    获取 frontmatter 中的字段值

    Args:
        content: 文件内容
        field_name: 字段名

    Returns:
        Optional[Any]: 字段值
    """
    frontmatter, _ = parse_frontmatter(content)

    if frontmatter and field_name in frontmatter:
        return frontmatter[field_name]

    return None


def set_frontmatter_field(
    content: str,
    field_name: str,
    value: Any,
    merge: bool = True
) -> str:
    """
    设置 frontmatter 中的字段值

    Args:
        content: 文件内容
        field_name: 字段名
        value: 字段值
        merge: 是否合并现有 frontmatter

    Returns:
        str: 更新后的内容
    """
    frontmatter, remaining = parse_frontmatter(content)

    if merge and frontmatter:
        frontmatter[field_name] = value
    else:
        frontmatter = {field_name: value}

    return update_frontmatter(content, frontmatter, merge)


def delete_frontmatter_field(content: str, field_name: str) -> str:
    """
    删除 frontmatter 中的字段

    Args:
        content: 文件内容
        field_name: 字段名

    Returns:
        str: 更新后的内容
    """
    frontmatter, remaining = parse_frontmatter(content)

    if frontmatter and field_name in frontmatter:
        del frontmatter[field_name]

        # 如果 frontmatter 为空，移除它
        if not frontmatter:
            return remaining

        return update_frontmatter(content, frontmatter, merge=False)

    return content
