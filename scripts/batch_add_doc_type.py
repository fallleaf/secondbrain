#!/usr/bin/env python3
"""
批量为 Markdown 文件添加 doc_type 字段

功能：
1. 扫描指定目录下的所有 Markdown 文件
2. 自动检测文档类型（或根据用户指定默认值）
3. 在 Frontmatter 中添加或更新 doc_type 字段
4. 生成处理报告

使用方法：
    python3 scripts/batch_add_doc_type.py --vault ~/NanobotMemory --default blog
    python3 scripts/batch_add_doc_type.py --vault ~/Obsidian --auto
    python3 scripts/batch_add_doc_type.py --vault ~/NanobotMemory --dry-run
"""

import argparse
import yaml
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# 导入自适应分块器用于类型检测
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from tools.adaptive_chunker import AdaptiveChunker


class DocTypeBatchProcessor:
    """批量处理文档类型"""
    
    def __init__(self, vault_path: str, default_type: str = "default", auto_detect: bool = False):
        """
        初始化处理器
        
        Args:
            vault_path: 仓库路径
            default_type: 默认文档类型
            auto_detect: 是否自动检测类型
        """
        self.vault_path = Path(vault_path)
        self.default_type = default_type
        self.auto_detect = auto_detect
        self.chunker = AdaptiveChunker() if auto_detect else None
        
        # 统计信息
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "type_distribution": {}
        }
        
        # 处理结果
        self.results: List[Dict] = []
    
    def detect_type(self, file_path: Path, content: str) -> str:
        """检测文档类型"""
        if self.auto_detect and self.chunker:
            return self.chunker.detect_doc_type(str(file_path), content)
        return self.default_type
    
    def process_file(self, file_path: Path) -> Optional[Dict]:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 处理结果，失败则返回 None
        """
        try:
            # 读取文件
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # 检测文档类型
            doc_type = self.detect_type(file_path, content)
            
            # 检查是否已有 Frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    # 解析 Frontmatter
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                        if not isinstance(frontmatter, dict):
                            frontmatter = {}
                    except yaml.YAMLError:
                        frontmatter = {}
                    
                    # 检查是否已有 doc_type
                    if "doc_type" in frontmatter:
                        # 已存在，跳过或更新
                        if frontmatter["doc_type"] == doc_type:
                            return {
                                "file": str(file_path),
                                "status": "skipped",
                                "reason": "doc_type 已存在且相同",
                                "doc_type": doc_type
                            }
                        else:
                            # 更新
                            frontmatter["doc_type"] = doc_type
                            new_frontmatter = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
                            content = "---\n" + new_frontmatter + "---\n" + parts[2]
                            self.stats["updated"] += 1
                    else:
                        # 添加
                        frontmatter["doc_type"] = doc_type
                        new_frontmatter = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
                        content = "---\n" + new_frontmatter + "---\n" + parts[2]
                        self.stats["updated"] += 1
                else:
                    # Frontmatter 格式错误，使用默认类型
                    frontmatter = {"doc_type": doc_type}
                    new_frontmatter = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
                    content = "---\n" + new_frontmatter + "---\n" + content
                    self.stats["updated"] += 1
            else:
                # 没有 Frontmatter，创建新的
                frontmatter = {"doc_type": doc_type}
                new_frontmatter = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
                content = "---\n" + new_frontmatter + "---\n" + content
                self.stats["updated"] += 1
            
            # 写入文件（如果内容已更改）
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
            
            # 记录结果
            result = {
                "file": str(file_path),
                "status": "updated" if content != original_content else "skipped",
                "doc_type": doc_type,
                "reason": "已添加/更新 doc_type" if content != original_content else "无变化"
            }
            
            # 更新类型分布
            self.stats["type_distribution"][doc_type] = self.stats["type_distribution"].get(doc_type, 0) + 1
            
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            return {
                "file": str(file_path),
                "status": "error",
                "error": str(e),
                "doc_type": None
            }
    
    def process_vault(self, dry_run: bool = False) -> Dict:
        """
        处理整个仓库
        
        Args:
            dry_run: 是否仅预览，不实际修改
            
        Returns:
            Dict: 处理统计信息
        """
        print(f"\n{'='*70}")
        print(f"📂 批量添加 doc_type 字段")
        print(f"{'='*70}")
        print(f"仓库路径：{self.vault_path}")
        print(f"默认类型：{self.default_type}")
        print(f"自动检测：{'是' if self.auto_detect else '否'}")
        print(f"预览模式：{'是' if dry_run else '否'}")
        print(f"{'='*70}\n")
        
        # 查找所有 Markdown 文件
        md_files = list(self.vault_path.rglob("*.md"))
        self.stats["total_files"] = len(md_files)
        
        print(f"📊 找到 {len(md_files)} 个 Markdown 文件\n")
        
        if dry_run:
            print("⚠️  预览模式：不会实际修改文件\n")
        
        # 处理每个文件
        for i, file_path in enumerate(md_files, 1):
            # 跳过隐藏目录和常见噪声目录
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if any(part in ['.git', 'node_modules', '__pycache__', '.obsidian'] for part in file_path.parts):
                continue
            
            print(f"[{i}/{len(md_files)}] 处理：{file_path.relative_to(self.vault_path)}", end="")
            
            result = self.process_file(file_path)
            if result:
                self.results.append(result)
                self.stats["processed"] += 1
                
                if result["status"] == "updated":
                    print(f" ✅ ({result['doc_type']})")
                elif result["status"] == "skipped":
                    print(f" ⏭️  {result['reason']}")
                elif result["status"] == "error":
                    print(f" ❌ {result['error']}")
            else:
                print(f" ❌ 处理失败")
        
        # 生成报告
        self._print_report(dry_run)
        
        return self.stats
    
    def _print_report(self, dry_run: bool):
        """打印处理报告"""
        print(f"\n{'='*70}")
        print(f"📊 处理报告")
        print(f"{'='*70}")
        print(f"总文件数：{self.stats['total_files']}")
        print(f"已处理：{self.stats['processed']}")
        print(f"已更新：{self.stats['updated']}")
        print(f"已跳过：{self.stats['skipped']}")
        print(f"错误数：{self.stats['errors']}")
        
        if dry_run:
            print(f"\n⚠️  这是预览模式，实际文件未被修改。")
            print(f"   运行时去掉 --dry-run 参数以实际执行。")
        
        print(f"\n📈 文档类型分布:")
        for doc_type, count in sorted(self.stats['type_distribution'].items(), key=lambda x: -x[1]):
            percentage = count / max(self.stats['processed'], 1) * 100
            print(f"   {doc_type}: {count} ({percentage:.1f}%)")
        
        # 显示前 10 个错误
        errors = [r for r in self.results if r.get("status") == "error"]
        if errors:
            print(f"\n❌ 错误列表 (前 10 个):")
            for error in errors[:10]:
                print(f"   - {error['file']}: {error['error']}")
        
        print(f"{'='*70}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量为 Markdown 文件添加 doc_type 字段",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认类型 'default'
  python3 batch_add_doc_type.py --vault ~/NanobotMemory
  
  # 使用默认类型 'blog'
  python3 batch_add_doc_type.py --vault ~/NanobotMemory --default blog
  
  # 自动检测类型
  python3 batch_add_doc_type.py --vault ~/Obsidian --auto
  
  # 预览模式（不实际修改）
  python3 batch_add_doc_type.py --vault ~/NanobotMemory --dry-run
        """
    )
    
    parser.add_argument(
        "--vault", "-v",
        required=True,
        help="仓库路径（如 ~/NanobotMemory 或 ~/Obsidian）"
    )
    
    parser.add_argument(
        "--default", "-d",
        default="default",
        help="默认文档类型（当 auto_detect 未启用时）"
    )
    
    parser.add_argument(
        "--auto", "-a",
        action="store_true",
        help="自动检测文档类型（使用 AdaptiveChunker）"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：仅显示将要做的修改，不实际写入文件"
    )
    
    args = parser.parse_args()
    
    # 验证路径
    vault_path = Path(args.vault).expanduser()
    if not vault_path.exists():
        print(f"❌ 错误：路径不存在：{vault_path}")
        return 1
    
    if not vault_path.is_dir():
        print(f"❌ 错误：不是目录：{vault_path}")
        return 1
    
    # 创建处理器并执行
    processor = DocTypeBatchProcessor(
        vault_path=str(vault_path),
        default_type=args.default,
        auto_detect=args.auto
    )
    
    stats = processor.process_vault(dry_run=args.dry_run)
    
    # 返回状态码
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
