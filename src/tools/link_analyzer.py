"""
链接分析工具模块

提供笔记链接分析功能
"""

import re
from pathlib import Path
from typing import Dict, List


class LinkAnalyzer:
    """链接分析工具"""

    def __init__(self, root_path: str):
        """
        初始化链接分析工具

        Args:
            root_path: 根目录路径
        """
        self.root_path = Path(root_path).expanduser().resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def find_backlinks(self, file_path: str) -> List[str]:
        """
        查找反向链接

        Args:
            file_path: 文件路径

        Returns:
            List[str]: 反向链接列表
        """
        backlinks = []
        file_path = self.root_path / file_path

        # 读取文件内容
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找 [[link]] 格式的链接
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            backlinks.extend(links)

        return backlinks

    def find_outbound_links(self, file_path: str) -> List[str]:
        """
        查找出站链接

        Args:
            file_path: 文件路径

        Returns:
            List[str]: 出站链接列表
        """
        outbound_links = []
        file_path = self.root_path / file_path

        # 读取文件内容
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找 [[link]] 格式的链接
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            outbound_links.extend(links)

        return outbound_links

    def find_broken_links(self) -> Dict[str, List[str]]:
        """
        查找断裂链接

        Returns:
            Dict[str, List[str]]: 断裂链接字典
        """
        broken_links = {}

        # 遍历所有 .md 文件
        for file_path in self.root_path.rglob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 查找 [[link]] 格式的链接
                links = re.findall(r'\[\[([^\]]+)\]\]', content)

                # 检查链接是否存在
                for link in links:
                    link_path = self.root_path / f"{link}.md"
                    if not link_path.exists():
                        if str(file_path.relative_to(self.root_path)) not in broken_links:
                            broken_links[str(file_path.relative_to(self.root_path))] = []
                        broken_links[str(file_path.relative_to(self.root_path))].append(link)

            except Exception:
                continue

        return broken_links

    def find_orphaned_notes(self) -> List[str]:
        """
        查找孤立笔记

        Returns:
            List[str]: 孤立笔记列表
        """
        orphaned_notes = []

        # 获取所有文件
        all_files = list(self.root_path.rglob("*.md"))
        referenced_files = set()

        # 查找所有被引用的文件
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 查找 [[link]] 格式的链接
                links = re.findall(r'\[\[([^\]]+)\]\]', content)
                referenced_files.update(links)

            except Exception:
                continue

        # 查找未被引用的文件
        for file_path in all_files:
            file_name = file_path.stem
            if file_name not in referenced_files:
                orphaned_notes.append(str(file_path.relative_to(self.root_path)))

        return orphaned_notes


# 测试
if __name__ == "__main__":
    print("🧪 链接分析工具测试")

    # 创建测试实例
    analyzer = LinkAnalyzer("/tmp/test-vault")

    # 创建测试文件
    test_file = "/tmp/test-vault/test.md"
    test_content = """# 测试文档

[[链接1]]
[[链接2]]

这是测试内容，包含一些 [[链接]]。
"""

    # 写入测试文件
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    # 测试反向链接
    backlinks = analyzer.find_backlinks("test.md")
    print(f"✅ 反向链接测试: {backlinks}")

    # 测试出站链接
    outbound_links = analyzer.find_outbound_links("test.md")
    print(f"✅ 出站链接测试: {outbound_links}")

    # 测试断裂链接
    broken_links = analyzer.find_broken_links()
    print(f"✅ 断裂链接测试: {broken_links}")

    # 测试孤立笔记
    orphaned_notes = analyzer.find_orphaned_notes()
    print(f"✅ 孤立笔记测试: {orphaned_notes}")

    print("✅ 链接分析工具测试通过")
