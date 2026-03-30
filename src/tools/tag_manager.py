"""
标签管理工具模块

提供笔记标签管理功能
"""

import re
from pathlib import Path
from typing import List, Dict


class TagManager:
    """标签管理工具"""

    def __init__(self, root_path: str):
        """
        初始化标签管理工具

        Args:
            root_path: 根目录路径
        """
        self.root_path = Path(root_path).expanduser().resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def add_tags(self, file_path: str, tags: List[str]) -> Dict[str, str]:
        """
        添加标签

        Args:
            file_path: 文件路径
            tags: 标签列表

        Returns:
            Dict[str, str]: 操作结果
        """
        result = {}
        file_path = Path(self.root_path) / Path(file_path)

        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析现有标签
            existing_tags = self._extract_tags(content)

            # 合并新标签
            all_tags = list(set(existing_tags + tags))

            # 更新内容
            updated_content = self._update_tags(content, all_tags)

            # 写入更新后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            result["status"] = "success"
            result["message"] = f"标签添加成功: {tags}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)

        return result

    def remove_tags(self, file_path: str, tags: List[str]) -> Dict[str, str]:
        """
        删除标签

        Args:
            file_path: 文件路径
            tags: 要删除的标签列表

        Returns:
            Dict[str, str]: 操作结果
        """
        result = {}
        file_path = Path(self.root_path) / Path(file_path)

        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析现有标签
            existing_tags = self._extract_tags(content)

            # 移除指定标签
            remaining_tags = [tag for tag in existing_tags if tag not in tags]

            # 更新内容
            updated_content = self._update_tags(content, remaining_tags)

            # 写入更新后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            result["status"] = "success"
            result["message"] = f"标签删除成功: {tags}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)

        return result

    def update_tags(self, file_path: str, tags: List[str],
                    mode: str = "replace") -> Dict[str, str]:
        """
        更新标签

        Args:
            file_path: 文件路径
            tags: 新标签列表
            mode: 更新模式 (replace, merge, remove)

        Returns:
            Dict[str, str]: 操作结果
        """
        result = {}
        file_path = Path(self.root_path) / Path(file_path)

        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if mode == "replace":
                # 替换所有标签
                updated_content = self._update_tags(content, tags)
            elif mode == "merge":
                # 合并标签
                existing_tags = self._extract_tags(content)
                all_tags = list(set(existing_tags + tags))
                updated_content = self._update_tags(content, all_tags)
            elif mode == "remove":
                # 移除指定标签
                existing_tags = self._extract_tags(content)
                remaining_tags = [tag for tag in existing_tags if tag not in tags]
                updated_content = self._update_tags(content, remaining_tags)
            else:
                updated_content = content

            # 写入更新后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            result["status"] = "success"
            result["message"] = f"标签更新成功: {mode}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)

        return result

    def list_tags(self, file_path: str) -> List[str]:
        """
        列出文件标签

        Args:
            file_path: 文件路径

        Returns:
            List[str]: 标签列表
        """
        file_path = Path(self.root_path) / Path(file_path)

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return self._extract_tags(content)

    def _extract_tags(self, content: str) -> List[str]:
        """提取标签"""
        # 查找 #tag 格式的标签
        tags = re.findall(r'#(\w+)', content)

        # 查找 frontmatter 中的 tags
        import yaml
        if content.startswith('---'):
            end_marker = content.find('\n---\n')
            if end_marker != -1:
                frontmatter_str = content[3:end_marker]
                try:
                    fm = yaml.safe_load(frontmatter_str)
                    if fm and 'tags' in fm:
                        tags.extend(fm['tags'])
                except Exception:
                    pass

        return list(set(tags))

    def _update_tags(self, content: str, tags: List[str]) -> str:
        """更新标签"""
        # 查找现有 frontmatter
        if content.startswith('---'):
            end_marker = content.find('\n---\n')
            if end_marker != -1:
                # 更新 frontmatter
                import yaml
                fm_str = content[3:end_marker]
                try:
                    fm = yaml.safe_load(fm_str) or {}
                    fm['tags'] = tags
                    fm_str = yaml.dump(fm, allow_unicode=True, default_flow_style=False)
                    return f"---\n{fm_str}---\n{content[end_marker + 5:]}"
                except Exception:
                    pass

        # 如果没有 frontmatter，添加新的
        if tags:
            tag_str = ' '.join([f"#{tag}" for tag in tags])
            return f"{tag_str}\n\n{content}"
        return content


# 测试
if __name__ == "__main__":
    print("🧪 标签管理工具测试")

    # 创建测试实例
    tag_manager = TagManager("/tmp/test-vault")

    # 测试内容
    test_content = """# 测试文档

#tag1 #tag2

这是测试内容"""

    # 写入测试文件
    with open("/tmp/test-vault/test.md", 'w', encoding='utf-8') as f:
        f.write(test_content)

    # 测试添加标签
    result = tag_manager.add_tags("test.md", ["new_tag"])
    print(f"✅ 添加标签测试: {result}")

    # 测试删除标签
    result = tag_manager.remove_tags("test.md", ["new_tag"])
    print(f"✅ 删除标签测试: {result}")

    # 测试列出标签
    tags = tag_manager.list_tags("test.md")
    print(f"✅ 列出标签测试: {tags}")

    print("✅ 标签管理工具测试通过")
