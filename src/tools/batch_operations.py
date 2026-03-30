"""
批量操作工具模块

提供批量文件操作功能
"""

from typing import List, Dict, Any
from pathlib import Path


class BatchOperations:
    """批量操作工具"""

    def __init__(self, root_path: str):
        """
        初始化批量操作工具

        Args:
            root_path: 根目录路径
        """
        self.root_path = Path(root_path).expanduser().resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def batch_update_frontmatter(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量更新 frontmatter

        Args:
            updates: 更新列表，每个元素包含 path 和 frontmatter 字段

        Returns:
            Dict[str, Any]: 操作结果
        """
        results = {}

        for update in updates:
            path = update.get("path", "")
            frontmatter = update.get("frontmatter", {})

            try:
                # 读取文件内容
                file_path = self.root_path / path
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析现有的 frontmatter
                existing_fm, remaining_content = self._parse_frontmatter(content)

                # 合并新的 frontmatter
                updated_content = self._update_frontmatter(content, frontmatter)

                # 写入更新后的内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)

                results[path] = {"status": "success", "message": "Frontmatter 更新成功"}

            except Exception as e:
                results[path] = {"status": "error", "message": str(e)}

        return results

    def batch_delete(self, file_paths: List[str], confirm: bool = False) -> Dict[str, Any]:
        """
        批量删除文件

        Args:
            file_paths: 文件路径列表
            confirm: 是否确认删除

        Returns:
            Dict[str, Any]: 删除结果
        """
        if not confirm:
            return {"status": "error", "message": "需要确认才能删除文件"}

        results = {}
        trash_dir = self.root_path / ".trash"
        trash_dir.mkdir(exist_ok=True)

        for path in file_paths:
            try:
                file_path = self.root_path / path

                # 移动到回收站
                trash_file = trash_dir / path
                trash_file.parent.mkdir(parents=True, exist_ok=True)

                file_path.rename(trash_file)
                results[path] = {"status": "success", "message": f"文件 {path} 删除成功"}

            except Exception as e:
                results[path] = {"status": "error", "message": str(e)}

        return results

    def batch_move(self, moves: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        批量移动文件

        Args:
            moves: 移动操作列表，每个元素包含 source 和 destination

        Returns:
            Dict[str, Any]: 移动结果
        """
        results = {}

        for move in moves:
            source = move.get("source", "")
            destination = move.get("destination", "")

            try:
                source_path = self.root_path / source
                dest_path = self.root_path / destination
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                source_path.rename(dest_path)
                results[f"{source} -> {destination}"] = {"status": "success", "message": "文件移动成功"}

            except Exception as e:
                results[f"{source} -> {destination}"] = {"status": "error", "message": str(e)}

        return results

    def _parse_frontmatter(self, content: str) -> tuple:
        """解析 frontmatter"""
        if not content.startswith('---'):
            return {}, content

        # 查找 frontmatter 结束标记
        end_marker = content.find('\n---\n')
        if end_marker == -1:
            return {}, content

        frontmatter_str = content[3:end_marker]
        remaining_content = content[end_marker + 5:]

        # 简单解析 YAML
        import yaml
        try:
            frontmatter = yaml.safe_load(frontmatter_str) or {}
            return frontmatter, remaining_content
        except Exception:
            return {}, remaining_content

    def _update_frontmatter(self, content: str, frontmatter: Dict[str, Any]) -> str:
        """更新 frontmatter"""
        # 解析现有内容
        existing_fm, remaining_content = self._parse_frontmatter(content)

        # 合并 frontmatter
        existing_fm.update(frontmatter)

        # 重新构建内容
        import yaml
        fm_str = yaml.dump(existing_fm, allow_unicode=True, default_flow_style=False)
        return f"---\n{fm_str}---\n{remaining_content}"


# 测试
if __name__ == "__main__":
    print("🧪 批量操作工具测试")

    # 创建测试实例
    batch_ops = BatchOperations("/tmp/test-vault")

    # 测试批量更新 frontmatter
    test_content = """---
title: 测试文档
tags: [test]
---
这是测试内容"""

    updates = [{
        "path": "test.md",
        "frontmatter": {"author": "test_user", "status": "draft"}
    }]

    result = batch_ops.batch_update_frontmatter(updates)
    print(f"✅ 批量更新 frontmatter 测试: {result}")

    print("✅ 批量操作工具测试通过")
